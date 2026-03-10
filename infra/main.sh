#!/usr/bin/env bash
# このスクリプトは infra 配下の設定を読み込み、各 generate スクリプトで
# .bicepparam と meta.json を生成したうえで、依存順に az deployment を実行する。
if [[ -z "${BASH_VERSION:-}" ]]; then
  echo "This script must be run with bash. Use: bash ./main.sh" >&2
  exit 1
fi

set -euo pipefail

# -----------------------------------------------------------------------------
# ファイルパス設定
# -----------------------------------------------------------------------------
# infraルートパス
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
infra_root="$repo_root/infra"

# 共通入力・生成物・ログの基本パス
common_file="$infra_root/common.parameter.json"
params_dir="$infra_root/params"
logs_dir="$infra_root/logs"

# 共通パラメータの事前検証スクリプト
common_validation_script="$infra_root/scripts/validate-common-params.py"

# 監視系リソース（Log Analytics）
log_config_file="$infra_root/config/log-analytics.json"
log_script="$infra_root/scripts/generate-log-analytics-params.py"
log_meta_file="$params_dir/log-analytics-meta.json"

# 監視系リソース（Application Insights）
appi_config_file="$infra_root/config/application-insights.json"
appi_script="$infra_root/scripts/generate-application-insights-params.py"
appi_meta_file="$params_dir/application-insights-meta.json"

# ネットワーク基盤（Virtual Network）
vnet_config_file="$infra_root/config/virtual-network.json"
vnet_script="$infra_root/scripts/generate-virtual-network-params.py"
vnet_meta_file="$params_dir/virtual-network-meta.json"

# ネットワーク基盤（Subnets）
subnets_config_file="$infra_root/config/subnets.json"
subnets_script="$infra_root/scripts/generate-subnets-params.py"
subnets_meta_file="$params_dir/subnets-meta.json"

# ネットワーク基盤（Firewall）
firewall_config_file="$infra_root/config/firewall.json"
firewall_script="$infra_root/scripts/generate-firewall-params.py"
firewall_meta_file="$params_dir/firewall-meta.json"

# ネットワーク制御（Route Tables）
route_tables_config_file="$infra_root/config/route-tables.json"
route_tables_script="$infra_root/scripts/generate-route-tables-params.py"
route_tables_meta_file="$params_dir/route-tables-meta.json"

# ネットワーク制御（NSGs / Subnet Attachments）
nsgs_config_file="$infra_root/config/nsgs.json"
nsgs_script="$infra_root/scripts/generate-nsgs-params.py"
nsgs_meta_file="$params_dir/nsgs-meta.json"
subnet_attachments_script="$infra_root/scripts/generate-subnet-attachments-params.py"
subnet_attachments_meta_file="$params_dir/subnet-attachments-meta.json"

# 共通マネージド ID
managed_ids_config_file="$infra_root/config/managed-ids.json"
managed_ids_script="$infra_root/scripts/generate-managed-ids-params.py"
managed_ids_meta_file="$params_dir/managed-ids-meta.json"

# ネットワーク公開（Application Gateway / 低遅延 / RBAC）
application_gateway_config_file="$infra_root/config/application-gateway.json"
application_gateway_script="$infra_root/scripts/generate-application-gateway-params.py"
application_gateway_meta_file="$params_dir/application-gateway-meta.json"
application_gateway_low_latency_script="$infra_root/scripts/generate-application-gateway-low-latency-params.py"
application_gateway_low_latency_meta_file="$params_dir/application-gateway-low-latency-meta.json"
application_gateway_rbac_config_file="$infra_root/config/application-gateway-rbac.json"
application_gateway_rbac_script="$infra_root/scripts/generate-application-gateway-rbac-params.py"
application_gateway_rbac_meta_file="$params_dir/application-gateway-rbac-meta.json"

# コンテナ実行基盤（AKS）
aks_config_file="$infra_root/config/aks.json"
aks_runtime_config_file="$aks_config_file"
aks_script="$infra_root/scripts/generate-aks-params.py"
aks_meta_file="$params_dir/aks-meta.json"

# Workload Identity 用 Federated Credential
federated_credential_config_file="$infra_root/config/federated-credential.json"
federated_credential_script="$infra_root/scripts/generate-federated-credential-params.py"
federated_credential_meta_file="$params_dir/federated-credential-meta.json"

# コンテナレジストリ（ACR）
acr_config_file="$infra_root/config/acr.json"
acr_script="$infra_root/scripts/generate-acr-params.py"
acr_meta_file="$params_dir/acr-meta.json"

# シークレット情報管理（Key Vault）
key_vault_config_file="$infra_root/config/key-vault.json"
key_vault_script="$infra_root/scripts/generate-key-vault-params.py"
key_vault_meta_file="$params_dir/key-vault-meta.json"

# メッセージング（Service Bus）
service_bus_config_file="$infra_root/config/service-bus.json"
service_bus_script="$infra_root/scripts/generate-service-bus-params.py"
service_bus_meta_file="$params_dir/service-bus-meta.json"

# ストレージ（Storage Account）
storage_config_file="$infra_root/config/storage.json"
storage_script="$infra_root/scripts/generate-storage-params.py"
storage_meta_file="$params_dir/storage-meta.json"

# RDB（PostgreSQL）
postgres_config_file="$infra_root/config/postgres-database.json"
postgres_script="$infra_root/scripts/generate-postgres-database-params.py"
postgres_meta_file="$params_dir/postgres-database-meta.json"

# メンテナンス環境（VM）
maintenance_vm_config_file="$infra_root/config/maintenance-vm.json"
maintenance_vm_script="$infra_root/scripts/generate-maintenance-vm-params.py"
maintenance_vm_meta_file="$params_dir/maintenance-vm-meta.json"

# NoSQL（Cosmos DB）
cosmos_config_file="$infra_root/config/cosmos-database.json"
cosmos_script="$infra_root/scripts/generate-cosmos-database-params.py"
cosmos_meta_file="$params_dir/cosmos-database-meta.json"

# キャッシュ（Redis）
redis_config_file="$infra_root/config/redis.json"
redis_script="$infra_root/scripts/generate-redis-params.py"
redis_meta_file="$params_dir/redis-meta.json"

