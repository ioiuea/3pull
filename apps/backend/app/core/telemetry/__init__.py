"""backend の telemetry パッケージ.

- `config.py`
  - Azure Monitor OpenTelemetry の初期化を提供する

利用側は `app.core.telemetry` から以下を import する。

- `configure_api_telemetry`
- `configure_telemetry`
- `instrument_api_app`
"""

from app.core.telemetry.config import (
    configure_api_telemetry,
    configure_telemetry,
    instrument_api_app,
)

__all__ = ["configure_api_telemetry", "configure_telemetry", "instrument_api_app"]
