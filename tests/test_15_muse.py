"""15. Muse experiment guards: masking (no date, year, place or label leaves the process), the formula
parser rejects unknown names and code, MUSE_MOCK=1 makes zero network calls, cache hit on re-run,
B uses only train-fitted statistics, the test split is never loaded, and the feature window used to
select anomalies matches the feature code."""

import json
import urllib.request

import numpy as np
import pandas as pd
import pytest

from frostwatch_ml import config, leakage
from frostwatch_ml.features.snapshot import previous_night, snapshot_features
from frostwatch_ml.models.logistic import make_lr
from frostwatch_ml.muse import client as mclient
from frostwatch_ml.muse import experiment, formula, masking, proposals, review, schema

MCFG = config.load_yaml("configs/muse.yaml")
RECORD_KEYS = {"id", "field", "name", "unit", "flag", "value", "context"}


@pytest.fixture(scope="module")
def plan():
    convs, _ = experiment.load_hourly()
    return experiment.plan_b1(MCFG, config.SEED, config.frost_config(), convs)


# Masking ---------------------------------------------------------------------------------------

def test_review_records_are_masked(plan):
    text = json.dumps(plan["records"])
    masking.assert_masked({"records": plan["records"]})
    for pid in config.point_ids():
        assert pid not in text
    for rec, (_, row) in zip(plan["records"], plan["sample"].iterrows(), strict=True):
        assert set(rec) == RECORD_KEYS
        assert rec["id"].startswith("r") and len(rec["id"]) == 11
        max_after = int((row["cutoff_utc"] - row["timestamp_utc"]) / pd.Timedelta(hours=1))
        for series in rec["context"].values():
            for k in series:
                off = 0 if k == "h0" else int(k[1:])
                assert off <= max_after, "a value after 18:00 local of the night was sent"


def test_sample_has_only_model_split_flags(plan):
    assert set(plan["sample"]["night_split"]) <= {"train", "validation"}
    assert len(plan["sample"]) <= MCFG["anomaly_review"]["sample_cap"]
    assert all(len(b) <= MCFG["anomaly_review"]["batch_size"] for b in plan["batches"])


def test_masking_rejects_dates_years_places_labels():
    ok = {"records": [{"id": "r1", "value": 1.5}]}
    masking.assert_masked(ok)
    for bad in ({"records": [{"id": "r1", "note": "2014-07-03"}]},
                {"records": [{"id": "r1", "note": "season 1997"}]},
                {"records": [{"id": "r1", "note": "near " + config.point_ids()[0].replace("_", " ")}]},
                {"records": [{"id": "r1", "frost": 1}]},
                {"records": [{"id": "r1", "latitude": -17.0}]},
                {"records": [{"id": "r1", "night_date": "x"}]}):
        with pytest.raises(masking.MaskingError):
            masking.assert_masked(bad)


def test_feature_proposal_payload_is_masked(features):
    names = proposals.usable_names(leakage.feature_list(), MCFG["feature_proposals"])
    assert "latitude" not in names and "elevation_proxy_m" not in names
    payload = proposals.summary_payload(leakage.model_rows(features, "train"), names, MCFG["feature_proposals"])
    masking.assert_masked(payload)
    assert {tuple(sorted(f)) for f in payload["features"]} == {("mean", "meaning", "name", "p5", "p95", "std", "unit")}


# Formula parser --------------------------------------------------------------------------------

def test_formula_parser_computes_allowed_grammar():
    df = pd.DataFrame({"a": [1.0, 4.0], "b": [2.0, -3.0]})
    tree = formula.parse("max(a, b) / (1 + abs(b)) - sqrt(a) + log1p(min(a, 0.5)) * -2", {"a", "b"})
    expected = np.maximum(df.a, df.b) / (1 + np.abs(df.b)) - np.sqrt(df.a) + np.log1p(np.minimum(df.a, 0.5)) * -2
    np.testing.assert_allclose(formula.evaluate(tree, df), expected)
    assert formula.names_used(tree) == {"a", "b"}


