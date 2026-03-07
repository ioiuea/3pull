#!/usr/bin/env python3
"""Application Gateway RBAC 用 bicepparam を生成する。"""

import json
import os
from pathlib import Path


def quote(value: str) -> str:
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


common_path = Path(os.environ["COMMON_FILE"])
config_path = Path(os.environ["RESOURCE_CONFIG_FILE"])
aks_meta_path = Path(os.environ["AKS_META_FILE"])
application_gateway_meta_path = Path(os.environ["APPLICATION_GATEWAY_META_FILE"])
application_gateway_low_latency_meta_path = Path(os.environ["APPLICATION_GATEWAY_LOW_LATENCY_META_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))
aks_meta = json.loads(aks_meta_path.read_text(encoding="utf-8"))
application_gateway_meta = json.loads(application_gateway_meta_path.read_text(encoding="utf-8"))
application_gateway_low_latency_meta = json.loads(application_gateway_low_latency_meta_path.read_text(encoding="utf-8"))

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
deploy = bool(resource_toggles.get("aks", True))

application_gateway_resource_group_name = application_gateway_meta.get(
    "resourceGroupName", f"rg-{environment_name}-{system_name}-nw"
)
managed_identity_resource_group_name = aks_meta.get("resourceGroupName", f"rg-{environment_name}-{system_name}-svc")

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

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "application-gateway-rbac.bicepparam"

lines = [
    "using '../bicep/main.application-gateway-rbac.bicep'",
    f"param managedIdentityResourceGroupName = {quote(managed_identity_resource_group_name)}",
    f"param agicStandardManagedIdentityName = {quote(agic_standard_managed_identity_name)}",
    f"param agicLowLatencyManagedIdentityName = {quote(agic_low_latency_managed_identity_name)}",
    f"param standardApplicationGatewayName = {quote(standard_application_gateway_name)}",
    f"param lowLatencyApplicationGatewayName = {quote(low_latency_application_gateway_name)}",
    f"param enableLowLatencyApplicationGatewaySubnet = {'true' if enable_low_latency_subnet else 'false'}",
    f"param appGatewayContributorRoleDefinitionId = {quote(app_gateway_contributor_role_definition_id)}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

meta = {
    "resourceGroupName": application_gateway_resource_group_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
