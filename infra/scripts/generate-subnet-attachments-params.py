#!/usr/bin/env python3
"""Subnet 紐づけ更新用 bicepparam を生成する。

このスクリプトは以下を一括で決定する:
- 各サブネットに紐づける Route Table 名
- 各サブネットに紐づける NSG 名
- 更新対象から除外するサブネット
"""

import ipaddress
import json
import os
import re
from pathlib import Path


def quote(value: str) -> str:
    """Bicep 文字列リテラル向けに値をクオートする。"""
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def key_literal(key: str) -> str:
    """Bicep オブジェクトのキー表現を返す。"""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        return key
    return quote(key)


def to_bicep(value, indent: int = 0) -> str:
    """Python 値を Bicep リテラルへ変換する。"""
    pad = " " * indent
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return quote(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        items = [f"{' ' * (indent + 2)}{to_bicep(v, indent + 2)}" for v in value]
        return "[\n" + "\n".join(items) + f"\n{pad}]"
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = [f"{' ' * (indent + 2)}{key_literal(k)}: {to_bicep(v, indent + 2)}" for k, v in value.items()]
        return "{\n" + "\n".join(items) + f"\n{pad}}}"
    raise TypeError(f"Unsupported type: {type(value)}")


# main.sh から受け取る入出力パス。
common_path = Path(os.environ["COMMON_FILE"])
subnets_config_path = Path(os.environ["SUBNETS_CONFIG_FILE"])
route_tables_config_path = Path(os.environ["ROUTE_TABLES_CONFIG_FILE"])
nsgs_config_path = Path(os.environ["NSGS_CONFIG_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

# 入力設定を読み込む。
common = json.loads(common_path.read_text(encoding="utf-8"))
subnets_config = json.loads(subnets_config_path.read_text(encoding="utf-8"))
route_tables_config = json.loads(route_tables_config_path.read_text(encoding="utf-8"))
nsgs_config = json.loads(nsgs_config_path.read_text(encoding="utf-8"))

common_values = common.get("common", {})
network_values = common.get("network", {})

environment_name = common_values.get("environmentName", "")
system_name = common_values.get("systemName", "")
if not environment_name or not system_name:
    raise SystemExit("common.parameter.json の common.environmentName / common.systemName を設定してください")

vnet_address_prefixes = network_values.get("vnetAddressPrefixes", [])
if not vnet_address_prefixes:
    raise SystemExit("common.parameter.json の network.vnetAddressPrefixes が空です")

subnet_defs = subnets_config.get("subnetDefinitions", [])
if not subnet_defs:
    raise SystemExit("subnets config の subnetDefinitions が空です")

shared_bastion_ip = network_values.get("sharedBastionIp", "")
if shared_bastion_ip:
    subnet_defs = [s for s in subnet_defs if s.get("alias", s.get("name")) != "bastion"]

base_prefixes = [ipaddress.ip_network(p) for p in vnet_address_prefixes]
range_index = 0
current = int(base_prefixes[0].network_address)
resolved_subnets = []

# Subnet 生成時と同じルールで CIDR を再計算し、更新対象情報を組み立てる。
for subnet in sorted(subnet_defs, key=lambda s: s["prefixLength"]):
    prefix_len = subnet["prefixLength"]
    allocated = None

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

    resolved_subnets.append(
        {
            "name": subnet["name"],
            "alias": subnet.get("alias", subnet["name"]),
            "addressPrefix": str(allocated),
        }
    )

modules_name = subnets_config.get("modulesName", "nw")
network_rg_name = f"rg-{environment_name}-{system_name}-{modules_name}"
vnet_name = f"vnet-{environment_name}-{system_name}"

# Route Table 紐づけ（firewall は agic、outbound は AKS 用/maint 用で分離）
route_name_by_alias = {"agic": "firewall"}
for alias in route_tables_config.get("outboundAksSubnetAliases", ["agentnode", "usernode"]):
    route_name_by_alias[alias] = "outbound-aks"
for alias in route_tables_config.get("outboundMaintSubnetAliases", ["maint"]):
    route_name_by_alias[alias] = "outbound-maint"

# NSG 紐づけ対象（nsg 生成スクリプトと同じ除外条件）
nsg_skip_aliases = {"agic", "firewall", "bastion"}
nsg_aliases = []
for subnet in resolved_subnets:
    alias = subnet["alias"]
    if alias in nsg_skip_aliases:
        continue
    nsg_aliases.append(alias)

subnets_for_update = []
skip_subnet_names = {"AzureFirewallSubnet"}
for subnet in resolved_subnets:
    if subnet["name"] in skip_subnet_names:
        continue

    alias = subnet["alias"]
    # alias に対応する route table / nsg 名を命名規則で確定する。
    route_suffix = route_name_by_alias.get(alias, "")
    route_table_name = f"rt-{environment_name}-{system_name}-{route_suffix}" if route_suffix else ""
    network_security_group_name = (
        f"nsg-{environment_name}-{system_name}-{alias}" if alias in nsg_aliases else ""
    )

    subnet_item = {
        "name": subnet["name"],
        "alias": alias,
        "addressPrefix": subnet["addressPrefix"],
        "networkSecurityGroupName": network_security_group_name,
        "routeTableName": route_table_name,
    }
    if subnet["name"] == "PrivateEndpointSubnet":
        subnet_item["privateEndpointNetworkPolicies"] = "Enabled"
    subnets_for_update.append(subnet_item)

# subnets トグルに連動して attach 更新の可否を決める。
deploy = bool(common.get("resourceToggles", {}).get("subnets", True))

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "subnet-attachments.bicepparam"

# main.subnet-attachments.bicep 用パラメータを出力する。
lines = [
    "using '../bicep/main.subnet-attachments.bicep'",
    f"param vnetName = {quote(vnet_name)}",
    f"param subnets = {to_bicep(subnets_for_update)}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

# main.sh が参照するメタ情報を保存する。
meta = {
    "resourceGroupName": network_rg_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
