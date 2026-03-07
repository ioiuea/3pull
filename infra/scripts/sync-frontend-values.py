#!/usr/bin/env python3
"""infra の出力に合わせて frontend Helm values を更新する。"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path


def normalize_registry_suffix(value: str) -> str:
    """ACR 名に利用可能な文字へ正規化する（英小文字/数字のみ）。"""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def normalize_image_component(value: str) -> str:
    """コンテナイメージ名に使う文字へ正規化する。"""
    name = re.sub(r"[^a-z0-9-]", "-", value.lower())
    name = re.sub(r"-{2,}", "-", name).strip("-")
    return name or "app"


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
        replacement = replacements.get(path)

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
# 1. image.tag の `__IMAGE_TAG__` を CI で実際のタグに置き換えます
#    例: git sha やリリースタグ
# 2. 変更したファイルを使って `helm upgrade --install` を実行します
# -----------------------------------------------------------------------------
"""

    section_comments = [
        (
            "ingress:",
            "# Ingress 設定\n# frontend は通常系 App Gateway のみで公開する前提です。",
        ),
        (
            "frontend:",
            "# Frontend Deployment 設定\n# image.repository はインフラ側で自動更新されます。\n# image.tag は CI で毎回置き換えてください。",
        ),
        (
            "    host:",
            "    # 必須: frontend の公開ドメインへ置き換えてください",
        ),
    ]

    lines = content.splitlines()
    output_lines: list[str] = []
    inserted = set()

    output_lines.extend(header.rstrip("\n").splitlines())

    for line in lines:
        for anchor, comment in section_comments:
            if anchor in inserted:
                continue
            if line.startswith(anchor):
                output_lines.extend(comment.splitlines())
                inserted.add(anchor)
        output_lines.append(line)

    return "\n".join(output_lines) + "\n"


common_path = Path(os.environ["COMMON_FILE"])
template_path_raw = os.environ.get("TEMPLATE_FILE", "").strip()
output_path_raw = os.environ.get("OUTPUT_FILE", "").strip()
if not template_path_raw:
    raise SystemExit("TEMPLATE_FILE が必要です。")
if not output_path_raw:
    raise SystemExit("OUTPUT_FILE が必要です。")

template_path = Path(template_path_raw)
output_path = Path(output_path_raw)

common = json.loads(common_path.read_text(encoding="utf-8"))
common_values = common.get("common", {})

environment_name = str(common_values.get("environmentName", "")).strip()
system_name = str(common_values.get("systemName", "")).strip()
if not environment_name or not system_name:
    raise SystemExit("common.environmentName / common.systemName が必要です。")

if not template_path.exists():
    raise SystemExit(f"template values が見つかりません: {template_path}")

acr_name = f"cr{normalize_registry_suffix(environment_name)}{normalize_registry_suffix(system_name)}"
image_prefix = f"{acr_name}.azurecr.io"
system_image_name = normalize_image_component(system_name)
frontend_host = f"app-{environment_name}-{system_name}.example.com"

replacements = {
    "systemName": yaml_quote(system_name),
    "ingress.standard.host": yaml_quote(frontend_host),
    "frontend.image.repository": yaml_quote(f"{image_prefix}/{system_image_name}-web"),
    "frontend.image.tag": yaml_quote("__IMAGE_TAG__"),
}

original = template_path.read_text(encoding="utf-8")
updated = update_values(original, replacements)
annotated = add_guidance_comments(updated)
output_path.write_text(annotated, encoding="utf-8")

print(f"[OK] frontend values synced: {template_path} -> {output_path}")
