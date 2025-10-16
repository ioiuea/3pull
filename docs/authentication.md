# 認証機能ドキュメント

このドキュメントでは、3pull-devinプロジェクトのAuth.js認証実装について説明します。

## 概要

本プロジェクトはAuth.js（NextAuth.js v5）を使用したカスタムヘッダー認証機能を実装しています。
フロントエンドでAuth.jsを使用してJWTセッションを管理し、バックエンドAPIリクエスト時にカスタムヘッダー（X-User-Id, X-User-Email）でユーザー情報を送信します。
バックエンド（FastAPI）はこれらのヘッダーを検証してユーザー認証を行います。

## 実装済み機能

### サポートIdP

以下のIdPをサポートしています（環境変数で有効化）：

1. **Microsoft EntraID（旧Azure AD）**
   - エンタープライズ認証
   - テスト用認証情報は.env.local.exampleを参照

2. **GitHub**
   - 開発者向け認証
   - 認証情報は各自設定が必要

3. **Google**
   - 一般ユーザー向け認証
   - 認証情報は各自設定が必要

### アーキテクチャ

```
web/
├── auth.ts                          # Auth.js設定（JWT戦略）
├── app/api/auth/[...nextauth]/route.ts  # 認証APIハンドラー
├── lib/apiClient.ts                 # APIクライアント（Phase 1版）
└── components/auth/                 # 認証関連コンポーネント
    ├── SignInButton.tsx             # サインインボタン
    ├── SignOutButton.tsx            # サインアウトボタン
    └── UserInfo.tsx                 # ユーザー情報表示
```

### 認証フロー

1. ユーザーがフロントエンドでIdPを選択してサインイン
2. Auth.jsがOAuth認証フローを処理
3. 認証成功後、JWTトークンにuser.idとuser.emailを保存
4. セッションコールバックでユーザー情報をクライアントに公開
5. APIリクエスト時、apiClient.tsが以下のヘッダーを付与：
   - `X-User-Id`: ユーザーID
   - `X-User-Email`: メールアドレス
6. **バックエンド（FastAPI）がヘッダーを検証：**
   - 認証依存性（`get_current_user`）がヘッダーを抽出
   - ヘッダーが不足している場合は401 Unauthorized
   - 認証済みユーザー情報をエンドポイントに提供
7. エンドポイントが認証済みユーザーでDB操作を実行
8. ユーザー固有のデータのみ取得・変更可能

## 環境変数設定

### 必要な環境変数

プロジェクトルートの `web/.env.local` ファイルに以下の環境変数を設定してください：

**AUTH_SECRET（必須）**
- JWTトークンの暗号化に使用
- 生成方法: `npx auth secret` を実行してコピー

**EntraID プロバイダー**（オプション）
- `AUTH_MICROSOFT_ENTRA_ID_ID`: クライアントID
- `AUTH_MICROSOFT_ENTRA_ID_SECRET`: クライアントシークレット
- `AUTH_MICROSOFT_ENTRA_ID_ISSUER`: Issuer URL（形式: `https://login.microsoftonline.com/{tenant-id}/v2.0`）
- テスト用認証情報は **GitHub issue #30** を参照

**GitHub プロバイダー**（オプション）
- `AUTH_GITHUB_ID`: GitHub OAuth App のクライアントID
- `AUTH_GITHUB_SECRET`: GitHub OAuth App のクライアントシークレット
- 設定方法: https://authjs.dev/getting-started/providers/github

**Google プロバイダー**（オプション）
- `AUTH_GOOGLE_ID`: Google OAuth クライアントID
- `AUTH_GOOGLE_SECRET`: Google OAuth クライアントシークレット
- 設定方法: https://authjs.dev/getting-started/providers/google

**バックエンドAPI URL**
- `NEXT_PUBLIC_API_URL`: バックエンドAPIのベースURL（開発環境: `http://localhost:8000`）

