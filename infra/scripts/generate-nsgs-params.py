#!/usr/bin/env python3
"""NSG 用 bicepparam を生成する。

主な処理:
1. サブネット CIDR を再計算する。
2. nsgs.json のテンプレートを対象サブネットに展開する。
3. source/destination の alias を実 CIDR に解決して .bicepparam を出力する。
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
    """Bicep オブジェクトのキーを安全に出力する。"""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        return key
    return quote(key)


def to_bicep(value, indent: int = 0) -> str:
    """Python 値を Bicep リテラル文字列へ変換する。"""
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
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

# 入力設定を読み込む。
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
if not subnet_defs:
    raise SystemExit("subnets config の subnetDefinitions が空です")

shared_bastion_ip = network_values.get("sharedBastionIp", "")
if shared_bastion_ip:
    subnet_defs = [s for s in subnet_defs if s.get("alias", s.get("name")) != "bastion"]

base_prefixes = [ipaddress.ip_network(p) for p in vnet_address_prefixes]
range_index = 0
current = int(base_prefixes[0].network_address)
resolved_subnets = []
subnet_prefix_map = {}

# Subnet 生成スクリプトと同じロジックで CIDR を再計算し、alias と対応付ける。
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
    subnet_prefix = str(allocated)

    resolved_subnets.append(
        {
            "name": subnet_name,
            "alias": subnet_alias,
            "addressPrefix": subnet_prefix,
        }
    )
    subnet_prefix_map[subnet_name] = subnet_prefix
    subnet_prefix_map[subnet_alias] = subnet_prefix

subnet_aliases = {s.get("alias", s.get("name", "")) for s in subnet_defs}
template_by_subnet = {t.get("targetSubnet", ""): t for t in config.get("templates", [])}


def resolve_prefix(value):
    """alias 指定なら CIDR へ展開し、通常値はそのまま返す。"""
    return subnet_prefix_map.get(value, value)


def resolve_prefixes(values):
    """複数 alias/CIDR をまとめて解決する。"""
    return [resolve_prefix(v) for v in values]


# 各サブネット用テンプレートから NSG ルールを展開する。
nsgs = []
for subnet in resolved_subnets:
    subnet_alias = subnet["alias"]
    if subnet_alias in {"agic", "firewall", "bastion"}:
        continue

    rules = []
    template = template_by_subnet.get(subnet_alias)
    if template:
        for rule in template.get("rules", []):
            direction = rule.get("direction", "Inbound")

            # maintBastion は sharedBastionIp 優先、未指定時は bastion subnet を利用する。
            source_selector = rule.get("sourceSelector", "")
            if source_selector == "maintBastion":
                source = shared_bastion_ip or subnet_prefix_map.get("bastion", "")
                if not source:
                    raise SystemExit(
                        "sourceSelector 'maintBastion' requires sharedBastionIp or AzureBastionSubnet"
                    )
            else:
                source = rule.get("source", "*")

            destination = rule.get("destination", "*")
            if direction == "Inbound" and "destination" not in rule:
                destination = subnet_alias
            if direction == "Outbound" and "source" not in rule:
                source = subnet_alias

            source_is_list = isinstance(source, list)
            destination_is_list = isinstance(destination, list)

            rules.append(
                {
                    "name": rule.get("name", ""),
                    "properties": {
                        **(
                            {"sourceAddressPrefixes": resolve_prefixes(source)}
                            if source_is_list
                            else {"sourceAddressPrefix": resolve_prefix(source)}
                        ),
                        "sourcePortRange": rule.get("sourcePortRange", "*"),
                        **(
                            {"destinationAddressPrefixes": resolve_prefixes(destination)}
                            if destination_is_list
                            else {"destinationAddressPrefix": resolve_prefix(destination)}
                        ),
                        **(
                            {"destinationPortRanges": rule.get("destinationPortRanges")}
                            if "destinationPortRanges" in rule
                            else {"destinationPortRange": rule.get("destinationPortRange", "*")}
                        ),
                        "protocol": rule.get("protocol", "*"),
                        "access": rule.get("access", "Allow"),
                        "priority": rule.get("priority", 100),
                        "direction": direction,
                    },
                }
            )

    nsgs.append(
        {
            "subnetName": subnet_alias,
            "securityRules": rules,
        }
    )

modules_name = config.get("modulesName", "nw")
enable_resource_lock = bool(common_values.get("enableResourceLock", True))
lock_kind = config.get("lockKind", "CanNotDelete") if enable_resource_lock else ""
network_rg_name = f"rg-{environment_name}-{system_name}-{modules_name}"

log_analytics_name = f"log-{environment_name}-{system_name}"
log_analytics_rg_name = f"rg-{environment_name}-{system_name}-monitor"

# subnets トグルに連動して NSG 作成の可否を決める。
deploy = bool(common.get("resourceToggles", {}).get("subnets", True))

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "nsgs.bicepparam"

# main.nsgs.bicep に渡すパラメータを出力する。
lines = [
    "using '../bicep/main.nsgs.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param logAnalyticsName = {quote(log_analytics_name)}",
    f"param logAnalyticsResourceGroupName = {quote(log_analytics_rg_name)}",
    f"param nsgs = {to_bicep(nsgs)}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

# 後続処理向けメタ情報。
meta = {
    "resourceGroupName": network_rg_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
