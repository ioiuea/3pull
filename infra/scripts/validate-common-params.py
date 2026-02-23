#!/usr/bin/env python3
"""infra/common.parameter.json の入力値を事前検証する。

方針:
- ここで共通パラメータを先に検証し、後続の各 generate スクリプトでは
  正常系処理に集中できるようにする。
- 不正値がある場合は理由を一覧表示し、main.sh の実処理を停止する。
"""

from __future__ import annotations

import ipaddress
import json
import math
import sys
from pathlib import Path


def parse_json(path: Path):
    """JSON ファイルを読み込み、構文エラー時は終了コード 1 で停止する。"""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"[ERROR] common parameter file が見つかりません: {path}", file=sys.stderr)
        raise SystemExit(1)
    except json.JSONDecodeError as exc:
        print(f"[ERROR] common parameter file の JSON 形式が不正です: {path}", file=sys.stderr)
        print(f"        {exc}", file=sys.stderr)
        raise SystemExit(1)


def as_bool(value, key: str, errors: list[str]):
    """bool を期待するキーの型検証を行う。"""
    if isinstance(value, bool):
        return value
    errors.append(f"{key}: true/false で指定してください。")
    return None


def as_non_empty_str(value, key: str, errors: list[str]):
    """空文字でない文字列かどうかを検証する。"""
    if isinstance(value, str) and value.strip() != "":
        return value.strip()
    errors.append(f"{key}: 空でない文字列を指定してください。")
    return None


def as_optional_ip_or_cidr(value, key: str, errors: list[str]):
    """任意入力の IPv4/CIDR 文字列を検証する。空文字は未指定扱い。"""
    if value == "":
        return None
    if not isinstance(value, str):
        errors.append(f"{key}: IPv4 アドレス/CIDR 文字列か空文字を指定してください。")
        return None
    try:
        if "/" in value:
            ipaddress.ip_network(value, strict=True)
        else:
            ipaddress.ip_address(value)
    except ValueError:
        errors.append(f"{key}: 有効な IP アドレスまたは CIDR 形式ではありません。指定値={value!r}")
        return None
    return value


def as_optional_ip(value, key: str, errors: list[str]):
    """任意入力の IPv4 文字列を検証する。空文字は未指定扱い。"""
    if value == "":
        return None
    if not isinstance(value, str):
        errors.append(f"{key}: IPv4 アドレス文字列か空文字を指定してください。")
        return None
    try:
        ipaddress.ip_address(value)
    except ValueError:
        errors.append(f"{key}: 有効な IP アドレス形式ではありません。指定値={value!r}")
        return None
    return value


def as_cidr(value, key: str, errors: list[str]):
    """必須 CIDR 文字列を検証し、正常時は ip_network を返す。"""
    if not isinstance(value, str) or value.strip() == "":
        errors.append(f"{key}: x.x.x.x/xx 形式の CIDR を指定してください。")
        return None
    try:
        return ipaddress.ip_network(value, strict=True)
    except ValueError:
        errors.append(f"{key}: 有効な CIDR 形式ではありません。指定値={value!r}")
        return None


def as_int(value, key: str, errors: list[str]):
    """整数値を検証する（bool は int として扱わない）。"""
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{key}: 整数を指定してください。")
        return None
    return value


