# データ永続化アーキテクチャ設計

## 概要

本ドキュメントは、FastAPI バックエンドのデータ永続化アーキテクチャ全体を定義します。
ローカル開発環境では**SQLite**、本番環境では**Azure Cosmos DB**を採用し、環境変数`DB_BACKEND`で切り替える構成です。

このアーキテクチャは 6 つのステップで段階的に実装され、本ドキュメントで定義したルール・構造・方針は全ステップで共通して参照されます。

---

## 全 Step の流れ

| Step | 内容                                       | 主な成果物                                              |
| ---- | ------------------------------------------ | ------------------------------------------------------- |
| 0    | アーキテクチャ設計・共通ルール定義         | `.env.example`, フォルダ構成, `docs/architecture.md`    |
| 1    | SQLite 基盤構築 (Alembic 適用)             | `core/db.py`, Alembic スクリプト                        |
| 2    | Pydantic スキーマ定義 & UUID/日時 ポリシー | `models/schemas.py`, `core/ids.py`, `core/clock.py`     |
| 3    | Repository 抽象化 & SQLite 実装            | `repositories/base.py`, `repositories/sqlite.py`        |
| 4    | REST API 実装 (folders/chatThreads)        | `routers/v1/folders.py`, `routers/v1/chat_threads.py`   |
| 5    | Azure Cosmos DB 実装                       | `repositories/cosmos.py`, `core/db.py` 更新             |
| 6    | Docs & 型生成 連携 (Next.js 側)            | `docs/architecture.md` 更新, `web/utils/types/api.d.ts` |

---

## データ構造

### folders

```json
{
  "id": "uuid",
  "name": "string",
  "type": "string",
  "createdAt": "2025-09-30T18:55:08+09:00",
  "userId": "string",
  "email": "string"
}
```

**フィールド説明:**

- `id`: フォルダの一意識別子（UUID v7 推奨）
- `name`: フォルダ名
- `type`: フォルダタイプ
- `createdAt`: 作成日時（ISO 8601 形式、タイムゾーンオフセット付き）
- `userId`: ユーザー ID（現在は固定値、将来的に認証と連携）
- `email`: ユーザーメールアドレス（現在は固定値）

### chatThreads

```json
{
  "id": "uuid",
  "name": "string",
  "prompt": "string",
  "temperature": 0.7,
  "folderId": "uuid",
  "isShared": false,
  "createdAt": "2025-02-08T07:15:11+09:00",
  "sharedAt": "2025-03-18T10:18:38+09:00",
  "userId": "string",
  "email": "string"
}
```

**フィールド説明:**

- `id`: チャットスレッドの一意識別子（UUID v7 推奨）
- `name`: チャットスレッド名
- `prompt`: プロンプト内容
- `temperature`: 温度パラメータ（0.0-1.0）
- `folderId`: 所属フォルダの ID
- `isShared`: 共有フラグ
- `createdAt`: 作成日時（ISO 8601 形式、タイムゾーンオフセット付き）
- `sharedAt`: 共有日時（共有時のみ設定）
- `userId`: ユーザー ID（現在は固定値）
- `email`: ユーザーメールアドレス（現在は固定値）

---

## 共通ルール（全 Step に適用）

### ユーザー情報の取扱方針

認証機能が未実装のため、現在は以下の固定値を使用します：

- **userId**: `12345678-1234-1234-1234-123456789000`
- **email**: `test@3pull.com`

**実装ポリシー:**

1. リクエストボディで`userId`/`email`を受け取らず、サーバー側で自動付与
2. データベース保存時は常にこれらの固定値を埋め込み、null を許可しない
3. 将来的に NextAuth や Entra ID と連携した際は、JWT の`sub`を`users.id`に対応付ける

### 日時・ID ポリシー

**ID 生成:**

- UUID（v7 推奨）をサーバー側で採番
- クライアントからの ID 指定は受け付けない
- 時系列順でソート可能な UUID v7 を優先的に使用

**日時管理:**

- データベースには**UTC**で保存
- API 出力時は`APP_TIMEZONE`環境変数で指定されたタイムゾーンのオフセット付き ISO 8601 形式に変換
- 例: `2025-09-30T18:55:08+09:00` (Asia/Tokyo の場合)

