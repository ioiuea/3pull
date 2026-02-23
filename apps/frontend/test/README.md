# Frontend テスト構成

`apps/frontend/test` は、フロントエンドテストコードの単一ルートです。

## ディレクトリ方針

- `test/unit/`: 小さなロジックやコンポーネント挙動を対象にした単体テストを配置します。
- `test/integration/`: 複数要素を組み合わせるルート/機能単位の統合テストを配置します。
- `test/mocks/`: テストで共通利用する `MSW` ハンドラとサーバー設定を配置します。
- `test/setup.ts`: `Vitest` + `Testing Library` + `MSW` のグローバルセットアップを定義します。

## React Router テスト方針

- ルーティング挙動のテストは `createMemoryRouter` + `RouterProvider` を優先します。
- ルートフィクスチャは、複数テストで共有しない限りテストファイル内に閉じて定義します。
- 外部 API 通信は `MSW` ハンドラでモックします。

## 命名規則

- テストファイル名は `*.test.ts` または `*.test.tsx` を使用します。
- テストファイルは `test/` 配下に配置し、`app/` 配下には置きません。
