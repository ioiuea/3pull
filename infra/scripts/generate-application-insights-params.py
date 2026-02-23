#!/usr/bin/env python3
"""Application Insights 用 bicepparam を生成する。

処理の流れ:
1. 共通パラメータと設定ファイルを読み込む。
2. 命名規則に従って Monitor 系のリソース名を組み立てる。
3. .bicepparam と実行メタ情報を出力する。
"""

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
params_dir = Path(os.environ["PARAMS_DIR"])
out_meta_path = Path(os.environ["OUT_META_FILE"])

# 共通定義とリソース設定を読み込む。
common = json.loads(common_path.read_text(encoding="utf-8"))
config = json.loads(config_path.read_text(encoding="utf-8"))

common_values = common.get("common", {})
enable_resource_lock = bool(common_values.get("enableResourceLock", True))
lock_kind = config.get("lockKind", "CanNotDelete") if enable_resource_lock else ""
environment_name = common_values.get("environmentName", "")
system_name = common_values.get("systemName", "")
location = common_values.get("location", "")

if not environment_name or not system_name or not location:
    raise SystemExit("common.parameter.json の common.environmentName / common.systemName / common.location を設定してください")

modules_name = config.get("modulesName", "monitor")
resource_group_name = f"rg-{environment_name}-{system_name}-{modules_name}"
log_analytics_name = f"log-{environment_name}-{system_name}"
application_insights_name = f"appi-{environment_name}-{system_name}"

# 実行有無トグル。false の場合は main.sh 側で deploy がスキップされる。
deploy = bool(common.get("resourceToggles", {}).get("applicationInsights", True))

params_dir.mkdir(parents=True, exist_ok=True)
params_file = params_dir / "application-insights.bicepparam"

# Bicep 実行用パラメータを出力する。
params_file.write_text(
    "\n".join(
        [
            "using '../bicep/main.application_insights.bicep'",
            f"param environmentName = {quote(environment_name)}",
            f"param systemName = {quote(system_name)}",
            f"param location = {quote(location)}",
            f"param modulesName = {quote(modules_name)}",
            f"param retentionInDays = {int(config.get('retentionInDays', 365))}",
            "param publicNetworkAccessForIngestion = "
            + quote(config.get("publicNetworkAccessForIngestion", "Disabled")),
            "param publicNetworkAccessForQuery = "
            + quote(config.get("publicNetworkAccessForQuery", "Enabled")),
            f"param lockKind = {quote(lock_kind)}",
            "param applicationInsightsIngestion = "
            + quote(config.get("applicationInsightsIngestion", "LogAnalytics")),
            "param applicationInsightsType = "
            + quote(config.get("applicationInsightsType", "web")),
            f"param logAnalyticsResourceGroupName = {quote(resource_group_name)}",
            f"param logAnalyticsName = {quote(log_analytics_name)}",
            f"param applicationInsightsName = {quote(application_insights_name)}",
            "",
        ]
    ),
    encoding="utf-8",
)

# 後続処理へ渡すメタ情報。
meta = {
    "location": location,
    "resourceGroupName": resource_group_name,
    "deploy": deploy,
    "paramsFile": str(params_file),
}
out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