---

## フォルダ構成

```
api/
├── pyproject.toml          # 依存関係定義
├── Dockerfile              # コンテナイメージ定義
├── .env.example            # 環境変数テンプレート
├── uv.lock                 # 依存関係ロックファイル
├── alembic/                # データベースマイグレーション (Step 1で作成)
│   ├── versions/           # マイグレーションスクリプト
│   └── env.py              # Alembic設定
└── src/
    └── app/
        ├── main.py                    # FastAPIアプリケーションエントリーポイント
        ├── core/
        │   ├── config.py              # アプリケーション設定
        │   ├── db.py                  # データベース接続管理 (Step 1で作成)
        │   ├── ids.py                 # UUID生成ユーティリティ (Step 2で作成)
        │   └── clock.py               # 日時ユーティリティ (Step 2で作成)
        ├── models/
        │   └── schemas.py             # Pydanticスキーマ定義 (Step 2で拡張)
        ├── repositories/              # Repository層 (Step 3で作成)
        │   ├── base.py                # 抽象Repositoryインターフェース
        │   ├── sqlite.py              # SQLite実装
        │   └── cosmos.py              # Azure Cosmos DB実装 (Step 5で作成)
        ├── routers/
        │   └── v1/
        │       ├── folders.py         # フォルダAPI (Step 4で作成)
        │       └── chat_threads.py    # チャットスレッドAPI (Step 4で作成)
        └── tests/
            ├── test_folders.py        # フォルダAPIテスト (Step 4で作成)
            └── test_chat_threads.py   # チャットスレッドAPIテスト (Step 4で作成)
```

---

## 環境変数

### .env.example

```bash
# アプリケーション設定
APP_ENV=local
APP_TIMEZONE=Asia/Tokyo

# データベース設定
DB_BACKEND=sqlite
DB_URI=sqlite+aiosqlite:///./data/app.db

# Azure Cosmos DB設定（本番環境用）
COSMOS_URI=
COSMOS_KEY=
COSMOS_DB_NAME=3pull
COSMOS_CONTAINER_FOLDERS=folders
COSMOS_CONTAINER_THREADS=chatThreads

# 固定ユーザー情報（認証実装まで使用）
FIXED_USER_ID=12345678-1234-1234-1234-123456789000
FIXED_EMAIL=test@3pull.com
```

### 環境変数説明

| 変数名                     | 説明                                 | デフォルト値                           | 環境          |
| -------------------------- | ------------------------------------ | -------------------------------------- | ------------- |
| `APP_ENV`                  | 実行環境 (local/staging/production)  | `local`                                | 全環境        |
| `APP_TIMEZONE`             | アプリケーションのタイムゾーン       | `Asia/Tokyo`                           | 全環境        |
| `DB_BACKEND`               | 使用するデータベース (sqlite/cosmos) | `sqlite`                               | 全環境        |
| `DB_URI`                   | SQLite 接続 URI                      | `sqlite+aiosqlite:///./data/app.db`    | local/staging |
| `COSMOS_URI`               | Azure Cosmos DB エンドポイント URI   | -                                      | production    |
| `COSMOS_KEY`               | Azure Cosmos DB アクセスキー         | -                                      | production    |
| `COSMOS_DB_NAME`           | Cosmos DB データベース名             | `3pull`                                | production    |
| `COSMOS_CONTAINER_FOLDERS` | folders コンテナ名                   | `folders`                              | production    |
| `COSMOS_CONTAINER_THREADS` | chatThreads コンテナ名               | `chatThreads`                          | production    |
| `FIXED_USER_ID`            | 固定ユーザー ID                      | `12345678-1234-1234-1234-123456789000` | 認証未実装時  |
| `FIXED_EMAIL`              | 固定メールアドレス                   | `test@3pull.com`                       | 認証未実装時  |

---

## 実装ステップ詳細

### Step 0: アーキテクチャ設計・共通ルール定義 ✅

**目的**: 全 Step で参照する共通仕様・ルール・フォルダ構成を定義する

**成果物**:

- `.env.example`: 全環境変数の定義
- `docs/architecture.md`: 本アーキテクチャドキュメント
- `core/config.py`: 拡張された設定クラス

