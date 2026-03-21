# api.routers

`app.api.routers` は、公開 API の FastAPI router をまとめるパッケージです。

この層の責務は、HTTP エンドポイントを定義し、request を受け取り、必要な service や repository を呼び出して response を返すことです。

## この層に置くもの

- `APIRouter` の定義
- path operation (`@router.get`, `@router.post` など)
- `Depends` を使った認証・認可・DB session の受け取り
- request / response schema の組み立て
- HTTP status code や `HTTPException` の制御

## この層に置かないもの

- 認証の業務ロジックそのもの
- DB CRUD の実装
- Azure / Redis など外部接続の実装
- 汎用 utility や横断基盤

これらはそれぞれ `services` `repositories` `adapters` `core` に置きます。

## 利用方針

router では、可能な限り package の公開入口を使って依存を受け取ります。

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security.http import CurrentUserDep
from app.db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def get_me(
    user: CurrentUserDep,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    return {"email": user.email}
```

router は薄く保ち、複雑な分岐や更新処理は service / helper へ寄せます。

## 構成

- `auth.py`
  - 認証・セッション・Entra ログイン関連の API
- `audit.py`
  - 認証監査ログ参照 API
- `health.py`
  - health / readiness 関連 API
- `jobs/`
  - 非同期ジョブを受け付け、ジョブ作成とキュー投入の入口になる API package

## jobs 配下の方針

`jobs` は endpoint 数が多いため、責務ごとに分けています。

この package は、重い処理を同期実行する場所ではありません。HTTP request を受けてジョブ要求を検証し、worker が処理するためのメッセージをキューへ流す入口です。

- `query.py`
  - 一覧・詳細・成果物取得など参照系
- `commands.py`
  - cancel など更新系
- `create/`
  - job type ごとの作成 API
  - それぞれの endpoint がジョブ要求を受け付け、非同期実行用のジョブ登録へつなぐ
- `helpers.py`
  - jobs router 内だけで共有する変換・所有者確認 helper

`helpers.py` は `jobs` router 専用です。`app.api.routers.jobs` の外から共通 utility として使わないようにします。

## 関連 package

- `app.api.schemas`
  - request / response schema
- `app.services`
  - 業務ロジック
- `app.repositories`
  - DB access
- `app.core.security.http`
  - router で使う認証・認可 dependency
