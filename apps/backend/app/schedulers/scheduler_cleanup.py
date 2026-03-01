"""
定期 cleanup バッチの CLI エントリポイント.
"""

from __future__ import annotations

import sys

from app.schedulers.cleanup.runner_registry import _build_parser, main

__all__ = ["main", "_build_parser"]


if __name__ == "__main__":
    sys.exit(main())