def main() -> int:
    """エントリポイント。検証結果に応じた終了コードを返す。"""
    if len(sys.argv) != 2:
        print("Usage: validate-common-params.py <common.parameter.json>", file=sys.stderr)
        return 2

    common_path = Path(sys.argv[1])
    common = parse_json(common_path)

    errors: list[str] = []

    if not isinstance(common, dict):
        print("[ERROR] common parameter file のトップレベルは object である必要があります。", file=sys.stderr)
        return 1

    common_values = common.get("common")
    network_values = common.get("network")
    aks_values = common.get("aks")
    postgres_values = common.get("postgres")
    redis_values = common.get("redis")
    cosno_values = common.get("cosno")

    if not isinstance(common_values, dict):
        errors.append("common: object で指定してください。")
        common_values = {}
    if not isinstance(network_values, dict):
        errors.append("network: object で指定してください。")
        network_values = {}
    if not isinstance(aks_values, dict):
        errors.append("aks: object で指定してください。")
        aks_values = {}
    if not isinstance(postgres_values, dict):
        errors.append("postgres: object で指定してください。")
        postgres_values = {}
    if not isinstance(redis_values, dict):
        errors.append("redis: object で指定してください。")
        redis_values = {}
    if not isinstance(cosno_values, dict):
        errors.append("cosno: object で指定してください。")
        cosno_values = {}

    # 基本識別子
    as_non_empty_str(common_values.get("location"), "common.location", errors)
    as_non_empty_str(common_values.get("environmentName"), "common.environmentName", errors)
    as_non_empty_str(common_values.get("systemName"), "common.systemName", errors)
    as_bool(common_values.get("enableResourceLock"), "common.enableResourceLock", errors)

    # ネットワーク/セキュリティ系のフラグ
    as_bool(network_values.get("enableFirewallIdps"), "network.enableFirewallIdps", errors)
    enable_ddos = as_bool(network_values.get("enableDdosProtection"), "network.enableDdosProtection", errors)
    as_bool(
        network_values.get("enableGatewayRoutePropagation"),
        "network.enableGatewayRoutePropagation",
        errors,
    )
    as_bool(
        network_values.get("enableCentralizedPrivateDns"),
        "network.enableCentralizedPrivateDns",
        errors,
    )

    ddos_plan_id = network_values.get("ddosProtectionPlanId")
    if not isinstance(ddos_plan_id, str):
        errors.append("network.ddosProtectionPlanId: 文字列で指定してください（未指定は空文字）。")
    elif enable_ddos and ddos_plan_id and not ddos_plan_id.startswith("/subscriptions/"):
        errors.append(
            "network.ddosProtectionPlanId: 指定時は Azure リソース ID 形式（/subscriptions/...）で指定してください。"
        )

    # VNET アドレス空間の検証（形式と重複チェック）
    vnet_prefixes_raw = network_values.get("vnetAddressPrefixes")
    vnet_prefixes: list[ipaddress._BaseNetwork] = []
    if not isinstance(vnet_prefixes_raw, list) or not vnet_prefixes_raw:
        errors.append("network.vnetAddressPrefixes: 1件以上の CIDR 配列で指定してください。")
    else:
        for i, raw in enumerate(vnet_prefixes_raw):
            net = as_cidr(raw, f"network.vnetAddressPrefixes[{i}]", errors)
            if net is not None:
                vnet_prefixes.append(net)

        for i in range(len(vnet_prefixes)):
            for j in range(i + 1, len(vnet_prefixes)):
                if vnet_prefixes[i].overlaps(vnet_prefixes[j]):
                    errors.append(
                        "network.vnetAddressPrefixes: レンジが重複しています "
                        f"({vnet_prefixes[i]} と {vnet_prefixes[j]})"
                    )

    # 任意指定 IP
    as_optional_ip(network_values.get("egressNextHopIp", ""), "network.egressNextHopIp", errors)
    as_optional_ip_or_cidr(network_values.get("sharedBastionIp", ""), "network.sharedBastionIp", errors)
    vnet_dns_servers = network_values.get("vnetDnsServers")
    if not isinstance(vnet_dns_servers, list):
        errors.append("network.vnetDnsServers: IPv4 アドレス配列で指定してください（未指定は空配列）。")
    else:
        for i, raw in enumerate(vnet_dns_servers):
            as_optional_ip(raw, f"network.vnetDnsServers[{i}]", errors)

    # AKS user pool 設定
    as_non_empty_str(aks_values.get("userPoolVmSize"), "aks.userPoolVmSize", errors)
    count = as_int(aks_values.get("userPoolCount"), "aks.userPoolCount", errors)
    min_count = as_int(aks_values.get("userPoolMinCount"), "aks.userPoolMinCount", errors)
    max_count = as_int(aks_values.get("userPoolMaxCount"), "aks.userPoolMaxCount", errors)
    as_non_empty_str(aks_values.get("userPoolLabel"), "aks.userPoolLabel", errors)

    if count is not None and count < 0:
        errors.append("aks.userPoolCount: 0 以上を指定してください。")
    if min_count is not None and min_count < 0:
        errors.append("aks.userPoolMinCount: 0 以上を指定してください。")
    if max_count is not None and max_count < 0:
        errors.append("aks.userPoolMaxCount: 0 以上を指定してください。")

    if count is not None and min_count is not None and max_count is not None:
        if not (min_count <= count <= max_count):
                errors.append(
                "aks.userPoolCount / aks.userPoolMinCount / "
                "aks.userPoolMaxCount: min <= count <= max を満たしてください。"
            )

    # AKS ネットワーク設定
    pod_cidr = as_cidr(aks_values.get("podCidr"), "aks.podCidr", errors)
    service_cidr = as_cidr(aks_values.get("serviceCidr"), "aks.serviceCidr", errors)

    if service_cidr is not None:
        host_count = sum(1 for _ in service_cidr.hosts())
        if host_count < 10:
            errors.append("aks.serviceCidr: DNS service IP 算出のため、利用可能 IP が 10 個以上必要です。")

    if pod_cidr is not None and service_cidr is not None and pod_cidr.overlaps(service_cidr):
        errors.append("aks.podCidr と aks.serviceCidr は重複できません。")

    if service_cidr is not None:
        for vnet in vnet_prefixes:
            if service_cidr.overlaps(vnet):
                errors.append(
                    "aks.serviceCidr は network.vnetAddressPrefixes と重複できません: "
                    f"serviceCidr={service_cidr}, vnet={vnet}"
                )

    # PostgreSQL 設定
    sku_tier = as_non_empty_str(postgres_values.get("skuTier"), "postgres.skuTier", errors)
    if sku_tier is not None and sku_tier not in ["Burstable", "GeneralPurpose", "MemoryOptimized"]:
        errors.append(
            "postgres.skuTier: Burstable / GeneralPurpose / MemoryOptimized のいずれかを指定してください。"
        )

    as_non_empty_str(postgres_values.get("skuName"), "postgres.skuName", errors)

    storage_size_gb = as_int(postgres_values.get("storageSizeGB"), "postgres.storageSizeGB", errors)
    if storage_size_gb is not None and storage_size_gb < 32:
        errors.append("postgres.storageSizeGB: 32 以上の整数を指定してください。")

    as_bool(postgres_values.get("enableStorageAutoGrow"), "postgres.enableStorageAutoGrow", errors)
    as_bool(postgres_values.get("enableZoneRedundantHa"), "postgres.enableZoneRedundantHa", errors)
    as_bool(
        postgres_values.get("enableGeoRedundantBackup"),
        "postgres.enableGeoRedundantBackup",
        errors,
    )
    backup_retention_days = as_int(postgres_values.get("backupRetentionDays"), "postgres.backupRetentionDays", errors)
    if backup_retention_days is not None and not (7 <= backup_retention_days <= 35):
        errors.append("postgres.backupRetentionDays: 7〜35 の範囲で指定してください。")

    enable_custom_mw = as_bool(
        postgres_values.get("enableCustomMaintenanceWindow"),
        "postgres.enableCustomMaintenanceWindow",
        errors,
    )
    maintenance_window = postgres_values.get("maintenanceWindow")
    if enable_custom_mw:
        if not isinstance(maintenance_window, dict):
            errors.append(
                "postgres.maintenanceWindow: object で指定してください。"
                "（enableCustomMaintenanceWindow=true の場合は必須）"
            )
        else:
            day_of_week = as_int(
                maintenance_window.get("dayOfWeek"),
                "postgres.maintenanceWindow.dayOfWeek",
                errors,
            )
            start_hour = as_int(
                maintenance_window.get("startHour"),
                "postgres.maintenanceWindow.startHour",
                errors,
            )
            start_minute = as_int(
                maintenance_window.get("startMinute"),
                "postgres.maintenanceWindow.startMinute",
                errors,
            )

            if day_of_week is not None and not (0 <= day_of_week <= 6):
                errors.append("postgres.maintenanceWindow.dayOfWeek: 0〜6 の範囲で指定してください。")
            if start_hour is not None and not (0 <= start_hour <= 23):
                errors.append("postgres.maintenanceWindow.startHour: 0〜23 の範囲で指定してください。")
            if start_minute is not None and not (0 <= start_minute <= 59):
                errors.append("postgres.maintenanceWindow.startMinute: 0〜59 の範囲で指定してください。")

    # Redis メンテナンスウィンドウ設定
    redis_sku_name = as_non_empty_str(
        redis_values.get("skuName"),
        "redis.skuName",
        errors,
    )
    if redis_sku_name is not None and redis_sku_name not in ["Basic", "Standard", "Premium"]:
        errors.append("redis.skuName: Basic / Standard / Premium のいずれかを指定してください。")

    redis_capacity = as_int(
        redis_values.get("capacity"),
        "redis.capacity",
        errors,
    )
    if redis_capacity is not None and redis_capacity < 0:
        errors.append("redis.capacity: 0 以上の整数を指定してください。")

    redis_shard_count = as_int(
        redis_values.get("shardCount"),
        "redis.shardCount",
        errors,
    )
    if redis_shard_count is not None and redis_shard_count < 1:
        errors.append("redis.shardCount: 1 以上の整数を指定してください。")

    redis_scale_strategy = as_non_empty_str(
        redis_values.get("scaleStrategy"),
        "redis.scaleStrategy",
        errors,
    )
    if redis_scale_strategy is not None and redis_scale_strategy not in ["vertical", "horizontal"]:
        errors.append("redis.scaleStrategy: vertical / horizontal のいずれかを指定してください。")

    if redis_sku_name in ["Basic", "Standard"]:
        if redis_capacity is not None and not (0 <= redis_capacity <= 6):
            errors.append("redis.capacity: Basic/Standard の場合は 0〜6 を指定してください。")
    elif redis_sku_name == "Premium":
        if redis_capacity is not None and not (1 <= redis_capacity <= 6):
            errors.append("redis.capacity: Premium の場合は 1〜6 を指定してください。")

    redis_zonal_allocation_policy = as_non_empty_str(
        redis_values.get("zonalAllocationPolicy"),
        "redis.zonalAllocationPolicy",
        errors,
    )
    if redis_zonal_allocation_policy is not None and redis_zonal_allocation_policy not in [
        "Automatic",
        "NoZones",
        "UserDefined",
    ]:
        errors.append("redis.zonalAllocationPolicy: Automatic / NoZones / UserDefined のいずれかを指定してください。")

    redis_zones = redis_values.get("zones")
    if not isinstance(redis_zones, list):
        errors.append("redis.zones: ゾーン番号文字列の配列で指定してください（未指定は空配列）。")
        redis_zones = []
    else:
        for i, zone in enumerate(redis_zones):
            if not isinstance(zone, str) or zone not in ["1", "2", "3"]:
                errors.append(f"redis.zones[{i}]: '1' / '2' / '3' のいずれかを指定してください。")

    redis_replicas_per_master = as_int(
        redis_values.get("replicasPerMaster"),
        "redis.replicasPerMaster",
        errors,
    )
    if redis_replicas_per_master is not None and redis_replicas_per_master < 0:
        errors.append("redis.replicasPerMaster: 0 以上の整数を指定してください。")

    redis_enable_geo_replication = as_bool(
        redis_values.get("enableGeoReplication"),
        "redis.enableGeoReplication",
        errors,
    )
    redis_enable_microsoft_entra_authentication = as_bool(
        redis_values.get("enableMicrosoftEntraAuthentication"),
        "redis.enableMicrosoftEntraAuthentication",
        errors,
    )
    as_bool(
        redis_values.get("disableAccessKeyAuthentication"),
        "redis.disableAccessKeyAuthentication",
        errors,
    )

    if redis_zonal_allocation_policy == "UserDefined":
        if redis_sku_name != "Premium":
            errors.append("redis.zonalAllocationPolicy=UserDefined は redis.skuName=Premium の場合のみ指定できます。")
        if len(redis_zones) == 0:
            errors.append("redis.zonalAllocationPolicy=UserDefined の場合は redis.zones を1件以上指定してください。")
    elif len(redis_zones) > 0:
        errors.append("redis.zones は redis.zonalAllocationPolicy=UserDefined の場合のみ指定できます。")

    if redis_enable_geo_replication:
        if redis_sku_name != "Premium":
            errors.append("redis.enableGeoReplication=true は redis.skuName=Premium の場合のみ指定できます。")
        if redis_replicas_per_master is not None and redis_replicas_per_master != 1:
            errors.append("redis.enableGeoReplication=true の場合は redis.replicasPerMaster=1 を指定してください。")

    if (
        redis_values.get("disableAccessKeyAuthentication") is True
        and redis_enable_microsoft_entra_authentication is False
    ):
        errors.append(
            "redis.disableAccessKeyAuthentication=true の場合は "
            "redis.enableMicrosoftEntraAuthentication=true を指定してください。"
        )

    redis_enable_custom_mw = as_bool(
        redis_values.get("enableCustomMaintenanceWindow"),
        "redis.enableCustomMaintenanceWindow",
        errors,
    )
    redis_maintenance_window = redis_values.get("maintenanceWindow")
    if redis_enable_custom_mw:
        if not isinstance(redis_maintenance_window, dict):
            errors.append(
                "redis.maintenanceWindow: object で指定してください。"
                "（enableCustomMaintenanceWindow=true の場合は必須）"
            )
        else:
            day_of_week = as_int(
                redis_maintenance_window.get("dayOfWeek"),
                "redis.maintenanceWindow.dayOfWeek",
                errors,
            )
            start_hour = as_int(
                redis_maintenance_window.get("startHour"),
                "redis.maintenanceWindow.startHour",
                errors,
            )
            duration = redis_maintenance_window.get("duration")

            if day_of_week is not None and not (0 <= day_of_week <= 6):
                errors.append("redis.maintenanceWindow.dayOfWeek: 0〜6 の範囲で指定してください。")
            if start_hour is not None and not (0 <= start_hour <= 23):
                errors.append("redis.maintenanceWindow.startHour: 0〜23 の範囲で指定してください。")
            if not isinstance(duration, str) or not duration.startswith("PT") or not duration.endswith("H"):
                errors.append("redis.maintenanceWindow.duration: ISO 8601 形式の時間（例: PT5H）で指定してください。")

    redis_enable_rdb_backup = as_bool(
        redis_values.get("enableRdbBackup"),
        "redis.enableRdbBackup",
        errors,
    )
    redis_rdb_backup_frequency = as_int(
        redis_values.get("rdbBackupFrequencyInMinutes"),
        "redis.rdbBackupFrequencyInMinutes",
        errors,
    )
    redis_rdb_backup_max_snapshot_count = as_int(
        redis_values.get("rdbBackupMaxSnapshotCount"),
        "redis.rdbBackupMaxSnapshotCount",
        errors,
    )
    redis_rdb_storage_connection_string = redis_values.get("rdbStorageConnectionString")
    if not isinstance(redis_rdb_storage_connection_string, str):
        errors.append("redis.rdbStorageConnectionString: 文字列で指定してください。")

    if redis_rdb_backup_frequency is not None and redis_rdb_backup_frequency not in [15, 30, 60, 360, 720, 1440]:
        errors.append(
            "redis.rdbBackupFrequencyInMinutes: 15 / 30 / 60 / 360 / 720 / 1440 のいずれかを指定してください。"
        )

    if redis_rdb_backup_max_snapshot_count is not None and redis_rdb_backup_max_snapshot_count < 1:
        errors.append("redis.rdbBackupMaxSnapshotCount: 1 以上の整数を指定してください。")

    if redis_enable_rdb_backup:
        if redis_sku_name != "Premium":
            # Basic/Standard では実装側で無視するため、ここでは停止させない。
            redis_enable_rdb_backup = False

    if redis_enable_rdb_backup:
        if isinstance(redis_rdb_storage_connection_string, str) and redis_rdb_storage_connection_string.strip() == "":
            errors.append(
                "redis.rdbStorageConnectionString: redis.enableRdbBackup=true の場合は保存先ストレージ接続文字列を指定してください。"
            )

    # Cosmos DB(NoSQL) スループット設定
    throughput_mode = as_non_empty_str(
        cosno_values.get("throughputMode"),
        "cosno.throughputMode",
        errors,
    )
    if throughput_mode is not None and throughput_mode not in ["Manual", "Autoscale", "Serverless"]:
        errors.append("cosno.throughputMode: Manual / Autoscale / Serverless のいずれかを指定してください。")

    manual_throughput = as_int(
        cosno_values.get("manualThroughputRu"),
        "cosno.manualThroughputRu",
        errors,
    )
    if manual_throughput is not None and manual_throughput < 400:
        errors.append("cosno.manualThroughputRu: 400 以上の整数を指定してください。")

    autoscale_max_throughput = as_int(
        cosno_values.get("autoscaleMaxThroughputRu"),
        "cosno.autoscaleMaxThroughputRu",
        errors,
    )
    if autoscale_max_throughput is not None and autoscale_max_throughput < 1000:
        errors.append("cosno.autoscaleMaxThroughputRu: 1000 以上の整数を指定してください。")

    # Cosmos DB(NoSQL) バックアップ設定
    backup_policy_type = as_non_empty_str(cosno_values.get("backupPolicyType"), "cosno.backupPolicyType", errors)
    if backup_policy_type is not None and backup_policy_type not in ["Periodic", "Continuous"]:
        errors.append("cosno.backupPolicyType: Periodic または Continuous を指定してください。")

    periodic_interval = as_int(
        cosno_values.get("periodicBackupIntervalInMinutes"),
        "cosno.periodicBackupIntervalInMinutes",
        errors,
    )
    if periodic_interval is not None and not (60 <= periodic_interval <= 1440):
        errors.append("cosno.periodicBackupIntervalInMinutes: 60〜1440 の範囲で指定してください。")

    periodic_retention = as_int(
        cosno_values.get("periodicBackupRetentionIntervalInHours"),
        "cosno.periodicBackupRetentionIntervalInHours",
        errors,
    )
    if periodic_retention is not None and not (8 <= periodic_retention <= 720):
        errors.append("cosno.periodicBackupRetentionIntervalInHours: 8〜720 の範囲で指定してください。")

    periodic_redundancy = as_non_empty_str(
        cosno_values.get("periodicBackupStorageRedundancy"),
        "cosno.periodicBackupStorageRedundancy",
        errors,
    )
    if periodic_redundancy is not None and periodic_redundancy not in ["Geo", "Local", "Zone"]:
        errors.append("cosno.periodicBackupStorageRedundancy: Geo / Local / Zone のいずれかを指定してください。")

    continuous_tier = as_non_empty_str(
        cosno_values.get("continuousBackupTier"),
        "cosno.continuousBackupTier",
        errors,
    )
    if continuous_tier is not None and continuous_tier not in ["Continuous7Days", "Continuous30Days"]:
        errors.append("cosno.continuousBackupTier: Continuous7Days / Continuous30Days のいずれかを指定してください。")

    if backup_policy_type == "Periodic" and periodic_interval is not None and periodic_retention is not None:
        min_retention_hours = math.ceil((periodic_interval * 2) / 60)
        if periodic_retention < min_retention_hours:
            errors.append(
                "cosno.periodicBackupRetentionIntervalInHours: "
                "periodicBackupIntervalInMinutes の2倍以上の保持時間を指定してください。"
            )

    failover_regions = cosno_values.get("failoverRegions")
    if not isinstance(failover_regions, list):
        errors.append("cosno.failoverRegions: 文字列配列で指定してください（未指定は空配列）。")
    else:
        for i, region in enumerate(failover_regions):
            if not isinstance(region, str) or region.strip() == "":
                errors.append(f"cosno.failoverRegions[{i}]: 空でないリージョン名文字列を指定してください。")

    as_bool(
        cosno_values.get("enableAutomaticFailover"),
        "cosno.enableAutomaticFailover",
        errors,
    )
    as_bool(
        cosno_values.get("enableMultipleWriteLocations"),
        "cosno.enableMultipleWriteLocations",
        errors,
    )
    as_bool(
        cosno_values.get("disableLocalAuth"),
        "cosno.disableLocalAuth",
        errors,
    )
    as_bool(
        cosno_values.get("disableKeyBasedMetadataWriteAccess"),
        "cosno.disableKeyBasedMetadataWriteAccess",
        errors,
    )

    consistency_level = as_non_empty_str(
        cosno_values.get("consistencyLevel"),
        "cosno.consistencyLevel",
        errors,
    )
    if consistency_level is not None and consistency_level not in [
        "Strong",
        "BoundedStaleness",
        "Session",
        "ConsistentPrefix",
        "Eventual",
    ]:
        errors.append(
            "cosno.consistencyLevel: "
            "Strong / BoundedStaleness / Session / ConsistentPrefix / Eventual のいずれかを指定してください。"
        )

    # リソース実行トグル
    toggles = common.get("resourceToggles")
    expected_toggle_keys = [
        "logAnalytics",
        "applicationInsights",
        "virtualNetwork",
        "subnets",
        "firewall",
        "applicationGateway",
        "acr",
        "storage",
        "redis",
        "cosmosDatabase",
        "postgresDatabase",
        "keyVault",
        "aks",
        "maintenanceVm",
    ]
    if not isinstance(toggles, dict):
        errors.append("resourceToggles: object で指定してください。")
    else:
        for key in expected_toggle_keys:
            if key not in toggles:
                errors.append(f"resourceToggles.{key}: 未設定です。true/false を指定してください。")
            elif not isinstance(toggles[key], bool):
                errors.append(f"resourceToggles.{key}: true/false で指定してください。")

    if errors:
        print("[ERROR] infra/common.parameter.json に不正な値があります。修正して再実行してください。", file=sys.stderr)
        for msg in errors:
            print(f"  - {msg}", file=sys.stderr)
        return 1

    print(f"[OK] common parameters validated: {common_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
