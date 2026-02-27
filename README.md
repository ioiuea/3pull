# 3pull

<p>
  <img src="docs/assets/3pull-logo.png" alt="3pull character icon" />
</p>

モノレポ構成の Web + API + Infra スターターパックです。

## スターター構成

### インフラ

- Infrastructure as Code（Bicep）によるインフラ構築
- インフラ設計/構成ドキュメント（`docs/infra/`）

### フロントエンド（`apps/frontend`）

- Web フレームワーク: React Router v7（Framework Mode / `ssr: false`）
- 認証: FastAPI セッション認証（Entra ID / Email）
- 国際化対応: i18next + react-i18next
- グローバルステート管理: Zustand
- バリデーション: Zod + react-hook-form
- UI フレームワーク: shadcn/ui + Tailwind CSS

### バックエンド（`apps/backend`）

- API フレームワーク: FastAPI
- 構造化ログ: structlog（JSON 出力）
- 設定管理 / バリデーション: Pydantic（pydantic-settings）
- ASGI プロセスマネージャ: Gunicorn

## セットアップ手順

1. インフラを構築する
   `infra/README.md` を参照し、`infra/common.parameter.json` を環境に合わせて編集してから `infra/main.sh` を実行します。  
   これで Azure 環境のインフラを構築します。

2. アプリ依存関係をインストールする（Makefile 運用）
   プロジェクトルートで `make install` を実行します。  
   フロントエンド/バックエンドの依存関係をまとめてセットアップします。

3. PostgreSQL 初期セットアップを行う
   `apps/backend/scripts/postgres/README.md` を参照して、データベース/スキーマ/ロール/`search_path` を作成します。

4. 非同期ジョブ用の Blob コンテナを作成する
   `apps/backend/scripts/storage/README.md` を参照して、非同期ジョブ成果物の保存先となる Blob コンテナを作成します。

5. Entra ID の OIDC アプリを作成する
   Entra ID 側で OIDC 用アプリを作成し、クライアントID/シークレット/リダイレクトURIを準備します。

6. 環境変数ファイルを展開して更新する
   まず `make env` で `.env` を生成し、生成後に各 `.env` を環境値に更新します。

7. アプリを起動する
   用途に応じて以下を実行します。
   - 本番相当起動: `make up-api` / `make up-web`
   - 開発起動: `make dev-api` / `make dev-web`

## 参照先

- Frontend 詳細: `apps/frontend/README.md`
- Backend 詳細: `apps/backend/README.md`
- Infrastructure 詳細: `docs/`
