# コーディングルール

このドキュメントでは、本プロジェクトにおけるコーディングルールを定義します。

## 概要

このプロジェクトは、TypeScript、React、Next.js 15 App Router、TailwindCSS、shadcn/uiを使用して開発されています。一貫性のある高品質なコードベースを維持するため、以下のコーディングルールに従ってください。

## ベースとなるルール

本プロジェクトのTypeScriptコーディング規約は、[TypeScript Deep Dive Style Guide](https://typescript-jp.gitbook.io/deep-dive/styleguide)をベースとしています。

### 主要な規約

**命名規則:**
- 変数と関数: `camelCase`
- クラス: `PascalCase`
- インターフェース: `PascalCase` (接頭辞 `I` は使用しない)
- タイプ: `PascalCase`
- Enum: `PascalCase` (名前とメンバー両方)
- ファイル名: `camelCase` (コンポーネントは `PascalCase`)

**フォーマット:**
- インデント: 2スペース (タブは使用しない)
- 引用符: シングルクォート `'` を使用
- セミコロン: 必ず使用
- 配列: `Foo[]` を使用 (`Array<Foo>` ではなく)
- 等価演算子: `===` を使用 (`==` ではなく)

**型定義:**
- `type` vs `interface`: 
  - ユニオン型や交差型には `type` を使用
  - `extends` や `implements` には `interface` を使用

## TypeScript コーディング規約

### 1. 関数のドキュメンテーション

**必須**: すべての関数の上部に、その機能を説明するTSDocコメントを記載すること。

TSDocの標準については [https://tsdoc.org/](https://tsdoc.org/) を参照してください。

**例:**

```typescript
/**
 * ユーザー情報を取得します
 * @param userId - 取得するユーザーのID
 * @returns ユーザー情報を含むPromise
 * @throws {Error} ユーザーが見つからない場合
 */
async function getUserById(userId: string): Promise<User> {
  const user = await db.users.findUnique({ where: { id: userId } })
  
  if (!user) {
    throw new Error(`User with id ${userId} not found`)
  }
  
  return user
}

/**
 * 2つの数値を加算します
 * @param a - 第一項
 * @param b - 第二項
 * @returns 加算結果
 */
function add(a: number, b: number): number {
  return a + b
}

/**
 * フォームデータを検証します
 * @param data - 検証するフォームデータ
 * @returns 検証結果とエラーメッセージ
 */
function validateForm(data: FormData): ValidationResult {
  return { isValid: true, errors: [] }
}
```

**エクスポートされる関数やクラスには必ずTSDocコメントを付けてください。**

### 2. 論理的なブロック間の空行

**必須**: 論理的なブロック間には適切な空行を入れて、コードを見やすくすること。

**良い例:**

```typescript
export function processUserData(userId: string) {
  const user = getUserById(userId)
  const preferences = getUserPreferences(userId)
  
  const processedUser = {
    ...user,
    fullName: `${user.firstName} ${user.lastName}`,
  }
  
  saveProcessedUser(processedUser)
  logActivity('user_processed', userId)
  
  return processedUser
}
```

**悪い例:**

```typescript
export function processUserData(userId: string) {
  const user = getUserById(userId)
  const preferences = getUserPreferences(userId)
  const processedUser = {
    ...user,
    fullName: `${user.firstName} ${user.lastName}`,
  }
  saveProcessedUser(processedUser)
  logActivity('user_processed', userId)
  return processedUser
}
```

### 3. 例外処理

**必須**: 例外をキャッチして、適切なエラーメッセージを出力すること。

**良い例:**

```typescript
async function fetchUserData(userId: string): Promise<User> {
  try {
    const response = await fetch(`/api/users/${userId}`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch user: ${response.statusText}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('Error fetching user data:', error)
    throw new Error(`Unable to fetch user ${userId}: ${error.message}`)
  }
}

async function saveUserSettings(settings: UserSettings): Promise<void> {
  try {
    await db.settings.update({
      where: { userId: settings.userId },
      data: settings,
    })
  } catch (error) {
    console.error('Failed to save user settings:', {
      userId: settings.userId,
      error: error.message,
    })
    throw new Error('設定の保存に失敗しました。もう一度お試しください。')
  }
}
```

**エラーメッセージは:**
- ユーザー向けメッセージは日本語で記載
- デバッグ情報（ログ）は英語で記載可能
- エラーの原因と対処方法を明確に伝える

## React コンポーネント規約

### 1. コンポーネントの定義

**必須**: Reactコンポーネントは原則アロー関数で作成すること。

**良い例:**

```typescript
interface ButtonProps {
  label: string
  onClick: () => void
}

export const Button = ({ label, onClick }: ButtonProps) => {
  return (
    <button onClick={onClick}>
      {label}
    </button>
  )
}
```

**例外**: 通常の関数宣言も許容されますが、プロジェクト全体で一貫性を保つこと。

```typescript
export function Button({ label, onClick }: ButtonProps) {
  return (
    <button onClick={onClick}>
      {label}
    </button>
  )
}
```

### 2. App Router のルーティング構造

**必須**: App Routerのルーティングは各featureごとに `page.tsx` を配置し、サーバーサイドコンポーネントとして配置すること。

**ディレクトリ構造:**

```
app/
└── [lang]/
    ├── page.tsx              # ホームページ (SSR) (important-comment)
    ├── chat/
    │   └── page.tsx          # チャット機能 (SSR) (important-comment)
    ├── zustand-demo/
    │   └── page.tsx          # Zustandデモ (SSR) (important-comment)
    └── sample/
        └── page.tsx          # サンプルページ (SSR) (important-comment)
```

**feature名について:**
- `/app/[lang]/chat/page.tsx` の場合、`chat` がfeature名
- `/app/[lang]/zustand-demo/page.tsx` の場合、`zustand-demo` がfeature名

**page.tsx の例:**

```typescript
import { getDictionary, type Locale } from '@/utils/dictionaries'
import { ChatClient } from '@/components/chat'

export default async function ChatPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  const dict = await getDictionary(lang as Locale);
  
  return <ChatClient dict={dict.chat} />
}
```

### 3. Feature名の命名規則

**禁止**: VSCode上で特別な意味を持つ（フォルダアイコンが変わる）名前は使用しないこと。

**避けるべきfeature名:**
- `components` (VSCodeの特殊フォルダ)
- `node_modules` (npmパッケージ)
- `public` (静的ファイル)
- `lib` (ライブラリ)
- `utils` (ユーティリティ)
- `src` (ソースフォルダ)
- `test` / `tests` (テストフォルダ)
- `docs` (ドキュメント)
- `assets` (アセット)

**推奨されるfeature名:**
- `chat` - チャット機能
- `zustand-demo` - Zustandデモ
- `user-profile` - ユーザープロフィール
- `settings` - 設定
- `dashboard` - ダッシュボード

### 4. コンポーネントの配置構造

**必須**: クライアントコンポーネントは `/components` フォルダにfeatureと対になるフォルダ構成で配置すること。

**ディレクトリ構造:**

```
app/
└── [lang]/
    └── chat/
        └── page.tsx          # SSRコンポーネント (important-comment)

components/
├── chat/                     # chatフィーチャー専用 (important-comment)
│   ├── index.tsx            # エントリーポイント ('use client') (important-comment)
│   ├── MessageList.tsx      # chatフィーチャーで使用 (important-comment)
│   ├── MessageInput.tsx     # chatフィーチャーで使用 (important-comment)
│   └── ThreadSidebar.tsx    # chatフィーチャーで使用 (important-comment)
├── common/                   # 複数のフィーチャーで共通利用 (important-comment)
│   ├── Header.tsx
│   ├── Footer.tsx
│   └── LoadingSpinner.tsx
└── ui/                       # shadcn/uiコンポーネント (important-comment)
    ├── button.tsx
    ├── input.tsx
    └── separator.tsx
```

**ルール:**
- `/app/[lang]/chat/page.tsx` (SSR) は `/components/chat/index.tsx` ('use client') を管理して呼び出す
- 各feature専用のコンポーネントは `/components/[feature]/` で管理
- 複数のfeatureで共通して再利用するコンポーネントは `/components/common/` で管理
- shadcn/uiのコンポーネントは `/components/ui/` で管理

**例: page.tsx からの呼び出し**

```typescript
import { getDictionary, type Locale } from '@/utils/dictionaries'
import { ChatClient } from '@/components/chat'

export default async function ChatPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  const dict = await getDictionary(lang as Locale);
  
  return <ChatClient dict={dict.chat} />
}
```

```typescript
'use client'

import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { ThreadSidebar } from './ThreadSidebar'

export function ChatClient({ dict }: ChatClientProps) {
  return (
    <div>
      <ThreadSidebar />
      <MessageList />
      <MessageInput />
    </div>
  )
}
```

### 5. Feature名の一貫性

**必須**: feature名は `/app` 配下と `/components` 配下で一貫して同一名で管理すること。

**良い例:**
- `/app/[lang]/user-profile/page.tsx`
- `/components/user-profile/index.tsx`

**悪い例:**
- `/app/[lang]/user-profile/page.tsx`
- `/components/profile/index.tsx` ❌ (名前が不一致)

### 6. index.tsx の使用

**必須**: `components/[feature]/` の起点となるコンポーネントのファイル名は `index.tsx` にすること。

これにより、親コンポーネント（page.tsx）からのインポートが簡潔になり、理解しやすくなります。

**良い例:**

```typescript
export function ChatClient() { }

import { ChatClient } from '@/components/chat'
```

**悪い例:**

```typescript
export function ChatClient() { }

import { ChatClient } from '@/components/chat/ChatClient'
```

### 7. 'use client' ディレクティブ

**必須**: クライアントコンポーネントにはすべて明示的に `'use client'` を宣言すること。

ファイルの先頭（インポートの前）に配置してください。

**例:**

```typescript
'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'

export function Counter() {
  const [count, setCount] = useState(0)
  
  return (
    <div>
      <p>Count: {count}</p>
      <Button onClick={() => setCount(count + 1)}>
        Increment
      </Button>
    </div>
  )
}
```

**サーバーコンポーネント（page.tsx）には `'use client'` は不要です。**

### 8. Propsのバケツリレー (Prop Drilling) の回避

**必須**: 特別な理由がない限り、Propsのバケツリレーは実装しないこと。

深いコンポーネント階層でPropsを渡す必要がある場合は、Zustandなどの状態管理ライブラリを使用してください。

**悪い例 (Prop Drilling):**

```typescript
function Parent() {
  const [user, setUser] = useState(...)
  return <Middle user={user} setUser={setUser} />
}

function Middle({ user, setUser }) {
  return <Child user={user} setUser={setUser} />
}

function Child({ user, setUser }) {
  return <div>{user.name}</div>
}
```

**良い例 (Zustand使用):**

```typescript
export const useUserStore = create<UserState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
}))

function Parent() {
  return <Middle />
}

function Middle() {
  return <Child />
}

function Child() {
  const user = useUserStore((state) => state.user)
  return <div>{user?.name}</div>
}
```

詳細は `/docs/state-management.md` を参照してください。

## スタイル定義規約

### 1. TailwindCSSの使用

**必須**: 特別な理由がない限り、TailwindCSSの記述方法でスタイリングを実装すること。

**良い例:**

```typescript
export function Card({ children }: CardProps) {
  return (
    <div className="bg-card rounded-lg border border-border p-6 space-y-4">
      {children}
    </div>
  )
}
```

**例外が許容される場合:**
- アニメーションが複雑な場合
- 動的なスタイル計算が必要な場合
- サードパーティライブラリとの統合

### 2. UIライブラリ

**必須**: UIライブラリは特別な理由がない限り、shadcn/uiを利用すること。

shadcn/uiコンポーネントは `/components/ui/` に配置されます。

**使用可能なコンポーネント例:**
- Button
- Input
- Separator
- Sheet
- Dialog
- Select
- など

**インポート例:**

```typescript
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
```

### 3. カラーの指定

**必須**: テキストや背景などカラーに関するスタイルは原則デフォルトとし、カラー変更したい場合は、必ず `dark:` 時のカラーもあわせて設定すること。

**TailwindCSSのセマンティックカラーを使用:**
- `text-foreground` / `text-muted-foreground`
- `bg-background` / `bg-card` / `bg-muted`
- `border-border`

これらのカラーは自動的にダークモードに対応します。

**良い例:**

```typescript
<div className="bg-card text-foreground border border-border">
  <h2 className="text-2xl font-semibold">Title</h2>
  <p className="text-sm text-muted-foreground">Description</p>
</div>
```

**カスタムカラーを使用する場合 (dark: を必ず指定):**

```typescript
<div className="bg-blue-500 dark:bg-blue-700 text-white">
  Custom colored element
</div>
```

### 4. アイコンの使用

**必須**: アイコンを利用する場合は [lucide](https://lucide.dev/icons/) を利用すること。

**インポート例:**

```typescript
import { Plus, Minus, Send, User, Settings } from 'lucide-react'
```

**使用例:**

```typescript
<Button>
  <Plus className="h-4 w-4 mr-2" />
  追加
</Button>

<Button variant="outline">
  <Settings className="h-4 w-4 mr-2" />
  設定
</Button>
```

**アイコンサイズのガイドライン:**
- ボタン内: `h-4 w-4`
- 大きなアイコン: `h-6 w-6` または `h-8 w-8`
- アイコンのみのボタン: `h-5 w-5`

### 5. アニメーションの実装

**必須**: Reactコンポーネントでアニメーションを実装する場合は、原則として [motion](https://motion.dev/docs/react) ライブラリを利用すること。

motionライブラリは、React向けに設計された高性能なアニメーションライブラリで、宣言的なAPIと優れたパフォーマンスを提供します。

**インストール:**

```bash
npm install motion
```

**インポート:**

```typescript
import { motion } from 'motion/react'
```

**基本的な使用例:**

```typescript
'use client'

import { motion } from 'motion/react'

export function FadeInComponent() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      コンテンツ
    </motion.div>
  )
}
```

**推奨されるアニメーションパターン:**

1. **フェードイン + スライドアップ** - ページ読み込み時の要素表示
```typescript
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.5 }}
>
```

2. **ホバー・タップアニメーション** - ボタンやインタラクティブ要素
```typescript
<motion.button
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
>
  クリック
</motion.button>
```

3. **スクロールトリガーアニメーション** - スクロール時に要素を表示
```typescript
<motion.div
  initial={{ opacity: 0, y: 50 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ once: true }}
  transition={{ duration: 0.6 }}
>
  スクロールで表示される要素
</motion.div>
```

4. **段階的アニメーション（Stagger）** - 複数要素を順次表示
```typescript
<motion.div
  initial="hidden"
  animate="visible"
  variants={{
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }}
>
  {items.map((item) => (
    <motion.div
      key={item.id}
      variants={{
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0 }
      }}
    >
      {item.content}
    </motion.div>
  ))}
</motion.div>
```

**アニメーション実装のガイドライン:**

- **パフォーマンス**: `opacity`、`scale`、`x`、`y`、`rotate` などのプロパティを優先的に使用（GPUアクセラレーション対応）
- **アクセシビリティ**: `prefers-reduced-motion` に配慮し、必要に応じて `useReducedMotion` フックを使用
- **控えめに**: アニメーションは控えめに使用し、ユーザー体験を損なわないこと
- **一貫性**: プロジェクト全体で一貫したアニメーション時間（duration）とイージング（easing）を使用

詳細は `/docs/ui-design-rules.md` のアニメーション実装ガイドラインと [motion公式ドキュメント](https://motion.dev/docs/react) を参照してください。



## 開発フロー

### 1. 開発着手前の確認

**必須**: 開発着手前に `/docs` 以下の各ドキュメントを確認し、構造やルールを理解すること。

**確認すべきドキュメント:**
- `/docs/folder-structure.md` - プロジェクト構造
- `/docs/i18n-implement.md` - 国際化実装
- `/docs/state-management.md` - 状態管理
- `/docs/ui-design-rules.md` - UIデザイン規約
- このドキュメント - コーディングルール

### 2. 国際化（i18n）対応

**必須**: UIの開発や修正をした場合は、i18n（国際化）対応としてすべての言語環境に対応させること。

現在サポートされている言語:
- 日本語 (ja)
- 英語 (en)

**手順:**

1. 辞書ファイルにテキストを追加:

```json
{
  "myFeature": {
    "title": "タイトル",
    "description": "説明文"
  }
}
```

```json
{
  "myFeature": {
    "title": "Title",
    "description": "Description"
  }
}
```

2. コンポーネントで辞書を使用:

```typescript
export default async function MyFeaturePage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  const dict = await getDictionary(lang as Locale);
  
  return <MyFeatureClient dict={dict.myFeature} />
}
```

詳細は `/docs/i18n-implement.md` を参照してください。

### 3. ドキュメントの更新

**必須**: 常に作業した内容で `/docs` のファイルに変更が必要な場合は、docsの修正も行うこと。

**ドキュメント更新が必要な場合:**
- 新しいfeatureを追加した場合
- フォルダ構造を変更した場合
- 新しいコーディング規約を追加した場合
- 既存のルールを変更した場合

### 4. Pull Requestの作成

**必須**: Pull Requestは日本語で記載すること。

**PRタイトルの形式:**

```
feat: 新機能の追加
fix: バグの修正
docs: ドキュメントの更新
refactor: リファクタリング
style: スタイルの修正
test: テストの追加・修正
chore: その他の変更
```

**PRの説明に含めるべき内容:**
- 変更の概要
- 変更の理由
- テスト方法
- スクリーンショット（UIの変更がある場合）
- 関連するissue番号

### 5. E2Eテスト

**原則**: 起動させた状態でのE2Eテストは、i18nの言語を追加していない限りは `/ja` の日本語環境のみで構いません。

**例外**: フランス語など別の言語を追加した場合は、すべての言語環境でE2Eテストを行うこと。

**テスト対象:**
- 新しく追加したfeatureの動作確認
- UIの表示確認（レスポンシブデザイン含む）
- インタラクションの確認（ボタンクリック、フォーム送信など）
- エラー処理の確認

## まとめ

このコーディングルールに従うことで、プロジェクト全体で一貫性のある高品質なコードベースを維持できます。

**重要なポイント:**
1. すべての関数にTSDocコメントを記載
2. 論理的なブロック間に空行を入れる
3. 例外処理を適切に実装
4. Reactコンポーネントはアロー関数で作成
5. App Routerの構造に従う
6. 'use client' を明示的に宣言
7. Prop Drillingを避ける
8. TailwindCSS + shadcn/ui + lucide を使用
9. ダークモード対応
10. i18n対応を必ず実装
11. PRは日本語で記載

不明な点があれば、既存のコードや `/docs` の他のドキュメントを参照してください。
