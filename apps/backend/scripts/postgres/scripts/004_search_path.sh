#!/usr/bin/env bash
set -euo pipefail

echo "[debug] PGHOST=${PGHOST:-}"
echo "[debug] PGPORT=${PGPORT:-}"
echo "[debug] PGUSER=${PGUSER:-}"
echo "[debug] PGDATABASE=${PGDATABASE:-}"
echo "[debug] APP_DB_USER=${APP_DB_USER:-}"

pause() {
  read -r -p "Press Enter to continue..." _ </dev/tty
}

missing_env=()
for env_key in PGHOST PGUSER PGPORT PGDATABASE PGPASSWORD APP_DB_USER; do
  if [[ -z "${!env_key:-}" ]]; then
    missing_env+=("$env_key")
  fi
done

if (( ${#missing_env[@]} > 0 )); then
  echo "❌ Required environment variables are missing: ${missing_env[*]}" >&2
  echo "Set them and rerun." >&2
  exit 1
fi

echo "----------------------------------------------"
echo "Setting search_path default on database '${PGDATABASE}'..."
echo "  - ${APP_DB_USER} => search_path=core,public"
echo "----------------------------------------------"
pause

# ロールごと・DBごとに search_path を固定
psql -v ON_ERROR_STOP=1 --username "$PGUSER" --dbname "$PGDATABASE" <<SQL
-- ロール '${APP_DB_USER}' : core を最優先、public をフォールバックに
ALTER ROLE ${APP_DB_USER} IN DATABASE ${PGDATABASE}
  SET search_path = core, public;
SQL

# 設定確認（pg_db_role_setting を人間が読みやすく）
psql --username "$PGUSER" --dbname "$PGDATABASE" -v ON_ERROR_STOP=1 -tAc "
  SELECT r.rolname AS role,
         d.datname AS db,
         regexp_replace(s.setconfig::text, '^{|}$', '') AS setconfig
  FROM pg_db_role_setting s
  JOIN pg_roles r     ON r.oid = s.setrole
  JOIN pg_database d  ON d.oid = s.setdatabase
  WHERE r.rolname = '${APP_DB_USER}'
    AND d.datname = '${PGDATABASE}'
  ORDER BY r.rolname;
" | sed 's/^/  */'

echo "----------------------------------------------"
echo "✅ search_path default configured."
echo "   - ${APP_DB_USER} -> core,public"
echo "----------------------------------------------"

echo "[verify] Per-role search_path setting"
pause
psql --username "$PGUSER" --dbname "$PGDATABASE" -x -c \
  "SELECT r.rolname AS role, d.datname AS db, regexp_replace(s.setconfig::text, '^{|}$', '') AS setconfig FROM pg_db_role_setting s JOIN pg_roles r ON r.oid = s.setrole JOIN pg_database d ON d.oid = s.setdatabase WHERE r.rolname = '${APP_DB_USER}' AND d.datname='${PGDATABASE}' ORDER BY r.rolname;"

echo "[verify] Effective search_path as ${APP_DB_USER}"
pause
PGPASSWORD="$PGPASSWORD" psql --username "${APP_DB_USER}" --dbname "$PGDATABASE" -x -c "SHOW search_path;"
