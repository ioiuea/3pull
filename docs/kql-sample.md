# KQL Sample

workspace-based `Application Insights` を前提とした KQL 例です。

## startup / telemetry 初期化ログ

```kusto
AppTraces
| where TimeGenerated > ago(30m)
| where Message has "telemetry.init.completed"
   or Message has "application.startup"
| order by TimeGenerated desc
```

補足:

- 現状の logging telemetry は `structlog` の JSON 文字列が `Message` に入る前提で検索する
- `Message in (...)` や `Properties.event` 前提では一致しない場合があるため、まずは `Message has ...` を使う

## request telemetry

```kusto
AppRequests
| where TimeGenerated > ago(30m)
| order by TimeGenerated desc
```

個別 path 確認例:

```kusto
AppRequests
| where TimeGenerated > ago(30m)
| where Url has "/livez" or Url has "/readyz"
| order by TimeGenerated desc
```

## exception telemetry

```kusto
AppExceptions
| where TimeGenerated > ago(30m)
| order by TimeGenerated desc
```

## access log / application log

```kusto
AppTraces
| where TimeGenerated > ago(30m)
| where Message has "http.access"
| order by TimeGenerated desc
```

## rate limit 関連ログ

```kusto
AppTraces
| where TimeGenerated > ago(30m)
| where Message has "auth.rate_limit"
| order by TimeGenerated desc
```

block のみ確認する場合:

```kusto
AppTraces
| where TimeGenerated > ago(30m)
| where Message has "auth.rate_limit.blocked"
| order by TimeGenerated desc
```

## worker / scheduler telemetry 確認

worker / scheduler の初期化確認:

```kusto
AppTraces
| where TimeGenerated > ago(30m)
| where Message has "telemetry.init.completed"
| where Message has "-worker-" or Message has "-scheduler-"
| order by TimeGenerated desc
```

worker 実行ログ確認:

```kusto
AppTraces
| where TimeGenerated > ago(30m)
| where Message has "worker.loop.started"
| order by TimeGenerated desc
```

scheduler 実行ログ確認:

```kusto
AppTraces
| where TimeGenerated > ago(30m)
| where Message has "cleanup.started"
| order by TimeGenerated desc
```

`service.name` 単位で見たい場合の例:

```kusto
AppTraces
| where TimeGenerated > ago(30m)
| where Message has "threepull-worker-auth-audit-export"
   or Message has "threepull-scheduler-sessions-cleanup"
| order by TimeGenerated desc
```

## Alert 用の叩き台

exception 急増:

```kusto
AppExceptions
| where TimeGenerated > ago(5m)
| summarize exception_count = count()
```

request duration 悪化:

```kusto
AppRequests
| where TimeGenerated > ago(5m)
| summarize avg_duration_ms = avg(DurationMs), p95_duration_ms = percentile(DurationMs, 95)
```

path 単位で確認したい場合:

```kusto
AppRequests
| where TimeGenerated > ago(5m)
| summarize avg_duration_ms = avg(DurationMs), p95_duration_ms = percentile(DurationMs, 95) by Name
```

rate limit block 急増:

```kusto
AppTraces
| where TimeGenerated > ago(5m)
| where Message has "auth.rate_limit.blocked"
| summarize blocked_count = count()
```

policy 別確認のための叩き台:

```kusto
AppTraces
| where TimeGenerated > ago(5m)
| where Message has "auth.rate_limit.blocked"
| summarize blocked_count = count() by Message
```
