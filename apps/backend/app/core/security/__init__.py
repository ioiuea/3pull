"""backend のセキュリティ基盤パッケージ.

- `http`: FastAPI 向けの API 保護機能
  - session guard / request context / CSRF / rate limit
- `crypto`: 認証用の暗号・ハッシュ機能
  - password hash / token encryption

実装コードからは、この top-level ではなく
`app.core.security.http` または `app.core.security.crypto` を使う。
"""
