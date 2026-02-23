#!/usr/bin/env python3
"""Storage Account 用 bicepparam を生成する。"""

import json
import os
import re
from pathlib import Path


def quote(value: str) -> str:
    """Bicep 文字列リテラル向けに single quote をエスケープする。"""
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def normalize_storage_account_name(environment_name: str, system_name: str) -> str:
    """Storage Account 命名制約に合わせて正規化する。"""
    env = re.sub(r"[^a-z0-9]", "", environment_name.lower())
    system = re.sub(r"[^a-z0-9]", "", system_name.lower())
    name = f"st{env}{system}"
    if len(name) < 3 or len(name) > 24:
        raise SystemExit(
            "Storage Account 名が長さ制約(3〜24文字)を満たしません。"
            "common.environmentName / common.systemName を調整してください。"
        )
    return name


def normalize_container_name(system_name: str) -> str:
    """Container 命名制約(小文字/数字/ハイフン)に合わせて正規化する。"""
    name = re.sub(r"[^a-z0-9-]", "-", system_name.lower())
    name = re.sub(r"-{2,}", "-", name).strip("-")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?", name):
        raise SystemExit(
            "Blob コンテナ名が命名制約を満たしません。"
            "common.systemName を調整してください。"
        )
    return name


common_path = Path(os.environ["COMMON_FILE"])
config_path = Path(os.environ["RESOURCE_CONFIG_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))

common_values = common.get("common", {})
network_values = common.get("network", {})

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

storage_account_name = normalize_storage_account_name(environment_name, system_name)
blob_container_name = normalize_container_name(system_name)

private_endpoint_blob_name = f"pep-st-blob-{environment_name}-{system_name}"
private_endpoint_file_name = f"pep-st-file-{environment_name}-{system_name}"
private_endpoint_queue_name = f"pep-st-queue-{environment_name}-{system_name}"
private_endpoint_table_name = f"pep-st-table-{environment_name}-{system_name}"
private_dns_zone_group_blob_name = f"dnszg-st-blob-{environment_name}-{system_name}"
private_dns_zone_group_file_name = f"dnszg-st-file-{environment_name}-{system_name}"
private_dns_zone_group_queue_name = f"dnszg-st-queue-{environment_name}-{system_name}"
private_dns_zone_group_table_name = f"dnszg-st-table-{environment_name}-{system_name}"
private_dns_vnet_link_blob_name = f"link-st-blob-to-vnet-{environment_name}-{system_name}"
private_dns_vnet_link_file_name = f"link-st-file-to-vnet-{environment_name}-{system_name}"
private_dns_vnet_link_queue_name = f"link-st-queue-to-vnet-{environment_name}-{system_name}"
private_dns_vnet_link_table_name = f"link-st-table-to-vnet-{environment_name}-{system_name}"
vnet_name = f"vnet-{environment_name}-{system_name}"

log_analytics_name = f"log-{environment_name}-{system_name}"
log_analytics_resource_group_name = f"rg-{environment_name}-{system_name}-monitor"

enable_centralized_private_dns = bool(network_values.get("enableCentralizedPrivateDns", False))
toggles = common.get("resourceToggles", {})
deploy = bool(toggles.get("storage", True))

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "storage.bicepparam"

lines = [
    "using '../bicep/main.storage.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param logAnalyticsName = {quote(log_analytics_name)}",
    f"param logAnalyticsResourceGroupName = {quote(log_analytics_resource_group_name)}",
    f"param vnetName = {quote(vnet_name)}",
    f"param vnetResourceGroupName = {quote(vnet_resource_group_name)}",
    f"param storageAccountName = {quote(storage_account_name)}",
    f"param blobContainerName = {quote(blob_container_name)}",
    f"param privateEndpointBlobName = {quote(private_endpoint_blob_name)}",
    f"param privateEndpointFileName = {quote(private_endpoint_file_name)}",
    f"param privateEndpointQueueName = {quote(private_endpoint_queue_name)}",
    f"param privateEndpointTableName = {quote(private_endpoint_table_name)}",
    f"param privateDnsZoneBlobName = {quote(config.get('privateDnsZoneBlobName', 'privatelink.blob.core.windows.net'))}",
    f"param privateDnsZoneFileName = {quote(config.get('privateDnsZoneFileName', 'privatelink.file.core.windows.net'))}",
    f"param privateDnsZoneQueueName = {quote(config.get('privateDnsZoneQueueName', 'privatelink.queue.core.windows.net'))}",
    f"param privateDnsZoneTableName = {quote(config.get('privateDnsZoneTableName', 'privatelink.table.core.windows.net'))}",
    f"param privateDnsZoneGroupBlobName = {quote(private_dns_zone_group_blob_name)}",
    f"param privateDnsZoneGroupFileName = {quote(private_dns_zone_group_file_name)}",
    f"param privateDnsZoneGroupQueueName = {quote(private_dns_zone_group_queue_name)}",
    f"param privateDnsZoneGroupTableName = {quote(private_dns_zone_group_table_name)}",
    f"param privateDnsVnetLinkBlobName = {quote(private_dns_vnet_link_blob_name)}",
    f"param privateDnsVnetLinkFileName = {quote(private_dns_vnet_link_file_name)}",
    f"param privateDnsVnetLinkQueueName = {quote(private_dns_vnet_link_queue_name)}",
    f"param privateDnsVnetLinkTableName = {quote(private_dns_vnet_link_table_name)}",
    f"param blobSkuName = {quote(config.get('blobSkuName', 'Standard_LRS'))}",
    f"param blobKind = {quote(config.get('blobKind', 'StorageV2'))}",
    f"param blobAccessTier = {quote(config.get('blobAccessTier', 'Hot'))}",
    f"param publicNetworkAccess = {quote(config.get('publicNetworkAccess', 'Disabled'))}",
    f"param enableBlobSoftDelete = {'true' if bool(config.get('enableBlobSoftDelete', True)) else 'false'}",
    f"param blobDeleteRetentionDays = {int(config.get('blobDeleteRetentionDays', 7))}",
    f"param enableContainerSoftDelete = {'true' if bool(config.get('enableContainerSoftDelete', True)) else 'false'}",
    f"param containerDeleteRetentionDays = {int(config.get('containerDeleteRetentionDays', 7))}",
    f"param enableBlobVersioning = {'true' if bool(config.get('enableBlobVersioning', True)) else 'false'}",
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
