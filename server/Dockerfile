# ── PixelPack 后端镜像 ─────────────────────────────────────────────────
# FastAPI + uvicorn + claude-agent-sdk
#
# ⚠️ 基础镜像必须是 glibc 系（Debian slim），不能用 alpine。
#    claude-agent-sdk 在 _bundled/claude 里捆绑了一个原生二进制（glibc 编译），
#    alpine 的 musl 跑不起来。
#
# ⚠️ 该捆绑二进制是平台相关的：构建平台必须 == 运行平台。
#    在 Apple Silicon 上构建却要跑在 amd64 服务器，必须用
#    `docker buildx build --platform linux/amd64`（QEMU 模拟，较慢），
#    或直接在服务器上构建。详见 docs/deploy.md。
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # 国内构建加速：pip 走清华源
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

WORKDIR /app

# 国内构建加速：apt 换阿里云源。
# 注意 trixie(Debian 13) 用 DEB822 格式 sources.list.d/debian.sources，
# 老版用 sources.list，两种都兼容。海外构建可删掉这两行。
RUN { sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null \
      || sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null; } \
 && apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates git \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# ── 切换到非 root 用户 ───────────────────────────────────────────────
# claude-agent-sdk 用 permission_mode="bypassPermissions" 启动 claude 子进程，
# 等价于 claude CLI 的 --dangerously-skip-permissions；该模式拒绝在 root 下运行。
# 所以容器必须以非特权用户身份跑，否则每日资讯 / 对话生成任务会报：
#   "--dangerously-skip-permissions cannot be used with root/sudo privileges"
# 固定 UID/GID=1000，便于宿主机挂载目录 chown 对齐权限。
RUN groupadd -r -g 1000 app \
 && useradd -r -u 1000 -g app -m -d /home/app app \
 && mkdir -p /app/data /app/uploads \
 && chown -R app:app /app /home/app

# claude 子进程需要可写的 HOME（写会话/缓存）；TMPDIR 默认 /tmp 全局可写。
ENV HOME=/home/app
USER app

# data.db 与 uploads/ 由 docker-compose 挂载到 /app/data（见 compose volumes）。
# ⚠️ 挂载会覆盖镜像内目录属主：宿主机的 ./data 必须 chown 给 1000:1000，
#    否则非 root 的 app 用户无法写入（见 docs/deploy.md）。
EXPOSE 8000

# 在 /app 下启动，使 "./data.db"、"uploads" 等相对路径解析到 /app。
# DATABASE_URL / UPLOAD_DIR 由 compose 注入，指向 /app/data 以实现持久化。
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
