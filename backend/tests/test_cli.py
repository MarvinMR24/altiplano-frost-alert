import json

from sqlalchemy import func, select

from app import cli
from app.config import reset_settings
from app.db import init_db, make_engine
from app.models import Alert, Aoi, User


def _env(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKEND_VAR_DIR", str(tmp_path / "var"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cli.db'}")
    reset_settings()
    return init_db(make_engine(f"sqlite:///{tmp_path / 'cli.db'}"))


def test_seed_demo_and_replay(tmp_path, monkeypatch, capsys):
    factory = _env(tmp_path, monkeypatch)
    try:
        assert cli.main(["seed-demo", "--email", "demo@example.com"]) == 0
        assert cli.main(["seed-demo", "--email", "demo@example.com"]) == 0  # idempotent
        with factory() as db:
            assert db.scalar(select(func.count()).select_from(Aoi)) == 2
            assert db.scalars(select(User)).one().is_demo is True
        capsys.readouterr()
        assert cli.main(["replay", "--night", "2026-07-14", "--email", "demo@example.com", "--dry-run"]) == 0
        dry = json.loads(capsys.readouterr().out)
        assert dry["dry_run"] is True and dry["alerts_created"] == []
        assert cli.main(["replay", "--night", "2026-07-14", "--email", "demo@example.com"]) == 0
        out = json.loads(capsys.readouterr().out)
        assert out["mode"] == "replay" and out["data_source"] == "MOCK"
        assert len(out["alerts_created"]) == len(dry["would_alert"])
        with factory() as db:
            alerts = db.scalars(select(Alert)).all()
            assert all(a.mode == "replay" for a in alerts)
        assert cli.main(["replay", "--night", "2026-07-14"]) == 0
        assert json.loads(capsys.readouterr().out)["alerts_created"] == []
        assert cli.main(["tick"]) == 0
        assert json.loads(capsys.readouterr().out)["night_date"] == "2026-07-14"
        assert cli.main(["replay", "--night", "1999-01-01"]) == 2
    finally:
        reset_settings()
