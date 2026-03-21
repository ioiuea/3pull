# api

`app.api` は、backend の HTTP インターフェース層をまとめるパッケージです。

この層の責務は、HTTP request を受け取り、必要な dependency を解決し、service や repository を呼び出して、HTTP response として返すことです。

## この層に置くもの

- 公開 API の router
- 内部運用向け API
- request / response schema
- FastAPI `Depends` による認証・DB session 解決
- HTTP status code や `HTTPException` の制御

## この層に置かないもの

- 認証やジョブ処理の業務ロジックそのもの
- DB CRUD の実装
- 外部サービス接続の実装
- 共通設定、ログ、セキュリティ基盤

HTTP 入口としての薄い層に保ち、複雑な処理は `services` `repositories` `adapters` `core` に分離します。

## 構成

- `routers/`
  - 公開 API の router 定義
- `internal/`
  - Kubernetes probe など内部運用向け endpoint
- `schemas/`
  - request / response の Pydantic schema

## 利用方針

router では package の公開入口を使って依存を受け取ります。

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.adapters.sql.session import get_session
from app.core.security.http import CurrentUserDep

router = APIRouter()


@router.get("/me")
async def get_me(
    user: CurrentUserDep,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    return {"email": user.email}
```

## 関連 package

- `app.services`
  - ユースケース実装
- `app.repositories`
  - DB access
- `app.core.security.http`
  - router で使う認証・認可 dependency
- `app.core.settings`
  - API 動作に必要な設定解決
