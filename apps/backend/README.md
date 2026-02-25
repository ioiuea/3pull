# Backend

## パッケージ管理方針

- `apps/backend` のパッケージ管理は `uv` を標準とします。
- 依存追加・更新・同期は `uv add` / `uv remove` / `uv sync` を利用します。
- ロックファイルは `uv.lock` を正とし、チーム開発では lockfile ベースで再現可能な環境を維持します。

## API フレームワーク方針

- API フレームワークは `FastAPI` を標準採用します。
- エントリーポイントは `apps/backend/app/main.py` とし、`app = FastAPI()` をこのファイルで管理します。
- ルーティング、依存性注入、ミドルウェアなどの API 構成は FastAPI の標準機能を優先して実装します。

### フォルダ構成戦略

- `apps/backend/app/` は「レイヤ責務 + feature 分割」を併用します。
- 実装構成は以下の `tree` を基準とします。

```text
apps/backend
├── pyproject.toml                        # Backend依存関係・ツール設定（ruff/pyright/pytest）
├── alembic.ini                           # Alembic実行設定
├── .env(.example)                        # Backend環境変数定義
├── app/                                  # アプリケーション本体
│   ├── main.py                           # FastAPIブートストラップ（middleware/router登録）
│   ├── api/                              # APIインタフェース層（HTTP入出力）
│   │   ├── routers/                      # エンドポイント定義層
│   │   ├── schemas/                      # Request/Responseスキーマ層
│   │   └── internal/                     # 内部運用API層（probe等）
│   ├── adapters/                         # 外部接続層（DB/IdP/Network）
│   │   ├── postgres/                     # PostgreSQL接続管理層
│   │   │   ├── base.py                   # SQLAlchemy Declarative Base/metadata定義
│   │   │   └── session.py                # AsyncEngine/Session/UoW依存定義
│   │   ├── idp/                          # IdP連携層
│   │   │   └── entra.py                  # Entra OIDCクライアント設定/連携
│   │   └── network/                      # ネットワーク疎通アダプタ層
│   │       └── tcp.py                    # TCP pingヘルパー
│   ├── core/                             # 横断基盤層（設定/ログ/セキュリティ/ライフサイクル）
│   │   ├── settings/config.py            # 環境変数設定の一元定義
│   │   ├── logging/config.py             # structlog設定
│   │   ├── security/password.py          # Argon2idパスワード処理
│   │   └── security/csrf.py              # CSRFチェックミドルウェア
│   ├── models/                           # ORMモデル層（テーブル定義）
│   │   └── auth/                         # 認証機能のモデル群
│   ├── repositories/                     # 永続化アクセス層（CRUD/クエリ）
│   │   └── auth/                         # 認証機能のRepository群
│   └── services/                         # ユースケース層（業務ロジック）
│       ├── auth/                         # 認証ユースケース
│       └── health.py                     # ヘルスチェックユースケース
├── alembic/                              # マイグレーション管理層
│   └── versions/                         # 生成されたリビジョンファイル
└── postgres/                             # 初期DB構築スクリプト群
    ├── run_all.sh                        # DB/Schema/Roleセットアップ実行
    └── scripts/                          # 個別セットアップスクリプト
```

- `api/` は HTTP 入出力、`services/` はユースケース、`repositories/` は DB 操作、`models/` は ORM 定義を担当します。
- `adapters/` は外部接続（DB・IdP・ネットワーク）を集約し、`core/` は横断関心事（設定/ログ/セキュリティ）を管理します。

## API インタフェース規約

- API のインタフェース定義は `apps/backend/app/api/` 配下に集約します。
- `apps/backend/app/api/routers/` にはエンドポイント定義（HTTP メソッド / パス / ルーター構成）を配置します。
- `apps/backend/app/api/schemas/` にはリクエスト・レスポンスのスキーマ（Pydantic モデル）を配置します。
- 各 API の公開インタフェースは `routers` と `schemas` の組み合わせで定義し、ハンドラ内で直接生の辞書構造を返す実装を避けます。
- `apps/backend/app/main.py` は FastAPI の API ブートストラップとして扱い、アプリ生成・ミドルウェア設定・ルーター登録を担当します。

