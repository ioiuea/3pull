# 国際化（i18n）実装ドキュメント

## 概要

このプロジェクトは Next.js 15 App Router の公式パターンを使用した国際化（i18n）を実装しています。現在、日本語、英語の2言語をサポートしています。

## アーキテクチャ

### ディレクトリ構造

```
.
├── middleware.ts                    # ロケール検出とリダイレクト
├── dictionaries/                    # 翻訳ファイル
│   ├── ja.json                     # 日本語
│   └── en.json                     # 英語
├── utils/
│   └── dictionaries.ts             # 辞書読み込み関数
└── app/
    └── [lang]/                      # ロケールごとの動的ルート
        ├── layout.tsx               # 言語対応ルートレイアウト
        ├── page.tsx                 # ホームページ
        ├── sample/
        │   └── page.tsx            # i18nサンプルページ
        └── components/
            └── LanguageSwitcher.tsx # 言語切り替えコンポーネント
```

### コンポーネントの役割

#### 1. middleware.ts
- **目的**: ブラウザの `Accept-Language` ヘッダーから優先言語を検出し、適切なロケールパスにリダイレクト
- **動作**:
  1. リクエストのパス名を確認
  2. パスにロケールが含まれていない場合、`Accept-Language` ヘッダーを解析
  3. サポートされているロケールと照合
  4. 適切なロケールパス（例：`/ja`、`/en`）にリダイレクト
- **デフォルトロケール**: `ja`（日本語）

#### 2. dictionaries/
- **目的**: 各言語の翻訳文字列を管理
- **フォーマット**: JSON
- **構造**: ネストされたオブジェクトで、各キーが翻訳キーを表す

例：
```json
{
  "home": {
    "title": "タイトル",
    "description": "説明"
  },
  "languages": {
    "ja": "日本語",
    "en": "English"
  }
}
```

#### 3. utils/dictionaries.ts
- **目的**: 動的に辞書ファイルを読み込む
- **特徴**:
  - `server-only` パッケージを使用してサーバー専用を保証
  - 動的インポートによる最適化
  - TypeScript型定義（`Locale`型）の提供

#### 4. app/[lang]/layout.tsx
- **目的**: 全ページに適用されるルートレイアウト
- **機能**:
  - `generateStaticParams` で全ロケールの静的ページを生成
  - HTML `lang` 属性を動的に設定
  - LanguageSwitcher コンポーネントを配置

#### 5. app/[lang]/components/LanguageSwitcher.tsx
- **目的**: ユーザーが言語を切り替えるためのUIコンポーネント
- **タイプ**: クライアントコンポーネント（`'use client'`）
- **機能**:
  - 現在の言語をハイライト表示
  - `useRouter` と `usePathname` を使用して言語切り替え時にナビゲーション
  - パス内のロケールセグメントを置換

## 新しい言語の追加方法

### ステップ1: 辞書ファイルを作成

`dictionaries/` フォルダに新しい言語のJSONファイルを作成します。

```bash
# 例: スペイン語を追加
touch dictionaries/es.json
```

### ステップ2: 翻訳を追加

既存の辞書ファイルと同じ構造で翻訳を追加します。

```json
{
  "home": {
    "title": "Crear aplicación Next",
    "description": "Generado por crear aplicación next"
  }
}
```

### ステップ3: middleware.ts を更新

サポートするロケールのリストに新しい言語コードを追加します。

```typescript
const locales = ['ja', 'en', 'es']  // 'es' を追加
```

### ステップ4: dictionaries.ts を更新

`utils/dictionaries.ts` の辞書インポートマップに新しい言語を追加します。

```typescript
const dictionaries = {
  ja: () => import('@/dictionaries/ja.json').then(module => module.default),
  en: () => import('@/dictionaries/en.json').then(module => module.default),
  es: () => import('@/dictionaries/es.json').then(module => module.default), // 追加
}
```

### ステップ5: LanguageSwitcher.tsx を更新

