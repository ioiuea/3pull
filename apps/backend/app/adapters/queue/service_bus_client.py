"""
Azure Service Bus クライアント生成アダプタ.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient

from app.core.settings import get_settings


@lru_cache(maxsize=1)
def _get_default_credential() -> DefaultAzureCredential:
    """
    DefaultAzureCredential をキャッシュして返す.
    """
    return DefaultAzureCredential()


def _create_service_bus_client() -> ServiceBusClient:
    """
    Service Bus クライアントを生成する.
    """
    settings = get_settings()

    # ローカル切り分け用にだけ接続文字列を許可し、通常は Entra 認証へ寄せる。
    if settings.service_bus_use_connection_string:
        if not settings.service_bus_connection_string:
            raise RuntimeError(
                "SERVICE_BUS_CONNECTION_STRING is required when "
                "SERVICE_BUS_USE_CONNECTION_STRING=true"
            )
        return ServiceBusClient.from_connection_string(
            conn_str=settings.service_bus_connection_string
        )

    if not settings.service_bus_namespace_fqdn:
        raise RuntimeError(
            "SERVICE_BUS_NAMESPACE_FQDN is required when "
            "SERVICE_BUS_USE_CONNECTION_STRING=false"
        )

    # 本番の AKS では Workload Identity、ローカルでは az login を通じて認証される。
    return ServiceBusClient(
        fully_qualified_namespace=settings.service_bus_namespace_fqdn,
        credential=_get_default_credential(),
    )


@contextmanager
def get_service_bus_sender(*, queue_name: str) -> Iterator[Any]:
    """
    指定キュー向け sender を返す.
    """
    client = _create_service_bus_client()
    with client:
        # sender は client の文脈内でだけ有効なので、with をネストして寿命をそろえる。
        sender = client.get_queue_sender(queue_name=queue_name)
        with sender:
            yield sender


@contextmanager
def get_service_bus_receiver(
    *,
    queue_name: str,
    max_wait_time: int = 5,
) -> Iterator[Any]:
    """
    指定キュー向け receiver を返す.
    """
    client = _create_service_bus_client()
    with client:
        # max_wait_time は 1 回の receive が空振り時にどれだけ待つかを決める。
        receiver = client.get_queue_receiver(
            queue_name=queue_name,
            max_wait_time=max_wait_time,
        )
        with receiver:
            yield receiver
