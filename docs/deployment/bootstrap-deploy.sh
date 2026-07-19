#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  PixelPack 一键部署（新环境）：网络 → 后端+前端容器 → 证书 → 网关
#
#  它做的事：
#    1. 装齐 docker / compose（缺才装），起 crond
#    2. 克隆 PixelPack + airise-gateway、建共享网络 airise-web、建数据目录并 chown 1000
#    3. 检查 / 生成 server/.env（密钥要你填）
#    4. 起后端 + 前端容器（pixelpack-api + pixelpack-web，web 镜像内构建 SPA）
#    5. 调 deploy-dns.sh：签 *.airise.site 通配证书 + 起网关 airise-gateway
#    6. 端到端验证
#
#  它不做的事（必须你先在 DNSPod 控制台做好）：
#    - 建 A 记录：<SITE_DOMAIN> → 本机公网 IP（且已生效）
#    - 建 DNSPod API token，写入 DNSPOD_INI（dns_dnspod_api_token = ID,TOKEN）
#
#  用法（root）：
#    bash bootstrap-deploy.sh
#    # 或覆盖默认值：
#    PROJECT_DIR=/opt/pixelpack GW_DIR=/opt/airise-gateway \
#    SITE_DOMAIN=pixelpack.airise.site \
#    BASE_DOMAIN=airise.site EMAIL=you@x.com \
#    DNSPOD_INI=/root/.secrets/dnspod.ini bash bootstrap-deploy.sh
#
#  关联：docs/deployment/deploy.md · docs/technology/260719-通配证书签发.md
# ─────────────────────────────────────────────────────────────
set -e

# ── 参数（环境变量覆盖）──────────────────────────────────────
PROJECT_DIR="${PROJECT_DIR:-/opt/pixelpack}"
REPO_URL="${REPO_URL:-https://github.com/LunaticKrian/PixelPack.git}"
GW_DIR="${GW_DIR:-/opt/airise-gateway}"
GW_REPO_URL="${GW_REPO_URL:-https://github.com/LunaticKrian/airise-gateway.git}"
BASE_DOMAIN="${BASE_DOMAIN:-airise.site}"
SITE_DOMAIN="${SITE_DOMAIN:-pixelpack.airise.site}"
EMAIL="${EMAIL:-2793260947@qq.com}"
DNSPOD_INI="${DNSPOD_INI:-/root/.secrets/dnspod.ini}"

log()  { echo -e "\033[1;34m▶ $*\033[0m"; }
ok()   { echo -e "\033[1;32m✅ $*\033[0m"; }
warn() { echo -e "\033[1;33m⚠ $*\033[0m"; }
die()  { echo -e "\033[1;31m❌ $*\033[0m" >&2; exit 1; }

# ── 0. 前置检查 ──────────────────────────────────────────────
[ "$(id -u)" -eq 0 ] || die "请用 root 运行"
[ -f "$DNSPOD_INI" ] || die "缺少 $DNSPOD_INI（DNSPod token，见通配证书文档 §1）"
chmod 600 "$DNSPOD_INI"

# crond（acme.sh 续期靠它）
systemctl enable --now crond 2>/dev/null || systemctl enable --now cron 2>/dev/null || warn "crond 未启用，acme.sh 自动续期不会触发"

# DNS 解析检查（仅提示，不致命——可能 NAT/未生效）
if command -v dig >/dev/null; then
  RESOLVED=$(dig +short "$SITE_DOMAIN" | tail -1)
  if [ -z "$RESOLVED" ]; then
    warn "$SITE_DOMAIN 尚未解析，先在 DNSPod 建 A 记录指向本机"
  else
    ok "$SITE_DOMAIN 解析到 $RESOLVED（确认是本机公网 IP）"
  fi
fi

# ── 1. docker / compose（缺才装）──────────────────────────────
if ! command -v docker >/dev/null; then
  log "安装 docker（get.docker.com）"
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi
docker version >/dev/null 2>&1 || die "docker 未就绪"
if ! docker compose version >/dev/null 2>&1; then
  die "缺少 docker compose 插件，请手动安装 compose v2"