言語名マップに新しい言語を追加します。

```typescript
const languages: Record<Locale, string> = {
  ja: '日本語',
  en: 'English',
  es: 'Español', // 追加
}
```

### ステップ6: layout.tsx を更新

`generateStaticParams` に新しいロケールを追加します。

```typescript
export async function generateStaticParams() {
  return [
    { lang: 'ja' },
    { lang: 'en' },
    { lang: 'es' }, // 追加
  ]
}
```

## 新しい翻訳文字列の追加方法

### ステップ1: 全ての辞書ファイルに翻訳を追加

各言語ファイル（ja.json、en.json）に同じキーで翻訳を追加します。

```json
{
  "newSection": {
    "title": "新しいセクション",
    "description": "説明文"
  }
}
```

### ステップ2: コンポーネントで使用

```typescript
export default async function MyPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  const dict = await getDictionary(lang as Locale);
  
  return (
    <div>
      <h1>{dict.newSection.title}</h1>
      <p>{dict.newSection.description}</p>
    </div>
  );
}
```

## ベストプラクティス

### 1. 辞書構造の一貫性
- 全ての言語ファイルで同じキー構造を維持
- ネストを使用して論理的にグループ化
- キー名は英語の camelCase を使用

### 2. 翻訳のメンテナンス
- 新しい翻訳を追加する際は、全ての言語ファイルを同時に更新
- 未翻訳の文字列は英語で記載し、TODO コメントを付ける
- 定期的に翻訳の品質をレビュー

### 3. パフォーマンス最適化
- `server-only` パッケージを使用して辞書がクライアントにバンドルされないように保証
- 動的インポートによる辞書の遅延読み込み
- `generateStaticParams` を使用した静的生成でビルド時に全ロケールを生成

### 4. TypeScript型安全性
- `Locale` 型を使用してロケールコードの型安全性を保証
- 辞書オブジェクトの型推論を活用
- `as Locale` 型アサーションは必要な場合のみ使用

### 5. URL構造
- SEO対応のため、ロケールをURLパスに含める（例：`/ja/about`、`/en/about`）
- 全てのリンクでロケールを保持
- `useRouter` と `usePathname` を使用してクライアント側のナビゲーションを実装

## トラブルシューティング

### 問題: ミドルウェアがリダイレクトしない
- **原因**: `middleware.ts` の `matcher` 設定が間違っている可能性
- **解決策**: `config.matcher` が正しいパターンを除外しているか確認

### 問題: 翻訳が表示されない
- **原因**: 辞書ファイルのキーが間違っている、または辞書が読み込まれていない
- **解決策**: 
  1. ブラウザの開発者ツールでコンソールエラーを確認
  2. 辞書ファイルのキーが正しいか確認
  3. `getDictionary` 関数が正しく呼び出されているか確認

### 問題: ビルドエラー
- **原因**: TypeScript型エラー、または辞書ファイルの構造が不一致
- **解決策**:
  1. `npm run build` でエラー詳細を確認
  2. 全ての辞書ファイルが同じ構造を持っているか確認
  3. `Locale` 型定義が最新か確認

### 問題: 言語切り替えが動作しない
- **原因**: LanguageSwitcher コンポーネントのルーティングロジックが間違っている
- **解決策**:
  1. ブラウザの開発者ツールでコンソールエラーを確認
  2. `usePathname` が正しいパスを返しているか確認
  3. ロケールの置換ロジックが正しいか確認

## 参考資料

- [Next.js 国際化ドキュメント](https://nextjs.org/docs/app/building-your-application/routing/internationalization)
- [Next.js App Router](https://nextjs.org/docs/app)
- [MDN: Accept-Language](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Accept-Language)

## 更新履歴

- **2024年10月**: 初版作成 - ja, en の2言語サポート
- **2024年10月**: dictionaries.tsをutilsフォルダに移動、フォルダ構成ドキュメント追加
