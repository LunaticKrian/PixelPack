# PixelPack 部署指南（网关托管模式）

PixelPack 接入统一的 `airise-gateway` 网关：
- **前端 SPA** 由本项目的 `web` 容器提供（多阶段镜像：`node` 构建 → `nginx` 静态服务，纯静态叶子），网关 `location /` 反代到 `pixelpack-web`。
- **上传文件** 由网关直接 serve（宿主机路径，只读挂载）。
- **后端 api**（FastAPI/uvicorn）以裸容器跑，接入共享网络 `airise-web`，网关 `location /api/` 按容器名反代。
- HTTPS/WSS 在网关统一终结；`/api`、`/uploads`、WS 信令仍由网关单层处理（不进 web 容器）。

> 架构与多项目接入说明见 [`technology/260719-nginx部署架构.md`](../technology/260719-nginx部署架构.md)；新项目接入流程见 [`technology/260719-新服务上线与网关扩展.md`](../technology/260719-新服务上线与网关扩展.md)；本次上线修复见 [`updatelog.md`](../updatelog.md) 2026-07-19。

---

## 部署顺序总览

三者解耦，顺序固定为 **前端/后端容器 → 网关更新**：

```
§0 前置（首次/全局，一次性）
   │
   ▼
§1 部署后端 + 前端容器（pixelpack-api + pixelpack-web，接入 airise-web）
   │   ← 网关依赖容器名 pixelpack-api / pixelpack-web 已在网络内
   ▼
§2 部署/更新网关 airise-gateway（独立项目，挂载上传 + 证书，反代到 web 容器）
   │
   ▼
§3 端到端验证
```

---

## §0 前置（首次部署 / 全局，一次性）

网关侧的共享网络、通配证书、DNS 需先就位（详见架构文档 §7 / §8）：

```bash
# 1) 共享网络：api/web 容器与网关都接入，按容器名互通（external，须事先建）
docker network create airise-web

# 2) 项目目录与权限（前端 dist 不再需要放到宿主机，由容器构建）
mkdir -p /opt/pixelpack/data/uploads
chown -R 1000:1000 /opt/pixelpack/data      # 非 root api 容器用户(UID 1000)须能写

# 3) 拉代码
git clone https://github.com/LunaticKrian/PixelPack.git /opt/pixelpack
cd /opt/pixelpack

# 4) 后端密钥（不进 git / 不进镜像，compose env_file 注入）
cp server/.env.example server/.env
vi server/.env        # 填 ANTHROPIC_AUTH_TOKEN / ANTHROPIC_BASE_URL / ANTHROPIC_MODEL
chmod 600 server/.env
```

- **DNS**：主机记录 `pixelpack` / 类型 `A` / 记录值=服务器公网 IP（拼成 `pixelpack.airise.site`）。
- **证书**：通配 `*.airise.site`（DNS-01 签发），`/etc/letsencrypt/live/airise.site/`。签发与续期步骤见 [`technology/260719-通配证书签发.md`](../technology/260719-通配证书签发.md)。
- **网关项目**：`airise-gateway` 是独立仓库，同步到 `/opt/airise-gateway`（部署网关时用，见 §2）。

---

## §1 部署后端 + 前端容器

根 `docker-compose.yml` 同时定义 `api`（FastAPI/uvicorn）与 `web`（多阶段 nginx 静态）两个服务，均接入 `airise-web`，都不对主机暴露端口，外部一律经网关反代。

```bash
cd /opt/pixelpack
chown -R 1000:1000 data          # 每次部署前确认，避免 readonly database
docker compose up -d --build     # 构建 api + web（web 镜像内执行 npm run build）
docker compose logs -f api       # 观察后端启动；claude 二进制 / DB 迁移应无报错
docker compose logs -f web       # 前端容器（nginx）应正常监听 80
```

`DATABASE_URL` 与 `UPLOAD_DIR` 已在 `docker-compose.yml` 固定指向 `/app/data`，`.env` 无需填。

要点：
- **前端**：`web/Dockerfile` 两阶段（`node:24-alpine` 跑 `npm ci` + `vue-tsc` + `vite build` → `nginx:alpine` serve `dist`）。生产环境**无需在宿主机跑 npm**。
- 镜像内置非 root 用户 `app` + `IS_SANDBOX=1`，AI 功能（资讯 / 对话生成）在 root 下也能跑。
- 捆绑二进制平台须一致：**在服务器上直接 `docker compose build`** 最稳（见 §6）。
- 自检：`docker compose exec api sh -c 'echo IS_SANDBOX=$IS_SANDBOX'` 应为 `1`。
- 容器互通自检：`docker network inspect airise-web --format '{{range .Containers}}{{.Name}} {{end}}'` 应含 `pixelpack-api`、`pixelpack-web`、`airise-gateway`。

---

## §2 部署 / 更新网关 airise-gateway

