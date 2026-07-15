# PixelPack Docker 部署指南

两个独立容器：`api`（FastAPI/uvicorn 后端）+ `web`（nginx 前端 + 反代）。
数据与上传文件通过 `./data` 目录挂载持久化，密钥通过 `.env` 注入。

---

## 1. 服务器准备

需要安装 **Docker + Docker Compose**（建议 Docker 24+，compose v2 插件）。

```bash
# Ubuntu/Debian 示例
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # 重新登录生效
```

克隆代码：

```bash
git clone https://github.com/LunaticKrian/PixelPack.git
cd PixelPack
```

## 2. 配置密钥（.env）

`.env` **不进 git、不进镜像**，仅在服务器本地创建，由 compose 运行时注入。

```bash
cp server/.env.example server/.env
vi server/.env     # 填入真实的 ANTHROPIC_AUTH_TOKEN
```

> `DATABASE_URL` 与 `UPLOAD_DIR` 已在 `docker-compose.yml` 中固定指向持久化卷
> `/app/data`，`.env` 里无需也不应填写这两项。

## 3. 关于密钥安全的说明

你问到的「手动上传 .env 到磁盘，还是更安全的方式」：

- **当前方案（env_file 指向本地 .env）已经是个人/小团队项目的最佳平衡**——密钥
  不进镜像（重建镜像不泄露）、不进 git、不进版本历史。镜像可以放心 push 到任何
  公开仓库。
- 更进一步的可选项：
  - **文件权限收紧**：`chmod 600 server/.env`，并确保只有部署用户可读。
  - **Docker secrets**（挂到 `/run/secrets`，进程内只读、权限更严）：单机 VPS 收益
    有限，配置更繁琐，一般不必。
  - **云密钥服务**（AWS Secrets Manager / Vault）：需要额外基础设施，对个人项目过度。
- ⚠️ 注意：当前仓库的 `.env` 已被 `.gitignore` 排除，token 不会进 git。但请确认
  历史 commit 里没有泄露过——一旦提交过，应**轮换（regenerate）该 GLM token**。

## 4. 构建并启动

```bash
docker compose up -d --build
```

首次构建后端较慢（`claude-agent-sdk` 会下载一个约 240MB 的捆绑二进制）。

查看状态与日志：

```bash
docker compose ps
docker compose logs -f api     # 后端日志
docker compose logs -f web     # nginx 日志
```

访问 `http://<服务器IP>` 即可。

## 5. ⚠️ 重要：捆绑二进制的平台一致性

`claude-agent-sdk` 在 `_bundled/claude` 里捆绑了一个**平台相关的原生二进制**。
**构建时的平台必须等于运行时的平台**，否则后端 Agent（每日资讯 / 对话生成任务）
会启动失败，报 "Claude Code not found" 或 exec format error。

- **服务器是 x86_64（绝大多数云主机）**：直接在服务器上 `docker compose build`
  即可，pip 会拉到 amd64 版二进制。
- **你在 Apple Silicon (arm64) Mac 上构建、推到 amd64 服务器**：必须显式指定
  目标平台走 QEMU 模拟（较慢，但能拉到正确二进制）：

  ```bash
  docker buildx build --platform linux/amd64 -t pixelpack-api --load ./server
  docker buildx build --platform linux/amd64 -t pixelpack-web --load ./web
  docker compose up -d
  ```

  最省心的做法仍是**直接在服务器上构建**。

## 6. 数据备份 / 迁移

所有有状态数据都在仓库下的 `./data`：

```
./data/
├── data.db        # SQLite 数据库
└── uploads/       # 用户上传的图片 / 头像
```

备份：

```bash
tar czf pixelpack-data-$(date +%F).tar.gz data/
```

迁移到新机器：拷贝 `data/` 与 `server/.env` 即可。

## 7. 更新代码

```bash
git pull
docker compose up -d --build
```

`./data` 不受影响，数据不丢。

## 8. 常见问题

- **图片上传后 404 / 显示不出**：确认 `main.py` 中 `UPLOAD_DIR = settings.UPLOAD_DIR`
  （已修复历史 bug）。若仍异常，检查 `./data/uploads` 是否有写入权限。
- **每日资讯 / 对话生成不工作**：大概率是捆绑二进制平台不匹配，见第 5 节；
  或 `.env` 里 `ANTHROPIC_AUTH_TOKEN` 未填 / 失效。
- **改端口**：编辑 `docker-compose.yml` 中 `web.ports`，如 `"8080:80"`。
- **上 HTTPS / 域名**：在 `web` 之前再加一层反代（nginx/traefik + Let's Encrypt），
  或直接给 web 容器加证书。当前配置仅 HTTP，适合已有外层网关或内网场景。
