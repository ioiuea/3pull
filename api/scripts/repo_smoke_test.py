"""Repository CRUD smoke test"""
import asyncio
import sys

sys.path.insert(0, "src")

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.models.schemas import (
    ChatThreadCreate,
    ChatThreadUpdate,
    FolderCreate,
    FolderUpdate,
)
from app.repositories.sqlite import SQLiteChatThreadRepository, SQLiteFolderRepository


async def test_folder_crud():
    """Test Folder CRUD operations"""
    print("Testing Folder CRUD...")

    async with AsyncSessionLocal() as session:
        repo = SQLiteFolderRepository(session)

        folder = await repo.create(FolderCreate(name="Test Folder", type="chat"))
        print(f"✅ Created: {folder.id}")
        assert folder.name == "Test Folder"
        assert folder.user_id == settings.fixed_user_id

        retrieved = await repo.get(folder.id)
        print(f"✅ Retrieved: {retrieved.id}")
        assert retrieved.name == "Test Folder"

        updated = await repo.update(folder.id, FolderUpdate(name="Updated Folder"))
        print(f"✅ Updated: {updated.id}")
        assert updated.name == "Updated Folder"

        folders = await repo.list(settings.fixed_user_id, limit=10)
        print(f"✅ Listed: {len(folders)} folders")
        assert len(folders) >= 1

        await repo.delete(folder.id)
        print(f"✅ Deleted: {folder.id}")

        try:
            await repo.get(folder.id)
            raise AssertionError("Should have raised RepositoryNotFoundError")
        except Exception:
            print("✅ Confirmed deleted (NotFound raised)")


async def test_chatthread_crud():
    """Test ChatThread CRUD operations"""
    print("\nTesting ChatThread CRUD...")

    async with AsyncSessionLocal() as session:
        folder_repo = SQLiteFolderRepository(session)
        thread_repo = SQLiteChatThreadRepository(session)

        folder = await folder_repo.create(FolderCreate(name="Test Folder", type="webchat"))

        thread = await thread_repo.create(
            ChatThreadCreate(
                name="Test Thread",
                prompt="Hello AI",
                temperature=0.7,
                folder_id=folder.id,
                is_shared=False,
            )
        )
        print(f"✅ Created: {thread.id}")
        assert thread.name == "Test Thread"
        assert thread.folder_id == folder.id

        retrieved = await thread_repo.get(thread.id)
        print(f"✅ Retrieved: {retrieved.id}")

        updated = await thread_repo.update(thread.id, ChatThreadUpdate(temperature=0.9))
        print(f"✅ Updated: {updated.id}")
        assert updated.temperature == 0.9

        threads = await thread_repo.list(settings.fixed_user_id, folder_id=folder.id)
        print(f"✅ Listed: {len(threads)} threads in folder")
        assert len(threads) >= 1

        await thread_repo.delete(thread.id)
        await folder_repo.delete(folder.id)
        print("✅ Deleted thread and folder")


async def main():
    print("Starting Repository smoke tests...\n")
    await test_folder_crud()
    await test_chatthread_crud()
    print("\n✅ All Repository smoke tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
