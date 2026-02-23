#!/usr/bin/env python3
"""Subnets 用 bicepparam を生成する。

このスクリプトは subnetDefinitions と vnetAddressPrefixes から
各サブネットの CIDR を順番に算出し、Subnet 作成用パラメータを生成する。
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
    """Bicep オブジェクトのキーをリテラル化する。"""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        return key
    return quote(key)


def to_bicep(value, indent: int = 0) -> str:
    """Python 値を Bicep で使えるリテラル文字列へ変換する。"""
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
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

# 共通パラメータと subnet 固定定義を読み込む。
common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))
subnet_defs = config.get("subnetDefinitions", [])

common_values = common.get("common", {})
network_values = common.get("network", {})

environment_name = common_values.get("environmentName", "")
system_name = common_values.get("systemName", "")
vnet_address_prefixes = network_values.get("vnetAddressPrefixes", [])
shared_bastion_ip = network_values.get("sharedBastionIp", "")

if not environment_name or not system_name:
    raise SystemExit("common.parameter.json の common.environmentName / common.systemName を設定してください")
if not vnet_address_prefixes:
    raise SystemExit("common.parameter.json の network.vnetAddressPrefixes が空です")
if not subnet_defs:
    raise SystemExit("subnets config の subnetDefinitions が空です")

modules_name = config.get("modulesName", "nw")
network_rg_name = f"rg-{environment_name}-{system_name}-{modules_name}"
vnet_name = f"vnet-{environment_name}-{system_name}"

# sharedBastionIp が設定される場合は AzureBastionSubnet を作成しない。
if shared_bastion_ip:
    subnet_defs = [s for s in subnet_defs if s.get("alias", s.get("name")) != "bastion"]

base_prefixes = [ipaddress.ip_network(p) for p in vnet_address_prefixes]
range_index = 0
current = int(base_prefixes[0].network_address)
resolved_subnets = []

# subnetDefinitions を prefixLength 昇順で割り当てる。
# 小さいネットワーク(例: /24)から順に確保することで意図しない断片化を防ぐ。
for subnet in sorted(subnet_defs, key=lambda s: s["prefixLength"]):
    prefix_len = subnet["prefixLength"]
    allocated = None

    # vnetAddressPrefixes を跨いで、収まるレンジを順に探す。
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

    subnet_item = {
        **subnet,
        "alias": subnet.get("alias", subnet.get("name")),
        "addressPrefix": str(allocated),
    }
    if subnet.get("name") == "PrivateEndpointSubnet":
        subnet_item["privateEndpointNetworkPolicies"] = "Enabled"
    resolved_subnets.append(subnet_item)

# subnets トグルで作成可否を制御する。
deploy = bool(common.get("resourceToggles", {}).get("subnets", True))

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "subnets.bicepparam"

# Bicep パラメータを出力する。
lines = [
    "using '../bicep/main.subnets.bicep'",
    f"param vnetName = {quote(vnet_name)}",
    f"param subnets = {to_bicep(resolved_subnets)}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

# 後続工程(main.sh)向けメタ情報。
meta = {
    "resourceGroupName": network_rg_name,
    "vnetName": vnet_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