# AKS デプロイ後に生成する初期化スクリプトの出力先
init_scripts_root="$repo_root/scripts/init"
agic_controller_init_dir="$init_scripts_root/agicController"
keda_controller_init_dir="$init_scripts_root/kedaController"

# Helm values 生成（backend chart）
backend_values_template_file="$infra_root/config/backend-values.template.yaml"
backend_values_generated_file="$repo_root/k8s/charts/backend/values.yaml"
backend_values_sync_script="$infra_root/scripts/sync-backend-values.py"

# Helm values 生成（frontend chart）
frontend_values_template_file="$infra_root/config/frontend-values.template.yaml"
frontend_values_generated_file="$repo_root/k8s/charts/frontend/values.yaml"
frontend_values_sync_script="$infra_root/scripts/sync-frontend-values.py"

# helper モジュール
meta_access_lib="$infra_root/lib/meta-access.sh"
deploy_helpers_lib="$infra_root/lib/deploy-helpers.sh"
network_deployment_lib="$infra_root/lib/network-deployment.sh"
post_actions_lib="$infra_root/lib/post-actions.sh"

# -----------------------------------------------------------------------------
# 共通ヘルパー
# -----------------------------------------------------------------------------
# 必須値の空チェックを行い、未設定なら即時終了する。
# 引数:
#   $1: value_name
#       - エラーメッセージに出す項目名。例: "location", "resourceGroupName"
#   $2: value
#       - 検証対象の値（空文字かどうかを判定）。
#   $3: hint
#       - 補足メッセージ。どのファイル/設定を確認すべきかを示す文言。
# 挙動:
#   - value が非空なら何もせず return する。
#   - value が空なら標準エラーへメッセージを出力し、exit 1 で処理を停止する。
# 用途:
#   - Meta 読み出し結果など、後続処理で必須になる値の fail-fast 検証に使う。
require_non_empty() {
  local value_name="$1"
  local value="$2"
  local hint="$3"

  if [[ -n "$value" ]]; then
    return
  fi

  echo "$value_name が取得できませんでした。$hint" >&2
  exit 1
}

# Resource Group を重複排除しながら作成（存在時は noop）する。
# 引数:
#   $1: location
#       - `az group create --location` に渡す Azure リージョン名。
#   $2 以降: resource group 名の可変長リスト
#       - 重複を含んで渡してよい。関数内で一意化して処理する。
# 挙動:
#   - 渡された順序で走査し、同名 RG は 2 回目以降をスキップする。
#   - 一意な RG ごとに `az group create` を実行する。
# 出力/副作用:
#   - 各 RG について "==> Ensure Resource Group: <name>" を標準出力へ表示する。
#   - Azure 側に RG 作成 API を呼ぶ（既存 RG の場合は実質 no-op）。
# 実装メモ:
#   - Bash 3.2 互換のため連想配列は使わず、`|name|` 形式の文字列で重複判定する。
ensure_resource_groups() {
  local location="$1"
  shift

  local rg_name
  local seen_names="|"
  for rg_name in "$@"; do
    if [[ "$seen_names" == *"|$rg_name|"* ]]; then
      continue
    fi
    seen_names+="${rg_name}|"

    echo "==> Ensure Resource Group: $rg_name"
    az group create \
      --name "$rg_name" \
      --location "$location" >/dev/null
  done
}

# manifest 配列を順に解釈し、複数のパラメータ生成スクリプトを実行する。
# 引数:
#   $1 以降: manifest エントリの可変長リスト
#       - 各要素は `"script|out_meta_file|extra_envs"` 形式を想定する。
#       - extra_envs は省略可（空文字可）。
# 解析ルール:
#   - `|` 区切りで 3 要素に分解し、`run_param_generator` へ引き渡す。
#   - IFS を一時的に `|` に変更し、分解後に元へ戻す。
# 挙動:
#   - 配列順に直列実行する（依存順の制御は manifest の並びで表現する）。
#   - 途中の生成で失敗した場合は、その時点で全体を停止する（set -e）。
run_param_generation_manifest() {
  local entry
  local script
  local out_meta_file
  local extra_envs
  local previous_ifs

  for entry in "$@"; do
    previous_ifs="$IFS"
    IFS='|'
    read -r script out_meta_file extra_envs <<<"$entry"
    IFS="$previous_ifs"

    run_param_generator "$script" "$out_meta_file" "$extra_envs"
  done
}

# 1リソース分のパラメータ生成スクリプトを、共通環境変数付きで実行する。
# 引数:
#   $1: script
#       - 実行する generate スクリプトのパス。
#   $2: out_meta_file
#       - 生成スクリプトへ渡す `OUT_META_FILE` の出力先パス。
#   $3: extra_envs（省略可）
#       - 追加で渡す環境変数の連結文字列。
#       - 形式: "KEY1=VAL1;KEY2=VAL2;..."
#       - 区切りは `;`、空要素は無視する。
# 挙動:
#   - 共通環境変数（COMMON_FILE / PARAMS_DIR / OUT_META_FILE / TIMESTAMP）を必ず付与する。
#   - extra_envs を分解して追加し、`env ... "$script"` 形式で実行する。
# 出力/副作用:
#   - 生成スクリプト側の標準出力/標準エラーはそのまま親プロセスへ流れる。
#   - 生成スクリプトの終了コードをそのまま返す（set -e により失敗時は全体停止）。
run_param_generator() {
  local script="$1"
  local out_meta_file="$2"
  local extra_envs="${3:-}"
  local -a env_args
  local env_kv

  env_args=(
    "COMMON_FILE=$common_file"
    "PARAMS_DIR=$params_dir"
    "OUT_META_FILE=$out_meta_file"
    "TIMESTAMP=$timestamp"
  )

  if [[ -n "$extra_envs" ]]; then
    local previous_ifs="$IFS"
    IFS=';'
    for env_kv in $extra_envs; do
      [[ -n "$env_kv" ]] && env_args+=("$env_kv")
    done
    IFS="$previous_ifs"
  fi

  env "${env_args[@]}" "$script"
}

