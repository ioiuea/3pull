"""
フォルダエンドポイント

このモジュールはフォルダのCRUD操作を提供します。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import AuthenticatedUser, get_current_user
from app.api.deps import get_folder_repo
from app.models.schemas import FolderCreate, FolderRead, FolderUpdate
from app.repositories.base import FolderRepositoryProtocol, RepositoryNotFoundError

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get("", response_model=list[FolderRead])
async def list_folders(
    limit: int = Query(50, ge=1, le=200, description="取得件数上限"),
    offset: int = Query(0, ge=0, description="取得開始位置"),
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    repo: FolderRepositoryProtocol = Depends(get_folder_repo),  # noqa: B008
) -> list[FolderRead]:
    """
    フォルダ一覧を取得

    認証済みユーザーのフォルダ一覧を取得します。

    Args:
        limit: 取得件数上限（1〜200、デフォルト50）
        offset: 取得開始位置（デフォルト0）
        current_user: 認証済みユーザー情報
        repo: フォルダリポジトリ

    Returns:
        list[FolderRead]: フォルダ一覧
    """
    return await repo.list(user_id=current_user.user_id, limit=limit, offset=offset)


@router.get("/{folder_id}", response_model=FolderRead)
async def get_folder(
    folder_id: str,
    repo: FolderRepositoryProtocol = Depends(get_folder_repo),  # noqa: B008
) -> FolderRead:
    """
    フォルダを取得

    指定されたIDのフォルダを取得します。

    Args:
        folder_id: フォルダID
        repo: フォルダリポジトリ

    Returns:
        FolderRead: フォルダ情報

    Raises:
        HTTPException: フォルダが見つからない場合（404）
    """
    try:
        return await repo.get(folder_id)
    except RepositoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder {folder_id} not found",
        ) from None


@router.post("", response_model=FolderRead, status_code=status.HTTP_201_CREATED)
async def create_folder(
    dto: FolderCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
    repo: FolderRepositoryProtocol = Depends(get_folder_repo),  # noqa: B008
) -> FolderRead:
    """
    フォルダを作成

    新しいフォルダを作成します。
    ID、作成日時、ユーザー情報は認証済みユーザーから自動付与されます。

    Args:
        dto: フォルダ作成データ
        current_user: 認証済みユーザー情報
        repo: フォルダリポジトリ

    Returns:
        FolderRead: 作成されたフォルダ情報
    """
    return await repo.create(
        dto, user_id=current_user.user_id, email=current_user.email
    )


@router.put("/{folder_id}", response_model=FolderRead)
async def update_folder(
    folder_id: str,
    dto: FolderUpdate,
    repo: FolderRepositoryProtocol = Depends(get_folder_repo),  # noqa: B008
) -> FolderRead:
    """
    フォルダを更新

    指定されたIDのフォルダを更新します。

    Args:
        folder_id: フォルダID
        dto: フォルダ更新データ
        repo: フォルダリポジトリ

    Returns:
        FolderRead: 更新されたフォルダ情報

    Raises:
        HTTPException: フォルダが見つからない場合（404）
    """
    try:
        return await repo.update(folder_id, dto)
    except RepositoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder {folder_id} not found",
        ) from None


@router.delete("/{folder_id}", status_code=status.HTTP_200_OK)
async def delete_folder(
    folder_id: str,
    repo: FolderRepositoryProtocol = Depends(get_folder_repo),  # noqa: B008
) -> dict[str, str]:
    """
    フォルダを削除

    指定されたIDのフォルダを削除します。

    Args:
        folder_id: フォルダID
        repo: フォルダリポジトリ

    Returns:
        dict[str, str]: 削除成功メッセージ

    Raises:
        HTTPException: フォルダが見つからない場合（404）
    """
    try:
        await repo.delete(folder_id)
        return {"message": f"Folder {folder_id} deleted successfully"}
    except RepositoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder {folder_id} not found",
        ) from None
