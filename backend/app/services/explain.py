"""Alert explanations: a static, curated catalog of actions and caveats per level and profile
(Spanish and English), a deterministic template, and optionally muse-spark through the
OpenAI-compatible Meta API, which only selects and rephrases catalog items and writes the
headline and why from the facts.

Facts are per cell and night: never emails, push tokens, user coordinates or labels (the
observed outcome of the night is not sent). One call per (cell, night, level, profile,
language), cached in the explanations table by a hash of the facts, the model version, the
prompt version and the engine. Every number in the generated text is checked against the facts;
on any failure, or when MUSE_MOCK=1, the template is used.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import Explanation
from ..providers.base import CellRecord
from ..schemas import DriverGroup
from .drivers import group_drivers
from .risk import LEVEL_ORDER

log = logging.getLogger("frostwatch.explain")

PROMPT_VERSION = "explain-v1"
PROMPT_FILE = Path(__file__).resolve().parents[1] / "prompts" / "explain_v1.txt"
CUTOFF_LOCAL = "18:00"

LEVEL_LABELS = {
    "es": {"low": "bajo", "moderate": "moderado", "high": "alto", "very_high": "muy alto"},
    "en": {"low": "low", "moderate": "moderate", "high": "high", "very_high": "very high"},
}


def content_language(language: str) -> str:
    """Language for explanations, emails and push. Catalogs exist only in es and en,
    so ay and qu users get the Spanish version."""
    return language if language in ("es", "en") else "es"

# (id, minimum level, {lang: text}). Qualitative only: no damage thresholds, no crop
# temperatures, no medical or health advice.
ACTIONS: dict[str, list[tuple[str, str, dict[str, str]]]] = {
    "producer": [
        ("cover_crops", "moderate", {
            "es": "Cubra los cultivos sensibles y los almácigos con tela o plástico antes del anochecer.",
            "en": "Cover sensitive crops and seedbeds with fabric or plastic before dusk."}),
        ("shelter_livestock", "moderate", {
            "es": "Guarde el ganado, sobre todo las crías, en corrales protegidos del viento.",
            "en": "Keep livestock, especially young animals, in corrals sheltered from the wind."}),
        ("water_troughs", "moderate", {
            "es": "Revise temprano los bebederos y las fuentes de agua del ganado por si se congelan.",
            "en": "Check livestock troughs and water sources early in the morning in case they freeze."}),
        ("harvest_ready", "high", {
            "es": "Si tiene una cosecha lista, considere recogerla antes de la noche.",
            "en": "If a crop is ready, consider harvesting it before the night."}),
        ("fodder", "high", {
            "es": "Tenga forraje a mano por si los pastos amanecen congelados.",
            "en": "Keep fodder at hand in case pastures are frozen in the morning."}),
        ("check_morning", "moderate", {
            "es": "Revise los cultivos por la mañana para ver si hubo daño.",
            "en": "Check the crops in the morning for damage."}),
    ],
    "resident": [
        ("insulate_pipes", "moderate", {
            "es": "Proteja o aísle las tuberías y los grifos expuestos.",
            "en": "Protect or insulate exposed water pipes and taps."}),
        ("drain_hoses", "moderate", {
            "es": "Vacíe las mangueras y los recipientes de agua que quedan afuera.",
            "en": "Drain hoses and outdoor water containers."}),
        ("road_ice", "moderate", {
            "es": "Si maneja temprano, tenga cuidado con el hielo en caminos y puentes.",
            "en": "When driving early, watch for ice on roads and bridges."}),
        ("vehicle", "high", {
            "es": "Si puede, estacione el vehículo bajo techo y revise el refrigerante.",
            "en": "If possible, park the vehicle under cover and check the coolant."}),
        ("store_water", "high", {
            "es": "Guarde algo de agua por si las tuberías se congelan.",
            "en": "Store some water in case the pipes freeze."}),
        ("plants_property", "moderate", {
            "es": "Entre las plantas en maceta y proteja lo que el hielo pueda dañar.",
            "en": "Bring potted plants indoors and protect property that ice can damage."}),
    ],
}

CAVEATS: list[tuple[str, dict[str, str]]] = [
    ("reanalysis", {
        "es": "Datos de reanálisis (ERA5-Land, Copernicus CDS), no son una observación directa ni un pronóstico en vivo.",
        "en": "Reanalysis data (ERA5-Land, Copernicus CDS), not a direct observation or a live forecast."}),
    ("labels", {
        "es": "El modelo se evaluó con heladas del mismo reanálisis; la helada en su terreno puede ser distinta.",
        "en": "The model was evaluated against frost from the same reanalysis; frost on your land can differ."}),
    ("processed", {
        "es": "Esta alerta se calculó al procesar la noche indicada; no es un aviso inmediato.",
        "en": "This alert was computed when the night was processed; it is not an instant warning."}),
    ("grid", {
        "es": "La celda del modelo cubre un área amplia; los bajos y las quebradas pueden enfriarse más.",
        "en": "The model cell covers a wide area; hollows and valley floors can get colder."}),
    ("mock", {
        "es": "DATOS SIMULADOS (MOCK): no provienen del modelo ni del reanálisis.",
        "en": "SIMULATED DATA (MOCK): not from the model or the reanalysis."}),
]
REQUIRED_CAVEATS = ["reanalysis", "labels", "processed"]
BANNED = re.compile(r"tiempo real|real[ -]time|instant|en vivo|live forecast|sat[eé]lite|satellite|salud|health|m[eé]dic",
                    re.IGNORECASE)
# A signed number not glued to a word (so "ERA5" or "stl1" are not numbers). Dates are checked
# as whole tokens first and must equal the night date.
NUMBER = re.compile(r"(?<![\w.,])-?\d+(?:[.,]\d+)?")
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


@dataclass
class Facts:
    night_date: str
    cell_name: str
    probability_pct: int
    level: str
    level_label: str
    language: str
    profile: str
    drivers: list[dict]
    reliability: dict
    data_source: str
    model_version: str
    cutoff_local: str = CUTOFF_LOCAL

    def public(self) -> dict:
        """What the LLM sees (the model version only enters the cache key)."""
        d = dict(self.__dict__)
        d.pop("model_version")
        return d


def build_facts(rec: CellRecord, profile: str, language: str, groups: list[DriverGroup] | None = None) -> Facts:
    language = content_language(language)
    groups = groups if groups is not None else group_drivers(rec.top_drivers)
    rel = rec.historical_reliability
    return Facts(
        night_date=rec.night_date.isoformat(), cell_name=rec.name, probability_pct=round(rec.probability * 100),
        level=rec.level, level_label=LEVEL_LABELS[language][rec.level], language=language, profile=profile,
        drivers=[{"theme": g.theme, "label": g.label_es if language == "es" else g.label_en,
                  "effect": "raises risk" if g.effect == "up" else "lowers risk"} for g in groups[:4]],
        reliability={"range_pct": [round(rel.range[0] * 100), round(rel.range[1] * 100)],
                     "observed_rate_pct": round(rel.observed_rate * 100), "n": rel.n},
        data_source=rec.data_source, model_version=rec.model_version)


def catalog_for(facts: Facts) -> dict:
    lvl = LEVEL_ORDER[facts.level]
    actions = [{"id": i, "text": t[facts.language]} for i, min_lvl, t in ACTIONS[facts.profile]
               if LEVEL_ORDER[min_lvl] <= lvl]
    caveat_ids = [*REQUIRED_CAVEATS, "grid"] + (["mock"] if facts.data_source == "MOCK" else [])
    caveats = [{"id": i, "text": t[facts.language]} for i, t in CAVEATS if i in caveat_ids]
    required = REQUIRED_CAVEATS + (["mock"] if facts.data_source == "MOCK" else [])
    return {"actions": actions, "caveats": caveats, "required_caveat_ids": required}


def allowed_numbers(facts: Facts, catalog: dict | None = None) -> set[float]:
    """Numbers that may appear in an explanation: the facts and the catalog texts (e.g. ERA5)."""
    rel = facts.reliability
    nums = {facts.probability_pct, *rel["range_pct"], rel["observed_rate_pct"], rel["n"]}
    nums |= {18, 0}  # the 18:00 cutoff
    texts = [facts.cell_name, facts.data_source]
    if catalog:
        texts += [it["text"] for it in catalog["actions"] + catalog["caveats"]]
    nums |= {float(x.replace(",", ".")) for t in texts for x in NUMBER.findall(t)}
    return {float(n) for n in nums}


def numbers_ok(text: str, allowed: set[float], night_date: str) -> bool:
    if any(d != night_date for d in DATE.findall(text)):
        return False
    for raw in NUMBER.findall(DATE.sub(" ", text)):
        if float(raw.replace(",", ".")) not in allowed:
            return False
    return True


def verify(payload: dict, facts: Facts, catalog: dict) -> str | None:
    """None when the explanation is acceptable, else the reason."""
    if not isinstance(payload, dict) or set(payload) != {"headline", "why", "actions", "caveats"}:
        return "schema"
    if not (isinstance(payload["headline"], str) and isinstance(payload["why"], str)):
        return "schema"
    if not payload["headline"].strip() or len(payload["headline"]) > 140 or not payload["why"].strip():
        return "schema"
    action_ids = {a["id"] for a in catalog["actions"]}
    caveat_ids = {c["id"] for c in catalog["caveats"]}
    for key, ids in (("actions", action_ids), ("caveats", caveat_ids)):
        items = payload[key]
        if not isinstance(items, list) or not items:
            return "schema"
        for it in items:
            if not (isinstance(it, dict) and it.get("id") in ids and isinstance(it.get("text"), str) and it["text"].strip()):
                return f"{key}_not_in_catalog"
    if not set(catalog["required_caveat_ids"]) <= {c["id"] for c in payload["caveats"]}:
        return "missing_required_caveat"
    allowed = allowed_numbers(facts, catalog)
    texts = [payload["headline"], payload["why"], *(a["text"] for a in payload["actions"]),
             *(c["text"] for c in payload["caveats"])]
    if not all(numbers_ok(t, allowed, facts.night_date) for t in texts):
        return "number_not_in_facts"
    if BANNED.search(payload["headline"] + " " + payload["why"]):
        return "banned_phrase"
    return None


def template(facts: Facts, catalog: dict) -> dict:
    """Deterministic explanation built only from the facts and the catalog."""
    es = facts.language == "es"
    up = [d["label"].lower() for d in facts.drivers if d["effect"] == "raises risk"][:2]
    down = [d["label"].lower() for d in facts.drivers if d["effect"] == "lowers risk"][:2]
    rel = facts.reliability
    if es:
        headline = f"Riesgo {facts.level_label} de helada en {facts.cell_name}, noche del {facts.night_date}"
        why = [f"La probabilidad estimada de helada para {facts.cell_name} la noche del {facts.night_date} es "
               f"{facts.probability_pct}% (nivel {facts.level_label}), con datos hasta las {facts.cutoff_local}."]
        if up:
            why.append(f"Lo que más sube el riesgo: {', '.join(up)}.")
        if down:
            why.append(f"Lo que más lo baja: {', '.join(down)}.")
        if rel["n"] > 0:
            why.append(f"En validación, de {rel['n']} noches con probabilidad entre {rel['range_pct'][0]}% y "
                       f"{rel['range_pct'][1]}%, hubo helada en el {rel['observed_rate_pct']}%.")
    else:
        headline = f"{facts.level_label.capitalize()} frost risk in {facts.cell_name}, night of {facts.night_date}"
        why = [f"The estimated frost probability for {facts.cell_name} on the night of {facts.night_date} is "
               f"{facts.probability_pct}% ({facts.level_label} level), using data up to {facts.cutoff_local}."]
        if up:
            why.append(f"Raising the risk most: {', '.join(up)}.")
        if down:
            why.append(f"Lowering it most: {', '.join(down)}.")
        if rel["n"] > 0:
            why.append(f"On validation, of {rel['n']} nights with a probability between {rel['range_pct'][0]}% and "
                       f"{rel['range_pct'][1]}%, frost occurred on {rel['observed_rate_pct']}%.")
    n_actions = 3 if facts.level == "moderate" else 5
    caveats = [c for c in catalog["caveats"] if c["id"] in catalog["required_caveat_ids"] or c["id"] == "grid"]
    return {"headline": headline, "why": " ".join(why), "actions": catalog["actions"][:n_actions], "caveats": caveats}


def facts_hash(facts: Facts, engine: str) -> str:
    blob = json.dumps({"facts": facts.__dict__, "prompt": PROMPT_VERSION, "engine": engine}, sort_keys=True,
                      ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    return text


@dataclass
class Explainer:
    settings: Settings
    http: httpx.Client | None = None
    calls_made: int = 0
    stats: dict = field(default_factory=lambda: {"cache_hits": 0, "muse_ok": 0, "template": 0, "fallbacks": {}})

    @property
    def engine(self) -> str:
        return "template" if self.settings.muse_mock else f"muse:{self.settings.muse_model}"

    def explain(self, db: Session, facts: Facts) -> Explanation:
        key = facts_hash(facts, self.engine)
        cached = db.scalar(select(Explanation).where(Explanation.facts_hash == key))
        if cached:
            self.stats["cache_hits"] += 1
            return cached
        catalog = catalog_for(facts)
        payload, source, reason = None, "template", None
        if self.settings.muse_mock:
            reason = None
        elif not (self.settings.meta_api_key and self.settings.meta_api_base_url):
            reason = "muse_not_configured"
        else:
            payload, reason = self._call_muse(facts, catalog, key)
            if payload is not None:
                source = "muse"
        if payload is None:
            payload = template(facts, catalog)
            self.stats["template"] += 1
            if reason:
                self.stats["fallbacks"][reason] = self.stats["fallbacks"].get(reason, 0) + 1
                log.info("explanation fallback to template: %s", reason)
        else:
            self.stats["muse_ok"] += 1
        row = Explanation(facts_hash=key, model_version=facts.model_version, language=facts.language,
                          profile=facts.profile, level=facts.level, source=source,
                          payload={"headline": payload["headline"], "why": payload["why"],
                                   "actions": [a["text"] for a in payload["actions"]],
                                   "caveats": [c["text"] for c in payload["caveats"]]},
                          fallback_reason=reason)
        db.add(row)
        db.flush()
        return row

    def _call_muse(self, facts: Facts, catalog: dict, key: str) -> tuple[dict | None, str | None]:
        """At most two requests: one retry only when the reply is not valid JSON."""
        user = json.dumps({"facts": facts.public(), "catalog": catalog}, ensure_ascii=False)
        messages = [{"role": "system", "content": PROMPT_FILE.read_text(encoding="utf-8")},
                    {"role": "user", "content": user}]
        for attempt in (1, 2):
            if self.calls_made >= self.settings.muse_max_calls_per_run:
                return None, "max_calls_per_run"
            self.calls_made += 1
            try:
                content, usage = self._post(messages)
            except Exception as exc:  # network or HTTP error: no retry
                self._log_usage(key, {}, f"error:{type(exc).__name__}")
                return None, f"api_error:{type(exc).__name__}"
            try:
                payload = json.loads(_strip_fences(content))
            except (json.JSONDecodeError, TypeError):
                self._log_usage(key, usage, "invalid_json")
                if attempt == 1:
                    continue
                return None, "invalid_json"
            self._log_usage(key, usage, "ok")
            reason = verify(payload, facts, catalog)
            return (payload, None) if reason is None else (None, reason)
        return None, "invalid_json"

    def _post(self, messages: list[dict]) -> tuple[str, dict]:
        url = self.settings.meta_api_base_url.rstrip("/") + "/chat/completions"
        body = {"model": self.settings.muse_model, "messages": messages, "temperature": 0,
                "max_tokens": self.settings.muse_max_tokens, "response_format": {"type": "json_object"}}
        client = self.http or httpx.Client(timeout=60)
        try:
            resp = client.post(url, json=body, headers={"Authorization": f"Bearer {self.settings.meta_api_key}"})
            resp.raise_for_status()
            data = resp.json()
        finally:
            if self.http is None:
                client.close()
        return data["choices"][0]["message"]["content"], data.get("usage") or {}

    def _log_usage(self, key: str, usage: dict, status: str) -> None:
        path = self.settings.muse_usage_log
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"ts": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), "model": self.settings.muse_model,
                 "prompt_version": PROMPT_VERSION, "facts_hash": key[:16], "status": status,
                 "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
                 "total_tokens": usage.get("total_tokens")}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