# AKS 構成ファイルを実行時に補正し、利用可能な AZ を runtime config へ反映する。
# 入力:
#   - common.parameter.json から location / aks.userPoolVmSize
#   - infra/config/aks.json から agentPoolVmSize
# 挙動:
#   - 必須値が欠ける場合は自動補正をスキップし、元設定を維持する。
#   - get_subscription_available_zones_json を使って agent/user pool の可用ゾーンを解決する。
#   - 解決できた pool のみ `agentPoolAvailabilityZones` / `userPoolAvailabilityZones` を上書きする。
# 出力/副作用:
#   - `${params_dir}/aks-runtime-config.json` を生成/更新する。
#   - `aks_runtime_config_file` を runtime ファイルに差し替え、
#     以降の AKS パラメータ生成でこちらを参照する。
update_aks_availability_zones() {
  local location
  local agent_pool_vm_size
  local user_pool_vm_size
  local agent_zones_json
  local user_zones_json

  location="$(COMMON_FILE="$common_file" python - <<'PY'
import json
import os
from pathlib import Path

common = json.loads(Path(os.environ["COMMON_FILE"]).read_text(encoding="utf-8"))
print(str(common.get("common", {}).get("location", "")).strip())
PY
)"

  agent_pool_vm_size="$(AKS_CONFIG_FILE="$aks_config_file" python - <<'PY'
import json
import os
from pathlib import Path

config = json.loads(Path(os.environ["AKS_CONFIG_FILE"]).read_text(encoding="utf-8"))
print(str(config.get("agentPoolVmSize", "")).strip())
PY
)"

  user_pool_vm_size="$(COMMON_FILE="$common_file" AKS_CONFIG_FILE="$aks_config_file" python - <<'PY'
import json
import os
from pathlib import Path

config = json.loads(Path(os.environ["AKS_CONFIG_FILE"]).read_text(encoding="utf-8"))
common = json.loads(Path(os.environ["COMMON_FILE"]).read_text(encoding="utf-8"))
print(str(common.get("aks", {}).get("userPoolVmSize", "")).strip())
PY
)"

  if [[ -z "$location" || -z "$agent_pool_vm_size" || -z "$user_pool_vm_size" ]]; then
    echo "==> Skip AKS availability zones auto-detect (required settings are missing)"
    return
  fi

  echo "==> Resolve AKS availability zones dynamically"
  agent_zones_json="$(get_subscription_available_zones_json "$location" "$agent_pool_vm_size")"
  user_zones_json="$(get_subscription_available_zones_json "$location" "$user_pool_vm_size")"

  if [[ "$agent_zones_json" == "[]" ]]; then
    echo "    - agent pool zones were not resolved for ${agent_pool_vm_size}; keep current values"
  fi
  if [[ "$user_zones_json" == "[]" ]]; then
    echo "    - user pool zones were not resolved for ${user_pool_vm_size}; keep current values"
  fi

  local runtime_aks_config_file="$params_dir/aks-runtime-config.json"

  AKS_CONFIG_FILE="$aks_config_file" \
  OUT_AKS_CONFIG_FILE="$runtime_aks_config_file" \
  AGENT_ZONES_JSON="$agent_zones_json" \
  USER_ZONES_JSON="$user_zones_json" \
  python - <<'PY'
import json
import os
from pathlib import Path

source_path = Path(os.environ["AKS_CONFIG_FILE"])
out_path = Path(os.environ["OUT_AKS_CONFIG_FILE"])
config = json.loads(source_path.read_text(encoding="utf-8"))

agent = json.loads(os.environ.get("AGENT_ZONES_JSON", "[]"))
user = json.loads(os.environ.get("USER_ZONES_JSON", "[]"))

if isinstance(agent, list) and agent:
    config["agentPoolAvailabilityZones"] = [str(zone) for zone in agent]

if isinstance(user, list) and user:
    config["userPoolAvailabilityZones"] = [str(zone) for zone in user]

out_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

  aks_runtime_config_file="$runtime_aks_config_file"
}

# 指定 VM SKU について、サブスクリプションで実際に利用可能な AZ 一覧を JSON 配列で返す。
# 引数:
#   $1: location
#       - Azure リージョン名。例: japaneast
#   $2: vm_size
#       - VM SKU 名。例: Standard_D4s_v5
# 出力:
#   - 例: ["1","2","3"] の JSON 文字列を標準出力へ出力する。
#   - SKU 情報を取得できない場合や解析失敗時は [] を返す。
# 判定ロジック:
#   - az vm list-skus の zones から候補を取得。
#   - restrictions.reasonCode == NotAvailableForSubscription の zone を除外。
#   - 差集合をソートして返す。
get_subscription_available_zones_json() {
  local location="$1"
  local vm_size="$2"

  az vm list-skus \
    --location "$location" \
    --resource-type virtualMachines \
    --all \
    --query "[?name=='$vm_size'] | [0].{zones:locationInfo[0].zones,restrictions:restrictions}" \
    -o json \
    --only-show-errors 2>/dev/null | python - <<'PY'
import json
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    print("[]")
    raise SystemExit(0)

all_zones = set(data.get("zones") or [])
deny_zones = set()
for restriction in data.get("restrictions") or []:
    if restriction.get("reasonCode") != "NotAvailableForSubscription":
        continue
    info = restriction.get("restrictionInfo") or {}
    for zone in info.get("zones") or restriction.get("values") or []:
        deny_zones.add(zone)

print(json.dumps(sorted(all_zones - deny_zones)))
PY
}

# -----------------------------------------------------------------------------
# 事前チェック
# -----------------------------------------------------------------------------
# 1) 実行オプションを解析する。
#    - 入力: スクリプト引数 ($@)
#    - 出力: 変数 what_if ("--what-if" または空文字)
# 現在は --what-if のみ受け付け、未知の引数は即時エラーにする。
what_if=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --what-if)
      what_if="--what-if"
      shift
      ;;
    *)
      echo "許可されていない引数です: $1" >&2
      echo "利用可能な引数: --what-if" >&2
      exit 1
      ;;
  esac
done

# 2) 共通入力ファイルを検証する。
#    common.parameter.json と validator スクリプトがそろっていることを確認する。
if [[ ! -f "$common_file" ]]; then
  echo "common parameter file が見つかりません: $common_file" >&2
  exit 1
fi

if [[ ! -f "$common_validation_script" ]]; then
  echo "common parameter validation script が見つかりません: $common_validation_script" >&2
  exit 1
