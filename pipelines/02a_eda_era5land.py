"""EDA of the hourly ERA5-Land series. Thin CLI over frostwatch_ml.eda.era5land.

Run: .venv/bin/python pipelines/02a_eda_era5land.py [--dry-run] [--no-sync]
"""

from frostwatch_ml import cli
from frostwatch_ml.dataio.manifest import verify_manifest
from frostwatch_ml.eda import era5land


def main() -> None:
    args = cli.parser(__doc__, "configs/frost.yaml").parse_args()
    if args.dry_run:
        rows = verify_manifest(check_hashes=False)
        print(f"dry run: {sum(r['size_ok'] for r in rows)}/{len(rows)} raw files present; would run eda.era5land")
        return
    era5land.main()
    cli.finish("02a_eda_era5land", args)


if __name__ == "__main__":
    main()
