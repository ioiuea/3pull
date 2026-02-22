# AGENTS

## Frontend Framework

- この `apps/frontend` は **React Router フレームワーク** を採用している。  
  参照: <https://reactrouter.com/home>
- このアプリは `npx create-react-router@latest` によって `apps` 配下にインストールされています。

## Package Manager Policy

- `apps/frontend/package.json` の `scripts.preinstall` で `npx only-allow pnpm` を実行し、利用可能なパッケージマネージャを `pnpm` に制限しています。
- `apps/frontend/package.json` の `packageManager` は `pnpm@10.30.1` に設定されています。

## Build Strategy

- このアプリは **Static Export 前提** で実装しています。
- 設定ファイル `apps/frontend/react-router.config.ts` では `ssr: false` を設定しています。
- 生成物は静的配信を前提とし、`build/client` を配信対象として扱います。

## Routing Strategy

- `flatRoutes` は利用しません。
- ルート定義は `apps/frontend/app/routes.ts` で `route` / `layout` / `index` を使い、明示的に管理します。
- ルートファイルはフォルダ階層で整理し、feature 単位で配置します。
- 画面実装は `apps/frontend/app/feature/<feature名>/` に同名の feature 用フォルダを作成し、ページコンポーネントを配置して `app/routes.ts` から呼び出す構成にします。
- `apps/frontend/app/components/` は部品単位の再利用コンポーネントを格納するフォルダとして扱います。

### Why Not `flatRoutes`

- `app/routes.ts` で `route` / `layout` / `index` を明示管理することで URL 構造・レイアウト境界・feature 単位の責務分離を一貫して保てる一方、`flatRoutes` はファイル名規約依存の暗黙解決が増えて命名変更やファイル移動時に意図しないルート変更、解釈差分、レビュー時の認知負荷を招きやすいため採用しません。

## UI Design Strategy

- UI デザイン実装では `shadcn` を利用します。
- `apps/frontend/app/components/ui/*` の既存コンポーネントを優先して再利用します。
- ボタン、カード、フォーム、テーブル、ツールチップなどの基礎 UI は独自実装より `shadcn` コンポーネントを優先して利用します。
- アイコンは `lucide` を優先して利用します。

## Form Validation Strategy

- フォームバリデーションは `zod` をスキーマ定義の標準として利用します。
- `react-hook-form` との接続は `@hookform/resolvers`（`zodResolver`）を標準として利用します。
- フォーム入力値の型・バリデーションルール・エラーメッセージは `zod` スキーマを基準に一元管理します。