fi

# 3) common.parameter.json の内容を検証する。
#    必須キー不足や型不整合を、この時点で明示的に失敗させる。
echo "==> Validate common parameters"
"$common_validation_script" "$common_file"

# 4) ログ出力先ディレクトリを作成する（既存の場合は何もしない）。
mkdir -p "$logs_dir"

# 5) 各リソースの固定設定 / 生成スクリプト / テンプレートの存在確認。
#    途中で missing file により処理が止まらないよう、ここで一括検証する。
if [[ ! -f "$log_config_file" ]]; then
  echo "log analytics config file が見つかりません: $log_config_file" >&2
  exit 1
fi

if [[ ! -f "$appi_config_file" ]]; then
  echo "application insights config file が見つかりません: $appi_config_file" >&2
  exit 1
fi

if [[ ! -f "$vnet_config_file" ]]; then
  echo "virtual network config file が見つかりません: $vnet_config_file" >&2
  exit 1
fi

if [[ ! -f "$subnets_config_file" ]]; then
  echo "subnets config file が見つかりません: $subnets_config_file" >&2
  exit 1
fi

if [[ ! -f "$firewall_config_file" ]]; then
  echo "firewall config file が見つかりません: $firewall_config_file" >&2
  exit 1
fi

if [[ ! -f "$application_gateway_config_file" ]]; then
  echo "application gateway config file が見つかりません: $application_gateway_config_file" >&2
  exit 1
fi

if [[ ! -f "$application_gateway_low_latency_script" ]]; then
  echo "application gateway low latency script が見つかりません: $application_gateway_low_latency_script" >&2
  exit 1
fi

if [[ ! -f "$application_gateway_rbac_config_file" ]]; then
  echo "application gateway rbac config file が見つかりません: $application_gateway_rbac_config_file" >&2
  exit 1
fi

if [[ ! -f "$application_gateway_rbac_script" ]]; then
  echo "application gateway rbac script が見つかりません: $application_gateway_rbac_script" >&2
  exit 1
fi

if [[ ! -f "$managed_ids_config_file" ]]; then
  echo "managed ids config file が見つかりません: $managed_ids_config_file" >&2
  exit 1
fi

if [[ ! -f "$managed_ids_script" ]]; then
  echo "managed ids script が見つかりません: $managed_ids_script" >&2
  exit 1
fi

if [[ ! -f "$key_vault_config_file" ]]; then
  echo "key vault config file が見つかりません: $key_vault_config_file" >&2
  exit 1
fi

if [[ ! -f "$service_bus_config_file" ]]; then
  echo "service bus config file が見つかりません: $service_bus_config_file" >&2
  exit 1
fi

if [[ ! -f "$acr_config_file" ]]; then
  echo "acr config file が見つかりません: $acr_config_file" >&2
  exit 1
fi

if [[ ! -f "$storage_config_file" ]]; then
  echo "storage config file が見つかりません: $storage_config_file" >&2
  exit 1
fi

if [[ ! -f "$redis_config_file" ]]; then
  echo "redis config file が見つかりません: $redis_config_file" >&2
  exit 1
fi

if [[ ! -f "$postgres_config_file" ]]; then
  echo "postgres config file が見つかりません: $postgres_config_file" >&2
  exit 1
fi

if [[ ! -f "$cosmos_config_file" ]]; then
  echo "cosmos config file が見つかりません: $cosmos_config_file" >&2
  exit 1
fi

if [[ ! -f "$aks_config_file" ]]; then
  echo "aks config file が見つかりません: $aks_config_file" >&2
  exit 1
fi

if [[ ! -f "$route_tables_config_file" ]]; then
  echo "route tables config file が見つかりません: $route_tables_config_file" >&2
  exit 1
fi

if [[ ! -f "$nsgs_config_file" ]]; then
  echo "nsgs config file が見つかりません: $nsgs_config_file" >&2
  exit 1
fi

if [[ ! -f "$maintenance_vm_config_file" ]]; then
  echo "maintenance vm config file が見つかりません: $maintenance_vm_config_file" >&2
  exit 1
fi

if [[ ! -f "$federated_credential_config_file" ]]; then
  echo "federated credential config file が見つかりません: $federated_credential_config_file" >&2
  exit 1
fi

if [[ ! -f "$federated_credential_script" ]]; then
  echo "federated credential script が見つかりません: $federated_credential_script" >&2
  exit 1
fi

if [[ ! -f "$backend_values_sync_script" ]]; then
  echo "backend values sync script が見つかりません: $backend_values_sync_script" >&2
  exit 1
fi

if [[ ! -f "$backend_values_template_file" ]]; then
  echo "backend Helm values template file が見つかりません: $backend_values_template_file" >&2
  exit 1
fi

if [[ ! -f "$frontend_values_sync_script" ]]; then
  echo "frontend values sync script が見つかりません: $frontend_values_sync_script" >&2
  exit 1
fi

if [[ ! -f "$frontend_values_template_file" ]]; then
  echo "frontend Helm values template file が見つかりません: $frontend_values_template_file" >&2
  exit 1
fi

# 6) 実行環境の必須コマンド確認。
#    このスクリプトは az CLI に依存するため、未インストール時は継続不可。
if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI (az) が見つかりません。" >&2
  exit 1
fi

# 7) ライブラリファイルの存在確認。
#    source 前にファイル有無をチェックし、読み込みエラーを分かりやすくする。
if [[ ! -f "$meta_access_lib" ]]; then
  echo "meta access helper script が見つかりません: $meta_access_lib" >&2
  exit 1
fi

if [[ ! -f "$deploy_helpers_lib" ]]; then
  echo "deploy helper script が見つかりません: $deploy_helpers_lib" >&2
  exit 1
fi

if [[ ! -f "$network_deployment_lib" ]]; then
  echo "network deployment helper script が見つかりません: $network_deployment_lib" >&2
  exit 1
fi

if [[ ! -f "$post_actions_lib" ]]; then
  echo "post actions helper script が見つかりません: $post_actions_lib" >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# 共通ライブラリ読み込み
