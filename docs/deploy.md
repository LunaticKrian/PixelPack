# PixelPack 部署指南（网关托管模式）

PixelPack 接入统一的 `airc-nginx` 网关：
- **前端 SPA** 与 **上传文件**由网关直接 serve（宿主机路径，只读挂载）。
- **后端 api**（FastAPI/uvicorn）以裸容器跑，接入共享网络 `airise-web`，网关按容器名反代。
- 不再有内层 nginx；HTTPS/WSS 在网关统一终结。

> 完整架构与多项目接入说明见 [`docs/technology/260719-nginx部署架构.md`](technology/260719-nginx部署架构.md)。

---

## 0. 前置（网关侧，一次性）

确保已执行（详见架构文档 §7）：

- `docker network create airise-web`
- airc-nginx 已加入 `airise-web` 网络，并挂载了 PixelPack 的 dist 与 uploads（只读）。
- `/opt/nginx/conf.d/pixelpack.airise.site.conf` 已就位。
- DNS：`pixelpack.airise.site` → 服务器 IP；证书已签发。

## 1. 拉取代码

```bash
git clone https://github.com/LunaticKrian/PixelPack.git /opt/pixelpack
cd /opt/pixelpack
```

## 2. 配置密钥（.env）

`.env` **不进 git、不进镜像**，仅服务器本地创建，由 compose 运行时注入。

```bash
cp server/.env.example server/.env
vi server/.env     # 填入真实的 ANTHROPIC_AUTH_TOKEN
chmod 600 server/.env
```

> `DATABASE_URL` 与 `UPLOAD_DIR` 已在 `docker-compose.yml` 中固定指向 `/app/data`，`.env` 无需填。

## 3. 数据目录权限

后端镜像以非 root 用户 `app`(UID 1000) 运行，`./data` 必须归 1000：

```bash
mkdir -p data
chown -R 1000:1000 data
```

## 4. 启动后端

```bash
docker compose up -d --build
```

首次构建较慢（`claude-agent-sdk` 会下载约 240MB 的捆绑二进制）。

```bash
docker compose logs -f api     # 查看后端日志
```

## 5. 构建前端到宿主机（网关直发）

前端由网关从 `/opt/pixelpack/web/dist` 直发，所以要在宿主机上构建：

```bash
cd web
npm install        # 首次
npm run build      # 产物 → web/dist
```

更新前端只需重新 `npm run build`，网关立即生效（只读挂载实时反映）。

## 6. 访问

```
https://pixelpack.airise.site
```

---

## 7. ⚠️ 捆绑二进制的平台一致性

`claude-agent-sdk` 捆绑了平台相关的原生二进制，**构建平台必须等于运行平台**：

- 服务器是 x86_64：直接在服务器上 `docker compose build` 即可。
- 在 Apple Silicon 构建、跑在 amd64 服务器：用
  `docker buildx build --platform linux/amd64 -t pixelpack-api --load ./server`，
  然后 `docker compose up -d`。最省心仍是直接在服务器上构建。

## 8. 数据备份 / 迁移

```
/opt/pixelpack/data/
├── data.db        # SQLite
└── uploads/       # 上传文件 / 头像
```

```bash
tar czf pixelpack-data-$(date +%F).tar.gz data/
```

迁移到新机器：拷贝 `data/` 与 `server/.env`。

## 9. 更新代码

```bash
git pull
docker compose up -d --build       # 后端
cd web && npm run build            # 前端
```

`./data` 不受影响。

## 10. 常见问题

- **图片上传后 404**：检查网关 `pixelpack.airise.site.conf` 的 `/uploads/` alias 是否指向
  `/opt/pixelpack/data/uploads`，以及该目录属主是否为 1000（api 需写入）。
- **`/api/rtc/signal` 信令卡 pending**：网关该 location 必须含
  `proxy_set_header Upgrade / Connection "upgrade"` 且 `proxy_buffering off`。
- **AI 功能报 `--dangerously-skip-permissions cannot be used with root`**：
  后端镜像已内置非 root 用户 `app`，并设了 `IS_SANDBOX=1`（claude 官方沙箱旁路开关，
  使 `bypassPermissions` 在 root 下也能跑）。若仍报错，确认线上容器跑的是最新构建的镜像
  （`docker compose build --no-cache` 后重启），且 `./data` 已 `chown -R 1000:1000`。
  如运行时被强制以 root 拉起，`IS_SANDBOX=1` 已能兜底，无需额外处理。
- **每日资讯 / 对话生成不工作**：多为捆绑二进制平台不匹配（见 §7）或 `.env` token 失效。
