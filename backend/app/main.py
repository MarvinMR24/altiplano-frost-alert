"""FrostWatch backend: app factory, routers and GET /health.

Risk data is precomputed offline per cell and night (DATA_PROVIDER=mock or artifacts). Alerts
are created only when a night is processed through the CLI (python -m app.cli replay|tick).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .db import init_db, make_engine
from .providers import get_provider
from .routers import alerts, aois, auth, geo, map, me, model
from .security import RateLimiter
from .services.notify_email import get_email_sender


def _validation_message(exc: RequestValidationError) -> str:
    parts = []
    for err in exc.errors()[:3]:
        loc = ".".join(str(x) for x in err.get("loc", []) if x != "body")
        parts.append(f"{loc}: {err.get('msg')}" if loc else str(err.get("msg")))
    return "; ".join(parts) or "invalid request"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings.var_dir.mkdir(parents=True, exist_ok=True)
    engine = make_engine(settings.database_url)

    app = FastAPI(title="FrostWatch Altiplano API", version="1.0.0")
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = init_db(engine)
    app.state.provider = get_provider(settings)
    app.state.email_sender = get_email_sender(settings)
    app.state.limiter = RateLimiter()

    # Expo web runs on another origin during local testing. Bearer tokens, no cookies.
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": _validation_message(exc)})

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    for module in (auth, me, geo, map, aois, alerts, model):
        app.include_router(module.router)
    app.include_router(auth.password_router)
    logging.getLogger("frostwatch").info("backend ready provider=%s email=%s muse_mock=%s",
                                         settings.data_provider, settings.email_provider, settings.muse_mock)
    return app


app = create_app()
