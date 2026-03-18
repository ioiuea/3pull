#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAM_CONF_PATH="${SCRIPT_DIR}/param.conf"

SQL_SERVER_FQDN="${SQL_SERVER_FQDN:-}"
SQL_DATABASE_NAME="${SQL_DATABASE_NAME:-}"
SQL_ADMIN_LOGIN="${SQL_ADMIN_LOGIN:-}"
SQL_ADMIN_PASSWORD="${SQL_ADMIN_PASSWORD:-}"
LOCAL_MODE="false"

usage() {
    cat <<'EOF'
Usage:
  ./scripts/init/sql/deploy.sh
  ./scripts/init/sql/deploy.sh --local

Options:
  --local
      ローカル向けに DB 名とサーバー FQDN を対話入力し、az login 中の個人 principal に権限を付与する

Behavior:
  デフォルト実行:
      scripts/init/sql/param.conf を読み込み、SQL 管理者ログイン + 対話入力したパスワードで接続して
      Managed Identity principal を作成して権限を付与する
  --local:
      対話入力した接続先に対して、az login 中の個人 principal を作成して権限を付与する
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

    : "${SQL_SERVER_FQDN:?SQL_SERVER_FQDN is required for --local}"
    : "${SQL_DATABASE_NAME:?SQL_DATABASE_NAME is required for --local}"
}

load_param_conf() {
    if [[ ! -f "${PARAM_CONF_PATH}" ]]; then
        echo "param.conf not found: ${PARAM_CONF_PATH}" >&2
        echo "Run infra/main.sh to generate it, or use --local." >&2
        exit 1
    fi

    # shellcheck disable=SC1090
    source "${PARAM_CONF_PATH}"

    : "${SQL_SERVER_FQDN:?SQL_SERVER_FQDN is required in param.conf}"
    : "${SQL_DATABASE_NAME:?SQL_DATABASE_NAME is required in param.conf}"
    : "${SQL_ADMIN_LOGIN:?SQL_ADMIN_LOGIN is required in param.conf}"
    : "${SQL_API_MI_NAME:?SQL_API_MI_NAME is required in param.conf}"
    : "${SQL_WORKER_MI_NAME:?SQL_WORKER_MI_NAME is required in param.conf}"
    : "${SQL_SCHEDULERS_MI_NAME:?SQL_SCHEDULERS_MI_NAME is required in param.conf}"
    : "${SQL_MIGRATION_MI_NAME:?SQL_MIGRATION_MI_NAME is required in param.conf}"
}