@pytest.mark.parametrize("bad", [
    "c + 1", "__import__('os').system('true')", "a.real", "a[0]", "a ** 2", "(lambda: 1)()", "'x'",
    "max(a, b, key=a)", "a > b", "sqrt(a, b)", "exp(a)", "a if b else 1", "open('x')", "", "[a]", "True + a",
])
def test_formula_parser_rejects_unknown_names_and_code(bad):
    with pytest.raises(formula.FormulaError):
        formula.parse(bad, {"a", "b"})


def test_feature_acceptance_rejects_bad_candidates():
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [0.0, 1.0, 2.0], "split": ["train", "train", "validation"]})
    cands = [{"name": "ok", "formula": "a * b", "category": "wind", "rationale": ""},
             {"name": "div0", "formula": "a / b", "category": "wind", "rationale": ""},
             {"name": "unknown", "formula": "z + 1", "category": "wind", "rationale": ""},
             {"name": "dup", "formula": "a + 0", "category": "wind", "rationale": ""},
             {"name": "same", "formula": "b * a", "category": "wind", "rationale": ""}]
    cols, rows = proposals.accept(cands, df, (df["split"] == "train").to_numpy(), ["a", "b"], ["a", "b"])
    assert list(cols) == ["muse_f1"]
    assert [r["decision"].split(":")[0] for r in rows] == ["accepted", "rejected", "rejected", "rejected", "rejected"]


# Client: mock, cache, budget -------------------------------------------------------------------

def _no_network(*a, **k):
    raise AssertionError("network call attempted")


def test_mock_makes_zero_network_calls(tmp_path, monkeypatch):
    monkeypatch.setenv("MUSE_MOCK", "1")
    monkeypatch.setattr(urllib.request, "urlopen", _no_network)
    c = mclient.MuseClient(MCFG, cache_dir=tmp_path / "cache", usage_log=tmp_path / "usage.jsonl", transport=_no_network)
    assert c.mock
    payload = {"records": [{"id": "r1", "field": "t2m", "value": 1.0, "context": {"t2m": {"h-1": 0.0, "h+1": 2.0}}}]}
    res = c.call("anomaly_review", "v1", "system", payload, review.mock_review)
    assert res.status == "ok" and res.source == "mock"
    items, errors = schema.validate_review(res.parsed, ["r1"])
    assert set(items) == {"r1"} and not errors
    assert not (tmp_path / "usage.jsonl").exists()
    assert c.call("anomaly_review", "v1", "system", payload, review.mock_review).source == "mock_cache"


