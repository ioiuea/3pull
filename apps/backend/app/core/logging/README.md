# Logging

`app/core/logging` は backend の logging 基盤をまとめるパッケージです。  
structlog の初期化、logger 取得、HTTP アクセスログ middleware を提供します。

## 何があるか

- `config.py`
  - `configure_logging()`
  - `get_logger()`
- `middleware.py`
  - `AccessLogMiddleware`

## 利用方法

### logger を取得する

```python
from app.core.logging import get_logger

logger = get_logger(__name__)
```

### logging を初期化する

```python
from app.core.logging import configure_logging

configure_logging(level="INFO")
```

### access log middleware を組み込む

```python
from app.core.logging import AccessLogMiddleware

app.add_middleware(AccessLogMiddleware)
```

## import ルール

- 利用側は `app.core.logging` から import する
- `config.py` や `middleware.py` の直 import は、このパッケージ内部を除いて避ける

## 置いてはいけないもの

- 業務ロジック固有の log formatting
- 特定 feature 専用の logger helper
- logging 以外の startup / lifecycle 処理
