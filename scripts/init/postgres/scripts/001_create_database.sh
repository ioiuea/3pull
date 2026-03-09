#!/usr/bin/env bash
set -euo pipefail

pause() {
  read -r -p "Press Enter to continue..." _ </dev/tty
}

echo "[debug] PGHOST=${PGHOST:-}"
echo "[debug] PGPORT=${PGPORT:-}"
echo "[debug] PGUSER=${PGUSER:-}"
echo "[debug] PGDATABASE=${PGDATABASE:-}"

missing_env=()
for env_key in PGHOST PGUSER PGPORT PGDATABASE PGPASSWORD; do
  if [[ -z "${!env_key:-}" ]]; then
    missing_env+=("$env_key")
  fi
done

if (( ${#missing_env[@]} > 0 )); then
  echo "❌ Required environment variables are missing: ${missing_env[*]}" >&2
  echo "Set them (e.g. export PGHOST=... PGUSER=...) and rerun." >&2
  exit 1
fi

# Azure Database for PostgreSQL など、PG* 環境変数で接続する前提で実行します。
# PGDATABASE で指定されたデータベースが無ければ作成（あれば何もしない）

create_database() {
  local db_name="$1"
  if [[ -z "$db_name" ]]; then
    return 0
  fi

  echo "[info] Checking/creating database: ${db_name}"
  pause
  psql -v ON_ERROR_STOP=1 -v db_name="$db_name" --username "$PGUSER" --dbname "postgres" <<'SQL'
  -- 存在しない場合のみ CREATE DATABASE 文を生成し、その場で実行する
  SELECT format('CREATE DATABASE %I', :'db_name')
  WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db_name');
  \gexec
SQL
}

create_database "$PGDATABASE"

# 指定データベースの存在を確認してメッセージ表示
echo "[info] Verifying database existence"
pause
DB_EXISTS=$(psql --username "$PGUSER" --dbname "postgres" -tAc \
  "SELECT 1 FROM pg_database WHERE datname = '${PGDATABASE}';" || true)

echo "----------------------------------------------"
if [[ "$DB_EXISTS" == "1" ]]; then
  echo "✅ Database '${PGDATABASE}' is present (created or already existed)."
else
  echo "❌ Failed to verify creation of database '${PGDATABASE}'."
fi
echo "----------------------------------------------"

echo "[verify] Listing databases"
pause
psql --username "$PGUSER" --dbname "postgres" -x -c "\l+"

echo "[verify] current_database() on target database"
pause
psql --username "$PGUSER" --dbname "$PGDATABASE" -x -c "SELECT current_database();"

echo "[verify] Server connection info"
pause
psql --username "$PGUSER" --dbname "postgres" -x -c "SELECT inet_server_addr(), inet_server_port(), version();"
