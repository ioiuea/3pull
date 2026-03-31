#!/usr/bin/env python3
"""Application Gateway RBAC 用 bicepparam を生成する。"""

import json
import os
import subprocess
from pathlib import Path


def quote(value: str) -> str:
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def identity_exists(resource_group_name: str, identity_name: str) -> bool:
    """Managed Identity の存在有無を判定する。"""
    result = subprocess.run(
        [
            "az",
            "identity",
            "show",
            "--resource-group",
            resource_group_name,
            "--name",
            identity_name,
            "--query",
            "id",
            "-o",
            "tsv",
            "--only-show-errors",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


common_path = Path(os.environ["COMMON_FILE"])
config_path = Path(os.environ["RESOURCE_CONFIG_FILE"])
managed_ids_meta_path = Path(os.environ["MANAGED_IDS_META_FILE"])
application_gateway_meta_path = Path(os.environ["APPLICATION_GATEWAY_META_FILE"])
application_gateway_low_latency_meta_path = Path(os.environ["APPLICATION_GATEWAY_LOW_LATENCY_META_FILE"])
subnets_config_path = Path(os.environ["SUBNETS_CONFIG_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))
managed_ids_meta = json.loads(managed_ids_meta_path.read_text(encoding="utf-8"))
application_gateway_meta = json.loads(application_gateway_meta_path.read_text(encoding="utf-8"))
application_gateway_low_latency_meta = json.loads(application_gateway_low_latency_meta_path.read_text(encoding="utf-8"))
subnets_config = json.loads(subnets_config_path.read_text(encoding="utf-8"))

common_values = common.get("common", {})
network_values = common.get("network", {})
resource_toggles = common.get("resourceToggles", {})

environment_name = common_values.get("environmentName", "")
system_name = common_values.get("systemName", "")
if not environment_name or not system_name:
    raise SystemExit(
        "common.parameter.json の common.environmentName / common.systemName を設定してください"
    )

enable_low_latency_subnet = bool(network_values.get("enableLowLatencyApplicationGatewaySubnet", False))
virtual_network_name = f"vnet-{environment_name}-{system_name}"

application_gateway_resource_group_name = application_gateway_meta.get(
    "resourceGroupName", f"rg-{environment_name}-{system_name}-nw"
)
managed_identity_resource_group_name = managed_ids_meta.get("resourceGroupName", f"rg-{environment_name}-{system_name}-svc")
if not managed_identity_resource_group_name:
    raise SystemExit("managed ids meta の resourceGroupName が取得できません")

standard_application_gateway_name = application_gateway_meta.get(
    "applicationGatewayName", f"agw-{environment_name}-{system_name}"
 ) or f"agw-{environment_name}-{system_name}"
low_latency_application_gateway_name = application_gateway_low_latency_meta.get(
    "applicationGatewayName", f"agw-ll-{environment_name}-{system_name}"
) or f"agw-ll-{environment_name}-{system_name}"

agic_standard_managed_identity_name = f"mi-{environment_name}-{system_name}-agic-standard"
agic_low_latency_managed_identity_name = f"mi-{environment_name}-{system_name}-agic-lowlatency"
app_gateway_contributor_role_definition_id = config.get(
    "appGatewayContributorRoleDefinitionId", "b24988ac-6180-42a0-ab88-20f7382dd24c"
)
network_contributor_role_definition_id = config.get(
    "networkContributorRoleDefinitionId", "4d97b98b-1d4f-4787-a291-c67834d212e7"
)

subnet_definitions = subnets_config.get("subnetDefinitions", [])
standard_application_gateway_subnet_name = next(
    (
        str(subnet.get("name", "")).strip()
        for subnet in subnet_definitions
        if subnet.get("alias") == "agic"
    ),
    "ApplicationGatewaySubnet",
)
low_latency_application_gateway_subnet_name = next(
    (
        str(subnet.get("name", "")).strip()
        for subnet in subnet_definitions
        if subnet.get("alias") == "agicll"
    ),
    "ApplicationGatewayLowLatencySubnet",
)

has_standard_agic_identity = identity_exists(
    managed_identity_resource_group_name,
    agic_standard_managed_identity_name,
)
has_low_latency_agic_identity = (
    identity_exists(managed_identity_resource_group_name, agic_low_latency_managed_identity_name)
    if enable_low_latency_subnet
    else True
)
deploy = bool(resource_toggles.get("applicationGateway", True)) and has_standard_agic_identity and has_low_latency_agic_identity

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "application-gateway-rbac.bicepparam"

lines = [
    "using '../bicep/main.application-gateway-rbac.bicep'",
    f"param managedIdentityResourceGroupName = {quote(managed_identity_resource_group_name)}",
    f"param agicStandardManagedIdentityName = {quote(agic_standard_managed_identity_name)}",
    f"param agicLowLatencyManagedIdentityName = {quote(agic_low_latency_managed_identity_name)}",
    f"param standardApplicationGatewayName = {quote(standard_application_gateway_name)}",
    f"param lowLatencyApplicationGatewayName = {quote(low_latency_application_gateway_name)}",
    f"param virtualNetworkName = {quote(virtual_network_name)}",
    f"param standardApplicationGatewaySubnetName = {quote(standard_application_gateway_subnet_name)}",
    f"param lowLatencyApplicationGatewaySubnetName = {quote(low_latency_application_gateway_subnet_name)}",
    f"param enableLowLatencyApplicationGatewaySubnet = {'true' if enable_low_latency_subnet else 'false'}",
    f"param appGatewayContributorRoleDefinitionId = {quote(app_gateway_contributor_role_definition_id)}",
    f"param networkContributorRoleDefinitionId = {quote(network_contributor_role_definition_id)}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

meta = {
    "resourceGroupName": application_gateway_resource_group_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
