"""
チャットスレッドエンドポイント

このモジュールはチャットスレッドのCRUD操作を提供します。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import AuthenticatedUser, get_current_user
from app.api.deps import get_chatthread_repo
from app.models.schemas import ChatThreadCreate, ChatThreadRead, ChatThreadUpdate
from app.repositories.base import (
    ChatThreadRepositoryProtocol,
    RepositoryNotFoundError,
)

router = APIRouter(prefix="/chat-threads", tags=["chatThreads"])


@router.get("", response_model=list[ChatThreadRead])
async def list_chat_threads(
    limit: int = Query(50, ge=1, le=200, description="取得件数上限"),
    offset: int = Query(0, ge=0, description="取得開始位置"),
    folder_id: str | None = Query(
        None, alias="folderId", description="フォルダIDでフィルタ"
    ),
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    repo: ChatThreadRepositoryProtocol = Depends(get_chatthread_repo),  # noqa: B008
) -> list[ChatThreadRead]:
    """
    チャットスレッド一覧を取得

    認証済みユーザーのチャットスレッド一覧を取得します。
    folderId指定でフォルダ内のスレッドに絞り込み可能です。

    Args:
        limit: 取得件数上限（1〜200、デフォルト50）
        offset: 取得開始位置（デフォルト0）
        folder_id: フォルダIDでフィルタ（任意）
        current_user: 認証済みユーザー情報
        repo: チャットスレッドリポジトリ

    Returns:
        list[ChatThreadRead]: チャットスレッド一覧
    """
    return await repo.list(
        user_id=current_user.user_id,
        limit=limit,
        offset=offset,
        folder_id=folder_id,
    )


@router.get("/{thread_id}", response_model=ChatThreadRead)
async def get_chat_thread(
    thread_id: str,
    repo: ChatThreadRepositoryProtocol = Depends(get_chatthread_repo),  # noqa: B008
) -> ChatThreadRead:
    """
    チャットスレッドを取得

    指定されたIDのチャットスレッドを取得します。

    Args:
        thread_id: チャットスレッドID
        repo: チャットスレッドリポジトリ

    Returns:
        ChatThreadRead: チャットスレッド情報

    Raises:
        HTTPException: チャットスレッドが見つからない場合（404）
    """
    try:
        return await repo.get(thread_id)
    except RepositoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ChatThread {thread_id} not found",
        ) from None


@router.post("", response_model=ChatThreadRead, status_code=status.HTTP_201_CREATED)
async def create_chat_thread(
    dto: ChatThreadCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    repo: ChatThreadRepositoryProtocol = Depends(get_chatthread_repo),  # noqa: B008
) -> ChatThreadRead:
    """
    チャットスレッドを作成

    新しいチャットスレッドを作成します。
    ID、作成日時、ユーザー情報は認証済みユーザーから自動付与されます。

    Args:
        dto: チャットスレッド作成データ
        current_user: 認証済みユーザー情報
        repo: チャットスレッドリポジトリ

    Returns:
        ChatThreadRead: 作成されたチャットスレッド情報
    """
    return await repo.create(
        dto, user_id=current_user.user_id, email=current_user.email
    )


@router.put("/{thread_id}", response_model=ChatThreadRead)
async def update_chat_thread(
    thread_id: str,
    dto: ChatThreadUpdate,
    repo: ChatThreadRepositoryProtocol = Depends(get_chatthread_repo),  # noqa: B008
) -> ChatThreadRead:
    """
    チャットスレッドを更新

    指定されたIDのチャットスレッドを更新します。

    Args:
        thread_id: チャットスレッドID
        dto: チャットスレッド更新データ
        repo: チャットスレッドリポジトリ

    Returns:
        ChatThreadRead: 更新されたチャットスレッド情報

    Raises:
        HTTPException: チャットスレッドが見つからない場合（404）
    """
    try:
        return await repo.update(thread_id, dto)
    except RepositoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ChatThread {thread_id} not found",
        ) from None


@router.delete("/{thread_id}", status_code=status.HTTP_200_OK)
async def delete_chat_thread(
    thread_id: str,
    repo: ChatThreadRepositoryProtocol = Depends(get_chatthread_repo),  # noqa: B008
) -> dict[str, str]:
    """
    チャットスレッドを削除

    指定されたIDのチャットスレッドを削除します。

    Args:
        thread_id: チャットスレッドID
        repo: チャットスレッドリポジトリ

    Returns:
        dict[str, str]: 削除成功メッセージ

    Raises:
        HTTPException: チャットスレッドが見つからない場合（404）
    """
    try:
        await repo.delete(thread_id)
        return {"message": f"ChatThread {thread_id} deleted successfully"}
    except RepositoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ChatThread {thread_id} not found",
        ) from None
