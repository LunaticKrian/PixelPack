# airise-gateway（统一网关）

直接用官方 `nginx:alpine` 跑的独立容器 `airise-gateway`，**conf / snippets / 证书 / 静态产物全部卷挂载**。**不与 ripro / airc-nginx 共用**，独占宿主机 `80/443`。

- 站点配置（`conf.d/`）、`snippets/` 只读挂载进容器；**改 conf 后 `nginx -s reload` 即生效，无需 rebuild 镜像**。
- 完整架构说明见 [`../docs/technology/260719-nginx部署架构.md`](../docs/technology/260719-nginx部署架构.md)。

## 目录结构

```
nginx/
├── docker-compose.yml               # 独立容器 airise-gateway，绑 80/443，卷挂载
├── conf.d/                          # 只读挂载 → /etc/nginx/conf.d
│   ├── 00-upgrade-map.conf          # 全局 WebSocket 升级映射（http{} 内唯一）
│   ├── pixelpack.airise.site.conf   # PixelPack 站点
│   └── _template.example            # 新项目模板（非 .conf，nginx 不加载；复制后改名）
└── snippets/                        # 只读挂载 → /etc/nginx/snippets
    └── proxy.conf                   # 反代通用参数（WS/SSE/上传/超时）
```

> `Dockerfile` 已废弃（卷挂载模式不再自建镜像），保留仅供参考。

## 关键约定

- **`conf.d/` 里只能放真正的 `*.conf`**：模板用 `_template.example`（非 `.conf`），nginx 不会加载，避免占位符 `<project>-api` 被当 upstream 解析导致启动崩溃。
- **`00-upgrade-map.conf` 必须且只能有一份**：定义 `$connection_upgrade`，`00-` 前缀保证最先加载。
- **`snippets/proxy.conf` 在每个 `proxy_pass` 的 location 里 `include`**：统一 WS 升级、头透传、关缓冲、长超时。
- **静态 / 上传文件由网关直接 serve**（`root` / `alias` 指向挂载卷），不走后端。

## 部署到服务器

> 前置：本容器独占 `80/443`。删除旧 `airc-nginx` 前，**ripro 站点需先迁入本网关**（照抄 `_template.example` 新建一个站点 `.conf`），否则 ripro 会下线。

### 1. 准备数据与网络

```bash
# 共享网络（api 容器与网关都接入，按容器名互通）
docker network create airise-web

# PixelPack 数据目录
mkdir -p /opt/pixelpack/web /opt/pixelpack/data/uploads
chown -R 1000:1000 /opt/pixelpack/data          # 非 root api 容器用户

# SPA 产物
cd /opt/pixelpack/web && git clone <repo> . && npm install && npm run build
# → 产物在 /opt/pixelpack/web/dist

# 证书：通配 *.airise.site（见架构文档 §8），路径 /etc/letsencrypt/live/airise.site/
```

### 2. 启动网关

```bash
cd /opt/nginx            # 把本目录同步过去（git pull 或 rsync）
docker compose up -d
```

### 3. 校验

```bash
docker exec airise-gateway nginx -t
curl -I https://pixelpack.airise.site
```

## 日常操作

| 场景 | 命令 |
|---|---|
| 改了 `conf.d/` / `snippets/`（增删站点、改路由） | `docker exec airise-gateway nginx -s reload`（卷挂载实时反映，无需 rebuild） |
| 改了 `docker-compose.yml`（如新增挂载卷、端口） | `docker compose up -d`（重建容器使新配置生效） |
| 看日志 | `docker compose logs -f nginx` |

> 卷挂载模式：conf 是宿主机文件直接挂进容器，改完 `reload` 即可，不再需要 `--build`。

## 证书路径

默认通配证书 `*.airise.site`（`/etc/letsencrypt/live/airise.site/`）。
某站点暂用单域证书时，把该 conf 的证书路径改为
`/etc/letsencrypt/live/<project>.airise.site/`，然后 `docker exec airise-gateway nginx -s reload`。签发方式见架构文档 §8。
