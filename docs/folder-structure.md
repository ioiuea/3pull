# フォルダ構成ドキュメント

このドキュメントでは、プロジェクトのフォルダ構成と各フォルダの役割について説明します。

## プロジェクト構造

```
.
├── app/                      # Next.jsページルート
│   ├── [lang]/              # ロケールごとの動的ルート
│   │   ├── layout.tsx       # レイアウトコンポーネント
│   │   ├── page.tsx         # ページコンポーネント
│   │   ├── sample/          # サンプルページ
│   │   └── chat/            # AIチャットUIデモページ
│   ├── globals.css          # グローバルスタイル
│   └── favicon.ico          # ファビコン
├── components/               # 再利用可能なReactコンポーネント
│   ├── ui/                  # shadcn/uiコンポーネント
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   └── ...
│   └── LanguageSwitcher.tsx # 言語切り替えコンポーネント
├── store/                   # Zustandストア（クライアント状態管理）
│   └── useDemoStore.ts      # デモストア
├── constants/               # 定数管理
│   ├── index.ts            # エントリーポイント
│   └── error.ts            # エラー定数
├── lib/                     # ライブラリとヘルパー
│   └── utils.ts             # cn()などのユーティリティ関数
├── utils/                    # アプリケーション固有のユーティリティ
│   └── dictionaries.ts      # i18n辞書読み込み関数
├── dictionaries/            # 翻訳ファイル
│   ├── ja.json
│   └── en.json
├── docs/                    # ドキュメント
│   ├── i18n.md
│   ├── folder-structure.md
│   └── ...
├── middleware.ts            # Next.jsミドルウェア
└── components.json          # shadcn/ui設定
```

## フォルダの役割

### /app - UIコンポーネント専用

`/app` フォルダは、**UIのReactコンポーネントのみを配置する場所**です。

**配置するもの:**
- ページコンポーネント (page.tsx)
- レイアウトコンポーネント (layout.tsx)
- UIコンポーネント (components/)
- スタイルファイル (globals.css)

**配置しないもの:**
- ビジネスロジック
- ヘルパー関数
- ユーティリティ関数
- データフェッチング関数（コンポーネント内での使用を除く）

### /components - 再利用可能なUIコンポーネント

`/components` フォルダは、**プロジェクト全体で再利用可能なReactコンポーネントを配置する場所**です。

**配置するもの:**
- クライアントサイドコンポーネント（'use client'を使用）
- shadcn/uiコンポーネント（/components/ui/）
- カスタムUIコンポーネント
- 共通のインタラクティブコンポーネント

**特徴:**
- /app配下ではなく、プロジェクトルート直下に配置
- shadcn/uiのデフォルト設定に従い、UIコンポーネントは/components/ui/に配置
- ページ間で共有される再利用可能なコンポーネント

**例:**
- LanguageSwitcher.tsx - 言語切り替えコンポーネント
- /ui/button.tsx - shadcn Buttonコンポーネント
- /ui/input.tsx - shadcn Inputコンポーネント
- /ui/sheet.tsx - shadcn Sheetコンポーネント（モバイルメニュー用）

### /lib - ライブラリとヘルパー関数

`/lib` フォルダは、**shadcn/uiに関連するヘルパー関数を配置する場所**です。

**配置するもの:**
- cn()関数（クラス名マージユーティリティ）
- shadcn関連のヘルパー関数
- UIに関連するユーティリティ

**例:**
- utils.ts - cn()関数とその他のUIユーティリティ

### /utils - ヘルパー関数とユーティリティ

`/utils` フォルダは、**アプリ内のヘルパー関数やユーティリティをまとめる場所**です。

**配置するもの:**
- 汎用的なヘルパー関数
- データ変換関数
- フォーマット関数
- サーバー専用の関数（'server-only'を使用）
- 型定義のエクスポート

**例:**
- dictionaries.ts - i18n辞書読み込み関数とLocale型定義
- formatDate.ts - 日付フォーマット関数
- validation.ts - バリデーション関数

**使用ルール:**
1. UIに依存しない純粋な関数を配置
2. 複数の場所で使用される共通ロジックを配置
3. サーバー専用の関数には `'server-only'` をインポート
4. 明確な関数名と型定義を使用

### /store - クライアント状態管理

`/store` フォルダは、**Zustandを使用したクライアントサイドのグローバル状態を定義する場所**です。

**配置するもの:**
- Zustandストア定義ファイル
- クライアントコンポーネント間で共有される状態
- グローバルな状態管理ロジック

**特徴:**
- 全てのファイルに `'use client'` ディレクティブを使用
- コンポーネント間のPropsバケツリレーを回避
- TypeScript型定義を必ず使用
- ストア名は `use{Name}Store` の命名規則に従う

**使用ケース:**
- ユーザー認証情報
- アプリケーション設定
- 複数のコンポーネント間で共有される状態
- Propsで渡すと深いネストが必要になる状態

**使用しないケース:**
- 単一コンポーネント内でのみ使用される状態（React useStateを使用）
- サーバーサイドの状態（Server Componentsで処理）

**例:**
- useDemoStore.ts - デモストア（整数、文字列、オブジェクトの状態管理例）
- useUserStore.ts - ユーザー情報ストア
- useAppStore.ts - アプリケーション設定ストア

**詳細:**
詳しい使用方法とガイドラインは `/docs/state-management.md` を参照してください。

### /constants - 定数管理

`/constants` フォルダは、**プロジェクト全体で使用する定数を一元管理する場所**です。

**配置するもの:**
- アプリケーション全体で共有される定数
- エラーコードとエラーメッセージ
- ルート定義
- 設定値（環境変数以外）

**特徴:**
- 全ての定数は `index.ts` を経由してエクスポート
- コンポーネントからは `@/constants` でインポート
- TypeScript型定義を必ず使用
- 定数名は `UPPER_SNAKE_CASE` の命名規則に従う

**インポート方法:**
```typescript
import { ERR_AUTH_001, ERROR_MESSAGES } from '@/constants'
```

**例:**
- error.ts - エラーコードとエラーメッセージ
- routes.ts - ルート定義
- config.ts - アプリケーション設定

**詳細:**
詳しい使用方法とガイドラインは `/docs/constants-management.md` を参照してください。

## インポートパス

プロジェクトでは、`@/` エイリアスを使用してプロジェクトルートからの絶対パスでインポートします。

**例:**
```typescript
// utils フォルダから (important-comment)
import { getDictionary } from '@/utils/dictionaries'

// dictionaries フォルダから (important-comment)
import jaDict from '@/dictionaries/ja.json'

// components フォルダから (important-comment)
import { LanguageSwitcher } from '@/components/LanguageSwitcher'
```

## ベストプラクティス

1. **関心の分離**: UI (app/)、ロジック (utils/)、データ (dictionaries/) を明確に分離
2. **再利用性**: 共通のロジックは utils/ に配置して再利用
3. **型安全性**: TypeScript の型定義を活用
4. **サーバー/クライアント**: サーバー専用の関数には 'server-only' を使用
5. **命名規則**: ファイル名とフォルダ名は小文字とハイフンを使用（例: folder-structure.md）
