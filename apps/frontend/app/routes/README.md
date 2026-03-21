# routes

`app/routes` は、画面ルートとレイアウト境界をまとめるフォルダです。

## この層に置くもの

- ページコンポーネント
- 共通レイアウト
- 認証ガード付きレイアウト
- 言語リダイレクトなどルーティング入口

## この層に置かないもの

- 再利用 UI 部品
- fetch helper
- 汎用 hook
- グローバル store 定義

## 構成

- `layout.tsx`
  - 共通レイアウト
- `protected-layout.tsx`
  - 認証必須ページのガード
- `landing-page.tsx` `login.tsx` `signup.tsx` `password-reset.tsx`
  - 主要画面
- `*/page.tsx`
  - feature ごとのサンプル画面

`routes` は画面とルーティング境界に責務を絞り、複雑な部品や helper は `components` `hooks` `lib` へ分離します。
