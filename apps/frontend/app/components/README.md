# components

`app/components` は、画面から再利用する React コンポーネントをまとめるフォルダです。

## この層に置くもの

- 複数ページで再利用する UI 部品
- フォーム部品
- provider コンポーネント
- `ui/` 配下の共通 UI

## この層に置かないもの

- ルーティング定義
- API fetch の実装
- グローバル定数
- Zustand store 定義

## 構成

- `ui/`
  - shadcn ベースの共通 UI
- `sample-switcher/`
  - サンプル画面で共有する切替 UI
- `login-form.tsx` `signup-form.tsx` `password-reset-form.tsx`
  - 認証フォーム部品
- `theme-provider.tsx`
  - テーマ provider

画面固有の大きな処理は `routes/` に残し、`components/` は再利用可能な単位に保ちます。
