# Auth Rate Limit

## 位置づけ

- 本ドキュメントは、backend の認証系 API に適用する IP ベース rate limit の恒久仕様をまとめる。
- infra 前提は [docs/infra/redis.md](./infra/redis.md) を正本とする。
- API 保護の責務分離は [docs/api-security.md](./api-security.md) を参照する。
- 監視実装は [docs/monitor-impl.md](./monitor-impl.md) を参照する。

## 目的

- ブルートフォース
- パスワードリセット乱発
- サインアップ乱発
- OIDC callback の過剰試行

を、`client IP + API 種別` 単位で制御する。

## 対象 API

- `POST /backend/auth/email/signup`
- `POST /backend/auth/email/login`
- `POST /backend/auth/password/reset/request`
- `POST /backend/auth/password/reset/confirm`
- `GET /backend/auth/entra/login`
- `GET /backend/auth/entra/callback`

## 非対象

- `/backend/auth/me`
- `/backend/auth/logout`
- `/backend/auth/session/refresh`
- jobs / audit / health などの認証以外 API

## 基本方針

- 既存のアカウント単位ロックを置き換えず、補完する
- 判定単位は `client IP + policy_key`
- 共有ストアに `Azure Managed Redis` を使う
- 複数 Pod 構成でも同一判定になるようにする
- Redis 障害時は `fail-open`

## クライアント IP 解決

- `X-Forwarded-For` を常時信頼しない
- `TRUST_PROXY_HEADERS=true` かつ `TRUSTED_PROXY_CIDRS` に一致する trusted proxy 配下でのみ forward header を採用する
- それ以外は TCP peer address を `client IP` として扱う

補足:

- `TRUSTED_PROXY_CIDRS` は infra 側で Application Gateway サブネット CIDR から生成する

## 応答仕様

- block 時:
  - `HTTP 429`
  - fixed message:
    - `Access to this function is currently restricted. Please contact support.`
- observe mode 時:
  - block せず通常応答
- Redis 障害時:
  - block せず通常応答

## policy 一覧

| API | policy_key |
| --- | --- |
| `POST /backend/auth/email/signup` | `email_signup` |
| `POST /backend/auth/email/login` | `email_login` |
| `POST /backend/auth/password/reset/request` | `password_reset_request` |
| `POST /backend/auth/password/reset/confirm` | `password_reset_confirm` |
| `GET /backend/auth/entra/login` | `entra_login` |
| `GET /backend/auth/entra/callback` | `entra_callback` |

## 判定ルール

- request 時:
  - block key を確認
  - request counter を sliding window で評価
  - 閾値超過時は block key を設定
- response/失敗時:
  - 必要な API では failure counter を更新

## Redis キー設計

- namespace:
  - `auth:ratelimit`
- request counter:
  - `auth:ratelimit:counter:<policy_key>:req:<client_ip>`
- failure counter:
  - `auth:ratelimit:counter:<policy_key>:fail:<client_ip>`
- block:
  - `auth:ratelimit:block:<policy_key>:<client_ip>`

例:

- `auth:ratelimit:counter:email_login:req:203.0.113.10`
- `auth:ratelimit:counter:email_login:fail:203.0.113.10`
- `auth:ratelimit:block:email_login:203.0.113.10`

## Redis データ構造

- counter:
  - Sorted Set
  - score は UNIX epoch milliseconds
- block:
  - string key + TTL

## TTL 方針

- counter:
  - policy の最長観測窓に合わせる
- block:
  - policy ごとの block 秒数をそのまま TTL にする
- 手動解除:
  - `block` key 削除で行う

## 運用方針

- 標準の手動解除は block key のみ削除する
- counter key は通常削除しない
- ops script:
  - [scripts/ops/ip-rate-limit/README.md](/Users/hiroki.ueda/Dev/3pull/scripts/ops/ip-rate-limit/README.md)
- maint-vm 運用時は `mi-[env]-[system]-redis-ops` を利用する

## 設定項目

主要項目:

- `RATE_LIMIT_MODE`
- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_SSL`
- `TRUST_PROXY_HEADERS`
- `TRUSTED_PROXY_CIDRS`
- 各 `RATE_LIMIT_POLICY_*`

補足:

- `RATE_LIMIT_RESPONSE_MESSAGE` は環境変数化しない

## 現在の実装方針

- rate limit コア:
  - `app/core/security/rate_limit/`
- API protect の責務分離:
  - [docs/api-security.md](./api-security.md)

## 検証で確認済みのこと

- `email/login` で block されること
- `password/reset/request` で block されること
- `email/signup` で block されること
- block TTL 経過で解除されること
- 手動解除で即時解除できること
- Redis 障害時に fail-open で継続すること
- infra から `generated.env.sh` が生成されること

## 残タスク

- AKS 上からの実接続確認
- 検証環境での複数 Pod 試験
