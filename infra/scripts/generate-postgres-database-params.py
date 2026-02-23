#!/usr/bin/env python3
"""PostgreSQL Flexible Server 用 bicepparam を生成する。

このスクリプトは、common.parameter.json と固定設定(config)を読み込み、
以下を行う。
1. PostgreSQL サーバー/PEP/DNS 名を命名規則に従って組み立てる。
2. 共通パラメータ(postgres, network)を Bicep 入力形式へ変換する。
3. params/postgres-database.bicepparam と meta.json を出力する。
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def quote(value: str) -> str:
    """Bicep 文字列リテラル向けに single quote をエスケープする。"""
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


# main.sh から渡される入出力パス。
common_path = Path(os.environ["COMMON_FILE"])
config_path = Path(os.environ["RESOURCE_CONFIG_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

# 入力を読み込む。
common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))

common_values = common.get("common", {})
network_values = common.get("network", {})
postgres_values = common.get("postgres", {})

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

postgres_server_name = f"psql-{environment_name}-{system_name}"
private_endpoint_name = f"pep-psql-{environment_name}-{system_name}"
private_dns_zone_group_name = f"dnszg-psql-{environment_name}-{system_name}"
private_dns_vnet_link_name = f"link-psql-to-vnet-{environment_name}-{system_name}"

log_analytics_name = f"log-{environment_name}-{system_name}"
log_analytics_resource_group_name = f"rg-{environment_name}-{system_name}-monitor"

enable_centralized_private_dns = bool(network_values.get("enableCentralizedPrivateDns", False))

toggles = common.get("resourceToggles", {})
deploy = bool(toggles.get("postgresDatabase", True))

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "postgres-database.bicepparam"

# .bicepparam の中で secure param を空で宣言し、main.sh 側で上書き投入する。
lines = [
    "using '../bicep/main.postgres-database.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param logAnalyticsName = {quote(log_analytics_name)}",
    f"param logAnalyticsResourceGroupName = {quote(log_analytics_resource_group_name)}",
    f"param vnetName = {quote(vnet_name)}",
    f"param vnetResourceGroupName = {quote(vnet_resource_group_name)}",
    f"param postgresServerName = {quote(postgres_server_name)}",
    f"param postgresVersion = {quote(config.get('postgresVersion', '16'))}",
    f"param administratorLogin = {quote(config.get('administratorLogin', 'pgadmin'))}",
    "param administratorPassword = ''",
    f"param publicNetworkAccess = {quote(config.get('publicNetworkAccess', 'Disabled'))}",
    f"param skuTier = {quote(postgres_values.get('skuTier', 'Burstable'))}",
    f"param skuName = {quote(postgres_values.get('skuName', 'Standard_B2s'))}",
    f"param storageSizeGB = {int(postgres_values.get('storageSizeGB', 32))}",
    f"param enableStorageAutoGrow = {'true' if bool(postgres_values.get('enableStorageAutoGrow', False)) else 'false'}",
    f"param backupRetentionDays = {int(postgres_values.get('backupRetentionDays', 7))}",
    f"param enableGeoRedundantBackup = {'true' if bool(postgres_values.get('enableGeoRedundantBackup', False)) else 'false'}",
    f"param enableZoneRedundantHa = {'true' if bool(postgres_values.get('enableZoneRedundantHa', False)) else 'false'}",
    f"param standbyAvailabilityZone = {quote(config.get('standbyAvailabilityZone', ''))}",
    f"param enableCustomMaintenanceWindow = {'true' if bool(postgres_values.get('enableCustomMaintenanceWindow', False)) else 'false'}",
    f"param maintenanceWindowDayOfWeek = {int(postgres_values.get('maintenanceWindow', {}).get('dayOfWeek', 0))}",
    f"param maintenanceWindowStartHour = {int(postgres_values.get('maintenanceWindow', {}).get('startHour', 3))}",
    f"param maintenanceWindowStartMinute = {int(postgres_values.get('maintenanceWindow', {}).get('startMinute', 0))}",
    f"param privateEndpointName = {quote(private_endpoint_name)}",
    f"param privateDnsZoneName = {quote(config.get('privateDnsZoneName', 'privatelink.postgres.database.azure.com'))}",
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
