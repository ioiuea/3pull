#!/usr/bin/env python3
"""infra の出力に合わせて backend Helm values を更新する。"""

from __future__ import annotations

import json
import os
import re
import subprocess
import ipaddress
from pathlib import Path


def normalize_registry_suffix(value: str) -> str:
    """ACR 名に利用可能な文字へ正規化する（英小文字/数字のみ）。"""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def normalize_storage_account_name(environment_name: str, system_name: str) -> str:
    """Storage Account 命名制約に合わせて正規化する。"""
    env = re.sub(r"[^a-z0-9]", "", environment_name.lower())
    system = re.sub(r"[^a-z0-9]", "", system_name.lower())
    return f"st{env}{system}"


def normalize_image_component(value: str) -> str:
    """コンテナイメージ名に使う文字へ正規化する。"""
    name = re.sub(r"[^a-z0-9-]", "-", value.lower())
    name = re.sub(r"-{2,}", "-", name).strip("-")
    return name or "app"


def normalize_redis_name(environment_name: str, system_name: str) -> str:
    env = re.sub(r"[^a-z0-9-]", "-", environment_name.lower())
    system = re.sub(r"[^a-z0-9-]", "-", system_name.lower())
    return re.sub(r"-{2,}", "-", f"redis-{env}-{system}").strip("-")


def resolve_trusted_proxy_cidrs(*, common: dict, subnets_config: dict) -> list[str]:
    subnet_defs = subnets_config.get("subnetDefinitions", [])
    vnet_address_prefixes = common.get("network", {}).get("vnetAddressPrefixes", [])
    enable_low_latency = bool(common.get("network", {}).get("enableLowLatencyApplicationGatewaySubnet", False))
    shared_bastion_ip = str(common.get("network", {}).get("sharedBastionIp", "")).strip()

    if shared_bastion_ip:
        subnet_defs = [s for s in subnet_defs if s.get("alias", s.get("name")) != "bastion"]
    if not enable_low_latency:
        subnet_defs = [
            s
            for s in subnet_defs
            if s.get("name") != "ApplicationGatewayLowLatencySubnet"
            and s.get("alias", s.get("name")) != "agicll"
        ]

    base_prefixes = [ipaddress.ip_network(p) for p in vnet_address_prefixes]
    range_index = 0
    current = int(base_prefixes[0].network_address)
    resolved_subnets: list[dict] = []

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

        resolved_subnets.append(
            {
                **subnet,
                "alias": subnet.get("alias", subnet.get("name")),
                "addressPrefix": str(allocated),
            }
        )

    aliases = {"agic", "firewall"}
    if enable_low_latency:
        aliases.add("agicll")

    return [
        subnet["addressPrefix"]
        for subnet in resolved_subnets
        if subnet.get("alias") in aliases
    ]


