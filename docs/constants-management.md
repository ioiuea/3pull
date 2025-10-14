# 定数管理ドキュメント

このドキュメントでは、プロジェクトにおける定数の管理方法について説明します。

## 概要

`/constants` フォルダは、**プロジェクト全体で使用する定数をまとめて管理する場所**です。

アプリケーション全体で共有される定数を一元管理することで、以下のメリットがあります:

- **一貫性の確保**: 同じ値を複数の場所で定義することを防ぐ
- **保守性の向上**: 値の変更が必要な場合、1箇所を修正するだけで済む
- **型安全性**: TypeScriptの型システムを活用して、誤った値の使用を防ぐ
- **可読性の向上**: 定数に意味のある名前を付けることで、コードの意図が明確になる

## フォルダ構成

```
constants/
├── index.ts          # エントリーポイント（全ての定数をエクスポート）
├── error.ts          # エラーコードとエラーメッセージ
├── routes.ts         # ルート定義（例）
├── config.ts         # アプリケーション設定（例）
└── ...               # その他の定数ファイル
```

## 基本ルール

### 1. インポートは必ずindex.tsから行う

**必須**: コンポーネントやユーティリティから定数を使用する際は、必ず `/constants/index.ts` からインポートすること。

**良い例:**

```typescript
import { ERR_AUTH_001, ERROR_MESSAGES } from '@/constants'
```

**悪い例:**

```typescript
import { ERR_AUTH_001 } from '@/constants/error'
```

### 2. 新しい定数ファイルを追加する場合

新しい定数ファイルを作成したら、必ず `index.ts` に追加すること。

**手順:**

1. 新しい定数ファイルを作成（例: `routes.ts`）
2. `index.ts` に以下を追加:

```typescript
export * from './routes'
```

### 3. 命名規則

**定数名:**
- `UPPER_SNAKE_CASE` を使用
- 定数の用途が明確にわかる名前を付ける

**良い例:**

```typescript
export const API_BASE_URL = 'https://api.example.com'
export const MAX_RETRY_COUNT = 3
export const DEFAULT_LOCALE = 'ja'
```

**悪い例:**

```typescript
export const url = 'https://api.example.com' // 小文字
export const MAX = 3 // 用途が不明
```


### 4. TSDocコメント

**必須**: エクスポートされる定数には、TSDocコメントを付けること。

**例:**

```typescript
/**
 * APIのベースURL
 */
export const API_BASE_URL = 'https://api.example.com'

/**
 * 最大リトライ回数
 */
export const MAX_RETRY_COUNT = 3
```

## エラー定数の管理

エラーコードとエラーメッセージは `error.ts` で管理します。

### エラーコードの命名規則

```
ERR_{カテゴリ}_{連番}
```

**カテゴリ例:**
- `AUTH` - 認証関連
- `VALIDATION` - バリデーション関連
- `NETWORK` - ネットワーク関連
- `DATABASE` - データベース関連

**例:**

```typescript
export const ERR_AUTH_001 = 'ERR_AUTH_001'
export const ERR_AUTH_002 = 'ERR_AUTH_002'
export const ERR_VALIDATION_001 = 'ERR_VALIDATION_001'
```

### エラーメッセージ

**重要**: エラーメッセージは共通言語として英語で記載すること。

```typescript
export const ERROR_MESSAGES = {
  [ERR_AUTH_001]: 'Authentication failed. Please log in again.',
  [ERR_AUTH_002]: 'Your session has expired. Please log in again.',
  [ERR_AUTH_003]: 'You do not have permission to access this resource.',
  [ERR_VALIDATION_001]: 'There was an error in your input. Please check and try again.',
  [ERR_VALIDATION_002]: 'A required field is missing.',
  [ERR_NETWORK_001]: 'A network error has occurred. Please check your connection.',
  [ERR_NETWORK_002]: 'Unable to connect to the server. Please try again later.',
} as const
```

### 使用例

```typescript
import { ERR_AUTH_001, getErrorMessage } from '@/constants'

try {
  await authenticate()
} catch (error) {
  console.error('Authentication failed:', error)
  
  const message = getErrorMessage(ERR_AUTH_001)
  showError(message)
}
```

## ベストプラクティス

### 1. マジックナンバーを避ける

数値を直接コードに書くのではなく、定数として定義する。

**悪い例:**

```typescript
if (retryCount > 3) {
  throw new Error('Max retries exceeded')
}
```

**良い例:**

```typescript
import { MAX_RETRY_COUNT } from '@/constants'

if (retryCount > MAX_RETRY_COUNT) {
  throw new Error('Max retries exceeded')
}
```

### 2. 環境変数と定数を分ける

環境変数（`.env`）とアプリケーション定数は分けて管理する。

- 環境変数: デプロイ環境によって変わる値（APIキー、データベースURLなど）
- 定数: アプリケーションロジックに固有の値（リトライ回数、タイムアウト時間など）

### 3. グループ化

関連する定数は同じファイルにまとめる。

**例:**

```typescript
export const ROUTE_HOME = '/'
export const ROUTE_CHAT = '/chat'
export const ROUTE_SETTINGS = '/settings'

export const MAX_FILE_SIZE = 5 * 1024 * 1024
export const SUPPORTED_LOCALES = ['ja', 'en'] as const
```

## 注意事項

- **既存のコードを変更する場合**: 既に定数として定義されている値があれば、それを使用すること
- **重複を避ける**: 同じ値を複数の定数として定義しないこと
- **型安全性**: `as const` を使用して、より厳密な型を定義することを推奨