网关是**独立项目/独立仓库**（`/opt/airise-gateway`），用官方 `nginx:alpine` + 卷挂载 conf.d/snippets/证书/上传，改 conf 后 `nginx -s reload` 即生效。

```bash
cd /opt/airise-gateway       # 独立仓库，git pull 或 rsync 同步
docker compose up -d         # 首次起容器（conf 卷挂载，通常无需 --build）

# 校验
docker exec airise-gateway nginx -t
curl -I https://pixelpack.airise.site   # 需 §1 的 pixelpack-web 已在 airise-web 内
docker compose logs -f nginx
```

`/opt/airise-gateway/docker-compose.yml` 只读挂载两项运行期数据：
- `/etc/letsencrypt` → 证书
- `/opt/pixelpack/data/uploads` → `/var/www/pixelpack-uploads`（上传直发）

> 前端 SPA 不再由网关挂载直发 —— 网关 `location /` 反代到 `pixelpack-web` 容器（见 `conf.d/pixelpack.airise.site.conf`）。

---

## §3 端到端验证

| 检查项 | 方法 |
|---|---|
| 前端可访问 | 浏览器开 `https://pixelpack.airise.site`，能进登录页 |
| API 通 | 登录、拉物品列表正常 |
| WS 信令 | `/api/rtc/signal` 不卡 pending（网关该 location 须 `proxy_buffering off` + WS 升级头，已在 `snippets/proxy.conf`） |
| 上传图片 | 物品图片上传后能预览（`/uploads/` alias 指向 `data/uploads`，目录属主 1000） |
| AI 功能 | 世界地图「发起侦测」、任务页 AI 对话不报 root 错误 |

---

## §4 日常更新（各组件各自的命令）

| 目标 | 命令 |
|---|---|
| 更新前端 | `cd /opt/pixelpack && git pull && docker compose up -d --build web`（重建 web 镜像，网关反代实时生效） |
| 更新后端 | `cd /opt/pixelpack && git pull && docker compose up -d --build api` |
| 更新前后端 | `cd /opt/pixelpack && git pull && docker compose up -d --build` |
| 更新网关配置 | 改 airise-gateway 仓库的 `conf.d/` 或 `snippets/` → `docker exec airise-gateway nginx -s reload`（卷挂载，无需 rebuild） |
| 网关改 compose（新增挂载卷） | `cd /opt/airise-gateway && docker compose up -d` |
| 仅续期证书（配置未变） | `docker exec airise-gateway nginx -s reload`（无需 rebuild） |

---

## §5 数据备份 / 迁移

```
/opt/pixelpack/data/
├── data.db        # SQLite
└── uploads/       # 上传文件 / 头像
```

```bash
tar czf pixelpack-data-$(date +%F).tar.gz data/
```

迁移到新机器：拷贝 `data/` 与 `server/.env`。`./data` 不受代码更新影响。

---

## §6 捆绑二进制的平台一致性

`claude-agent-sdk` 捆绑了平台相关的原生二进制（约 240MB），**构建平台必须等于运行平台**：

- 服务器是 x86_64：直接在服务器上 `docker compose build` 即可。
- 在 Apple Silicon 构建、跑在 amd64 服务器：用
  `docker buildx build --platform linux/amd64 -t pixelpack-api --load ./server`，
  然后 `docker compose up -d`。最省心仍是直接在服务器上构建。

> 镜像基础必须是 glibc 系（Debian slim），不能用 alpine——捆绑二进制是 glibc 编译，musl 跑不起来。

---

## §7 常见故障速查

- **`response from daemon: network airise-web not found`**：首次部署没建网，`docker network create airise-web`。
- **启动报 `attempt to write a readonly database`**：`data` 属主非 1000，`chown -R 1000:1000 data` 后重启 api。
- **AI 报 `--dangerously-skip-permissions cannot be used with root`**：镜像缺 `IS_SANDBOX=1`，确认跑的是最新 `--build` 的镜像（`docker compose exec api sh -c 'echo $IS_SANDBOX'` 应为 `1`）。
- **网关无限重启 `host not found in upstream "pixelpack-web"` / `"pixelpack-api"`**：相应容器没接入 `airise-web`、容器名拼错，或 `airise-web` 没建。也可能是 airise-gateway 的 `conf.d/` 里有带占位符的模板被当 `.conf` 加载（模板须为 `_template.example`，非 `.conf`）。
- **首页 502 / 连不上前端**：`pixelpack-web` 容器未起或不在 `airise-web`（网关按容器名 `pixelpack-web` 反代）。`docker compose ps web` + `docker network inspect airise-web`。
- **每日资讯 / 对话生成不工作**：多为捆绑二进制平台不匹配（见 §6）或 `.env` token 失效。
- **图片上传后 404**：网关 `/uploads/` alias 未指向 `data/uploads`，或该目录属主非 1000。
- **`/api/rtc/signal` 卡 pending**：网关该 location 未关 `proxy_buffering` 或缺 WS 升级头。
