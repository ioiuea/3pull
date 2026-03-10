#!/usr/bin/env bash

# Virtual Network 用 .bicepparam から vnetName を抽出する。
# 返り値:
#   - 成功: vnetName（標準出力）
#   - 失敗/未検出: 空文字
extract_vnet_name_from_params_file() {
  local params_file="$1"
  PARAMS_FILE="$params_file" python - <<'PY'
import os
import re
from pathlib import Path

content = Path(os.environ["PARAMS_FILE"]).read_text(encoding="utf-8")
match = re.search(r"^param vnetName = '([^']*)'$", content, flags=re.MULTILINE)
print(match.group(1) if match else "")
PY
}

# Azure 上の既存 VNET を確認する。
# 引数:
#   $1: VNET の resource group 名
#   $2: VNET 名
# 返り値（標準出力）:
#   - 見つかった場合: VNET 名
#   - 見つからない場合: 空文字
#   - 確認失敗（タイムアウト/リトライ上限）: "__CHECK_FAILED__"
check_existing_virtual_network_name() {
  local vnet_resource_group_name="$1"
  local vnet_name="$2"

  VNET_RG_NAME="$vnet_resource_group_name" VNET_NAME="$vnet_name" SUBSCRIPTION_ID="$(az account show --query id -o tsv)" python - <<'PY'
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
}

run_virtual_network_deployment() {
  # 既存 VNET がある環境では peering 等の手動設定を壊さないため、
  # 既存検出時は VNET の apply/update をスキップする。
  vnet_deploy="$(meta_bool "$vnet_meta_file" "deploy")"
  vnet_params_file="$(meta_get "$vnet_meta_file" "paramsFile")"

  vnet_apply_skipped_existing=false
  vnet_created_in_this_run=false

  if [[ "$vnet_deploy" == "true" ]]; then
    vnet_name="$(extract_vnet_name_from_params_file "$vnet_params_file")"

    if [[ -z "$vnet_name" ]]; then
      echo "vnetName が取得できませんでした: $vnet_params_file" >&2
      exit 1
    fi

    echo "==> Check existing Virtual Network: $vnet_name"
    existing_vnet_name="$(check_existing_virtual_network_name "$vnet_resource_group_name" "$vnet_name")"

    if [[ "$existing_vnet_name" == "__CHECK_FAILED__" ]]; then
      echo "==> エラー: 既存 Virtual Network の存在確認に失敗しました（タイムアウト/リトライ上限）。" >&2
      echo "==> Error: Failed to check existing Virtual Network state (timeout/retry exhausted)." >&2
      echo "==> Azure CLI のログイン状態・セッション・ネットワークを確認して再実行してください。" >&2
      echo "==> Please verify Azure CLI login/session/network and retry." >&2
      exit 1
    fi

    if [[ -n "$existing_vnet_name" ]]; then
      vnet_apply_skipped_existing=true
      cat <<EOF_INNER
------------------------------------------------------------
NOTICE: Virtual Network
[JA] 既存の Virtual Network を検出したため、Virtual Network の適用/更新をスキップします。
     VNET 名: $existing_vnet_name
[EN] Existing Virtual Network detected. Skipping Virtual Network apply/update.
     VNET Name: $existing_vnet_name
------------------------------------------------------------
EOF_INNER
    else
      echo "==> Deploy Virtual Network"
      run_bicep_deployment "virtual-network" az deployment group create \
        --name "main-network-virtual-network-${timestamp}" \
        --resource-group "$vnet_resource_group_name" \
        --parameters "$vnet_params_file" \
        ${what_if:+$what_if}
      vnet_created_in_this_run=true

      cat <<'EOF_INNER'
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
EOF_INNER
      exit 0
    fi
  else
    echo "==> Skip Virtual Network (resourceToggles.virtualNetwork=false)"
  fi
}

