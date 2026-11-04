# Muse Experiment: can Muse Spark improve the frost dataset?

Validation results only (2010-2017). The test set (2018-2025) is locked and has not been evaluated.

Data: ERA5-Land and AgERA5 reanalysis from the Copernicus Climate Data Store (CDS). Reanalysis combines a weather model with assimilated observations, including satellite data. It is not raw satellite imagery. The frost labels come from the same reanalysis, so every metric below measures agreement with reanalysis frost on a 0.1 degree grid, not with weather stations.

Run: `muse-ab-fbbf62c6`, mirrored to MLflow on DagsHub (experiment "frostwatch-altiplano"). The generated technical report is `reports/muse_experiment.md`. Call-level usage is in `docs/muse_usage.md`.

## 1. What the experiment asks

FrostWatch predicts, at 18:00 local time, whether the coming night will have frost (minimum 2 m air temperature at or below 0 C between 18:00 and 09:00 local) for 8 ERA5-Land cells between La Paz and Oruro. The production model is a logistic regression (LR_best).

The question: if Meta's Muse Spark (`muse-spark-1.3`, Meta Model API) acts as a data analyst on our dataset, does the same logistic regression get better?

Two conditions only, on the same rows and the same chronological split:

| condition | data | model |
|---|---|---|
| A | raw features (24 allowlisted columns) | LR_best: C=1, L1 penalty, no class weight, sigmoid calibration kept only if it lowers the validation Brier score, threshold that maximizes F2 on validation |
| B | A plus Muse contributions: B1 corrections of flagged values and B2 new feature combinations | the same model, hyperparameters, preprocessing, calibration rule and threshold rule |

Decision rule, declared before running: adopt B only if PR-AUC and F2 both improve by at least 0.02 over A on validation, and later again on test. Otherwise ship A. A negative result is a valid result.

## 2. How Muse was used

### B1: anomaly review (corrections)

1. Our own EDA (not Muse) produced a list of 43,160 flagged hourly values with exact positions (cell, timestamp, field, rule).
2. Only flags that can change a model feature were kept: values at hours that a feature reads, at or before 18:00 local of the night that uses them. Anything later, or used only by the label, is out of scope.
3. Tiny negative de-accumulation values (about -0.001) in precipitation and shortwave radiation are a known ERA5 artifact. They were clipped to 0 in code and never sent to Muse: 38,321 precipitation hours and 802 shortwave hours.
4. What remained: 277 hourly jumps (188 in air temperature, 89 in dew point) in the train and validation years. Test-year flags were never sent. All 277 were reviewed (the sample cap was 300), in 14 calls of up to 20 records.
5. Each record carried an opaque id, the field and unit, the screening rule, the flagged value and the hourly values of the same variable plus air temperature and dew point at relative offsets h-3 to h+3, cut at 18:00 local. No dates, years, hours of day, cell names, coordinates, elevation, labels or frost flags. A masking check runs on every payload before it is sent.
6. Muse answered in strict JSON per record: keep or correct, value, confidence, reason. A correction would be applied only with confidence >= 0.8 and if it passed physical checks in code (range, dew point not above temperature, no larger hourly jump than the original). The night table is then rebuilt with the same feature code used for A.

### B2: feature proposals (Muse proposes, code computes)

One call. Muse received only feature names, units, one-line meanings and training-period statistics (mean, std, 5th and 95th percentiles). No rows, labels, dates or places. Latitude and elevation were excluded because they identify cells. It could propose up to 6 formulas in a restricted grammar (+ - * /, constants, min, max, abs, log1p, sqrt).

Our code parses each formula with a whitelist parser (no `eval`), rejects unknown names, NaN or inf values, constant columns and duplicates, and computes the accepted ones. Scaling statistics are fitted on training years only.

### Reproducibility and cost controls

- Temperature 0, pinned model id, versioned prompts in `prompts/`.
- Every call is cached by request hash in `logs/muse_cache/`. A re-run made 15 cache hits and 0 API calls, with identical results.
- `MUSE_MOCK=1` gives deterministic fake answers, so the pipeline and the tests run without spending.
- Hard budget stop before each real call (cap 10 USD for this experiment). One attempt per call, no retry loops.

## 3. Results

### What Muse returned

**B1:** Muse marked all 277 records as "keep" and proposed no corrections. Its reasons describe the jumps as real weather, for example a steady warming trend or a moist air mass arriving (Muse never sees the hour of day). This agrees with our EDA: the flags are mostly morning warming. So Muse changed 0 feature values. The only change in B1 came from the code clipping: 29,009 values of `precip_24h_mm`, each by at most about 0.0001 mm.

**B2:** Muse proposed 6 formulas, and all 6 passed the parser and the checks. B therefore has 30 features.

| feature | formula | category | Muse rationale |
|---|---|---|---|
| cooling_extrap_6h_c | t2m_1800_c + 6 * cooling_rate_1500_1800_c_per_h | radiative cooling | Extrapolates late-afternoon cooling six hours to approximate midnight temperature |
| soil_air_excess_c | stl1_1800_c - t2m_1800_c | radiative cooling | Warmer soil than air stores daytime heat that slows nighttime cooling |
| dry_clear_index | log1p(max(dewpoint_depression_1800_c, 0)) * afternoon_clearness | humidity deficit | Dry air with a clear afternoon amplifies nighttime heat loss |
| calm_dry_index | max(3 - wind_1800_ms, 0) * dewpoint_depression_1800_c | wind | Calm wind below 3 m/s limits mixing while dry air enhances cooling |
| clear_sky_persist | afternoon_clearness * max(1 - sky_emissivity_1800, 0) | cloud | Clear skies from afternoon to evening maximize longwave loss |
| lw_drop_afternoon_evening | strd_afternoon_mean_wm2 - strd_1800_wm2 | cloud | Falling longwave radiation signals clearing skies |

