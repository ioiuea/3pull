# IP Rate Limit Ops

## 生成済み接続情報の読み込み

`infra/main.sh` 実行後は、必要に応じて次を読み込んでから実行します。

```bash
source scripts/ops/ip-rate-limit/generated.env.sh
```

`_common.sh` でも同じファイルを自動読込するため、通常は明示 `source` しなくても動作します。
ただし、別値で上書きしたい場合は `--host` / `--port` または環境変数を優先してください。

生成ファイルには少なくとも次が含まれます。

- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_OPS_MANAGED_IDENTITY_CLIENT_ID`
- `REDIS_OPS_MANAGED_IDENTITY_PRINCIPAL_ID`

このディレクトリは、IP ベース rate limit の block key 確認と解除に使う運用スクリプトを配置します。

配置スクリプト:

- `get-block.sh`
  - block key の存在、理由、TTL を確認します。
- `delete-block.sh`
  - block key を削除します。

共通前提:

- `redis-cli` が利用できること
- Azure Managed Redis がクラスタ構成の場合も動くよう、内部で `redis-cli -c` を利用します

認証モード:

- ローカル開発:
  - `az login` 済みの個人ユーザーで実行
  - `--auth-mode user`
- maint-vm:
  - `mi-<env>-<system>-redis-ops` を使って実行
  - `--auth-mode mi --login-managed-identity`
  - `generated.env.sh` から `REDIS_OPS_MANAGED_IDENTITY_CLIENT_ID` / `REDIS_OPS_MANAGED_IDENTITY_PRINCIPAL_ID` を読み込みます

指定できる `policy-key`:

- `email_login`
- `entra_login`
- `entra_callback`
- `password_reset_request`
- `password_reset_confirm`
- `email_signup`

例:

```bash
scripts/ops/ip-rate-limit/get-block.sh \
  --auth-mode user \
  --host redis-dev-example.japaneast.redis.azure.net \
  --policy-key email_login \
  --client-ip 127.0.0.1
```

```bash
scripts/ops/ip-rate-limit/delete-block.sh \
  --auth-mode user \
  --host redis-dev-example.japaneast.redis.azure.net \
  --policy-key email_login \
  --client-ip 127.0.0.1
```

maint-vm での例:

```bash
scripts/ops/ip-rate-limit/get-block.sh \
  --auth-mode mi \
  --login-managed-identity \
  --policy-key email_login \
  --client-ip 203.0.113.10
```