**完了条件**:

- 後続 Step で参照する全ての仕様が明文化されている
- 新規開発者が本ドキュメントだけで開発準備を完了できる

### Step 1: SQLite 基盤構築 (Alembic 適用) ✅

**目的**: ローカル開発用の SQLite 基盤とマイグレーション管理を構築

**主な実装**:

- `core/db.py`: データベース接続管理
- `alembic/`: マイグレーション管理
- folders/chatThreads テーブルのマイグレーションスクリプト

**技術スタック**:

- SQLAlchemy (非同期 ORM)
- Alembic (マイグレーション)
- aiosqlite (非同期 SQLite ドライバ)

**完了条件**:

- ✅ `alembic upgrade head` が正常終了
- ✅ `data/app.db` に folders/chat_threads テーブルが作成される
- ✅ WAL モードと外部キー制約が有効化される
- ✅ doc カラムに JSON 文字列を格納可能

**実装手順**:

1. 依存関係追加: `sqlalchemy[asyncio]`, `aiosqlite`, `alembic`
2. `core/db.py`実装: async engine、PRAGMA 設定、sessionmaker
3. Alembic 初期化: `alembic init alembic`
4. `alembic/env.py`を async 対応に修正
5. 初回マイグレーション作成: `alembic revision -m "init sqlite"`
6. マイグレーション適用: `alembic upgrade head`

**マイグレーション実行コマンド**:

```bash
cd /home/ubuntu/repos/3pull-devin/api
uv run alembic upgrade head
```

**既知の制約**:

- `doc`カラムは TEXT 型（JSON1 拡張は使用しない、互換性重視）
- JSON のシリアライズ/デシリアライズは Pydantic で実施
- 将来的な検索最適化が必要な場合は user_id 等の補助列追加を検討

### Step 2: Pydantic スキーマ定義 & UUID/日時 ポリシー ✅

**目的**: API スキーマと ID/日時ユーティリティを実装

**主な実装**:

- `models/schemas.py`: Folder/ChatThread スキーマ（Create/Update/Read）
- `core/ids.py`: UUID 生成ユーティリティ（v4 使用）
- `core/clock.py`: タイムゾーン対応日時処理

**技術スタック**:

- Pydantic v2（BaseModel、ConfigDict、Field）
- Python 標準ライブラリ（uuid、datetime、zoneinfo）

**完了条件**:

- ✅ `schemas.py`に Folders/ChatThreads の Create/Update/Read 定義
- ✅ `ids.py`に UUIDv4 生成関数（v7 未対応環境のため v4 使用）
- ✅ `clock.py`に UTC 保存・API 出力 ISO8601(+TZ)変換関数
- ✅ Body に`userId`/`email`を含めない設計（サーバ側付与）
- ✅ `createdAt`サーバ自動付与、`sharedAt`は null 許容
- ✅ Pydantic バリデーション（型/範囲/必須）が機能

**実装詳細**:

1. **UUID 生成（`core/ids.py`）**

   - `new_uuid()`: UUIDv4 を生成して文字列で返す
   - Python 3.13 環境でも UUIDv7 未サポートのため v4 を使用
   - 将来的な Python 3.14+への移行時に v7 への切り替えを検討

2. **日時処理（`core/clock.py`）**

   - `utc_now()`: 現在の UTC datetime を返す
   - `to_api_datetime(dt_utc)`: UTC→APP_TIMEZONE 変換し ISO8601 文字列化
   - DB 保存は常に UTC、API 出力時に`to_api_datetime`で整形

3. **Pydantic スキーマ（`models/schemas.py`）**
   - **入力（Create/Update）と出力（Read）を分離**
   - **Create**: クライアント送信データ（id、userId、email 等は含まない）
   - **Update**: 任意項目の部分更新（全フィールド Optional）
   - **Read**: 完全な JSON レスポンス（サーバ付与フィールド含む）
   - `ConfigDict(populate_by_name=True)`でエイリアス対応
   - `temperature`範囲バリデーション（ge=0.0, le=1.0）
   - `sharedAt`は Optional（未共有時は null）

**スキーマ構造**:

Folders:

```json
{
  "id": "uuid",
  "name": "string",
  "type": "string",
  "createdAt": "2025-09-30T18:55:08+09:00",
  "userId": "string",
  "email": "string"
}
```

ChatThreads:

```json
{
  "id": "uuid",
  "name": "string",
  "prompt": "string",
  "temperature": 0.7,
  "folderId": "uuid",
  "isShared": false,
  "createdAt": "2025-02-08T07:15:11+09:00",
  "sharedAt": "2025-03-18T10:18:38+09:00",
  "userId": "string",
  "email": "string"
}
```

**使用例**:

```python
from app.core.ids import new_uuid
from app.core.clock import utc_now, to_api_datetime
from app.models.schemas import FolderCreate, FolderRead

# UUID生成
folder_id = new_uuid()  # "579525b3-1d87-4055-98d1-37a54ee8f52f"

# 日時処理
now = utc_now()  # datetime(2025, 10, 16, 5, 30, 0, tzinfo=UTC)
api_time = to_api_datetime(now)  # "2025-10-16T14:30:00+09:00"

# スキーマ利用
create_data = FolderCreate(name="My Folder", type="chat")
read_data = FolderRead(
    id=folder_id,
    name=create_data.name,
    type=create_data.type,
    createdAt=api_time,
    userId="12345678-1234-1234-1234-123456789000",
    email="test@3pull.com"
)
json_doc = read_data.model_dump(by_alias=True)  # API/DB保存用JSON
```

**既知の制約**:

- UUIDv7 は非対応（Python 3.13 環境）。Python 3.14+移行時に検討
- `doc`カラムに JSON 文字列として保存（`json.dumps(read_data.model_dump(by_alias=True))`）
- スキーマ変更は後続 Step（Repository/Router）へ波及するため PR で周知必要

### Step 3: Repository 抽象化 & SQLite 実装 ✅

**目的**: データアクセス層を抽象化し、SQLite 実装を提供

**主な実装**:

- `repositories/base.py`: Repository 抽象インターフェース（Protocol）
- `repositories/sqlite.py`: SQLite 実装（SQLAlchemy Async）
- `api/deps.py`: DI（Dependency Injection）ファクトリ関数
- CRUD 操作の実装（Create, Read, Update, Delete）

**設計パターン**:

- Repository パターン（Protocol-based 抽象化）
- Dependency Injection（FastAPI Depends）

**完了条件**:

- ✅ `base.py`に FolderRepositoryProtocol/ChatThreadRepositoryProtocol 定義
- ✅ カスタム例外クラス（RepositoryNotFoundError 等）定義
- ✅ `sqlite.py`に SQLite CRUD 実装（get/list/create/update/delete）
- ✅ create 時に id/createdAt/userId/email をサーバ側自動付与
- ✅ update 時に updatedAt（DB 側 UTC）を更新
- ✅ list が userId スコープで動作、chatThreads は folderId フィルタ対応
- ✅ 返却値は常に Pydantic Read モデル
- ✅ `api/deps.py`で Depends による Repository 注入が可能
- ✅ NotFound 等の例外が Repository 層で処理可能

**実装詳細**:

1. **抽象インターフェース（`repositories/base.py`）**

   - `FolderRepositoryProtocol`: フォルダリポジトリの抽象定義
   - `ChatThreadRepositoryProtocol`: チャットスレッドリポジトリの抽象定義
   - `RepositoryNotFoundError`: リソースが見つからない場合の例外
   - `RepositoryConflictError`: 整合性エラーの場合の例外
   - Protocol を使用した構造的サブタイピング（柔軟性重視）

2. **SQLite 実装（`repositories/sqlite.py`）**

   - `SQLiteFolderRepository`: フォルダの CRUD 実装
   - `SQLiteChatThreadRepository`: チャットスレッドの CRUD 実装
   - SQLAlchemy Async セッションで DB 操作
   - `doc`カラムに JSON 文字列を格納（`json.dumps(read.model_dump(by_alias=True))`）
   - `created_at`/`updated_at`は UTC datetime で保存
   - list()は Python 側で userId/folderId フィルタリング（TEXT load 方式）