## ログ出力方針

- アプリケーションログは `structlog` による構造化ログ（JSON）を標準とします。
- ログ関連の実装は `apps/backend/app/core/logging/` 配下に集約します。
- ログ設定（processor / renderer / level）は `apps/backend/app/core/logging/config.py` で一元管理します。
- アクセスログは `apps/backend/app/core/logging/middleware.py` のミドルウェアで出力し、リクエスト単位のメタ情報を JSON で記録します。
- `apps/backend/app/main.py`（ブートストラップ）で logging 設定を import して適用し、アプリ起動時に必ず有効化します。

## 設定管理方針（pydantic-settings）

- アプリ設定の読み込みは `pydantic-settings` を標準採用し、`apps/backend/app/core/settings/config.py` に集約します。
- 設定値は `AppSettings` という 1 つの設定クラスにまとめて定義し、「どの環境変数名から読むか」を各項目ごとに明示します。
- 設定値を使うときは必ず `get_settings()` を使い、毎回作り直さずに同じ設定インスタンスを再利用します。
- ローカル開発時は `apps/backend/.env` が存在する場合のみ `python-dotenv` で読み込み、本番は環境変数注入を前提とします。
- `model_config` では「環境変数の大文字/小文字の違いは厳密に見ない」「未使用の追加環境変数があってもエラーにしない」設定にして、環境ごとの差異で起動失敗しにくくします。

### 設定の利用方法

- ブートストラップ（`apps/backend/app/main.py`）で `get_settings()` を呼び出し、`FastAPI` の title やポートなど起動設定に利用します。
- ライフサイクル（`apps/backend/app/core/lifecycle/startup.py`）で `get_settings()` を呼び出し、ログレベルやサービス名など運用情報の出力に利用します。
- 各モジュールで直接 `os.environ` を読む実装は避け、設定参照は必ず `get_settings()` 経由で統一します。

## 認証実装方針

- 認証はフロント主導ではなく API（FastAPI）主導で実装し、フロントは `/backend/auth/*` を利用します。
- 認証方式は 2 系統です。
- Entra ID（OIDC）: 社内ユーザー向け
- Email/Password: 社外ユーザー向け
- アカウント統合は Entra 優先ポリシーです。
- 同一メールで先に Email 登録済みの場合は Entra ログイン時に Entra 側へ統合します。
- Entra が先に紐づいているメールの Email サインアップは拒否します。
- Email 認証はメール検証完了までログイン不可です。
- セッションは DB（`sessions` テーブル）で管理し、Cookie は `HttpOnly` + `SameSite=Lax` を標準とします。
- パスワードは Argon2id でハッシュ化し、平文保存しません。
- 検証トークン/リセットトークンは生値を DB 保存せず、SHA-256 ハッシュのみ保存します。
- Entra の Graph API 用 `access_token` / `refresh_token` は DB 保存時に暗号化し、参照時に復号します（`ENTRA_TOKEN_ENCRYPTION_KEY` が必須）。
- Entra トークンは `offline_access` を使って refresh し、アプリセッションと有効期限が乖離しても `/auth/entra/profile` で自動再取得します。

### 認証データモデル

- `users`: ユーザー本体（`email`, `display_name`, `user_type`, `is_active`）
- `auth_identities`: 認証方式ごとの識別子（`provider`, `provider_subject`, `email_normalized`, `password_hash` など）
- `sessions`: セッション管理（`session_token_hash`, `expires_at`, `revoked_at`）
- Entra 用トークン管理（`entra_access_token`, `entra_refresh_token`, `entra_access_token_expires_at`）
- `email_verification_tokens`: メール検証トークン（ハッシュ保存）
- `password_reset_tokens`: パスワードリセットトークン（ハッシュ保存）

### DB/トランザクション方針

