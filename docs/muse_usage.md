# Muse usage (Meta Model API, muse-spark-1.3)

Generated from `logs/muse_usage.jsonl` (gitignored) by `pipelines/05_muse_correct.py`. Only real API calls are logged; cache hits and mock calls cost nothing and are not listed. Cost is estimated from the API token counts and the prices in `configs/muse.yaml` (marked verify).

Total: 31 calls, 100925 input tokens, 138262 output tokens, 0.7138 USD estimated (experiment cap 10.0 USD).

## By purpose

| purpose | calls | ok | failed | invalid_json | prompt_tokens | completion_tokens | est_cost_usd |
|---|---|---|---|---|---|---|---|
| smoke_anomaly_review | 1 | 1 | 0 | 0 | 601 | 2637 | 0.0120 |
| anomaly_review | 28 | 14 | 0 | 14 | 97134 | 126480 | 0.6590 |
| feature_proposals | 2 | 1 | 0 | 1 | 3190 | 9145 | 0.0429 |

## Calls

| call | ts | purpose | status | finish_reason | prompt_tokens | completion_tokens | reasoning_tokens | est_cost_usd | error |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-11-04T05:47:48Z | smoke_anomaly_review | ok |  | 601 | 2637 |  | 0.011959 | None |
| 2 | 2026-11-04T05:49:40Z | anomaly_review | invalid_json |  | 3471 | 4000 |  | 0.021339 | None |
| 3 | 2026-11-04T05:50:15Z | anomaly_review | invalid_json |  | 3481 | 4000 |  | 0.021351 | None |
| 4 | 2026-11-04T05:50:50Z | anomaly_review | invalid_json |  | 3624 | 4000 |  | 0.021530 | None |
| 5 | 2026-11-04T05:51:22Z | anomaly_review | invalid_json |  | 3473 | 4000 |  | 0.021341 | None |
| 6 | 2026-11-04T05:51:55Z | anomaly_review | invalid_json |  | 3429 | 4000 |  | 0.021286 | None |
| 7 | 2026-11-04T05:52:29Z | anomaly_review | invalid_json |  | 3470 | 4000 |  | 0.021337 | None |
| 8 | 2026-11-04T05:53:02Z | anomaly_review | invalid_json |  | 3535 | 4000 |  | 0.021419 | None |
| 9 | 2026-11-04T05:53:35Z | anomaly_review | invalid_json |  | 3570 | 4000 |  | 0.021462 | None |
| 10 | 2026-11-04T05:54:09Z | anomaly_review | invalid_json |  | 3708 | 4000 |  | 0.021635 | None |
| 11 | 2026-11-04T05:54:43Z | anomaly_review | invalid_json |  | 3523 | 4000 |  | 0.021404 | None |
| 12 | 2026-11-04T05:55:20Z | anomaly_review | invalid_json |  | 3290 | 4000 |  | 0.021112 | None |
| 13 | 2026-11-04T05:55:53Z | anomaly_review | invalid_json |  | 3516 | 4000 |  | 0.021395 | None |
| 14 | 2026-11-04T05:56:27Z | anomaly_review | invalid_json |  | 3426 | 4000 |  | 0.021282 | None |
| 15 | 2026-11-04T05:57:02Z | anomaly_review | invalid_json |  | 3051 | 4000 |  | 0.020814 | None |
| 16 | 2026-11-04T05:57:49Z | feature_proposals | invalid_json |  | 1595 | 4000 |  | 0.018994 | None |
| 17 | 2026-11-04T06:09:24Z | anomaly_review | ok | stop | 3471 | 4230 | 3240.000000 | 0.022316 | None |
| 18 | 2026-11-04T06:10:02Z | anomaly_review | ok | stop | 3481 | 4866 | 3831.000000 | 0.025032 | None |
| 19 | 2026-11-04T06:10:28Z | anomaly_review | ok | stop | 3624 | 3717 | 2715.000000 | 0.020327 | None |
| 20 | 2026-11-04T06:11:22Z | anomaly_review | ok | stop | 3473 | 6471 | 5448.000000 | 0.031843 | None |
| 21 | 2026-11-04T06:12:00Z | anomaly_review | ok | stop | 3429 | 4815 | 3784.000000 | 0.024750 | None |
| 22 | 2026-11-04T06:12:40Z | anomaly_review | ok | stop | 3470 | 5380 | 4349.000000 | 0.027203 | None |
| 23 | 2026-11-04T06:13:42Z | anomaly_review | ok | stop | 3535 | 7738 | 6666.000000 | 0.037305 | None |
| 24 | 2026-11-04T06:14:20Z | anomaly_review | ok | stop | 3570 | 5274 | 4233.000000 | 0.026877 | None |
| 25 | 2026-11-04T06:14:59Z | anomaly_review | ok | stop | 3708 | 4732 | 3733.000000 | 0.024746 | None |
| 26 | 2026-11-04T06:15:40Z | anomaly_review | ok | stop | 3523 | 5120 | 4097.000000 | 0.026164 | None |
| 27 | 2026-11-04T06:16:13Z | anomaly_review | ok | stop | 3290 | 4017 | 2995.000000 | 0.021185 | None |
| 28 | 2026-11-04T06:16:51Z | anomaly_review | ok | stop | 3516 | 5004 | 3945.000000 | 0.025662 | None |
| 29 | 2026-11-04T06:17:28Z | anomaly_review | ok | stop | 3426 | 4944 | 3867.000000 | 0.025295 | None |
| 30 | 2026-11-04T06:18:04Z | anomaly_review | ok | stop | 3051 | 4172 | 3318.000000 | 0.021545 | None |
| 31 | 2026-11-04T06:19:00Z | feature_proposals | ok | stop | 1595 | 5145 | 4751.000000 | 0.023860 | None |
