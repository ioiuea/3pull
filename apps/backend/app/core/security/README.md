# Security

`app/core/security` は backend のセキュリティ基盤をまとめるパッケージです。  
このディレクトリ直下の `__init__.py` は導線だけを担い、実際の import 先は `http` または `crypto` に分けます。

- API 保護を扱う場合は [http/README.md](./http/README.md)
- 認証用暗号を扱う場合は [crypto/README.md](./crypto/README.md)

## 構成

- `http/`
  - FastAPI / Request / Depends / middleware に依存する API 保護機能
  - session guard、request context、CSRF、rate limit を配置する
- `crypto/`
  - FastAPI に依存しない認証用暗号・ハッシュ機能
  - password hash、token encryption を配置する

## 使い分け

- router や `main.py` からは `app.core.security.http` を使う
- auth service など HTTP 非依存の層からは `app.core.security.crypto` を使う
- `http/*` の内部実装ファイルを router から直接 import しない
- `crypto/*` の内部実装ファイルを service から直接 import しない

## 典型的な import

router / middleware 側:

```python
from app.core.security.http import (
    AuthenticatedRequestDep,
    CurrentUserDep,
    RateLimitPolicyKey,
    require_rate_limit,
    install_security_middleware,
)
```

auth service 側:

```python
from app.core.security.crypto import (
    decrypt_token,
    encrypt_token,
    hash_password,
    needs_rehash,
    verify_password,
)
```

## top-level の扱い

- `app.core.security` から個別関数は import しない
- top-level は `http` と `crypto` への導線としてだけ扱う
- 実装コードでは `app.core.security.http` または `app.core.security.crypto` を使う

## ルール

- 新しい FastAPI dependency は `http/dependencies.py` から公開する
- 新しい middleware は `http/middleware.py` から組み込める形にする
- 新しい暗号系 utility は `crypto/` 配下へ置く
