# DevContainer for Next.js Development

このディレクトリには、Next.jsプロジェクトの開発環境をコンテナで構築するためのDevContainer設定が含まれています。

## 必要なもの

- Visual Studio Code
- Docker Desktop
- Dev Containers拡張機能 (ms-vscode-remote.remote-containers)

## 使い方

1. このリポジトリをローカルにクローンします
2. Visual Studio Codeでリポジトリを開きます
3. 左下の「><」アイコンをクリックするか、コマンドパレット（F1）で「Dev Containers: Reopen in Container」を選択します
4. コンテナのビルドと起動が完了するまで待ちます

## 含まれる機能

### 開発環境
- Node.js 20 (LTS)
- Git
- GitHub CLI
- pnpm (post-create時に自動インストール)

### VS Code拡張機能
- ESLint - コードの品質チェック
- Prettier - コードフォーマッター
- Tailwind CSS IntelliSense - Tailwind CSSの補完
- Docker - Dockerファイルのサポート
- GitLens - Git統合機能の強化

### ポート設定
- ポート3000, 3001が自動的に転送されます（Next.jsの開発サーバー用）

## Next.jsプロジェクトの作成

DevContainerが起動したら、ターミナルで以下のコマンドを実行してNext.jsプロジェクトをセットアップできます：

```bash
# pnpmを使用する場合
pnpm create next-app@latest

# npmを使用する場合
npx create-next-app@latest

# yarnを使用する場合
yarn create next-app
```

## カスタマイズ

必要に応じて `devcontainer.json` を編集して、追加の拡張機能や設定を追加できます。
