from fastapi import APIRouter

from app.api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Return service health status."""
    return HealthResponse(status="ok")
