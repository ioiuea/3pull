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
  echo "Set them (e.g. export PGHOST=... PGUSER=... PGPORT=... PGDATABASE=... PGPASSWORD=...) and rerun." >&2
  exit 1
fi

# PGDATABASE に接続し、core スキーマが存在しなければ作成
# Azure Database for PostgreSQL など、PG* 環境変数で接続する前提です。
echo "[info] Creating schemas in database: ${PGDATABASE}"
pause
psql -v ON_ERROR_STOP=1 --username "$PGUSER" --dbname "$PGDATABASE" <<'SQL'
  DO $$
  BEGIN
    -- ★ core スキーマのみ
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'core') THEN
      EXECUTE 'CREATE SCHEMA core';
    END IF;
  END $$;
SQL

# スキーマの存在確認
echo "[info] Verifying schema existence: core"
pause
SCHEMA_EXISTS=$(psql --username "$PGUSER" --dbname "$PGDATABASE" -tAc \
  "SELECT 1 FROM pg_namespace WHERE nspname = 'core';" || true)

echo "----------------------------------------------"
if [[ "$SCHEMA_EXISTS" == "1" ]]; then
  echo "✅ Schema 'core' is present in database '${PGDATABASE}' (created or already existed)."
else
  echo "❌ Failed to verify creation of schema 'core' in database '${PGDATABASE}'."
fi
echo "----------------------------------------------"

echo "[verify] Listing schemas"
pause
psql --username "$PGUSER" --dbname "$PGDATABASE" -x -c "\dn+"

echo "[verify] Checking core schema exists"
pause
psql --username "$PGUSER" --dbname "$PGDATABASE" -x -c "SELECT nspname FROM pg_namespace WHERE nspname = 'core';"

echo "[verify] Server connection info"
pause
psql --username "$PGUSER" --dbname "$PGDATABASE" -x -c "SELECT inet_server_addr(), inet_server_port(), current_database(), version();"
