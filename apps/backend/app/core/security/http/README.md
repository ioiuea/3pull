# Security HTTP

`app/core/security/http` は HTTP request を保護するためのパッケージです。  
FastAPI、`Request`、`Depends`、middleware に依存してよい層です。

## 何があるか

- `session.py`
  - Cookie セッションから user / session context を解決する
- `dependencies.py`
  - `CurrentUserDep` など router 向けの依存 alias を公開する
- `request_context.py`
  - client IP、XFF、user-agent をまとめて解決する
- `client_ip.py`
  - trusted proxy 前提の client IP 解決本体
- `csrf.py`
  - Origin / Referer ベースの CSRF middleware
- `middleware.py`
  - `install_security_middleware(app)` の入口
- `rate_limit/`
  - request / failure ベース rate limit の実装

## 利用方法

### 1. router で current user を使う

```python
from app.core.security.http import CurrentUserDep


@router.get("/me")
async def get_me(user: CurrentUserDep) -> dict[str, str]:
    return {"user_id": str(user.id)}
```

### 2. router で session context を使う

```python
from app.core.security.http import AuthenticatedSessionDep


@router.post("/password/change")
async def post_password_change(auth_context: AuthenticatedSessionDep) -> None:
    user = auth_context.user
    raw_token = auth_context.raw_token
```

### 3. endpoint に rate limit をかける

```python
from fastapi import Depends

from app.core.security.http import RateLimitPolicyKey, require_rate_limit


@router.post("/email/login")
async def post_login(
    _: None = Depends(require_rate_limit(RateLimitPolicyKey.EMAIL_LOGIN)),
) -> None:
    ...
```

### 4. app に middleware を組み込む

```python
from app.core.security.http import install_security_middleware

install_security_middleware(app)
```

## import ルール

- router からは `app.core.security.http` を使う
- `session.py` `client_ip.py` `csrf.py` を個別 import してもよいのは、このパッケージ内部だけ
- request 情報の解決は `resolve_request_security_context()` を優先する

## 置いてはいけないもの

- password hash や token encryption のような HTTP 非依存 logic
- repository や service の業務ロジック