# -----------------------------------------------------------------------------
# 後続フェーズで利用する関数群を有効化する。
# meta.json 参照ヘルパー（meta_get / meta_bool / meta_get_stripped）
source "$meta_access_lib"
# Bicep デプロイ実行ヘルパー（deploy_group_if_enabled / run_bicep_deployment）
source "$deploy_helpers_lib"
# ネットワーク関連デプロイ処理（VNET/Subnets/Firewall/RouteTables/NSG など）
source "$network_deployment_lib"
# デプロイ後処理ヘルパー（Helm values 同期、追加構成処理）
source "$post_actions_lib"

# -----------------------------------------------------------------------------
# パラメータ生成
# -----------------------------------------------------------------------------
# 各 Python スクリプトが以下を出力する:
# - params/*.bicepparam (Bicep 実行引数)
# - params/*-meta.json  (deploy 可否、RG 名などの制御情報)

# 生成ログのファイル名に使う実行時刻（例: 20260310T123456）
timestamp="$(date +'%Y%m%dT%H%M%S')"

# パラメータ出力先ディレクトリを作成（既存の場合はそのまま）
mkdir -p "$params_dir"

# AKS 設定の availability zones を、サブスクリプション実態に合わせて事前補正する。
update_aks_availability_zones

# 生成対象と依存関係の manifest。
# 1要素の形式: "generator_script|meta_output_file|ENV1=...;ENV2=..."
# run_param_generation_manifest が先頭から順に実行し、必要な環境変数を渡す。
param_generation_manifest=(
  "$log_script|$log_meta_file|RESOURCE_CONFIG_FILE=$log_config_file"
  "$appi_script|$appi_meta_file|RESOURCE_CONFIG_FILE=$appi_config_file"
  "$vnet_script|$vnet_meta_file|RESOURCE_CONFIG_FILE=$vnet_config_file"
  "$subnets_script|$subnets_meta_file|RESOURCE_CONFIG_FILE=$subnets_config_file"
  "$firewall_script|$firewall_meta_file|RESOURCE_CONFIG_FILE=$firewall_config_file;SUBNETS_CONFIG_FILE=$subnets_config_file"
  "$managed_ids_script|$managed_ids_meta_file|RESOURCE_CONFIG_FILE=$managed_ids_config_file"
  "$application_gateway_script|$application_gateway_meta_file|RESOURCE_CONFIG_FILE=$application_gateway_config_file;SUBNETS_CONFIG_FILE=$subnets_config_file"
  "$application_gateway_low_latency_script|$application_gateway_low_latency_meta_file|RESOURCE_CONFIG_FILE=$application_gateway_config_file;SUBNETS_CONFIG_FILE=$subnets_config_file"
  "$redis_script|$redis_meta_file|RESOURCE_CONFIG_FILE=$redis_config_file"
  "$postgres_script|$postgres_meta_file|RESOURCE_CONFIG_FILE=$postgres_config_file"
  "$cosmos_script|$cosmos_meta_file|RESOURCE_CONFIG_FILE=$cosmos_config_file"
  "$aks_script|$aks_meta_file|RESOURCE_CONFIG_FILE=$aks_runtime_config_file;SUBNETS_CONFIG_FILE=$subnets_config_file;APPLICATION_GATEWAY_META_FILE=$application_gateway_meta_file"
  "$application_gateway_rbac_script|$application_gateway_rbac_meta_file|RESOURCE_CONFIG_FILE=$application_gateway_rbac_config_file;MANAGED_IDS_META_FILE=$managed_ids_meta_file;APPLICATION_GATEWAY_META_FILE=$application_gateway_meta_file;APPLICATION_GATEWAY_LOW_LATENCY_META_FILE=$application_gateway_low_latency_meta_file"
  "$acr_script|$acr_meta_file|RESOURCE_CONFIG_FILE=$acr_config_file;AKS_META_FILE=$aks_meta_file"
  "$key_vault_script|$key_vault_meta_file|RESOURCE_CONFIG_FILE=$key_vault_config_file;MANAGED_IDS_META_FILE=$managed_ids_meta_file"
  "$service_bus_script|$service_bus_meta_file|RESOURCE_CONFIG_FILE=$service_bus_config_file;MANAGED_IDS_META_FILE=$managed_ids_meta_file"
  "$storage_script|$storage_meta_file|RESOURCE_CONFIG_FILE=$storage_config_file;MANAGED_IDS_META_FILE=$managed_ids_meta_file"
  "$route_tables_script|$route_tables_meta_file|RESOURCE_CONFIG_FILE=$route_tables_config_file;SUBNETS_CONFIG_FILE=$subnets_config_file;FIREWALL_META_FILE=$firewall_meta_file"
  "$nsgs_script|$nsgs_meta_file|RESOURCE_CONFIG_FILE=$nsgs_config_file;SUBNETS_CONFIG_FILE=$subnets_config_file"
  "$subnet_attachments_script|$subnet_attachments_meta_file|SUBNETS_CONFIG_FILE=$subnets_config_file;ROUTE_TABLES_CONFIG_FILE=$route_tables_config_file;NSGS_CONFIG_FILE=$nsgs_config_file"
  "$maintenance_vm_script|$maintenance_vm_meta_file|RESOURCE_CONFIG_FILE=$maintenance_vm_config_file;SUBNETS_CONFIG_FILE=$subnets_config_file"
)

# manifest 定義に従って .bicepparam / meta.json を一括生成する。
run_param_generation_manifest "${param_generation_manifest[@]}"

# -----------------------------------------------------------------------------
# メタ情報読み込みと検証
# -----------------------------------------------------------------------------
# 1) 生成済み meta.json から、デプロイ全体で使う location を取得する。
#    ここでは log analytics の meta を基準値として扱う。
location="$(meta_get "$log_meta_file" "location")"

