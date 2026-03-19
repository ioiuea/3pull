#!/usr/bin/env python3
"""AKS Azure RBAC 用 bicepparam を生成する。"""

import json
import os
import subprocess
from pathlib import Path


def quote(value: str) -> str:
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def identity_exists(resource_group_name: str, identity_name: str) -> bool:
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
aks_meta_path = Path(os.environ["AKS_META_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))
managed_ids_meta = json.loads(managed_ids_meta_path.read_text(encoding="utf-8"))
aks_meta = json.loads(aks_meta_path.read_text(encoding="utf-8"))

common_values = common.get("common", {})
resource_toggles = common.get("resourceToggles", {})

environment_name = str(common_values.get("environmentName", "")).strip()
system_name = str(common_values.get("systemName", "")).strip()
location = str(common_values.get("location", "")).strip()
if not environment_name or not system_name or not location:
    raise SystemExit(
        "common.parameter.json の common.environmentName / common.systemName / common.location を設定してください"
    )

modules_name = str(config.get("modulesName", "svc")).strip() or "svc"
resource_group_name = str(aks_meta.get("resourceGroupName", "")).strip() or f"rg-{environment_name}-{system_name}-{modules_name}"
aks_name = str(aks_meta.get("aksName", "")).strip() or f"aks-{environment_name}-{system_name}"
managed_identity_resource_group_name = str(managed_ids_meta.get("resourceGroupName", "")).strip()
if not managed_identity_resource_group_name:
    raise SystemExit("managed ids meta の resourceGroupName が取得できません")

aks_operator_managed_identity_name = f"mi-{environment_name}-{system_name}-aks-operator"
aks_admin_managed_identity_name = f"mi-{environment_name}-{system_name}-aks-admin"

deploy = (
    bool(resource_toggles.get("aks", True))
    and bool(resource_toggles.get("managedIds", True))
    and identity_exists(managed_identity_resource_group_name, aks_operator_managed_identity_name)
    and identity_exists(managed_identity_resource_group_name, aks_admin_managed_identity_name)
)

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "aks-rbac.bicepparam"

lines = [
    "using '../bicep/main.aks-rbac.bicep'",
    f"param managedIdentityResourceGroupName = {quote(managed_identity_resource_group_name)}",
    f"param aksName = {quote(aks_name)}",
    f"param aksOperatorManagedIdentityName = {quote(aks_operator_managed_identity_name)}",
    f"param aksAdminManagedIdentityName = {quote(aks_admin_managed_identity_name)}",
    f"param aksClusterUserRoleDefinitionId = {quote(config.get('aksClusterUserRoleDefinitionId', '4abbcc35-e782-43d8-92c5-2d3f1bd2253f'))}",
    f"param aksRbacReaderRoleDefinitionId = {quote(config.get('aksRbacReaderRoleDefinitionId', '7f6c6a51-bcf8-42ba-9220-52d62157d7db'))}",
    f"param aksRbacWriterRoleDefinitionId = {quote(config.get('aksRbacWriterRoleDefinitionId', 'a7ffa36f-339b-4b5c-8bdf-e2c188b2c0eb'))}",
    f"param aksRbacClusterAdminRoleDefinitionId = {quote(config.get('aksRbacClusterAdminRoleDefinitionId', 'b1ff04bb-8a4e-4dc4-8eb5-8693973ce19b'))}",
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

meta = {
    "resourceGroupName": resource_group_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