- DB 接続は `apps/backend/app/adapters/postgres/session.py` で一元管理します。
- `DATABASE_URL` は必須運用で、未設定時は起動時に失敗させます。
- `get_session()` は `async with session.begin()` の UoW として動作し、Router/Service で `commit()/rollback()` を直接呼ばない方針です。
- マイグレーションは Alembic を利用し、`apps/backend/alembic/` で管理します。

### 認証 API 利用方法

- `POST /backend/auth/email/signup`
- Email ユーザーを登録し、検証トークン発行状態を返します。
- `POST /backend/auth/email/verify`
- 検証トークンを消費して Email 検証を完了します。
- `POST /backend/auth/email/login`
- Email ログインを行い、セッション Cookie を発行します。
- `GET /backend/auth/entra/login`
- Entra OIDC ログインへリダイレクトします。
- `GET /backend/auth/entra/callback`
- OIDC コールバックを処理し、アプリセッションを発行します。
- `POST /backend/auth/password/reset/request`
- パスワードリセット要求を受け付けます（存在有無に関わらず同一レスポンス）。
- `POST /backend/auth/password/reset/confirm`
- リセットトークンでパスワード再設定を確定します。
- `POST /backend/auth/password/change`
- 現在パスワード確認後に変更し、全セッション失効ポリシーを適用します。
- `GET /backend/auth/me`
- 現在ログイン中ユーザーを返します。
- `GET /backend/auth/entra/profile`
- Entra 認証ユーザー向けに Graph `/me` を返します。アクセストークン期限切れ時は refresh token で再取得します。
- `POST /backend/auth/logout`
- 現在セッションを失効してログアウトします。
- `POST /backend/auth/session/refresh`
- セッションをローテーションし、新 Cookie を再発行します。

## APIプロテクト方針

- API の保護は「セッション Cookie + DB セッション検証」を標準とします。
- 公開API（フロントが利用）は `/backend/*` 配下に集約し、必要なエンドポイントへ認証依存を適用します。
- ヘルス系は役割で分離します。
- フロント向け健全性確認: `GET /backend/health`（認証必須）
- 運用プローブ: `GET /livez`, `GET /readyz`（認証不要、`/backend` 配下外、`include_in_schema=False`）
- `/livez` / `/readyz` はコード上は公開ルートですが、実運用では Ingress/ALB 側で外部公開しない前提です。
- CSRF は `Origin/Referer` 検証ミドルウェアで保護し、許可オリジンは `CSRF_TRUSTED_ORIGINS` で管理します。

### APIプロテクトの利用方法

- フロントから保護APIを呼ぶときは Cookie を必ず送る（`credentials: include`）。
- 未認証時は `401` を受け取り、ログイン導線へ遷移します。
- `GET /backend/health` は次を返します。
- `status`: `ok` または `degraded`
- `dependencies.postgres`: TCP 到達性（`ok`, `latency_ms`, `error`）
- `GET /backend/auth/entra/profile` は internal ユーザー専用です。
- external ユーザーは `403`
- セッショントークン不備/失効時は `401`

## TCP Ping アダプター利用方法

- TCP 到達性チェックは `apps/backend/app/adapters/network/tcp.py` の `tcp_ping` を利用します。
- 用途は「アプリヘルス判定」「外部依存の疎通確認」です。
- 現在は `GET /backend/health` で PostgreSQL の到達性確認に利用しています。

### 関数仕様

- シグネチャ: `tcp_ping(host: str, port: int, timeout: float = 1.0) -> tuple[bool, int, str | None]`
- 返り値:
- `ok`: 接続成功なら `True`
- `latency_ms`: 接続に要したミリ秒
- `error`: 失敗時の理由（成功時は `None`）

### 使用例

```python
from app.adapters.network.tcp import tcp_ping

ok, latency_ms, error = tcp_ping("localhost", 5432, timeout=1.0)
if ok:
    print(f"reachable: {latency_ms}ms")
else:
    print(f"unreachable: {error}")
```

### 実装上の注意

