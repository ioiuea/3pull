# schedulers

`app.schedulers` は、定期実行される処理の入口をまとめるパッケージです。

## この層の責務

- 定期実行処理の CLI エントリーポイントを提供する
- カテゴリや実行対象ごとの runner を切り替える
- dry-run / 実行ログ / 終了コードなど、運用実行の枠組みを提供する

## この層に置くもの

- scheduler 用 CLI
- 実行カテゴリごとの runner 登録
- runner 共通 helper
- cleanup など対象別の定期実行処理

## この層に置かないもの

- HTTP endpoint
- 非同期ジョブ worker の実行本体
- 外部サービス接続の実装
- 認証や監査の業務ロジックそのもの

## 構成

- `batch_jobs.py`
  - 定期実行バッチジョブの CLI エントリーポイント
  - 現状は cleanup カテゴリの実行入口
- `cleanup/runner_registry.py`
  - cleanup 内の subcommand と runner の対応付け
- `cleanup/runners/`
  - cleanup 内の対象別実行単位
- `cleanup/helpers.py`
  - cleanup 実行で共有する helper

## 利用イメージ

`schedulers` はアプリ内部から直接呼ぶより、CLI として定期実行する前提です。現状の利用例は cleanup カテゴリです。

```bash
python -m app.schedulers.batch_jobs sessions-cleanup --dry-run
python -m app.schedulers.batch_jobs audit-cleanup
python -m app.schedulers.batch_jobs jobs-cleanup
```

## workers との違い

- `schedulers`
  - 定期実行される処理全般
  - cleanup のような運用ジョブをカテゴリ単位の CLI として起動する
- `workers`
  - キューから受け取った非同期ジョブを実行する

どちらもバックグラウンド処理ですが、`schedulers` は時間起点、`workers` はメッセージ起点です。

## 現在のカテゴリ

- `cleanup`
  - セッション、監査ログ、非同期ジョブ関連データなどの定期 cleanup を扱う

今後 cleanup 以外の定期実行カテゴリが増える場合も、同じ `app.schedulers` 配下で管理します。