# 2) 各リソース用の resourceGroupName を meta.json から読み込む。
#    後続の RG 作成とデプロイ実行で利用するため、ここで一括取得する。
resource_group_name="$(meta_get "$log_meta_file" "resourceGroupName")"
vnet_resource_group_name="$(meta_get "$vnet_meta_file" "resourceGroupName")"
subnets_resource_group_name="$(meta_get "$subnets_meta_file" "resourceGroupName")"
firewall_resource_group_name="$(meta_get "$firewall_meta_file" "resourceGroupName")"
managed_ids_resource_group_name="$(meta_get "$managed_ids_meta_file" "resourceGroupName")"
application_gateway_resource_group_name="$(meta_get "$application_gateway_meta_file" "resourceGroupName")"
application_gateway_rbac_resource_group_name="$(meta_get "$application_gateway_rbac_meta_file" "resourceGroupName")"
key_vault_resource_group_name="$(meta_get "$key_vault_meta_file" "resourceGroupName")"
service_bus_resource_group_name="$(meta_get "$service_bus_meta_file" "resourceGroupName")"
acr_resource_group_name="$(meta_get "$acr_meta_file" "resourceGroupName")"
storage_resource_group_name="$(meta_get "$storage_meta_file" "resourceGroupName")"
redis_resource_group_name="$(meta_get "$redis_meta_file" "resourceGroupName")"
postgres_resource_group_name="$(meta_get "$postgres_meta_file" "resourceGroupName")"
cosmos_resource_group_name="$(meta_get "$cosmos_meta_file" "resourceGroupName")"
aks_resource_group_name="$(meta_get "$aks_meta_file" "resourceGroupName")"
route_tables_resource_group_name="$(meta_get "$route_tables_meta_file" "resourceGroupName")"
nsgs_resource_group_name="$(meta_get "$nsgs_meta_file" "resourceGroupName")"
subnet_attachments_resource_group_name="$(meta_get "$subnet_attachments_meta_file" "resourceGroupName")"
maintenance_vm_resource_group_name="$(meta_get "$maintenance_vm_meta_file" "resourceGroupName")"

# 3) 必須メタ情報の空チェック。
#    ここで失敗させることで、後続フェーズの az コマンド失敗を未然に防ぐ。
require_non_empty "location" "$location" "infra/common.parameter.json を確認してください。"
require_non_empty "resourceGroupName" "$resource_group_name" "config を確認してください。"
require_non_empty "vnet resourceGroupName" "$vnet_resource_group_name" "config を確認してください。"
require_non_empty "subnets resourceGroupName" "$subnets_resource_group_name" "config を確認してください。"
require_non_empty "firewall resourceGroupName" "$firewall_resource_group_name" "config を確認してください。"
require_non_empty "managed ids resourceGroupName" "$managed_ids_resource_group_name" "config を確認してください。"
require_non_empty "application gateway resourceGroupName" "$application_gateway_resource_group_name" "config を確認してください。"
require_non_empty "application gateway rbac resourceGroupName" "$application_gateway_rbac_resource_group_name" "config を確認してください。"
require_non_empty "key vault resourceGroupName" "$key_vault_resource_group_name" "config を確認してください。"
require_non_empty "service bus resourceGroupName" "$service_bus_resource_group_name" "config を確認してください。"
require_non_empty "acr resourceGroupName" "$acr_resource_group_name" "config を確認してください。"
require_non_empty "storage resourceGroupName" "$storage_resource_group_name" "config を確認してください。"
require_non_empty "redis resourceGroupName" "$redis_resource_group_name" "config を確認してください。"
require_non_empty "postgres resourceGroupName" "$postgres_resource_group_name" "config を確認してください。"
require_non_empty "cosmos resourceGroupName" "$cosmos_resource_group_name" "config を確認してください。"
require_non_empty "aks resourceGroupName" "$aks_resource_group_name" "config を確認してください。"
require_non_empty "route tables resourceGroupName" "$route_tables_resource_group_name" "config を確認してください。"
require_non_empty "nsgs resourceGroupName" "$nsgs_resource_group_name" "config を確認してください。"
require_non_empty "subnet attachments resourceGroupName" "$subnet_attachments_resource_group_name" "config を確認してください。"
require_non_empty "maintenance vm resourceGroupName" "$maintenance_vm_resource_group_name" "config を確認してください。"

# 4) location が Azure で有効なリージョン名かを検証する。
#    タイポや廃止リージョン指定を早期に検知するため、az の一覧と突き合わせる。
available_locations="$(az account list-locations --query "[].name" -o tsv)"
if ! printf '%s\n' "$available_locations" | grep -qx "$location"; then
  echo "location が Azure のリージョン名ではありません: $location" >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# リソースグループ準備
# -----------------------------------------------------------------------------
# 各リソースが利用する Resource Group を事前作成する。
# - 第1引数: location（RG 作成リージョン）
# - 第2引数以降: 作成対象の RG 名一覧
# 既存 RG がある場合は `az group create` が冪等に処理するため、そのまま継続する。
ensure_resource_groups "$location" \
  "$resource_group_name" \
  "$vnet_resource_group_name" \
  "$subnets_resource_group_name" \
  "$firewall_resource_group_name" \
  "$managed_ids_resource_group_name" \
  "$application_gateway_resource_group_name" \
  "$key_vault_resource_group_name" \
  "$acr_resource_group_name" \
  "$service_bus_resource_group_name" \
  "$storage_resource_group_name" \
  "$redis_resource_group_name" \
  "$postgres_resource_group_name" \
  "$cosmos_resource_group_name" \
  "$aks_resource_group_name" \
  "$route_tables_resource_group_name" \
  "$nsgs_resource_group_name" \
  "$subnet_attachments_resource_group_name" \
  "$maintenance_vm_resource_group_name"

# -----------------------------------------------------------------------------
# Monitor resources
# -----------------------------------------------------------------------------
# Log Analytics -> Application Insights の順で実行する。
log_deploy="$(meta_bool "$log_meta_file" "deploy")"

log_params_file="$(meta_get "$log_meta_file" "paramsFile")"

appi_deploy="$(meta_bool "$appi_meta_file" "deploy")"

appi_params_file="$(meta_get "$appi_meta_file" "paramsFile")"

deploy_group_if_enabled \
  "$log_deploy" \
  "Deploy Log Analytics" \
  "log-analytics" \
  "main-monitor-log-analytics-${timestamp}" \
  "$resource_group_name" \
  "$log_params_file" \
  "Skip Log Analytics (resourceToggles.logAnalytics=false)"

deploy_group_if_enabled \
  "$appi_deploy" \
  "Deploy Application Insights" \
  "application-insights" \
  "main-monitor-application-insights-${timestamp}" \
  "$resource_group_name" \
  "$appi_params_file" \
  "Skip Application Insights (resourceToggles.applicationInsights=false)"