3. **DI（`api/deps.py`）**
   - `get_folder_repo()`: フォルダリポジトリを返す DI 関数
   - `get_chatthread_repo()`: チャットスレッドリポジトリを返す DI 関数
   - `DB_BACKEND`環境変数で sqlite/cosmos 切り替え
   - Step 5 で Cosmos DB 実装追加予定

**Repository 使用例**:

```python
from fastapi import APIRouter, Depends
from app.api.deps import get_folder_repo
from app.repositories.base import FolderRepositoryProtocol
from app.models.schemas import FolderCreate, FolderRead

router = APIRouter()

@router.post("/folders", response_model=FolderRead)
async def create_folder(
    dto: FolderCreate,
    repo: FolderRepositoryProtocol = Depends(get_folder_repo),
) -> FolderRead:
    return await repo.create(dto)

@router.get("/folders/{folder_id}", response_model=FolderRead)
async def get_folder(
    folder_id: str,
    repo: FolderRepositoryProtocol = Depends(get_folder_repo),
) -> FolderRead:
    return await repo.get(folder_id)
```

**例外ハンドリング**:

```python
from fastapi import HTTPException, status
from app.repositories.base import RepositoryNotFoundError

try:
    folder = await repo.get(folder_id)
except RepositoryNotFoundError:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Folder {folder_id} not found"
    )
```

**既知の制約**:

- list()のフィルタリングは Python 側で実施（TEXT load 方式）
- 性能最適化が必要な場合は userId 等の補助列追加を検討（別 Issue）
- Cosmos DB 実装は Step 5 で追加予定

### Step 4: REST API 実装（folders / chatThreads）✅

**目的**: FastAPI で folders と chatThreads の CRUD REST API を実装

**主な実装**:

- `routers/v1/folders.py`: フォルダ CRUD エンドポイント
- `routers/v1/chat_threads.py`: チャットスレッド CRUD エンドポイント
- `main.py`: CORS 設定更新（localhost:3000 対応）
- `tests/test_folders.py` / `tests/test_chat_threads.py`: 非同期 API テスト

**完了条件**:

- ✅ 全エンドポイント実装（GET/POST/PUT/DELETE）
- ✅ POST は 201、GET/PUT/DELETE は 200 を返却
- ✅ Body に userId/email を受け取らずサーバー側で固定値付与
- ✅ RepositoryNotFoundError → HTTPException(404) 変換
- ✅ temperature 範囲バリデーション（0.0〜1.0）が有効
- ✅ OpenAPI（/openapi.json）に反映
- ✅ httpx.AsyncClient による非同期テスト実装
- ✅ CORS を localhost:3000 に更新

**エンドポイント一覧**:

#### Folders エンドポイント

| Method | Path                   | 説明                              | ステータス |
| ------ | ---------------------- | --------------------------------- | ---------- |
| GET    | `/api/v1/folders`      | フォルダ一覧取得（limit, offset） | 200        |
| GET    | `/api/v1/folders/{id}` | フォルダ詳細取得                  | 200, 404   |
| POST   | `/api/v1/folders`      | フォルダ作成（name, type）        | 201        |
| PUT    | `/api/v1/folders/{id}` | フォルダ更新（name?, type?）      | 200, 404   |
| DELETE | `/api/v1/folders/{id}` | フォルダ削除                      | 200, 404   |

#### ChatThreads エンドポイント

| Method | Path                        | 説明                                         | ステータス    |
| ------ | --------------------------- | -------------------------------------------- | ------------- |
| GET    | `/api/v1/chat-threads`      | スレッド一覧取得（limit, offset, folderId?） | 200           |
| GET    | `/api/v1/chat-threads/{id}` | スレッド詳細取得                             | 200, 404      |
| POST   | `/api/v1/chat-threads`      | スレッド作成                                 | 201, 422      |
| PUT    | `/api/v1/chat-threads/{id}` | スレッド更新                                 | 200, 404, 422 |
| DELETE | `/api/v1/chat-threads/{id}` | スレッド削除                                 | 200, 404      |

**リクエスト例**:

