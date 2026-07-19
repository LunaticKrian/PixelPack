# airise-gateway（统一网关）

自包含的 nginx 网关镜像 + 独立容器 `airise-gateway`。**不与 ripro / airc-nginx 共用容器**，独占宿主机 `80/443`。

- 站点配置（`conf.d/`、`snippets/`）在**构建期烤进镜像**，运行期只挂载会变的数据（证书、SPA 产物、上传文件）。
- 完整架构说明见 [`../docs/technology/260719-nginx部署架构.md`](../docs/technology/260719-nginx部署架构.md)。

## 目录结构

```
nginx/
├── Dockerfile                       # 自包含网关镜像（conf 构建期 COPY 进去）
├── docker-compose.yml               # 独立容器 airise-gateway，绑 80/443
├── conf.d/
│   ├── 00-upgrade-map.conf          # 全局 WebSocket 升级映射（http{} 内唯一）
│   ├── pixelpack.airise.site.conf   # PixelPack 站点
│   └── _template.conf               # 新项目模板（复制后改 <project>）
└── snippets/
    └── proxy.conf                   # 反代通用参数（WS/SSE/上传/超时）
```

## 关键约定

- **`00-upgrade-map.conf` 必须且只能有一份**：定义 `$connection_upgrade`，`00-` 前缀保证最先加载。
- **`snippets/proxy.conf` 在每个 `proxy_pass` 的 location 里 `include`**：统一 WS 升级、头透传、关缓冲、长超时。
- **静态 / 上传文件由网关直接 serve**（`root` / `alias` 指向挂载卷），不走后端。

## 部署到服务器

> 前置：本容器独占 `80/443`。删除旧 `airc-nginx` 前，**ripro 站点需先迁入本网关**（照抄 `_template.conf` 新建一个站点文件并 rebuild），否则 ripro 会下线。

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

### 2. 构建并启动网关

```bash
cd /opt/nginx            # 把本目录同步过去（git pull 或 rsync）
docker compose up -d --build
```

### 3. 校验

```bash
docker exec airise-gateway nginx -t
curl -I https://pixelpack.airise.site
```

## 日常操作

| 场景 | 命令 |
|---|---|
| 改了 `conf.d/` / `snippets/` | `docker compose up -d --build`（重建镜像 + 替换容器） |
| 只想热加载（仅证书续期等不涉及配置时） | `docker exec airise-gateway nginx -s reload` |
| 看日志 | `docker compose logs -f nginx` |

> 与旧方案的区别：旧方案把 `conf.d` 目录 bind-mount 进 `airc-nginx`、靠 `nginx -s reload` 生效；新方案 conf **烤进镜像**，配置变更必须 `--build`。这换来的是镜像自包含、可版本化、不依赖宿主机 conf 目录结构。

## 证书路径

默认通配证书 `*.airise.site`（`/etc/letsencrypt/live/airise.site/`）。
某站点暂用单域证书时，把该 conf 的证书路径改为
`/etc/letsencrypt/live/<project>.airise.site/`，然后 `--build`。签发方式见架构文档 §8。
