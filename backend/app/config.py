"""Settings read from environment variables (values live only in the environment or .env files).

Every variable the backend reads is listed in backend/.env.backend.example. On the host, values
can be put in backend/.env.backend (loaded without overriding the environment). Secrets are
never logged; `Settings.__repr__` hides them.
"""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent

log = logging.getLogger("frostwatch.config")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _int(name: str, default: int) -> int:
    raw = _env(name)
    return int(raw) if raw else default


def _float(name: str, default: float) -> float:
    raw = _env(name)
    return float(raw) if raw else default


def _bool(name: str, default: bool) -> bool:
    raw = _env(name).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _default_artifacts_dir() -> str:
    docker_path = Path("/app/artifacts")
    return str(docker_path if docker_path.is_dir() else REPO_DIR / "artifacts")


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    var_dir: Path
    data_provider: str
    artifacts_dir: Path
    coverage_radius_km: float
    session_secret: str = field(repr=False)
    session_ttl_days: int
    email_provider: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str = field(repr=False)
    email_from: str
    expo_push_url: str
    meta_api_key: str = field(repr=False)
    meta_api_base_url: str
    muse_model: str
    muse_mock: bool
    muse_max_tokens: int
    muse_max_calls_per_run: int
    rate_limit_per_minute: int
    # Browser origins allowed by CORS (the Expo web dev server). Native apps ignore CORS.
    cors_origins: tuple[str, ...] = ("http://localhost:8081", "http://127.0.0.1:8081")
    # Muse Spark reasons before answering (about 30 to 55 s per call in the experiment).
    muse_timeout_s: int = 120
    # Google sign in needs a web OAuth client and the public backend URL (the redirect URI
    # is PUBLIC_BASE_URL/auth/google/callback).
    public_base_url: str = ""
    google_client_id: str = ""
    google_client_secret: str = field(default="", repr=False)
    # Deep links the Google flow may return to (Expo Go and the app scheme).
    app_redirect_prefixes: tuple[str, ...] = ("exp://", "exps://", "frostwatch://")

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret and self.public_base_url)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def muse_usage_log(self) -> Path:
        return self.var_dir / "logs" / "muse_usage.jsonl"


def _load_env_file() -> None:
    """Optional host-run convenience: backend/.env.backend (gitignored), never overriding the environment."""
    path = Path(_env("BACKEND_ENV_FILE", str(BACKEND_DIR / ".env.backend")))
    if path.is_file():
        from dotenv import load_dotenv

        load_dotenv(path, override=False)


def load_settings() -> Settings:
    if _env("APP_ENV") != "test":
        _load_env_file()
    var_dir = Path(_env("BACKEND_VAR_DIR", str(BACKEND_DIR / "var")))
    secret = _env("SESSION_SECRET")
    app_env = _env("APP_ENV", "development").lower()
    if not secret:
        if app_env == "production":
            raise RuntimeError("SESSION_SECRET is required when APP_ENV=production")
        secret = secrets.token_urlsafe(48)
        log.warning("SESSION_SECRET not set: using an ephemeral secret, sessions end on restart")
    return Settings(
        app_env=app_env,
        database_url=_env("DATABASE_URL", f"sqlite:///{var_dir / 'frostwatch.db'}"),
        var_dir=var_dir,
        data_provider=_env("DATA_PROVIDER", "mock").lower(),
        artifacts_dir=Path(_env("ARTIFACTS_DIR", _default_artifacts_dir())),
        coverage_radius_km=_float("COVERAGE_RADIUS_KM", 30.0),
        session_secret=secret,
        session_ttl_days=30,
        email_provider=_env("EMAIL_PROVIDER", "console").lower(),
        smtp_host=_env("EMAIL_SMTP_HOST"),
        smtp_port=_int("EMAIL_SMTP_PORT", 587),
        smtp_user=_env("EMAIL_SMTP_USER"),
        smtp_password=_env("EMAIL_SMTP_PASSWORD"),
        email_from=_env("EMAIL_FROM"),
        expo_push_url=_env("EXPO_PUSH_URL", "https://exp.host/--/api/v2/push/send"),
        meta_api_key=_env("META_API_KEY"),
        meta_api_base_url=_env("META_API_BASE_URL"),
        muse_model=_env("MUSE_MODEL", "muse-spark-1.3"),
        muse_mock=_bool("MUSE_MOCK", True),
        # Reasoning tokens count toward max_tokens: the experiment used 2,700 to 5,400 of them per
        # answer, and 700 left the reply empty (finish_reason length).
        muse_max_tokens=_int("MUSE_MAX_TOKENS", 8000),
        muse_timeout_s=_int("MUSE_TIMEOUT_S", 120),
        public_base_url=_env("PUBLIC_BASE_URL").rstrip("/"),
        google_client_id=_env("GOOGLE_CLIENT_ID"),
        google_client_secret=_env("GOOGLE_CLIENT_SECRET"),
        muse_max_calls_per_run=_int("MUSE_MAX_CALLS_PER_RUN", 40),
        rate_limit_per_minute=_int("RATE_LIMIT_PER_MINUTE", 120),
        cors_origins=tuple(
            o.strip()
            for o in _env("CORS_ORIGINS", "http://localhost:8081,http://127.0.0.1:8081").split(",")
            if o.strip()
        ),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


def reset_settings() -> None:
    get_settings.cache_clear()
