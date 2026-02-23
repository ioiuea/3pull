#!/usr/bin/env python3
"""Azure Cache for Redis 用 bicepparam を生成する。"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path


def quote(value: str) -> str:
    """Bicep 文字列リテラル向けに single quote をエスケープする。"""
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def normalize_redis_name(environment_name: str, system_name: str) -> str:
    """Redis 名の制約に合わせて正規化する。"""
    env = re.sub(r"[^a-z0-9-]", "-", environment_name.lower())
    system = re.sub(r"[^a-z0-9-]", "-", system_name.lower())
    name = re.sub(r"-{2,}", "-", f"redis-{env}-{system}").strip("-")

    if len(name) < 1 or len(name) > 63:
        raise SystemExit(
            "Redis 名が長さ制約(1〜63文字)を満たしません。"
            "common.environmentName / common.systemName を調整してください。"
        )

    if not re.fullmatch(r"[a-z](?:[a-z0-9-]*[a-z0-9])?", name):
        raise SystemExit("Redis 名が命名制約を満たしません。")

    return name


common_path = Path(os.environ["COMMON_FILE"])
config_path = Path(os.environ["RESOURCE_CONFIG_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))

common_values = common.get("common", {})
network_values = common.get("network", {})
redis_values = common.get("redis", {})

environment_name = common_values.get("environmentName", "")
system_name = common_values.get("systemName", "")
location = common_values.get("location", "")

if not environment_name or not system_name or not location:
    raise SystemExit(
        "common.parameter.json の common.environmentName / "
        "common.systemName / common.location を設定してください"
    )

modules_name = config.get("modulesName", "svc")
network_modules_name = config.get("networkModulesName", "nw")
enable_resource_lock = bool(common_values.get("enableResourceLock", True))
lock_kind = config.get("lockKind", "CanNotDelete") if enable_resource_lock else ""

resource_group_name = f"rg-{environment_name}-{system_name}-{modules_name}"
vnet_resource_group_name = f"rg-{environment_name}-{system_name}-{network_modules_name}"
vnet_name = f"vnet-{environment_name}-{system_name}"

redis_name = normalize_redis_name(environment_name, system_name)
private_endpoint_name = f"pep-redis-{environment_name}-{system_name}"
private_dns_zone_group_name = f"dnszg-redis-{environment_name}-{system_name}"
private_dns_vnet_link_name = f"link-redis-to-vnet-{environment_name}-{system_name}"

log_analytics_name = f"log-{environment_name}-{system_name}"
log_analytics_resource_group_name = f"rg-{environment_name}-{system_name}-monitor"

enable_centralized_private_dns = bool(network_values.get("enableCentralizedPrivateDns", False))
toggles = common.get("resourceToggles", {})
deploy = bool(toggles.get("redis", True))

sku_name = str(redis_values.get("skuName", "Basic"))
sku_family = "P" if sku_name == "Premium" else "C"

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "redis.bicepparam"

lines = [
    "using '../bicep/main.redis.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param logAnalyticsName = {quote(log_analytics_name)}",
    f"param logAnalyticsResourceGroupName = {quote(log_analytics_resource_group_name)}",
    f"param vnetName = {quote(vnet_name)}",
    f"param vnetResourceGroupName = {quote(vnet_resource_group_name)}",
    f"param redisName = {quote(redis_name)}",
    f"param publicNetworkAccess = {quote(config.get('publicNetworkAccess', 'Disabled'))}",
    f"param minimumTlsVersion = {quote(config.get('minimumTlsVersion', '1.2'))}",
    f"param enableNonSslPort = {'true' if bool(config.get('enableNonSslPort', False)) else 'false'}",
    f"param skuName = {quote(sku_name)}",
    f"param skuFamily = {quote(sku_family)}",
    f"param skuCapacity = {int(redis_values.get('capacity', 0))}",
    f"param shardCount = {int(redis_values.get('shardCount', 1))}",
    f"param zonalAllocationPolicy = {quote(redis_values.get('zonalAllocationPolicy', 'Automatic'))}",
    f"param zones = {json.dumps(redis_values.get('zones', []), ensure_ascii=False)}",
    f"param replicasPerMaster = {int(redis_values.get('replicasPerMaster', 1))}",
    f"param enableGeoReplication = {'true' if bool(redis_values.get('enableGeoReplication', False)) else 'false'}",
    "param enableMicrosoftEntraAuthentication = "
    f"{'true' if bool(redis_values.get('enableMicrosoftEntraAuthentication', True)) else 'false'}",
    "param disableAccessKeyAuthentication = "
    f"{'true' if bool(redis_values.get('disableAccessKeyAuthentication', False)) else 'false'}",
    "param enableCustomMaintenanceWindow = "
    f"{'true' if bool(redis_values.get('enableCustomMaintenanceWindow', False)) else 'false'}",
    f"param maintenanceWindowDayOfWeek = {int(redis_values.get('maintenanceWindow', {}).get('dayOfWeek', 0))}",
    f"param maintenanceWindowStartHour = {int(redis_values.get('maintenanceWindow', {}).get('startHour', 3))}",
    f"param maintenanceWindowDuration = {quote(redis_values.get('maintenanceWindow', {}).get('duration', 'PT5H'))}",
    f"param enableRdbBackup = {'true' if bool(redis_values.get('enableRdbBackup', False)) else 'false'}",
    f"param rdbBackupFrequencyInMinutes = {int(redis_values.get('rdbBackupFrequencyInMinutes', 60))}",
    f"param rdbBackupMaxSnapshotCount = {int(redis_values.get('rdbBackupMaxSnapshotCount', 1))}",
    f"param rdbStorageConnectionString = {quote(redis_values.get('rdbStorageConnectionString', ''))}",
    f"param privateEndpointName = {quote(private_endpoint_name)}",
    f"param privateDnsZoneName = {quote(config.get('privateDnsZoneName', 'privatelink.redis.cache.windows.net'))}",
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
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
