"""
エンドポイントのテスト

このモジュールはAPIエンドポイントのテストを提供します。
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root() -> None:
    """
    ルートエンドポイントのテスト
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data


def test_health_check() -> None:
    """
    ヘルスチェックエンドポイントのテスト
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "message" in data


def test_get_items_empty() -> None:
    """
    アイテム一覧取得のテスト（空の場合）
    """
    response = client.get("/api/v1/items")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_get_item() -> None:
    """
    アイテム作成と取得のテスト
    """
    create_data = {
        "name": "テストアイテム",
        "description": "これはテスト用のアイテムです",
        "price": 1000.0,
    }
    create_response = client.post("/api/v1/items", json=create_data)
    assert create_response.status_code == 201
    created_item = create_response.json()
    assert created_item["name"] == create_data["name"]
    assert created_item["price"] == create_data["price"]
    item_id = created_item["id"]

    get_response = client.get(f"/api/v1/items/{item_id}")
    assert get_response.status_code == 200
    assert get_response.json() == created_item


def test_get_item_not_found() -> None:
    """
    存在しないアイテムの取得テスト
    """
    response = client.get("/api/v1/items/99999")
    assert response.status_code == 404
