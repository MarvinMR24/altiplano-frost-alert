"""Internal operations as a CLI (never HTTP: the public tunnel forwards every route).

    python -m app.cli replay --night YYYY-MM-DD [--email X] [--dry-run]
    python -m app.cli tick [--night YYYY-MM-DD] [--dry-run]
    python -m app.cli seed-demo [--email X]

replay is the demo path: it processes a past night with its simulated clock, a real
explanation, real email and real push, and labels everything "replay". tick processes one
night (default: the latest available). Alerts are generated when a night is processed, never
in real time.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from sqlalchemy import select

from .config import get_settings
from .db import init_db, make_engine
from .models import Aoi, User
from .providers import NightNotFound, ProviderError, get_provider
from .services.alerting import process_night
from .services.notify_email import get_email_sender

DEMO_EMAIL = "demo@frostwatch.invalid"
# Small squares (about 2 km) around two cells, inside the coverage. Flagged DEMO.
DEMO_AOIS = [
    ("DEMO El Alto", -68.2, -16.5, 30),
    ("DEMO Oruro", -67.1, -18.0, 50),
]


def _square(lon: float, lat: float, half: float = 0.01) -> dict:
    ring = [[lon - half, lat - half], [lon + half, lat - half], [lon + half, lat + half], [lon - half, lat + half]]
    return {"type": "Polygon", "coordinates": [[*ring, ring[0]]]}


def _night(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("use YYYY-MM-DD") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    rp = sub.add_parser("replay", help="Process a past night as a labeled replay (demo path)")
    rp.add_argument("--night", type=_night, required=True)
    rp.add_argument("--email", help="Only this user's AOIs")
    rp.add_argument("--dry-run", action="store_true", help="Report what would be sent; create and send nothing")
    tk = sub.add_parser("tick", help="Process one night (default: the latest available)")
    tk.add_argument("--night", "--date", dest="night", type=_night)
    tk.add_argument("--email", help="Only this user's AOIs")
    tk.add_argument("--dry-run", action="store_true")
    sd = sub.add_parser("seed-demo", help="Create a demo user with AOIs (flagged DEMO)")
    sd.add_argument("--email", default=DEMO_EMAIL)
    sd.add_argument("--language", choices=["es", "en", "ay", "qu"], default="es")
    sd.add_argument("--profile", choices=["producer", "resident"], default="producer")
    args = parser.parse_args(argv)

    settings = get_settings()
    settings.var_dir.mkdir(parents=True, exist_ok=True)
    factory = init_db(make_engine(settings.database_url))
    with factory() as db:
        if args.command == "seed-demo":
            return _seed(db, args)
        provider = get_provider(settings)
        try:
            night = args.night or provider.latest_night()
            summary = process_night(db, settings=settings, provider=provider, night=night,
                                    mode="replay" if args.command == "replay" else "tick",
                                    email_sender=get_email_sender(settings), email=args.email, dry_run=args.dry_run)
        except NightNotFound:
            print(f"error: no predictions for night {args.night}", file=sys.stderr)
            return 2
        except ProviderError as exc:
            print(f"error: data provider unavailable: {exc}", file=sys.stderr)
            return 3
    print(json.dumps(summary.as_dict(), indent=2, default=str))
    return 0


def _seed(db, args) -> int:
    email = args.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, notification_email=email, name="DEMO", language=args.language, profile=args.profile,
                    onboarded=True, is_demo=True, email_verified=True)
        db.add(user)
        db.flush()
    created = 0
    for name, lon, lat, threshold in DEMO_AOIS:
        if db.scalar(select(Aoi).where(Aoi.user_id == user.id, Aoi.name == name)) is None:
            db.add(Aoi(user_id=user.id, name=name, polygon=_square(lon, lat), threshold=threshold,
                       channel_push=True, channel_email=True, is_demo=True))
            created += 1
    db.commit()
    print(json.dumps({"user_id": user.id, "email": email, "demo": True, "aois_created": created}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