def test_cache_hit_on_rerun_and_usage_log(tmp_path, monkeypatch):
    monkeypatch.setenv("META_API_KEY", "fake-key-for-test")
    monkeypatch.setenv("META_API_BASE_URL", "https://example.invalid/v1")
    calls = []

    def transport(url, headers, body, timeout):
        calls.append(url)
        return {"choices": [{"message": {"content": json.dumps({"features": []})}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 10}}

    def make():
        return mclient.MuseClient(MCFG, mock=False, cache_dir=tmp_path / "cache", usage_log=tmp_path / "u.jsonl",
                                  transport=transport)
    first = make().call("feature_proposals", "v1", "system", {"features": []}, proposals.mock_proposals)
    second_client = make()
    second = second_client.call("feature_proposals", "v1", "system", {"features": []}, proposals.mock_proposals)
    assert first.source == "api" and second.source == "cache" and second.parsed == {"features": []}
    assert len(calls) == 1 and second_client.stats.api_calls == 0 and second_client.stats.cache_hits == 1
    log = (tmp_path / "u.jsonl").read_text().splitlines()
    assert len(log) == 1 and "fake-key-for-test" not in log[0]
    assert "fake-key-for-test" not in "".join(p.read_text() for p in (tmp_path / "cache").glob("*.json"))


def test_budget_cap_stops_before_the_call(tmp_path, monkeypatch):
    monkeypatch.setenv("META_API_KEY", "x")
    monkeypatch.setenv("META_API_BASE_URL", "https://example.invalid/v1")
    cfg = {**MCFG, "budget": {**MCFG["budget"], "experiment_cap_usd": 1e-9}}
    c = mclient.MuseClient(cfg, mock=False, cache_dir=tmp_path, usage_log=tmp_path / "u.jsonl", transport=_no_network)
    with pytest.raises(mclient.BudgetExceeded):
        c.call("feature_proposals", "v1", "system", {"features": []}, proposals.mock_proposals)


def test_failed_call_is_logged_and_not_retried(tmp_path, monkeypatch):
    monkeypatch.setenv("META_API_KEY", "x")
    monkeypatch.setenv("META_API_BASE_URL", "https://example.invalid/v1")
    n = []

    def boom(*a):
        n.append(1)
        raise TimeoutError

    c = mclient.MuseClient(MCFG, mock=False, cache_dir=tmp_path, usage_log=tmp_path / "u.jsonl", transport=boom)
    res = c.call("feature_proposals", "v1", "system", {"features": []}, proposals.mock_proposals)
    assert res.status == "failed" and len(n) == 1
    assert json.loads((tmp_path / "u.jsonl").read_text())["status"] == "failed"


# Corrections -----------------------------------------------------------------------------------

def _conv():
    idx = pd.date_range("2000-01-01", periods=6, freq="h")
    return pd.DataFrame({"t2m_c": [5.0, 5.0, 5.0, 20.0, 5.0, 5.0], "d2m_c": [-5.0] * 6,
                         "t2m_k": np.array([5.0, 5.0, 5.0, 20.0, 5.0, 5.0]) + 273.15}, index=idx)


def test_corrections_pass_physical_checks_only():
    conv = _conv()
    row = pd.Series({"field": "t2m_c", "timestamp_utc": conv.index[3], "cutoff_utc": conv.index[5]})
    cfg = MCFG["anomaly_review"]

    def item(v, c=0.9, a="correct"):
        return {"action": a, "value": v, "confidence": c, "reason": ""}
    assert review.decide(row, item(5.0), conv, cfg) == ("applied", 5.0)
    assert review.decide(row, item(5.0, c=0.5), conv, cfg)[0] == "rejected_low_confidence"
    assert review.decide(row, item(-6.0), conv, cfg)[0] == "rejected_dewpoint"
    assert review.decide(row, item(99.0), conv, cfg)[0] == "rejected_range"
    assert review.decide(row, item(36.0), conv, cfg)[0] == "rejected_jump"
    assert review.decide(row, item(20.0, a="keep"), conv, cfg)[0] == "kept"
    assert review.decide(row, None, conv, cfg)[0] == "invalid_response"
    out = review.apply_corrections(conv, pd.DataFrame({"timestamp_utc": [conv.index[3]], "field": ["t2m_c"], "new_value": [5.0]}))
    assert out["t2m_c"].iloc[3] == 5.0 and out["t2m_k"].iloc[3] == pytest.approx(278.15)
    assert conv["t2m_c"].iloc[3] == 20.0


def test_clip_only_tiny_negatives():
    conv = pd.DataFrame({"tp_mm": [-0.00005, -0.5, 0.2], "ssrd_wm2": [-0.001, 3.0, 0.0]})
    out, n = review.clip_tiny_negatives(conv, MCFG["anomaly_review"]["clip_tiny_negatives"])
    assert out["tp_mm"].tolist() == [0.0, -0.5, 0.2] and out["ssrd_wm2"].tolist() == [0.0, 3.0, 0.0]
    assert n == {"tp_mm": 1, "ssrd_wm2": 1}


@pytest.mark.parametrize("field", ["t2m_c", "d2m_c", "skt_c"])
def test_feature_hours_match_the_feature_code(field, frost_cfg):
    idx = pd.date_range("2000-01-01", periods=24 * 6, freq="h")
    rng = np.random.default_rng(0)
    conv = pd.DataFrame({c: rng.normal(5, 1, len(idx)) for c in
                         ("t2m_c", "d2m_c", "wind_ms", "ssrd_wm2", "strd_wm2", "skt_c", "stl1_c", "tp_mm")}, index=idx)
    conv["d2m_c"] -= 10
    conv["sp_hpa"] = 640.0
    conv["strd_wm2"] += 300
    conv["t2m_k"] = conv["t2m_c"] + 273.15
    days = pd.date_range("2000-01-03", periods=3, freq="D")

    def feats(c):
        return pd.concat([snapshot_features(c, days, frost_cfg), previous_night(c, days, frost_cfg)], axis=1)
    base = feats(conv)
    hours = review.feature_hours(field, frost_cfg)
    for h in range(24):
        ts = days[1] + pd.Timedelta(hours=h)
        alt = conv.copy()
        alt.loc[ts, field] -= 50
        if field == "t2m_c":
            alt.loc[ts, "t2m_k"] -= 50
        changed = not feats(alt).equals(base)
        assert changed == (h in hours), (field, h)


# Train-only statistics and the locked test split ----------------------------------------------

def _b_like(features):
    b = features.copy()
    b["muse_f1"] = formula.evaluate(formula.parse("dewpoint_depression_1800_c * (1 - sky_emissivity_1800)",
                                                  set(leakage.feature_list())), b)
    return b, leakage.feature_list() + ["muse_f1"]


def test_b_uses_only_train_fitted_statistics(features):
    b, feats_b = _b_like(features)
    alt = b.copy()
    other = alt["split"] != "train"
    rng = np.random.default_rng(config.SEED)
    for c in feats_b:
        alt.loc[other, c] = rng.normal(0, 1000, other.sum()).astype(alt[c].dtype) if alt[c].dtype.kind == "f" else alt.loc[other, c]
    tr1, tr2 = leakage.model_rows(b, "train"), leakage.model_rows(alt, "train")
    m1 = make_lr(feats_b, C=1.0, penalty="l1").fit(tr1, tr1["frost"].to_numpy(int))
    m2 = make_lr(feats_b, C=1.0, penalty="l1").fit(tr2, tr2["frost"].to_numpy(int))
    s1, s2 = m1.estimator.named_steps["scaler"], m2.estimator.named_steps["scaler"]
    np.testing.assert_array_equal(s1.mean_, s2.mean_)
    np.testing.assert_array_equal(s1.scale_, s2.scale_)
    np.testing.assert_allclose(s1.mean_, tr1[feats_b].to_numpy(float).mean(axis=0), rtol=1e-6)


def test_b_model_data_never_holds_locked_rows(features, monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("load_test_split called")
    monkeypatch.setattr(leakage, "load_test_split", refuse)
    b, feats_b = _b_like(features)
    data = experiment.model_data_b(b, feats_b, experiment.runner.load_model_data())
    assert set(data.train["split"]) == {"train"} and set(data.val["split"]) == {"validation"}
    years = set(data.train["night_date"].dt.year) | set(data.val["night_date"].dt.year)
    lo, hi = config.frost_config()["split"]["validation"]
    assert max(years) <= hi


def test_stratified_sample_is_capped_balanced_and_seeded():
    df = pd.DataFrame({"field": ["a"] * 50 + ["b"] * 5 + ["c"] * 30, "rule": "r", "x": range(85)})
    s1 = review.stratified_sample(df, 20, 42)
    assert len(s1) == 20 and s1["field"].value_counts().to_dict() == {"a": 8, "b": 5, "c": 7} or \
        s1["field"].value_counts().to_dict() == {"a": 7, "b": 5, "c": 8}
    assert s1.equals(review.stratified_sample(df, 20, 42))
    assert len(review.stratified_sample(df, 300, 42)) == 85
