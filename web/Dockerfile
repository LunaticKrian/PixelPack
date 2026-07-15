# ── PixelPack 前端镜像（多阶段）──────────────────────────────────────
# Stage 1: Node 构建 Vue/Vite 产物到 dist/
# Stage 2: nginx 提供静态文件 + 反代 /api、/uploads 到后端 api:8000

# ---- 构建阶段 ----
FROM node:22-alpine AS build
WORKDIR /app

# 先装依赖（利用层缓存）
COPY package.json package-lock.json ./
RUN npm ci

# 再拷源码并构建
COPY tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY index.html vite.config.ts ./
COPY public/ ./public/
COPY src/ ./src/
RUN npm run build
# 产物在 /app/dist

# ---- 运行阶段 ----
FROM nginx:alpine AS runtime

# 清掉默认配置，换上我们的（含 /api、/uploads 反代与 SPA 回退）
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