### 環境変数の設定例

web/.env.local ファイルを作成し、上記の環境変数を設定してください。
少なくとも AUTH_SECRET は必須です。他のプロバイダーは使用するものだけ設定すれば有効化されます。

## 使用方法

### サインインボタンの追加

```typescript
import { SignInButton } from '@/components/auth/SignInButton'

export function LoginPage() {
  return (
    <div>
      <SignInButton provider="microsoft-entra-id" label="EntraID でサインイン" />
      <SignInButton provider="github" label="GitHub でサインイン" />
      <SignInButton provider="google" label="Google でサインイン" />
    </div>
  )
}
```

### APIリクエストの送信

```typescript
import { apiRequest } from '@/lib/apiClient'

// 認証情報付きでAPIリクエスト (important-comment)
// apiClient.tsが自動的にX-User-Id、X-User-Emailヘッダーを付与 (important-comment)
const response = await apiRequest('/api/v1/folders', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ name: 'My Folder', type: 'personal' }),
})
```

### セッション情報の取得

```typescript
import { auth } from '@/auth'

export async function MyComponent() {
  const session = await auth()

  if (!session?.user) {
    return <div>ログインしてください</div>
  }

  return <div>こんにちは、{session.user.email}さん</div>
}
```

## セキュリティ考慮事項

### 実装済みセキュリティ

- **JWTセッション管理**: HttpOnlyクッキーに暗号化保存、AUTH_SECRETによる暗号化
- **カスタムヘッダー認証**: X-User-Id、X-User-Emailヘッダーでユーザー情報送信
- **バックエンド検証**: FastAPIでヘッダー検証、401エラーで未認証リクエストを拒否
- **ユーザースコープ**: 各ユーザーは自分のデータのみアクセス可能
- **CORS設定**: 信頼されたオリジンのみ許可

### セキュリティの制限事項

このカスタムヘッダー方式は、フロントエンドとバックエンドが**同じ信頼ドメイン**で動作することを前提としています：

- ✅ 適切な環境: Next.js（localhost:3000）→ FastAPI（localhost:8000）同一サーバー内
- ⚠️ 注意が必要: 異なるドメイン間の通信
- ❌ 非推奨: 公開APIとして第三者に提供

### 今後の改善案

より強固なセキュリティが必要な場合、以下を検討：

1. **JWT Bearer認証への移行**: Authorization: Bearer {token}で標準的な認証
2. **トークン有効期限管理**: 短期アクセストークン + リフレッシュトークン
3. **署名検証**: バックエンドで暗号化されたJWTトークンを復号・検証

## トラブルシューティング

### サインインできない

1. 環境変数が正しく設定されているか確認
2. IdPの設定（リダイレクトURL等）が正しいか確認
3. コールバックURL: `http://localhost:3000/api/auth/callback/{provider}`
4. AUTH_SECRETが設定されているか確認

### APIリクエストでユーザー情報が取得できない

1. `apiClient.ts`を使用してリクエストを送信しているか確認
2. セッションが有効か確認（`auth()`で取得）
3. ブラウザの開発者ツールでリクエストヘッダーにX-User-Id、X-User-Emailが含まれているか確認
4. バックエンドログで認証エラー（401）が発生していないか確認

## 参考リンク

- [Auth.js Documentation](https://authjs.dev/)
- [EntraID Provider](https://authjs.dev/getting-started/providers/microsoft-entra-id)
- [GitHub Provider](https://authjs.dev/getting-started/providers/github)
- [Google Provider](https://authjs.dev/getting-started/providers/google)
- [JWT Session Strategy](https://authjs.dev/concepts/session-strategies)

## 実装完了

✅ Phase 1: フロントエンド認証とJWT生成
✅ Phase 2: バックエンドカスタムヘッダー認証

認証機能の基本実装が完了しました。今後、より強固なセキュリティが必要な場合はJWT Bearer認証への移行を検討してください。
