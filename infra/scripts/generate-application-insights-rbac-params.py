#!/usr/bin/env python3
"""Application Insights RBAC 用 bicepparam を生成する。"""

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
appi_meta_path = Path(os.environ["APPI_META_FILE"])
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))
managed_ids_meta = json.loads(managed_ids_meta_path.read_text(encoding="utf-8"))
appi_meta = json.loads(appi_meta_path.read_text(encoding="utf-8"))

common_values = common.get("common", {})
resource_toggles = common.get("resourceToggles", {})

environment_name = str(common_values.get("environmentName", "")).strip()
system_name = str(common_values.get("systemName", "")).strip()
if not environment_name or not system_name:
    raise SystemExit(
        "common.parameter.json の common.environmentName / common.systemName を設定してください"
    )

managed_identity_resource_group_name = str(managed_ids_meta.get("resourceGroupName", "")).strip()
application_insights_resource_group_name = str(appi_meta.get("resourceGroupName", "")).strip()
if not managed_identity_resource_group_name:
    raise SystemExit("managed ids meta の resourceGroupName が取得できません")
if not application_insights_resource_group_name:
    raise SystemExit("application insights meta の resourceGroupName が取得できません")

application_insights_name = f"appi-{environment_name}-{system_name}"
api_managed_identity_name = f"mi-{environment_name}-{system_name}-api"
worker_managed_identity_name = f"mi-{environment_name}-{system_name}-worker"
schedulers_managed_identity_name = f"mi-{environment_name}-{system_name}-schedulers"

deploy = (
    bool(resource_toggles.get("applicationInsights", True))
    and bool(resource_toggles.get("managedIds", True))
    and bool(config.get("enabled", True))
    and identity_exists(managed_identity_resource_group_name, api_managed_identity_name)
    and identity_exists(managed_identity_resource_group_name, worker_managed_identity_name)
    and identity_exists(managed_identity_resource_group_name, schedulers_managed_identity_name)
)

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "application-insights-rbac.bicepparam"

lines = [
    "using '../bicep/main.application-insights-rbac.bicep'",
    f"param managedIdentityResourceGroupName = {quote(managed_identity_resource_group_name)}",
    f"param applicationInsightsName = {quote(application_insights_name)}",
    f"param apiManagedIdentityName = {quote(api_managed_identity_name)}",
    f"param workerManagedIdentityName = {quote(worker_managed_identity_name)}",
    f"param schedulersManagedIdentityName = {quote(schedulers_managed_identity_name)}",
    "param monitoringMetricsPublisherRoleDefinitionId = "
    + quote(config.get("monitoringMetricsPublisherRoleDefinitionId", "3913510d-42f4-4e42-8a64-420c390055eb")),
    "",
]
params_file.write_text("\n".join(lines), encoding="utf-8")

meta = {
    "resourceGroupName": application_insights_resource_group_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
