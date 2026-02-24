# Backend

## パッケージ管理方針

- `apps/backend` のパッケージ管理は `uv` を標準とします。
- 依存追加・更新・同期は `uv add` / `uv remove` / `uv sync` を利用します。
- ロックファイルは `uv.lock` を正とし、チーム開発では lockfile ベースで再現可能な環境を維持します。

## API フレームワーク方針

- API フレームワークは `FastAPI` を標準採用します。
- エントリーポイントは `apps/backend/app/main.py` とし、`app = FastAPI()` をこのファイルで管理します。
- ルーティング、依存性注入、ミドルウェアなどの API 構成は FastAPI の標準機能を優先して実装します。

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

### 認証データモデル

- `users`: ユーザー本体（`email`, `display_name`, `user_type`, `is_active`）
- `auth_identities`: 認証方式ごとの識別子（`provider`, `provider_subject`, `email_normalized`, `password_hash` など）
- `sessions`: セッション管理（`session_token_hash`, `expires_at`, `revoked_at`）
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
- `POST /backend/auth/logout`
- 現在セッションを失効してログアウトします。
- `POST /backend/auth/session/refresh`
- セッションをローテーションし、新 Cookie を再発行します。

### セキュリティ・運用設定

- CORS は `CSRF_TRUSTED_ORIGINS` を基準に許可オリジンを制御します。
- CSRF は `Origin/Referer` ベースの検証ミドルウェア（`app/core/security/csrf.py`）で保護します。
- Cookie セキュリティは `SESSION_COOKIE_SECURE` で環境ごとに切り替えます。
- ローカル開発時は `false`、HTTPS 必須環境は `true` を推奨します。
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