# -----------------------------------------------------------------------------
# Network (VNET/Subnets/Firewall/UDR/NSG)
# -----------------------------------------------------------------------------
run_virtual_network_deployment
run_subnets_base_deployment
run_firewall_deployment
run_route_tables_nsgs_subnet_attachments

# -----------------------------------------------------------------------------
# その他リソース
# -----------------------------------------------------------------------------
# 依存順:
# 1) Managed IDs
# 2) Application Gateway
# 3) Application Gateway RBAC (Managed IDs に App Gateway 更新権限を付与)
# 4) AKS
# 5) ACR (ACR RG スコープで AKS kubelet へ AcrPull を付与)
# 6) Key Vault (Private Endpoint 用サブネットが先に必要)
# 7) Service Bus (Private Endpoint 用サブネットが先に必要)
# 8) Storage Account (Private Endpoint 用サブネットが先に必要)
# 9) PostgreSQL Flexible Server (Private Endpoint 用サブネットが先に必要)
# 10) Maintenance VM
# 11) Cosmos DB (Private Endpoint 用サブネットが先に必要)
# 12) Redis (Private Endpoint 用サブネットが先に必要)

# -----------------------------------------------------------------------------
# Managed IDs
# -----------------------------------------------------------------------------
managed_ids_deploy="$(meta_bool "$managed_ids_meta_file" "deploy")"

managed_ids_params_file="$(meta_get "$managed_ids_meta_file" "paramsFile")"

deploy_group_if_enabled \
  "$managed_ids_deploy" \
  "Deploy Managed IDs" \
  "managed-ids" \
  "main-service-managed-ids-${timestamp}" \
  "$managed_ids_resource_group_name" \
  "$managed_ids_params_file" \
  "Skip Managed IDs (resourceToggles.managedIds=false)"

# -----------------------------------------------------------------------------
# Application Gateway
# -----------------------------------------------------------------------------
deploy_group_if_enabled \
  "$application_gateway_deploy" \
  "Deploy Application Gateway" \
  "application-gateway" \
  "main-network-application-gateway-${timestamp}" \
  "$application_gateway_resource_group_name" \
  "$application_gateway_params_file" \
  "Skip Application Gateway (resourceToggles.applicationGateway=false)"

deploy_group_if_enabled \
  "$application_gateway_low_latency_deploy" \
  "Deploy Application Gateway (Low Latency)" \
  "application-gateway-low-latency" \
  "main-network-application-gateway-low-latency-${timestamp}" \
  "$application_gateway_resource_group_name" \
  "$application_gateway_low_latency_params_file" \
  "Skip Application Gateway (Low Latency)"

# -----------------------------------------------------------------------------
# Application Gateway RBAC
# -----------------------------------------------------------------------------
COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$application_gateway_rbac_config_file" \
MANAGED_IDS_META_FILE="$managed_ids_meta_file" \
APPLICATION_GATEWAY_META_FILE="$application_gateway_meta_file" \
APPLICATION_GATEWAY_LOW_LATENCY_META_FILE="$application_gateway_low_latency_meta_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$application_gateway_rbac_meta_file" \
TIMESTAMP="$timestamp" \
"$application_gateway_rbac_script"

application_gateway_rbac_deploy="$(meta_bool "$application_gateway_rbac_meta_file" "deploy")"

application_gateway_rbac_params_file="$(meta_get "$application_gateway_rbac_meta_file" "paramsFile")"

deploy_group_if_enabled \
  "$application_gateway_rbac_deploy" \
  "Deploy Application Gateway RBAC" \
  "application-gateway-rbac" \
  "main-service-application-gateway-rbac-${timestamp}" \
  "$application_gateway_rbac_resource_group_name" \
  "$application_gateway_rbac_params_file" \
  "Skip Application Gateway RBAC (resourceToggles.applicationGateway=false or required managed identities not found)"

# -----------------------------------------------------------------------------
# AKS
# -----------------------------------------------------------------------------
aks_deploy="$(meta_bool "$aks_meta_file" "deploy")"

aks_params_file="$(meta_get "$aks_meta_file" "paramsFile")"

deploy_group_if_enabled \
  "$aks_deploy" \
  "Deploy AKS" \
  "aks" \
  "main-service-aks-${timestamp}" \
  "$aks_resource_group_name" \
  "$aks_params_file" \
  "Skip AKS (resourceToggles.aks=false)"

# -----------------------------------------------------------------------------
# Federated Credential (AKS 関連)
# -----------------------------------------------------------------------------
federated_credential_deploy="false"
if [[ "$aks_deploy" == "true" ]]; then
  if [[ -n "$what_if" ]]; then
    echo "==> Skip Federated Credential (--what-if)"
  else
    COMMON_FILE="$common_file" \
    RESOURCE_CONFIG_FILE="$federated_credential_config_file" \
    AKS_META_FILE="$aks_meta_file" \
    PARAMS_DIR="$params_dir" \
    OUT_META_FILE="$federated_credential_meta_file" \
    TIMESTAMP="$timestamp" \
    "$federated_credential_script"

    federated_credential_deploy="$(meta_bool "$federated_credential_meta_file" "deploy")"

    federated_credential_params_file="$(meta_get "$federated_credential_meta_file" "paramsFile")"

    if [[ "$federated_credential_deploy" == "true" ]]; then
      echo "==> Deploy Federated Credential"
      run_bicep_deployment "federated-credential" az deployment group create \
        --name "main-service-federated-credential-${timestamp}" \
        --resource-group "$aks_resource_group_name" \
        --parameters "$federated_credential_params_file"
    else
      echo "==> Skip Federated Credential (required managed identities not found or resourceToggles.aks=false or config.enabled=false)"
    fi
  fi
else
  echo "==> Skip Federated Credential (requires resourceToggles.aks=true)"
fi

# -----------------------------------------------------------------------------
# ACR
# -----------------------------------------------------------------------------
acr_deploy="$(meta_bool "$acr_meta_file" "deploy")"

acr_params_file="$(meta_get "$acr_meta_file" "paramsFile")"

