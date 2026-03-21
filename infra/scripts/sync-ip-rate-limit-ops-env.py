#!/usr/bin/env python3
"""IP rate limit ops 向けの generated.env.sh を生成する。"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def az_tsv(*args: str) -> str:
    result = subprocess.run(
        ["az", *args, "-o", "tsv", "--only-show-errors"],
        capture_output=True,
        text=True,
        check=False,
    )
    value = result.stdout.strip()
    if result.returncode != 0 or not value:
        raise SystemExit(f"Azure CLI から値を取得できません: {' '.join(args)}")
    return value


common_path = Path(os.environ["COMMON_FILE"])
managed_ids_meta_path = Path(os.environ["MANAGED_IDS_META_FILE"])
redis_meta_path = Path(os.environ["REDIS_META_FILE"])
output_path = Path(os.environ["OUTPUT_FILE"])

common = json.loads(common_path.read_text(encoding="utf-8"))
managed_ids_meta = json.loads(managed_ids_meta_path.read_text(encoding="utf-8"))
redis_meta = json.loads(redis_meta_path.read_text(encoding="utf-8"))

environment_name = str(common.get("common", {}).get("environmentName", "")).strip()
system_name = str(common.get("common", {}).get("systemName", "")).strip()
managed_identity_resource_group_name = str(managed_ids_meta.get("resourceGroupName", "")).strip()

redis_host = str(redis_meta.get("redisHost", "")).strip()
redis_port = str(redis_meta.get("redisPort", "")).strip()
redis_ops_managed_identity_name = f"mi-{environment_name}-{system_name}-redis-ops"

if not redis_host:
    raise SystemExit("REDIS host が取得できません。")
if not redis_port:
    raise SystemExit("REDIS port が取得できません。")
if not environment_name or not system_name:
    raise SystemExit("environmentName/systemName が取得できません。")
if not managed_identity_resource_group_name:
    raise SystemExit("managed ids resourceGroupName が取得できません。")

redis_ops_managed_identity_client_id = az_tsv(
    "identity",
    "show",
    "--resource-group",
    managed_identity_resource_group_name,
    "--name",
    redis_ops_managed_identity_name,
    "--query",
    "clientId",
)
redis_ops_managed_identity_principal_id = az_tsv(
    "identity",
    "show",
    "--resource-group",
    managed_identity_resource_group_name,
    "--name",
    redis_ops_managed_identity_name,
    "--query",
    "principalId",
)

content = f"""#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Auto-generated file
# -----------------------------------------------------------------------------
# このファイルは infra/main.sh から自動生成されます。
# 直接編集しても次回生成時に上書きされます。

export REDIS_HOST={redis_host}
export REDIS_PORT={redis_port}
export REDIS_OPS_MANAGED_IDENTITY_CLIENT_ID={redis_ops_managed_identity_client_id}
export REDIS_OPS_MANAGED_IDENTITY_PRINCIPAL_ID={redis_ops_managed_identity_principal_id}
"""

output_path.write_text(content, encoding="utf-8")
output_path.chmod(0o755)

print(f"[OK] ip rate limit ops env synced: {output_path}")
