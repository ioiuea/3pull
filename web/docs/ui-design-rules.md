# UIデザインルールドキュメント

## 概要

このドキュメントでは、プロジェクトのUIデザインに関するルールとガイドラインを説明します。

## メインターゲット解像度

### 1280×580 - Windowsノートパソコンユーザー

**背景:**
- Windows 13-15インチノートPCを前提
- フルHD（1920×1080）対応だが、DPIスケールが150%の端末を想定
- フルHD × 150% DPI = 1920÷1.5 = 1280px（横幅）
- 縦横比16:9の理論値：1280×720
- ブラウザUI（タブバー、アドレスバー、お気に入りバー）：約90px
- Windowsタスクバー：約50px
- 実効viewport：1280×580px

**重要性:**
このターゲット解像度は、最も一般的なビジネス用途のWindows端末における実際の使用可能領域を表しています。

## Tailwind CSSブレークポイント

| ブレークポイント | 範囲（px） | 用途 |
|-----------------|-----------|------|
| なし | 0-639 | モバイル利用者 |
| sm | 640-767 | レスポンシブ対応（ウィンドウサイズ変更時） |
| md | 768-1023 | レスポンシブ対応（ウィンドウサイズ変更時） |
| lg | 1024-1279 | レスポンシブ対応（ウィンドウサイズ変更時） |
| xl | 1280-1535 | **Windowsノートパソコン利用者（メインターゲット）** |
| 2xl | 1536以上 | **フルHD描画端末利用者** |

## 実装時のポイント

### 1. メインターゲット（xl: 1280-1535px）
- Windows 13-15インチノートPC利用者向け
- 実効viewport 1280×580を前提としたデザイン
- すべての主要機能が表示されている状態だがViewportの高さを意識してヘッダーなどを排除

### 2. フルHD端末（2xl: 1536px以上）
- デスクトップPC、大型ディスプレイ利用者向け
- xlと原則同じレイアウトだが、より広いスペースを活用
- パネル幅を適切に拡大し、読みやすさを向上

### 3. モバイル（なし: 0-639px）
- スマートフォン、タブレット利用者向け
- シングルパネルレイアウト
- タッチ操作に最適化されたUI要素サイズ

### 4. レスポンシブ対応（sm, md, lg: 640-1279px）
- ブラウザのウィンドウサイズ変更時の中間状態
- サイドメニューなどアイコンのみ表示またはハンバーガーメニュー化

## レイアウトガイドライン

### AIチャットUIの構成(例)

#### モバイル（< 640px）
```
┌─────────────────────┐
│  [Menu] Chat Title  │ ← ヘッダー（Sheetトリガー）
├─────────────────────┤
│                     │
│   Chat Display      │ ← チャット表示エリア
│                     │
│                     │
├─────────────────────┤
│  [Input] [Send]     │ ← 入力エリア
└─────────────────────┘
```

#### lg（1024-1279px）
```
┌───┬─────────────────┐
│ S │                 │ ← サイドメニュー（S）+ ヘッダー（Chat Title非表示）
│ i │                 │
│ d │  Chat Display   │
│ e │                 │ ← チャット表示エリア
│   │                 │
│   │                 │
│   ├─────────────────┤
│   │  [Input] [Send] │ ← 入力エリア
└───┴─────────────────┘
```

#### xl（1280-1535px）
```
┌───┬────────┬──────────────┬─────────┐
│ S │ Thread │              │ Prompts │ ← サイドメニュー + 3パネル（Chat Title非表示）
│ i ├────────│              │─────────┤
│ d │        │ Chat Display │         │
│ e │ Thread │              │ Prompt  │ ← 各エリア
│   │ Mgmt   │              │ Mgmt    │
│   │        │              │         │
│   │        ├──────────────┤         │
│   │        │ [Input][Send]│         │ ← 入力エリア
└───┴────────┴──────────────┴─────────┘
```

#### 2xl（1536px以上）
```
┌───┬────────┬──────────────┬─────────┐
│ S │ Thread │ Chat Title   │ Prompts │ ← サイドメニュー + 3パネル（Chat Title表示）
│ i ├────────┼──────────────┼─────────┤
│ d │        │              │         │
│ e │ Thread │ Chat Display │ Prompt  │ ← 各エリア
│   │ Mgmt   │              │ Mgmt    │
│   │        │              │         │
│   │        ├──────────────┤         │
│   │        │ [Input][Send]│         │ ← 入力エリア
└───┴────────┴──────────────┴─────────┘
```

## カラーシステム

### CSS変数の使用
shadcn/uiのCSS変数システムを使用し、一貫性のあるカラーパレットを維持：

- `--background` / `--foreground`: 背景と前景色
- `--primary` / `--primary-foreground`: プライマリカラー
- `--secondary` / `--secondary-foreground`: セカンダリカラー
- `--muted` / `--muted-foreground`: ミュートカラー
- `--accent` / `--accent-foreground`: アクセントカラー
- `--border` / `--input` / `--ring`: 境界線とフォーカスリング