fi
ok "docker $(docker version --format '{{.Server.Version}}') + compose 就绪"

# ── 2. 代码 / 网络 / 数据目录 ─────────────────────────────────
if [ ! -d "$PROJECT_DIR/.git" ]; then
  log "克隆 PixelPack 到 $PROJECT_DIR"
  git clone "$REPO_URL" "$PROJECT_DIR"
else
  log "PixelPack 代码已存在，git pull"
  git -C "$PROJECT_DIR" pull --ff-only || warn "git pull 失败，继续用现有代码"
fi

if [ ! -d "$GW_DIR/.git" ]; then
  log "克隆网关 airise-gateway 到 $GW_DIR"
  git clone "$GW_REPO_URL" "$GW_DIR"
else
  log "网关代码已存在，git pull"
  git -C "$GW_DIR" pull --ff-only || warn "git pull 失败，继续用现有代码"
fi

log "建共享网络 airise-web"
docker network create airise-web 2>/dev/null || ok "airise-web 已存在"

log "建数据目录并 chown 1000（非 root api 容器用户）"
mkdir -p "$PROJECT_DIR/data/uploads"
chown -R 1000:1000 "$PROJECT_DIR/data"

# 网关 compose 默认挂载 /opt/pixelpack/data/uploads（前端 dist 已不再挂载），
# 按实际 PROJECT_DIR 改写，保证上传目录路径一致。
if [ "$PROJECT_DIR" != "/opt/pixelpack" ]; then
  log "按 $PROJECT_DIR 调整网关 compose 上传目录挂载路径"
  sed -i "s|/opt/pixelpack|$PROJECT_DIR|g" "$GW_DIR/docker-compose.yml"
fi

# ── 3. server/.env ────────────────────────────────────────────
ENV_FILE="$PROJECT_DIR/server/.env"
if [ ! -f "$ENV_FILE" ]; then
  if [ -f "$PROJECT_DIR/server/.env.example" ]; then
    cp "$PROJECT_DIR/server/.env.example" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    warn "已生成 $ENV_FILE，请填入 ANTHROPIC_AUTH_TOKEN / ANTHROPIC_BASE_URL / ANTHROPIC_MODEL 后重启 api"
  else
    die "缺少 server/.env.example，无法生成 $ENV_FILE"
  fi
else
  grep -q '^ANTHROPIC_AUTH_TOKEN=.' "$ENV_FILE" \
    || warn "$ENV_FILE 缺 ANTHROPIC_AUTH_TOKEN，AI 功能会失败"
fi

# ── 4. 起后端 + 前端容器 ─────────────────────────────────────
# 前端不再在宿主机 npm 构建：web/Dockerfile 多阶段镜像内完成（node 构建→nginx serve）。
log "部署 pixelpack-api + pixelpack-web（web 镜像内构建 SPA）"
cd "$PROJECT_DIR"
docker compose up -d --build
ok "api + web 已启动"

# ── 5. 签证书 + 起网关（deploy-dns.sh 内：先签证书再 up 网关，避开证书-网关鸡生蛋）──
log "签发通配证书 + 启动网关 airise-gateway"
export EMAIL BASE_DOMAIN DNSPOD_INI GW_DIR
bash "$PROJECT_DIR/docs/deployment/deploy-dns.sh"

# ── 6. 验证 ──────────────────────────────────────────────────
log "端到端验证"
docker compose -f "$GW_DIR/docker-compose.yml" ps
docker exec airise-gateway nginx -t
echo
ok "部署完成。访问 https://$SITE_DOMAIN 验证"
echo "  - 后端日志：cd $PROJECT_DIR && docker compose logs -f api"
echo "  - 前端日志：cd $PROJECT_DIR && docker compose logs -f web"
echo "  - 网关日志：cd $GW_DIR && docker compose logs -f nginx"
echo "  - 证书续期：acme.sh cron 已注册（systemctl status crond）"
