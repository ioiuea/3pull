"""Kubernetes などの内部ヘルスプローブ用エンドポイント。"""

from fastapi import APIRouter

router = APIRouter(tags=["probes"], include_in_schema=False)


@router.get("/livez")
def livez() -> dict[str, str]:
    """プロセス生存確認用の軽量プローブ。"""
    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> dict[str, str]:
    """受け付け準備完了確認用の軽量プローブ。"""
    return {"status": "ok"}

