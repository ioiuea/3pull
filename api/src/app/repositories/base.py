"""
Repository抽象インターフェース

このモジュールはデータアクセス層の抽象インターフェースを定義します。
"""

from typing import Protocol

from app.models.schemas import (
    ChatThreadCreate,
    ChatThreadRead,
    ChatThreadUpdate,
    FolderCreate,
    FolderRead,
    FolderUpdate,
)


class RepositoryNotFoundError(Exception):
    """リソースが見つからない場合の例外"""

    pass


class RepositoryConflictError(Exception):
    """リソースの整合性エラーの場合の例外"""

    pass


class FolderRepositoryProtocol(Protocol):
    """
    フォルダリポジトリのプロトコル

    SQLite/Cosmos DB双方で同一のメソッド契約を維持します。
    """

    async def get(self, id: str) -> FolderRead:
        """
        IDでフォルダを取得

        Args:
            id: フォルダID

        Returns:
            FolderRead: フォルダ情報

        Raises:
            RepositoryNotFoundError: フォルダが見つからない場合
        """
        ...

    async def list(
        self, user_id: str, *, limit: int = 50, offset: int = 0
    ) -> list[FolderRead]:
        """
        フォルダ一覧を取得

        Args:
            user_id: ユーザーID
            limit: 取得件数上限
            offset: 取得開始位置

        Returns:
            list[FolderRead]: フォルダ一覧
        """
        ...

    async def create(
        self, dto: FolderCreate, *, user_id: str, email: str
    ) -> FolderRead:
        """
        フォルダを作成

        Args:
            dto: フォルダ作成データ
            user_id: ユーザーID
            email: メールアドレス

        Returns:
            FolderRead: 作成されたフォルダ情報
        """
        ...

    async def update(self, id: str, dto: FolderUpdate) -> FolderRead:
        """
        フォルダを更新

        Args:
            id: フォルダID
            dto: フォルダ更新データ

        Returns:
            FolderRead: 更新されたフォルダ情報

        Raises:
            RepositoryNotFoundError: フォルダが見つからない場合
        """
        ...

    async def delete(self, id: str) -> None:
        """
        フォルダを削除

        Args:
            id: フォルダID

        Raises:
            RepositoryNotFoundError: フォルダが見つからない場合
        """
        ...


class ChatThreadRepositoryProtocol(Protocol):
    """
    チャットスレッドリポジトリのプロトコル

    SQLite/Cosmos DB双方で同一のメソッド契約を維持します。
    """

    async def get(self, id: str) -> ChatThreadRead:
        """
        IDでチャットスレッドを取得

        Args:
            id: チャットスレッドID

        Returns:
            ChatThreadRead: チャットスレッド情報

        Raises:
            RepositoryNotFoundError: チャットスレッドが見つからない場合
        """
        ...

    async def list(
        self,
        user_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
        folder_id: str | None = None,
    ) -> list[ChatThreadRead]:
        """
        チャットスレッド一覧を取得

        Args:
            user_id: ユーザーID
            limit: 取得件数上限
            offset: 取得開始位置
            folder_id: フォルダIDでフィルタ（任意）

        Returns:
            list[ChatThreadRead]: チャットスレッド一覧
        """
        ...

    async def create(
        self, dto: ChatThreadCreate, *, user_id: str, email: str
    ) -> ChatThreadRead:
        """
        チャットスレッドを作成

        Args:
            dto: チャットスレッド作成データ
            user_id: ユーザーID
            email: メールアドレス

        Returns:
            ChatThreadRead: 作成されたチャットスレッド情報
        """
        ...

    async def update(self, id: str, dto: ChatThreadUpdate) -> ChatThreadRead:
        """
        チャットスレッドを更新

        Args:
            id: チャットスレッドID
            dto: チャットスレッド更新データ

        Returns:
            ChatThreadRead: 更新されたチャットスレッド情報

        Raises:
            RepositoryNotFoundError: チャットスレッドが見つからない場合
        """
        ...

    async def delete(self, id: str) -> None:
        """
        チャットスレッドを削除

        Args:
            id: チャットスレッドID

        Raises:
            RepositoryNotFoundError: チャットスレッドが見つからない場合
        """
        ...
