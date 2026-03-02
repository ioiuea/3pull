# ================================================================
# Frontend Web (React Router SPA) — Dockerfile
# - Node 22 で静的ビルド
# - nginx で `build/client` を配信
# ================================================================

# -------------------------
# deps: package install 専用ステージ
# -------------------------
FROM node:22-bookworm-slim AS deps

ENV PNPM_HOME=/pnpm
ENV PATH=${PNPM_HOME}:${PATH}

WORKDIR /workspace/apps/frontend

RUN corepack enable && corepack prepare pnpm@10.30.1 --activate

# 依存解決に必要なファイルだけ先にコピーしてキャッシュを効かせる。
COPY apps/frontend/package.json apps/frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# -------------------------
# builder: React Router を静的ビルド
# -------------------------
FROM node:22-bookworm-slim AS builder

ENV PNPM_HOME=/pnpm
ENV PATH=${PNPM_HOME}:${PATH}

WORKDIR /workspace/apps/frontend

RUN corepack enable && corepack prepare pnpm@10.30.1 --activate

COPY --from=deps /workspace/apps/frontend/node_modules ./node_modules
COPY apps/frontend ./

# `react-router.config.ts` は `ssr: false` のため、静的出力は `build/client` が正本。
RUN pnpm run build

# -------------------------
# runtime: nginx で静的配信
# -------------------------
FROM nginx:1.27-alpine AS runtime

WORKDIR /usr/share/nginx/html

# SPA ルーティングのため、すべての未知パスを /index.html へフォールバックする。
COPY docker/frontend-nginx.conf /etc/nginx/conf.d/default.conf

# React Router の静的出力を nginx 配下へ配置する。
COPY --from=builder /workspace/apps/frontend/build/client ./

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
