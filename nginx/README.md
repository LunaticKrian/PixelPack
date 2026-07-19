# Nginx 网关配置

本目录是 `airc-nginx` 网关的站点配置，结构镜像服务器上的 `/opt/nginx/`，便于用 git 同步。

完整架构说明见 [`../docs/technology/260719-nginx部署架构.md`](../docs/technology/260719-nginx部署架构.md)。

## 目录结构

```
nginx/
├── conf.d/
│   ├── 00-upgrade-map.conf          # 全局 WebSocket 升级映射（http{} 内，全 nginx 唯一）
│   ├── pixelpack.airise.site.conf   # PixelPack 站点
│   └── _template.conf               # 新项目模板（复制后改 <project>）
└── snippets/
    └── proxy.conf                   # 反代通用参数（WS/SSE/上传/超时，location 内 include）
```

## 关键约定

- **`00-upgrade-map.conf` 必须且只能有一份**。它定义 `$connection_upgrade`，供所有站点的 WS 升级使用。文件名 `00-` 前缀确保它最先加载。
- **`snippets/proxy.conf` 在每个 `proxy_pass` 的 location 里 include**，统一 WS 升级、头透传、关缓冲、长超时，避免每个站点各写各的漏配。
- **静态 / 上传文件由网关直接 serve**（`root` / `alias` 指向挂载卷），不走后端。

## 部署到服务器

1. 把本目录同步到服务器：

   ```bash
   # 在服务器
   git pull
   rsync -av nginx/ /opt/nginx/
   ```

2. 确保 `airc-nginx` 容器挂载了这些路径（见架构文档 §6.3）：

   ```yaml
   volumes:
     - /opt/nginx/conf.d:/etc/nginx/conf.d:ro     # 多站点目录
     - /opt/nginx/snippets:/etc/nginx/snippets:ro # 复用片段
     - /opt/pixelpack/web/dist:/var/www/pixelpack:ro
     - /opt/pixelpack/data/uploads:/var/www/pixelpack-uploads:ro
     - /etc/letsencrypt:/etc/letsencrypt:ro
   networks:
     - airise-web: { external: true }
   ```

3. 校验并热加载：

   ```bash
   docker exec airc-nginx nginx -t
   docker exec airc-nginx nginx -s reload
   ```

## 证书路径

默认使用通配证书 `*.airise.site`（路径 `/etc/letsencrypt/live/airise.site/`）。
若某站点暂用单域证书，把该 conf 里的证书路径改为
`/etc/letsencrypt/live/<project>.airise.site/`。签发方式见架构文档 §8。
