# PixelPack

一款 RPG 像素风格的个人物品管理与日常追踪系统。将你的物品、消费、任务以游戏化的方式管理起来。

## 功能

- **物品管理** — 记录物品信息（价格、购买渠道、保修期、标签分类），自动计算日均成本
- **角色系统** — 上传立绘、设置角色名和职业、记录生日与星座
- **每日任务** — 自动生成的每日任务（添加物品、记录消费等），完成后获得 EXP
- **成就系统** — 收集类成就（首次添加、收集达人等），解锁后记录到冒险日志
- **冒险日志** — 自动记录系统事件 + 用户手动写日志，RPG 风格时间线
- **数据统计** — 消费趋势、物品状态分布、保修提醒等可视化图表
- **像素风 UI** — 基于 NES.css 的像素艺术主题，Press Start 2P / Ark Pixel 字体

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vue 3.5 + TypeScript + Pinia 3 + Vue Router 4 + Vite 8 |
| 后端 | FastAPI + SQLAlchemy 2.0 (async) + SQLite (aiosqlite) |
| 认证 | JWT (access + refresh token) |
| 图表 | ECharts 6 |
| 风格 | NES.css + 自定义像素风组件 |

## 项目结构

```
PixelPack/
├── server/                # Python 后端
│   ├── app/
│   │   ├── main.py        # FastAPI 入口，路由注册，静态文件
│   │   ├── config.py      # 配置（数据库、密钥、上传目录）
│   │   ├── database.py    # SQLAlchemy async 引擎 + Session
│   │   ├── models/        # ORM 模型（User, Item, Journal, Quest...）
│   │   ├── schemas/       # Pydantic 请求/响应模型
│   │   ├── services/      # 业务逻辑层
│   │   ├── routers/       # API 路由（REST 端点）
│   │   └── utils/         # JWT、密码哈希、依赖注入
│   └── requirements.txt
├── web/                   # Vue 前端
│   ├── src/
│   │   ├── api/           # ofetch API 封装
│   │   ├── components/    # 可复用组件（PixelDatePicker 等）
│   │   ├── layouts/       # 页面布局（AuthLayout, MainLayout）
│   │   ├── router/        # 路由配置 + 导航守卫
│   │   ├── stores/        # Pinia 状态管理（auth, notification）
│   │   ├── styles/        # 全局样式（像素风主题、动画、字体）
│   │   ├── types/         # TypeScript 类型定义
│   │   ├── utils/         # 工具函数（格式化、导出、计算）
│   │   └── views/         # 页面组件（Dashboard, ItemList, Quests...）
│   └── package.json
└── uploads/               # 用户上传的图片（gitignored）
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- npm 9+

### 后端

虚拟环境创建在**项目根目录**（前后端共用一个仓库，Python 仅用于后端）：

```bash
# 在项目根目录
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r server/requirements.txt
```

启动开发服务器（⚠️ 必须在 `server/` 目录下运行，因为 `DATABASE_URL` 和 `UPLOAD_DIR` 是相对路径）：

```bash
cd server
uvicorn app.main:app --reload --port 8000
```

启动后访问 `http://127.0.0.1:8000/docs` 查看 API 文档。

### 前端

```bash
cd web
npm install
npm run dev
```

前端开发服务器运行在 `http://localhost:3000`，自动代理 `/api` 和 `/uploads` 到后端 `http://127.0.0.1:8000`。

### 生产构建

```bash
# 后端
cd server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端
cd web
npm run build
```

## API 概览

| 路径前缀 | 说明 |
|----------|------|
| `/api/auth` | 注册、登录、Token 刷新、个人信息更新 |
| `/api/items` | 物品 CRUD、图片上传、状态变更、CSV 导出 |
| `/api/categories` | 分类管理 |
| `/api/tags` | 标签管理 |
| `/api/journals` | 冒险日志（系统自动 + 手动创建） |
| `/api/quests` | 每日任务进度、成就查询 |
| `/api/stats` | 数据总览、最近物品、保修提醒 |

所有需要认证的端点使用 `Authorization: Bearer <token>` 头部。

## 配置

后端配置通过环境变量或 `server/.env` 文件：

```env
DATABASE_URL=sqlite+aiosqlite:///./data.db
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
UPLOAD_DIR=uploads
```

## License

MIT
