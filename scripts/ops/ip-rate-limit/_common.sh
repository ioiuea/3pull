#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
generated_env_file="$script_dir/generated.env.sh"
if [[ -f "$generated_env_file" ]]; then
  # shellcheck source=/dev/null
  source "$generated_env_file"
fi

REDIS_PORT_DEFAULT="${REDIS_PORT:-10000}"
REDIS_RESOURCE="https://redis.azure.com"

usage_common() {
  cat <<'EOF'
Required arguments:
  --policy-key <policy_key>   e.g. email_login
  --client-ip <client_ip>     e.g. 127.0.0.1

Optional arguments:
  --auth-mode <user|mi>       default: $REDIS_AUTH_MODE or user
  --host <redis_host>         default: $REDIS_HOST
  --port <redis_port>         default: $REDIS_PORT or 10000
  --redis-user-object-id <id> default: $REDIS_USER_OBJECT_ID or current az login user
  --managed-identity-client-id <id>
                               default: $REDIS_OPS_MANAGED_IDENTITY_CLIENT_ID
  --managed-identity-principal-id <id>
                               default: $REDIS_OPS_MANAGED_IDENTITY_PRINCIPAL_ID
  --login-managed-identity     run az login --identity before token acquisition

Environment variables:
  REDIS_AUTH_MODE
  REDIS_HOST
  REDIS_PORT
  REDIS_USER_OBJECT_ID
  REDIS_OPS_MANAGED_IDENTITY_CLIENT_ID
  REDIS_OPS_MANAGED_IDENTITY_PRINCIPAL_ID
EOF
}

parse_common_args() {
  POLICY_KEY=""
  CLIENT_IP=""
  REDIS_AUTH_MODE_ARG="${REDIS_AUTH_MODE:-user}"
  REDIS_HOST_ARG="${REDIS_HOST:-}"
  REDIS_PORT_ARG="${REDIS_PORT_DEFAULT}"
  REDIS_USER_OBJECT_ID_ARG="${REDIS_USER_OBJECT_ID:-}"
  REDIS_MANAGED_IDENTITY_CLIENT_ID_ARG="${REDIS_OPS_MANAGED_IDENTITY_CLIENT_ID:-}"
  REDIS_MANAGED_IDENTITY_PRINCIPAL_ID_ARG="${REDIS_OPS_MANAGED_IDENTITY_PRINCIPAL_ID:-}"
  LOGIN_MANAGED_IDENTITY="false"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --policy-key)
        POLICY_KEY="${2:-}"
        shift 2
        ;;
      --client-ip)
        CLIENT_IP="${2:-}"
        shift 2
        ;;
      --auth-mode)
        REDIS_AUTH_MODE_ARG="${2:-}"
        shift 2
        ;;
      --host)
        REDIS_HOST_ARG="${2:-}"
        shift 2
        ;;
      --port)
        REDIS_PORT_ARG="${2:-}"
        shift 2
        ;;
      --redis-user-object-id)
        REDIS_USER_OBJECT_ID_ARG="${2:-}"
        shift 2
        ;;
      --managed-identity-client-id)
        REDIS_MANAGED_IDENTITY_CLIENT_ID_ARG="${2:-}"
        shift 2
        ;;
      --managed-identity-principal-id)
        REDIS_MANAGED_IDENTITY_PRINCIPAL_ID_ARG="${2:-}"
        shift 2
        ;;
      --login-managed-identity)
        LOGIN_MANAGED_IDENTITY="true"
        shift
        ;;
      -h|--help)
        usage_common
        exit 0
        ;;
      *)
        echo "Unknown argument: $1" >&2
        usage_common >&2
        exit 1
        ;;
    esac
  done

  if [[ -z "${POLICY_KEY}" || -z "${CLIENT_IP}" ]]; then
    echo "--policy-key and --client-ip are required." >&2
    usage_common >&2
    exit 1
  fi

  if [[ -z "${REDIS_HOST_ARG}" ]]; then
    echo "Redis host is required. Pass --host or set REDIS_HOST." >&2
    exit 1
  fi

  if [[ "${REDIS_AUTH_MODE_ARG}" != "user" && "${REDIS_AUTH_MODE_ARG}" != "mi" ]]; then
    echo "Invalid --auth-mode. Expected 'user' or 'mi'." >&2
    exit 1
  fi

  if [[ "${REDIS_AUTH_MODE_ARG}" == "user" ]]; then
    if [[ -z "${REDIS_USER_OBJECT_ID_ARG}" ]]; then
      REDIS_USER_OBJECT_ID_ARG="$(az ad signed-in-user show --query id -o tsv 2>/dev/null || true)"
    fi

    if [[ -z "${REDIS_USER_OBJECT_ID_ARG}" ]]; then
      echo "Redis user object id could not be resolved." >&2
      exit 1
    fi

    REDIS_USERNAME="${REDIS_USER_OBJECT_ID_ARG}"
  else
    if [[ -z "${REDIS_MANAGED_IDENTITY_CLIENT_ID_ARG}" ]]; then
      echo "Managed identity client id is required for --auth-mode mi." >&2
      exit 1
    fi
    if [[ -z "${REDIS_MANAGED_IDENTITY_PRINCIPAL_ID_ARG}" ]]; then
      echo "Managed identity principal id is required for --auth-mode mi." >&2
      exit 1
    fi
    if [[ "${LOGIN_MANAGED_IDENTITY}" == "true" ]]; then
      az login --identity --client-id "${REDIS_MANAGED_IDENTITY_CLIENT_ID_ARG}" --allow-no-subscriptions >/dev/null
    fi

    REDIS_USERNAME="${REDIS_MANAGED_IDENTITY_PRINCIPAL_ID_ARG}"
  fi

  REDIS_ACCESS_TOKEN="$(az account get-access-token --resource "${REDIS_RESOURCE}" --query accessToken -o tsv 2>/dev/null || true)"

  if [[ -z "${REDIS_ACCESS_TOKEN}" ]]; then
    echo "Redis access token could not be resolved." >&2
    exit 1
  fi

  REDIS_BLOCK_KEY="auth:ratelimit:block:${POLICY_KEY}:${CLIENT_IP}"
}

redis_cli() {
  redis-cli -c \
    -h "${REDIS_HOST_ARG}" \
    -p "${REDIS_PORT_ARG}" \
    --tls \
    --user "${REDIS_USERNAME}" \
    -a "${REDIS_ACCESS_TOKEN}" \
    "$@"
}
