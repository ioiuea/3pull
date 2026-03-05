#!/usr/bin/env python3
"""Key Vault 用 bicepparam を生成する。"""

import json
import os
from pathlib import Path


def quote(value: str) -> str:
    """Bicep 文字列リテラル向けに single quote をエスケープする。"""
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


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
key_vault_values = common.get("keyVault", {})

environment_name = common_values.get("environmentName", "")
system_name = common_values.get("systemName", "")
location = common_values.get("location", "")

if not environment_name or not system_name or not location:
    raise SystemExit(
        "common.parameter.json の common.environmentName / "
        "common.systemName / common.location を設定してください"
    )

modules_name = config.get("modulesName", "svc")
enable_resource_lock = bool(common_values.get("enableResourceLock", True))
lock_kind = config.get("lockKind", "CanNotDelete") if enable_resource_lock else ""
resource_group_name = f"rg-{environment_name}-{system_name}-{modules_name}"
vnet_resource_group_name = f"rg-{environment_name}-{system_name}-nw"
managed_identity_resource_group_name = aks_meta.get("resourceGroupName", "")
if not managed_identity_resource_group_name:
    raise SystemExit("AKS meta の resourceGroupName が取得できません")
api_managed_identity_name = f"mi-{environment_name}-{system_name}-api"
worker_managed_identity_name = f"mi-{environment_name}-{system_name}-worker"
cleanup_managed_identity_name = f"mi-{environment_name}-{system_name}-cleanup"
enable_workload_identity_rbac = bool(key_vault_values.get("enableWorkloadIdentityRbac", True))

key_vault_name = f"kv-{environment_name}-{system_name}"
private_endpoint_name = f"pep-kv-{environment_name}-{system_name}"
private_dns_zone_group_name = f"dnszg-kv-{environment_name}-{system_name}"
private_dns_vnet_link_name = f"link-kv-to-vnet-{environment_name}-{system_name}"
vnet_name = f"vnet-{environment_name}-{system_name}"

log_analytics_name = f"log-{environment_name}-{system_name}"
log_analytics_resource_group_name = f"rg-{environment_name}-{system_name}-monitor"

enable_centralized_private_dns = bool(network_values.get("enableCentralizedPrivateDns", False))
deploy = bool(common.get("resourceToggles", {}).get("keyVault", True))

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "key-vault.bicepparam"

lines = [
    "using '../bicep/main.key-vault.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param logAnalyticsName = {quote(log_analytics_name)}",
    f"param logAnalyticsResourceGroupName = {quote(log_analytics_resource_group_name)}",
    f"param vnetName = {quote(vnet_name)}",
    f"param vnetResourceGroupName = {quote(vnet_resource_group_name)}",
    f"param managedIdentityResourceGroupName = {quote(managed_identity_resource_group_name)}",
    f"param apiManagedIdentityName = {quote(api_managed_identity_name)}",
    f"param workerManagedIdentityName = {quote(worker_managed_identity_name)}",
    f"param cleanupManagedIdentityName = {quote(cleanup_managed_identity_name)}",
    f"param enableWorkloadIdentityRbac = {'true' if enable_workload_identity_rbac else 'false'}",
    f"param keyVaultName = {quote(key_vault_name)}",
    f"param privateEndpointName = {quote(private_endpoint_name)}",
    f"param privateDnsZoneName = {quote(config.get('privateDnsZoneName', 'privatelink.vaultcore.azure.net'))}",
    f"param privateDnsZoneGroupName = {quote(private_dns_zone_group_name)}",
    f"param privateDnsVnetLinkName = {quote(private_dns_vnet_link_name)}",
    f"param keyVaultSkuFamily = {quote(config.get('keyVaultSkuFamily', 'A'))}",
    f"param keyVaultSkuName = {quote(config.get('keyVaultSkuName', 'standard'))}",
    f"param publicNetworkAccess = {quote(config.get('publicNetworkAccess', 'Disabled'))}",
    f"param enableRbacAuthorization = {'true' if bool(config.get('enableRbacAuthorization', True)) else 'false'}",
    f"param enableSoftDelete = {'true' if bool(config.get('enableSoftDelete', True)) else 'false'}",
    f"param enablePurgeProtection = {'true' if bool(config.get('enablePurgeProtection', True)) else 'false'}",
    f"param softDeleteRetentionInDays = {int(config.get('softDeleteRetentionInDays', 90))}",
    f"param enableCentralizedPrivateDns = {'true' if enable_centralized_private_dns else 'false'}",
    f"param keyVaultOfficerObjectId = {quote(config.get('keyVaultOfficerObjectId', ''))}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

meta = {
    "resourceGroupName": resource_group_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
