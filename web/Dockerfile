# ── PixelPack 前端多阶段构建 ──────────────────────────────────────────
# stage 1: node 构建 SPA；stage 2: nginx 静态服务。
# 产物由共享网关 airc-nginx 反代访问（见 nginx/conf.d/*.conf 的 location /）。
# 运行时不再依赖宿主机 node 环境与手动 npm run build。

# ── stage 1: 构建 SPA ──
FROM node:24-alpine AS build
WORKDIR /app
# 先拷锁文件，利用层缓存
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# vue-tsc -b 类型检查 + vite build → /app/dist
RUN npm run build

# ── stage 2: nginx 静态服务 ──
FROM nginx:alpine AS runtime
# 覆盖 nginx 默认站点（自带 SPA 回退 + gzip + 静态缓存）
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
