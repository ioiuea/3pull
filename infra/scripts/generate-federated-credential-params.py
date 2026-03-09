#!/usr/bin/env python3
"""Federated Credential 用 bicepparam を生成する。"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def quote(value: str) -> str:
    """Bicep 文字列リテラル向けに single quote をエスケープする。"""
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def run_az(cmd: list[str]) -> str:
    """Azure CLI を実行し、stdout を返す。失敗時は終了する。"""
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise SystemExit(f"Azure CLI 実行失敗: {' '.join(cmd)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def identity_exists(resource_group_name: str, identity_name: str) -> bool:
    """Managed Identity の存在有無を判定する。"""
    result = subprocess.run(
        [
            "az",
            "identity",
            "show",
            "--resource-group",
            resource_group_name,
            "--name",
            identity_name,
            "--query",
            "id",
            "-o",
            "tsv",
            "--only-show-errors",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


common_path = Path(os.environ["COMMON_FILE"])
config_path = Path(os.environ["RESOURCE_CONFIG_FILE"])
aks_meta_path = Path(os.environ["AKS_META_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))
aks_meta = json.loads(aks_meta_path.read_text(encoding="utf-8"))

common_values = common.get("common", {})
network_values = common.get("network", {})
toggles = common.get("resourceToggles", {})
environment_name = str(common_values.get("environmentName", "")).strip()
system_name = str(common_values.get("systemName", "")).strip()
if not environment_name or not system_name:
    raise SystemExit(
        "common.parameter.json の common.environmentName / common.systemName を設定してください"
    )

base_deploy = bool(toggles.get("aks", True)) and bool(config.get("enabled", True))
if not base_deploy:
    meta = {
        "resourceGroupName": str(aks_meta.get("resourceGroupName", "")).strip(),
        "deploy": False,
        "paramsFile": "",
    }
    out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    raise SystemExit(0)

resource_group_name = str(aks_meta.get("resourceGroupName", "")).strip()
aks_name = str(aks_meta.get("aksName", "")).strip()
if not resource_group_name or not aks_name:
    raise SystemExit("AKS meta の resourceGroupName / aksName が取得できません")

api_managed_identity_name = f"mi-{environment_name}-{system_name}-api"
worker_managed_identity_name = f"mi-{environment_name}-{system_name}-worker"
cleanup_managed_identity_name = f"mi-{environment_name}-{system_name}-cleanup"
keda_operator_managed_identity_name = f"mi-{environment_name}-{system_name}-keda-operator"
agic_standard_managed_identity_name = f"mi-{environment_name}-{system_name}-agic-standard"
agic_low_latency_managed_identity_name = f"mi-{environment_name}-{system_name}-agic-lowlatency"
enable_low_latency_application_gateway_subnet = bool(
    network_values.get("enableLowLatencyApplicationGatewaySubnet", False)
)

deploy = all(
    [
        identity_exists(resource_group_name, api_managed_identity_name),
        identity_exists(resource_group_name, worker_managed_identity_name),
        identity_exists(resource_group_name, cleanup_managed_identity_name),
        identity_exists(resource_group_name, keda_operator_managed_identity_name),
        identity_exists(resource_group_name, agic_standard_managed_identity_name),
        (
            identity_exists(resource_group_name, agic_low_latency_managed_identity_name)
            if enable_low_latency_application_gateway_subnet
            else True
        ),
    ]
)

if not deploy:
    meta = {
        "resourceGroupName": resource_group_name,
        "deploy": False,
        "paramsFile": "",
    }
    out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    raise SystemExit(0)

oidc_issuer_url = run_az(
    [
        "az",
        "aks",
        "show",
        "--resource-group",
        resource_group_name,
        "--name",
        aks_name,
        "--query",
        "oidcIssuerProfile.issuerUrl",
        "-o",
        "tsv",
    ]
)
if not oidc_issuer_url:
    raise SystemExit(
        "AKS の OIDC issuer URL が取得できません。"
        "AKS の OIDC issuer / Workload Identity が有効か確認してください。"
    )

app_namespace = str(config.get("appNamespace", system_name)).strip() or system_name
keda_namespace = str(config.get("kedaNamespace", "keda")).strip() or "keda"
keda_operator_service_account_name = (
    str(config.get("kedaOperatorServiceAccountName", "keda-operator")).strip() or "keda-operator"
)
agic_namespace = str(config.get("agicNamespace", "ingress")).strip() or "ingress"
agic_standard_service_account_name = (
    str(config.get("agicStandardServiceAccountName", "sa-agic-standard")).strip() or "sa-agic-standard"
)
agic_low_latency_service_account_name = (
    str(config.get("agicLowLatencyServiceAccountName", "sa-agic-lowlatency")).strip() or "sa-agic-lowlatency"
)

api_service_account_name = f"sa-{environment_name}-{system_name}-api"
worker_service_account_name = f"sa-{environment_name}-{system_name}-worker"
cleanup_service_account_name = f"sa-{environment_name}-{system_name}-cleanup"

api_federated_credential_name = f"fic-{environment_name}-{system_name}-api"
worker_federated_credential_name = f"fic-{environment_name}-{system_name}-worker"
cleanup_federated_credential_name = f"fic-{environment_name}-{system_name}-cleanup"
keda_operator_federated_credential_name = f"fic-{environment_name}-{system_name}-keda-operator"
agic_standard_federated_credential_name = f"fic-{environment_name}-{system_name}-agic-standard"
agic_low_latency_federated_credential_name = f"fic-{environment_name}-{system_name}-agic-lowlatency"

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "federated-credential.bicepparam"

lines = [
    "using '../bicep/main.federated-credential.bicep'",
    f"param oidcIssuerUrl = {quote(oidc_issuer_url)}",
    f"param apiManagedIdentityName = {quote(api_managed_identity_name)}",
    f"param workerManagedIdentityName = {quote(worker_managed_identity_name)}",
    f"param cleanupManagedIdentityName = {quote(cleanup_managed_identity_name)}",
    f"param kedaOperatorManagedIdentityName = {quote(keda_operator_managed_identity_name)}",
    f"param appNamespace = {quote(app_namespace)}",
    f"param apiServiceAccountName = {quote(api_service_account_name)}",
    f"param workerServiceAccountName = {quote(worker_service_account_name)}",
    f"param cleanupServiceAccountName = {quote(cleanup_service_account_name)}",
    f"param agicNamespace = {quote(agic_namespace)}",
    f"param agicStandardServiceAccountName = {quote(agic_standard_service_account_name)}",
    f"param agicLowLatencyServiceAccountName = {quote(agic_low_latency_service_account_name)}",
    f"param kedaNamespace = {quote(keda_namespace)}",
    f"param kedaOperatorServiceAccountName = {quote(keda_operator_service_account_name)}",
    f"param agicStandardManagedIdentityName = {quote(agic_standard_managed_identity_name)}",
    f"param agicLowLatencyManagedIdentityName = {quote(agic_low_latency_managed_identity_name)}",
    f"param enableLowLatencyApplicationGatewaySubnet = {'true' if enable_low_latency_application_gateway_subnet else 'false'}",
    f"param apiFederatedCredentialName = {quote(api_federated_credential_name)}",
    f"param workerFederatedCredentialName = {quote(worker_federated_credential_name)}",
    f"param cleanupFederatedCredentialName = {quote(cleanup_federated_credential_name)}",
    f"param kedaOperatorFederatedCredentialName = {quote(keda_operator_federated_credential_name)}",
    f"param agicStandardFederatedCredentialName = {quote(agic_standard_federated_credential_name)}",
    f"param agicLowLatencyFederatedCredentialName = {quote(agic_low_latency_federated_credential_name)}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

meta = {
    "resourceGroupName": resource_group_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
