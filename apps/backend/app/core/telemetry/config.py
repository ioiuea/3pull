"""Azure Monitor OpenTelemetry の初期化設定."""

from __future__ import annotations

from platform import node
from typing import Any

from opentelemetry.sdk.resources import Resource

from app.core.settings import get_settings

APP_TELEMETRY_LOGGER_NAME = "app"
_UNSET = object()

_telemetry_configured = False
_app_instrumented = False


def configure_telemetry(
    *,
    service_name: str,
    connection_string: str | None | object = _UNSET,
) -> bool:
    """指定 service.name で telemetry を初期化し、実行時は True を返す."""
    global _telemetry_configured

    if _telemetry_configured:
        return True

    settings = get_settings()
    resolved_connection_string = (
        connection_string
        if connection_string is not _UNSET
        else settings.applicationinsights_connection_string
    )
    if not resolved_connection_string:
        return False

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.instance.id": node() or service_name,
        }
    )

    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(
        connection_string=resolved_connection_string,
        logger_name=APP_TELEMETRY_LOGGER_NAME,
        resource=resource,
    )
    _telemetry_configured = True
    return True


def configure_api_telemetry() -> bool:
    """API 向け telemetry を初期化し、実行時は True を返す."""
    settings = get_settings()
    return configure_telemetry(
        service_name=settings.api_service_name,
        connection_string=settings.applicationinsights_connection_string,
    )


def instrument_api_app(app: Any) -> None:
    """既存の FastAPI app に request telemetry 計装を適用する."""
    global _app_instrumented

    if _app_instrumented:
        return

    settings = get_settings()
    if not settings.applicationinsights_connection_string:
        return

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)
    _app_instrumented = True
