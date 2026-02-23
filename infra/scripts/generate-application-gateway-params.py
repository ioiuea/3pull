#!/usr/bin/env python3
"""Application Gateway 用 bicepparam を生成する。

主な処理:
1. サブネット定義から ApplicationGatewaySubnet の CIDR を再計算する。
2. フロントエンド固定 Private IP を算出する。
3. AGW/WAF/PIP 作成に必要な .bicepparam とメタ情報を出力する。
"""

import ipaddress
import json
import os
from pathlib import Path


def quote(value: str) -> str:
    """Bicep 文字列リテラル向けに single quote をエスケープする。"""
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


# main.sh から受け取る入出力パス。
common_path = Path(os.environ["COMMON_FILE"])
config_path = Path(os.environ["RESOURCE_CONFIG_FILE"])
subnets_config_path = Path(os.environ["SUBNETS_CONFIG_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

# 共通値とリソース固定定義を読み込む。
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
application_gateway_subnet = None

# Subnet 生成ロジックと同じ手順で AGW サブネットを特定する。
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

    if subnet.get("name") == "ApplicationGatewaySubnet":
        application_gateway_subnet = allocated

if application_gateway_subnet is None:
    raise SystemExit("ApplicationGatewaySubnet is not defined")

# 設計上、フロントエンド Private IP は 10 番目の利用可能 IP を使う。
hosts = list(application_gateway_subnet.hosts())
if len(hosts) < 10:
    raise SystemExit("ApplicationGatewaySubnet does not have enough usable IPs to assign the 10th host")
frontend_private_ip = str(hosts[9])

modules_name = config.get("modulesName", "nw")
enable_resource_lock = bool(common_values.get("enableResourceLock", True))
lock_kind = config.get("lockKind", "CanNotDelete") if enable_resource_lock else ""
network_rg_name = f"rg-{environment_name}-{system_name}-{modules_name}"
vnet_name = f"vnet-{environment_name}-{system_name}"
log_analytics_name = f"log-{environment_name}-{system_name}"
log_analytics_resource_group_name = f"rg-{environment_name}-{system_name}-monitor"

enable_ddos_protection = bool(network_values.get("enableDdosProtection", True))
deploy = bool(common.get("resourceToggles", {}).get("applicationGateway", True))

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "application-gateway.bicepparam"

application_gateway_name = f"agw-{environment_name}-{system_name}"
public_ip_name = f"pip-agw-{environment_name}-{system_name}"
waf_policy_name = f"waf-{environment_name}-{system_name}"

# AGW デプロイ用パラメータを出力する。
lines = [
    "using '../bicep/main.application-gateway.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param logAnalyticsName = {quote(log_analytics_name)}",
    f"param logAnalyticsResourceGroupName = {quote(log_analytics_resource_group_name)}",
    f"param vnetName = {quote(vnet_name)}",
    f"param applicationGatewayName = {quote(application_gateway_name)}",
    f"param publicIPName = {quote(public_ip_name)}",
    f"param wafPolicyName = {quote(waf_policy_name)}",
    f"param frontendPrivateIPAddress = {quote(frontend_private_ip)}",
    f"param protectionMode = {quote('Enabled' if enable_ddos_protection else 'Disabled')}",
    f"param publicIPSku = {quote(config.get('publicIPSku', 'Standard'))}",
    f"param publicIPAllocationMethod = {quote(config.get('publicIPAllocationMethod', 'Static'))}",
    f"param publicIPAddressVersion = {quote(config.get('publicIPAddressVersion', 'IPv4'))}",
    f"param appGatewaySkuName = {quote(config.get('appGatewaySkuName', 'WAF_v2'))}",
    f"param appGatewaySkuTier = {quote(config.get('appGatewaySkuTier', 'WAF_v2'))}",
    f"param appGatewaySkuCapacity = {int(config.get('appGatewaySkuCapacity', 1))}",
    f"param frontendPrivateIPAllocationMethod = {quote(config.get('frontendPrivateIPAllocationMethod', 'Static'))}",
    f"param frontendPort = {int(config.get('frontendPort', 80))}",
    f"param backendHttpPort = {int(config.get('backendHttpPort', 80))}",
    f"param backendHttpProtocol = {quote(config.get('backendHttpProtocol', 'Http'))}",
    f"param backendCookieBasedAffinity = {quote(config.get('backendCookieBasedAffinity', 'Enabled'))}",
    f"param backendRequestTimeout = {int(config.get('backendRequestTimeout', 60))}",
    f"param probeProtocol = {quote(config.get('probeProtocol', 'Http'))}",
    f"param probeHost = {quote(config.get('probeHost', 'www.contoso.com'))}",
    f"param probePath = {quote(config.get('probePath', '/path/to/probe'))}",
    f"param probeInterval = {int(config.get('probeInterval', 30))}",
    f"param probeTimeout = {int(config.get('probeTimeout', 120))}",
    f"param probeUnhealthyThreshold = {int(config.get('probeUnhealthyThreshold', 8))}",
    f"param wafMode = {quote(config.get('wafMode', 'Detection'))}",
    f"param wafState = {quote(config.get('wafState', 'Enabled'))}",
    f"param wafRequestBodyCheck = {'true' if bool(config.get('wafRequestBodyCheck', True)) else 'false'}",
    f"param wafRequestBodyInspectLimitInKB = {int(config.get('wafRequestBodyInspectLimitInKB', 2000))}",
    f"param wafMaxRequestBodySizeInKb = {int(config.get('wafMaxRequestBodySizeInKb', 2000))}",
    f"param wafFileUploadLimitInMb = {int(config.get('wafFileUploadLimitInMb', 100))}",
    f"param wafRuleSetType = {quote(config.get('wafRuleSetType', 'OWASP'))}",
    f"param wafRuleSetVersion = {quote(config.get('wafRuleSetVersion', '3.2'))}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

# main.sh が参照するメタ情報。
meta = {
    "resourceGroupName": network_rg_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
    "applicationGatewayName": application_gateway_name,
    "publicIPName": public_ip_name,
    "wafPolicyName": waf_policy_name,
    "frontendPrivateIPAddress": frontend_private_ip,
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
