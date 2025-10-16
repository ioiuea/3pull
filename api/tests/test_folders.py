"""
フォルダエンドポイントのテスト

このモジュールはフォルダAPIのテストを提供します。
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

TEST_USER_ID = "test-user-123"
TEST_USER_EMAIL = "test@example.com"
AUTH_HEADERS = {"X-User-Id": TEST_USER_ID, "X-User-Email": TEST_USER_EMAIL}


@pytest.mark.asyncio
async def test_create_and_get_folder():
    """
    フォルダ作成と取得のテスト
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_data = {"name": "Test Folder", "type": "chat"}
        create_response = await client.post(
            "/api/v1/folders", json=create_data, headers=AUTH_HEADERS
        )
        assert create_response.status_code == 201
        created_folder = create_response.json()
        assert created_folder["name"] == create_data["name"]
        assert created_folder["type"] == create_data["type"]
        assert "id" in created_folder
        assert "createdAt" in created_folder
        assert created_folder["userId"] == TEST_USER_ID
        assert created_folder["email"] == TEST_USER_EMAIL
        folder_id = created_folder["id"]

        get_response = await client.get(
            f"/api/v1/folders/{folder_id}", headers=AUTH_HEADERS
        )
        assert get_response.status_code == 200
        assert get_response.json() == created_folder


@pytest.mark.asyncio
async def test_update_folder():
    """
    フォルダ更新のテスト
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_data = {"name": "Original Name", "type": "webchat"}
        create_response = await client.post(
            "/api/v1/folders", json=create_data, headers=AUTH_HEADERS
        )
        folder_id = create_response.json()["id"]

        update_data = {"name": "Updated Name"}
        update_response = await client.put(
            f"/api/v1/folders/{folder_id}", json=update_data, headers=AUTH_HEADERS
        )
        assert update_response.status_code == 200
        updated_folder = update_response.json()
        assert updated_folder["name"] == "Updated Name"
        assert updated_folder["type"] == "webchat"


@pytest.mark.asyncio
async def test_list_folders():
    """
    フォルダ一覧取得のテスト
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/api/v1/folders",
            json={"name": "Folder 1", "type": "chat"},
            headers=AUTH_HEADERS,
        )
        await client.post(
            "/api/v1/folders",
            json={"name": "Folder 2", "type": "webchat"},
            headers=AUTH_HEADERS,
        )

        list_response = await client.get(
            "/api/v1/folders?limit=10&offset=0", headers=AUTH_HEADERS
        )
        assert list_response.status_code == 200
        folders = list_response.json()
        assert isinstance(folders, list)
        assert len(folders) >= 2


@pytest.mark.asyncio
async def test_delete_folder():
    """
    フォルダ削除のテスト
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_response = await client.post(
            "/api/v1/folders",
            json={"name": "To Delete", "type": "chat"},
            headers=AUTH_HEADERS,
        )
        folder_id = create_response.json()["id"]

        delete_response = await client.delete(
            f"/api/v1/folders/{folder_id}", headers=AUTH_HEADERS
        )
        assert delete_response.status_code == 200
        assert "message" in delete_response.json()

        get_response = await client.get(
            f"/api/v1/folders/{folder_id}", headers=AUTH_HEADERS
        )
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_get_folder_not_found():
    """
    存在しないフォルダの取得テスト
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/folders/non-existent-id", headers=AUTH_HEADERS
        )
        assert response.status_code == 404
        assert "detail" in response.json()


@pytest.mark.asyncio
async def test_update_folder_not_found():
    """
    存在しないフォルダの更新テスト
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.put(
            "/api/v1/folders/non-existent-id",
            json={"name": "Updated"},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_folder_not_found():
    """
    存在しないフォルダの削除テスト
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.delete(
            "/api/v1/folders/non-existent-id", headers=AUTH_HEADERS
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_user_data_ignored_in_request():
    """
    リクエストボディのユーザーデータが無視されることのテスト
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_data = {
            "name": "Test Folder",
            "type": "chat",
            "userId": "fake-user-id",
            "email": "fake@example.com",
        }
        create_response = await client.post(
            "/api/v1/folders", json=create_data, headers=AUTH_HEADERS
        )
        assert create_response.status_code == 201
        created_folder = create_response.json()
        assert created_folder["userId"] == TEST_USER_ID
        assert created_folder["email"] == TEST_USER_EMAIL
