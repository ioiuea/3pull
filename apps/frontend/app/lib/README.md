# lib

`app/lib` は、画面や hook から使う実装ヘルパーをまとめるフォルダです。

## この層に置くもの

- API 呼び出し helper
- i18n 初期化
- async job 関連の共通型や判定
- UI 非依存の utility 関数

## この層に置かないもの

- React component
- route 定義
- Zustand store
- 画面固有の表示ロジック

## 役割

- `api-helper.ts`
  - backend API 呼び出しの共通入口
- `i18n.ts`
  - i18next 初期化
- `async-jobs.ts` `async-job-providers.ts`
  - async job まわりの共通定義
- `utils.ts`
  - 汎用 utility

`lib` は React 非依存の実装を置くことを優先します。