- `tcp_ping` は同期関数です。FastAPI ハンドラから呼ぶ場合は `run_in_threadpool` 経由で実行します。
- TCP 到達性は「ポートが開いている」ことの確認であり、DB 認証成功やSQL実行成功までは保証しません。
- タイムアウトは短め（例: `0.5〜1.0s`）に設定し、ヘルスAPIの応答遅延を抑えます。

### セキュリティ・運用設定

- CORS は `CSRF_TRUSTED_ORIGINS` を基準に許可オリジンを制御します。
- CSRF は `Origin/Referer` ベースの検証ミドルウェア（`app/core/security/csrf.py`）で保護します。
- Cookie セキュリティは `SESSION_COOKIE_SECURE` で環境ごとに切り替えます。
- ローカル開発時は `false`、HTTPS 必須環境は `true` を推奨します。
- Entra トークン暗号化鍵は `ENTRA_TOKEN_ENCRYPTION_KEY` を使用します。
- 本番では Secret Manager / Key Vault で安全に注入し、平文でリポジトリ管理しません。
- 鍵を変更すると既存暗号化トークンは復号できなくなるため、ローテーション時は再ログイン導線を含めて運用設計します。
- Email ログインのロック制御は設定値で管理します。
- `EMAIL_LOGIN_MAX_FAILURES`（既定: 5）
- `EMAIL_LOGIN_LOCK_MINUTES`（既定: 15）
- 有効期限設定は以下で管理します。
- `EMAIL_VERIFICATION_TTL_MINUTES`（既定: 60）
- `PASSWORD_RESET_TTL_MINUTES`（既定: 60）
- `SESSION_TTL_MINUTES`（既定: 10080 = 7日）

### 監査ログ（構造化ログ）

- 認証系の主要イベントは `structlog` で JSON 出力します。
- `auth.audit.login.success`
- `auth.audit.login.failure`
- `auth.audit.logout`
- `auth.audit.session.refresh`
- `auth.audit.session.revoke_all`

## CI 実装方針

- バックエンドの品質ゲートは「format / lint / typecheck / test」の4段階で構成します。
- ローカルと CI で同じコマンドを使えるよう、`Makefile` ターゲットを正とします。

### ruff（Formatter）

- フォーマッタは `ruff format` を採用します。
- check（差分検出）:
- `make backend-format`
- fix（整形反映）:
- `make backend-format-fix`
- ルール設定は `apps/backend/pyproject.toml` の `[tool.ruff]` を参照します。

### ruff（Linter）

- Linter は `ruff check` を採用します。
- check:
- `make backend-lint`
- fix（自動修正可能な項目のみ）:
- `make backend-lint-fix`
- ルール設定は `apps/backend/pyproject.toml` の `[tool.ruff.lint]` を参照します。

### pyright（Typecheck）

- 型チェックは `pyright` を採用します。
- 実行:
- `make backend-typecheck`
- 設定は `apps/backend/pyproject.toml` の `[tool.pyright]` を参照します。
- `alembic` は型チェック対象から除外しています。

### pytest（Test）

- テスト実行は `pytest` を採用します。
- 実行:
- `make backend-test`
- pytest 設定は `apps/backend/pyproject.toml` の `[tool.pytest.ini_options]` を参照します。

### Makefile での CI 運用

- バックエンド単体の CI 実行:
- `make backend-ci`
- 実行順: `backend-format` → `backend-lint` → `backend-typecheck` → `backend-test`
- リポジトリ全体（frontend + backend）の CI 実行:
- `make ci`
- 実行順: `install` → `frontend-ci` → `backend-ci`

## Alembic（Makefile 利用方法）

- マイグレーション運用は `Makefile` ターゲット経由を標準とします。
- 実行前提として `apps/backend/.env` の `DATABASE_URL` が正しく設定されている必要があります。

### マイグレーション生成

- 実行:
- `make alembic-revision "add entra token columns to sessions"`
- 内部で実行されるコマンド:
- `uv run alembic revision --autogenerate -m "<message>"`
- メッセージ未指定時はエラー終了します。

