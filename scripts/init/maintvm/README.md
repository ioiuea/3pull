# Maint VM Setup Script

メンテナンス VM の初期セットアップで必要なツール導入をまとめて実行するスクリプトです。

対象:

- APT 前提パッケージの導入
- Azure CLI / Helm / ODBC Driver 18 の導入
- Docker / docker buildx の導入
- `uv` の導入
- `kubectl` / `kubelogin` の導入
- 導入確認コマンドの実行

使い方:

```bash
./scripts/init/maintvm/setup.sh
```

必要に応じて、以下の環境変数で version を固定できます。

```bash
KUBECTL_VERSION=v1.33.4 KUBELOGIN_VERSION=v0.2.12 ./scripts/init/maintvm/setup.sh
```

補足:

- `sudo` 権限が必要です。
- `docker` を `sudo` なしで使えるよう、実行ユーザーを `docker` グループへ追加します。反映には再ログインが必要です。
- `uv` はデフォルトで `~/.local/bin` に導入し、未設定なら `~/.bashrc` に PATH を追記します。
- backend 依存の `uv sync --frozen` や `az login` はこのスクリプトの対象外です。
