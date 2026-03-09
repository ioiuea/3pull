#!/usr/bin/env bash
if [[ -z "${BASH_VERSION:-}" ]]; then
  echo "This script must be run with bash. Use: bash ./main.sh" >&2
  exit 1
fi

set -euo pipefail

# -----------------------------------------------------------------------------
# Path / file definitions
# -----------------------------------------------------------------------------
# このスクリプトは infra 配下の設定を読み込み、各 generate スクリプトで
# .bicepparam と meta.json を生成したうえで、依存順に az deployment を実行する。
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
infra_root="$repo_root/infra"
init_scripts_root="$repo_root/scripts/init"
agic_controller_init_dir="$init_scripts_root/agicController"
keda_controller_init_dir="$init_scripts_root/kedaController"
common_file="$infra_root/common.parameter.json"
params_dir="$infra_root/params"
logs_dir="$infra_root/logs"
common_validation_script="$infra_root/scripts/validate-common-params.py"

log_config_file="$infra_root/config/log-analytics.json"
log_script="$infra_root/scripts/generate-log-analytics-params.py"
log_meta_file="$params_dir/log-analytics-meta.json"

appi_config_file="$infra_root/config/application-insights.json"
appi_script="$infra_root/scripts/generate-application-insights-params.py"
appi_meta_file="$params_dir/application-insights-meta.json"

vnet_config_file="$infra_root/config/virtual-network.json"
vnet_script="$infra_root/scripts/generate-virtual-network-params.py"
vnet_meta_file="$params_dir/virtual-network-meta.json"

subnets_config_file="$infra_root/config/subnets.json"
subnets_script="$infra_root/scripts/generate-subnets-params.py"
subnets_meta_file="$params_dir/subnets-meta.json"

firewall_config_file="$infra_root/config/firewall.json"
firewall_script="$infra_root/scripts/generate-firewall-params.py"
firewall_meta_file="$params_dir/firewall-meta.json"

application_gateway_config_file="$infra_root/config/application-gateway.json"
application_gateway_script="$infra_root/scripts/generate-application-gateway-params.py"
application_gateway_meta_file="$params_dir/application-gateway-meta.json"
application_gateway_low_latency_script="$infra_root/scripts/generate-application-gateway-low-latency-params.py"
application_gateway_low_latency_meta_file="$params_dir/application-gateway-low-latency-meta.json"
application_gateway_rbac_config_file="$infra_root/config/application-gateway-rbac.json"
application_gateway_rbac_script="$infra_root/scripts/generate-application-gateway-rbac-params.py"
application_gateway_rbac_meta_file="$params_dir/application-gateway-rbac-meta.json"

managed_ids_config_file="$infra_root/config/managed-ids.json"
managed_ids_script="$infra_root/scripts/generate-managed-ids-params.py"
managed_ids_meta_file="$params_dir/managed-ids-meta.json"

key_vault_config_file="$infra_root/config/key-vault.json"
key_vault_script="$infra_root/scripts/generate-key-vault-params.py"
key_vault_meta_file="$params_dir/key-vault-meta.json"

service_bus_config_file="$infra_root/config/service-bus.json"
service_bus_script="$infra_root/scripts/generate-service-bus-params.py"
service_bus_meta_file="$params_dir/service-bus-meta.json"

acr_config_file="$infra_root/config/acr.json"
acr_script="$infra_root/scripts/generate-acr-params.py"
acr_meta_file="$params_dir/acr-meta.json"

storage_config_file="$infra_root/config/storage.json"
storage_script="$infra_root/scripts/generate-storage-params.py"
storage_meta_file="$params_dir/storage-meta.json"

redis_config_file="$infra_root/config/redis.json"
redis_script="$infra_root/scripts/generate-redis-params.py"
redis_meta_file="$params_dir/redis-meta.json"

postgres_config_file="$infra_root/config/postgres-database.json"
postgres_script="$infra_root/scripts/generate-postgres-database-params.py"
postgres_meta_file="$params_dir/postgres-database-meta.json"

cosmos_config_file="$infra_root/config/cosmos-database.json"
cosmos_script="$infra_root/scripts/generate-cosmos-database-params.py"
cosmos_meta_file="$params_dir/cosmos-database-meta.json"

aks_config_file="$infra_root/config/aks.json"
aks_runtime_config_file="$aks_config_file"
aks_script="$infra_root/scripts/generate-aks-params.py"
aks_meta_file="$params_dir/aks-meta.json"

route_tables_config_file="$infra_root/config/route-tables.json"
route_tables_script="$infra_root/scripts/generate-route-tables-params.py"
route_tables_meta_file="$params_dir/route-tables-meta.json"

nsgs_config_file="$infra_root/config/nsgs.json"
nsgs_script="$infra_root/scripts/generate-nsgs-params.py"
nsgs_meta_file="$params_dir/nsgs-meta.json"
subnet_attachments_script="$infra_root/scripts/generate-subnet-attachments-params.py"
subnet_attachments_meta_file="$params_dir/subnet-attachments-meta.json"

maintenance_vm_config_file="$infra_root/config/maintenance-vm.json"
maintenance_vm_script="$infra_root/scripts/generate-maintenance-vm-params.py"
maintenance_vm_meta_file="$params_dir/maintenance-vm-meta.json"

federated_credential_config_file="$infra_root/config/federated-credential.json"
federated_credential_script="$infra_root/scripts/generate-federated-credential-params.py"
federated_credential_meta_file="$params_dir/federated-credential-meta.json"

backend_values_template_file="$infra_root/config/backend-values.template.yaml"
backend_values_generated_file="$repo_root/k8s/charts/backend/values.yaml"
backend_values_sync_script="$infra_root/scripts/sync-backend-values.py"

frontend_values_template_file="$infra_root/config/frontend-values.template.yaml"
frontend_values_generated_file="$repo_root/k8s/charts/frontend/values.yaml"
frontend_values_sync_script="$infra_root/scripts/sync-frontend-values.py"

# -----------------------------------------------------------------------------
# CLI option parsing
# -----------------------------------------------------------------------------
# --what-if 指定時は Azure へ実変更せず、差分確認のみ行う。
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

run_bicep_deployment() {
  local log_key="$1"
  shift
  local log_file
  log_file="$logs_dir/${timestamp}-${log_key}.log"

  "$@" >"$log_file" 2> >(tee -a "$log_file" >&2)
}

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

# -----------------------------------------------------------------------------
# Pre-flight checks
# -----------------------------------------------------------------------------
# 1) 共通パラメータファイルと validator の存在確認
# 2) 共通パラメータの型・値検証
if [[ ! -f "$common_file" ]]; then
  echo "common parameter file が見つかりません: $common_file" >&2
  exit 1
fi

if [[ ! -f "$common_validation_script" ]]; then
  echo "common parameter validation script が見つかりません: $common_validation_script" >&2
  exit 1
fi

echo "==> Validate common parameters"
"$common_validation_script" "$common_file"

mkdir -p "$logs_dir"