### ダークモード対応
- `prefers-color-scheme: dark` メディアクエリを使用
- すべてのCSS変数にダークモード用の値を定義
- 自動的にシステム設定に応じて切り替え

## コンポーネント設計原則

### 1. shadcn/uiコンポーネントの活用
- Button, Input, ScrollArea, Separator, Sheet, Sidebarなどを使用
- カスタマイズは最小限に抑え、デフォルトのスタイルを尊重
- cn()ユーティリティを使用してクラス名を結合

### 2. レスポンシブ設計
- モバイルファーストアプローチ
- Tailwindのブレークポイントプレフィックスを使用（sm:, md:, lg:, xl:, 2xl:）
- 隠す要素には `hidden` と `xl:flex` などの組み合わせを使用

### 3. アクセシビリティ
- セマンティックHTML要素を使用
- キーボードナビゲーションのサポート
- 適切なARIA属性の設定

## 実装例

### レスポンシブな要素の表示/非表示

```tsx
{/* モバイルでは非表示、xl以上で表示 */}
<div className="hidden xl:flex w-64 flex-col">
  {/* コンテンツ */}
</div>

{/* lg以下では非表示、xl以上で表示 */}
<div className="hidden xl:block">
  {/* コンテンツ */}
</div>

{/* モバイルのみ表示、md以上で非表示 */}
<div className="md:hidden">
  {/* コンテンツ */}
</div>
```
## アニメーション実装ガイドライン

### 1. motionライブラリの使用

**必須**: アニメーション実装には [motion](https://motion.dev/docs/react) ライブラリを使用すること。

motionは高性能で宣言的なReactアニメーションライブラリです。

**基本的な使用方法:**

```typescript
import { motion } from 'motion/react'

<motion.div
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  transition={{ duration: 0.5 }}
/>
```

### 2. アニメーションの種類と使用場面

#### 2.1 エントランスアニメーション

ページやコンポーネントの初期表示時に使用:

```typescript
<motion.section
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.6, ease: 'easeOut' }}
>
  <h1>タイトル</h1>
  <p>説明文</p>
</motion.section>
```

**推奨設定:**
- duration: 0.4〜0.6秒
- ease: 'easeOut' または 'easeInOut'
- y: 20〜50px のスライド

#### 2.2 インタラクションアニメーション

ボタンやカードなどのホバー・タップ時に使用:

```typescript
<motion.button
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
  transition={{ duration: 0.2 }}
>
  クリック
</motion.button>
```

**推奨設定:**
- ホバー: scale: 1.02〜1.05
- タップ: scale: 0.95〜0.98
- duration: 0.1〜0.2秒

#### 2.3 スクロールアニメーション

スクロール時に要素を表示する場合:

```typescript
<motion.div
  initial={{ opacity: 0, y: 50 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ once: true, margin: '-100px' }}
  transition={{ duration: 0.6 }}
>
  スクロールで表示される要素
</motion.div>
```

**推奨設定:**
- viewport.once: true (一度だけアニメーション)
- viewport.margin: '-100px' (少し早めに発火)
- duration: 0.5〜0.8秒

#### 2.4 段階的アニメーション（Stagger）

複数要素を順次表示する場合:

```typescript
<motion.div
  initial="hidden"
  animate="visible"
  variants={{
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  }}
>
  {features.map((feature) => (
    <motion.div
      key={feature.id}
      variants={{
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0 }
      }}
    >
      {feature.content}
    </motion.div>
  ))}
</motion.div>
```

**推奨設定:**
- staggerChildren: 0.05〜0.15秒
- 子要素のアニメーションは軽量に

### 3. パフォーマンス最適化

**優先的に使用するプロパティ:**
- `opacity` - 透明度
- `scale` - 拡大縮小
- `x`, `y` - 平行移動
- `rotate` - 回転

これらはGPUアクセラレーションに対応しており、高性能です。

**避けるべきプロパティ:**
- `width`, `height` - レイアウトの再計算が発生
- `top`, `left` - 代わりに `x`, `y` を使用
- 複雑な `filter` や `backdrop-filter`

### 4. アクセシビリティ対応

アニメーションを望まないユーザーへの配慮:

```typescript
import { motion, useReducedMotion } from 'motion/react'

export function AnimatedComponent() {
  const shouldReduceMotion = useReducedMotion()
  
  return (
    <motion.div
      initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: shouldReduceMotion ? 0 : 0.5 }}
    >
      コンテンツ
    </motion.div>
  )
}
```

### 5. アニメーション設計原則

1. **控えめに**: アニメーションは控えめに使用し、ユーザー体験を妨げないこと
2. **意図的に**: アニメーションには明確な目的を持たせること（注目を集める、階層を示すなど）
3. **一貫性**: プロジェクト全体で一貫したタイミングとイージングを使用
4. **高速に**: アニメーションは素早く（0.2〜0.6秒程度）
5. **目的に応じて**: 
   - フィードバック: 0.1〜0.2秒（即座）
   - 遷移: 0.3〜0.5秒（スムーズ）
   - 演出: 0.5〜0.8秒（印象的）

詳細は [motion公式ドキュメント](https://motion.dev/docs/react) を参照してください。