def run_az(cmd: list[str]) -> str:
    """Azure CLI を実行し、stdout を返す。失敗時は終了する。"""
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise SystemExit(f"Azure CLI 実行失敗: {' '.join(cmd)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def yaml_quote(value: str) -> str:
    """YAML 向けに単一引用符で文字列化する。"""
    return "'" + value.replace("'", "''") + "'"


def update_values(content: str, replacements: dict[str, str]) -> str:
    """YAML テキストを path 指定で置換する。"""
    updated_lines: list[str] = []
    path_stack: list[tuple[int, str]] = []

    for raw_line in content.splitlines(keepends=True):
        line = raw_line
        stripped = line.strip()
        match = re.match(r"^(\s*)([A-Za-z0-9_-]+):(.*)$", line)

        if not match or stripped.startswith("#") or stripped.startswith("- "):
            updated_lines.append(line)
            continue

        indent = len(match.group(1))
        key = match.group(2)
        rest = match.group(3)

        while path_stack and indent <= path_stack[-1][0]:
            path_stack.pop()
        path_stack.append((indent, key))

        path = ".".join(item[1] for item in path_stack)
        wildcard_path = path
        wildcard_path = re.sub(r"^workers\.[^.]+\.image\.repository$", "workers.*.image.repository", wildcard_path)
        wildcard_path = re.sub(r"^workers\.[^.]+\.image\.tag$", "workers.*.image.tag", wildcard_path)
        replacement = replacements.get(path, replacements.get(wildcard_path))

        # 「key:」形式（値なし）は親ノードなので置換しない
        if replacement is None or rest.strip() == "":
            updated_lines.append(line)
            continue

        updated_lines.append(f"{match.group(1)}{key}: {replacement}\n")

    return "".join(updated_lines)


def add_guidance_comments(content: str) -> str:
    """生成 values に利用者向けガイドコメントを付与する。"""
    header = """# -----------------------------------------------------------------------------
# Auto-generated file
# -----------------------------------------------------------------------------
# このファイルは `infra/main.sh` から自動生成されます。
# 直接編集しても次回生成時に上書きされます。
#
# 使い方:
# 1. まず image.tag の `__IMAGE_TAG__` を CI で実際のタグに置き換えます
#    例: git sha やリリースタグ
# 2. Entra 関連の値は環境に合わせて必ず設定します
# 3. 変更したファイルを使って `helm upgrade --install` を実行します
# -----------------------------------------------------------------------------
"""

    section_comments = [
        (
            "ingress:",
            "# Ingress 設定\n# 通常系/低遅延系のドメイン分離を前提とします（ll = low-latency）。",
        ),
        (
            "  standard:",
            "  # 通常系 API 向け Ingress",
        ),
        (
            "  lowLatency:",
            "  # 低遅延系 API 向け Ingress（限定 API のみ公開）",
        ),
        (
            "api:",
            "# API Deployment 設定\n# image.repository はインフラ側で自動更新されます。\n# image.tag は CI で毎回置き換えてください。",
        ),
        (
            "workers:",
            "# 非同期 worker 設定\n# worker ごとの queueName / workerModule を定義します。\n# image.tag は CI で毎回置き換えてください。",
        ),
        (
            "keda:",
            "# KEDA 設定\n# workloadIdentity.clientId は keda-operator Managed Identity で自動更新されます。",
        ),
        (
            "schedulers:",
            "# Schedulers CronJob 設定\n# image.tag は CI で毎回置き換えてください。",
        ),
        (
            "keyVault:",
            "# Key Vault 連携設定\n# vaultName / tenantId はインフラ情報から自動更新されます。",
        ),
        (
            "serviceAccounts:",
            "# ServiceAccount 設定\n# name / clientId は Managed Identity 情報で自動更新されます。\n# 手動変更すると federated credential と不整合になるため非推奨です。",
        ),
        (
            "config:",
            "# アプリケーション設定（環境変数）\n# Azure 接続先（Service Bus / Blob など）は自動更新されます。",
        ),
        (
            "secretRefs:",
            "# Secret のキー名マッピング\n# Key Vault から取得したシークレット名と一致させます。",
        ),
        (
            "    host:",
            "    # 必須: 公開ドメインへ置き換えてください",
        ),
        (
            "    ENTRA_TENANT_ID:",
            "    # 必須: Entra テナント ID（本番値に置き換えてください）",
        ),
        (
            "    FRONTEND_BASE_URL:",
            "    # 必須: frontend の公開 URL（実ドメイン）に置き換えてください",
        ),
        (
            "    CSRF_TRUSTED_ORIGINS:",
            "    # 必須: CSRF 許可オリジンを実ドメインに置き換えてください（複数はカンマ区切り）",
        ),
        (
            "    ENTRA_CLIENT_ID:",
            "    # 必須: Entra アプリケーション(クライアント) ID（本番値に置き換えてください）",
        ),
        (
            "    ENTRA_REDIRECT_URI:",
            "    # 必須: Entra リダイレクト URI（公開 URL に合わせてください）",
        ),
        (
            "    ENTRA_INTERNAL_DOMAINS:",
            "    # 必須: 許可する社内ドメイン（例: example.com）",
        ),
    ]

    lines = content.splitlines()
    output_lines: list[str] = []
    inserted = set()

    output_lines.extend(header.rstrip("\n").splitlines())

    for line in lines:
        stripped = line.strip()
        for anchor, comment in section_comments:
            if anchor in inserted:
                continue
            if line.startswith(anchor):
                output_lines.extend(comment.splitlines())
                inserted.add(anchor)
        output_lines.append(line)

    return "\n".join(output_lines) + "\n"


common_path = Path(os.environ["COMMON_FILE"])
aks_meta_path = Path(os.environ["AKS_META_FILE"])
storage_config_path = Path(os.environ["STORAGE_CONFIG_FILE"])
redis_meta_path = Path(os.environ["REDIS_META_FILE"])
subnets_config_path = Path(os.environ["SUBNETS_CONFIG_FILE"])
template_path_raw = os.environ.get("TEMPLATE_FILE", "").strip()
output_path_raw = os.environ.get("OUTPUT_FILE", "").strip()
if not template_path_raw:
    raise SystemExit("TEMPLATE_FILE が必要です。")
if not output_path_raw:
    raise SystemExit("OUTPUT_FILE が必要です。")
template_path = Path(template_path_raw)
output_path = Path(output_path_raw)

common = json.loads(common_path.read_text(encoding="utf-8"))
aks_meta = json.loads(aks_meta_path.read_text(encoding="utf-8"))
storage_config = json.loads(storage_config_path.read_text(encoding="utf-8"))
redis_meta = json.loads(redis_meta_path.read_text(encoding="utf-8"))
subnets_config = json.loads(subnets_config_path.read_text(encoding="utf-8"))

common_values = common.get("common", {})
network_values = common.get("network", {})
environment_name = str(common_values.get("environmentName", "")).strip()
system_name = str(common_values.get("systemName", "")).strip()
if not environment_name or not system_name:
    raise SystemExit("common.environmentName / common.systemName が必要です。")

managed_identity_resource_group_name = str(aks_meta.get("resourceGroupName", "")).strip()
if not managed_identity_resource_group_name:
    raise SystemExit("AKS meta の resourceGroupName が取得できません。")

if not template_path.exists():
    raise SystemExit(f"template values が見つかりません: {template_path}")

api_identity_name = f"mi-{environment_name}-{system_name}-api"
worker_identity_name = f"mi-{environment_name}-{system_name}-worker"
schedulers_identity_name = f"mi-{environment_name}-{system_name}-schedulers"
keda_operator_identity_name = f"mi-{environment_name}-{system_name}-keda-operator"

api_client_id = run_az(
    [
        "az",
        "identity",
        "show",
        "--resource-group",
        managed_identity_resource_group_name,
        "--name",
        api_identity_name,
        "--query",
        "clientId",
        "-o",
        "tsv",
    ]
)

worker_client_id = run_az(
    [
        "az",
        "identity",
        "show",
        "--resource-group",
        managed_identity_resource_group_name,
        "--name",
        worker_identity_name,
        "--query",
        "clientId",
        "-o",
        "tsv",
    ]
)

schedulers_client_id = run_az(
    [
        "az",
        "identity",
        "show",
        "--resource-group",
        managed_identity_resource_group_name,
        "--name",
        schedulers_identity_name,
        "--query",
        "clientId",
        "-o",
        "tsv",
    ]
)

keda_operator_client_id = run_az(
    [
        "az",
        "identity",
        "show",
        "--resource-group",
        managed_identity_resource_group_name,
        "--name",
        keda_operator_identity_name,
        "--query",
        "clientId",
        "-o",
        "tsv",
    ]
)

tenant_id = run_az(["az", "account", "show", "--query", "tenantId", "-o", "tsv"])

acr_name = f"cr{normalize_registry_suffix(environment_name)}{normalize_registry_suffix(system_name)}"
image_prefix = f"{acr_name}.azurecr.io"
system_image_name = normalize_image_component(system_name)
storage_account_name = normalize_storage_account_name(environment_name, system_name)
redis_name = str(redis_meta.get("redisName", "")).strip() or normalize_redis_name(environment_name, system_name)
redis_host = str(redis_meta.get("redisHost", "")).strip() or f"{redis_name}.{common_values.get('location', '')}.redis.azure.net"
redis_port = int(redis_meta.get("redisPort", 10000))
blob_container_name = str(storage_config.get("blobContainerName", "async-jobs")).strip() or "async-jobs"
standard_api_host = f"api-{environment_name}-{system_name}.example.com"
low_latency_api_host = f"ll-api-{environment_name}-{system_name}.example.com"
enable_low_latency_subnet = bool(network_values.get("enableLowLatencyApplicationGatewaySubnet", False))
trusted_proxy_cidrs = resolve_trusted_proxy_cidrs(common=common, subnets_config=subnets_config)
trusted_proxy_headers = bool(common.get("resourceToggles", {}).get("applicationGateway", True))

replacements = {
    "systemName": yaml_quote(system_name),
    "ingress.standard.host": yaml_quote(standard_api_host),
    "ingress.lowLatency.host": yaml_quote(low_latency_api_host),
    "ingress.lowLatency.enabled": "true" if enable_low_latency_subnet else "false",
    "api.image.repository": yaml_quote(f"{image_prefix}/{system_image_name}-api"),
    "api.image.tag": yaml_quote("__IMAGE_TAG__"),
    "workers.*.image.repository": yaml_quote(f"{image_prefix}/{system_image_name}-worker"),
    "workers.*.image.tag": yaml_quote("__IMAGE_TAG__"),
    "schedulers.image.repository": yaml_quote(f"{image_prefix}/{system_image_name}-schedulers"),
    "schedulers.image.tag": yaml_quote("__IMAGE_TAG__"),
    "keda.workloadIdentity.clientId": yaml_quote(keda_operator_client_id),
    "keyVault.vaultName": yaml_quote(f"kv-{environment_name}-{system_name}"),
    "keyVault.tenantId": yaml_quote(tenant_id),
    "serviceAccounts.api.name": yaml_quote(f"sa-{environment_name}-{system_name}-api"),
    "serviceAccounts.api.clientId": yaml_quote(api_client_id),
    "serviceAccounts.worker.name": yaml_quote(f"sa-{environment_name}-{system_name}-worker"),
    "serviceAccounts.worker.clientId": yaml_quote(worker_client_id),
    "serviceAccounts.schedulers.name": yaml_quote(f"sa-{environment_name}-{system_name}-schedulers"),
    "serviceAccounts.schedulers.clientId": yaml_quote(schedulers_client_id),
    "config.env.SERVICE_NAME": yaml_quote(f"{system_image_name}-api"),
    "config.env.SERVICE_BUS_NAMESPACE_FQDN": yaml_quote(f"sb-{environment_name}-{system_name}.servicebus.windows.net"),
    "config.env.AZURE_BLOB_ACCOUNT_URL": yaml_quote(f"https://{storage_account_name}.blob.core.windows.net/"),
    "config.env.AZURE_BLOB_CONTAINER": yaml_quote(blob_container_name),
    "config.env.REDIS_HOST": yaml_quote(redis_host),
    "config.env.REDIS_PORT": yaml_quote(str(redis_port)),
    "config.env.REDIS_SSL": yaml_quote("true"),
    "config.env.TRUST_PROXY_HEADERS": yaml_quote("true" if trusted_proxy_headers else "false"),
    "config.env.TRUSTED_PROXY_CIDRS": yaml_quote(",".join(trusted_proxy_cidrs)),
    "config.env.ENTRA_TENANT_ID": yaml_quote("00000000-0000-0000-0000-000000000000"),
    "config.env.ENTRA_CLIENT_ID": yaml_quote("00000000-0000-0000-0000-000000000000"),
    "config.env.ENTRA_INTERNAL_DOMAINS": yaml_quote("example.com"),
}

original = template_path.read_text(encoding="utf-8")
updated = update_values(original, replacements)
annotated = add_guidance_comments(updated)
output_path.write_text(annotated, encoding="utf-8")

print(f"[OK] backend values synced: {template_path} -> {output_path}")
