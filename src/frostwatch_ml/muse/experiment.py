"""Muse experiment, condition A vs condition B, validation only (the test split stays locked).

A: LR_best as stored (C=1, L1, no class weight, sigmoid calibration kept only if it lowers the
validation Brier score, threshold maximizing F2 on validation), recomputed once with the same code.
B: the same model and preprocessing on the Muse-improved table:
  B1 tiny negative de-accumulation values clipped in code, plus Muse-reviewed corrections of a capped
     sample of flagged hours (train and validation years), features rebuilt with the same code;
  B2 Muse-proposed formulas over the allowlist, computed by the whitelist parser.
Labels are never edited: B keeps the labels of A. Model rows come from leakage.model_rows only.
"""

from __future__ import annotations

import json
import platform
from typing import Any

import joblib
import numpy as np
import pandas as pd
import yaml

from .. import config, leakage, runner, splits
from ..artifacts.bundle import package_versions
from ..dataio.cds_reader import read_agera5, read_era5land
from ..dataio.manifest import manifest_entries
from ..dataio.tables import content_sha256, read_json, sha256_of, write_csv, write_json, write_parquet, write_text
from ..evaluation import reports
from ..evaluation.cells import MAIN, skill
from ..features import fitted
from ..features.night_table import build_point_frame, finalize
from ..models.calibration import apply_platt, fit_platt_oof
from ..models.registry import build
from ..prep.units import convert_era5land
from ..tracking import mlflow_logger
from . import costs, masking, proposals, review, schema
from .client import MuseClient

OUT = config.PROCESSED / "muse"
PRED_DIR = config.PREDICTIONS / "muse"
REPORT = config.REPORTS / "muse_experiment.md"
USAGE_DOC = config.DOCS / "muse_usage.md"
SAMPLE_CALLS = config.ROOT / "logs" / "sample_muse_calls.jsonl"
REPRODUCE = ".venv/bin/python pipelines/05_muse_correct.py --config configs/muse.yaml --no-sync"
FEATURE_KEYS = ["point_id", "night_date"]


# Data -----------------------------------------------------------------------------------------

def load_hourly() -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    """Converted hourly ERA5-Land series and daily AgERA5 series per cell."""
    entries = manifest_entries()
    convs, agera = {}, {}
    for pid in config.point_ids():
        convs[pid] = convert_era5land(read_era5land(pid, entries))
        agera[pid] = read_agera5(pid, entries)
    return convs, agera


def build_table(convs: dict[str, pd.DataFrame], agera: dict[str, pd.DataFrame], frost_cfg: dict) -> pd.DataFrame:
    """Night table from given hourly series with the same code as features/night_table.py."""
    parts, xcs = [], []
    for pid in config.point_ids():
        df, xc = build_point_frame(pid, convs[pid], agera[pid], frost_cfg)
        parts.append(df)
        xcs.append(xc)
    df = pd.concat(parts, ignore_index=True)
    stats = fitted.fit(df, frost_cfg)
    df, _ = finalize(df, pd.concat(xcs, ignore_index=True), stats)
    splits.assert_integrity(df, frost_cfg["split"])
    return df


def with_labels_of(table: pd.DataFrame, a: pd.DataFrame) -> pd.DataFrame:
    """Same rows as A, labels copied from A (B never edits labels)."""
    if not table[FEATURE_KEYS].equals(a[FEATURE_KEYS]):
        raise ValueError("rebuilt table rows differ from the A table")
    out = table.copy()
    out["frost"] = a["frost"].to_numpy()
    out["tmin_c"] = a["tmin_c"].to_numpy()
    return out


def diff_values(before: pd.DataFrame, after: pd.DataFrame, feats: list[str]) -> dict[str, Any]:
    """Number of feature values that changed, per feature, with the largest absolute change."""
    per = {}
    rows_changed = np.zeros(len(before), dtype=bool)
    for f in feats:
        x, y = before[f].to_numpy(dtype=float), after[f].to_numpy(dtype=float)
        ch = ~((x == y) | (np.isnan(x) & np.isnan(y)))
        if ch.any():
            per[f] = {"changed": int(ch.sum()), "max_abs_change": float(np.nanmax(np.abs(x[ch] - y[ch])))}
            rows_changed |= ch
    by_split = pd.Series(before["split"].to_numpy()[rows_changed]).value_counts().to_dict()
    return {"values_changed": int(sum(v["changed"] for v in per.values())), "rows_changed": int(rows_changed.sum()),
            "rows_changed_by_split": {str(k): int(v) for k, v in by_split.items()}, "per_feature": per}


