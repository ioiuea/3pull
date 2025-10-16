# 認証機能ドキュメント

このドキュメントでは、3pull の Auth.js 認証実装について説明します。

## 概要

本プロジェクトは Auth.js（NextAuth.js v5）を使用したカスタムヘッダー認証機能を実装しています。
フロントエンドで Auth.js を使用して JWT セッションを管理し、バックエンド API リクエスト時にカスタムヘッダー（X-User-Id, X-User-Email）でユーザー情報を送信します。
バックエンド（FastAPI）はこれらのヘッダーを検証してユーザー認証を行います。

## 実装済み機能

### サポート IdP

以下の IdP をサポートしています（環境変数で有効化）：

1. **Microsoft EntraID（旧 Azure AD）**

   - エンタープライズ認証
   - テスト用認証情報は.env.local.example を参照

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

1. ユーザーがフロントエンドで IdP を選択してサインイン
2. Auth.js が OAuth 認証フローを処理
3. 認証成功後、JWT トークンに user.id と user.email を保存
4. セッションコールバックでユーザー情報をクライアントに公開
5. API リクエスト時、apiClient.ts が以下のヘッダーを付与：
   - `X-User-Id`: ユーザー ID
   - `X-User-Email`: メールアドレス
6. **バックエンド（FastAPI）がヘッダーを検証：**
   - 認証依存性（`get_current_user`）がヘッダーを抽出
   - ヘッダーが不足している場合は 401 Unauthorized
   - 認証済みユーザー情報をエンドポイントに提供
7. エンドポイントが認証済みユーザーで DB 操作を実行
8. ユーザー固有のデータのみ取得・変更可能

## 環境変数設定

### 必要な環境変数

プロジェクトルートの `web/.env.local` ファイルに以下の環境変数を設定してください：

**AUTH_SECRET（必須）**

- JWT トークンの暗号化に使用
- 生成方法: `npx auth secret` を実行してコピー

**EntraID プロバイダー**（オプション）

- `AUTH_MICROSOFT_ENTRA_ID_ID`: クライアント ID
- `AUTH_MICROSOFT_ENTRA_ID_SECRET`: クライアントシークレット
- `AUTH_MICROSOFT_ENTRA_ID_ISSUER`: Issuer URL（形式: `https://login.microsoftonline.com/{tenant-id}/v2.0`）
- テスト用認証情報は **GitHub issue #30** を参照

**GitHub プロバイダー**（オプション）

- `AUTH_GITHUB_ID`: GitHub OAuth App のクライアント ID
- `AUTH_GITHUB_SECRET`: GitHub OAuth App のクライアントシークレット
- 設定方法: https://authjs.dev/getting-started/providers/github

**Google プロバイダー**（オプション）

- `AUTH_GOOGLE_ID`: Google OAuth クライアント ID
- `AUTH_GOOGLE_SECRET`: Google OAuth クライアントシークレット
- 設定方法: https://authjs.dev/getting-started/providers/google

**バックエンド API URL**

- `NEXT_PUBLIC_API_URL`: バックエンド API のベース URL（開発環境: `http://localhost:8000`）

### 環境変数の設定例

web/.env.local ファイルを作成し、上記の環境変数を設定してください。
少なくとも AUTH_SECRET は必須です。他のプロバイダーは使用するものだけ設定すれば有効化されます。

## 使用方法

### サインインボタンの追加

```typescript
import { SignInButton } from "@/components/auth/SignInButton";

export function LoginPage() {
  return (
    <div>
      <SignInButton
        provider="microsoft-entra-id"
        label="EntraID でサインイン"
      />
      <SignInButton provider="github" label="GitHub でサインイン" />
      <SignInButton provider="google" label="Google でサインイン" />
    </div>
  );
}
```

### API リクエストの送信

```typescript
import { apiRequest } from "@/lib/apiClient";

// 認証情報付きでAPIリクエスト (important-comment)
// apiClient.tsが自動的にX-User-Id、X-User-Emailヘッダーを付与 (important-comment)
const response = await apiRequest("/api/v1/folders", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ name: "My Folder", type: "chat" }),
});
```

### セッション情報の取得

```typescript
import { auth } from "@/auth";

export async function MyComponent() {
  const session = await auth();

  if (!session?.user) {
    return <div>ログインしてください</div>;
  }

  return <div>こんにちは、{session.user.email}さん</div>;
}
```

## セキュリティ考慮事項

### 実装済みセキュリティ

- **JWT セッション管理**: HttpOnly クッキーに暗号化保存、AUTH_SECRET による暗号化
- **カスタムヘッダー認証**: X-User-Id、X-User-Email ヘッダーでユーザー情報送信
- **バックエンド検証**: FastAPI でヘッダー検証、401 エラーで未認証リクエストを拒否
- **ユーザースコープ**: 各ユーザーは自分のデータのみアクセス可能
- **CORS 設定**: 信頼されたオリジンのみ許可

### セキュリティの制限事項

このカスタムヘッダー方式は、フロントエンドとバックエンドが**同じ信頼ドメイン**で動作することを前提としています：

- ✅ 適切な環境: Next.js（localhost:3000）→ FastAPI（localhost:8000）同一サーバー内
- ⚠️ 注意が必要: 異なるドメイン間の通信
- ❌ 非推奨: 公開 API として第三者に提供

### 今後の改善案

より強固なセキュリティが必要な場合、以下を検討：

1. **JWT Bearer 認証への移行**: Authorization: Bearer {token}で標準的な認証
2. **トークン有効期限管理**: 短期アクセストークン + リフレッシュトークン
3. **署名検証**: バックエンドで暗号化された JWT トークンを復号・検証

## トラブルシューティング

### サインインできない

1. 環境変数が正しく設定されているか確認
2. IdP の設定（リダイレクト URL 等）が正しいか確認
3. コールバック URL: `http://localhost:3000/api/auth/callback/{provider}`
4. AUTH_SECRET が設定されているか確認

### API リクエストでユーザー情報が取得できない

1. `apiClient.ts`を使用してリクエストを送信しているか確認
2. セッションが有効か確認（`auth()`で取得）
3. ブラウザの開発者ツールでリクエストヘッダーに X-User-Id、X-User-Email が含まれているか確認
4. バックエンドログで認証エラー（401）が発生していないか確認

## 参考リンク

- [Auth.js Documentation](https://authjs.dev/)
- [EntraID Provider](https://authjs.dev/getting-started/providers/microsoft-entra-id)
- [GitHub Provider](https://authjs.dev/getting-started/providers/github)
- [Google Provider](https://authjs.dev/getting-started/providers/google)
- [JWT Session Strategy](https://authjs.dev/concepts/session-strategies)

## 実装完了

✅ Phase 1: フロントエンド認証と JWT 生成
✅ Phase 2: バックエンドカスタムヘッダー認証

認証機能の基本実装が完了しました。今後、より強固なセキュリティが必要な場合は JWT Bearer 認証への移行を検討してください。