### A vs B on validation (2010-2017, 23,376 nights)

Recomputing A with the same code reproduced the stored LR_best validation metrics exactly. The sigmoid calibration was kept for A. For B it did not lower the validation Brier score, so B uses raw probabilities, as the shared rule says.

Pooled over all cells:

| model | PR-AUC | F2 | precision | recall | F1 | ROC-AUC | Brier | accuracy | majority-class accuracy |
|---|---|---|---|---|---|---|---|---|---|
| climatology (best baseline) | 0.8135 | 0.8470 | 0.5869 | 0.9525 | 0.7263 | 0.9078 | 0.1195 | 0.7593 | 0.6647 |
| persistence | 0.6573 | 0.7594 | 0.7593 | 0.7594 | 0.7594 | 0.8190 | 0.1614 | 0.8386 | 0.6647 |
| **A (LR_best)** | **0.8918** | **0.8757** | 0.6525 | 0.9576 | 0.7762 | 0.9426 | 0.0913 | 0.8148 | 0.6647 |
| **B (Muse)** | **0.8924** | **0.8769** | 0.6626 | 0.9541 | 0.7821 | 0.9435 | 0.0905 | 0.8217 | 0.6647 |

Macro-average over the 8 cells: A has PR-AUC 0.8374 and F2 0.8570. B has PR-AUC 0.8397 and F2 0.8580.

| | PR-AUC gain | F2 gain | required by the rule |
|---|---|---|---|
| pooled | +0.0006 | +0.0012 | +0.02 each |
| macro over cells | +0.0023 | +0.0010 | (reported only) |

Per cell, B minus A: PR-AUC moves between -0.0013 (Charana) and +0.0062 (El Alto). F2 moves between -0.0042 (Calamarca) and +0.0038 (Huanuni). Both A and B beat the best baseline (climatology) by about 0.08 in PR-AUC and 0.03 in F2.

## 4. Verdict

**Ship A.** B improves PR-AUC by 0.0006 and F2 by 0.0012 on validation, far below the pre-declared 0.02. B is not adopted. `pipelines/06_final_eval.py` will record B as "not adopted on validation" in its single test run.

No confidence intervals are computed. Differences this small are within what noise could produce.

## 5. Why the result looks like this

- There is very little real anomaly material in this data. There are no stuck values and no dew point above temperature. The flags are tiny de-accumulation negatives, which code fixes better than an LLM, and hourly jumps that are real morning weather. Muse correctly declined to "fix" real weather, which is the behavior we want from a data reviewer.
- The 6 proposed features are physically sensible, but they are combinations of columns the model already sees. A regularized logistic regression can already weight those columns, so the new combinations add little.

## 6. Limitations

- Labels come from the same ERA5-Land reanalysis as the features, not from stations.
- B bundles B1 and B2, so we cannot say which part helped. Here B1 changed nothing through Muse, so the small gain almost certainly comes from B2 and the clipping.
- Rows outside the sample are unchanged by Muse (only clipped). Test-year flags were not reviewed.
- Labels are never edited. A corrected value would change features only.
- Muse-generated per-row columns (`daily_summary`, `frost_likelihood`), described in the original plan, are not part of B. They would require sending every row of the history to Muse, which the project rules forbid. Future work: a capped, masked sample with its own condition and budget.
- Costs use configured prices of 1.25 USD per million input tokens and 4.25 USD per million output tokens. These prices still have to be verified.

## 7. Cost and calls

| | calls | input tokens | output tokens | estimated cost (USD) |
|---|---|---|---|---|
| smoke test (2 records) | 1 | 601 | 2,637 | 0.0120 |
| first attempt, max_tokens 4000 (all truncated, invalid JSON) | 15 | 50,162 | 60,000 | 0.3177 |
| final run, max_tokens 16000 (all valid) | 15 | 50,162 | 75,625 | 0.3841 |
| re-run from cache | 0 | 0 | 0 | 0 |
| **total** | **31** | **100,925** | **138,262** | **0.7138** |

Lesson learned: Muse Spark is a reasoning model, and its reasoning tokens count toward `max_tokens`. With 4000 tokens, every 20-record answer was cut before the JSON closed (finish reason "length"). For example, reasoning used 3,718 of the 4,000 tokens in one review call and 3,998 in the proposal call, which returned empty content. The limit is now 16,000, and the client logs reasoning tokens and the finish reason of every call.

## 8. Reproduce

```
.venv/bin/python pipelines/05_muse_correct.py --config configs/muse.yaml --dry-run   # plan and cost estimate, no calls
MUSE_MOCK=1 .venv/bin/python pipelines/05_muse_correct.py --no-sync                  # fake answers, no spending
MUSE_MOCK=0 .venv/bin/python pipelines/05_muse_correct.py --no-sync                  # real calls, or the cache if present
```

Real calls need `META_API_KEY` and `META_API_BASE_URL` in the environment. Code: `src/frostwatch_ml/muse/`. Tests: `tests/test_15_muse.py` cover masking, the formula parser, zero network calls with MUSE_MOCK=1, cache hits, the budget stop, physical checks, train-only statistics and the locked test split.
