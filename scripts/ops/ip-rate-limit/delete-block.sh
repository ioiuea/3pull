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

BEFORE_VALUE="$(redis_cli --raw GET "${REDIS_BLOCK_KEY}" || true)"
if [[ -z "${BEFORE_VALUE}" ]]; then
  echo "block_exists_before=false"
  echo "deleted_count=0"
  exit 0
fi

echo "block_exists_before=true"
echo "block_reason_before=${BEFORE_VALUE}"

DELETED_COUNT="$(redis_cli --raw DEL "${REDIS_BLOCK_KEY}")"
AFTER_VALUE="$(redis_cli --raw GET "${REDIS_BLOCK_KEY}" || true)"

echo "deleted_count=${DELETED_COUNT}"
if [[ -z "${AFTER_VALUE}" ]]; then
  echo "block_exists_after=false"
else
  echo "block_exists_after=true"
  echo "block_reason_after=${AFTER_VALUE}"
fi

