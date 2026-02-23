#!/usr/bin/env python3
"""Maintenance VM 用 bicepparam を生成する。

このスクリプトはメンテナンス VM の配置先サブネットを特定し、
VM/NIC/OS Disk 作成に必要なパラメータを .bicepparam として出力する。
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
    """Bicep オブジェクトキーの表現を返す。"""
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
config_path = Path(os.environ["RESOURCE_CONFIG_FILE"])
subnets_config_path = Path(os.environ["SUBNETS_CONFIG_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

# 設定を読み込む。
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

if network_values.get("sharedBastionIp", ""):
    subnet_defs = [s for s in subnet_defs if s.get("alias", s.get("name")) != "bastion"]

base_prefixes = [ipaddress.ip_network(p) for p in vnet_address_prefixes]
range_index = 0
current = int(base_prefixes[0].network_address)
maint_subnet_name = ""

# サブネット割り当てを再計算し、MaintenanceSubnet を探索する。
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

    alias = subnet.get("alias", subnet["name"])
    if alias == "maint" or subnet["name"] == "MaintenanceSubnet":
        maint_subnet_name = subnet["name"]

if not maint_subnet_name:
    raise SystemExit("MaintenanceSubnet が見つかりませんでした")

modules_name = config.get("modulesName", "maint")
network_modules_name = config.get("networkModulesName", "nw")
enable_resource_lock = bool(common_values.get("enableResourceLock", True))
lock_kind = config.get("lockKind", "CanNotDelete") if enable_resource_lock else ""

service_rg_name = f"rg-{environment_name}-{system_name}-{modules_name}"
nw_rg_name = f"rg-{environment_name}-{system_name}-{network_modules_name}"
vnet_name = f"vnet-{environment_name}-{system_name}"
log_analytics_name = f"log-{environment_name}-{system_name}"
log_analytics_resource_group_name = f"rg-{environment_name}-{system_name}-monitor"

deploy = bool(common.get("resourceToggles", {}).get("maintenanceVm", True))

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "maintenance-vm.bicepparam"

# main.maintenance-vm.bicep へ渡すパラメータを出力する。
lines = [
    "using '../bicep/main.maintenance-vm.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param nwResourceGroup = {quote(nw_rg_name)}",
    f"param vnetName = {quote(vnet_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param logAnalyticsName = {quote(log_analytics_name)}",
    f"param logAnalyticsResourceGroupName = {quote(log_analytics_resource_group_name)}",
    f"param maintVmName = {quote(f'vm-{environment_name}-{system_name}-maint')}",
    f"param maintNicName = {quote(f'nic-vm-{environment_name}-{system_name}-maint')}",
    f"param maintSubnetName = {quote(maint_subnet_name)}",
    f"param maintVmSize = {quote(config.get('maintVmSize', 'Standard_D4as_v5'))}",
    f"param maintVmAdminUsername = {quote(config.get('maintVmAdminUsername', 'adminUser'))}",
    "param maintVmAdminPassword = ''",
    f"param maintVmImageReference = {to_bicep(config.get('maintVmImageReference', {}))}",
    f"param maintVmOsDisk = {to_bicep(config.get('maintVmOsDisk', {}))}",
    f"param maintBootDiagnosticsEnabled = {'true' if bool(config.get('maintBootDiagnosticsEnabled', True)) else 'false'}",
    f"param maintSecurityType = {quote(config.get('maintSecurityType', 'TrustedLaunch'))}",
    f"param maintSecureBootEnabled = {'true' if bool(config.get('maintSecureBootEnabled', True)) else 'false'}",
    f"param maintVTpmEnabled = {'true' if bool(config.get('maintVTpmEnabled', True)) else 'false'}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

# 後続処理向けメタ情報。
meta = {
    "resourceGroupName": service_rg_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
    "maintSubnetName": maint_subnet_name,
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