deploy_group_if_enabled \
  "$acr_deploy" \
  "Deploy ACR" \
  "acr" \
  "main-service-acr-${timestamp}" \
  "$acr_resource_group_name" \
  "$acr_params_file" \
  "Skip ACR (resourceToggles.acr=false)"

# -----------------------------------------------------------------------------
# Key Vault
# -----------------------------------------------------------------------------
COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$key_vault_config_file" \
MANAGED_IDS_META_FILE="$managed_ids_meta_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$key_vault_meta_file" \
TIMESTAMP="$timestamp" \
"$key_vault_script"

key_vault_deploy="$(meta_bool "$key_vault_meta_file" "deploy")"

key_vault_params_file="$(meta_get "$key_vault_meta_file" "paramsFile")"

deploy_group_if_enabled \
  "$key_vault_deploy" \
  "Deploy Key Vault" \
  "key-vault" \
  "main-service-key-vault-${timestamp}" \
  "$key_vault_resource_group_name" \
  "$key_vault_params_file" \
  "Skip Key Vault (resourceToggles.keyVault=false)"

# -----------------------------------------------------------------------------
# Service Bus
# -----------------------------------------------------------------------------
COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$service_bus_config_file" \
MANAGED_IDS_META_FILE="$managed_ids_meta_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$service_bus_meta_file" \
TIMESTAMP="$timestamp" \
"$service_bus_script"

service_bus_deploy="$(meta_bool "$service_bus_meta_file" "deploy")"

service_bus_params_file="$(meta_get "$service_bus_meta_file" "paramsFile")"

deploy_group_if_enabled \
  "$service_bus_deploy" \
  "Deploy Service Bus" \
  "service-bus" \
  "main-service-service-bus-${timestamp}" \
  "$service_bus_resource_group_name" \
  "$service_bus_params_file" \
  "Skip Service Bus (resourceToggles.serviceBus=false)"

# -----------------------------------------------------------------------------
# Storage Account
# -----------------------------------------------------------------------------
COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$storage_config_file" \
MANAGED_IDS_META_FILE="$managed_ids_meta_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$storage_meta_file" \
TIMESTAMP="$timestamp" \
"$storage_script"

storage_deploy="$(meta_bool "$storage_meta_file" "deploy")"

storage_params_file="$(meta_get "$storage_meta_file" "paramsFile")"

deploy_group_if_enabled \
  "$storage_deploy" \
  "Deploy Storage Account" \
  "storage" \
  "main-service-storage-${timestamp}" \
  "$storage_resource_group_name" \
  "$storage_params_file" \
  "Skip Storage Account (resourceToggles.storage=false)"

# -----------------------------------------------------------------------------
# PostgreSQL Flexible Server
# -----------------------------------------------------------------------------
postgres_deploy="$(meta_bool "$postgres_meta_file" "deploy")"

postgres_params_file="$(meta_get "$postgres_meta_file" "paramsFile")"

if [[ "$postgres_deploy" == "true" ]]; then
  if [[ -z "${POSTGRES_ADMIN_PASSWORD:-}" ]]; then
    echo "POSTGRES_ADMIN_PASSWORD が未設定です。" >&2
    echo "例: POSTGRES_ADMIN_PASSWORD='YourStrongPassword!' ./main.sh --what-if" >&2
    exit 1
  fi

  echo "==> Deploy PostgreSQL Flexible Server"
  run_bicep_deployment "postgres-database" az deployment group create \
    --name "main-service-postgres-database-${timestamp}" \
    --resource-group "$postgres_resource_group_name" \
    --parameters "$postgres_params_file" \
    --parameters administratorPassword="$POSTGRES_ADMIN_PASSWORD" \
    ${what_if:+$what_if}
else
  echo "==> Skip PostgreSQL Flexible Server (resourceToggles.postgresDatabase=false)"
fi

# -----------------------------------------------------------------------------
# Maintenance VM
# -----------------------------------------------------------------------------
maintenance_vm_deploy="$(meta_bool "$maintenance_vm_meta_file" "deploy")"

maintenance_vm_params_file="$(meta_get "$maintenance_vm_meta_file" "paramsFile")"

if [[ "$maintenance_vm_deploy" == "true" ]]; then
  if [[ -z "${MAINT_VM_ADMIN_PASSWORD:-}" ]]; then
    echo "MAINT_VM_ADMIN_PASSWORD が未設定です。" >&2
    echo "例: MAINT_VM_ADMIN_PASSWORD='YourStrongPassword!' ./main.sh --what-if" >&2
    exit 1
  fi

  echo "==> Deploy Maintenance VM"
  run_bicep_deployment "maintenance-vm" az deployment group create \
    --name "main-service-maintenance-vm-${timestamp}" \
    --resource-group "$maintenance_vm_resource_group_name" \
    --parameters "$maintenance_vm_params_file" \
    --parameters maintVmAdminPassword="$MAINT_VM_ADMIN_PASSWORD" \
    ${what_if:+$what_if}
else
  echo "==> Skip Maintenance VM (resourceToggles.maintenanceVm=false)"
fi

# -----------------------------------------------------------------------------
# Cosmos DB
# -----------------------------------------------------------------------------
cosmos_deploy="$(meta_bool "$cosmos_meta_file" "deploy")"

cosmos_params_file="$(meta_get "$cosmos_meta_file" "paramsFile")"

deploy_group_if_enabled \
  "$cosmos_deploy" \
  "Deploy Cosmos DB (NoSQL)" \
  "cosmos-database" \
  "main-service-cosmos-database-${timestamp}" \
  "$cosmos_resource_group_name" \
  "$cosmos_params_file" \
  "Skip Cosmos DB (resourceToggles.cosmosDatabase=false)"

# -----------------------------------------------------------------------------
# Redis
# -----------------------------------------------------------------------------
redis_deploy="$(meta_bool "$redis_meta_file" "deploy")"

redis_params_file="$(meta_get "$redis_meta_file" "paramsFile")"

deploy_group_if_enabled \
  "$redis_deploy" \
  "Deploy Redis" \
  "redis" \
  "main-service-redis-${timestamp}" \
  "$redis_resource_group_name" \
  "$redis_params_file" \
  "Skip Redis (resourceToggles.redis=false)"

# Post-deploy notices
# -----------------------------------------------------------------------------
run_post_deploy_actions
