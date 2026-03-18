# Azure SQL Database

## 概要

本システムの永続データストアには Azure SQL Database を採用する。  
アプリケーション実装は `DATABASE_URL` 1 本、SQLAlchemy `Base.metadata` 1 つ、Alembic 1 系統を前提としているため、データベースは 1 つに集約し、その中で `auth` / `audit` / `core` の 3 schema を用いて論理分割する。

接続は runtime では Microsoft Entra 認証を標準とし、backend 実装では `mssql+pyodbc`、ODBC Driver 18 for SQL Server、Entra access token 注入方式を用いる。  
一方で Azure SQL Server には緊急時運用のため SQL 管理者ログインも保持する。  
ネットワークは Private Endpoint 経由を標準とし、Public Network Access は無効化する。

## リソース設計

### Azure SQL Server / Database

| 項目 | 設定値 | Bicepプロパティ名 |
| --- | --- | --- |
| サービス | Azure SQL Database | `Microsoft.Sql/servers`, `Microsoft.Sql/servers/databases` |
| サーバー名 | `sql-[common.environmentName]-[common.systemName]` | `server.name` |
| データベース名 | `sqldb-[common.environmentName]-[common.systemName]` | `database.name` |
| 場所 | `[common.location]` | `location` |
| 認証 | Microsoft Entra admin + SQL 管理者ログイン併用 | server 設定 |
| 接続方式 | `mssql+pyodbc` + ODBC Driver 18 + Entra access token | アプリ実装側 |
| 既定ポート | `1433/TCP` | 接続仕様 |
| Public Network Access | `Disabled` | server property |

命名規則は Microsoft Learn の resource abbreviations に合わせ、SQL Server を `sql`、SQL Database を `sqldb` とする。

## データベース構成

### 論理構成

データベースは 1 Database 構成とし、業務テーブルは以下の 3 schema に分離する。

- `auth`
- `audit`
- `core`

Database 自体は分割せず、schema によって責務境界を表現する。これにより、現行 backend の接続方式、モデル構成、Alembic 運用を大きく変えずに論理分離を実現する。

### テーブル配置

現時点の主要テーブルは以下の通り。

- `auth.users`
- `auth.auth_identities`
- `auth.sessions`
- `auth.email_verification_tokens`
- `auth.password_reset_tokens`
- `audit.auth_audit_logs`
- `core.async_jobs`
- `core.async_job_artifacts`

schema 作成は migration に含めず、bootstrap script 側で実施する。  
初期 schema 作成、Entra user 作成、schema 権限付与は `scripts/init/sql/deploy.sh` を前提とする。

## 認証・接続設計

### 接続方針

| 項目 | 設定方針 |
| --- | --- |
| ローカル開発 | `az login` + `DefaultAzureCredential` |
| AKS 実行時 | Workload Identity / User Assigned Managed Identity |
| SQLAlchemy 接続 | `pyodbc` |
| ODBC Driver | `ODBC Driver 18 for SQL Server` |
| Secret 管理 | `DATABASE_URL` は Key Vault 経由注入を想定 |

backend 実装では、接続直前に Entra access token を ODBC 属性へ注入する。  
runtime では API / worker / schedulers を別 principal として扱い、migration / bootstrap は maint-vm 上の専用 User Assigned Managed Identity で実行する。  
Azure SQL Server には Microsoft Entra admin を設定する。  
加えて、サーバー作成時に bootstrap / 緊急時用の SQL 管理者ログインを設定し、平常時のアプリ接続では利用しない。

## 権限設計

### principal 構成

Azure SQL Database 内の principal は以下に分離する。

- API 用 Managed Identity
- worker 用 Managed Identity
- schedulers 用 Managed Identity
- migration / bootstrap 用 Managed Identity

ローカル開発時に `az login` で利用するユーザー付与は、上記 runtime / migration principal と分離して扱う。

### runtime principal の DB 内権限

共通権限:

- `CONNECT`
- `VIEW DEFINITION`

schema ごとの権限は以下とする。

