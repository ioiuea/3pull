#!/usr/bin/env bash

run_post_deploy_actions() {
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
    cat <<'EOF_INNER'
------------------------------------------------------------
NOTICE: Virtual Network (Initial Provisioning)
[EN] A new Virtual Network has been created. If peering with other VNETs is required,
     configure it from Azure Portal: https://portal.azure.com/

[JA] Virtual Network を新規作成しています。別 VNET とのピアリングなどが必要な場合は、
     Azure Portal（https://portal.azure.com/）から設定してください。
------------------------------------------------------------
EOF_INNER
  fi

  if [[ "$firewall_deploy" == "true" && -z "$egress_next_hop_ip" && "$firewall_policy_apply_skipped" != "true" ]]; then
    cat <<'EOF_INNER'
------------------------------------------------------------
NOTICE: Firewall Outbound Rule (Initial Provisioning)
[EN] Because network.egressNextHopIp is not specified, outbound traffic in Firewall Policy is temporarily allowed to Any
     to permit required external communication during the initial Azure Kubernetes Service / maintenance VM provisioning.
     After provisioning, review and tighten Firewall Policy allow/deny rules according to your enterprise policy.
     Edit Firewall Policy from Azure Portal: https://portal.azure.com/

[JA] network.egressNextHopIp が未指定のため、初期構築段階では Azure Kubernetes Service / メンテナンス VM の構築に必要な外部通信を許可する目的で、
     Firewall Policy のアウトバウンド通信が宛先 Any で許可される構成になります。
     構築完了後は、企業ポリシーに合わせて Firewall Policy の許可/遮断ルールを見直して運用してください。
     Firewall Policy の編集は Azure Portal（https://portal.azure.com/）から実施してください。
------------------------------------------------------------
EOF_INNER
  fi

  aks_name_for_post="$(meta_get "$aks_meta_file" "aksName")"

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
    cat <<'EOF_INNER'
------------------------------------------------------------
NOTICE: Skip Helm / Values Export
[EN] AKS is not found in the target resource group.
     AGIC/KEDA init script generation and Helm values export are skipped.
     Create/deploy AKS first, then run this script again.

[JA] 対象リソースグループに AKS が存在しないため、
     AGIC/KEDA 初期化スクリプト生成、および Helm values エクスポートをスキップします。
     先に AKS を作成/デプロイしてから、このスクリプトを再実行してください。
------------------------------------------------------------
EOF_INNER
  else
    if [[ -n "$what_if" ]]; then
      echo "==> Skip Generate AGIC/KEDA init scripts (--what-if)"
      echo "==> Skip Generate frontend Helm values file (--what-if)"
      echo "==> Skip Generate backend Helm values file (--what-if)"
      echo "==> Skip Generate ip rate limit ops env (--what-if)"
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

      standard_application_gateway_name="$(meta_get_stripped "$application_gateway_meta_file" "applicationGatewayName")"
      low_latency_application_gateway_name="$(meta_get_stripped "$application_gateway_low_latency_meta_file" "applicationGatewayName")"

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
        cat >"$agic_controller_init_script" <<EOF_INNER
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
  --set-string nodeSelector.kubernetes\\.azure\\.com/mode="system" \\
  --set-string kubernetes.ingressClass="azure-application-gateway" \\
  --set-string serviceAccount.name="$agic_standard_service_account_name" \\
  --set serviceAccount.create=true \\
  --set-string serviceAccount.annotations.azure\\.workload\\.identity/client-id="$agic_standard_client_id_for_init" \\
  --set-string armAuth.type="workloadIdentity" \\
  --set-string armAuth.identityClientID="$agic_standard_client_id_for_init" \\
  --set-string armAuth.identityClientId="$agic_standard_client_id_for_init"
EOF_INNER
        if [[ "$include_low_latency_agic_for_init" == "true" ]]; then
          cat >>"$agic_controller_init_script" <<EOF_INNER
helm upgrade --install agic-lowlatency oci://mcr.microsoft.com/azure-application-gateway/charts/ingress-azure \\
  --namespace "$agic_namespace" \\
  --create-namespace \\
  --set-string appgw.applicationGatewayID="$low_latency_application_gateway_id_for_init" \\
  --set-string nodeSelector.kubernetes\\.azure\\.com/mode="system" \\
  --set-string kubernetes.ingressClass="azure-application-gateway-low-latency" \\
  --set-string serviceAccount.name="$agic_low_latency_service_account_name" \\
  --set serviceAccount.create=true \\
  --set-string serviceAccount.annotations.azure\\.workload\\.identity/client-id="$agic_low_latency_client_id_for_init" \\
  --set-string armAuth.type="workloadIdentity" \\
  --set-string armAuth.identityClientID="$agic_low_latency_client_id_for_init" \\
  --set-string armAuth.identityClientId="$agic_low_latency_client_id_for_init"
EOF_INNER
        else
          cat >>"$agic_controller_init_script" <<'EOF_INNER'
echo "==> Skip AGIC Helm release: agic-lowlatency (required resources not found)"
EOF_INNER
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
        cat >"$keda_controller_init_script" <<EOF_INNER
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
  --set-string nodeSelector.kubernetes\\.azure\\.com/mode="system" \\
  --set serviceAccount.operator.create=true \\
  --set-string serviceAccount.operator.name="$keda_operator_service_account_name" \\
  --set-string serviceAccount.operator.annotations.azure\\.workload\\.identity/client-id="$keda_operator_client_id_for_init" \\
  --set podIdentity.azureWorkload.enabled=true \\
  --set-string podIdentity.azureWorkload.clientId="$keda_operator_client_id_for_init"
EOF_INNER
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
      REDIS_META_FILE="$redis_meta_file" \
      STORAGE_CONFIG_FILE="$storage_config_file" \
      SUBNETS_CONFIG_FILE="$subnets_config_file" \
      TEMPLATE_FILE="$backend_values_template_file" \
      OUTPUT_FILE="$backend_values_generated_file" \
      "$backend_values_sync_script"

      if [[ "$(meta_bool "$redis_meta_file" "deploy" "false")" == "true" ]]; then
        echo "==> Generate ip rate limit ops env"
        COMMON_FILE="$common_file" \
        MANAGED_IDS_META_FILE="$managed_ids_meta_file" \
        REDIS_META_FILE="$redis_meta_file" \
        OUTPUT_FILE="$ip_rate_limit_generated_env_file" \
        "$ip_rate_limit_env_sync_script"
      else
        echo "==> Skip Generate ip rate limit ops env (resourceToggles.redis=false)"
      fi

      cat <<'EOF_INNER'
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
EOF_INNER
    fi
  fi
}
