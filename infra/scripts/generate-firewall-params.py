#!/usr/bin/env python3
"""Firewall 用 bicepparam を生成する。

主な責務:
1. サブネット定義から AzureFirewallSubnet の CIDR を再計算する。
2. Firewall 用パラメータと AKS 送信元レンジを組み立てる。
3. .bicepparam と firewall-meta.json を出力する。
"""

import ipaddress
import json
import os
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


# main.sh から受け取る入力/出力パス。
common_path = Path(os.environ["COMMON_FILE"])
config_path = Path(os.environ["RESOURCE_CONFIG_FILE"])
subnets_config_path = Path(os.environ["SUBNETS_CONFIG_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

# 設定を読み込む。common は可変値、config は固定定義。
common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))
subnets_config = json.loads(subnets_config_path.read_text(encoding="utf-8"))

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

vnet_address_prefixes = network_values.get("vnetAddressPrefixes", [])
if not vnet_address_prefixes:
    raise SystemExit("common.parameter.json の network.vnetAddressPrefixes が空です")

subnet_defs = subnets_config.get("subnetDefinitions", [])
if network_values.get("sharedBastionIp", ""):
    subnet_defs = [s for s in subnet_defs if s.get("alias", s.get("name")) != "bastion"]

base_prefixes = [ipaddress.ip_network(p) for p in vnet_address_prefixes]
range_index = 0
current = int(base_prefixes[0].network_address)
firewall_subnet = None
subnet_prefix_map = {}

# VNET 内でのサブネット割り当てを再現し、Firewall のサブネットを特定する。
for subnet in sorted(subnet_defs, key=lambda s: s["prefixLength"]):
    prefix_len = subnet["prefixLength"]
    allocated = None

    # 現在位置から、対象 prefixLength が収まるブロックを探索する。
    while range_index < len(base_prefixes):
        rng = base_prefixes[range_index]
        block = 1 << (32 - prefix_len)

        if current % block != 0:
            current = ((current // block) + 1) * block

        net = ipaddress.ip_network((current, prefix_len))
        if net.subnet_of(rng):
            allocated = net
            current = int(net.broadcast_address) + 1
            break

        range_index += 1
        if range_index < len(base_prefixes):
            current = int(base_prefixes[range_index].network_address)

    if allocated is None:
        raise SystemExit(f"subnet '{subnet['name']}' does not fit in vnetAddressPrefixes")

    subnet_name = subnet["name"]
    subnet_alias = subnet.get("alias", subnet_name)
    subnet_prefix_map[subnet_name] = str(allocated)
    subnet_prefix_map[subnet_alias] = str(allocated)

    if subnet.get("name") == "AzureFirewallSubnet":
        firewall_subnet = allocated

if firewall_subnet is None:
    raise SystemExit("AzureFirewallSubnet is not defined")

# Azure Firewall のプライベート IP は subnet の最初の利用可能 IP を利用する。
hosts = list(firewall_subnet.hosts())
if not hosts:
    raise SystemExit("No usable IPs in AzureFirewallSubnet")
firewall_private_ip = str(hosts[0])

modules_name = config.get("modulesName", "nw")
enable_resource_lock = bool(common_values.get("enableResourceLock", True))
lock_kind = config.get("lockKind", "CanNotDelete") if enable_resource_lock else ""
network_rg_name = f"rg-{environment_name}-{system_name}-{modules_name}"
vnet_name = f"vnet-{environment_name}-{system_name}"

log_analytics_name = f"log-{environment_name}-{system_name}"
log_analytics_rg_name = f"rg-{environment_name}-{system_name}-monitor"

enable_firewall_idps = bool(network_values.get("enableFirewallIdps", False))
enable_ddos_protection = bool(network_values.get("enableDdosProtection", True))
egress_next_hop_ip = network_values.get("egressNextHopIp", "")
deploy = bool(common.get("resourceToggles", {}).get("firewall", True))

# Firewall ポリシーで AKS 由来通信を扱うための送信元レンジ。
aks_egress_source_prefixes = []
for alias in ("agentnode", "usernode"):
    prefix = subnet_prefix_map.get(alias, "")
    if prefix:
        aks_egress_source_prefixes.append(prefix)

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "firewall.bicepparam"

# Bicep へ渡すパラメータファイルを組み立てる。
lines = [
    "using '../bicep/main.firewall.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param logAnalyticsName = {quote(log_analytics_name)}",
    f"param logAnalyticsResourceGroupName = {quote(log_analytics_rg_name)}",
    f"param vnetName = {quote(vnet_name)}",
    f"param enableFirewallIdps = {'true' if enable_firewall_idps else 'false'}",
    f"param egressNextHopIp = {quote(egress_next_hop_ip)}",
    f"param aksEgressSourceAddressPrefixes = {to_bicep_string_array(aks_egress_source_prefixes)}",
    f"param publicIPName = {quote(f'pip-afw-{environment_name}-{system_name}')}",
    f"param firewallPolicyName = {quote(f'afwp-{environment_name}-{system_name}')}",
    f"param firewallName = {quote(f'afw-{environment_name}-{system_name}')}",
    f"param ipConfigurationName = {quote(f'ipconf-afw-{environment_name}-{system_name}')}",
    f"param publicIPSku = {quote(config.get('publicIPSku', 'Standard'))}",
    f"param publicIPAllocationMethod = {quote(config.get('publicIPAllocationMethod', 'Static'))}",
    f"param publicIPAddressVersion = {quote(config.get('publicIPAddressVersion', 'IPv4'))}",
    f"param protectionMode = {quote('Enabled' if enable_ddos_protection else 'Disabled')}",
    f"param threatIntelMode = {quote(config.get('threatIntelMode', 'Deny'))}",
    f"param intrusionDetectionMode = {quote(config.get('intrusionDetectionMode', 'Alert'))}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

# 後続スクリプトが next hop を解決できるよう、Firewall IP をメタへ保存する。
meta = {
    "resourceGroupName": network_rg_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
    "firewallPrivateIp": firewall_private_ip,
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
