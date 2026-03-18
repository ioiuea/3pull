#!/usr/bin/env python3
"""Azure SQL Database 用 bicepparam を生成する。"""

from __future__ import annotations

import json
import os
from pathlib import Path


def quote(value: str) -> str:
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


common_path = Path(os.environ["COMMON_FILE"])
config_path = Path(os.environ["RESOURCE_CONFIG_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))

common_values = common.get("common", {})
network_values = common.get("network", {})
sql_database_values = common.get("sqlDatabase", {})

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

sql_server_name = f"sql-{environment_name}-{system_name}"
sql_database_name = f"sqldb-{environment_name}-{system_name}"
private_endpoint_name = f"pep-sql-{environment_name}-{system_name}"
private_dns_zone_group_name = f"dnszg-sql-{environment_name}-{system_name}"
private_dns_vnet_link_name = f"link-sql-to-vnet-{environment_name}-{system_name}"

log_analytics_name = f"log-{environment_name}-{system_name}"
log_analytics_resource_group_name = f"rg-{environment_name}-{system_name}-monitor"

enable_centralized_private_dns = bool(network_values.get("enableCentralizedPrivateDns", False))

toggles = common.get("resourceToggles", {})
deploy = bool(toggles.get("sqlDatabase", True))

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "sql-database.bicepparam"

lines = [
    "using '../bicep/main.sql-database.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param logAnalyticsName = {quote(log_analytics_name)}",
    f"param logAnalyticsResourceGroupName = {quote(log_analytics_resource_group_name)}",
    f"param vnetName = {quote(vnet_name)}",
    f"param vnetResourceGroupName = {quote(vnet_resource_group_name)}",
    f"param sqlServerName = {quote(sql_server_name)}",
    f"param sqlDatabaseName = {quote(sql_database_name)}",
    f"param publicNetworkAccess = {quote(config.get('publicNetworkAccess', 'Disabled'))}",
    f"param minimalTlsVersion = {quote(config.get('minimalTlsVersion', '1.2'))}",
    f"param skuTier = {quote(sql_database_values.get('skuTier', 'Basic'))}",
    f"param skuName = {quote(sql_database_values.get('skuName', 'Basic'))}",
    f"param maxSizeGb = {int(sql_database_values.get('maxSizeGb', 2))}",
    f"param collation = {quote(config.get('collation', 'SQL_Latin1_General_CP1_CI_AS'))}",
    f"param zoneRedundant = {'true' if bool(sql_database_values.get('zoneRedundant', False)) else 'false'}",
    f"param entraAdminLogin = {quote(sql_database_values.get('entraAdminLogin', ''))}",
    f"param entraAdminObjectId = {quote(sql_database_values.get('entraAdminObjectId', ''))}",
    f"param privateEndpointName = {quote(private_endpoint_name)}",
    f"param privateDnsZoneName = {quote(config.get('privateDnsZoneName', 'privatelink.database.windows.net'))}",
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
