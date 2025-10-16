"""
チャットスレッドエンドポイントのテスト

このモジュールはチャットスレッドAPIのテストを提供します。
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

TEST_USER_ID = "test-user-123"
TEST_USER_EMAIL = "test@example.com"
AUTH_HEADERS = {"X-User-Id": TEST_USER_ID, "X-User-Email": TEST_USER_EMAIL}


@pytest.mark.asyncio
async def test_create_and_get_chat_thread():
    """
    チャットスレッド作成と取得のテスト
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder_response = await client.post(
            "/api/v1/folders",
            json={"name": "Test Folder", "type": "webchat"},
            headers=AUTH_HEADERS,
        )
        folder_id = folder_response.json()["id"]

        create_data = {
            "name": "Test Thread",
            "prompt": "You are a helpful assistant",
            "temperature": 0.7,
            "folderId": folder_id,
            "isShared": False,
        }
        create_response = await client.post(
            "/api/v1/chat-threads", json=create_data, headers=AUTH_HEADERS
        )
        assert create_response.status_code == 201
        created_thread = create_response.json()
        assert created_thread["name"] == create_data["name"]
        assert created_thread["prompt"] == create_data["prompt"]
        assert created_thread["temperature"] == create_data["temperature"]
        assert created_thread["folderId"] == folder_id
        assert created_thread["isShared"] is False
        assert "id" in created_thread
        assert "createdAt" in created_thread
        assert created_thread["userId"] == TEST_USER_ID
        assert created_thread["email"] == TEST_USER_EMAIL
        thread_id = created_thread["id"]

        get_response = await client.get(
            f"/api/v1/chat-threads/{thread_id}", headers=AUTH_HEADERS
        )
        assert get_response.status_code == 200
        assert get_response.json() == created_thread


@pytest.mark.asyncio
async def test_update_chat_thread():
    """
    チャットスレッド更新のテスト
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder_response = await client.post(
            "/api/v1/folders",
            json={"name": "Test Folder", "type": "webchat"},
            headers=AUTH_HEADERS,
        )
        folder_id = folder_response.json()["id"]

        create_data = {
            "name": "Original Thread",
            "prompt": "Original prompt",
            "temperature": 0.5,
            "folderId": folder_id,
            "isShared": False,
        }
        create_response = await client.post(
            "/api/v1/chat-threads", json=create_data, headers=AUTH_HEADERS
        )
        thread_id = create_response.json()["id"]

        update_data = {"temperature": 0.9, "name": "Updated Thread"}
        update_response = await client.put(
            f"/api/v1/chat-threads/{thread_id}", json=update_data, headers=AUTH_HEADERS
        )
        assert update_response.status_code == 200
        updated_thread = update_response.json()
        assert updated_thread["temperature"] == 0.9
        assert updated_thread["name"] == "Updated Thread"
        assert updated_thread["prompt"] == "Original prompt"


@pytest.mark.asyncio
async def test_list_chat_threads_with_folder_filter():
    """
    チャットスレッド一覧取得（フォルダフィルタ付き）のテスト
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder1_response = await client.post(
            "/api/v1/folders",
            json={"name": "Folder 1", "type": "webchat"},
            headers=AUTH_HEADERS,
        )
        folder1_id = folder1_response.json()["id"]

        folder2_response = await client.post(
            "/api/v1/folders",
            json={"name": "Folder 2", "type": "chat"},
            headers=AUTH_HEADERS,
        )
        folder2_id = folder2_response.json()["id"]

        await client.post(
            "/api/v1/chat-threads",
            json={
                "name": "Thread in Folder 1",
                "prompt": "Test",
                "temperature": 0.7,
                "folderId": folder1_id,
            },
            headers=AUTH_HEADERS,
        )
        await client.post(
            "/api/v1/chat-threads",
            json={
                "name": "Thread in Folder 2",
                "prompt": "Test",
                "temperature": 0.7,
                "folderId": folder2_id,
            },
            headers=AUTH_HEADERS,
        )

        list_response = await client.get(
            f"/api/v1/chat-threads?folderId={folder1_id}&limit=10", headers=AUTH_HEADERS
        )
        assert list_response.status_code == 200
        threads = list_response.json()
        assert isinstance(threads, list)
        assert all(thread["folderId"] == folder1_id for thread in threads)


@pytest.mark.asyncio
async def test_delete_chat_thread():
    """
    チャットスレッド削除のテスト
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder_response = await client.post(
            "/api/v1/folders",
            json={"name": "Test Folder", "type": "webchat"},
            headers=AUTH_HEADERS,
        )
        folder_id = folder_response.json()["id"]

        create_response = await client.post(
            "/api/v1/chat-threads",
            json={
                "name": "To Delete",
                "prompt": "Test",
                "temperature": 0.7,
                "folderId": folder_id,
            },
            headers=AUTH_HEADERS,
        )
        thread_id = create_response.json()["id"]

        delete_response = await client.delete(
            f"/api/v1/chat-threads/{thread_id}", headers=AUTH_HEADERS
        )
        assert delete_response.status_code == 200
        assert "message" in delete_response.json()

        get_response = await client.get(
            f"/api/v1/chat-threads/{thread_id}", headers=AUTH_HEADERS
        )
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_temperature_validation():
    """
    temperature範囲バリデーションのテスト
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        folder_response = await client.post(
            "/api/v1/folders",
            json={"name": "Test Folder", "type": "webchat"},
            headers=AUTH_HEADERS,
        )
        folder_id = folder_response.json()["id"]

        invalid_data = {
            "name": "Invalid Thread",
            "prompt": "Test",
            "temperature": 1.5,
            "folderId": folder_id,
        }
        response = await client.post(
            "/api/v1/chat-threads", json=invalid_data, headers=AUTH_HEADERS
        )
        assert response.status_code == 422
