"""MLflow mirror of experiments/<run_id>/ (the local folder is the source of truth).

Explicit logging only (no autolog). Credentials are read by MLflow from the environment, loaded
from .env without printing. One attempt: HTTP retries are disabled; on any failure (auth, network)
logging is disabled for the rest of the process and reported once. Nothing about the test set is
ever logged.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .. import config

_STATE = {"enabled": None, "reason": None, "experiment_id": None}
EXPERIMENT = "frostwatch-altiplano"


def _init() -> bool:
    if _STATE["enabled"] is not None:
        return _STATE["enabled"]
    log = config.get_logger("mlflow")
    if os.environ.get("FROSTWATCH_MLFLOW") == "0":
        _STATE.update(enabled=False, reason="disabled by FROSTWATCH_MLFLOW=0")
        return False
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    try:
        from dotenv import load_dotenv
        load_dotenv(config.ROOT / ".env", override=False)
        uri = os.environ.get("MLFLOW_TRACKING_URI")
        if not uri or not uri.startswith("https://dagshub.com/"):
            raise RuntimeError("MLFLOW_TRACKING_URI missing or not on dagshub.com")
        os.environ["MLFLOW_HTTP_REQUEST_MAX_RETRIES"] = "0"
        os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "60")
        import mlflow
        mlflow.set_tracking_uri(uri)
        exp = mlflow.set_experiment(EXPERIMENT)
        _STATE.update(enabled=True, experiment_id=exp.experiment_id)
        config.log_event(log, "mlflow ready", experiment=EXPERIMENT)
    except Exception as exc:  # report once, continue locally
        msg = type(exc).__name__ + ": " + str(exc).split("\n")[0][:200]
        _STATE.update(enabled=False, reason=msg)
        config.log_event(log, "mlflow disabled, continuing locally", reason=msg)
    return _STATE["enabled"]


def status() -> dict:
    return dict(_STATE)


def git_head() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config.ROOT, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else "unknown"
    except Exception:
        return "unknown"


def run_url(run_id: str) -> str | None:
    uri = os.environ.get("MLFLOW_TRACKING_URI", "")
    if not _STATE["enabled"] or not uri:
        return None
    return f"{uri.rstrip('/')}/#/experiments/{_STATE['experiment_id']}/runs/{run_id}"


def log_run(run_name: str, params: dict, metrics: dict, tags: dict, artifacts: list[Path]) -> str | None:
    """Log one run; returns its MLflow UI link (no credentials) or None when MLflow is unavailable."""
    if not _init():
        return None
    import mlflow
    try:
        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_params({k: str(v) for k, v in params.items()})
            mlflow.log_metrics({k: float(v) for k, v in metrics.items() if v == v})
            mlflow.set_tags({k: str(v) for k, v in tags.items()})
            for a in artifacts:
                if Path(a).exists():
                    mlflow.log_artifact(str(a))
            return run_url(run.info.run_id)
    except Exception as exc:
        msg = type(exc).__name__ + ": " + str(exc).split("\n")[0][:200]
        _STATE.update(enabled=False, reason=msg)
        config.log_event(config.get_logger("mlflow"), "mlflow run failed, disabled", run=run_name, reason=msg)
        return None