| principal | `auth` | `audit` | `core` |
| --- | --- | --- | --- |
| API | `SELECT, INSERT, UPDATE, DELETE` | `SELECT, INSERT` | `SELECT, INSERT, UPDATE, DELETE` |
| worker | `SELECT, INSERT, UPDATE` | `SELECT, INSERT` | `SELECT, INSERT, UPDATE, DELETE` |
| schedulers | `SELECT, UPDATE, DELETE` | `SELECT, DELETE` | `SELECT, UPDATE, DELETE` |

設計意図は以下の通り。

- `audit` schema は監査証跡として扱うため、runtime principal に `UPDATE` は付与しない
- `schedulers` は cleanup 専用のため `INSERT` は不要
- `worker` は将来の非同期補助処理やジョブ監査ログ記録を見込み、`auth` / `audit` に `INSERT` を含める

### migration / bootstrap principal

migration / bootstrap principal は runtime principal と分離した専用 principal とし、maint-vm 上で実行する。  
maint-vm に割り当てる identity は migration 用 User Assigned Managed Identity のみとし、runtime 用 Managed Identity は割り当てない。

この principal の用途は以下とする。

- `auth` / `audit` / `core` schema 作成
- `CREATE USER ... FROM EXTERNAL PROVIDER`
- runtime principal への `GRANT`
- Alembic 初期適用
- 将来の schema migration

DB 内権限は、Alembic による DDL 実行が詰まりにくいことを優先し、`db_ddladmin` 相当の広めの付与を基本とする。  
ただし `db_owner` 相当までは付与しない。

## ネットワーク設計

### 接続経路

| 項目 | 設定方針 |
| --- | --- |
| 接続経路 | Private Endpoint 経由を標準とする |
| Private DNS Zone | `privatelink.database.windows.net` |
| centralized DNS | `network.enableCentralizedPrivateDns=true` 時は環境側管理を優先 |
| Public Network Access | `Disabled` |
| Private Endpoint 配置先 | Bicep で作成される既存の Private Endpoint 用 subnet を利用 |

backend の `DATABASE_URL` には、Private Endpoint 経由で名前解決される FQDN を設定する。  
Azure SQL Database 専用の Private Endpoint subnet は新設せず、Storage / Service Bus と同様に共通の Private Endpoint 用 subnet に配置する。

Firewall 例外でのパブリック接続許可は原則採らない。開発・本番ともに Private Endpoint 前提とし、環境差を増やさない方針とする。

## 監視・監査設計

### 診断設定

診断設定は Azure SQL Database resource 単位で構成する。  
初期導入時の設定は以下とする。

- ログカテゴリ: `allLogs`
- メトリック: `Basic`

`InstanceAndAppAdvanced` と `WorkloadManagement` は、初期導入では有効化しない。  
高詳細メトリックはコストとノイズが増えやすいため、性能分析要件が明確になった段階で追加判断する。

### SQL Auditing

SQL Auditing は診断設定とは別に有効化し、送信先は Log Analytics とする。  
監査ログの初期運用は Log Analytics 集約を優先し、Storage / Event Hub 連携は必要になった時点で拡張する。

### Defender for SQL

Defender for SQL は本設計の必須構成には含めない。  
ただし Azure 基盤全体の Policy により有効化される可能性を前提とし、実装時は環境側設定と整合を取る。

### ロック

`enableResourceLock=true` 時は、少なくとも以下を削除ロック対象とする。

- Azure SQL Server
- Azure SQL Database
- Private Endpoint
- Private DNS 関連リソース

## アプリケーション実装との整合

本設計は以下の現行実装を前提としている。

- backend は 1 つの `DATABASE_URL` で接続する
- Alembic は 1 系統の migration として運用する
- schema 作成は migration ではなく bootstrap script 側で行う
- JSON 相当データは `NVARCHAR(MAX)` 保存
- 日時型は `datetime2(3)` を前提とする

根拠となる主な実装ファイル:

- `apps/backend/app/adapters/sql/session.py`
- `apps/backend/app/adapters/sql/base.py`
- `apps/backend/alembic/env.py`
- `apps/backend/alembic/versions/6177c957a67e_init_table_schemas.py`
- `scripts/init/sql/deploy.sh`

## 実装対象

- `infra/bicep/` 配下に Azure SQL Database 用 Bicep を追加する
- `infra/config/` 配下に Azure SQL Database 用設定ファイルを追加する
- `scripts/init/sql/deploy.sh` を bootstrap script として維持する
