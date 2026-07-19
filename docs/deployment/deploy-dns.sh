#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  *.airise.site 通配证书签发（acme.sh + DNSPod DNS-01）
#
#  为什么用 acme.sh 而非 certbot：
#    snap certbot 仅 latest(5.7.0) 通道，社区 certbot-dns-dnspod 插件
#    用老 Python 打包、与 3.0+ 不兼容；acme.sh 对 DNSPod 原生内置支持。
#
#  关联文档：docs/technology/260719-通配证书签发.md
#  用法：以 root 运行   bash deploy-dns.sh
# ─────────────────────────────────────────────────────────────
set -e

# 支持环境变量覆盖，便于 bootstrap 脚本驱动
EMAIL="${EMAIL:-2793260947@qq.com}"
BASE_DOMAIN="${BASE_DOMAIN:-airise.site}"
DOMAINS=(-d "$BASE_DOMAIN" -d "*.$BASE_DOMAIN")
CRED_FILE="${CRED_FILE:-/root/.secrets/dnspod.ini}"   # 含 dns_dnspod_api_token = ID,TOKEN
CERT_DIR="/etc/letsencrypt/live/$BASE_DOMAIN"
GW_DIR="${GW_DIR:-/root/pixel-pack/nginx}"            # 网关 compose 目录，按实际改

# ── 0. 前置检查 + 解析 DNSPod 凭证 ────────────────────────────
[ "$(id -u)" -eq 0 ] || { echo "请用 root 运行"; exit 1; }
[ -f "$CRED_FILE" ] || { echo "缺少 $CRED_FILE，先创建（见通配证书文档 §1）"; exit 1; }
chmod 600 "$CRED_FILE"

# 从 dnspod.ini 的 "dns_dnspod_api_token = ID,TOKEN" 解析出 acme.sh 要的 DP_Id / DP_Key
TOKEN_LINE=$(grep -E '^\s*dns_dnspod_api_token' "$CRED_FILE" | sed -E 's/^[^=]*=\s*//; s/\s*$//')
[ -n "$TOKEN_LINE" ] || { echo "❌ $CRED_FILE 里没找到 dns_dnspod_api_token"; exit 1; }
export DP_Id="${TOKEN_LINE%%,*}"
export DP_Key="${TOKEN_LINE#*,}"
[ -n "$DP_Id" ] && [ -n "$DP_Key" ] || { echo "❌ token 格式不对，应为 ID,TOKEN"; exit 1; }
echo "✅ 已解析 DNSPod 凭证 (DP_Id=${DP_Id})"

# ── 1. 装 acme.sh（国内默认走 Gitee 镜像，ACME_SOURCE=github 可切回）──
ACME="$HOME/.acme.sh/acme.sh"
if [ ! -x "$ACME" ]; then
  if [ "${ACME_SOURCE:-gitee}" = "github" ]; then
    curl https://get.acme.sh | sh -s email="$EMAIL"
  else
    # Gitee 官方镜像（作者 neilpang 维护），国内拉取稳定
    git clone --depth 1 https://gitee.com/neilpang/acme.sh.git /tmp/acme-install
    ( cd /tmp/acme-install && ./acme.sh --install -m "$EMAIL" --home "$HOME/.acme.sh" )
    rm -rf /tmp/acme-install
  fi
  ACME="$HOME/.acme.sh/acme.sh"
fi
# 默认 CA 设为 Let's Encrypt（acme.sh 默认 ZeroSSL，需额外注册账号）
"$ACME" --set-default-ca --server letsencrypt

# ── 2. 签发通配证书（DNSPod DNS-01）───────────────────────────
# acme.sh 在「证书已签发、未到续期」时会跳过并返回非零；用 || true 放过该状态，
# 让脚本继续走 --install-cert（幂等）和起网关。真正签发失败时，下一步 install-cert
# 会因找不到证书而报错退出，不会静默通过。
"$ACME" --issue --dns dns_dp "${DOMAINS[@]}" || true

# ── 3. 装到网关期望路径 + 续期自动 reload ─────────────────────
mkdir -p "$CERT_DIR"
"$ACME" --install-cert -d "$BASE_DOMAIN" \
  --key-file       "$CERT_DIR/privkey.pem" \
  --fullchain-file "$CERT_DIR/fullchain.pem" \
  --reloadcmd      "docker exec airise-gateway nginx -s reload"

[ -f "$CERT_DIR/fullchain.pem" ] && [ -f "$CERT_DIR/privkey.pem" ] \
  && echo "✅ 证书已安装: $CERT_DIR/" \
  || { echo "❌ 证书安装失败"; exit 1; }

# acme.sh 已注册 cron 自动续期，续期后会执行上面的 --reloadcmd
echo "✅ 自动续期已就绪（acme.sh cron + reloadcmd）"

# ── 4. 重建网关 + 验证 ───────────────────────────────────────
cd "$GW_DIR"
docker compose up -d --build
docker exec airise-gateway nginx -t
echo "✅ 全部完成。浏览器访问 https://pixelpack.airise.site 验证证书为 *.airise.site"
