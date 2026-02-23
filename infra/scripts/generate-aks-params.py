#!/usr/bin/env python3
"""AKS 用 bicepparam を生成する。

主な責務:
1. common/config から AKS の可変値と固定値を統合する。
2. serviceCidr から DNS Service IP(10 番目の利用可能 IP)を算出する。
3. AKS 作成用 .bicepparam とメタ情報を出力する。
"""

import ipaddress
import json
import os
from pathlib import Path


def quote(value: str) -> str:
    """Bicep 文字列リテラル向けに single quote をエスケープする。"""
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def to_bicep_array(values: list[str]) -> str:
    """文字列配列を Bicep 配列表現へ変換する。"""
    if not values:
        return "[]"
    lines = ["["]
    for value in values:
        lines.append(f"  {quote(value)}")
    lines.append("]")
    return "\n".join(lines)


# main.sh から受け取る入出力パス。
common_path = Path(os.environ["COMMON_FILE"])
config_path = Path(os.environ["RESOURCE_CONFIG_FILE"])
subnets_config_path = Path(os.environ["SUBNETS_CONFIG_FILE"])
application_gateway_meta_path = Path(os.environ["APPLICATION_GATEWAY_META_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

# 入力設定を読み込む。
common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))
subnets_config = json.loads(subnets_config_path.read_text(encoding="utf-8"))
application_gateway_meta = json.loads(application_gateway_meta_path.read_text(encoding="utf-8"))

common_values = common.get("common", {})
network_values = common.get("network", {})
aks_values = common.get("aks", {})

environment_name = common_values.get("environmentName", "")
system_name = common_values.get("systemName", "")
location = common_values.get("location", "")

if not environment_name or not system_name or not location:
    raise SystemExit(
        "common.parameter.json の common.environmentName / "
        "common.systemName / common.location を設定してください"
    )

vnet_address_prefixes = network_values.get("vnetAddressPrefixes", [])
if not vnet_address_prefixes:
    raise SystemExit("common.parameter.json の network.vnetAddressPrefixes が空です")

service_cidr_raw = aks_values.get("serviceCidr", "")
if not service_cidr_raw:
    raise SystemExit("common.parameter.json の aks.serviceCidr が空です")

# service CIDR の 10 番目の利用可能 IP を DNS Service IP として使う。
service_cidr_network = ipaddress.ip_network(service_cidr_raw, strict=True)
service_hosts = list(service_cidr_network.hosts())
if len(service_hosts) < 10:
    raise SystemExit("serviceCidr does not have enough usable IPs to assign the 10th host")

service_cidr = str(service_cidr_network)
dns_service_ip = str(service_hosts[9])

modules_name = config.get("modulesName", "svc")
enable_resource_lock = bool(common_values.get("enableResourceLock", True))
lock_kind = config.get("lockKind", "CanNotDelete") if enable_resource_lock else ""
aks_rg_name = f"rg-{environment_name}-{system_name}-{modules_name}"
log_analytics_name = f"log-{environment_name}-{system_name}"
log_analytics_resource_group_name = f"rg-{environment_name}-{system_name}-monitor"

vnet_modules_name = subnets_config.get("modulesName", "nw")
vnet_rg_name = f"rg-{environment_name}-{system_name}-{vnet_modules_name}"
vnet_name = f"vnet-{environment_name}-{system_name}"

application_gateway_name = application_gateway_meta.get("applicationGatewayName", f"agw-{environment_name}-{system_name}")
application_gateway_rg_name = application_gateway_meta.get("resourceGroupName", f"rg-{environment_name}-{system_name}-nw")

pod_cidr = aks_values.get("podCidr", "")
if not pod_cidr:
    raise SystemExit("common.parameter.json の aks.podCidr が空です")

user_pool_vm_size = aks_values.get("userPoolVmSize", "")
user_pool_count = int(aks_values.get("userPoolCount", 0))
user_pool_min_count = int(aks_values.get("userPoolMinCount", 0))
user_pool_max_count = int(aks_values.get("userPoolMaxCount", 0))
user_pool_label = aks_values.get("userPoolLabel", "")

if not user_pool_vm_size or not user_pool_label:
    raise SystemExit("common.parameter.json の aks.userPoolVmSize / aks.userPoolLabel を設定してください")
if user_pool_min_count > user_pool_count or user_pool_count > user_pool_max_count:
    raise SystemExit("aks user pool の count / min / max の大小関係が不正です")

aks_name = f"aks-{environment_name}-{system_name}"
dns_prefix_base = config.get("dnsPrefix", "aks-dns")
dns_prefix = f"{dns_prefix_base}-{environment_name}-{system_name}"

