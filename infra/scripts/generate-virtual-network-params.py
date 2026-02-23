#!/usr/bin/env python3
"""Virtual Network 用 bicepparam を生成する。

このスクリプトは VNET 作成に必要な値を common/config から集約し、
`main.virtual-network.bicep` へ渡す .bicepparam とメタ情報を作る。
"""

import json
import os
import re
from pathlib import Path


def quote(value: str) -> str:
    """Bicep 文字列リテラルを安全に出力する。"""
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def key_literal(key: str) -> str:
    """Bicep オブジェクトのキー表現を返す。"""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        return key
    return quote(key)


def to_bicep(value, indent: int = 0) -> str:
    """Python の値を Bicep リテラル形式に変換する。"""
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


# main.sh から受け取るファイルパス。
common_path = Path(os.environ["COMMON_FILE"])
config_path = Path(os.environ["RESOURCE_CONFIG_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

# まず JSON を読み込んで入力値を確定する。
common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))

common_values = common.get("common", {})
network_values = common.get("network", {})

environment_name = common_values.get("environmentName", "")
system_name = common_values.get("systemName", "")
location = common_values.get("location", "")
vnet_address_prefixes = network_values.get("vnetAddressPrefixes", [])

if not environment_name or not system_name or not location:
    raise SystemExit(
        "common.parameter.json の common.environmentName / "
        "common.systemName / common.location を設定してください"
    )
if not vnet_address_prefixes:
    raise SystemExit("common.parameter.json の network.vnetAddressPrefixes が空です")

modules_name = config.get("modulesName", "nw")
enable_resource_lock = bool(common_values.get("enableResourceLock", True))
lock_kind = config.get("lockKind", "CanNotDelete") if enable_resource_lock else ""
vnet_dns_servers = network_values.get("vnetDnsServers", [])

network_rg_name = f"rg-{environment_name}-{system_name}-{modules_name}"
vnet_name = f"vnet-{environment_name}-{system_name}"
ddos_plan_name = f"ddos-{environment_name}-{system_name}"

log_analytics_name = f"log-{environment_name}-{system_name}"
log_analytics_rg_name = f"rg-{environment_name}-{system_name}-monitor"

ddos_protection_plan_id = network_values.get("ddosProtectionPlanId", "")
enable_ddos_protection = bool(network_values.get("enableDdosProtection", True))
# virtualNetwork のトグルでデプロイ可否を制御する。
deploy = bool(common.get("resourceToggles", {}).get("virtualNetwork", True))

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "virtual-network.bicepparam"

# Bicep パラメータを行単位で構築して保存する。
lines = [
    "using '../bicep/main.virtual-network.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param logAnalyticsName = {quote(log_analytics_name)}",
    f"param logAnalyticsResourceGroupName = {quote(log_analytics_rg_name)}",
    f"param vnetName = {quote(vnet_name)}",
    f"param vnetAddressPrefixes = {to_bicep(vnet_address_prefixes)}",
    f"param vnetDnsServers = {to_bicep(vnet_dns_servers)}",
    f"param enableDdosProtection = {'true' if enable_ddos_protection else 'false'}",
    f"param ddosProtectionPlanId = {quote(ddos_protection_plan_id)}",
    f"param ddosProtectionPlanName = {quote(ddos_plan_name)}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

# 後続ステップが参照する最小限のメタ情報を保存する。
meta = {
    "location": location,
    "resourceGroupName": network_rg_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