# 各リソースの固定設定ファイルが欠けていないかを先に検証する。
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

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI (az) が見つかりません。" >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# Parameter generation phase
# -----------------------------------------------------------------------------
# 各 Python スクリプトが以下を出力する:
# - params/*.bicepparam (Bicep 実行引数)
# - params/*-meta.json  (deploy 可否、RG 名などの制御情報)
timestamp="$(date +'%Y%m%dT%H%M%S')"
mkdir -p "$params_dir"
update_aks_availability_zones

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$log_config_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$log_meta_file" \
TIMESTAMP="$timestamp" \
"$log_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$appi_config_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$appi_meta_file" \
TIMESTAMP="$timestamp" \
"$appi_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$vnet_config_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$vnet_meta_file" \
TIMESTAMP="$timestamp" \
"$vnet_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$subnets_config_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$subnets_meta_file" \
TIMESTAMP="$timestamp" \
"$subnets_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$firewall_config_file" \
SUBNETS_CONFIG_FILE="$subnets_config_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$firewall_meta_file" \
TIMESTAMP="$timestamp" \
"$firewall_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$managed_ids_config_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$managed_ids_meta_file" \
TIMESTAMP="$timestamp" \
"$managed_ids_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$application_gateway_config_file" \
SUBNETS_CONFIG_FILE="$subnets_config_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$application_gateway_meta_file" \
TIMESTAMP="$timestamp" \
"$application_gateway_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$application_gateway_config_file" \
SUBNETS_CONFIG_FILE="$subnets_config_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$application_gateway_low_latency_meta_file" \
TIMESTAMP="$timestamp" \
"$application_gateway_low_latency_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$redis_config_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$redis_meta_file" \
TIMESTAMP="$timestamp" \
"$redis_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$postgres_config_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$postgres_meta_file" \
TIMESTAMP="$timestamp" \
"$postgres_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$cosmos_config_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$cosmos_meta_file" \
TIMESTAMP="$timestamp" \
"$cosmos_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$aks_runtime_config_file" \
SUBNETS_CONFIG_FILE="$subnets_config_file" \
APPLICATION_GATEWAY_META_FILE="$application_gateway_meta_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$aks_meta_file" \
TIMESTAMP="$timestamp" \
"$aks_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$application_gateway_rbac_config_file" \
MANAGED_IDS_META_FILE="$managed_ids_meta_file" \
APPLICATION_GATEWAY_META_FILE="$application_gateway_meta_file" \
APPLICATION_GATEWAY_LOW_LATENCY_META_FILE="$application_gateway_low_latency_meta_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$application_gateway_rbac_meta_file" \
TIMESTAMP="$timestamp" \
"$application_gateway_rbac_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$acr_config_file" \
AKS_META_FILE="$aks_meta_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$acr_meta_file" \
TIMESTAMP="$timestamp" \
"$acr_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$key_vault_config_file" \
MANAGED_IDS_META_FILE="$managed_ids_meta_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$key_vault_meta_file" \
TIMESTAMP="$timestamp" \
"$key_vault_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$service_bus_config_file" \
MANAGED_IDS_META_FILE="$managed_ids_meta_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$service_bus_meta_file" \
TIMESTAMP="$timestamp" \
"$service_bus_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$storage_config_file" \
MANAGED_IDS_META_FILE="$managed_ids_meta_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$storage_meta_file" \
TIMESTAMP="$timestamp" \
"$storage_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$route_tables_config_file" \
SUBNETS_CONFIG_FILE="$subnets_config_file" \
FIREWALL_META_FILE="$firewall_meta_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$route_tables_meta_file" \
TIMESTAMP="$timestamp" \
"$route_tables_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$nsgs_config_file" \
SUBNETS_CONFIG_FILE="$subnets_config_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$nsgs_meta_file" \
TIMESTAMP="$timestamp" \
"$nsgs_script"

COMMON_FILE="$common_file" \
SUBNETS_CONFIG_FILE="$subnets_config_file" \
ROUTE_TABLES_CONFIG_FILE="$route_tables_config_file" \
NSGS_CONFIG_FILE="$nsgs_config_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$subnet_attachments_meta_file" \
TIMESTAMP="$timestamp" \
"$subnet_attachments_script"

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$maintenance_vm_config_file" \
SUBNETS_CONFIG_FILE="$subnets_config_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$maintenance_vm_meta_file" \
TIMESTAMP="$timestamp" \
"$maintenance_vm_script"

# -----------------------------------------------------------------------------
# Meta loading phase
# -----------------------------------------------------------------------------
# 生成済み meta.json から、以降で使う実行情報（location / RG / paramsFile）を取得する。
location="$(META_FILE="$log_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("location", ""))
PY
)"

resource_group_name="$(META_FILE="$log_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

vnet_resource_group_name="$(META_FILE="$vnet_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

subnets_resource_group_name="$(META_FILE="$subnets_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

firewall_resource_group_name="$(META_FILE="$firewall_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

managed_ids_resource_group_name="$(META_FILE="$managed_ids_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

application_gateway_resource_group_name="$(META_FILE="$application_gateway_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

application_gateway_rbac_resource_group_name="$(META_FILE="$application_gateway_rbac_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

key_vault_resource_group_name="$(META_FILE="$key_vault_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

service_bus_resource_group_name="$(META_FILE="$service_bus_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

acr_resource_group_name="$(META_FILE="$acr_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

storage_resource_group_name="$(META_FILE="$storage_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

redis_resource_group_name="$(META_FILE="$redis_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

postgres_resource_group_name="$(META_FILE="$postgres_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

cosmos_resource_group_name="$(META_FILE="$cosmos_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

aks_resource_group_name="$(META_FILE="$aks_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

route_tables_resource_group_name="$(META_FILE="$route_tables_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

nsgs_resource_group_name="$(META_FILE="$nsgs_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

subnet_attachments_resource_group_name="$(META_FILE="$subnet_attachments_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

maintenance_vm_resource_group_name="$(META_FILE="$maintenance_vm_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("resourceGroupName", ""))
PY
)"

# 取得必須のメタ情報を検証する。ここで失敗させることで後続の実行時エラーを防ぐ。
if [[ -z "$location" ]]; then
  echo "location が取得できませんでした。infra/common.parameter.json を確認してください。" >&2
  exit 1
fi

if [[ -z "$resource_group_name" ]]; then
  echo "resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$vnet_resource_group_name" ]]; then
  echo "vnet resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$subnets_resource_group_name" ]]; then
  echo "subnets resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$firewall_resource_group_name" ]]; then
  echo "firewall resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$managed_ids_resource_group_name" ]]; then
  echo "managed ids resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$application_gateway_resource_group_name" ]]; then
  echo "application gateway resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$application_gateway_rbac_resource_group_name" ]]; then
  echo "application gateway rbac resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$key_vault_resource_group_name" ]]; then
  echo "key vault resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$service_bus_resource_group_name" ]]; then
  echo "service bus resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$acr_resource_group_name" ]]; then
  echo "acr resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$storage_resource_group_name" ]]; then
  echo "storage resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$redis_resource_group_name" ]]; then
  echo "redis resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$postgres_resource_group_name" ]]; then
  echo "postgres resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$cosmos_resource_group_name" ]]; then
  echo "cosmos resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$aks_resource_group_name" ]]; then
  echo "aks resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$route_tables_resource_group_name" ]]; then
  echo "route tables resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$nsgs_resource_group_name" ]]; then
  echo "nsgs resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$subnet_attachments_resource_group_name" ]]; then
  echo "subnet attachments resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

if [[ -z "$maintenance_vm_resource_group_name" ]]; then
  echo "maintenance vm resourceGroupName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

available_locations="$(az account list-locations --query "[].name" -o tsv)"
if ! printf '%s\n' "$available_locations" | grep -qx "$location"; then
  echo "location が Azure のリージョン名ではありません: $location" >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# Resource group ensure phase
# -----------------------------------------------------------------------------
# 各リソースが利用する RG を作成(存在する場合は noop)する。
# 同名 RG への重複作成を避けるため、条件分岐で重複呼び出しを抑制している。
echo "==> Ensure Resource Group: $resource_group_name"
az group create \
  --name "$resource_group_name" \
  --location "$location" >/dev/null

echo "==> Ensure Resource Group: $vnet_resource_group_name"
az group create \
  --name "$vnet_resource_group_name" \
  --location "$location" >/dev/null