# AKS の実行有無トグル。
deploy = bool(common.get("resourceToggles", {}).get("aks", True))

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "aks.bicepparam"

# AKS デプロイ用 .bicepparam を出力する。
lines = [
    "using '../bicep/main.aks.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param logAnalyticsName = {quote(log_analytics_name)}",
    f"param logAnalyticsResourceGroupName = {quote(log_analytics_resource_group_name)}",
    f"param aksName = {quote(aks_name)}",
    f"param dnsPrefix = {quote(dns_prefix)}",
    f"param enableRbac = {'true' if bool(config.get('enableRbac', True)) else 'false'}",
    f"param vnetName = {quote(vnet_name)}",
    f"param vnetResourceGroupName = {quote(vnet_rg_name)}",
    f"param applicationGatewayName = {quote(application_gateway_name)}",
    f"param applicationGatewayResourceGroupName = {quote(application_gateway_rg_name)}",
    f"param agentPoolName = {quote(config.get('agentPoolName', 'agentpool'))}",
    f"param agentPoolVmSize = {quote(config.get('agentPoolVmSize', 'standard_d2s_v4'))}",
    f"param agentPoolOsDiskSizeGB = {int(config.get('agentPoolOsDiskSizeGB', 0))}",
    f"param agentPoolAvailabilityZones = {to_bicep_array(config.get('agentPoolAvailabilityZones', ['1', '2', '3']))}",
    f"param agentPoolOsType = {quote(config.get('agentPoolOsType', 'Linux'))}",
    f"param agentPoolMode = {quote(config.get('agentPoolMode', 'System'))}",
    f"param agentPoolCount = {int(config.get('agentPoolCount', 3))}",
    f"param agentPoolMinCount = {int(config.get('agentPoolMinCount', 3))}",
    f"param agentPoolMaxCount = {int(config.get('agentPoolMaxCount', 6))}",
    f"param agentPoolEnableAutoScaling = {'true' if bool(config.get('agentPoolEnableAutoScaling', True)) else 'false'}",
    f"param userPoolName = {quote(config.get('userPoolName', 'userpool'))}",
    f"param userPoolVmSize = {quote(user_pool_vm_size)}",
    f"param userPoolOsDiskSizeGB = {int(config.get('userPoolOsDiskSizeGB', 0))}",
    f"param userPoolAvailabilityZones = {to_bicep_array(config.get('userPoolAvailabilityZones', ['1', '2', '3']))}",
    f"param userPoolOsType = {quote(config.get('userPoolOsType', 'Linux'))}",
    f"param userPoolMode = {quote(config.get('userPoolMode', 'User'))}",
    f"param userPoolCount = {user_pool_count}",
    f"param userPoolMinCount = {user_pool_min_count}",
    f"param userPoolMaxCount = {user_pool_max_count}",
    f"param userPoolEnableAutoScaling = {'true' if bool(config.get('userPoolEnableAutoScaling', True)) else 'false'}",
    f"param userPoolLabel = {quote(user_pool_label)}",
    f"param networkPlugin = {quote(config.get('networkPlugin', 'azure'))}",
    f"param networkPolicy = {quote(config.get('networkPolicy', 'azure'))}",
    f"param networkPluginMode = {quote(config.get('networkPluginMode', 'overlay'))}",
    f"param loadBalancerSku = {quote(config.get('loadBalancerSku', 'standard'))}",
    f"param podCidr = {quote(pod_cidr)}",
    f"param serviceCidr = {quote(service_cidr)}",
    f"param dnsServiceIP = {quote(dns_service_ip)}",
    f"param autoUpgradeChannel = {quote(config.get('autoUpgradeChannel', 'patch'))}",
    f"param enableAzurePolicyAddon = {'true' if bool(config.get('enableAzurePolicyAddon', True)) else 'false'}",
    f"param enableIngressApplicationGatewayAddon = {'true' if bool(config.get('enableIngressApplicationGatewayAddon', True)) else 'false'}",
    f"param enableAzureRbac = {'true' if bool(config.get('enableAzureRbac', True)) else 'false'}",
    f"param managedAad = {'true' if bool(config.get('managedAad', True)) else 'false'}",
    f"param enablePrivateCluster = {'true' if bool(config.get('enablePrivateCluster', True)) else 'false'}",
    f"param enablePrivateClusterPublicFqdn = {'true' if bool(config.get('enablePrivateClusterPublicFqdn', False)) else 'false'}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

# main.sh が参照するメタ情報。
meta = {
    "resourceGroupName": aks_rg_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
    "aksName": aks_name,
    "serviceCidr": service_cidr,
    "dnsServiceIP": dns_service_ip,
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
