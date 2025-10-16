# バックエンドコーディングルール

このドキュメントは、3pull-devinバックエンド（FastAPI）の開発における統一されたコーディング規約を定義します。

## 目次
- [基本開発ルール](#基本開発ルール)
- [パッケージ管理](#パッケージ管理)
- [コード品質](#コード品質)
- [テスト要件](#テスト要件)
- [開発ツール](#開発ツール)
- [Commit/PRルール](#commitprルール)
- [エラー処理](#エラー処理)
- [PEP8準拠](#pep8準拠)

## 基本開発ルール

### パッケージ管理の原則

**必須**: パッケージ管理には**uvのみ**を使用し、**pipは絶対に使用しない**こと。

#### 許可されるコマンド

```bash
# パッケージのインストール (important-comment)
uv add package-name

# 開発用パッケージのインストール (important-comment)
uv add --dev package-name

# パッケージのアップグレード (important-comment)
uv add --upgrade-package package-name

# ツールの実行 (important-comment)
uv run tool-name

# 依存関係を固定してツールを実行 (important-comment)
uv run --frozen tool-name
```

#### 禁止事項

```bash
# ❌ 絶対に使用禁止 (important-comment)
uv pip install package-name
pip install package-name

# ❌ @latestでのインストール禁止（バージョン指定必須） (important-comment)
uv add package-name@latest
```

**理由**: バージョンを明示的に指定することで、環境間の一貫性を保ち、予期しない動作を防ぎます。

### コード品質要件

#### 1. 型ヒント（Type Hints）

**必須**: 全ての関数とメソッドに型ヒントを付けること。

```python
# ✅ 良い例 (important-comment)
def calculate_total(price: float, quantity: int) -> float:
    """合計金額を計算する"""
    return price * quantity

# ❌ 悪い例 (important-comment)
def calculate_total(price, quantity):
    return price * quantity
```

#### 2. ドキュメンテーション文字列（Docstring）

**必須**: 全てのクラスと関数（def）にドキュメンテーション文字列を付けること。

**形式**: Google Docstring形式を採用し、**日本語**で記述すること。

```python
def fetch_user_data(user_id: int, include_details: bool = False) -> dict[str, any]:
    """
    ユーザーデータを取得する

    指定されたIDのユーザー情報をデータベースから取得します。

    Args:
        user_id: ユーザーID
        include_details: 詳細情報を含めるかどうか（デフォルト: False）

    Returns:
        dict[str, any]: ユーザー情報を含む辞書

    Raises:
        ValueError: user_idが無効な場合
        DatabaseError: データベース接続エラーが発生した場合

    Examples:
        >>> user = fetch_user_data(123)
        >>> user['name']
        '山田太郎'
    """
    if user_id <= 0:
        raise ValueError("user_idは正の整数である必要があります")

    return {}
```

**参考リンク**:
- [Google Docstring形式（英語）](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html)
- [Google Docstring形式（日本語サンプル）](https://qiita.com/11ohina017/items/118b3b42b612e527dc1d#日本語のサンプルコード)

#### 3. 関数の設計原則

**原則**: 関数は集中して小さく保つこと。

- 1つの関数は1つの責任のみを持つべき
- 複雑な処理は小さな関数に分割する
- 関数の長さは可能な限り短く（推奨: 50行以内）

```python
# ✅ 良い例: 処理を小さな関数に分割 (important-comment)
def process_order(order_data: dict) -> OrderResult:
    """注文を処理する"""
    validated_data = validate_order_data(order_data)
    calculated_price = calculate_total_price(validated_data)
    order = create_order(validated_data, calculated_price)
    send_confirmation_email(order)
    return order

# ❌ 悪い例: 1つの関数に全ての処理を詰め込む (important-comment)
def process_order(order_data: dict) -> OrderResult:
    """注文を処理する"""
    pass
```

#### 4. ネスト構造の制限

**原則**: if/else/elifのネスト構造は**原則1階層、最大2階層まで**とする。

これ以上深くなる場合は、可読性を考慮して関数化すること。

```python
# ✅ 良い例: 早期リターンでネストを浅く保つ (important-comment)
def process_payment(amount: float, user: User) -> PaymentResult:
    """支払いを処理する"""
    if amount <= 0:
        return PaymentResult(success=False, error="金額が無効です")

    if not user.is_verified:
        return PaymentResult(success=False, error="ユーザーが未認証です")

    if user.balance < amount:
        return PaymentResult(success=False, error="残高不足です")

    return execute_payment(amount, user)

# ❌ 悪い例: 深いネスト構造 (important-comment)
def process_payment(amount: float, user: User) -> PaymentResult:
    """支払いを処理する"""
    if amount > 0:
        if user.is_verified:
            if user.balance >= amount:
                return execute_payment(amount, user)
            else:
                return PaymentResult(success=False, error="残高不足です")
        else:
            return PaymentResult(success=False, error="ユーザーが未認証です")
    else:
        return PaymentResult(success=False, error="金額が無効です")
```

#### 5. コードの行の長さ

**原則**: コードの1行の長さは**最大88文字**とする。

これはRuffのデフォルト設定と一致しており、PEP8の推奨範囲内です。

```python
# ✅ 良い例: 適切な改行で88文字以内に収める (important-comment)
def create_user_profile(
    username: str,
    email: str,
    first_name: str,
    last_name: str,
) -> UserProfile:
    """ユーザープロフィールを作成する"""
    return UserProfile(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
```

## パッケージ管理

### uvコマンドリファレンス

#### 基本コマンド

```bash
# パッケージの追加 (important-comment)
uv add fastapi

# バージョン指定でパッケージを追加 (important-comment)
uv add "fastapi>=0.110.0"

# 開発用パッケージの追加 (important-comment)
uv add --dev pytest

# 複数パッケージの同時追加 (important-comment)
uv add fastapi uvicorn pydantic

# パッケージのアップグレード (important-comment)
uv add --upgrade-package fastapi

# パッケージの削除 (important-comment)
uv remove fastapi
```

#### ツールの実行

```bash
# 通常の実行 (important-comment)
uv run uvicorn app.main:app --reload

# 依存関係を固定して実行（本番環境推奨） (important-comment)
uv run --frozen uvicorn app.main:app

# pytest実行 (important-comment)
uv run --frozen pytest

# ruff実行 (important-comment)
uv run --frozen ruff format .
uv run --frozen ruff check .
```

### 依存関係の管理

- `pyproject.toml`: パッケージの依存関係を定義
- `uv.lock`: 正確なバージョンを記録（自動生成）

**重要**: `uv.lock`はバージョン管理に含めること。これにより、チーム全体で同じバージョンの依存関係を使用できます。

## テスト要件

### テストフレームワーク

**使用ツール**: pytest

```bash
# 全テストを実行 (important-comment)
uv run --frozen pytest

# 詳細な出力で実行 (important-comment)
uv run --frozen pytest -v

# カバレッジを表示 (important-comment)
uv run --frozen pytest --cov=app --cov-report=term-missing
```

### テストの原則

1. **カバレッジ**: エッジケースとエラーケースを必ずテストする
2. **新機能**: 新機能を追加したら、必ずテストケースを作成する
3. **バグ修正**: バグ修正を行ったら、回帰テストを追加する
4. **非同期テスト**: 非同期関数のテストには`pytest-asyncio`を使用する

```python
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    """ヘルスチェックエンドポイントのテスト"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_async_function() -> None:
    """非同期関数のテスト"""
    result = await some_async_function()
    assert result is not None
```

## 開発ツール

### Ruff（フォーマッター・リンター）

Ruffは高速なPythonフォーマッター・リンターです。

#### コマンド

```bash
# コードをフォーマット (important-comment)
uv run --frozen ruff format .

# コードをチェック (important-comment)
uv run --frozen ruff check .

# 自動修正可能な問題を修正 (important-comment)
uv run --frozen ruff check . --fix
```

#### 重要な問題

1. **行の長さ（88文字）**: 長すぎる行は自動的に折り返される
2. **インポートの並び替え（I001）**: インポートは自動的にソートされる
3. **使われていないインポート**: 未使用のインポートは削除される

#### 行の折り返し規則

```python
# 文字列: 括弧を使用 (important-comment)
message = (
    "これは非常に長い文字列です。"
    "括弧を使用して複数行に分割します。"
)

# 関数呼び出し: 適切なインデントで複数行に (important-comment)
result = some_function(
    first_argument,
    second_argument,
    third_argument,
    fourth_argument,
)

# インポート: 複数行に分割 (important-comment)
from app.models import (
    User,
    Post,
    Comment,
    Tag,
)
```

### Pyright（型チェッカー）

Pyrightは高速な静的型チェッカーです。

#### コマンド

```bash
# 型チェックを実行 (important-comment)
uv run --frozen pyright
```

#### 要件

1. **Optionalの明示的なNoneチェック**: Optional型は必ずNoneチェックを行う
2. **型の絞り込み**: 条件分岐で型を絞り込む
3. **バージョン警告**: チェックが通る場合、バージョン警告は無視できる

```python
from typing import Optional

def process_user(user: Optional[User]) -> str:
    """ユーザー情報を処理する"""
    if user is None:
        return "ユーザーが見つかりません"

    return user.name
```

### Pre-commit

Pre-commitフックを使用して、コミット前に自動的にチェックを実行します。

#### セットアップ

```bash
# pre-commitのインストール (important-comment)
uv add --dev pre-commit

# フックのインストール (important-comment)
uv run pre-commit install
```

#### 実行

```bash
# 全ファイルに対して実行 (important-comment)
uv run pre-commit run --all-files

# 特定のファイルに対して実行 (important-comment)
uv run pre-commit run --files src/app/main.py
```

git commitを実行すると、自動的にpre-commitフックが実行されます。

## Commit/PRルール

### ブランチ戦略

**重要**: 作業ブランチは**mainブランチから派生**させて作成すること。

**注意**: 本来はdevelopブランチから派生させる設計ですが、現在developブランチが存在しないため、当面はmainブランチから派生させます。将来的にdevelopブランチが作成された際は、developブランチからの派生に移行する予定です。

```bash
# 作業ブランチの作成（現状） (important-comment)
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

### Commitメッセージ

**原則**: Commitコメントはバックログに合った内容を簡潔に記述すること。

```bash
# ✅ 良い例 (important-comment)
git commit -m "feat: ユーザー認証機能を追加"
git commit -m "fix: 価格計算のバグを修正"
git commit -m "docs: APIドキュメントを更新"

# ❌ 悪い例（意図が不明確） (important-comment)
git commit -m "コメント削除"
git commit -m "レビュー対応"
git commit -m "修正"
```

### Commit前のチェック

**必須**: Commit時にpytestを全体に実行し、正常終了しない場合はテストコードに問題があるので、修正するまでpushしないこと。

```bash
# Commit前の確認手順 (important-comment)
# 1. フォーマット (important-comment)
uv run --frozen ruff format .

# 2. リントチェック (important-comment)
uv run --frozen ruff check .

# 3. 型チェック (important-comment)
uv run --frozen pyright

# 4. テスト実行 (important-comment)
uv run --frozen pytest

# 全てが正常に完了したらcommit (important-comment)
git add .
git commit -m "feat: 新機能を追加"
```

## エラー処理

### 例外処理のベストプラクティス

```python
import logging

logger = logging.getLogger(__name__)

# ✅ 良い例: 具体的な例外をキャッチ (important-comment)
try:
    result = await database.fetch_user(user_id)
except UserNotFoundError:
    logger.exception("ユーザーが見つかりませんでした")
    raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
except DatabaseError:
    logger.exception("データベースエラーが発生しました")
    raise HTTPException(status_code=500, detail="内部サーバーエラー")

# ❌ 悪い例: 包括的な例外キャッチ (important-comment)
try:
    result = await database.fetch_user(user_id)
except Exception as e:
    logger.error(f"エラー: {e}")
    raise
```

### ログ出力

```python
# ✅ 良い例: logger.exception()を使用 (important-comment)
try:
    process_data()
except ValueError:
    logger.exception("データ処理に失敗しました")

# ❌ 悪い例: 例外情報を文字列に含める (important-comment)
try:
    process_data()
except ValueError as e:
    logger.exception(f"データ処理に失敗しました: {e}")
```

## PEP8準拠

このプロジェクトはPEP8（Pythonコーディング規約）に準拠します。

### 主要なPEP8ルール

#### インデント
- 4スペースを使用（タブは使用しない）

#### インポート
```python
# 標準ライブラリ (important-comment)
import os
import sys

# サードパーティライブラリ (important-comment)
from fastapi import FastAPI
from pydantic import BaseModel

# ローカルアプリケーション (important-comment)
from app.core.config import settings
from app.models.schemas import UserResponse
```

#### 命名規則
- クラス名: `PascalCase`（例: `UserProfile`）
- 関数名/変数名: `snake_case`（例: `get_user_data`）
- 定数: `UPPER_SNAKE_CASE`（例: `MAX_RETRY_COUNT`）
- プライベート: `_leading_underscore`（例: `_internal_method`）

#### 空白行
- トップレベルの関数とクラス定義の間: 2行
- クラス内のメソッド定義の間: 1行

### 参考リンク

- [PEP8 日本語版](https://pep8-ja.readthedocs.io/ja/latest/)
- [PEP8 英語版（公式）](https://peps.python.org/pep-0008/)

## 参考資料

- [Anthropicで利用されているモダンなPython開発のベストプラクティス](https://zenn.dev/yareyare/articles/d67aa75b37537c)
- [MCP Python SDK - CLAUDE.md](https://github.com/modelcontextprotocol/python-sdk/blob/main/CLAUDE.md)
- [Google Docstring形式](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html)
- [Google Docstring日本語サンプル](https://qiita.com/11ohina017/items/118b3b42b612e527dc1d#日本語のサンプルコード)

## まとめ

このコーディングルールに従うことで、チーム全体で一貫性のある高品質なコードベースを維持できます。

**重要なポイント**:
1. uvのみを使用（pipは禁止）
2. @latestでのインストール禁止（バージョン指定必須）
3. 型ヒント必須
4. Docstring必須（Google形式、日本語）
5. 関数は小さく保つ
6. ネストは最大2階層
7. 行の長さは88文字以内
8. Commit前に必ずテストを実行

質問や不明点がある場合は、チームメンバーに相談してください。
