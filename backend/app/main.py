"""FrostWatch backend entry point.

Skeleton only: the API in docs/api_contract.md is implemented by the backend session.
"""

from fastapi import FastAPI

app = FastAPI(title="FrostWatch Altiplano API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
