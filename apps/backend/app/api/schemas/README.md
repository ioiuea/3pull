# api.schemas

`app.api.schemas` は、API の request / response で使う Pydantic schema をまとめるパッケージです。

この層の責務は、HTTP 入出力の形を明示し、router が受け取る request body と返す response body を型として定義することです。

## この層に置くもの

- request body の schema
- response body の schema
- API エラー応答の schema
- HTTP 入出力のための最小限の field 制約

## この層に置かないもの

- 認証や業務ロジック
- DB CRUD
- SQLAlchemy ORM model
- 外部サービス呼び出し

`api.schemas` は HTTP 契約を表す層です。永続化モデルや業務モデルの置き場ではありません。

## 利用方針

router では request / response を `app.api.schemas` から import して使います。

```python
from fastapi import APIRouter

from app.api.schemas.auth import EmailLoginRequest, EmailLoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/email/login", response_model=EmailLoginResponse)
async def login(payload: EmailLoginRequest) -> EmailLoginResponse:
    ...
```

複雑な変換や DB model からの組み立ては router / service 側で行い、schema 側には処理を持ち込まないようにします。

## 構成

- `auth.py`
  - 認証 API の request / response schema
- `audit.py`
  - 監査ログ参照 API の schema
- `health.py`
  - health / readiness API の schema
- `jobs.py`
  - 非同期ジョブ API の schema

## モデルとの境界

- `app.api.schemas`
  - HTTP 入出力モデル
- `app.models`
  - SQLAlchemy ORM model

同じデータを表していても責務は異なります。ORM model をそのまま API response として使わず、必要な形へ詰め替える前提で管理します。
