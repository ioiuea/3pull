from fastapi import FastAPI
import uvicorn

from app.api.routers.health import router as health_router

API_PREFIX = "/backend"

app = FastAPI()
app.include_router(health_router, prefix=API_PREFIX)


def main() -> None:
    """Run FastAPI bootstrap entrypoint for `uv run backend`."""
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
