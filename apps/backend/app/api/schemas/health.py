from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response schema for health check endpoint."""

    status: Literal["ok"]