if [[ "$subnets_resource_group_name" != "$vnet_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $subnets_resource_group_name"
  az group create \
    --name "$subnets_resource_group_name" \
    --location "$location" >/dev/null
fi

if [[ "$firewall_resource_group_name" != "$vnet_resource_group_name" && "$firewall_resource_group_name" != "$subnets_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $firewall_resource_group_name"
  az group create \
    --name "$firewall_resource_group_name" \
    --location "$location" >/dev/null
fi

if [[ "$managed_ids_resource_group_name" != "$vnet_resource_group_name" && "$managed_ids_resource_group_name" != "$subnets_resource_group_name" && "$managed_ids_resource_group_name" != "$firewall_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $managed_ids_resource_group_name"
  az group create \
    --name "$managed_ids_resource_group_name" \
    --location "$location" >/dev/null
fi

if [[ "$application_gateway_resource_group_name" != "$vnet_resource_group_name" && "$application_gateway_resource_group_name" != "$subnets_resource_group_name" && "$application_gateway_resource_group_name" != "$firewall_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $application_gateway_resource_group_name"
  az group create \
    --name "$application_gateway_resource_group_name" \
    --location "$location" >/dev/null
fi

if [[ "$key_vault_resource_group_name" != "$vnet_resource_group_name" && "$key_vault_resource_group_name" != "$subnets_resource_group_name" && "$key_vault_resource_group_name" != "$firewall_resource_group_name" && "$key_vault_resource_group_name" != "$application_gateway_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $key_vault_resource_group_name"
  az group create \
    --name "$key_vault_resource_group_name" \
    --location "$location" >/dev/null
fi

if [[ "$acr_resource_group_name" != "$vnet_resource_group_name" && "$acr_resource_group_name" != "$subnets_resource_group_name" && "$acr_resource_group_name" != "$firewall_resource_group_name" && "$acr_resource_group_name" != "$application_gateway_resource_group_name" && "$acr_resource_group_name" != "$key_vault_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $acr_resource_group_name"
  az group create \
    --name "$acr_resource_group_name" \
    --location "$location" >/dev/null
fi

if [[ "$service_bus_resource_group_name" != "$vnet_resource_group_name" && "$service_bus_resource_group_name" != "$subnets_resource_group_name" && "$service_bus_resource_group_name" != "$firewall_resource_group_name" && "$service_bus_resource_group_name" != "$application_gateway_resource_group_name" && "$service_bus_resource_group_name" != "$key_vault_resource_group_name" && "$service_bus_resource_group_name" != "$acr_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $service_bus_resource_group_name"
  az group create \
    --name "$service_bus_resource_group_name" \
    --location "$location" >/dev/null
fi

if [[ "$storage_resource_group_name" != "$vnet_resource_group_name" && "$storage_resource_group_name" != "$subnets_resource_group_name" && "$storage_resource_group_name" != "$firewall_resource_group_name" && "$storage_resource_group_name" != "$application_gateway_resource_group_name" && "$storage_resource_group_name" != "$key_vault_resource_group_name" && "$storage_resource_group_name" != "$acr_resource_group_name" && "$storage_resource_group_name" != "$service_bus_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $storage_resource_group_name"
  az group create \
    --name "$storage_resource_group_name" \
    --location "$location" >/dev/null
fi

if [[ "$redis_resource_group_name" != "$vnet_resource_group_name" && "$redis_resource_group_name" != "$subnets_resource_group_name" && "$redis_resource_group_name" != "$firewall_resource_group_name" && "$redis_resource_group_name" != "$application_gateway_resource_group_name" && "$redis_resource_group_name" != "$key_vault_resource_group_name" && "$redis_resource_group_name" != "$acr_resource_group_name" && "$redis_resource_group_name" != "$service_bus_resource_group_name" && "$redis_resource_group_name" != "$storage_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $redis_resource_group_name"
  az group create \
    --name "$redis_resource_group_name" \
    --location "$location" >/dev/null
fi

if [[ "$postgres_resource_group_name" != "$vnet_resource_group_name" && "$postgres_resource_group_name" != "$subnets_resource_group_name" && "$postgres_resource_group_name" != "$firewall_resource_group_name" && "$postgres_resource_group_name" != "$application_gateway_resource_group_name" && "$postgres_resource_group_name" != "$key_vault_resource_group_name" && "$postgres_resource_group_name" != "$acr_resource_group_name" && "$postgres_resource_group_name" != "$service_bus_resource_group_name" && "$postgres_resource_group_name" != "$storage_resource_group_name" && "$postgres_resource_group_name" != "$redis_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $postgres_resource_group_name"
  az group create \
    --name "$postgres_resource_group_name" \
    --location "$location" >/dev/null
fi

if [[ "$cosmos_resource_group_name" != "$vnet_resource_group_name" && "$cosmos_resource_group_name" != "$subnets_resource_group_name" && "$cosmos_resource_group_name" != "$firewall_resource_group_name" && "$cosmos_resource_group_name" != "$application_gateway_resource_group_name" && "$cosmos_resource_group_name" != "$key_vault_resource_group_name" && "$cosmos_resource_group_name" != "$acr_resource_group_name" && "$cosmos_resource_group_name" != "$service_bus_resource_group_name" && "$cosmos_resource_group_name" != "$storage_resource_group_name" && "$cosmos_resource_group_name" != "$redis_resource_group_name" && "$cosmos_resource_group_name" != "$postgres_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $cosmos_resource_group_name"
  az group create \
    --name "$cosmos_resource_group_name" \
    --location "$location" >/dev/null
fi

if [[ "$aks_resource_group_name" != "$vnet_resource_group_name" && "$aks_resource_group_name" != "$subnets_resource_group_name" && "$aks_resource_group_name" != "$firewall_resource_group_name" && "$aks_resource_group_name" != "$application_gateway_resource_group_name" && "$aks_resource_group_name" != "$key_vault_resource_group_name" && "$aks_resource_group_name" != "$acr_resource_group_name" && "$aks_resource_group_name" != "$service_bus_resource_group_name" && "$aks_resource_group_name" != "$storage_resource_group_name" && "$aks_resource_group_name" != "$redis_resource_group_name" && "$aks_resource_group_name" != "$postgres_resource_group_name" && "$aks_resource_group_name" != "$cosmos_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $aks_resource_group_name"
  az group create \
    --name "$aks_resource_group_name" \
    --location "$location" >/dev/null
fi

if [[ "$route_tables_resource_group_name" != "$vnet_resource_group_name" && "$route_tables_resource_group_name" != "$subnets_resource_group_name" && "$route_tables_resource_group_name" != "$firewall_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $route_tables_resource_group_name"
  az group create \
    --name "$route_tables_resource_group_name" \
    --location "$location" >/dev/null
fi

if [[ "$nsgs_resource_group_name" != "$vnet_resource_group_name" && "$nsgs_resource_group_name" != "$subnets_resource_group_name" && "$nsgs_resource_group_name" != "$firewall_resource_group_name" && "$nsgs_resource_group_name" != "$route_tables_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $nsgs_resource_group_name"
  az group create \
    --name "$nsgs_resource_group_name" \
    --location "$location" >/dev/null
fi

if [[ "$subnet_attachments_resource_group_name" != "$vnet_resource_group_name" && "$subnet_attachments_resource_group_name" != "$subnets_resource_group_name" && "$subnet_attachments_resource_group_name" != "$firewall_resource_group_name" && "$subnet_attachments_resource_group_name" != "$route_tables_resource_group_name" && "$subnet_attachments_resource_group_name" != "$nsgs_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $subnet_attachments_resource_group_name"
  az group create \
    --name "$subnet_attachments_resource_group_name" \
    --location "$location" >/dev/null
fi

if [[ "$maintenance_vm_resource_group_name" != "$vnet_resource_group_name" && "$maintenance_vm_resource_group_name" != "$subnets_resource_group_name" && "$maintenance_vm_resource_group_name" != "$firewall_resource_group_name" && "$maintenance_vm_resource_group_name" != "$application_gateway_resource_group_name" && "$maintenance_vm_resource_group_name" != "$key_vault_resource_group_name" && "$maintenance_vm_resource_group_name" != "$acr_resource_group_name" && "$maintenance_vm_resource_group_name" != "$service_bus_resource_group_name" && "$maintenance_vm_resource_group_name" != "$storage_resource_group_name" && "$maintenance_vm_resource_group_name" != "$redis_resource_group_name" && "$maintenance_vm_resource_group_name" != "$postgres_resource_group_name" && "$maintenance_vm_resource_group_name" != "$cosmos_resource_group_name" && "$maintenance_vm_resource_group_name" != "$aks_resource_group_name" && "$maintenance_vm_resource_group_name" != "$route_tables_resource_group_name" && "$maintenance_vm_resource_group_name" != "$nsgs_resource_group_name" && "$maintenance_vm_resource_group_name" != "$subnet_attachments_resource_group_name" ]]; then
  echo "==> Ensure Resource Group: $maintenance_vm_resource_group_name"
  az group create \
    --name "$maintenance_vm_resource_group_name" \
    --location "$location" >/dev/null
fi

# -----------------------------------------------------------------------------
# Monitor resources
# -----------------------------------------------------------------------------
# Log Analytics -> Application Insights の順で実行する。
log_deploy="$(META_FILE="$log_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

log_params_file="$(META_FILE="$log_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

appi_deploy="$(META_FILE="$appi_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

appi_params_file="$(META_FILE="$appi_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

if [[ "$log_deploy" == "true" ]]; then
  echo "==> Deploy Log Analytics"
  run_bicep_deployment "log-analytics" az deployment group create \
    --name "main-monitor-log-analytics-${timestamp}" \
    --resource-group "$resource_group_name" \
    --parameters "$log_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip Log Analytics (resourceToggles.logAnalytics=false)"
fi

if [[ "$appi_deploy" == "true" ]]; then
  echo "==> Deploy Application Insights"
  run_bicep_deployment "application-insights" az deployment group create \
    --name "main-monitor-application-insights-${timestamp}" \
    --resource-group "$resource_group_name" \
    --parameters "$appi_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip Application Insights (resourceToggles.applicationInsights=false)"
fi

# -----------------------------------------------------------------------------
# Virtual Network (existing check aware)
# -----------------------------------------------------------------------------
# 既存 VNET がある環境では peering 等の手動設定を壊さないため、
# 既存検出時は VNET の apply/update をスキップする。
vnet_deploy="$(META_FILE="$vnet_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

vnet_params_file="$(META_FILE="$vnet_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

vnet_apply_skipped_existing=false
vnet_created_in_this_run=false

if [[ "$vnet_deploy" == "true" ]]; then
  vnet_name="$(PARAMS_FILE="$vnet_params_file" python - <<'PY'
import os
import re
from pathlib import Path

content = Path(os.environ["PARAMS_FILE"]).read_text(encoding="utf-8")
match = re.search(r"^param vnetName = '([^']*)'$", content, flags=re.MULTILINE)
print(match.group(1) if match else "")
PY
)"

  if [[ -z "$vnet_name" ]]; then
    echo "vnetName が取得できませんでした: $vnet_params_file" >&2
    exit 1
  fi

  echo "==> Check existing Virtual Network: $vnet_name"
  existing_vnet_name="$(VNET_RG_NAME="$vnet_resource_group_name" VNET_NAME="$vnet_name" SUBSCRIPTION_ID="$(az account show --query id -o tsv)" python - <<'PY'
import os
import subprocess
import sys

vnet_id = (
    f"/subscriptions/{os.environ['SUBSCRIPTION_ID']}"
    f"/resourceGroups/{os.environ['VNET_RG_NAME']}"
    f"/providers/Microsoft.Network/virtualNetworks/{os.environ['VNET_NAME']}"
)

cmd = [
    "az",
    "resource",
    "show",
    "--ids",
    vnet_id,
    "--query",
    "name",
    "--output",
    "tsv",
    "--only-show-errors",
]

for _ in range(3):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    except subprocess.TimeoutExpired:
        continue

    if result.returncode == 0:
        print(result.stdout.strip())
        sys.exit(0)
    if result.returncode != 0 and "was not found" in (result.stderr or ""):
        print("")
        sys.exit(0)

print("__CHECK_FAILED__")
PY
)"

  if [[ "$existing_vnet_name" == "__CHECK_FAILED__" ]]; then
    echo "==> エラー: 既存 Virtual Network の存在確認に失敗しました（タイムアウト/リトライ上限）。" >&2
    echo "==> Error: Failed to check existing Virtual Network state (timeout/retry exhausted)." >&2
    echo "==> Azure CLI のログイン状態・セッション・ネットワークを確認して再実行してください。" >&2
    echo "==> Please verify Azure CLI login/session/network and retry." >&2
    exit 1
  fi

  if [[ -n "$existing_vnet_name" ]]; then
    vnet_apply_skipped_existing=true
    cat <<EOF
------------------------------------------------------------
NOTICE: Virtual Network
[JA] 既存の Virtual Network を検出したため、Virtual Network の適用/更新をスキップします。
     VNET 名: $existing_vnet_name
[EN] Existing Virtual Network detected. Skipping Virtual Network apply/update.
     VNET Name: $existing_vnet_name
------------------------------------------------------------
EOF
  else
    echo "==> Deploy Virtual Network"
    run_bicep_deployment "virtual-network" az deployment group create \
      --name "main-network-virtual-network-${timestamp}" \
      --resource-group "$vnet_resource_group_name" \
      --parameters "$vnet_params_file" \
      ${what_if:+$what_if}
    vnet_created_in_this_run=true

    cat <<'EOF'
------------------------------------------------------------
NOTICE: Initial VNET Provisioning
[EN] A new VNET has been created for the initial run.
     If you specify egressNextHopIp individually, implement VNET peering first so that
     outbound communication to external networks is available before deployment.
     After VNET peering is completed, run this script again.

[JA] 初回実行のため新規VNETを作成しました。
     egressNextHopIpを個別指定している場合は、デプロイ前に外部への通信が可能になるように
     VNETピアリングを先に実装してください。
     VNETピアリング完了後に再度このスクリプトを実行してください。
------------------------------------------------------------
EOF
    exit 0
  fi
else
  echo "==> Skip Virtual Network (resourceToggles.virtualNetwork=false)"
fi

# -----------------------------------------------------------------------------
# Subnets (base creation)
# -----------------------------------------------------------------------------
# まずは NSG / UDR を付けずにサブネットだけ作成する。
subnets_deploy="$(META_FILE="$subnets_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

subnets_params_file="$(META_FILE="$subnets_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

if [[ "$subnets_deploy" == "true" ]]; then
  echo "==> Deploy Subnets (without NSG/RouteTable)"
  run_bicep_deployment "subnets" az deployment group create \
    --name "main-network-subnets-${timestamp}" \
    --resource-group "$subnets_resource_group_name" \
    --parameters "$subnets_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip Subnets (resourceToggles.subnets=false)"
fi

# -----------------------------------------------------------------------------
# Firewall (policy existing check aware)
# -----------------------------------------------------------------------------
# Firewall Policy が既存の場合、既存ポリシーを維持するため
# ポリシー更新だけスキップして Firewall リソース本体を実行する。
firewall_deploy="$(META_FILE="$firewall_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

firewall_params_file="$(META_FILE="$firewall_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

firewall_policy_apply_skipped=false

if [[ "$firewall_deploy" == "true" ]]; then
  firewall_policy_name="$(PARAMS_FILE="$firewall_params_file" python - <<'PY'
import os
import re
from pathlib import Path

content = Path(os.environ["PARAMS_FILE"]).read_text(encoding="utf-8")
match = re.search(r"^param firewallPolicyName = '([^']*)'$", content, flags=re.MULTILINE)
print(match.group(1) if match else "")
PY
)"

  if [[ -z "$firewall_policy_name" ]]; then
    echo "firewallPolicyName が取得できませんでした: $firewall_params_file" >&2
    exit 1
  fi

  echo "==> Check existing Firewall Policy: $firewall_policy_name"
  existing_firewall_policy_name="$(FIREWALL_RG_NAME="$firewall_resource_group_name" FIREWALL_POLICY_NAME="$firewall_policy_name" SUBSCRIPTION_ID="$(az account show --query id -o tsv)" python - <<'PY'
import os
import subprocess
import sys

policy_id = (
    f"/subscriptions/{os.environ['SUBSCRIPTION_ID']}"
    f"/resourceGroups/{os.environ['FIREWALL_RG_NAME']}"
    f"/providers/Microsoft.Network/firewallPolicies/{os.environ['FIREWALL_POLICY_NAME']}"
)

cmd = [
    "az",
    "resource",
    "show",
    "--ids",
    policy_id,
    "--query",
    "name",
    "--output",
    "tsv",
    "--only-show-errors",
]

for _ in range(3):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    except subprocess.TimeoutExpired:
        continue

    if result.returncode == 0:
        print(result.stdout.strip())
        sys.exit(0)
    if result.returncode != 0 and "was not found" in (result.stderr or ""):
        print("")
        sys.exit(0)

print("__CHECK_FAILED__")
PY
)"

  if [[ "$existing_firewall_policy_name" == "__CHECK_FAILED__" ]]; then
    echo "==> Error: Failed to check existing Firewall Policy state (timeout/retry exhausted)." >&2
    echo "==> エラー: 既存 Firewall Policy の存在確認に失敗しました（タイムアウト/リトライ上限）。" >&2
    echo "==> Please verify Azure CLI login/session/network and retry." >&2
    echo "==> Azure CLI のログイン状態・セッション・ネットワークを確認して再実行してください。" >&2
    exit 1
  fi

  if [[ -n "$existing_firewall_policy_name" ]]; then
    firewall_policy_apply_skipped=true
    cat <<EOF
------------------------------------------------------------
NOTICE: Firewall Policy
[EN] Existing Firewall Policy detected. Skipping policy apply/update.
     Policy Name: $existing_firewall_policy_name
[JA] 既存の Firewall Policy を検出したため、Policy の適用/更新をスキップします。
     Policy 名: $existing_firewall_policy_name
------------------------------------------------------------
EOF
    echo "==> Deploy Firewall (use existing Firewall Policy)"
    firewall_deploy_cmd=(
      az deployment group create
      --name "main-network-firewall-${timestamp}"
      --resource-group "$firewall_resource_group_name"
      --parameters "$firewall_params_file"
      --parameters skipFirewallPolicyDeployment=true
    )
    if [[ -n "${what_if:-}" ]]; then
      firewall_deploy_cmd+=("$what_if")
    fi
    run_bicep_deployment "firewall" "${firewall_deploy_cmd[@]}"
  else
    echo "==> Deploy Firewall"
    firewall_deploy_cmd=(
      az deployment group create
      --name "main-network-firewall-${timestamp}"
      --resource-group "$firewall_resource_group_name"
      --parameters "$firewall_params_file"
    )
    if [[ -n "${what_if:-}" ]]; then
      firewall_deploy_cmd+=("$what_if")
    fi
    run_bicep_deployment "firewall" "${firewall_deploy_cmd[@]}"
  fi
else
  echo "==> Skip Firewall (resourceToggles.firewall=false)"
fi

# -----------------------------------------------------------------------------
# Route table / NSG / subnet attachments
# -----------------------------------------------------------------------------
# 注意:
# - network.egressNextHopIp 未指定時は、実際の Firewall Private IP を Azure から再取得し、
#   その値で route-tables.bicepparam を再生成してから適用する。
# - これにより nextHop の古い値で UDR が適用されることを防ぐ。
application_gateway_deploy="$(META_FILE="$application_gateway_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

application_gateway_params_file="$(META_FILE="$application_gateway_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

application_gateway_low_latency_deploy="$(META_FILE="$application_gateway_low_latency_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

application_gateway_low_latency_params_file="$(META_FILE="$application_gateway_low_latency_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

route_tables_deploy="$(META_FILE="$route_tables_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

route_tables_params_file="$(META_FILE="$route_tables_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

egress_next_hop_ip_for_routes="$(COMMON_FILE="$common_file" python - <<'PY'
import json
import os
from pathlib import Path

common = json.loads(Path(os.environ["COMMON_FILE"]).read_text(encoding="utf-8"))
print(common.get("network", {}).get("egressNextHopIp", ""))
PY
)"

if [[ "$route_tables_deploy" == "true" ]]; then
  if [[ -z "$egress_next_hop_ip_for_routes" ]]; then
    firewall_name_for_routes="$(PARAMS_FILE="$firewall_params_file" python - <<'PY'
import os
import re
from pathlib import Path

content = Path(os.environ["PARAMS_FILE"]).read_text(encoding="utf-8")
match = re.search(r"^param firewallName = '([^']*)'$", content, flags=re.MULTILINE)
print(match.group(1) if match else "")
PY
)"

    if [[ -z "$firewall_name_for_routes" ]]; then
      echo "firewallName が取得できませんでした: $firewall_params_file" >&2
      exit 1
    fi

    echo "==> Resolve Firewall Private IP for Route Tables: $firewall_name_for_routes"
    actual_firewall_private_ip="$(FIREWALL_RG_NAME="$firewall_resource_group_name" FIREWALL_NAME="$firewall_name_for_routes" python - <<'PY'
import os
import subprocess
import sys

cmd = [
    "az",
    "network",
    "firewall",
    "show",
    "--resource-group",
    os.environ["FIREWALL_RG_NAME"],
    "--name",
    os.environ["FIREWALL_NAME"],
    "--query",
    "ipConfigurations[0].privateIPAddress",
    "--output",
    "tsv",
    "--only-show-errors",
]

for _ in range(3):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    except subprocess.TimeoutExpired:
        continue

    if result.returncode == 0:
        print(result.stdout.strip())
        sys.exit(0)
    if result.returncode != 0 and "was not found" in (result.stderr or ""):
        print("")
        sys.exit(0)

print("__CHECK_FAILED__")
PY
)"

    if [[ "$actual_firewall_private_ip" == "__CHECK_FAILED__" ]]; then
      echo "==> Error: Failed to resolve Firewall private IP for Route Tables (timeout/retry exhausted)." >&2
      echo "==> エラー: Route Tables 用の Firewall プライベート IP 解決に失敗しました（タイムアウト/リトライ上限）。" >&2
      exit 1
    fi

    if [[ -z "$actual_firewall_private_ip" ]]; then
      if [[ -n "${what_if:-}" ]]; then
        echo "==> WARN: Firewall private IP could not be resolved in --what-if mode. Continue with generated value."
        echo "==> 警告: --what-if 実行のため Firewall プライベート IP を解決できませんでした。生成済み値で継続します。"
      else
        echo "==> Error: Firewall private IP is empty. Ensure Firewall exists before Route Tables deployment." >&2
        echo "==> エラー: Firewall プライベート IP が空です。Route Tables 実行前に Firewall が存在することを確認してください。" >&2
        exit 1
      fi
    else
      FIREWALL_META_FILE="$firewall_meta_file" FIREWALL_PRIVATE_IP="$actual_firewall_private_ip" python - <<'PY'
import json
import os
from pathlib import Path

meta_path = Path(os.environ["FIREWALL_META_FILE"])
meta = json.loads(meta_path.read_text(encoding="utf-8"))
meta["firewallPrivateIp"] = os.environ["FIREWALL_PRIVATE_IP"]
meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY

      COMMON_FILE="$common_file" \
      RESOURCE_CONFIG_FILE="$route_tables_config_file" \
      SUBNETS_CONFIG_FILE="$subnets_config_file" \
      FIREWALL_META_FILE="$firewall_meta_file" \
      PARAMS_DIR="$params_dir" \
      OUT_META_FILE="$route_tables_meta_file" \
      TIMESTAMP="$timestamp" \
      "$route_tables_script"

      route_tables_params_file="$(META_FILE="$route_tables_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"
    fi
  fi

  echo "==> Deploy Route Tables (UDR)"
  run_bicep_deployment "route-tables" az deployment group create \
    --name "main-network-route-tables-${timestamp}" \
    --resource-group "$route_tables_resource_group_name" \
    --parameters "$route_tables_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip Route Tables (resourceToggles.subnets=false)"
fi

nsgs_deploy="$(META_FILE="$nsgs_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

nsgs_params_file="$(META_FILE="$nsgs_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

if [[ "$nsgs_deploy" == "true" ]]; then
  echo "==> Deploy NSGs"
  run_bicep_deployment "nsgs" az deployment group create \
    --name "main-network-nsgs-${timestamp}" \
    --resource-group "$nsgs_resource_group_name" \
    --parameters "$nsgs_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip NSGs (resourceToggles.subnets=false)"
fi

subnet_attachments_deploy="$(META_FILE="$subnet_attachments_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

subnet_attachments_params_file="$(META_FILE="$subnet_attachments_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

if [[ "$subnet_attachments_deploy" == "true" ]]; then
  echo "==> Attach Route Tables / NSGs to Subnets"
  run_bicep_deployment "subnet-attachments" az deployment group create \
    --name "main-network-subnet-attachments-${timestamp}" \
    --resource-group "$subnet_attachments_resource_group_name" \
    --parameters "$subnet_attachments_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip Subnet Attachments (resourceToggles.subnets=false)"
fi

# -----------------------------------------------------------------------------
# Managed IDs / Application Gateway / AKS / ACR / Key Vault / Service Bus / Storage / PostgreSQL / Maintenance VM / Cosmos DB / Redis
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
managed_ids_deploy="$(META_FILE="$managed_ids_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

managed_ids_params_file="$(META_FILE="$managed_ids_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

if [[ "$managed_ids_deploy" == "true" ]]; then
  echo "==> Deploy Managed IDs"
  run_bicep_deployment "managed-ids" az deployment group create \
    --name "main-service-managed-ids-${timestamp}" \
    --resource-group "$managed_ids_resource_group_name" \
    --parameters "$managed_ids_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip Managed IDs (resourceToggles.managedIds=false)"
fi

if [[ "$application_gateway_deploy" == "true" ]]; then
  echo "==> Deploy Application Gateway"
  run_bicep_deployment "application-gateway" az deployment group create \
    --name "main-network-application-gateway-${timestamp}" \
    --resource-group "$application_gateway_resource_group_name" \
    --parameters "$application_gateway_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip Application Gateway (resourceToggles.applicationGateway=false)"
fi

if [[ "$application_gateway_low_latency_deploy" == "true" ]]; then
  echo "==> Deploy Application Gateway (Low Latency)"
  run_bicep_deployment "application-gateway-low-latency" az deployment group create \
    --name "main-network-application-gateway-low-latency-${timestamp}" \
    --resource-group "$application_gateway_resource_group_name" \
    --parameters "$application_gateway_low_latency_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip Application Gateway (Low Latency)"
fi

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$application_gateway_rbac_config_file" \
MANAGED_IDS_META_FILE="$managed_ids_meta_file" \
APPLICATION_GATEWAY_META_FILE="$application_gateway_meta_file" \
APPLICATION_GATEWAY_LOW_LATENCY_META_FILE="$application_gateway_low_latency_meta_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$application_gateway_rbac_meta_file" \
TIMESTAMP="$timestamp" \
"$application_gateway_rbac_script"

application_gateway_rbac_deploy="$(META_FILE="$application_gateway_rbac_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

application_gateway_rbac_params_file="$(META_FILE="$application_gateway_rbac_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

if [[ "$application_gateway_rbac_deploy" == "true" ]]; then
  echo "==> Deploy Application Gateway RBAC"
  run_bicep_deployment "application-gateway-rbac" az deployment group create \
    --name "main-service-application-gateway-rbac-${timestamp}" \
    --resource-group "$application_gateway_rbac_resource_group_name" \
    --parameters "$application_gateway_rbac_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip Application Gateway RBAC (resourceToggles.applicationGateway=false or required managed identities not found)"
fi

aks_deploy="$(META_FILE="$aks_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

aks_params_file="$(META_FILE="$aks_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

if [[ "$aks_deploy" == "true" ]]; then
  echo "==> Deploy AKS"
  run_bicep_deployment "aks" az deployment group create \
    --name "main-service-aks-${timestamp}" \
    --resource-group "$aks_resource_group_name" \
    --parameters "$aks_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip AKS (resourceToggles.aks=false)"
fi

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

    federated_credential_deploy="$(META_FILE="$federated_credential_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

    federated_credential_params_file="$(META_FILE="$federated_credential_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

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

acr_deploy="$(META_FILE="$acr_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

acr_params_file="$(META_FILE="$acr_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

if [[ "$acr_deploy" == "true" ]]; then
  echo "==> Deploy ACR"
  run_bicep_deployment "acr" az deployment group create \
    --name "main-service-acr-${timestamp}" \
    --resource-group "$acr_resource_group_name" \
    --parameters "$acr_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip ACR (resourceToggles.acr=false)"
fi

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$key_vault_config_file" \
MANAGED_IDS_META_FILE="$managed_ids_meta_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$key_vault_meta_file" \
TIMESTAMP="$timestamp" \
"$key_vault_script"

key_vault_deploy="$(META_FILE="$key_vault_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

key_vault_params_file="$(META_FILE="$key_vault_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

if [[ "$key_vault_deploy" == "true" ]]; then
  echo "==> Deploy Key Vault"
  run_bicep_deployment "key-vault" az deployment group create \
    --name "main-service-key-vault-${timestamp}" \
    --resource-group "$key_vault_resource_group_name" \
    --parameters "$key_vault_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip Key Vault (resourceToggles.keyVault=false)"
fi

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$service_bus_config_file" \
MANAGED_IDS_META_FILE="$managed_ids_meta_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$service_bus_meta_file" \
TIMESTAMP="$timestamp" \
"$service_bus_script"

service_bus_deploy="$(META_FILE="$service_bus_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

service_bus_params_file="$(META_FILE="$service_bus_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

if [[ "$service_bus_deploy" == "true" ]]; then
  echo "==> Deploy Service Bus"
  run_bicep_deployment "service-bus" az deployment group create \
    --name "main-service-service-bus-${timestamp}" \
    --resource-group "$service_bus_resource_group_name" \
    --parameters "$service_bus_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip Service Bus (resourceToggles.serviceBus=false)"
fi

COMMON_FILE="$common_file" \
RESOURCE_CONFIG_FILE="$storage_config_file" \
MANAGED_IDS_META_FILE="$managed_ids_meta_file" \
PARAMS_DIR="$params_dir" \
OUT_META_FILE="$storage_meta_file" \
TIMESTAMP="$timestamp" \
"$storage_script"

storage_deploy="$(META_FILE="$storage_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

storage_params_file="$(META_FILE="$storage_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

if [[ "$storage_deploy" == "true" ]]; then
  echo "==> Deploy Storage Account"
  run_bicep_deployment "storage" az deployment group create \
    --name "main-service-storage-${timestamp}" \
    --resource-group "$storage_resource_group_name" \
    --parameters "$storage_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip Storage Account (resourceToggles.storage=false)"
fi

postgres_deploy="$(META_FILE="$postgres_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

postgres_params_file="$(META_FILE="$postgres_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

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

maintenance_vm_deploy="$(META_FILE="$maintenance_vm_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

maintenance_vm_params_file="$(META_FILE="$maintenance_vm_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

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

cosmos_deploy="$(META_FILE="$cosmos_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

cosmos_params_file="$(META_FILE="$cosmos_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

if [[ "$cosmos_deploy" == "true" ]]; then
  echo "==> Deploy Cosmos DB (NoSQL)"
  run_bicep_deployment "cosmos-database" az deployment group create \
    --name "main-service-cosmos-database-${timestamp}" \
    --resource-group "$cosmos_resource_group_name" \
    --parameters "$cosmos_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip Cosmos DB (resourceToggles.cosmosDatabase=false)"
fi

redis_deploy="$(META_FILE="$redis_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(bool(meta.get("deploy", True))).lower())
PY
)"

redis_params_file="$(META_FILE="$redis_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("paramsFile", ""))
PY
)"

if [[ "$redis_deploy" == "true" ]]; then
  echo "==> Deploy Redis"
  run_bicep_deployment "redis" az deployment group create \
    --name "main-service-redis-${timestamp}" \
    --resource-group "$redis_resource_group_name" \
    --parameters "$redis_params_file" \
    ${what_if:+$what_if}
else
  echo "==> Skip Redis (resourceToggles.redis=false)"
fi

# -----------------------------------------------------------------------------
# Post-deploy notices
# -----------------------------------------------------------------------------
# 初期構築で見落としやすい運用作業を、条件付きでメッセージ表示する。
egress_next_hop_ip="$(COMMON_FILE="$common_file" python - <<'PY'
import json
import os
from pathlib import Path

common = json.loads(Path(os.environ["COMMON_FILE"]).read_text(encoding="utf-8"))
print(common.get("network", {}).get("egressNextHopIp", ""))
PY
)"

if [[ "$vnet_deploy" == "true" && "$vnet_apply_skipped_existing" != "true" && "$vnet_created_in_this_run" == "true" ]]; then
  cat <<'EOF'
------------------------------------------------------------
NOTICE: Virtual Network (Initial Provisioning)
[EN] A new Virtual Network has been created. If peering with other VNETs is required,
     configure it from Azure Portal: https://portal.azure.com/

[JA] Virtual Network を新規作成しています。別 VNET とのピアリングなどが必要な場合は、
     Azure Portal（https://portal.azure.com/）から設定してください。
------------------------------------------------------------
EOF
fi

if [[ "$firewall_deploy" == "true" && -z "$egress_next_hop_ip" && "$firewall_policy_apply_skipped" != "true" ]]; then
  cat <<'EOF'
------------------------------------------------------------
NOTICE: Firewall Outbound Rule (Initial Provisioning)
[EN] Because network.egressNextHopIp is not specified, outbound traffic in Firewall Policy is temporarily allowed to Any
     to permit required external communication during the initial Azure Kubernetes Service provisioning.
     After provisioning, review and tighten Firewall Policy allow/deny rules according to your enterprise policy.
     Edit Firewall Policy from Azure Portal: https://portal.azure.com/

[JA] network.egressNextHopIp が未指定のため、初期構築段階では Azure Kubernetes Service の構築に必要な外部通信を許可する目的で、
     Firewall Policy のアウトバウンド通信が宛先 Any で許可される構成になります。
     構築完了後は、企業ポリシーに合わせて Firewall Policy の許可/遮断ルールを見直して運用してください。
     Firewall Policy の編集は Azure Portal（https://portal.azure.com/）から実施してください。
------------------------------------------------------------
EOF
fi

aks_name_for_post="$(META_FILE="$aks_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get("aksName", ""))
PY
)"

if [[ -z "$aks_name_for_post" ]]; then
  echo "aksName が取得できませんでした。config を確認してください。" >&2
  exit 1
fi

echo "==> Check existing AKS: $aks_name_for_post"
existing_aks_name="$(AKS_RG_NAME="$aks_resource_group_name" AKS_NAME="$aks_name_for_post" python - <<'PY'
import os
import subprocess
import sys

cmd = [
    "az",
    "aks",
    "show",
    "--resource-group",
    os.environ["AKS_RG_NAME"],
    "--name",
    os.environ["AKS_NAME"],
    "--query",
    "name",
    "-o",
    "tsv",
    "--only-show-errors",
]

for _ in range(3):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    except subprocess.TimeoutExpired:
        continue

    if result.returncode == 0:
        print(result.stdout.strip())
        sys.exit(0)
    if result.returncode != 0 and "was not found" in (result.stderr or ""):
        print("")
        sys.exit(0)

print("__CHECK_FAILED__")
PY
)"

if [[ "$existing_aks_name" == "__CHECK_FAILED__" ]]; then
  echo "==> エラー: AKS の存在確認に失敗しました（タイムアウト/リトライ上限）。" >&2
  echo "==> Error: Failed to check AKS state (timeout/retry exhausted)." >&2
  echo "==> Azure CLI のログイン状態・セッション・ネットワークを確認して再実行してください。" >&2
  echo "==> Please verify Azure CLI login/session/network and retry." >&2
  exit 1
fi

if [[ -z "$existing_aks_name" ]]; then
  cat <<'EOF'
------------------------------------------------------------
NOTICE: Skip Helm / Values Export
[EN] AKS is not found in the target resource group.
     AGIC/KEDA init script generation and Helm values export are skipped.
     Create/deploy AKS first, then run this script again.

[JA] 対象リソースグループに AKS が存在しないため、
     AGIC/KEDA 初期化スクリプト生成、および Helm values エクスポートをスキップします。
     先に AKS を作成/デプロイしてから、このスクリプトを再実行してください。
------------------------------------------------------------
EOF
else
  if [[ -n "$what_if" ]]; then
    echo "==> Skip Generate AGIC/KEDA init scripts (--what-if)"
    echo "==> Skip Generate frontend Helm values file (--what-if)"
    echo "==> Skip Generate backend Helm values file (--what-if)"
  else
    agic_namespace="$(RESOURCE_CONFIG_FILE="$federated_credential_config_file" python - <<'PY'
import json
import os
from pathlib import Path

config = json.loads(Path(os.environ["RESOURCE_CONFIG_FILE"]).read_text(encoding="utf-8"))
print(str(config.get("agicNamespace", "ingress")).strip() or "ingress")
PY
)"

    agic_standard_service_account_name="$(RESOURCE_CONFIG_FILE="$federated_credential_config_file" python - <<'PY'
import json
import os
from pathlib import Path

config = json.loads(Path(os.environ["RESOURCE_CONFIG_FILE"]).read_text(encoding="utf-8"))
print(str(config.get("agicStandardServiceAccountName", "sa-agic-standard")).strip() or "sa-agic-standard")
PY
)"

    agic_low_latency_service_account_name="$(RESOURCE_CONFIG_FILE="$federated_credential_config_file" python - <<'PY'
import json
import os
from pathlib import Path

config = json.loads(Path(os.environ["RESOURCE_CONFIG_FILE"]).read_text(encoding="utf-8"))
print(str(config.get("agicLowLatencyServiceAccountName", "sa-agic-lowlatency")).strip() or "sa-agic-lowlatency")
PY
)"

    keda_namespace="$(RESOURCE_CONFIG_FILE="$federated_credential_config_file" python - <<'PY'
import json
import os
from pathlib import Path

config = json.loads(Path(os.environ["RESOURCE_CONFIG_FILE"]).read_text(encoding="utf-8"))
print(str(config.get("kedaNamespace", "keda")).strip() or "keda")
PY
)"

    keda_operator_service_account_name="$(RESOURCE_CONFIG_FILE="$federated_credential_config_file" python - <<'PY'
import json
import os
from pathlib import Path

config = json.loads(Path(os.environ["RESOURCE_CONFIG_FILE"]).read_text(encoding="utf-8"))
print(str(config.get("kedaOperatorServiceAccountName", "keda-operator")).strip() or "keda-operator")
PY
)"

    environment_name_for_agic="$(COMMON_FILE="$common_file" python - <<'PY'
import json
import os
from pathlib import Path

common = json.loads(Path(os.environ["COMMON_FILE"]).read_text(encoding="utf-8"))
print(str(common.get("common", {}).get("environmentName", "")).strip())
PY
)"

    system_name_for_agic="$(COMMON_FILE="$common_file" python - <<'PY'
import json
import os
from pathlib import Path

common = json.loads(Path(os.environ["COMMON_FILE"]).read_text(encoding="utf-8"))
print(str(common.get("common", {}).get("systemName", "")).strip())
PY
)"

    standard_application_gateway_name="$(META_FILE="$application_gateway_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(meta.get("applicationGatewayName", "")).strip())
PY
)"

    low_latency_application_gateway_name="$(META_FILE="$application_gateway_low_latency_meta_file" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(meta.get("applicationGatewayName", "")).strip())
PY
)"

    # AGIC/KEDA の init スクリプトは resourceToggles の値に依存させず、
    # 必要な固有情報が取得できる場合は常に生成する。
    agic_standard_client_id_for_init="$(az identity show \
      --resource-group "$aks_resource_group_name" \
      --name "mi-${environment_name_for_agic}-${system_name_for_agic}-agic-standard" \
      --query clientId \
      -o tsv \
      --only-show-errors 2>/dev/null || true)"

    standard_application_gateway_id_for_init=""
    if [[ -n "$standard_application_gateway_name" ]]; then
      standard_application_gateway_id_for_init="$(az network application-gateway show \
        --resource-group "$application_gateway_resource_group_name" \
        --name "$standard_application_gateway_name" \
        --query id \
        -o tsv \
        --only-show-errors 2>/dev/null || true)"
    fi

    if [[ -n "$standard_application_gateway_id_for_init" && -n "$agic_standard_client_id_for_init" ]]; then
      include_low_latency_agic_for_init="false"
      low_latency_application_gateway_id_for_init=""
      agic_low_latency_client_id_for_init=""
      if [[ -n "$low_latency_application_gateway_name" ]]; then
        low_latency_application_gateway_id_for_init="$(az network application-gateway show \
          --resource-group "$application_gateway_resource_group_name" \
          --name "$low_latency_application_gateway_name" \
          --query id \
          -o tsv \
          --only-show-errors 2>/dev/null || true)"
        if [[ -n "$low_latency_application_gateway_id_for_init" ]]; then
          agic_low_latency_client_id_for_init="$(az identity show \
            --resource-group "$aks_resource_group_name" \
            --name "mi-${environment_name_for_agic}-${system_name_for_agic}-agic-lowlatency" \
            --query clientId \
            -o tsv \
            --only-show-errors 2>/dev/null || true)"
          if [[ -n "$agic_low_latency_client_id_for_init" ]]; then
            include_low_latency_agic_for_init="true"
          fi
        fi
      fi

      mkdir -p "$agic_controller_init_dir"
      agic_controller_init_script="$agic_controller_init_dir/deploy.sh"
      cat >"$agic_controller_init_script" <<EOF
#!/usr/bin/env bash
set -euo pipefail

az aks get-credentials \\
  --resource-group "$aks_resource_group_name" \\
  --name "$aks_name_for_post" \\
  --overwrite-existing \\
  --only-show-errors >/dev/null

helm upgrade --install agic-standard oci://mcr.microsoft.com/azure-application-gateway/charts/ingress-azure \\
  --namespace "$agic_namespace" \\
  --create-namespace \\
  --set-string appgw.applicationGatewayID="$standard_application_gateway_id_for_init" \\
  --set-string kubernetes.ingressClass="azure-application-gateway" \\
  --set-string serviceAccount.name="$agic_standard_service_account_name" \\
  --set serviceAccount.create=true \\
  --set-string serviceAccount.annotations.azure\\.workload\\.identity/client-id="$agic_standard_client_id_for_init" \\
  --set-string armAuth.type="workloadIdentity" \\
  --set-string armAuth.identityClientID="$agic_standard_client_id_for_init" \\
  --set-string armAuth.identityClientId="$agic_standard_client_id_for_init"
EOF
      if [[ "$include_low_latency_agic_for_init" == "true" ]]; then
        cat >>"$agic_controller_init_script" <<EOF
helm upgrade --install agic-lowlatency oci://mcr.microsoft.com/azure-application-gateway/charts/ingress-azure \\
  --namespace "$agic_namespace" \\
  --create-namespace \\
  --set-string appgw.applicationGatewayID="$low_latency_application_gateway_id_for_init" \\
  --set-string kubernetes.ingressClass="azure-application-gateway-low-latency" \\
  --set-string serviceAccount.name="$agic_low_latency_service_account_name" \\
  --set serviceAccount.create=true \\
  --set-string serviceAccount.annotations.azure\\.workload\\.identity/client-id="$agic_low_latency_client_id_for_init" \\
  --set-string armAuth.type="workloadIdentity" \\
  --set-string armAuth.identityClientID="$agic_low_latency_client_id_for_init" \\
  --set-string armAuth.identityClientId="$agic_low_latency_client_id_for_init"
EOF
      else
        cat >>"$agic_controller_init_script" <<'EOF'
echo "==> Skip AGIC Helm release: agic-lowlatency (required resources not found)"
EOF
      fi
      chmod +x "$agic_controller_init_script"
      echo "==> Generate init script: $agic_controller_init_script"
    else
      echo "==> Skip Generate init script: $agic_controller_init_dir/deploy.sh (required standard AGIC resources not found)"
    fi

    keda_operator_client_id_for_init="$(az identity show \
      --resource-group "$aks_resource_group_name" \
      --name "mi-${environment_name_for_agic}-${system_name_for_agic}-keda-operator" \
      --query clientId \
      -o tsv \
      --only-show-errors 2>/dev/null || true)"
    if [[ -n "$keda_operator_client_id_for_init" ]]; then
      mkdir -p "$keda_controller_init_dir"
      keda_controller_init_script="$keda_controller_init_dir/deploy.sh"
      cat >"$keda_controller_init_script" <<EOF
#!/usr/bin/env bash
set -euo pipefail

az aks get-credentials \\
  --resource-group "$aks_resource_group_name" \\
  --name "$aks_name_for_post" \\
  --overwrite-existing \\
  --only-show-errors >/dev/null

helm repo add kedacore https://kedacore.github.io/charts >/dev/null
helm repo update >/dev/null
helm upgrade --install keda kedacore/keda \\
  --namespace "$keda_namespace" \\
  --create-namespace \\
  --set serviceAccount.operator.create=true \\
  --set-string serviceAccount.operator.name="$keda_operator_service_account_name" \\
  --set-string serviceAccount.operator.annotations.azure\\.workload\\.identity/client-id="$keda_operator_client_id_for_init" \\
  --set podIdentity.azureWorkload.enabled=true \\
  --set-string podIdentity.azureWorkload.clientId="$keda_operator_client_id_for_init"
EOF
      chmod +x "$keda_controller_init_script"
      echo "==> Generate init script: $keda_controller_init_script"
    else
      echo "==> Skip Generate init script: $keda_controller_init_dir/deploy.sh (required KEDA resources not found)"
    fi

    echo "==> Generate frontend Helm values file"
    COMMON_FILE="$common_file" \
    TEMPLATE_FILE="$frontend_values_template_file" \
    OUTPUT_FILE="$frontend_values_generated_file" \
    "$frontend_values_sync_script"

    echo "==> Generate backend Helm values file"
    COMMON_FILE="$common_file" \
    AKS_META_FILE="$aks_meta_file" \
    STORAGE_CONFIG_FILE="$storage_config_file" \
    TEMPLATE_FILE="$backend_values_template_file" \
    OUTPUT_FILE="$backend_values_generated_file" \
    "$backend_values_sync_script"

    cat <<'EOF'
------------------------------------------------------------
NOTICE: Backend Helm values (manual update required)
[EN] Please review and update the following parameters in backend values before Helm deploy:
     - ingress.standard.host
     - ingress.lowLatency.host
     - config.env.FRONTEND_BASE_URL
     - config.env.CSRF_TRUSTED_ORIGINS
     - config.env.ENTRA_TENANT_ID
     - config.env.ENTRA_CLIENT_ID
     - config.env.ENTRA_REDIRECT_URI
     - config.env.ENTRA_INTERNAL_DOMAINS

[JA] Helm デプロイ前に、backend values の以下パラメータを確認し、実環境値へ更新してください:
     - ingress.standard.host
     - ingress.lowLatency.host
     - config.env.FRONTEND_BASE_URL
     - config.env.CSRF_TRUSTED_ORIGINS
     - config.env.ENTRA_TENANT_ID
     - config.env.ENTRA_CLIENT_ID
     - config.env.ENTRA_REDIRECT_URI
     - config.env.ENTRA_INTERNAL_DOMAINS
------------------------------------------------------------
EOF
  fi
fi
