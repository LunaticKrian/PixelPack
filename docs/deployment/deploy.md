# PixelPack 部署指南（网关托管模式）

PixelPack 接入统一的 `airise-gateway` 网关：
- **前端 SPA** 与 **上传文件**由网关直接 serve（宿主机路径，只读挂载）。
- **后端 api**（FastAPI/uvicorn）以裸容器跑，接入共享网络 `airise-web`，网关按容器名反代。
- 不再有内层 nginx；HTTPS/WSS 在网关统一终结。

> 架构与多项目接入说明见 [`technology/260719-nginx部署架构.md`](technology/260719-nginx部署架构.md)；新项目接入流程见 [`technology/260719-新服务上线与网关扩展.md`](technology/260719-新服务上线与网关扩展.md)；本次上线修复见 [`updatelog.md`](updatelog.md) 2026-07-19。

---

## 部署顺序总览

三者解耦，顺序固定为 **前端构建 → 后端部署 → 网关更新**：

```
§0 前置（首次/全局，一次性）
   │
   ▼
§1 构建前端（宿主机 npm run build → /opt/pixelpack/web/dist）
   │
   ▼
§2 部署后端 server（容器 pixelpack-api，接入 airise-web）
   │   ← 网关依赖容器名 pixelpack-api 已在网络内
   ▼
§3 部署/更新网关 airise-gateway（挂载前端产物 + 上传 + 证书）
   │   ← 网关依赖前端产物已就位
   ▼
§4 端到端验证
```

---

## §0 前置（首次部署 / 全局，一次性）

网关侧的共享网络、通配证书、DNS 需先就位（详见架构文档 §7 / §8）：

```bash
# 1) 共享网络：api 容器与网关都接入，按容器名互通（external，须事先建）
docker network create airise-web

# 2) 项目目录与权限
mkdir -p /opt/pixelpack/web /opt/pixelpack/data/uploads
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
- **证书**：通配 `*.airise.site`（DNS-01 签发），`/etc/letsencrypt/live/airise.site/`。签发与续期步骤见 [`technology/260719-通配证书签发.md`](technology/260719-通配证书签发.md)。
- **网关目录**：`nginx/` 同步到 `/opt/nginx`（部署网关时用，见 §3）。

---

## §1 构建前端（宿主机，网关直发）

前端 SPA 由网关从 `/opt/pixelpack/web/dist` 只读直发，故**必须在宿主机构建**：

```bash
cd /opt/pixelpack/web
npm install          # 首次
npm run build        # 产物 → web/dist
```

> 之后更新前端只需 `git pull && npm run build`，网关实时反映（只读挂载），**无需重启任何容器**。

---

## §2 部署后端 server

容器名 `pixelpack-api`，不对主机暴露端口，外部一律经网关反代。

```bash
cd /opt/pixelpack
chown -R 1000:1000 data          # 每次部署前确认，避免 readonly database
docker compose up -d --build     # 用根目录 docker-compose.yml
docker compose logs -f api       # 观察启动；claude 二进制 / DB 迁移应无报错
```

`DATABASE_URL` 与 `UPLOAD_DIR` 已在 `docker-compose.yml` 固定指向 `/app/data`，`.env` 无需填。

要点：
- 镜像内置非 root 用户 `app` + `IS_SANDBOX=1`，AI 功能（资讯 / 对话生成）在 root 下也能跑。
- 捆绑二进制平台须一致：**在服务器上直接 `docker compose build`** 最稳（见 §7）。
- 自检：`docker compose exec api sh -c 'echo IS_SANDBOX=$IS_SANDBOX'` 应为 `1`。

---

## §3 部署 / 更新网关 airise-gateway

网关是独立容器（仓库 `nginx/` 自包含镜像），`conf.d/` + `snippets/` 在**构建期烤进镜像**，配置变更必须 `--build`。

```bash
# 同步 nginx/ 目录到 /opt/nginx（git pull 或 rsync）
cd /opt/nginx
docker compose up -d --build

# 校验
docker exec airise-gateway nginx -t
curl -I https://pixelpack.airise.site
docker compose logs -f nginx
```

`/opt/nginx/docker-compose.yml` 挂载三项运行期数据（均只读）：
- `/etc/letsencrypt` → 证书
- `/opt/pixelpack/web/dist` → `/var/www/pixelpack`（SPA 直发）
- `/opt/pixelpack/data/uploads` → `/var/www/pixelpack-uploads`（上传直发）

> 与旧方案区别：旧方案把 `conf.d` bind-mount 进 `airc-nginx` 靠 `nginx -s reload` 生效；新方案 conf **烤进镜像**，配置变更必须 `--build`，换来镜像自包含、可版本化。

---

## §4 端到端验证

| 检查项 | 方法 |
|---|---|
| 前端可访问 | 浏览器开 `https://pixelpack.airise.site`，能进登录页 |
| API 通 | 登录、拉物品列表正常 |
| WS 信令 | `/api/rtc/signal` 不卡 pending（网关该 location 须 `proxy_buffering off` + WS 升级头，已在 `snippets/proxy.conf`） |
| 上传图片 | 物品图片上传后能预览（`/uploads/` alias 指向 `data/uploads`，目录属主 1000） |
| AI 功能 | 世界地图「发起侦测」、任务页 AI 对话不报 root 错误 |

---

## §5 日常更新（三者各自的命令）

| 目标 | 命令 |
|---|---|
| 更新前端 | `cd web && git pull && npm run build`（网关实时生效，无需重启） |
| 更新后端 | `cd /opt/pixelpack && git pull && docker compose up -d --build` |
| 更新网关配置 | 改 `nginx/conf.d` 或 `snippets` → `cd /opt/nginx && docker compose up -d --build` |
| 仅续期证书（配置未变） | `docker exec airise-gateway nginx -s reload`（无需 rebuild） |

---

## §6 数据备份 / 迁移

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

## §7 捆绑二进制的平台一致性

`claude-agent-sdk` 捆绑了平台相关的原生二进制（约 240MB），**构建平台必须等于运行平台**：

- 服务器是 x86_64：直接在服务器上 `docker compose build` 即可。
- 在 Apple Silicon 构建、跑在 amd64 服务器：用
  `docker buildx build --platform linux/amd64 -t pixelpack-api --load ./server`，
  然后 `docker compose up -d`。最省心仍是直接在服务器上构建。

> 镜像基础必须是 glibc 系（Debian slim），不能用 alpine——捆绑二进制是 glibc 编译，musl 跑不起来。

---

## §8 常见故障速查

- **`response from daemon: network airise-web not found`**：首次部署没建网，`docker network create airise-web`。
- **启动报 `attempt to write a readonly database`**：`data` 属主非 1000，`chown -R 1000:1000 data` 后重启 api。
- **AI 报 `--dangerously-skip-permissions cannot be used with root`**：镜像缺 `IS_SANDBOX=1`，确认跑的是最新 `--build` 的镜像（`docker compose exec api sh -c 'echo $IS_SANDBOX'` 应为 `1`）。
- **网关无限重启 `host not found in upstream "<project>-api"`**：模板 `_template.conf` 混进镜像（确认 `nginx/.dockerignore` 已排除），或后端容器名 / 网络名拼错（确认 `pixelpack-api` 在 `airise-web`）。
- **每日资讯 / 对话生成不工作**：多为捆绑二进制平台不匹配（见 §7）或 `.env` token 失效。
- **图片上传后 404**：网关 `/uploads/` alias 未指向 `data/uploads`，或该目录属主非 1000。
- **`/api/rtc/signal` 卡 pending**：网关该 location 未关 `proxy_buffering` 或缺 WS 升级头。