run_subnets_base_deployment() {
  # まずは NSG / UDR を付けずにサブネットだけ作成する。
  subnets_deploy="$(meta_bool "$subnets_meta_file" "deploy")"
  subnets_params_file="$(meta_get "$subnets_meta_file" "paramsFile")"

  deploy_group_if_enabled \
    "$subnets_deploy" \
    "Deploy Subnets (without NSG/RouteTable)" \
    "subnets" \
    "main-network-subnets-${timestamp}" \
    "$subnets_resource_group_name" \
    "$subnets_params_file" \
    "Skip Subnets (resourceToggles.subnets=false)"
}

run_firewall_deployment() {
  # Firewall Policy が既存の場合、既存ポリシーを維持するため
  # ポリシー更新だけスキップして Firewall リソース本体を実行する。
  firewall_deploy="$(meta_bool "$firewall_meta_file" "deploy")"
  firewall_params_file="$(meta_get "$firewall_meta_file" "paramsFile")"

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
      cat <<EOF_INNER
------------------------------------------------------------
NOTICE: Firewall Policy
[EN] Existing Firewall Policy detected. Skipping policy apply/update.
     Policy Name: $existing_firewall_policy_name
[JA] 既存の Firewall Policy を検出したため、Policy の適用/更新をスキップします。
     Policy 名: $existing_firewall_policy_name
------------------------------------------------------------
EOF_INNER
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
}

run_route_tables_nsgs_subnet_attachments() {
  # 注意:
  # - network.egressNextHopIp 未指定時は、実際の Firewall Private IP を Azure から再取得し、
  #   その値で route-tables.bicepparam を再生成してから適用する。
  # - これにより nextHop の古い値で UDR が適用されることを防ぐ。
  application_gateway_deploy="$(meta_bool "$application_gateway_meta_file" "deploy")"
  application_gateway_params_file="$(meta_get "$application_gateway_meta_file" "paramsFile")"

  application_gateway_low_latency_deploy="$(meta_bool "$application_gateway_low_latency_meta_file" "deploy")"
  application_gateway_low_latency_params_file="$(meta_get "$application_gateway_low_latency_meta_file" "paramsFile")"

  route_tables_deploy="$(meta_bool "$route_tables_meta_file" "deploy")"
  route_tables_params_file="$(meta_get "$route_tables_meta_file" "paramsFile")"

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

        route_tables_params_file="$(meta_get "$route_tables_meta_file" "paramsFile")"
      fi
    fi

    deploy_group_if_enabled \
      "$route_tables_deploy" \
      "Deploy Route Tables (UDR)" \
      "route-tables" \
      "main-network-route-tables-${timestamp}" \
      "$route_tables_resource_group_name" \
      "$route_tables_params_file" \
      "Skip Route Tables (resourceToggles.subnets=false)"
  else
    echo "==> Skip Route Tables (resourceToggles.subnets=false)"
  fi

  nsgs_deploy="$(meta_bool "$nsgs_meta_file" "deploy")"
  nsgs_params_file="$(meta_get "$nsgs_meta_file" "paramsFile")"

  deploy_group_if_enabled \
    "$nsgs_deploy" \
    "Deploy NSGs" \
    "nsgs" \
    "main-network-nsgs-${timestamp}" \
    "$nsgs_resource_group_name" \
    "$nsgs_params_file" \
    "Skip NSGs (resourceToggles.subnets=false)"

  subnet_attachments_deploy="$(meta_bool "$subnet_attachments_meta_file" "deploy")"
  subnet_attachments_params_file="$(meta_get "$subnet_attachments_meta_file" "paramsFile")"

  deploy_group_if_enabled \
    "$subnet_attachments_deploy" \
    "Attach Route Tables / NSGs to Subnets" \
    "subnet-attachments" \
    "main-network-subnet-attachments-${timestamp}" \
    "$subnet_attachments_resource_group_name" \
    "$subnet_attachments_params_file" \
    "Skip Subnet Attachments (resourceToggles.subnets=false)"
}
