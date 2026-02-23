from fastapi import FastAPI
import uvicorn

app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    """Run development server entrypoint for `uv run backend`."""
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
