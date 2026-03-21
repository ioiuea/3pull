#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_common.sh
source "${SCRIPT_DIR}/_common.sh"

parse_common_args "$@"

echo "redis_host=${REDIS_HOST_ARG}"
echo "redis_port=${REDIS_PORT_ARG}"
echo "policy_key=${POLICY_KEY}"
echo "client_ip=${CLIENT_IP}"
echo "block_key=${REDIS_BLOCK_KEY}"

VALUE="$(redis_cli --raw GET "${REDIS_BLOCK_KEY}" || true)"
TTL="$(redis_cli --raw TTL "${REDIS_BLOCK_KEY}" || true)"

if [[ -z "${VALUE}" ]]; then
  echo "block_exists=false"
else
  echo "block_exists=true"
  echo "block_reason=${VALUE}"
fi

if [[ -n "${TTL}" ]]; then
  echo "block_ttl_seconds=${TTL}"
fi

