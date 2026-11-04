"""EDA of the AgERA5 daily series and cross-checks. Thin CLI over frostwatch_ml.eda.agera5.

Run: .venv/bin/python pipelines/02b_eda_agera5.py [--dry-run] [--no-sync]
"""

from frostwatch_ml import cli
from frostwatch_ml.dataio.manifest import verify_manifest
from frostwatch_ml.eda import agera5


def main() -> None:
    args = cli.parser(__doc__, "configs/frost.yaml").parse_args()
    if args.dry_run:
        rows = verify_manifest(check_hashes=False)
        print(f"dry run: {sum(r['size_ok'] for r in rows)}/{len(rows)} raw files present; would run eda.agera5")
        return
    agera5.main()
    cli.finish("02b_eda_agera5", args)


if __name__ == "__main__":
    main()