def prompt_version(relpath: str) -> tuple[str, str]:
    path = config.ROOT / relpath
    text = path.read_text()
    return text, f"{path.stem}@{sha256_of(path)[:8]}"


# Models ---------------------------------------------------------------------------------------

def fit_like_best(data: runner.ModelData, params: dict, seed: int, cv_splits: int, name: str):
    """Same procedure as LR_best in pipelines/05_round2.py: fit on train, sigmoid calibration from a
    year-grouped out-of-fold fit on train, kept only if it lowers the validation Brier score; the
    F2 threshold is chosen on validation."""
    def factory():
        return build("lr", data.features, seed=seed, **params)
    res = runner.evaluate(factory(), data, name=name)
    cal = fit_platt_oof(factory, data.train, data.train["frost"].to_numpy(int), n_splits=cv_splits)
    p_cal = apply_platt(res.model.decision_score(data.val), cal)
    res_cal = runner.evaluate(res.model, data, score_val=p_cal, name=name)
    if res_cal.pooled["brier"] < res.pooled["brier"]:
        return res_cal, cal
    return res, None


def model_data_b(b: pd.DataFrame, features_b: list[str], a_data: runner.ModelData) -> runner.ModelData:
    leakage.assert_no_crosscheck_columns(b)
    leakage.assert_feature_list(features_b)
    return runner.ModelData(train=leakage.model_rows(b, "train"), val=leakage.model_rows(b, "validation"),
                            features=features_b, data_hash=content_sha256(b),
                            features_manifest_sha256=a_data.features_manifest_sha256,
                            split_cfg=a_data.split_cfg, label_definition=a_data.label_definition)


# Run ------------------------------------------------------------------------------------------

