# Lifecycle

`app/core/lifecycle` は backend アプリケーションの起動・停止処理をまとめるパッケージです。  
現在は FastAPI の `lifespan` を公開するシンプルな構成です。

## 何があるか

- `startup.py`
  - `lifespan` を定義する
  - 起動時に logging を初期化する
  - startup / shutdown を構造化ログへ記録する

## 利用方法

`FastAPI` アプリ生成時に `lifespan` を渡します。

```python
from fastapi import FastAPI

from app.core.lifecycle import lifespan

app = FastAPI(lifespan=lifespan)
```

## import ルール

- 利用側は `app.core.lifecycle` から import する
- `startup.py` を直接 import するのは、このパッケージ内部に限定する

## 今後ここに置くもの

- startup 時の初期化処理
- shutdown 時の解放処理
- lifespan に関する hook の組み立て
