"""EDA of the night table. Thin CLI over frostwatch_ml.eda.merged.

Run: .venv/bin/python pipelines/03b_eda_merged.py [--dry-run] [--no-sync]
"""

from frostwatch_ml import cli
from frostwatch_ml.dataio.manifest import verify_manifest
from frostwatch_ml.eda import merged


def main() -> None:
    args = cli.parser(__doc__, "configs/frost.yaml").parse_args()
    if args.dry_run:
        rows = verify_manifest(check_hashes=False)
        print(f"dry run: {sum(r['size_ok'] for r in rows)}/{len(rows)} raw files present; would run eda.merged")
        return
    merged.main()
    cli.finish("03b_eda_merged", args)


if __name__ == "__main__":
    main()
