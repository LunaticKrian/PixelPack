# ── airise 统一网关（airise-gateway）──────────────────────────────────
# 自包含镜像：conf.d + snippets 在构建期 COPY 进镜像，运行期不再依赖
# 宿主机挂载配置目录。会变的数据（证书、SPA 产物、上传文件）由 compose 挂载。
# 架构：docs/technology/260719-nginx部署架构.md

FROM nginx:alpine

# 移除 nginx 默认站点，避免抢占 80
RUN rm -f /etc/nginx/conf.d/default.conf

# 构建期内置全部站点配置 + 复用片段（自包含）
COPY conf.d/   /etc/nginx/conf.d/
COPY snippets/ /etc/nginx/snippets/

# 配置变更需重新构建镜像：docker compose up -d --build
EXPOSE 80 443
