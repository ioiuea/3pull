# Azure SQL Database

## このドキュメントの位置づけ

- ファイル名は旧来のままですが、現行実装の DB 前提は `Azure SQL Database` です。
- backend は `Azure SQL Database + Microsoft Entra 認証 + SQLAlchemy(pyodbc)` を前提に接続します。
- スキーマ管理はアプリケーション側の `Alembic` を正とし、DB 本体・ネットワーク・認証基盤をインフラ設計対象とします。

## Azure SQL Database 本体

| 項目 | 設定方針 |
| --- | --- |
| サービス | Azure SQL Database |
| 認証 | Microsoft Entra 認証を標準とする |
| アプリ接続 | `DefaultAzureCredential` / Workload Identity 経由 |
| アプリケーション接続ドライバ | ODBC Driver 18 for SQL Server + `pyodbc` |
| 既定ポート | `1433/TCP` |
| パブリックアクセス | 原則 `Disabled` |
| 接続経路 | Private Endpoint 経由を標準とする |

## 認証・アクセス方針

- backend からの DB 接続は Microsoft Entra 認証を標準とします。
- ローカル開発では `az login + DefaultAzureCredential` を使います。
- AKS などの実行環境では Workload Identity / Managed Identity を使います。
- パスワードベース接続は運用上の例外用途がない限り前提にしません。

## スキーマ管理方針

- DB / テーブル作成は `apps/backend/alembic` の migration を正とします。
- データベース内の業務スキーマ差分は `make alembic-upgrade` で適用します。
- 初期データ投入は migration ではなく seed コマンドで分離します。

## ネットワーク方針

- `publicNetworkAccess=Disabled` を前提とし、Private Endpoint 経由で接続します。
- Private Endpoint は AKS / アプリ実行サブネットからの到達のみを許可します。
- 宛先ポートは `1433/TCP` を許可対象とします。
- Private DNS は Azure SQL Database 用のプライベートゾーンを利用します。

## Private DNS 方針

- 集約 DNS を使わない場合は `privatelink.database.windows.net` を環境内で管理します。
- 集約 DNS を使う場合はハブ側の同ゾーンを参照します。
- アプリケーションの `DATABASE_URL` には Private Endpoint 経由で解決される FQDN を設定します。

## アプリケーション側の前提

- `DATABASE_URL` は SQLAlchemy の `mssql+pyodbc://...` 形式を前提とします。
- SQLAlchemy 側で Entra アクセストークンを ODBC 接続へ注入します。
- JSON 相当データは Azure SQL Database の `NVARCHAR(MAX)` に保存します。
- 日時は `datetime2(3)` 相当で UTC 保存を前提とします。

## 現時点の補足

- 現行コードベースでは backend の DB 前提は Azure SQL Database に移行済みです。
- インフラコード側のリソース名や Bicep パラメータは、別途 Azure SQL Database 前提へ整理が必要な可能性があります。