def plan_b1(mcfg: dict, seed: int, frost_cfg: dict, convs: dict) -> dict[str, Any]:
    rcfg = mcfg["anomaly_review"]
    anoms = pd.read_parquet(config.PROCESSED / "anomalies.parquet")
    clipped, clip_counts = {}, {}
    for pid, conv in convs.items():
        clipped[pid], n = review.clip_tiny_negatives(conv, rcfg["clip_tiny_negatives"])
        for k, v in n.items():
            clip_counts[k] = clip_counts.get(k, 0) + v
    scope = review.in_scope(anoms, frost_cfg, rcfg["sample_splits"])
    sample = review.stratified_sample(scope, rcfg["sample_cap"], seed)
    sample["record_id"] = [review.record_id(seed, p, t, f) for p, t, f in
                           zip(sample["point_id"], sample["timestamp_utc"], sample["field"], strict=True)]
    records = [review.build_record(r, clipped[r["point_id"]], rcfg, frost_cfg, r["record_id"]) for _, r in sample.iterrows()]
    for rec in records:
        masking.assert_masked({"records": [rec]})
    bs = rcfg["batch_size"]
    batches = [records[i:i + bs] for i in range(0, len(records), bs)]
    sample["batch"] = [i // bs for i in range(len(sample))]
    hour = anoms["timestamp_utc"].dt.hour
    funnel = {"anomalies_total": int(len(anoms)),
              "by_rule_field": anoms.groupby(["rule", "field"]).size().rename("n").reset_index().to_dict(orient="records"),
              "affect_a_feature": int(sum(h in review.feature_hours(f, frost_cfg) for f, h in zip(anoms["field"], hour, strict=True))),
              "clipped_values_in_code": clip_counts,
              "in_scope_for_review": int(len(scope)),
              "in_scope_by_rule_field": scope.groupby(["rule", "field"]).size().rename("n").reset_index().to_dict(orient="records"),
              "sampled": int(len(sample)), "batches": len(batches)}
    return {"clipped": clipped, "sample": sample, "records": records, "batches": batches, "funnel": funnel}


def estimate(client: MuseClient, calls: list[tuple[str, dict]]) -> dict[str, Any]:
    """Planning estimate from the real prompt texts (chars / 4) and max_tokens as the output bound."""
    b = client.cfg["budget"]
    inp = 0
    for system, payload in calls:
        user = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        inp += costs.estimate_tokens(system + user, b["chars_per_token_estimate"])
    out = client.max_tokens * len(calls)
    return {"calls": len(calls), "input_tokens_est": inp, "output_tokens_worst_case": out,
            "cost_worst_case_usd": round(costs.cost_usd(inp, out, b), 4),
            "cost_input_only_usd": round(costs.cost_usd(inp, 0, b), 4)}


def smoke(mcfg: dict, seed: int, n: int) -> dict[str, Any]:
    """One real call with an n-record batch; checks that strict JSON parses and matches the schema."""
    frost_cfg = config.frost_config()
    convs, _ = load_hourly()
    plan = plan_b1(mcfg, seed, frost_cfg, convs)
    system, pv = prompt_version(mcfg["prompts"]["anomaly_review"])
    batch = plan["records"][:n]
    client = MuseClient(mcfg)
    res = client.call("smoke_anomaly_review", pv, system, {"records": batch}, review.mock_review)
    items, errors = schema.validate_review(res.parsed, [r["id"] for r in batch])
    return {"mock": client.mock, "status": res.status, "source": res.source, "usage": res.usage, "error": res.error,
            "json_parsed": res.parsed is not None, "schema_valid_items": len(items), "schema_errors": errors,
            "items": items}


def run(mcfg: dict, seed: int, dry_run: bool = False, log_mlflow: bool = True) -> dict[str, Any]:
    frost_cfg = config.frost_config()
    rcfg, pcfg = mcfg["anomaly_review"], mcfg["feature_proposals"]
    client = MuseClient(mcfg)
    usage_before = costs.summarize(costs.read_usage(client.usage_log))
    a = pd.read_parquet(config.PROCESSED / "features.parquet")
    a_hash = content_sha256(a)
    run_id = f"muse-ab-{a_hash[:8]}"
    feats = leakage.feature_list()

    convs, agera = load_hourly()
    plan = plan_b1(mcfg, seed, frost_cfg, convs)
    sys_review, pv_review = prompt_version(mcfg["prompts"]["anomaly_review"])
    sys_prop, pv_prop = prompt_version(mcfg["prompts"]["feature_proposals"])
    names = proposals.usable_names(feats, pcfg)
    est_payload = proposals.summary_payload(leakage.model_rows(a, "train"), names, pcfg)
    est = estimate(client, [(sys_review, {"records": b}) for b in plan["batches"]] + [(sys_prop, est_payload)])
    print(f"mode: {'MOCK' if client.mock else 'REAL'}; usage so far (real calls, this experiment): "
          f"{usage_before['total']['calls']} calls, {usage_before['total']['est_cost_usd']:.4f} USD")
    print("plan:", json.dumps(plan["funnel"]["clipped_values_in_code"]), f"in scope {plan['funnel']['in_scope_for_review']},",
          f"sampled {plan['funnel']['sampled']}, batches {plan['funnel']['batches']}")
    print("estimate:", json.dumps(est))
    if dry_run:
        return {"run_id": run_id, "estimate": est, "funnel": plan["funnel"], "dry_run": True}

    # Sanity check: the same code on the unmodified series reproduces the A table exactly.
    rebuilt = build_table(convs, agera, frost_cfg)
    if content_sha256(rebuilt) != a_hash:
        raise RuntimeError("rebuilding the night table without changes does not reproduce features.parquet")
    del rebuilt

    # B1: Muse review of the sampled flagged hours
    sample, batches = plan["sample"], plan["batches"]
    items: dict[str, dict] = {}
    batch_status, call_log = {}, []
    for bi, batch in enumerate(batches):
        payload = {"records": batch}
        masking.assert_masked(payload)
        res = client.call("anomaly_review", pv_review, sys_review, payload, review.mock_review)
        got, errs = schema.validate_review(res.parsed, [r["id"] for r in batch]) if res.status == "ok" else ({}, [])
        items.update(got)
        batch_status[bi] = res.status
        call_log.append({"batch": bi, "records": len(batch), "status": res.status, "source": res.source,
                         "cache_key": res.cache_key, "usage": res.usage, "error": res.error, "schema_errors": errs})
    decisions, new_values = [], []
    for _, row in sample.iterrows():
        st = batch_status[row["batch"]]
        item = items.get(row["record_id"])
        if st != "ok":
            d, v = ("call_failed" if st == "failed" else "invalid_json"), None
        else:
            d, v = review.decide(row, item, plan["clipped"][row["point_id"]], rcfg)
        decisions.append({"action": item["action"] if item else None, "muse_value": item["value"] if item else None,
                          "confidence": item["confidence"] if item else None, "reason": item["reason"] if item else None,
                          "decision": d})
        new_values.append(v)
    corr = pd.concat([sample[["record_id", "batch", "point_id", "timestamp_utc", "cutoff_utc", "night_split", "field",
                              "rule", "value"]].rename(columns={"value": "original_value"}),
                      pd.DataFrame(decisions)], axis=1)
    corr["new_value"] = new_values
    applied = corr[corr["decision"] == "applied"]
    conv_b = {pid: review.apply_corrections(c, applied[applied["point_id"] == pid]) for pid, c in plan["clipped"].items()}
    clip_t = with_labels_of(build_table(plan["clipped"], agera, frost_cfg), a)
    b1 = with_labels_of(build_table(conv_b, agera, frost_cfg), a)
    diff_clip = diff_values(a, clip_t, feats)
    diff_muse = diff_values(clip_t, b1, feats)
    del clip_t

    # B2: one call, Muse proposes formulas, code computes them
    train_b1 = leakage.model_rows(b1, "train")
    prop_payload = proposals.summary_payload(train_b1, names, pcfg)
    masking.assert_masked(prop_payload)
    pres = client.call("feature_proposals", pv_prop, sys_prop, prop_payload, proposals.mock_proposals)
    cands, prop_errors = schema.validate_proposals(pres.parsed, pcfg["max_features"]) if pres.status == "ok" else ([], [pres.status])
    model_mask = b1["split"].isin(["train", "validation"]) & b1["frost"].notna()
    lab = b1[model_mask.to_numpy()].reset_index(drop=True)
    cols, prop_rows = proposals.accept(cands, lab, (lab["split"] == "train").to_numpy(), names, feats)
    b = b1.copy()
    for name, row in ((r["column"], r) for r in prop_rows if r["column"]):
        b[name] = proposals.formula.evaluate(proposals.formula.parse(row["formula"], set(names)), b1)
    features_b = feats + list(cols)

    # Models on validation
    a_data = runner.load_model_data()
    b_data = model_data_b(b, features_b, a_data)
    cand = read_json(config.PROCESSED / "model_candidates.json")["finalists"]["LR_best"]
    params = dict(cand["params"])
    cv_splits = config.model_config()["round2"]["calibration"]["cv_splits"]
    res_a, cal_a = fit_like_best(a_data, params, seed, cv_splits, "A_LR_best")
    res_b, cal_b = fit_like_best(b_data, params, seed, cv_splits, "B_muse")
    ref_id = mcfg["decision_rule"]["reference_run"]
    stored = read_json(config.EXPERIMENTS / ref_id / "metrics.json")
    check_keys = ["pr_auc", "f2", "precision", "recall", "f1", "roc_auc", "brier", "accuracy", "threshold"]
    a_diff = {k: abs(res_a.pooled[k] - stored["validation_pooled"][k]) for k in check_keys}
    a_confirmed = max(a_diff.values()) < 1e-9
    refs = {k: runner.evaluate(build(k, feats, **({"doy_halfwidth": 7} if k == "climatology" else {})), a_data, name=k)
            for k in ("climatology", "persistence")}

    pooled = pd.DataFrame({**{k: r.pooled for k, r in refs.items()}, "A": res_a.pooled, "B": res_b.pooled}).T[MAIN + ["threshold"]]
    macro_t = pd.DataFrame({**{k: r.macro for k, r in refs.items()}, "A": res_a.macro, "B": res_b.macro}).T[MAIN]
    pooled.index.name = macro_t.index.name = "model"
    cells = pd.concat({"A": res_a.cells[["pr_auc", "f2"]], "B": res_b.cells[["pr_auc", "f2"]]}, axis=1)
    cells.columns = [f"{m}_{k}" for m, k in cells.columns]
    cells["delta_pr_auc"] = cells["B_pr_auc"] - cells["A_pr_auc"]
    cells["delta_f2"] = cells["B_f2"] - cells["A_f2"]
    rule = mcfg["decision_rule"]
    gain = {"pr_auc": res_b.pooled["pr_auc"] - res_a.pooled["pr_auc"], "f2": res_b.pooled["f2"] - res_a.pooled["f2"]}
    gain_macro = {"pr_auc": res_b.macro["pr_auc"] - res_a.macro["pr_auc"], "f2": res_b.macro["f2"] - res_a.macro["f2"]}
    adopted = gain["pr_auc"] >= rule["min_gain_pr_auc"] and gain["f2"] >= rule["min_gain_f2"]
    verdict = "B passes on validation; adopt only if it also passes on test" if adopted else "ship A"

    # Outputs -------------------------------------------------------------------------------
    exp_dir = config.EXPERIMENTS / run_id
    write_csv(corr, OUT / "corrections.csv", index=False)
    write_parquet(b, OUT / "features_b.parquet")
    write_json(prop_rows, OUT / "b2_features.json")
    model_dir = OUT / "model_b"
    model_dir.mkdir(parents=True, exist_ok=True)
    tmp = model_dir / ".model.joblib.tmp"
    joblib.dump(res_b.model, tmp)
    tmp.replace(model_dir / "model.joblib")
    write_json({"features": features_b, "params": params, "threshold": res_b.threshold, "calibration": cal_b,
                "data_hash": b_data.data_hash, "joblib_sha256": sha256_of(model_dir / "model.joblib")},
               model_dir / "bundle_meta.json")
    write_json({"run_id": run_id, "adopted_on_validation": adopted, "rule": rule, "gain_validation_pooled": gain,
                "A": {"model_version": rule["reference_model_version"], "threshold": res_a.threshold, "calibration": cal_a},
                "B": {"model_path": "data/processed/muse/model_b/model.joblib", "features_table": "data/processed/muse/features_b.parquet",
                      "features": features_b, "threshold": res_b.threshold, "calibration": cal_b,
                      "validation_pooled": res_b.pooled}},
               OUT / "muse_candidates.json")
    for tag, res, data in (("A", res_a, a_data), ("B", res_b, b_data)):
        preds = pd.DataFrame({"point_id": data.val["point_id"], "night_date": data.val["night_date"].dt.date,
                              "frost": data.val["frost"].astype(int), "score": res.score_val,
                              "predicted": (res.score_val >= res.threshold).astype(int)})
        write_csv(preds, PRED_DIR / f"{run_id}-{tag}.csv", index=False)

    decision_counts = corr["decision"].value_counts().to_dict()
    run_stats = {"mode": "mock" if client.mock else "real", "api_calls": client.stats.api_calls,
                 "cache_hits": client.stats.cache_hits, "mock_calls": client.stats.mock_calls, "failed": client.stats.failed,
                 "prompt_tokens": client.stats.prompt_tokens, "completion_tokens": client.stats.completion_tokens,
                 "est_cost_usd": round(client.stats.est_cost_usd, 6)}
    usage_after = costs.summarize(costs.read_usage(client.usage_log))
    cfg_out = {"run_id": run_id, "conditions": {"A": f"{ref_id} recomputed", "B": "A + B1 corrections + B2 features"},
               "seed": seed, "muse": {k: mcfg[k] for k in ("model", "temperature", "max_tokens")},
               "prompt_versions": {"anomaly_review": pv_review, "feature_proposals": pv_prop},
               "anomaly_review": rcfg, "feature_proposals": {k: v for k, v in pcfg.items() if k != "meanings"},
               "decision_rule": rule, "model_params": params, "features_a": feats, "features_b": features_b,
               "data_hash_a": a_hash, "data_hash_b": b_data.data_hash,
               "features_manifest_sha256": a_data.features_manifest_sha256, "split_definition": a_data.split_cfg,
               "selection": "fit on train, threshold on validation; test locked", "reproduce": REPRODUCE}
    metrics = {"run_id": run_id, "muse_mode": run_stats["mode"], "seed": seed, "data_hash_a": a_hash,
               "data_hash_b": b_data.data_hash, "features_manifest_sha256": a_data.features_manifest_sha256,
               "package_versions": {**package_versions(), "python": platform.python_version()},
               "prompt_versions": {"anomaly_review": pv_review, "feature_proposals": pv_prop},
               "muse_calls_this_run": run_stats, "muse_usage_experiment_total": usage_after["total"],
               "estimate": est, "b1_funnel": plan["funnel"], "b1_decisions": decision_counts,
               "b1_feature_changes_from_clipping": diff_clip, "b1_feature_changes_from_muse": diff_muse,
               "b2_candidates": prop_rows, "b2_schema_errors": prop_errors, "b2_call_status": pres.status,
               "a_recheck": {"reference_run": ref_id, "max_abs_diff": max(a_diff.values()), "confirmed": a_confirmed,
                             "per_metric_abs_diff": a_diff},
               "validation_pooled": {"A": res_a.pooled, "B": res_b.pooled, **{k: r.pooled for k, r in refs.items()}},
               "validation_macro_over_cells": {"A": res_a.macro, "B": res_b.macro, **{k: r.macro for k, r in refs.items()}},
               "validation_per_cell": {"A": res_a.cells.reset_index().to_dict(orient="records"),
                                       "B": res_b.cells.reset_index().to_dict(orient="records")},
               "calibration": {"A": cal_a, "B": cal_b},
               "gain_b_minus_a_pooled": gain, "gain_b_minus_a_macro": gain_macro,
               "adopted_on_validation": adopted, "verdict": verdict, "test_set": "locked, not evaluated",
               "reproduce": REPRODUCE}
    write_text(yaml.safe_dump(runner._plain(cfg_out), sort_keys=False), exp_dir / "config.yaml")
    write_json(runner._plain(metrics), exp_dir / "metrics.json")
    write_text(sys_prop + "\n\n--- user message (JSON) ---\n" + json.dumps(prop_payload, indent=1), exp_dir / "b2_prompt.txt")
    write_json({"status": pres.status, "source": pres.source, "content": pres.content, "usage": pres.usage}, exp_dir / "b2_raw_response.json")
    write_json({"candidates": prop_rows, "schema_errors": prop_errors}, exp_dir / "b2_parsed.json")
    write_json({"funnel": plan["funnel"], "calls": call_log, "decisions": decision_counts}, exp_dir / "b1_summary.json")

    skill_p, skill_m = skill(pooled), skill(macro_t)
    write_report(run_id, run_stats, usage_after, est, plan["funnel"], decision_counts, corr, diff_clip, diff_muse,
                 prop_rows, prop_errors, pres.status, a_confirmed, a_diff, pooled, macro_t, cells, skill_p, skill_m,
                 gain, gain_macro, adopted, verdict, cal_a, cal_b, rule)
    write_usage_doc(client.usage_log)
    if not client.mock:
        write_sample_calls(client, [c["cache_key"] for c in call_log][:4] + [pres.cache_key])
    url = None
    if log_mlflow and not client.mock:
        flat = {f"val_{m}_{k}": float(v) for m, r in (("A", res_a), ("B", res_b)) for k, v in r.pooled.items()
                if isinstance(v, float)}
        flat.update({"gain_pr_auc": gain["pr_auc"], "gain_f2": gain["f2"], "muse_cost_usd": usage_after["total"]["est_cost_usd"]})
        url = mlflow_logger.log_run(run_id, {"seed": seed, "C": params["C"], "penalty": params["penalty"],
                                             "class_weight": params["class_weight"], "n_features_b": len(features_b),
                                             "prompt_review": pv_review, "prompt_proposals": pv_prop}, flat,
                                    {"data_hash": a_hash, "data_hash_b": b_data.data_hash, "verdict": verdict,
                                     "test_set": "locked, not evaluated", "git_head": mlflow_logger.git_head()},
                                    [exp_dir / "config.yaml", exp_dir / "metrics.json"])
    return {"run_id": run_id, "estimate": est, "run_stats": run_stats, "decisions": decision_counts,
            "diff_muse": diff_muse, "diff_clip": diff_clip, "b2": prop_rows, "pooled": pooled, "gain": gain,
            "adopted": adopted, "verdict": verdict, "a_confirmed": a_confirmed, "mlflow_url": url,
            "usage_after": usage_after["total"]}


# Docs -----------------------------------------------------------------------------------------

def _fmt(x, nd=4) -> str:
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def write_report(run_id, run_stats, usage, est, funnel, decision_counts, corr, diff_clip, diff_muse, prop_rows, prop_errors,
                 prop_status, a_confirmed, a_diff, pooled, macro_t, cells, skill_p, skill_m, gain, gain_macro, adopted,
                 verdict, cal_a, cal_b, rule) -> None:
    mock = run_stats["mode"] == "mock"
    applied = corr[corr["decision"] == "applied"]
    ab = pooled.loc[["A", "B"], ["pr_auc", "f2"]]
    clip_lines = [f"- {k}: {v} hourly values clipped to 0" for k, v in funnel["clipped_values_in_code"].items()]
    feat_rows = pd.DataFrame([{k: r.get(k) for k in ("candidate", "muse_name", "formula", "category", "decision", "column")}
                              for r in prop_rows]).set_index("candidate") if prop_rows else pd.DataFrame()
    def _changes(d):
        if not d["per_feature"]:
            return "No feature value changed."
        t = pd.DataFrame.from_dict(d["per_feature"], orient="index")
        t.index.name = "feature"
        return (f"{d['values_changed']} feature values in {d['rows_changed']} rows changed "
                f"(rows by split: {d['rows_changed_by_split']}).\n\n" + reports.md_table(t, 6))
    lines = [
        "# Muse experiment: condition A vs condition B (validation only; test pending)",
        "",
        f"Generated by `pipelines/05_muse_correct.py` (run `{run_id}`). " + (
            "**MOCK RUN: Muse answers are deterministic fakes (MUSE_MOCK=1). These numbers are not the experiment result.**"
            if mock else "Muse answers come from real `muse-spark-1.3` calls (cached in `logs/muse_cache/`)."),
        "",
        "Data: ERA5-Land reanalysis from the Copernicus CDS (not raw satellite imagery). Labels come from the same "
        "reanalysis, so both conditions are scored against reanalysis frost, not station observations.",
        "",
        "## What was sent to Muse",
        "",
        "B1, anomaly review (corrections):",
        f"- The EDA anomaly list has {funnel['anomalies_total']} flags. {funnel['affect_a_feature']} of them fall on an "
        "hour that a feature reads (at or before 18:00 local of the night that uses it).",
        "- Tiny negative de-accumulation values in precipitation and shortwave radiation are a known ERA5 artifact. They were "
        "clipped to 0 in code and never sent:",
        *clip_lines,
        f"- {funnel['in_scope_for_review']} remaining flagged hours can change a feature in the train and validation years "
        "(test-year flags are never sent). All are hourly jumps; there are no stuck values and no dew point above temperature.",
        f"- Sample: {funnel['sampled']} records (cap {cfg_cap()}; stratified by field and rule, seed 42), "
        f"{funnel['batches']} calls of up to 20 records.",
        "- Each record: an opaque id, the field, unit, flag, the flagged value and the hourly values of the same variable plus "
        "t2m and d2m at relative offsets h-3 to h+3, cut at the 18:00 local snapshot of the night that uses the value. "
        "No dates, years, hours of day, cell names, coordinates, elevation, labels or frost flags.",
        "",
        "B2, feature proposals (one call): the allowlisted feature names (without latitude and elevation, which identify "
        "cells), their units, a one-line meaning and train-only mean, std, p5 and p95. No rows, labels, dates or places. "
        "The statistics of `prev_night_frost` imply the training frost rate of the previous night; no per-row label is sent.",
        "",
        "## What came back",
        "",
        "B1 decisions (a correction is applied only if action is correct, confidence >= 0.8 and the value passes the "
        "physical checks in code: range, dew point <= temperature, no larger hourly jump than the original):",
        "",
        reports.md_table(pd.Series(decision_counts, name="records").to_frame().rename_axis("decision"), 0),
        "",
        f"Corrections applied: {len(applied)}. Full log: `data/processed/muse/corrections.csv` (DVC).",
        "",
        "Feature values changed by the clipping (all rows, all splits):",
        "",
        _changes(diff_clip),
        "",
        "Feature values changed by the applied Muse corrections:",
        "",
        _changes(diff_muse),
        "",
        f"B2 response status: {prop_status}. Schema problems: {prop_errors or 'none'}.",
        "",
        (reports.md_table(feat_rows, 4) if len(feat_rows) else "No candidate features."),
        "",
        "Rationales:",
        "",
        *[f"- {r['muse_name']}: {r['rationale']}" for r in prop_rows],
        "",
        "## A vs B on validation (2010-2017)",
        "",
        f"A is LR_best (`{rule['reference_run']}`: C=1, L1, no class weight), recomputed with the same code: "
        + ("matches the stored validation metrics exactly" if a_confirmed else f"DOES NOT match the stored metrics (max abs diff {max(a_diff.values()):.2e})")
        + f". B uses the same hyperparameters, preprocessing, calibration rule and F2 threshold rule. Calibration kept: A {cal_a is not None}, B {cal_b is not None}.",
        "",
        "Decision metrics (pooled):",
        "",
        reports.md_table(ab, 4),
        "",
        f"Gain B minus A, pooled: PR-AUC {gain['pr_auc']:+.4f}, F2 {gain['f2']:+.4f}. Macro over cells: PR-AUC {gain_macro['pr_auc']:+.4f}, F2 {gain_macro['f2']:+.4f}.",
        "",
        "All metrics, pooled (accuracy next to majority-class accuracy):",
        "",
        reports.md_table(pooled, 4),
        "",
        "Macro-average over the 8 cells:",
        "",
        reports.md_table(macro_t, 4),
        "",
        "Per cell (each model at its own single validation threshold):",
        "",
        reports.md_table(cells, 4),
        "",
        "Skill versus the best baseline (climatology or persistence), pooled:",
        "",
        reports.md_table(skill_p, 4),
        "",
        "Macro:",
        "",
        reports.md_table(skill_m, 4),
        "",
        "## Verdict",
        "",
        f"Pre-declared rule: adopt B only if PR-AUC AND F2 (pooled) both improve by at least {rule['min_gain_pr_auc']} over A on "
        "validation, and later on test.",
        "",
        f"**{verdict.upper() if not adopted else verdict}**" + ("" if adopted else ": B does not pass on validation, so the raw-feature model A ships. This is a valid result."),
        "",
        "No confidence intervals are computed; small differences in either direction may be noise.",
        "",
        "## Limitations",
        "",
        "- Labels come from the same ERA5-Land reanalysis as the features, not from stations.",
        "- There is little real anomaly material: tiny negative de-accumulation values and hourly jumps, mostly in dew point and "
        "temperature during morning warming. There are no stuck values and no dew point above temperature. B1 can only change "
        "a small number of feature values.",
        "- B bundles B1 and B2, so this experiment cannot say which part helped or hurt.",
        "- Rows outside the sample are unchanged by Muse (only clipped). Test-year flags were not reviewed, so on test B differs "
        "from A only by clipping and the B2 features.",
        "- Labels are never edited: a corrected morning temperature changes the previous-night feature of the next night but "
        "not the label of the night it belongs to.",
        "- Muse-generated per-row columns (`daily_summary`, `frost_likelihood`) are NOT part of B: they would require sending "
        "every row of the history, which the project rules forbid. Future work: a capped, masked sample with a separate "
        "condition and its own budget.",
        "- Prices used for cost are configured in `configs/muse.yaml` and marked verify. Token counts come from the API usage field.",
        "",
        "## Cost",
        "",
        f"This run: {run_stats['api_calls']} API calls, {run_stats['cache_hits']} cache hits, {run_stats['mock_calls']} mock calls, "
        f"{run_stats['failed']} failed. Experiment total so far (real calls in `logs/muse_usage.jsonl`): {usage['total']['calls']} calls, "
        f"{usage['total']['prompt_tokens']} input and {usage['total']['completion_tokens']} output tokens, "
        f"{usage['total']['est_cost_usd']:.4f} USD estimated. Planning estimate for the full run: {est['calls']} calls, "
        f"about {est['input_tokens_est']} input tokens, worst case {est['cost_worst_case_usd']} USD. See `docs/muse_usage.md`.",
        "",
        f"Reproduce: `{REPRODUCE}` (re-runs read from the cache).",
        "",
    ]
    write_text("\n".join(lines), REPORT)


def cfg_cap() -> int:
    return int(config.load_yaml("configs/muse.yaml")["anomaly_review"]["sample_cap"])


def write_usage_doc(usage_log) -> None:
    entries = costs.read_usage(usage_log)
    s = costs.summarize(entries)
    by = pd.DataFrame(s["by_purpose"]).T if s["by_purpose"] else pd.DataFrame()
    if len(by):
        by.index.name = "purpose"
    calls = pd.DataFrame([{k: e.get(k) for k in ("ts", "purpose", "status", "prompt_tokens", "completion_tokens",
                                                   "est_cost_usd", "error")} for e in entries])
    if len(calls):
        calls.index = range(1, len(calls) + 1)
        calls.index.name = "call"
    lines = ["# Muse usage (Meta Model API, muse-spark-1.3)", "",
             "Generated from `logs/muse_usage.jsonl` (gitignored) by `pipelines/05_muse_correct.py`. Only real API calls are "
             "logged; cache hits and mock calls cost nothing and are not listed. Cost is estimated from the API token counts "
             "and the prices in `configs/muse.yaml` (marked verify).", "",
             f"Total: {s['total']['calls']} calls, {s['total']['prompt_tokens']} input tokens, "
             f"{s['total']['completion_tokens']} output tokens, {s['total']['est_cost_usd']:.4f} USD estimated "
             "(experiment cap 25 USD).", "",
             "## By purpose", "", reports.md_table(by, 4) if len(by) else "No calls yet.", "",
             "## Calls", "", reports.md_table(calls, 6) if len(calls) else "No calls yet.", ""]
    write_text("\n".join(lines), USAGE_DOC)


def write_sample_calls(client: MuseClient, keys: list[str]) -> None:
    """At most 5 real calls (masked request and response), for the public repo."""
    out = []
    for k in keys[:5]:
        p = client.cache_dir / f"{k}.json"
        if not p.exists():
            continue
        e = json.loads(p.read_text())
        out.append({"purpose": e["purpose"], "prompt_version": e["prompt_version"], "model": e["request"]["model"],
                    "temperature": e["request"]["temperature"], "messages": e["request"]["messages"],
                    "response_content": e["content"], "usage": e["usage"], "status": e["status"]})
    write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in out), SAMPLE_CALLS)
