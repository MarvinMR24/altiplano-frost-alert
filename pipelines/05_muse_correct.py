"""Muse experiment: condition B (Muse-reviewed corrections B1 plus Muse-proposed features B2) against
condition A (LR_best), validation only. The test split stays locked.

MUSE_MOCK=1 (default) uses deterministic fake answers and makes no network call; MUSE_MOCK=0 calls
the Meta Model API with META_API_KEY and META_API_BASE_URL from the environment. Every call is cached
in logs/muse_cache/; re-runs read from the cache.

Run: .venv/bin/python pipelines/05_muse_correct.py --config configs/muse.yaml [--dry-run] [--smoke N] [--no-sync]
  --dry-run   build the masked payloads, print the number of calls and the cost estimate, write nothing
  --smoke N   one call with an N-record review batch, check that strict JSON parses, write nothing else
"""

import json

from frostwatch_ml import cli, config
from frostwatch_ml.muse import experiment


def main() -> None:
    p = cli.parser(__doc__, "configs/muse.yaml")
    p.add_argument("--smoke", type=int, default=0, help="one review call with N records, then stop")
    args = p.parse_args()
    mcfg = config.load_yaml(args.config)
    if args.smoke:
        print(json.dumps(experiment.smoke(mcfg, args.seed, args.smoke), indent=1, default=str))
        return
    out = experiment.run(mcfg, args.seed, dry_run=args.dry_run)
    if not args.dry_run:
        print("run", out["run_id"], "| this run:", json.dumps(out["run_stats"]))
        print("B1 decisions:", out["decisions"], "| feature values changed by Muse:", out["diff_muse"]["values_changed"],
              "| by clipping:", out["diff_clip"]["values_changed"])
        print("B2:", [(r["muse_name"], r["decision"]) for r in out["b2"]])
        print(out["pooled"].loc[["climatology", "persistence", "A", "B"], ["pr_auc", "f2", "brier"]].round(4).to_string())
        print("A recheck confirmed:", out["a_confirmed"], "| gain:", {k: round(v, 4) for k, v in out["gain"].items()},
              "| verdict:", out["verdict"], "| mlflow:", out["mlflow_url"])
        print("experiment usage total:", out["usage_after"])
    cli.finish("05_muse_correct", args)


if __name__ == "__main__":
    main()
