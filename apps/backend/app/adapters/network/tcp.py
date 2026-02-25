"""
運用チェックやヘルスエンドポイント向けの軽量 TCP 到達性プローブ。

- TCP 接続を試みて即時にクローズする。
- 返り値は (成功可否, レイテンシ, エラー文字列)。
"""

from __future__ import annotations

import socket
import time
from typing import Final

_NS_PER_MS: Final[int] = 1_000_000
_MIN_PORT: Final[int] = 1
_MAX_PORT: Final[int] = 65_535
_DEFAULT_TIMEOUT_SEC: Final[float] = 1.0


def _normalize_timeout(timeout: float) -> float:
    """
    タイムアウト秒を検証して正規化する。
    """
    if timeout <= 0:
        raise ValueError("timeout must be > 0")
    return timeout


def _validate_target(host: str, port: int) -> None:
    """
    呼び出し側に明確なエラーを返すため host/port を検証する。
    """
    if not host.strip():
        raise ValueError("host must not be empty")
    if not (_MIN_PORT <= port <= _MAX_PORT):
        raise ValueError(f"port must be between {_MIN_PORT} and {_MAX_PORT}")


def _elapsed_ms(start_ns: int) -> int:
    """
    単調時計の開始時刻からの経過ミリ秒を返す。

    引数:
        start_ns: 開始時刻（ns）

    戻り値:
        int: 経過ミリ秒
    """
    return int((time.perf_counter_ns() - start_ns) / _NS_PER_MS)


def tcp_ping(
    host: str, port: int, timeout: float = _DEFAULT_TIMEOUT_SEC
) -> tuple[bool, int, str | None]:
    """
    軽量な TCP 到達性チェック。

    `(host, port)` へ TCP 接続を試み、接続後すぐにクローズする。
    返り値は (成功可否, レイテンシms, エラー文字列)。

    引数:
        host: 対象ホスト名または IP
        port: 対象ポート番号
        timeout: 接続タイムアウト秒（既定: 1.0）

    戻り値:
        tuple[bool, int, str | None]:
            - ok: 接続成功なら True
            - latency_ms: 測定レイテンシ（ms）
            - error: エラー文字列または None

    使用例:
        >>> ok, ms, err = tcp_ping("127.0.0.1", 80, timeout=0.1)
        >>> isinstance(ok, bool) and isinstance(ms, int)
        True
    """
    _validate_target(host, port)
    normalized_timeout = _normalize_timeout(timeout)
    start_ns = time.perf_counter_ns()

    try:
        # create_connection はソケットを返し、with でクローズできる。
        with socket.create_connection((host, port), timeout=normalized_timeout):
            return True, _elapsed_ms(start_ns), None
    except socket.timeout:
        return False, _elapsed_ms(start_ns), "timeout"

    except ConnectionRefusedError as error:
        # ポート閉塞や未待受など。
        return False, _elapsed_ms(start_ns), str(error)

    except socket.gaierror as error:
        # 名前解決エラー。
        return False, _elapsed_ms(start_ns), str(error)

    except OSError as error:
        # その他のソケット系エラー。
        error_message = str(error) or error.__class__.__name__
        return False, _elapsed_ms(start_ns), error_message
