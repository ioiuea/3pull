#!/usr/bin/env python3
"""Azure Managed Redis 用 bicepparam を生成する。"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


def quote(value: str) -> str:
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def normalize_redis_name(environment_name: str, system_name: str) -> str:
    env = re.sub(r"[^a-z0-9-]", "-", environment_name.lower())
    system = re.sub(r"[^a-z0-9-]", "-", system_name.lower())
    return re.sub(r"-{2,}", "-", f"redis-{env}-{system}").strip("-")


def identity_exists(resource_group_name: str, identity_name: str) -> bool:
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


def get_identity_principal_id(resource_group_name: str, identity_name: str) -> str:
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
            "principalId",
            "-o",
            "tsv",
            "--only-show-errors",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    principal_id = result.stdout.strip()
    if result.returncode != 0 or not principal_id:
        raise SystemExit(
            "Azure Managed Redis の Access Policy 付与に必要な "
            "API Managed Identity の principalId を取得できません"
        )
    return principal_id


common_path = Path(os.environ["COMMON_FILE"])
config_path = Path(os.environ["RESOURCE_CONFIG_FILE"])
managed_ids_meta_path = Path(os.environ["MANAGED_IDS_META_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))
managed_ids_meta = json.loads(managed_ids_meta_path.read_text(encoding="utf-8"))

common_values = common.get("common", {})
network_values = common.get("network", {})
redis_values = common.get("redis", {})

environment_name = str(common_values.get("environmentName", "")).strip()
system_name = str(common_values.get("systemName", "")).strip()
location = str(common_values.get("location", "")).strip()

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
managed_identity_resource_group_name = managed_ids_meta.get("resourceGroupName", "")
if not managed_identity_resource_group_name:
    raise SystemExit("managed ids meta の resourceGroupName が取得できません")

api_managed_identity_name = f"mi-{environment_name}-{system_name}-api"
redis_ops_managed_identity_name = f"mi-{environment_name}-{system_name}-redis-ops"
toggle_enabled = bool(common.get("resourceToggles", {}).get("redis", True))
enable_access_policy_assignment = toggle_enabled and identity_exists(
    managed_identity_resource_group_name,
    api_managed_identity_name,
)
api_managed_identity_principal_id = (
    get_identity_principal_id(managed_identity_resource_group_name, api_managed_identity_name)
    if enable_access_policy_assignment
    else ""
)
enable_redis_ops_access_policy_assignment = toggle_enabled and identity_exists(
    managed_identity_resource_group_name,
    redis_ops_managed_identity_name,
)
redis_ops_managed_identity_principal_id = (
    get_identity_principal_id(managed_identity_resource_group_name, redis_ops_managed_identity_name)
    if enable_redis_ops_access_policy_assignment
    else ""
)

redis_name = normalize_redis_name(environment_name, system_name)
redis_host = f"{redis_name}.{location}.redis.azure.net"
redis_port = 10000
private_endpoint_name = f"pep-redis-{environment_name}-{system_name}"
private_dns_zone_group_name = f"dnszg-redis-{environment_name}-{system_name}"
private_dns_vnet_link_name = f"link-redis-to-vnet-{environment_name}-{system_name}"
vnet_name = f"vnet-{environment_name}-{system_name}"

log_analytics_name = f"log-{environment_name}-{system_name}"
log_analytics_resource_group_name = f"rg-{environment_name}-{system_name}-monitor"

enable_centralized_private_dns = bool(network_values.get("enableCentralizedPrivateDns", False))
deploy = bool(common.get("resourceToggles", {}).get("redis", True))

sku_name = str(redis_values.get("skuName", config.get("skuName", "Balanced_B0"))).strip()
high_availability = "Enabled" if bool(redis_values.get("highAvailabilityEnabled", True)) else "Disabled"

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "redis-managed.bicepparam"

lines = [
    "using '../bicep/main.redis-managed.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param logAnalyticsName = {quote(log_analytics_name)}",
    f"param logAnalyticsResourceGroupName = {quote(log_analytics_resource_group_name)}",
    f"param vnetName = {quote(vnet_name)}",
    f"param vnetResourceGroupName = {quote(vnet_resource_group_name)}",
    f"param apiManagedIdentityPrincipalId = {quote(api_managed_identity_principal_id)}",
    f"param enableAccessPolicyAssignment = {'true' if enable_access_policy_assignment else 'false'}",
    f"param redisOpsManagedIdentityPrincipalId = {quote(redis_ops_managed_identity_principal_id)}",
    f"param enableRedisOpsAccessPolicyAssignment = {'true' if enable_redis_ops_access_policy_assignment else 'false'}",
    f"param redisName = {quote(redis_name)}",
    f"param minimumTlsVersion = {quote(config.get('minimumTlsVersion', '1.2'))}",
    f"param publicNetworkAccess = {quote(config.get('publicNetworkAccess', 'Disabled'))}",
    f"param redisSkuName = {quote(sku_name)}",
    f"param highAvailability = {quote(high_availability)}",
    "param databaseName = 'default'",
    f"param accessPolicyName = {quote(config.get('accessPolicyName', 'default'))}",
    f"param accessKeysAuthentication = {quote(config.get('accessKeysAuthentication', 'Disabled'))}",
    f"param clientProtocol = {quote(config.get('clientProtocol', 'Encrypted'))}",
    f"param clusteringPolicy = {quote(config.get('clusteringPolicy', 'OSSCluster'))}",
    f"param redisPort = {redis_port}",
    f"param privateEndpointName = {quote(private_endpoint_name)}",
    f"param privateDnsZoneName = {quote(config.get('privateDnsZoneName', 'privatelink.redis.azure.net'))}",
    f"param privateDnsZoneGroupName = {quote(private_dns_zone_group_name)}",
    f"param privateDnsVnetLinkName = {quote(private_dns_vnet_link_name)}",
    f"param enableCentralizedPrivateDns = {'true' if enable_centralized_private_dns else 'false'}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

meta = {
    "resourceGroupName": resource_group_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
    "redisName": redis_name,
    "redisHost": redis_host,
    "redisPort": redis_port,
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
