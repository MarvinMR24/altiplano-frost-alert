"""Build the night table (features, crosschecks, fitted statistics). Thin CLI over
frostwatch_ml.features.night_table.

Run: .venv/bin/python pipelines/03_build_night_table.py [--dry-run] [--no-sync]
"""

from frostwatch_ml import cli, config
from frostwatch_ml.dataio.manifest import verify_manifest
from frostwatch_ml.features import night_table


def main() -> None:
    args = cli.parser(__doc__, "configs/frost.yaml").parse_args()
    cfg = config.load_yaml(args.config)
    if args.dry_run:
        rows = verify_manifest(check_hashes=False)
        print(f"dry run: {sum(r['size_ok'] for r in rows)}/{len(rows)} raw files present; {len(night_table.feature_columns())} features")
        return
    df, xc, stats = night_table.build_night_table(cfg)
    manifest = night_table.write_outputs(df, xc, stats, cfg)
    print({k: v for k, v in manifest["split_counts"].items()})
    print("rows", manifest["rows"], "latest night", manifest["latest_available_night"])
    cli.finish("03_build_night_table", args)


if __name__ == "__main__":
    main()