### マイグレーション適用

- 実行:
- `make alembic-upgrade`
- 内部で実行されるコマンド:
- `uv run alembic upgrade head`

### よくある注意点

- `Target database is not up to date.` が出た場合:
- 先に `make alembic-upgrade` で最新まで適用してから `make alembic-revision` を実行します。
- 既に `alembic/versions` に手動追加済みファイルがある場合:
- 追加で `revision` を切らず、`make alembic-upgrade` のみで適用します。

## Graph プロファイル取得実装

- Entra 認証ユーザー（`user_type=internal`）向けに、Microsoft Graph の `/me` を backend 経由で取得します。
- フロントは Graph に直接アクセスせず、`/backend/auth/entra/profile` を呼びます。

### API 仕様

- エンドポイント:
- `GET /backend/auth/entra/profile`
- 認証:
- セッション Cookie 必須（APIプロテクト対象）
- アクセス制御:
- internal ユーザーのみ許可（external は `403`）
- 主なレスポンス項目:
- `displayName`, `companyName`, `department`, `jobTitle`, `email`
- `access_token_expires_at`

### 実装フロー

- 1. Entra ログイン（`/backend/auth/entra/callback`）時に token を取得
- 2. `sessions` テーブルへ以下を保存
- `entra_access_token`
- `entra_refresh_token`
- `entra_access_token_expires_at`
- 3. `/backend/auth/entra/profile` 呼び出し時に access token の期限を判定
- 4. 期限切れ/未設定の場合は refresh token grant で再取得
- 5. 新しい token を `sessions` に更新してから Graph `/me` を呼び出し
- 6. Graph 結果を API レスポンスとして返却

### セキュリティ方針

- access/refresh token は DB 保存前に暗号化します。
- 復号鍵は `ENTRA_TOKEN_ENCRYPTION_KEY` を使用します。
- 鍵未設定時はトークン処理で `503` を返します。
- 既存平文データとの後方互換として、非暗号化値の読み取りも許容しています。

### 必須設定

- Entra アプリ側 permission:
- `User.Read`（Graph `/me` 用）
- `offline_access`（refresh token 用）
- backend 環境変数:
- `ENTRA_TENANT_ID`
- `ENTRA_CLIENT_ID`
- `ENTRA_CLIENT_SECRET`
- `ENTRA_REDIRECT_URI`
- `ENTRA_TOKEN_ENCRYPTION_KEY`

## Python コーディング規約

- Python コードは `PEP 8` に準拠して実装します。

## コメント・ドキュメント記述ルール

- 第三者が読んで処理意図を理解できることを最優先とし、コメントを省略しません。
- 各 Python ファイルの先頭には、ファイル全体の責務を示すモジュールドックストリングを必ず記載します。
- モジュールドックストリングには「このファイルが何を担当し、どの処理を行うか」を箇条書きで明記します。
- 関数・メソッドには、目的・入出力・副作用が分かるドックストリングを必ず記載します。
- ロジック上の重要な判断（分岐理由、運用上の制約、性能/安全性の意図）には、行単位コメントを付与します。
- コメントは「何をしているか」だけでなく「なぜそうするか」を優先して記載します。
- 一時対応や暫定実装には、`TODO` コメントで背景と解消条件を明示します。
- コメントと実装の不整合を禁止し、ロジック変更時はコメントも同時更新します。

## `app/__init__.py` 運用方針

- `apps/backend/app/__init__.py` は、`app` ディレクトリを Python パッケージとして扱うために配置します。
- `__init__.py` は原則空ファイルにせず、パッケージ責務を示すモジュールドックストリングを記載します。
- 将来、パッケージ公開面の都合で再エクスポートが必要になった場合のみ、`__init__.py` に `__all__` や公開シンボルを明示的に追加します。
- 実行ロジックや副作用のある初期化処理は `__init__.py` に書かず、`app/main.py` または適切なモジュールへ配置します。
