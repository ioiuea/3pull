"""
Azure SQL 接続用の Microsoft Entra アクセストークン処理.
"""

from __future__ import annotations

import struct

from azure.identity import DefaultAzureCredential

SQL_COPT_SS_ACCESS_TOKEN = 1256


def create_access_token_struct(*, scope: str) -> bytes:
    """
    ODBC Driver 18 for SQL Server 向けのアクセストークン構造体を作る.

    Args:
        scope: Azure SQL 用トークンスコープ

    Returns:
        bytes: `attrs_before` に渡すトークン構造体
    """
    credential = DefaultAzureCredential()
    token = credential.get_token(scope).token.encode("utf-16-le")
    return struct.pack(f"<I{len(token)}s", len(token), token)