```bash
# フォルダ作成 (important-comment)
curl -X POST http://localhost:8000/api/v1/folders \
  -H "Content-Type: application/json" \
  -d '{"name":"My Folder","type":"chat"}'

# スレッド作成 (important-comment)
curl -X POST http://localhost:8000/api/v1/chat-threads \
  -H "Content-Type: application/json" \
  -d '{
    "name":"First Thread",
    "prompt":"You are helpful",
    "temperature":0.7,
    "folderId":"<folder-uuid>",
    "isShared":false
  }'
```

**CORS 設定**:

- ローカル開発用: `["http://localhost:3000", "http://127.0.0.1:3000"]`
- 本番環境では ENV で厳格化予定

**テスト戦略**:

- httpx.AsyncClient で非同期テスト
- CRUD 完全サイクルテスト（作成 → 取得 → 更新 → 削除）
- エラーケーステスト（404, 422）
- ユーザーデータ無視テスト（固定値付与確認）
- temperature バリデーションテスト

**実装詳細**:

1. **ルータ構成**

   - `folders.py`: APIRouter(prefix="/folders", tags=["folders"])
   - `chat_threads.py`: APIRouter(prefix="/chat-threads", tags=["chatThreads"])
   - DI: `Depends(get_folder_repo)` / `Depends(get_chatthread_repo)`

2. **例外ハンドリング**

   ```python
   try:
       item = await repo.get(id)
   except RepositoryNotFoundError:
       raise HTTPException(status_code=404, detail=f"Resource {id} not found")
   ```

3. **クエリパラメータ**

   - limit: Query(50, ge=1, le=200) - デフォルト 50、最大 200
   - offset: Query(0, ge=0) - デフォルト 0
   - folderId: Query(None, alias="folderId") - 任意フィルタ

4. **レスポンスモデル**
   - すべてのエンドポイントで `response_model` 指定
   - Pydantic スキーマで自動バリデーション
   - by_alias=True で camelCase JSON 出力

**既知の制約**:

- 認証なし（固定ユーザー）
- CORS は本番環境で厳格化必要
- Step 5 で Cosmos DB 切替実装予定

### Step 5: Azure Cosmos DB 実装

**目的**: 本番環境用の Azure Cosmos DB 実装を追加

**主な実装**:

- `repositories/cosmos.py`: Cosmos DB 実装
- `core/db.py`: Cosmos DB 接続管理の追加
- 環境変数による自動切り替え

**技術スタック**:

- azure-cosmos (Azure Cosmos DB Python SDK)

### Step 6: Docs & 型生成 連携 (Next.js 側)

**目的**: API ドキュメント整備とフロントエンド型定義の自動生成

**主な実装**:

- OpenAPI 仕様書の最終確認
- TypeScript 型定義の生成 (`web/utils/types/api.d.ts`)
- 本アーキテクチャドキュメントの最終更新

---

## データベース切り替え戦略

### 環境別の設定

**ローカル開発環境**:

```bash
DB_BACKEND=sqlite
DB_URI=sqlite+aiosqlite:///./data/app.db
```

**本番環境**:

```bash
DB_BACKEND=cosmos
COSMOS_URI=https://your-cosmos-account.documents.azure.com:443/
COSMOS_KEY=your-cosmos-key
COSMOS_DB_NAME=3pull
COSMOS_CONTAINER_FOLDERS=folders
COSMOS_CONTAINER_THREADS=chatThreads
```

### 切り替えロジック

`core/db.py`で環境変数`DB_BACKEND`を参照し、適切な Repository を返す:

```python
def get_repository():
    if settings.db_backend == "sqlite":
        return SQLiteRepository()
    elif settings.db_backend == "cosmos":
        return CosmosRepository()
    else:
        raise ValueError(f"Unknown DB_BACKEND: {settings.db_backend}")
```

---

## テスト戦略

### ユニットテスト

- Repository 層の各メソッドをテスト
- モックを使用してデータベースから独立

### 統合テスト

- 実際の SQLite データベースを使用
- API エンドポイントの E2E テスト

### テスト実行

```bash
# 全テスト実行
uv run --frozen pytest

# カバレッジ付き実行
uv run --frozen pytest --cov=app --cov-report=term-missing
```

---

## セキュリティ考慮事項

1. **環境変数の管理**

   - `.env`ファイルは`.gitignore`に含める
   - 本番環境では Azure Key Vault などのシークレット管理サービスを使用

