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

# 本スクリプトは core スキーマ運用向けの API ロールを初期化します。
# 目的:
# - API(FastAPI) 用: ${APP_DB_USER} を作成/更新
# - core スキーマのオーナー・最小権限を設定
# - PUBLIC の過剰権限を剥奪
# - すべて idempotent（再実行安全）
echo "[info] Initializing API role and privileges on database: ${PGDATABASE}"
pause

psql -v ON_ERROR_STOP=1 --username "$PGUSER" --dbname "$PGDATABASE" <<SQL

-- =========================================================
-- 1) API ロール作成（存在チェック付き）
-- =========================================================
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${APP_DB_USER}') THEN
    CREATE ROLE ${APP_DB_USER} LOGIN PASSWORD '${PGPASSWORD}';
  ELSE
    ALTER ROLE ${APP_DB_USER} LOGIN PASSWORD '${PGPASSWORD}';
  END IF;
END
\$\$;

-- DB 接続権限（最低限）
GRANT CONNECT ON DATABASE ${PGDATABASE} TO ${APP_DB_USER};

-- =========================================================
-- 2) core スキーマのハードニングと権限設定
-- =========================================================
DO \$\$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'core') THEN
    -- PUBLIC から不要な権限を剥奪
    REVOKE ALL ON SCHEMA core FROM PUBLIC;

    -- core スキーマのオーナー変更
    ALTER SCHEMA core OWNER TO ${APP_DB_USER};

    -- core スキーマの利用/作成
    GRANT USAGE, CREATE ON SCHEMA core TO ${APP_DB_USER};

    -- 既存オブジェクトへの権限
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA core TO ${APP_DB_USER};
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA core TO ${APP_DB_USER};

    -- 将来作成されるオブジェクトへのデフォルト権限
    ALTER DEFAULT PRIVILEGES FOR ROLE ${APP_DB_USER} IN SCHEMA core
      GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${APP_DB_USER};
    ALTER DEFAULT PRIVILEGES FOR ROLE ${APP_DB_USER} IN SCHEMA core
      GRANT USAGE, SELECT ON SEQUENCES TO ${APP_DB_USER};
  END IF;
END
\$\$;

-- =========================================================
-- 3) public スキーマの最小権限
-- =========================================================
GRANT USAGE ON SCHEMA public TO ${APP_DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${APP_DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO ${APP_DB_USER};
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

SQL

echo "----------------------------------------------"
echo "✅ Roles & privileges initialized:"
echo "   - ${APP_DB_USER} (core schema)"
echo "   PUBLIC hardening applied (core/public)."
echo "----------------------------------------------"

echo "[verify] List roles"
pause
psql --username "$PGUSER" --dbname "$PGDATABASE" -x -c "\du+"

echo "[verify] Schema owners"
pause
psql --username "$PGUSER" --dbname "$PGDATABASE" -x -c \
  "SELECT nspname, nspowner::regrole FROM pg_namespace WHERE nspname IN ('core','public');"

echo "[verify] API role schema privileges (core)"
pause
psql --username "$PGUSER" --dbname "$PGDATABASE" -x -c \
  "SELECT 'USAGE' AS privilege, has_schema_privilege('${APP_DB_USER}','core','USAGE') AS granted UNION ALL SELECT 'CREATE', has_schema_privilege('${APP_DB_USER}','core','CREATE');"
