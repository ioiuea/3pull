#!/usr/bin/env python3
"""Route Table 用 bicepparam を生成する。

設計意図:
- agic(=ApplicationGatewaySubnet) 用 inbound ルートを作る。
- AKS 用と Maintenance 用で outbound ルートテーブルを分離する。
- Firewall 実 IP をメタファイルから受け取り、next hop として埋め込む。
- BGP ルート伝搬は common parameter で有効/無効を切り替える。
"""

import ipaddress
import json
import os
import re
from pathlib import Path


def quote(value: str) -> str:
    """Bicep 文字列リテラル向けに single quote をエスケープする。"""
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def key_literal(key: str) -> str:
    """Bicep オブジェクトのキーを文字列化する。"""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        return key
    return quote(key)


def to_bicep(value, indent: int = 0) -> str:
    """Python の値を Bicep リテラルへ変換する。"""
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
config_path = Path(os.environ["RESOURCE_CONFIG_FILE"])
subnets_config_path = Path(os.environ["SUBNETS_CONFIG_FILE"])
firewall_meta_path = Path(os.environ["FIREWALL_META_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

# 入力設定を読み込む。
common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))
subnets_config = json.loads(subnets_config_path.read_text(encoding="utf-8"))
firewall_meta = json.loads(firewall_meta_path.read_text(encoding="utf-8"))

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
subnet_prefix_map = {}

# Subnet 割り当てロジックを再現し、alias -> CIDR の対応表を作る。
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

    subnet_name = subnet["name"]
    subnet_alias = subnet.get("alias", subnet_name)
    subnet_prefix_map[subnet_name] = str(allocated)
    subnet_prefix_map[subnet_alias] = str(allocated)

known_aliases = {s.get("alias", s.get("name", "")) for s in subnet_defs}

# 既存または直前作成された Firewall の実 IP を参照する。
firewall_private_ip = firewall_meta.get("firewallPrivateIp", "")
if not firewall_private_ip:
    raise SystemExit("firewall-meta.json に firewallPrivateIp がありません")

try:
    ipaddress.ip_address(firewall_private_ip)
except ValueError as exc:
    raise SystemExit("firewallPrivateIp が不正な IP です") from exc

agic_alias = "agic"
if agic_alias not in known_aliases:
    raise SystemExit("ApplicationGatewaySubnet(agic) が定義されていません")
agic_prefix = subnet_prefix_map.get(agic_alias, "")
if not agic_prefix:
    raise SystemExit("ApplicationGatewaySubnet(agic) のプレフィックスが見つかりません")

# egressNextHopIp が未指定なら、この環境の Firewall を既定 next hop とする。
next_hop_ip = network_values.get("egressNextHopIp", "") or firewall_private_ip
try:
    ipaddress.ip_address(next_hop_ip)
except ValueError as exc:
    raise SystemExit("egressNextHopIp が不正な IP です") from exc

# true: 伝搬有効、false: 伝搬無効（推奨）
enable_gateway_route_propagation = bool(network_values.get("enableGatewayRoutePropagation", False))
disable_bgp_route_propagation = not enable_gateway_route_propagation

outbound_aks_targets = config.get("outboundAksSubnetAliases", ["agentnode", "usernode"])
outbound_maint_targets = config.get("outboundMaintSubnetAliases", ["maint"])
outbound_aks_subnet_aliases = [alias for alias in outbound_aks_targets if alias in known_aliases]
outbound_maint_subnet_aliases = [alias for alias in outbound_maint_targets if alias in known_aliases]
inbound_target_aliases = [alias for alias in config.get("inboundTargetSubnetAliases", ["usernode", "agentnode"]) if alias in known_aliases]
if not inbound_target_aliases:
    raise SystemExit("inboundTargetSubnetAliases に有効なサブネット alias がありません")

# Application Gateway から各 AKS ノードサブネットへ向かう経路を定義する。
inbound_routes = []
for alias in inbound_target_aliases:
    address_prefix = subnet_prefix_map.get(alias, "")
    if not address_prefix:
        raise SystemExit(f"inbound ルート宛先サブネットのプレフィックスが見つかりません: {alias}")

    route_name = f"udr-{alias}-inbound"
    inbound_routes.append(
        {
            "name": route_name,
            "properties": {
                "addressPrefix": address_prefix,
                "nextHopType": "VirtualAppliance",
                "nextHopIpAddress": firewall_private_ip,
            },
        }
    )

# 設計に沿った 3 種類のルートテーブルを定義する。
route_tables = [
    {
        "name": "firewall",
        "disableBgpRoutePropagation": disable_bgp_route_propagation,
        "routes": inbound_routes,
        "subnetNames": [agic_alias],
    },
    {
        "name": "outbound-aks",
        "disableBgpRoutePropagation": disable_bgp_route_propagation,
        "routes": [
            {
                "name": config.get("appGatewayReturnRouteName", "udr-appgw-return"),
                "properties": {
                    "addressPrefix": agic_prefix,
                    "nextHopType": "VirtualAppliance",
                    "nextHopIpAddress": firewall_private_ip,
                },
            },
            {
                "name": config.get("outboundRouteName", "udr-internet-outbound"),
                "properties": {
                    "addressPrefix": config.get("outboundAddressPrefix", "0.0.0.0/0"),
                    "nextHopType": "VirtualAppliance",
                    "nextHopIpAddress": next_hop_ip,
                },
            }
        ],
        "subnetNames": outbound_aks_subnet_aliases,
    },
    {
        "name": "outbound-maint",
        "disableBgpRoutePropagation": disable_bgp_route_propagation,
        "routes": [
            {
                "name": config.get("outboundRouteName", "udr-internet-outbound"),
                "properties": {
                    "addressPrefix": config.get("outboundAddressPrefix", "0.0.0.0/0"),
                    "nextHopType": "VirtualAppliance",
                    "nextHopIpAddress": next_hop_ip,
                },
            }
        ],
        "subnetNames": outbound_maint_subnet_aliases,
    },
]

modules_name = config.get("modulesName", "nw")
enable_resource_lock = bool(common_values.get("enableResourceLock", True))
lock_kind = config.get("lockKind", "CanNotDelete") if enable_resource_lock else ""
network_rg_name = f"rg-{environment_name}-{system_name}-{modules_name}"
# subnets トグルに連動して route table の作成可否を決める。
deploy = bool(common.get("resourceToggles", {}).get("subnets", True))

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "route-tables.bicepparam"

# main.route-tables.bicep へ渡す .bicepparam を生成する。
lines = [
    "using '../bicep/main.route-tables.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param routeTables = {to_bicep(route_tables)}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

# 後続工程向けメタ情報。
meta = {
    "resourceGroupName": network_rg_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
