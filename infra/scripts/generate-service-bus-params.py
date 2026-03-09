#!/usr/bin/env python3
"""Service Bus 用 bicepparam を生成する。"""

import json
import os
import subprocess
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


def resolve_role_definition_id(*, role_name: str) -> str:
    """Azure ロール名から roleDefinitionId(リソースID)を取得する。"""
    result = subprocess.run(
        [
            "az",
            "role",
            "definition",
            "list",
            "--name",
            role_name,
            "--query",
            "[0].id",
            "-o",
            "tsv",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"ロール定義の取得に失敗しました: {role_name}\n{result.stderr.strip()}"
        )
    role_definition_id = result.stdout.strip()
    if not role_definition_id:
        raise SystemExit(f"ロール定義が見つかりません: {role_name}")
    return role_definition_id


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
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))
managed_ids_meta = json.loads(managed_ids_meta_path.read_text(encoding="utf-8"))

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

modules_name = config.get("modulesName", "svc")
enable_resource_lock = bool(common_values.get("enableResourceLock", True))
lock_kind = config.get("lockKind", "CanNotDelete") if enable_resource_lock else ""
resource_group_name = f"rg-{environment_name}-{system_name}-{modules_name}"
vnet_resource_group_name = f"rg-{environment_name}-{system_name}-nw"
managed_identity_resource_group_name = managed_ids_meta.get("resourceGroupName", "")
if not managed_identity_resource_group_name:
    raise SystemExit("managed ids meta の resourceGroupName が取得できません")

api_managed_identity_name = f"mi-{environment_name}-{system_name}-api"
worker_managed_identity_name = f"mi-{environment_name}-{system_name}-worker"
keda_operator_managed_identity_name = f"mi-{environment_name}-{system_name}-keda-operator"
toggle_enabled = bool(common.get("resourceToggles", {}).get("serviceBus", True))
enable_workload_identity_rbac = toggle_enabled and all(
    [
        identity_exists(managed_identity_resource_group_name, api_managed_identity_name),
        identity_exists(managed_identity_resource_group_name, worker_managed_identity_name),
        identity_exists(managed_identity_resource_group_name, keda_operator_managed_identity_name),
    ]
)

service_bus_namespace_name = f"sb-{environment_name}-{system_name}"
private_endpoint_name = f"pep-sb-{environment_name}-{system_name}"
private_dns_zone_group_name = f"dnszg-sb-{environment_name}-{system_name}"
private_dns_vnet_link_name = f"link-sb-to-vnet-{environment_name}-{system_name}"
vnet_name = f"vnet-{environment_name}-{system_name}"

log_analytics_name = f"log-{environment_name}-{system_name}"
log_analytics_resource_group_name = f"rg-{environment_name}-{system_name}-monitor"

queues = config.get("queues", [])
if not isinstance(queues, list) or not queues or not all(isinstance(q, str) and q.strip() for q in queues):
    raise SystemExit("service-bus config の queues は空でない文字列配列で指定してください。")
queues = [q.strip() for q in queues]

service_bus_data_sender_role_definition_id = config.get("serviceBusDataSenderRoleDefinitionId", "").strip()
if not service_bus_data_sender_role_definition_id:
    service_bus_data_sender_role_definition_id = resolve_role_definition_id(
        role_name="Azure Service Bus Data Sender"
    )

service_bus_data_receiver_role_definition_id = config.get("serviceBusDataReceiverRoleDefinitionId", "").strip()
if not service_bus_data_receiver_role_definition_id:
    service_bus_data_receiver_role_definition_id = resolve_role_definition_id(
        role_name="Azure Service Bus Data Receiver"
    )

enable_centralized_private_dns = bool(network_values.get("enableCentralizedPrivateDns", False))
deploy = bool(common.get("resourceToggles", {}).get("serviceBus", True))

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "service-bus.bicepparam"

lines = [
    "using '../bicep/main.service-bus.bicep'",
    f"param environmentName = {quote(environment_name)}",
    f"param systemName = {quote(system_name)}",
    f"param location = {quote(location)}",
    f"param modulesName = {quote(modules_name)}",
    f"param lockKind = {quote(lock_kind)}",
    f"param logAnalyticsName = {quote(log_analytics_name)}",
    f"param logAnalyticsResourceGroupName = {quote(log_analytics_resource_group_name)}",
    f"param vnetName = {quote(vnet_name)}",
    f"param vnetResourceGroupName = {quote(vnet_resource_group_name)}",
    f"param managedIdentityResourceGroupName = {quote(managed_identity_resource_group_name)}",
    f"param apiManagedIdentityName = {quote(api_managed_identity_name)}",
    f"param workerManagedIdentityName = {quote(worker_managed_identity_name)}",
    f"param kedaOperatorManagedIdentityName = {quote(keda_operator_managed_identity_name)}",
    f"param enableWorkloadIdentityRbac = {'true' if enable_workload_identity_rbac else 'false'}",
    f"param serviceBusNamespaceName = {quote(service_bus_namespace_name)}",
    f"param serviceBusSkuName = {quote(config.get('skuName', 'Standard'))}",
    f"param serviceBusSkuCapacity = {int(config.get('skuCapacity', 1))}",
    f"param publicNetworkAccess = {quote(config.get('publicNetworkAccess', 'Disabled'))}",
    f"param minimumTlsVersion = {quote(config.get('minimumTlsVersion', '1.2'))}",
    f"param disableLocalAuth = {'true' if bool(config.get('disableLocalAuth', True)) else 'false'}",
    f"param zoneRedundant = {'true' if bool(config.get('zoneRedundant', False)) else 'false'}",
    f"param queueNames = {to_bicep_string_array(queues)}",
    f"param serviceBusDataSenderRoleDefinitionId = {quote(service_bus_data_sender_role_definition_id)}",
    f"param serviceBusDataReceiverRoleDefinitionId = {quote(service_bus_data_receiver_role_definition_id)}",
    f"param privateEndpointName = {quote(private_endpoint_name)}",
    f"param privateDnsZoneName = {quote(config.get('privateDnsZoneName', 'privatelink.servicebus.windows.net'))}",
    f"param privateDnsZoneGroupName = {quote(private_dns_zone_group_name)}",
    f"param privateDnsVnetLinkName = {quote(private_dns_vnet_link_name)}",
    f"param enableCentralizedPrivateDns = {'true' if enable_centralized_private_dns else 'false'}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

meta = {
    "resourceGroupName": resource_group_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
    "serviceBusNamespaceName": service_bus_namespace_name,
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