2. **Cosmos DB アクセス制御**

   - 最小権限の原則に従った IAM 設定
   - 接続文字列の暗号化

3. **入力検証**
   - Pydantic スキーマで厳格な型検証
   - SQL インジェクション対策（ORM を使用）

---

## パフォーマンス最適化

1. **SQLite**

   - WAL モードの有効化
   - 適切なインデックスの設定

2. **Cosmos DB**

   - パーティションキーの最適化
   - クエリの RU 消費量モニタリング

3. **接続プーリング**
   - 非同期接続プールの使用
   - 適切なタイムアウト設定

---

## 認証アーキテクチャ

### 概要

フロントエンド（Next.js + Auth.js）からカスタムヘッダー（X-User-Id, X-User-Email）を受け取り、
バックエンド（FastAPI）で検証してユーザー認証を行います。

### 認証フロー

1. フロントエンドが Auth.js で OAuth 認証（EntraID/GitHub/Google）
2. Auth.js が JWT セッションに user.id と user.email を保存
3. API リクエスト時、`apiClient.ts`がセッションから情報を取得してヘッダーに含める
4. FastAPI の認証依存性（`get_current_user`）がヘッダーを抽出・検証
5. 認証済みユーザー情報をエンドポイントに提供
6. エンドポイントがユーザー固有の DB 操作を実行

### 実装詳細

#### 認証依存性（app/api/auth.py）

```python
async def get_current_user(
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    x_user_email: str | None = Header(None, alias="X-User-Email"),
) -> AuthenticatedUser:
    if not x_user_id or not x_user_email:
        raise HTTPException(status_code=401, detail="Authentication required")
    return AuthenticatedUser(user_id=x_user_id, email=x_user_email)
```

#### エンドポイント使用例

```python
@router.post("/folders", response_model=FolderRead)
async def create_folder(
    dto: FolderCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    repo: FolderRepositoryProtocol = Depends(get_folder_repo),
) -> FolderRead:
    return await repo.create(dto, user_id=current_user.user_id, email=current_user.email)
```

#### Repository 実装

Repository 層は明示的に user_id と email を受け取り、データに埋め込みます：

```python
async def create(self, dto: FolderCreate, *, user_id: str, email: str) -> FolderRead:
    read = FolderRead(
        id=new_uuid(),
        name=dto.name,
        type=dto.type,
        createdAt=to_api_datetime(utc_now()),
        userId=user_id,
        email=email,
    )
    # DB保存...
```

### セキュリティ考慮事項

- **認証必須**: 全てのユーザースコープエンドポイントで認証が必要（401 エラー）
- **ユーザー分離**: 各ユーザーは自分のデータのみアクセス可能
- **ヘッダー検証**: X-User-Id、X-User-Email 両方が必須
- **信頼ドメイン**: フロントエンドとバックエンドが同一信頼環境で動作することを前提

---

## 今後の拡張予定

1. **認証・認可の強化**

   - JWT Bearer 認証への移行検討
   - トークン有効期限管理
   - リフレッシュトークンの実装

2. **マルチテナント対応**

   - ユーザーごとのデータ分離（実装済み）
   - テナント ID ベースのパーティショニング

3. **キャッシング**

   - Redis キャッシュの導入
   - クエリ結果のキャッシング

4. **監視・ログ**
   - Application Insights 連携
   - 構造化ログの導入

---

## 参考資料

- [FastAPI 公式ドキュメント](https://fastapi.tiangolo.com/)
- [SQLAlchemy 公式ドキュメント](https://docs.sqlalchemy.org/)
- [Azure Cosmos DB Python SDK](https://docs.microsoft.com/azure/cosmos-db/sql-api-sdk-python)
- [Alembic 公式ドキュメント](https://alembic.sqlalchemy.org/)
- [Pydantic 公式ドキュメント](https://docs.pydantic.dev/)

---

## 変更履歴

| 日付       | バージョン | 変更内容 | 担当者   |
| ---------- | ---------- | -------- | -------- |
| 2025-10-16 | 1.0.0      | 初版作成 | Devin AI |

---

**注意**: 本ドキュメントは全 6 ステップの実装において常に最新の状態に保つこと。各ステップ完了時に該当セクションを更新すること。
