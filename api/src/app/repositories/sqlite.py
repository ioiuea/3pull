"""
SQLiteリポジトリ実装

このモジュールはSQLiteを使用したリポジトリ実装を提供します。
"""

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import to_api_datetime, utc_now
from app.core.ids import new_uuid
from app.models.schemas import (
    ChatThreadCreate,
    ChatThreadRead,
    ChatThreadUpdate,
    FolderCreate,
    FolderRead,
    FolderUpdate,
)
from app.repositories.base import RepositoryNotFoundError


class SQLiteFolderRepository:
    """
    フォルダのSQLiteリポジトリ実装

    Attributes:
        session: 非同期SQLAlchemyセッション
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        コンストラクタ

        Args:
            session: 非同期SQLAlchemyセッション
        """
        self.session = session

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
        result = await self.session.execute(
            text("SELECT doc FROM folders WHERE id = :id"), {"id": id}
        )
        row = result.scalar_one_or_none()

        if row is None:
            raise RepositoryNotFoundError(f"Folder with id {id} not found")

        doc = json.loads(row)
        return FolderRead(**doc)

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
        result = await self.session.execute(
            text(
                "SELECT doc FROM folders "
                "WHERE json_extract(doc, '$.userId') = :user_id "
                "LIMIT :limit OFFSET :offset"
            ),
            {"user_id": user_id, "limit": limit, "offset": offset},
        )
        rows = result.scalars().all()

        folders = []
        for row in rows:
            doc = json.loads(row)
            folders.append(FolderRead(**doc))

        return folders

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
        folder_id = new_uuid()
        now_utc = utc_now()
        created_at_api = to_api_datetime(now_utc)

        read = FolderRead(
            id=folder_id,
            name=dto.name,
            type=dto.type,
            createdAt=created_at_api,
            userId=user_id,
            email=email,
        )

        doc_json = json.dumps(read.model_dump(by_alias=True), ensure_ascii=False)

        await self.session.execute(
            text(
                "INSERT INTO folders (id, doc, created_at, updated_at) "
                "VALUES (:id, :doc, :created_at, :updated_at)"
            ),
            {
                "id": folder_id,
                "doc": doc_json,
                "created_at": now_utc,
                "updated_at": now_utc,
            },
        )
        await self.session.commit()

        return read

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
        result = await self.session.execute(
            text("SELECT doc FROM folders WHERE id = :id"), {"id": id}
        )
        row = result.scalar_one_or_none()

        if row is None:
            raise RepositoryNotFoundError(f"Folder with id {id} not found")

        current = FolderRead(**json.loads(row))
        update_data = dto.model_dump(exclude_unset=True)
        patched = current.model_copy(update=update_data)

        now_utc = utc_now()
        doc_json = json.dumps(patched.model_dump(by_alias=True), ensure_ascii=False)

        await self.session.execute(
            text(
                "UPDATE folders SET doc = :doc, updated_at = :updated_at WHERE id = :id"
            ),
            {
                "id": id,
                "doc": doc_json,
                "updated_at": now_utc,
            },
        )
        await self.session.commit()

        return patched

    async def delete(self, id: str) -> None:
        """
        フォルダを削除

        Args:
            id: フォルダID

        Raises:
            RepositoryNotFoundError: フォルダが見つからない場合
        """
        result = await self.session.execute(
            text("SELECT id FROM folders WHERE id = :id"), {"id": id}
        )
        row = result.scalar_one_or_none()

        if row is None:
            raise RepositoryNotFoundError(f"Folder with id {id} not found")

        await self.session.execute(
            text("DELETE FROM folders WHERE id = :id"), {"id": id}
        )
        await self.session.commit()


class SQLiteChatThreadRepository:
    """
    チャットスレッドのSQLiteリポジトリ実装

    Attributes:
        session: 非同期SQLAlchemyセッション
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        コンストラクタ

        Args:
            session: 非同期SQLAlchemyセッション
        """
        self.session = session

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
        result = await self.session.execute(
            text("SELECT doc FROM chat_threads WHERE id = :id"), {"id": id}
        )
        row = result.scalar_one_or_none()

        if row is None:
            raise RepositoryNotFoundError(f"ChatThread with id {id} not found")

        doc = json.loads(row)
        return ChatThreadRead(**doc)

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
        if folder_id is not None:
            result = await self.session.execute(
                text(
                    "SELECT doc FROM chat_threads "
                    "WHERE json_extract(doc, '$.userId') = :user_id "
                    "AND json_extract(doc, '$.folderId') = :folder_id "
                    "LIMIT :limit OFFSET :offset"
                ),
                {
                    "user_id": user_id,
                    "folder_id": folder_id,
                    "limit": limit,
                    "offset": offset,
                },
            )
        else:
            result = await self.session.execute(
                text(
                    "SELECT doc FROM chat_threads "
                    "WHERE json_extract(doc, '$.userId') = :user_id "
                    "LIMIT :limit OFFSET :offset"
                ),
                {"user_id": user_id, "limit": limit, "offset": offset},
            )
        rows = result.scalars().all()

        threads = []
        for row in rows:
            doc = json.loads(row)
            threads.append(ChatThreadRead(**doc))

        return threads

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
        thread_id = new_uuid()
        now_utc = utc_now()
        created_at_api = to_api_datetime(now_utc)

        read = ChatThreadRead(
            id=thread_id,
            name=dto.name,
            prompt=dto.prompt,
            temperature=dto.temperature,
            folderId=dto.folder_id,
            isShared=dto.is_shared,
            createdAt=created_at_api,
            sharedAt=dto.shared_at,
            userId=user_id,
            email=email,
        )

        doc_json = json.dumps(read.model_dump(by_alias=True), ensure_ascii=False)

        await self.session.execute(
            text(
                "INSERT INTO chat_threads (id, doc, created_at, updated_at) "
                "VALUES (:id, :doc, :created_at, :updated_at)"
            ),
            {
                "id": thread_id,
                "doc": doc_json,
                "created_at": now_utc,
                "updated_at": now_utc,
            },
        )
        await self.session.commit()

        return read

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
        result = await self.session.execute(
            text("SELECT doc FROM chat_threads WHERE id = :id"), {"id": id}
        )
        row = result.scalar_one_or_none()

        if row is None:
            raise RepositoryNotFoundError(f"ChatThread with id {id} not found")

        current = ChatThreadRead(**json.loads(row))
        update_data = dto.model_dump(exclude_unset=True)
        patched = current.model_copy(update=update_data)

        now_utc = utc_now()
        doc_json = json.dumps(patched.model_dump(by_alias=True), ensure_ascii=False)

        await self.session.execute(
            text(
                "UPDATE chat_threads SET doc = :doc, updated_at = :updated_at "
                "WHERE id = :id"
            ),
            {
                "id": id,
                "doc": doc_json,
                "updated_at": now_utc,
            },
        )
        await self.session.commit()

        return patched

    async def delete(self, id: str) -> None:
        """
        チャットスレッドを削除

        Args:
            id: チャットスレッドID

        Raises:
            RepositoryNotFoundError: チャットスレッドが見つからない場合
        """
        result = await self.session.execute(
            text("SELECT id FROM chat_threads WHERE id = :id"), {"id": id}
        )
        row = result.scalar_one_or_none()

        if row is None:
            raise RepositoryNotFoundError(f"ChatThread with id {id} not found")

        await self.session.execute(
            text("DELETE FROM chat_threads WHERE id = :id"), {"id": id}
        )
        await self.session.commit()
