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
- 認証: Microsoft Entra ID + MSAL（SPA OIDC PKCE）
- 国際化対応: i18next + react-i18next
- グローバルステート管理: Zustand
- バリデーション: Zod + react-hook-form
- UI フレームワーク: shadcn/ui + Tailwind CSS

### バックエンド（`apps/backend`）

- API フレームワーク: FastAPI
- 構造化ログ: structlog（JSON 出力）
- 設定管理 / バリデーション: Pydantic（pydantic-settings）
- ASGI プロセスマネージャ: Gunicorn

## 参照先

- Frontend 詳細: `apps/frontend/README.md`
- Backend 詳細: `apps/backend/README.md`
- Infrastructure 詳細: `docs/`
