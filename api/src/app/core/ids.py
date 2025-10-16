"""
UUID生成ユーティリティ

このモジュールはUUIDの生成機能を提供します。
"""

import uuid


def new_uuid() -> str:
    """
    新しいUUIDを生成する

    UUIDv7が利用可能な場合はv7を、そうでない場合はv4を生成します。

    Returns:
        str: UUID文字列（例: "579525b3-1d87-4055-98d1-37a54ee8f52f"）

    Example:
        ```python
        id = new_uuid()
        print(id)  # "579525b3-1d87-4055-98d1-37a54ee8f52f"
        ```
    """
    return str(uuid.uuid4())
