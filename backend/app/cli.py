"""Internal operations as a CLI (never HTTP, the public tunnel forwards every route).

Usage:
    python -m app.cli replay
    python -m app.cli tick [--date YYYY-MM-DD]

Skeleton only: the backend session implements both commands.
"""

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("replay", help="Replay a held-out test night with a simulated clock")
    tick = sub.add_parser("tick", help="Process one night (default: latest available)")
    tick.add_argument("--date", help="Night date YYYY-MM-DD")
    args = parser.parse_args(argv)
    print(f"{args.command}: not implemented yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
