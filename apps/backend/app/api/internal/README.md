# api.internal

`app.api.internal` は、運用基盤から参照される内部向け API を置くパッケージです。

現状は Kubernetes などのオーケストレーション基盤から使う probe endpoint をここで管理します。

## 役割

- liveness probe 用 endpoint の提供
- readiness probe 用 endpoint の提供
- OpenAPI の公開対象に含めない内部運用 endpoint の集約

## 含まれる endpoint

- `/livez`
  - プロセスが起動しているかを確認する軽量 probe
- `/readyz`
  - リクエスト受付可能かを確認する軽量 probe

これらはユーザー向け機能 API ではなく、Kubernetes の probe やロードバランサ、運用監視から参照することを想定しています。

## 利用方針

internal API は公開 API の `/backend` 配下には入れず、アプリ直下で公開します。

```python
from app.api.internal.probes import router as probes_router

app.include_router(probes_router)
```

また、internal API は原則として次の性質を保ちます。

- 認証不要で軽量に応答する
- 副作用を持たない
- OpenAPI schema に載せない
- 運用上の生存確認・準備確認に用途を限定する

## 含めないもの

- 業務機能の API
- 管理画面向けの内部運用機能
- 重い依存確認を伴う複雑な health check

業務機能は `app.api.routers` に置き、公開 API として管理します。
