#!/usr/bin/env python3
"""ACR 用 bicepparam を生成する。"""

import json
import os
import re
from pathlib import Path


def quote(value: str) -> str:
    """Bicep 文字列リテラル向けに single quote をエスケープする。"""
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def to_bicep_string_array(values: list[str]) -> str:
    """文字列配列を Bicep の配列表現へ変換する。"""
    if not values:
        return "[]"
    items = "\n".join(f"  {quote(v)}" for v in values)
    return "[\n" + items + "\n]"


def normalize_registry_suffix(value: str) -> str:
    """ACR 名に利用可能な文字へ正規化する（英小文字/数字のみ）。"""
    return re.sub(r"[^a-z0-9]", "", value.lower())


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

registry_name = f"cr{normalize_registry_suffix(environment_name)}{normalize_registry_suffix(system_name)}"
if len(registry_name) < 5 or len(registry_name) > 50:
    raise SystemExit(
        "ACR 名が長さ制約(5〜50文字)を満たしません。"
        "common.environmentName / common.systemName を調整してください。"
    )

private_endpoint_name = f"pep-cr-{environment_name}-{system_name}"
private_dns_zone_group_name = f"dnszg-cr-{environment_name}-{system_name}"
private_dns_vnet_link_name = f"link-acr-to-vnet-{environment_name}-{system_name}"
vnet_name = f"vnet-{environment_name}-{system_name}"

log_analytics_name = f"log-{environment_name}-{system_name}"
log_analytics_resource_group_name = f"rg-{environment_name}-{system_name}-monitor"

network_rule_ip_rules = config.get("networkRuleIpRules", [])
if not isinstance(network_rule_ip_rules, list):
    raise SystemExit("acr config の networkRuleIpRules は配列で指定してください。")

enable_centralized_private_dns = bool(network_values.get("enableCentralizedPrivateDns", False))
deploy = bool(common.get("resourceToggles", {}).get("acr", True))

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "acr.bicepparam"

lines = [
    "using '../bicep/main.acr.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param logAnalyticsName = {quote(log_analytics_name)}",
    f"param logAnalyticsResourceGroupName = {quote(log_analytics_resource_group_name)}",
    f"param vnetName = {quote(vnet_name)}",
    f"param vnetResourceGroupName = {quote(vnet_resource_group_name)}",
    f"param containerRegistryName = {quote(registry_name)}",
    f"param privateEndpointName = {quote(private_endpoint_name)}",
    f"param privateDnsZoneName = {quote(config.get('privateDnsZoneName', 'privatelink.azurecr.io'))}",
    f"param privateDnsZoneGroupName = {quote(private_dns_zone_group_name)}",
    f"param privateDnsVnetLinkName = {quote(private_dns_vnet_link_name)}",
    f"param acrSkuName = {quote(config.get('acrSkuName', 'Premium'))}",
    f"param publicNetworkAccess = {quote(config.get('publicNetworkAccess', 'Disabled'))}",
    f"param networkRuleBypassOptions = {quote(config.get('networkRuleBypassOptions', 'AzureServices'))}",
    f"param networkRuleDefaultAction = {quote(config.get('networkRuleDefaultAction', 'Allow'))}",
    f"param networkRuleIpRules = {to_bicep_string_array(network_rule_ip_rules)}",
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
