#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 現時点の既定値。将来的には infra 側で環境固有値を埋め込む想定。
DEFAULT_SQL_SERVER_FQDN="sql-3pull-test.database.windows.net"
DEFAULT_SQL_DATABASE_NAME="sql-3pull-test"

SQL_SERVER_FQDN="${SQL_SERVER_FQDN:-$DEFAULT_SQL_SERVER_FQDN}"
SQL_DATABASE_NAME="${SQL_DATABASE_NAME:-$DEFAULT_SQL_DATABASE_NAME}"
LOCAL_MODE="false"

usage() {
    cat <<'EOF'
Usage:
  ./scripts/init/sql/deploy.sh
  ./scripts/init/sql/deploy.sh -local

Options:
  -local, --local
      ローカル向けに DB 名とサーバー FQDN を対話入力する
EOF
}

REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/apps/backend"

require_command() {
    local command_name="$1"
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Required command not found: ${command_name}" >&2
        exit 1
    fi
}

escape_sql_identifier() {
    local value="$1"
    printf '%s' "${value//]/]]}"
}

escape_sql_nstring() {
    local value="$1"
    printf '%s' "${value//\'/\'\'}"
}

resolve_current_principal() {
    local principal
    principal="$(az ad signed-in-user show --query userPrincipalName -o tsv 2>/dev/null || true)"
    if [[ -n "${principal}" ]]; then
        printf '%s\n' "${principal}"
        return 0
    fi

    principal="$(az account show --query user.name -o tsv 2>/dev/null || true)"
    if [[ -n "${principal}" ]]; then
        printf '%s\n' "${principal}"
        return 0
    fi

    echo "Could not resolve the signed-in Entra principal from az login." >&2
    exit 1
}

prompt_local_overrides() {
    local input

    read -r -p "SQL Server FQDN [${SQL_SERVER_FQDN}]: " input
    if [[ -n "${input}" ]]; then
        SQL_SERVER_FQDN="${input}"
    fi

    read -r -p "Database name [${SQL_DATABASE_NAME}]: " input
    if [[ -n "${input}" ]]; then
        SQL_DATABASE_NAME="${input}"
    fi
}

resolve_python_runner() {
    if command -v uv >/dev/null 2>&1 && [[ -f "${BACKEND_DIR}/pyproject.toml" ]]; then
        printf 'uv --directory %q run python' "${BACKEND_DIR}"
        return 0
    fi

    if command -v python3 >/dev/null 2>&1; then
        printf 'python3'
        return 0
    fi

    echo "Could not find a Python runner. Install uv or python3." >&2
    exit 1
}

resolve_sql_access_token() {
    az account get-access-token \
        --resource https://database.windows.net/ \
        --query accessToken \
        -o tsv
}

run_sql_file() {
    local file_path="$1"
    local access_token="$2"
    local python_runner
    python_runner="$(resolve_python_runner)"

    SQL_SERVER_FQDN="${SQL_SERVER_FQDN}" \
    SQL_DATABASE_NAME="${SQL_DATABASE_NAME}" \
    SQL_FILE_PATH="${file_path}" \
    AZURE_SQL_ACCESS_TOKEN="${access_token}" \
    eval "${python_runner}" - <<'PY'
import os
import re
import struct
import sys

try:
    import pyodbc
except ModuleNotFoundError as exc:
    raise SystemExit(
        "pyodbc is required to run deploy.sh. "
        "Use `uv --directory apps/backend sync` or install pyodbc in python3."
    ) from exc

SQL_COPT_SS_ACCESS_TOKEN = 1256


def create_access_token_struct(token: str) -> bytes:
    token_bytes = token.encode("utf-16-le")
    return struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)


def split_batches(sql_text: str) -> list[str]:
    parts = re.split(r"(?im)^\s*GO\s*?$", sql_text)
    return [part.strip() for part in parts if part.strip()]


server = os.environ["SQL_SERVER_FQDN"]
database = os.environ["SQL_DATABASE_NAME"]
sql_file_path = os.environ["SQL_FILE_PATH"]
access_token = os.environ["AZURE_SQL_ACCESS_TOKEN"]

connection_string = (
    "Driver={ODBC Driver 18 for SQL Server};"
    f"Server=tcp:{server},1433;"
    f"Database={database};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
)

with open(sql_file_path, "r", encoding="utf-8") as fp:
    batches = split_batches(fp.read())

with pyodbc.connect(
    connection_string,
    attrs_before={SQL_COPT_SS_ACCESS_TOKEN: create_access_token_struct(access_token)},
    autocommit=True,
) as connection:
    cursor = connection.cursor()
    for batch in batches:
        cursor.execute(batch)
PY
}

main() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -local|--local)
                LOCAL_MODE="true"
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo "Unknown argument: $1" >&2
                usage >&2
                exit 1
                ;;
        esac
    done

    require_command az
    if [[ "${LOCAL_MODE}" == "true" ]]; then
        prompt_local_overrides
    fi

    local principal_name
    principal_name="$(resolve_current_principal)"
    local access_token
    access_token="$(resolve_sql_access_token)"

    local principal_identifier
    local principal_literal
    principal_identifier="$(escape_sql_identifier "${principal_name}")"
    principal_literal="$(escape_sql_nstring "${principal_name}")"

    local temp_sql
    temp_sql="$(mktemp)"
    trap "rm -f '${temp_sql}'" EXIT

    cat >"${temp_sql}" <<EOF
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'auth')
BEGIN
    EXEC(N'CREATE SCHEMA [auth]');
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'audit')
BEGIN
    EXEC(N'CREATE SCHEMA [audit]');
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'core')
BEGIN
    EXEC(N'CREATE SCHEMA [core]');
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.database_principals
    WHERE name = N'${principal_literal}'
)
BEGIN
    EXEC(N'CREATE USER [${principal_identifier}] FROM EXTERNAL PROVIDER');
END;
GO

GRANT CREATE TABLE TO [${principal_identifier}];
GO
GRANT CREATE VIEW TO [${principal_identifier}];
GO
GRANT CREATE PROCEDURE TO [${principal_identifier}];
GO
GRANT CREATE FUNCTION TO [${principal_identifier}];
GO
GRANT CREATE TYPE TO [${principal_identifier}];
GO

GRANT ALTER, CONTROL, DELETE, EXECUTE, INSERT, REFERENCES, SELECT, UPDATE, VIEW DEFINITION
ON SCHEMA::auth TO [${principal_identifier}];
GO

GRANT ALTER, CONTROL, DELETE, EXECUTE, INSERT, REFERENCES, SELECT, UPDATE, VIEW DEFINITION
ON SCHEMA::audit TO [${principal_identifier}];
GO

GRANT ALTER, CONTROL, DELETE, EXECUTE, INSERT, REFERENCES, SELECT, UPDATE, VIEW DEFINITION
ON SCHEMA::core TO [${principal_identifier}];
GO
EOF

    echo "Applying schema bootstrap and principal grants to ${SQL_SERVER_FQDN}/${SQL_DATABASE_NAME}"
    echo "Creating / granting Azure SQL user for Entra principal: ${principal_name}"
    run_sql_file "${temp_sql}" "${access_token}"

    echo "Completed."
}

main "$@"
