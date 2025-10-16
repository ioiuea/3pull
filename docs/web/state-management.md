# 状態管理戦略ドキュメント

## 概要

このプロジェクトでは、クライアントサイドの状態管理にZustandを使用しています。Zustandは軽量でシンプルなAPIを持ち、TypeScriptとの相性が良く、React 19とNext.js 15 App Routerでも問題なく動作します。

## Zustandとは

Zustandは、Reactアプリケーション向けのシンプルで高速な状態管理ライブラリです。

**主な特徴:**
- 軽量（約1KB gzipped）
- シンプルなAPI
- TypeScript完全サポート
- ボイラープレートコードが少ない
- React Hooksベース
- ミドルウェアサポート（devtools, persist等）

公式ドキュメント: https://zustand.docs.pmnd.rs/

## フォルダ構成

```
.
├── store/                    # Zustandストア定義 (important-comment)
│   └── useDemoStore.ts      # デモストア (important-comment)
└── app/
    └── [lang]/
        └── zustand-demo/    # Zustandデモページ (important-comment)
            ├── page.tsx
            └── ZustandDemoClient.tsx
```

## 状態管理の原則

### 1. グローバルステート vs ローカルステート

#### グローバルステート（Zustand使用）

**使用するケース:**
- コンポーネント間で共有される状態
- Propsバケツリレー（prop drilling）を避けたい場合
- アプリケーション全体で参照・更新される状態
- 複数のページで使用される状態

**例:**
- ユーザー認証情報
- アプリケーション設定
- 共有されるUIの状態（サイドバーの開閉状態等）
- グローバルなフォームデータ

#### ローカルステート（React useState使用）

**使用するケース:**
- 単一コンポーネント内でのみ使用される状態
- 他のコンポーネントと共有する必要がない状態
- 一時的なUIフラグ（モーダルの開閉、ツールチップの表示等）

**例:**
- フォーム入力の一時的な値（送信前）
- モーダルやドロップダウンの開閉状態
- ホバー状態
- ローカルなアニメーション状態

### 2. Propsバケツリレーの回避

**❌ 避けるべきパターン:**
```typescript
function Parent() { // (important-comment)
  const [user, setUser] = useState(...)
  return <Middle user={user} setUser={setUser} />
}

function Middle({ user, setUser }) { // (important-comment)
  return <Child user={user} setUser={setUser} />
}

function Child({ user, setUser }) { // (important-comment)
  return <div>{user.name}</div>
}
```

**✅ 推奨パターン（Zustand使用）:**
```typescript
export const useUserStore = create<UserState>((set) => ({ // (important-comment)
  user: null,
  setUser: (user) => set({ user }),
}))

function Parent() { // (important-comment)
  return <Middle />
}

function Middle() { // (important-comment)
  return <Child />
}

function Child() { // (important-comment)
  const user = useUserStore((state) => state.user)
  return <div>{user?.name}</div>
}
```

## ストアの作成方法

### 基本的なストア

```typescript
'use client'

import { create } from 'zustand'

interface CounterState {
  count: number
  increment: () => void
  decrement: () => void
}

export const useCounterStore = create<CounterState>((set) => ({
  count: 0,
  increment: () => set((state) => ({ count: state.count + 1 })),
  decrement: () => set((state) => ({ count: state.count - 1 })),
}))
```

### DevToolsミドルウェアを使用したストア

```typescript
'use client'

import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

interface UserState {
  user: { name: string; email: string } | null
  setUser: (user: { name: string; email: string }) => void
  clearUser: () => void
}

export const useUserStore = create<UserState>()(
  devtools(
    (set) => ({
      user: null,
      setUser: (user) => set({ user }),
      clearUser: () => set({ user: null }),
    }),
    { name: 'UserStore' }
  )
)
```

## コンポーネントでの使用方法

### 1. ストア全体を取得

```typescript
'use client'

import { useCounterStore } from '@/store/useCounterStore'

export function Counter() {
  const { count, increment, decrement } = useCounterStore()
  
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={increment}>+</button>
      <button onClick={decrement}>-</button>
    </div>
  )
}
```

### 2. セレクターを使用した最適化

不必要な再レンダリングを避けるため、必要な状態のみを選択します。

```typescript
'use client'

import { useCounterStore } from '@/store/useCounterStore'

export function CountDisplay() {
  const count = useCounterStore((state) => state.count) // (important-comment)
  
  return <p>Count: {count}</p>
}

export function CounterButtons() {
  const increment = useCounterStore((state) => state.increment) // (important-comment)
  const decrement = useCounterStore((state) => state.decrement)
  
  return (
    <div>
      <button onClick={increment}>+</button>
      <button onClick={decrement}>-</button>
    </div>
  )
}
```

## ベストプラクティス

### 1. ストアの命名規則
- ストアファイル名: `use{Name}Store.ts` （例: `useUserStore.ts`, `useCartStore.ts`）
- ストアフック名: `use{Name}Store` （例: `useUserStore`, `useCartStore`）

### 2. ストアの配置
- 全てのストアは `/store` ディレクトリに配置
- 関連するストアはサブディレクトリにグループ化可能

### 3. TypeScriptの活用
- 必ず型定義を使用
- ストアの状態とアクションの型を明確に定義
- `create<StateType>()`でストアの型を指定

### 4. アクションの定義
- 状態の更新ロジックはストア内に定義
- コンポーネントから直接状態を変更しない
- 複雑なロジックはストア内のアクションにカプセル化

### 5. パフォーマンス最適化
- セレクターを使用して必要な状態のみを取得
- 複数の状態を取得する場合は、shallow比較を検討
- 大きなオブジェクトは分割して管理

## 参考資料

- [Zustand公式ドキュメント](https://zustand.docs.pmnd.rs/)
- [Zustand GitHubリポジトリ](https://github.com/pmndrs/zustand)
- [Next.js App RouterでのZustand使用例](https://zustand.docs.pmnd.rs/guides/nextjs)
