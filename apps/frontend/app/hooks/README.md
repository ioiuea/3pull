# hooks

`app/hooks` は、React 向けの再利用 hook をまとめるフォルダです。

## この層に置くもの

- SWR を使ったデータ取得 hook
- UI 状態を整理する custom hook
- ブラウザ環境依存の判定 hook

## この層に置かないもの

- 画面そのもの
- 汎用 utility 関数
- Zustand store 定義

## 役割

- `lib/`
  - fetch や実装 helper の正本
- `hooks/`
  - React から使うための再利用単位

`hooks` は React component から直接呼ぶ入口として保ち、fetch 本体や純粋関数は `lib/` に寄せます。