prompt_sql_admin_password() {
    local input

    if [[ -n "${SQL_ADMIN_PASSWORD}" ]]; then
        return 0
    fi

    read -r -s -p "SQL admin password for ${SQL_ADMIN_LOGIN}: " input
    echo

    if [[ -z "${input}" ]]; then
        echo "SQL admin password is required." >&2
        exit 1
    fi

    SQL_ADMIN_PASSWORD="${input}"
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

run_sql_file_with_token() {
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

run_sql_file_with_sql_auth() {
    local file_path="$1"
    local python_runner
    python_runner="$(resolve_python_runner)"

    SQL_SERVER_FQDN="${SQL_SERVER_FQDN}" \
    SQL_DATABASE_NAME="${SQL_DATABASE_NAME}" \
    SQL_FILE_PATH="${file_path}" \
    SQL_ADMIN_LOGIN="${SQL_ADMIN_LOGIN}" \
    SQL_ADMIN_PASSWORD="${SQL_ADMIN_PASSWORD}" \
    eval "${python_runner}" - <<'PY'
import os
import re

try:
    import pyodbc
except ModuleNotFoundError as exc:
    raise SystemExit(
        "pyodbc is required to run deploy.sh. "
        "Use `uv --directory apps/backend sync` or install pyodbc in python3."
    ) from exc


def split_batches(sql_text: str) -> list[str]:
    parts = re.split(r"(?im)^\s*GO\s*?$", sql_text)
    return [part.strip() for part in parts if part.strip()]


server = os.environ["SQL_SERVER_FQDN"]
database = os.environ["SQL_DATABASE_NAME"]
sql_file_path = os.environ["SQL_FILE_PATH"]
admin_login = os.environ["SQL_ADMIN_LOGIN"]
admin_password = os.environ["SQL_ADMIN_PASSWORD"]

connection_string = (
    "Driver={ODBC Driver 18 for SQL Server};"
    f"Server=tcp:{server},1433;"
    f"Database={database};"
    f"UID={admin_login};"
    f"PWD={admin_password};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
)

with open(sql_file_path, "r", encoding="utf-8") as fp:
    batches = split_batches(fp.read())

with pyodbc.connect(connection_string, autocommit=True) as connection:
    cursor = connection.cursor()
    for batch in batches:
        cursor.execute(batch)
PY
}

write_schema_bootstrap_sql() {
    local target_file="$1"

    cat >>"${target_file}" <<'EOF'
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
EOF
}

write_local_principal_sql() {
    local target_file="$1"
    local principal_name="$2"
    local principal_identifier
    local principal_literal

    principal_identifier="$(escape_sql_identifier "${principal_name}")"
    principal_literal="$(escape_sql_nstring "${principal_name}")"

    cat >>"${target_file}" <<EOF
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
}

write_managed_identity_principal_sql() {
    local target_file="$1"
    local principal_name="$2"
    local auth_permissions="$3"
    local audit_permissions="$4"
    local core_permissions="$5"
    local enable_ddladmin="$6"
    local principal_identifier
    local principal_literal

    principal_identifier="$(escape_sql_identifier "${principal_name}")"
    principal_literal="$(escape_sql_nstring "${principal_name}")"

    cat >>"${target_file}" <<EOF
IF NOT EXISTS (
    SELECT 1
    FROM sys.database_principals
    WHERE name = N'${principal_literal}'
)
BEGIN
    EXEC(N'CREATE USER [${principal_identifier}] FROM EXTERNAL PROVIDER');
END;
GO

GRANT CONNECT TO [${principal_identifier}];
GO
GRANT VIEW DEFINITION TO [${principal_identifier}];
GO

GRANT ${auth_permissions}
ON SCHEMA::auth TO [${principal_identifier}];
GO

GRANT ${audit_permissions}
ON SCHEMA::audit TO [${principal_identifier}];
GO

GRANT ${core_permissions}
ON SCHEMA::core TO [${principal_identifier}];
GO
EOF

    if [[ "${enable_ddladmin}" == "true" ]]; then
        cat >>"${target_file}" <<EOF
ALTER ROLE db_ddladmin ADD MEMBER [${principal_identifier}];
GO
EOF
    fi
}

main() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --local)
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

    if [[ "${LOCAL_MODE}" == "true" ]]; then
        require_command az
        prompt_local_overrides
    else
        load_param_conf
    fi

    local temp_sql
    temp_sql="$(mktemp)"
    trap "rm -f '${temp_sql}'" EXIT

    write_schema_bootstrap_sql "${temp_sql}"

    if [[ "${LOCAL_MODE}" == "true" ]]; then
        local principal_name
        principal_name="$(resolve_current_principal)"
        echo "Applying schema bootstrap and grants to ${SQL_SERVER_FQDN}/${SQL_DATABASE_NAME}"
        echo "Creating / granting Azure SQL user for local Entra principal: ${principal_name}"
        write_local_principal_sql "${temp_sql}" "${principal_name}"
    else
        prompt_sql_admin_password
        echo "Applying schema bootstrap and managed identity grants to ${SQL_SERVER_FQDN}/${SQL_DATABASE_NAME}"
        echo "Connecting with SQL admin login: ${SQL_ADMIN_LOGIN}"
        echo "Creating / granting Azure SQL users for Managed Identities:"
        echo "  - ${SQL_API_MI_NAME}"
        echo "  - ${SQL_WORKER_MI_NAME}"
        echo "  - ${SQL_SCHEDULERS_MI_NAME}"
        echo "  - ${SQL_MIGRATION_MI_NAME}"

        write_managed_identity_principal_sql \
            "${temp_sql}" \
            "${SQL_API_MI_NAME}" \
            "SELECT, INSERT, UPDATE, DELETE" \
            "SELECT, INSERT" \
            "SELECT, INSERT, UPDATE, DELETE" \
            "false"

        write_managed_identity_principal_sql \
            "${temp_sql}" \
            "${SQL_WORKER_MI_NAME}" \
            "SELECT, INSERT, UPDATE" \
            "SELECT, INSERT" \
            "SELECT, INSERT, UPDATE, DELETE" \
            "false"

        write_managed_identity_principal_sql \
            "${temp_sql}" \
            "${SQL_SCHEDULERS_MI_NAME}" \
            "SELECT, UPDATE, DELETE" \
            "SELECT, DELETE" \
            "SELECT, UPDATE, DELETE" \
            "false"

        write_managed_identity_principal_sql \
            "${temp_sql}" \
            "${SQL_MIGRATION_MI_NAME}" \
            "ALTER, CONTROL, DELETE, EXECUTE, INSERT, REFERENCES, SELECT, UPDATE" \
            "ALTER, CONTROL, DELETE, EXECUTE, INSERT, REFERENCES, SELECT, UPDATE" \
            "ALTER, CONTROL, DELETE, EXECUTE, INSERT, REFERENCES, SELECT, UPDATE" \
            "true"
    fi

    if [[ "${LOCAL_MODE}" == "true" ]]; then
        local access_token
        access_token="$(resolve_sql_access_token)"
        run_sql_file_with_token "${temp_sql}" "${access_token}"
    else
        run_sql_file_with_sql_auth "${temp_sql}"
    fi

    echo "Completed."
}

main "$@"
