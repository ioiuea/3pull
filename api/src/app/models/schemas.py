"""
APIスキーマ定義

このモジュールはAPIのリクエスト/レスポンスのスキーマを定義します。
"""

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """
    ヘルスチェックレスポンス

    Attributes:
        status: ステータス（例: "healthy"）
        message: メッセージ
    """

    status: str = Field(..., description="ステータス")
    message: str = Field(..., description="メッセージ")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "healthy",
                    "message": "アプリケーションは正常に動作しています",
                }
            ]
        }
    }


class ItemBase(BaseModel):
    """
    アイテムの基本スキーマ

    Attributes:
        name: アイテム名
        description: アイテムの説明
        price: アイテムの価格
    """

    name: str = Field(..., min_length=1, max_length=100, description="アイテム名")
    description: str | None = Field(None, max_length=500, description="アイテムの説明")
    price: float = Field(..., gt=0, description="アイテムの価格")


class ItemCreate(ItemBase):
    """
    アイテム作成リクエスト

    ItemBaseを継承し、作成時に必要なフィールドを定義します。
    """

    pass


class ItemResponse(ItemBase):
    """
    アイテムレスポンス

    Attributes:
        id: アイテムID
        name: アイテム名
        description: アイテムの説明
        price: アイテムの価格
    """

    id: int = Field(..., description="アイテムID")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "name": "サンプルアイテム",
                    "description": "これはサンプルアイテムです",
                    "price": 1000.0,
                }
            ]
        }
    }


class FolderCreate(BaseModel):
    """
    フォルダ作成リクエスト

    Attributes:
        name: フォルダ名
        type: フォルダタイプ
    """

    name: str = Field(..., min_length=1, description="フォルダ名")
    type: str = Field(..., description="フォルダタイプ")


class FolderUpdate(BaseModel):
    """
    フォルダ更新リクエスト

    Attributes:
        name: フォルダ名（任意）
        type: フォルダタイプ（任意）
    """

    name: str | None = Field(None, min_length=1, description="フォルダ名")
    type: str | None = Field(None, description="フォルダタイプ")


class FolderRead(BaseModel):
    """
    フォルダレスポンス

    Attributes:
        id: フォルダID
        name: フォルダ名
        type: フォルダタイプ
        created_at: 作成日時
        user_id: ユーザーID
        email: メールアドレス
    """

    id: str = Field(..., description="フォルダID")
    name: str = Field(..., description="フォルダ名")
    type: str = Field(..., description="フォルダタイプ")
    created_at: str = Field(..., alias="createdAt", description="作成日時")
    user_id: str = Field(..., alias="userId", description="ユーザーID")
    email: str = Field(..., description="メールアドレス")

    model_config = ConfigDict(populate_by_name=True)


class ChatThreadCreate(BaseModel):
    """
    チャットスレッド作成リクエスト

    Attributes:
        name: スレッド名
        prompt: プロンプト
        temperature: 温度パラメータ
        folder_id: 所属フォルダID
        is_shared: 共有フラグ（任意、デフォルトFalse）
        shared_at: 共有日時（任意）
    """

    name: str = Field(..., min_length=1, description="スレッド名")
    prompt: str = Field(..., description="プロンプト")
    temperature: float = Field(..., ge=0.0, le=1.0, description="温度パラメータ")
    folder_id: str = Field(..., alias="folderId", description="所属フォルダID")
    is_shared: bool = Field(False, alias="isShared", description="共有フラグ")
    shared_at: str | None = Field(None, alias="sharedAt", description="共有日時")

    model_config = ConfigDict(populate_by_name=True)


class ChatThreadUpdate(BaseModel):
    """
    チャットスレッド更新リクエスト

    Attributes:
        name: スレッド名（任意）
        prompt: プロンプト（任意）
        temperature: 温度パラメータ（任意）
        folder_id: 所属フォルダID（任意）
        is_shared: 共有フラグ（任意）
        shared_at: 共有日時（任意）
    """

    name: str | None = Field(None, min_length=1, description="スレッド名")
    prompt: str | None = Field(None, description="プロンプト")
    temperature: float | None = Field(
        None, ge=0.0, le=1.0, description="温度パラメータ"
    )
    folder_id: str | None = Field(None, alias="folderId", description="所属フォルダID")
    is_shared: bool | None = Field(None, alias="isShared", description="共有フラグ")
    shared_at: str | None = Field(None, alias="sharedAt", description="共有日時")

    model_config = ConfigDict(populate_by_name=True)


class ChatThreadRead(BaseModel):
    """
    チャットスレッドレスポンス

    Attributes:
        id: スレッドID
        name: スレッド名
        prompt: プロンプト
        temperature: 温度パラメータ
        folder_id: 所属フォルダID
        is_shared: 共有フラグ
        created_at: 作成日時
        shared_at: 共有日時（null許容）
        user_id: ユーザーID
        email: メールアドレス
    """

    id: str = Field(..., description="スレッドID")
    name: str = Field(..., description="スレッド名")
    prompt: str = Field(..., description="プロンプト")
    temperature: float = Field(..., description="温度パラメータ")
    folder_id: str = Field(..., alias="folderId", description="所属フォルダID")
    is_shared: bool = Field(..., alias="isShared", description="共有フラグ")
    created_at: str = Field(..., alias="createdAt", description="作成日時")
    shared_at: str | None = Field(None, alias="sharedAt", description="共有日時")
    user_id: str = Field(..., alias="userId", description="ユーザーID")
    email: str = Field(..., description="メールアドレス")

    model_config = ConfigDict(populate_by_name=True)
