# store

`app/store` は、Zustand を使ったグローバル state 定義をまとめるフォルダです。

## この層に置くもの

- Zustand store 定義
- state 型
- action / updater
- reset を含む状態更新ロジック

## この層に置かないもの

- 一時的なローカル UI state
- API fetch の実装
- 画面コンポーネント

グローバル共有が不要な state は `useState` を優先し、`store` には複数コンポーネントで共有する state だけを置きます。

現状はサンプル store が中心ですが、今後実アプリの共有 state も同じ方針でここに集約します。
