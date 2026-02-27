"""
認証系 cleanup バッチの CLI エントリポイント.
"""

from __future__ import annotations

import sys

from app.jobs.cleanup.runner import _build_parser, main

__all__ = ["main", "_build_parser"]


if __name__ == "__main__":
    sys.exit(main())
