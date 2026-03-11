#!/usr/bin/env python3
"""Interactive VM size selector for infra/main.sh.

Expected environment variables:
- LOCATION
- CURRENT_AGENT_VM_SIZE
- CURRENT_USER_VM_SIZE
- CURRENT_MAINT_VM_SIZE
- OUT_FILE
- OUT_CATALOG_FILE (optional)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Any

ALLOWED_FAMILIES = [
    "Standard_D2s",
    "Standard_D2as",
    "Standard_D4s",
    "Standard_D4as",
    "Standard_D8s",
    "Standard_D8as",
    "Standard_D16s",
    "Standard_D16as",
    "Standard_D32s",
    "Standard_D32as",
    "Standard_D48s",
    "Standard_D48as",
    "Standard_D64s",
    "Standard_D64as",
    "Standard_D96s",
    "Standard_D96as",
]
FAMILY_ORDER = {name: idx for idx, name in enumerate(ALLOWED_FAMILIES)}


def eprint(msg: str) -> None:
    sys.stderr.write(msg + "\n")


def cap_value(item: dict[str, Any], key: str) -> str:
    caps = item.get("capabilities") or []
    for cap in caps:
        if not isinstance(cap, dict):
            continue
        if str(cap.get("name", "")).strip() == key:
            return str(cap.get("value", "")).strip()
    return ""


def zones_for_location(item: dict[str, Any], location: str) -> list[str]:
    infos = item.get("locationInfo") or []
    target = location.lower()
    for info in infos:
        if not isinstance(info, dict):
            continue
        loc = str(info.get("location", "")).strip().lower()
        if loc == target:
            return [str(z) for z in (info.get("zones") or [])]
    for info in infos:
        if not isinstance(info, dict):
            continue
        zones = info.get("zones") or []
        if zones:
            return [str(z) for z in zones]
    return []


def is_region_unavailable(item: dict[str, Any]) -> bool:
    restrictions = item.get("restrictions") or []
    for restriction in restrictions:
        if not isinstance(restriction, dict):
            continue
        if restriction.get("reasonCode") != "NotAvailableForSubscription":
            continue
        info = restriction.get("restrictionInfo") or {}
        zones = info.get("zones") or restriction.get("values") or []
        # zones 指定なしの NotAvailableForSubscription はリージョン全体で不可とみなす。
        if not zones:
            return True
    return False


def build_catalog(location: str) -> list[dict[str, Any]]:
    cmd = [
        "az",
        "vm",
        "list-skus",
        "--location",
        location,
        "--resource-type",
        "virtualMachines",
        "--all",
        "-o",
        "json",
        "--only-show-errors",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        eprint("VM SKU 一覧の取得に失敗しました。")
        eprint(result.stderr.strip())
        raise SystemExit(1)

    try:
        rows = json.loads(result.stdout or "[]")
    except Exception:
        eprint("VM SKU 一覧の JSON 解析に失敗しました。")
        raise SystemExit(1)

    if not isinstance(rows, list) or not rows:
        eprint("VM SKU 一覧が空です。")
        raise SystemExit(1)

    catalog: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        if not name or name in seen:
            continue
        if is_region_unavailable(row):
            continue
        seen.add(name)
        catalog.append(
            {
                "name": name,
                "vcpus": cap_value(row, "vCPUs") or "-",
                "memory_gb": cap_value(row, "MemoryGB") or "-",
                "max_data_disks": cap_value(row, "MaxDataDiskCount") or "-",
                "zones": zones_for_location(row, location),
            }
        )

    catalog.sort(key=lambda x: x["name"].lower())
    if not catalog:
        eprint("利用可能な VM SKU が見つかりませんでした。")
        raise SystemExit(1)
    return catalog


def sku_family(name: str) -> str:
    for family in ALLOWED_FAMILIES:
        if name.startswith(family + "_") or name == family:
            return family
    return ""


def pick_allowed_catalog(catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered = []
    for item in catalog:
        name = str(item.get("name", ""))
        family = sku_family(name)
        if not family:
            continue
        copied = dict(item)
        copied["family"] = family
        filtered.append(copied)
    filtered.sort(
        key=lambda x: (
            FAMILY_ORDER.get(str(x["family"]), 9999),
            -extract_version(str(x["name"])),
            str(x["name"]).lower(),
        )
    )
    return filtered


def extract_version(name: str) -> int:
    # 例: Standard_D4s_v5 -> 5
    match = re.search(r"_v(\d+)\b", name, flags=re.IGNORECASE)
    if not match:
        return 0
    try:
        return int(match.group(1))
    except Exception:
        return 0


def resolve_recommended_name(candidates: list[dict[str, Any]], recommended_family: str) -> str:
    family_items = [c for c in candidates if str(c.get("family", "")) == recommended_family]
    if not family_items:
        return ""
    best = max(
        family_items,
        key=lambda x: (extract_version(str(x.get("name", ""))), str(x.get("name", ""))),
    )
    return str(best.get("name", ""))


def print_catalog(location: str, filtered: list[dict[str, Any]], recommended_name: str) -> None:
    print("")
    print(f"候補一覧 (location={location}, count={len(filtered)})")
    print(" idx | name                          | vCPU | Memory(GB) | MaxDataDisk | Zones           | Note")
    print("-----+-------------------------------+------+------------+-------------+-----------------+----------------")
    for idx, item in enumerate(filtered, start=1):
        zones = ",".join(item["zones"]) if item["zones"] else "-"
        note = "Recommended" if str(item.get("name", "")) == recommended_name else ""
        print(
            f"{idx:>4} | "
            f"{item['name'][:29]:<29} | "
            f"{str(item['vcpus'])[:4]:>4} | "
            f"{str(item['memory_gb'])[:10]:>10} | "
            f"{str(item['max_data_disks'])[:11]:>11} | "
            f"{zones[:15]:<15} | "
            f"{note}"
        )
    print("")


def prompt_choice(
    label: str,
    candidates: list[dict[str, Any]],
    location: str,
    current_name: str,
    recommended_family: str,
    guidance: str,
) -> str:
    recommended_name = resolve_recommended_name(candidates, recommended_family)
    print("")
    print(f"{label}: {guidance}")
    print_catalog(location, candidates, recommended_name)

    current_idx = None
    current_lower = current_name.strip().lower()
    if current_lower:
        for i, item in enumerate(candidates, start=1):
            if item["name"].lower() == current_lower:
                current_idx = i
                break

    recommended_idx = None
    for i, item in enumerate(candidates, start=1):
        if str(item.get("name", "")) == recommended_name:
            recommended_idx = i
            break

    while True:
        if current_idx is not None:
            prompt = f"{label} を選択 [1-{len(candidates)}] (Enterで現在値: {current_name}): "
        elif recommended_idx is not None:
            recommended_name = candidates[recommended_idx - 1]["name"]
            prompt = f"{label} を選択 [1-{len(candidates)}] (Enterで推奨: {recommended_name}): "
        else:
            prompt = f"{label} を選択 [1-{len(candidates)}]: "

        raw = input(prompt).strip()
        if raw == "":
            if current_idx is not None:
                return candidates[current_idx - 1]["name"]
            if recommended_idx is not None:
                return candidates[recommended_idx - 1]["name"]
            print("番号入力が必要です。")
            continue
        if not raw.isdigit():
            print("番号で入力してください。")
            continue
        idx = int(raw)
        if 1 <= idx <= len(candidates):
            return candidates[idx - 1]["name"]
        print(f"1 から {len(candidates)} の範囲で入力してください。")


def main() -> int:
    location = os.environ.get("LOCATION", "").strip()
    out_file = os.environ.get("OUT_FILE", "").strip()
    out_catalog_file = os.environ.get("OUT_CATALOG_FILE", "").strip()
    current_agent = os.environ.get("CURRENT_AGENT_VM_SIZE", "").strip()
    current_user = os.environ.get("CURRENT_USER_VM_SIZE", "").strip()
    current_maint = os.environ.get("CURRENT_MAINT_VM_SIZE", "").strip()

    if not location or not out_file:
        eprint("必要な環境変数が不足しています。")
        return 1

    catalog = build_catalog(location)
    candidates = pick_allowed_catalog(catalog)
    if not candidates:
        eprint("指定の D シリーズ(s/as)候補が見つかりませんでした。")
        return 1

    print("固定フィルタ: D シリーズ (s/as)")
    print("対象: " + ", ".join(ALLOWED_FAMILIES))

    selected_agent = prompt_choice(
        "AKS agentPoolVmSize",
        candidates,
        location,
        current_agent,
        "Standard_D2s",
        "Standard_D2s 系を推奨",
    )
    selected_user = prompt_choice(
        "AKS userPoolVmSize",
        candidates,
        location,
        current_user,
        "Standard_D4s",
        "アプリ要件に合わせて選択（標準は Standard_D4s 系）",
    )
    selected_maint = prompt_choice(
        "Maintenance VM maintVmSize",
        candidates,
        location,
        current_maint,
        "Standard_D4as",
        "Standard_D4as 系を推奨",
    )

    by_name = {str(item["name"]): item for item in candidates}
    agent_item = by_name.get(selected_agent, {})
    user_item = by_name.get(selected_user, {})
    maint_item = by_name.get(selected_maint, {})

    print("")
    print("選択結果:")
    print(f"  - agentPoolVmSize: {selected_agent}")
    print(f"  - userPoolVmSize: {selected_user}")
    print(f"  - maintVmSize: {selected_maint}")
    while True:
        confirm = input("この内容で続行しますか? [Y/n]: ").strip()
        lowered = confirm.lower()
        if lowered in ("", "y", "yes"):
            break
        if lowered in ("n", "no"):
            eprint("ユーザーキャンセルにより終了します。")
            return 1
        print("無効な入力です。y/yes か n/no を入力してください。")

    selection = {
        "agentPoolVmSize": selected_agent,
        "userPoolVmSize": selected_user,
        "maintVmSize": selected_maint,
        "agentPoolZones": [str(z) for z in (agent_item.get("zones") or [])],
        "userPoolZones": [str(z) for z in (user_item.get("zones") or [])],
        "maintVmZones": [str(z) for z in (maint_item.get("zones") or [])],
        "location": location,
    }
    with open(out_file, "w", encoding="utf-8") as fp:
        json.dump(selection, fp, ensure_ascii=False, indent=2)
        fp.write("\n")

    if out_catalog_file:
        with open(out_catalog_file, "w", encoding="utf-8") as fp:
            json.dump(
                {
                    "location": location,
                    "allowedFamilies": ALLOWED_FAMILIES,
                    "candidates": candidates,
                },
                fp,
                ensure_ascii=False,
                indent=2,
            )
            fp.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
