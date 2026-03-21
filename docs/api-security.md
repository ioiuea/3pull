# API Security

## 目的

- API に適用するセキュリティ対策の責務分離を明確にする
- `rate limit` と `cookie/session` ベースの API protect を同じ設計原則で整理する
- `app/core/security`、`app/api/dependencies`、`app/api/routers` の境界を揃える

## 対象

- `apps/backend/app/core/security/*`
- `apps/backend/app/api/dependencies/*`
- `apps/backend/app/api/routers/*`
- `apps/backend/app/services/auth/*`

## 設計原則

1. セキュリティポリシーは `app/core/security` に置く
2. 認証ドメインの本体は `app/services/auth` に置く
3. router は HTTP 入出力と `Depends(...)` の接着に限定する
4. `app/api/dependencies` は薄い adapter 以外を置かない
5. 同じ保護手段を複数 router で使う場合、router helper に重複させない

## AsIs

### 1. rate limit

- コアロジック:
  - `apps/backend/app/core/security/rate_limit/models.py`
  - `apps/backend/app/core/security/rate_limit/store.py`
  - `apps/backend/app/core/security/rate_limit/service.py`
- FastAPI dependency:
  - `apps/backend/app/api/dependencies/rate_limit.py`
- router 側:
  - `apps/backend/app/api/routers/auth.py`

現状の問題:

- `require_rate_limit(...)` が `api/dependencies` にある
- 中身は単なる FastAPI adapter ではなく、次を持っている
  - client IP 解決
  - service 呼び出し
  - fail-open
  - logging
  - `HTTPException(429)` 変換
- つまり API 層に security concern が入り込みすぎている

### 2. cookie/session による API protect

- 認証ドメイン本体:
  - `apps/backend/app/services/auth/session_auth_service.py`
- router helper:
  - `apps/backend/app/api/routers/auth.py`
  - `apps/backend/app/api/routers/jobs/helpers.py`
  - `apps/backend/app/api/routers/health.py`

現状の問題:

- `session cookie -> raw token -> user resolve -> HTTP 401 変換` が複数箇所に重複している
- `auth.py`、`jobs/helpers.py`、`health.py` で同種の処理を別々に持っている
- セキュリティルールではなく router helper として散っている

### 3. `app/api/dependencies` の位置づけ

- 現在は `rate_limit.py` のみが存在する
- ただし、中身は薄い adapter ではなくセキュリティ適用本体に近い
- 現状のままだと「dependency だから api に置く」という整理になっている

## ToBe

## 1. レイヤ責務

### `app/services/auth`

責務:

- 認証/セッションのドメイン処理
- DB を使った user/session 解決
- 認証エラーをドメインエラーとして返す

置くもの:

- `resolve_user_by_session_token(...)`
- `refresh_user_session(...)`
- `revoke_session_by_token(...)`

置かないもの:

- `Request` の直接操作
- Cookie 名の解決
- `HTTPException` 変換

### `app/core/security`

責務:

- API 保護の共通ルール
- セキュリティポリシーの適用
- FastAPI 依存として使う guard の本体

置くもの:

- CSRF
- client IP 解決
- rate limit policy 適用
- session cookie ベースの API protect

置かないもの:

- router 固有のレスポンス整形
- 個別エンドポイントの業務処理

### `app/api/routers`

責務:

- HTTP 入出力
- schema 変換
- `Depends(...)` の適用

置くもの:

- route 定義
- request/response schema
- 業務サービス呼び出し

置かないもの:

- cookie/session protect の共通ロジック
- rate limit の共通ロジック

### `app/api/dependencies`

責務:

- 原則として置かない
- 置く場合も、`core/security` を再 export するだけの薄い adapter に限定する

推奨:

- 新規追加はしない
- 既存 `rate_limit.py` は `core/security` 側へ移す

## 2. 推奨構成

```text
apps/backend/app/
  core/
    security/
      client_ip.py
      csrf.py
      rate_limit/
        models.py
        store.py
        service.py
        fastapi.py
      session/
        fastapi.py
        http.py
  services/
    auth/
      session_auth_service.py
  api/
    routers/
      auth.py
      health.py
      jobs/
        helpers.py
```

## 3. rate limit の ToBe

### AsIs

- `app/api/dependencies/rate_limit.py` に `require_rate_limit(...)` がある

### ToBe

- `app/core/security/rate_limit/fastapi.py` へ移す

責務:

- `Request` から client IP を解決する
- `RateLimitService` を呼ぶ
- fail-open を行う
- log を記録する
- `429` へ変換する

router 側:

```python
from app.core.security.rate_limit.fastapi import require_rate_limit
```

## 4. cookie/session protect の ToBe

### AsIs

- router ごとに `require_session_user` 相当処理が散在している

### ToBe

- `app/core/security/session/fastapi.py` に集約する

置く関数の例:

- `require_session_user(request: Request, session: Session) -> User`
- `require_authenticated_session(request: Request, session: Session) -> None`
- `require_session_context(...) -> AuthenticatedSessionContext`

補助:

- `app/core/security/session/http.py`
  - `SessionAuthError -> HTTPException` 変換

router 側:

- `auth.py`
- `jobs/helpers.py`
- `health.py`

の重複実装を廃止し、共通 dependency を import して使う

## 5. 実施順

1. `app/api/dependencies/rate_limit.py` を `app/core/security/rate_limit/fastapi.py` に移す
2. session cookie protect を `app/core/security/session/fastapi.py` に新設する
3. `auth.py` の `_require_session_user` / `_raise_session_error` を共通化する
4. `jobs/helpers.py` の `require_session_user` / `raise_session_error` を共通化する
5. `health.py` の `_require_authenticated_session` を共通化する
6. `app/api/dependencies` を空にできるなら削除、残すなら再 export 専用に限定する

## 結論

- `rate limit` も `cookie/session` による API protect も、API 層の都合ではなくセキュリティ concern として扱うべき
- したがって主配置は `app/core/security` が適切
- `app/services/auth` は認証ドメイン本体、`app/api/routers` は HTTP 接着に限定する
- `app/api/dependencies` は本質的には不要で、残すとしても薄い adapter に留める
