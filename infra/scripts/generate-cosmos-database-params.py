#!/usr/bin/env python3
"""Cosmos DB（NoSQL API）用 bicepparam を生成する。"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path


def quote(value: str) -> str:
    """Bicep 文字列リテラル向けに single quote をエスケープする。"""
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def normalize_cosmos_account_name(environment_name: str, system_name: str) -> str:
    """Cosmos DB account 名の制約に合わせて正規化する。"""
    env = re.sub(r"[^a-z0-9-]", "-", environment_name.lower())
    system = re.sub(r"[^a-z0-9-]", "-", system_name.lower())
    name = re.sub(r"-{2,}", "-", f"cosno-{env}-{system}").strip("-")

    if len(name) < 3 or len(name) > 44:
        raise SystemExit(
            "Cosmos DB account 名が長さ制約(3〜44文字)を満たしません。"
            "common.environmentName / common.systemName を調整してください。"
        )

    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", name):
        raise SystemExit("Cosmos DB account 名が命名制約を満たしません。")

    return name


common_path = Path(os.environ["COMMON_FILE"])
config_path = Path(os.environ["RESOURCE_CONFIG_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))

common_values = common.get("common", {})
network_values = common.get("network", {})
cosno_values = common.get("cosno", {})

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

cosmos_account_name = normalize_cosmos_account_name(environment_name, system_name)
# SQL Database 名は systemName をそのまま利用する。
sql_database_name = system_name

private_endpoint_name = f"pep-cosno-{environment_name}-{system_name}"
private_dns_zone_group_name = f"dnszg-cosno-{environment_name}-{system_name}"
private_dns_vnet_link_name = f"link-cosno-to-vnet-{environment_name}-{system_name}"

log_analytics_name = f"log-{environment_name}-{system_name}"
log_analytics_resource_group_name = f"rg-{environment_name}-{system_name}-monitor"

enable_centralized_private_dns = bool(network_values.get("enableCentralizedPrivateDns", False))

toggles = common.get("resourceToggles", {})
deploy = bool(toggles.get("cosmosDatabase", True))

failover_regions = cosno_values.get("failoverRegions", [])
if not isinstance(failover_regions, list):
    raise SystemExit("common.parameter.json の cosno.failoverRegions は配列で指定してください")

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "cosmos-database.bicepparam"

lines = [
    "using '../bicep/main.cosmos-database.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param logAnalyticsName = {quote(log_analytics_name)}",
    f"param logAnalyticsResourceGroupName = {quote(log_analytics_resource_group_name)}",
    f"param vnetName = {quote(vnet_name)}",
    f"param vnetResourceGroupName = {quote(vnet_resource_group_name)}",
    f"param cosmosAccountName = {quote(cosmos_account_name)}",
    f"param sqlDatabaseName = {quote(sql_database_name)}",
    f"param publicNetworkAccess = {quote(config.get('publicNetworkAccess', 'Disabled'))}",
    f"param throughputMode = {quote(cosno_values.get('throughputMode', 'Serverless'))}",
    f"param manualThroughputRu = {int(cosno_values.get('manualThroughputRu', 400))}",
    f"param autoscaleMaxThroughputRu = {int(cosno_values.get('autoscaleMaxThroughputRu', 1000))}",
    f"param backupPolicyType = {quote(cosno_values.get('backupPolicyType', 'Periodic'))}",
    "param periodicBackupIntervalInMinutes = "
    f"{int(cosno_values.get('periodicBackupIntervalInMinutes', 240))}",
    "param periodicBackupRetentionIntervalInHours = "
    f"{int(cosno_values.get('periodicBackupRetentionIntervalInHours', 8))}",
    "param periodicBackupStorageRedundancy = "
    f"{quote(cosno_values.get('periodicBackupStorageRedundancy', 'Geo'))}",
    f"param continuousBackupTier = {quote(cosno_values.get('continuousBackupTier', 'Continuous30Days'))}",
    f"param failoverRegions = {json.dumps(failover_regions, ensure_ascii=False)}",
    "param enableAutomaticFailover = "
    f"{'true' if bool(cosno_values.get('enableAutomaticFailover', False)) else 'false'}",
    "param enableMultipleWriteLocations = "
    f"{'true' if bool(cosno_values.get('enableMultipleWriteLocations', False)) else 'false'}",
    f"param consistencyLevel = {quote(cosno_values.get('consistencyLevel', 'Session'))}",
    "param disableLocalAuth = "
    f"{'true' if bool(cosno_values.get('disableLocalAuth', False)) else 'false'}",
    "param disableKeyBasedMetadataWriteAccess = "
    f"{'true' if bool(cosno_values.get('disableKeyBasedMetadataWriteAccess', False)) else 'false'}",
    f"param privateEndpointName = {quote(private_endpoint_name)}",
    f"param privateDnsZoneName = {quote(config.get('privateDnsZoneName', 'privatelink.documents.azure.com'))}",
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
