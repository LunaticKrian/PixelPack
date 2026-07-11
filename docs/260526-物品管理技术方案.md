# DailyStuff - 物品管理Web应用技术方案

## Context

目前市面上"物品日均成本计算"类应用几乎全是原生移动端 App（归物、Daily Penny、Skip or Buy），没有成熟的 Web 方案。本项目旨在构建一个 Web 端物品管理应用，用于记录物品、计算日均使用成本、追踪生命周期，支持小范围分享（家人/朋友）。

**前端视觉风格：像素风（Pixel Art）**

---

## 技术栈

| 层级 | 技术选型 | 理由 |
|------|---------|------|
| **后端** | FastAPI + SQLAlchemy 2.0 | 异步高性能，Python生态，自动生成API文档 |
| **数据库** | SQLite（开发）→ PostgreSQL（生产） | 小规模部署用SQLite足够，方便迁移 |
| **前端** | Vue 3 + TypeScript + Vite | 轻量灵活，中文生态好 |
| **UI组件库** | [Pixelium Design](https://github.com/shika-works/pixelium-design) + [NES.css](https://github.com/nostalgic-css/NES.css) | 详见下方"UI框架策略" |
| **图表** | ECharts + 自定义像素风主题 | 功能强大，可深度定制主题 |
| **HTTP客户端** | [ofetch](https://github.com/unjs/ofetch) | 轻量现代，支持拦截器，比axios更简洁 |
| **状态管理** | Pinia | Vue 3 官方推荐 |
| **认证** | JWT (python-jose) + passlib[bcrypt] | JWT令牌 + bcrypt密码哈希 |
| **数据库迁移** | Alembic | SQLAlchemy标配 |
| **图片存储** | 本地文件系统（开发）→ 对象存储（生产） | 先简单实现，后续可扩展 |

---

## UI 框架策略

### 风险评估

Pixelium Design（npm: `@pixelium/web-vue`）当前状态：
- 版本 v0.1.4（pre-1.0），API 可能变更
- 单人维护项目（602/606 commits 来自同一人）
- 228 stars，2025年8月创建
- 优势：70+ 组件，TypeScript，明暗主题，Tree-shakable

### 策略：NES.css 为主，Pixelium 按需补充

采用**两层架构**，降低对 Pixelium 的耦合依赖：

**第一层 — NES.css（稳定基础）**
- 20k+ stars，纯 CSS，无 JS 依赖，不会 break
- 提供核心像素风样式：按钮、容器、对话框、列表、图标、进度条
- 通过 CSS class 直接使用，与 Vue 组件无耦合

**第二层 — Pixelium Design（增强体验）**
- 仅用于 NES.css 无法覆盖的**交互型组件**
- 使用范围限制在：Form（表单校验）、Table（排序筛选）、Select/Dropdown、Pagination、Dialog、Notification
- **锁定版本号**（`package.json` 中写死具体版本），不使用 `^` 前缀
- 将 Pixelium 组件统一封装在 `src/components/pixel/` 目录下，若项目停止维护可直接替换内部实现

**降级方案**：如果 Pixelium 出现兼容性问题，可逐个替换为 NES.css 样式 + 自行封装逻辑，影响范围可控。

---

## 像素风设计规范

### 字体

| 用途 | 字体 | 来源 | 说明 |
|------|------|------|------|
| **英文/数字** | Press Start 2P | Google Fonts CDN | 经典8-bit像素字体 |
| **中文** | [Ark Pixel Font](https://github.com/TakWolf/ark-pixel-font) 16px | 自托管 WOFF2 (~0.48MB) | OFL-1.1 开源免费，支持 zh_cn/zh_tw/ja/ko |
| **代码/辅助** | VT323 | Google Fonts CDN | 像素等宽字体，用于数字展示 |

> 不使用 Zpix（7.18MB 太大，商用需 $1000 授权）。Ark Pixel Font 16px WOFF2 仅 0.48MB，免费商用。

### 色彩方案（Sweetie 16 变体 — Lospec 社区验证）
```
主色调:     #41a6f6 (天蓝)
强调色:     #b13e53 (暗红)
警告色:     #ef7d57 (暖橙)
成功色:     #38b764 (翡翠绿)
信息色:     #73eff7 (冰蓝)
背景色:     #1a1c2c (深蓝黑) / #e8e8e8 (浅色主题)
面板背景:   #333c57 / #d0d0d0
卡片背景:   #29366f / #f4f4f4
边框色:     #566c86 / #94b0c2
文字色:     #f4f4f4 / #1a1c2c
次要文字:   #94b0c2 / #333c57
```

### UI 元素规范
- **边框**: 3-4px 实线边框，无圆角（或 max 2px）
- **阴影**: 硬边缘偏移阴影（如 `3px 3px 0 #000`），无模糊
- **按钮**: 像素风格按钮，hover 时向下偏移 2px（按压效果）
- **图标**: 16x16 或 32x32 像素图标（FontAwesome Pixel 或手绘SVG）
- **动画**: 逐帧动画或 step 动画，模拟8-bit游戏效果
- **滚动条**: 自定义像素风滚动条
- **加载动画**: 像素风的 loading spinner 或进度条

---

## 数据模型

```
User
├── id, username, password_hash, email, avatar_url
├── created_at, updated_at
└── settings (JSON: default_currency, theme, etc.)

Category（分类）
├── id, user_id, name, icon, color, sort_order
└── parent_id (支持二级分类)

Tag（标签）
├── id, user_id, name, color
└── 多对多关联 Item

Item（物品 - 核心模型）
├── id, user_id, name, description
├── category_id, status (ACTIVE/IDLE/RETIRED/SOLD/DISCARDED)
├── purchase_date, purchase_price, currency (默认CNY)
├── purchase_channel (购买渠道，可选)
├── current_value (当前估值，可选)
├── warranty_expiry (保修截止日)
├── expected_lifespan (预期寿命天数，可选)
├── usage_count (使用次数，用户手动记录，可选)
├── retired_at, retired_reason
├── deleted_at (软删除，NULL表示未删除)
├── created_at, updated_at
└── 计算属性: daily_cost, per_use_cost, total_cost, usage_days

ItemImage（物品图片）
├── id, item_id, url, sort_order
└── created_at

AdditionalCost（附加费用）
├── id, item_id, name, amount, date
└── description (如: 维修费、配件费、保养费)

ItemTag（物品-标签关联）
├── item_id, tag_id
└── 联合主键
```

**相比初版的改动**：
- Item 新增 `currency` 字段，支持多币种
- Item 新增 `usage_count` 字段，支持"单次使用成本"计算
- Item 新增 `deleted_at` 软删除字段
- `image_urls` JSON 数组改为 `ItemImage` 关联表，SQLite 友好，支持排序
- 去掉 `purchase_channel` 从必填改为可选（简化录入）

---

## 核心计算逻辑

```python
# 使用天数（至少为1，避免除零）
purchase_date = item.purchase_date
end_date = item.retired_at or date.today()
usage_days = max(1, (end_date - purchase_date).days)

# 闲置天数（IDLE状态下不计入使用天数）
idle_days = sum(period.idle_days for period in item.idle_periods)
effective_days = max(1, usage_days - idle_days)

# 总投入成本
total_cost = item.purchase_price + sum(c.amount for c in item.additional_costs)

# 日均使用成本
daily_cost = total_cost / effective_days

# 单次使用成本（如果记录了使用次数）
per_use_cost = total_cost / max(1, item.usage_count) if item.usage_count else None

# 日均损耗（考虑当前估值，反映真实贬值）
daily_depreciation = (item.purchase_price - (item.current_value or 0)) / effective_days

# 物品状态机
#   ACTIVE ──→ IDLE ──→ ACTIVE (可恢复)
#     │                      │
#     └──→ RETIRED ──→ SOLD / DISCARDED
```

**关键边界处理**：
- `usage_days` 下限为 1，购买当天不会除零
- IDLE 状态单独记录闲置时间段，不计入 effective_days
- `usage_count` 为空时不计算单次成本，显示为"—"
- 所有金额计算使用 `Decimal` 类型，避免浮点精度问题

---

## API 设计

```
认证
  POST   /api/auth/register       (注册)
  POST   /api/auth/login          (登录，返回access_token + refresh_token)
  POST   /api/auth/logout         (登出，前端清除token即可，无需黑名单)
  POST   /api/auth/refresh        (刷新token)
  GET    /api/auth/me             (获取当前用户信息)
  PUT    /api/auth/me             (修改个人信息)
  PUT    /api/auth/password       (修改密码)

物品
  GET    /api/items
    ?keyword=        (名称搜索)
    &category_id=    (按分类筛选)
    &status=         (按状态筛选: ACTIVE/IDLE/RETIRED/SOLD/DISCARDED)
    &tag_id=         (按标签筛选)
    &sort_by=        (排序字段: daily_cost/purchase_date/usage_days/price)
    &order=          (asc/desc)
    &page=           (页码)
    &page_size=      (每页数量)
  POST   /api/items              (创建)
  GET    /api/items/{id}         (详情，含计算属性)
  PUT    /api/items/{id}         (更新)
  DELETE /api/items/{id}         (软删除)
  PATCH  /api/items/{id}/status  (状态变更，body: {status, reason?})

附加费用
  GET    /api/items/{id}/costs
  POST   /api/items/{id}/costs
  PUT    /api/costs/{id}
  DELETE /api/costs/{id}

物品图片
  POST   /api/items/{id}/images     (上传图片)
  PUT    /api/items/{id}/images/order (调整图片顺序)
  DELETE /api/images/{id}           (删除图片)

分类
  GET    /api/categories
  POST   /api/categories
  PUT    /api/categories/{id}
  DELETE /api/categories/{id}       (需检查是否有关联物品)

标签
  GET    /api/tags
  POST   /api/tags
  PUT    /api/tags/{id}
  DELETE /api/tags/{id}

统计
  GET    /api/stats/overview
    ?currency=       (币种筛选)
  GET    /api/stats/by-category
    ?start_date=     (时间范围起始)
    &end_date=       (时间范围结束)
  GET    /api/stats/daily-cost-rank
    ?limit=          (返回数量，默认10)
    &status=         (状态筛选)
  GET    /api/stats/trends
    ?period=         (统计粒度: month/quarter/year)
    &start_date=
    &end_date=
  GET    /api/stats/warranty-alerts
    ?days=           (未来N天内到期，默认30)
  GET    /api/stats/lifecycle
    ?category_id=    (可选分类筛选)

文件上传
  POST   /api/upload/image         (通用图片上传，返回url)
```

---

## 页面结构

```
/ (首页/Dashboard - 像素风仪表盘)
├── /login, /register (认证页)
├── /items (物品列表 - 像素卡片网格)
│   ├── /items/new (新增物品)
│   └── /items/:id (物品详情)
│       └── /items/:id/edit (编辑物品)
├── /categories (分类管理)
├── /tags (标签管理)
└── /stats (统计分析)
    ├── 总览仪表盘
    ├── 分类占比饼图
    ├── 月度趋势折线图
    └── 日均成本排行柱状图
```

---

## 项目结构

```
DailyStuff/
├── server/                     # 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI入口
│   │   ├── config.py          # 配置（环境变量 + pydantic-settings）
│   │   ├── database.py        # 数据库连接
│   │   ├── models/            # SQLAlchemy模型
│   │   │   ├── __init__.py    # 导出所有模型
│   │   │   ├── user.py
│   │   │   ├── item.py
│   │   │   ├── category.py
│   │   │   ├── tag.py
│   │   │   ├── cost.py
│   │   │   └── image.py
│   │   ├── schemas/           # Pydantic Schema
│   │   │   ├── auth.py
│   │   │   ├── item.py
│   │   │   ├── category.py
│   │   │   └── stats.py
│   │   ├── routers/           # API路由
│   │   │   ├── auth.py
│   │   │   ├── items.py
│   │   │   ├── categories.py
│   │   │   ├── tags.py
│   │   │   ├── stats.py
│   │   │   └── upload.py
│   │   ├── services/          # 业务逻辑
│   │   │   ├── auth.py
│   │   │   ├── item.py
│   │   │   └── stats.py
│   │   └── utils/
│   │       ├── security.py    # JWT + bcrypt 工具
│   │       └── deps.py        # FastAPI 依赖注入
│   ├── migrations/            # Alembic迁移
│   ├── uploads/               # 上传文件目录（开发环境）
│   ├── requirements.txt
│   └── alembic.ini
├── web/                        # 前端
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/
│   │   │   └── index.ts
│   │   ├── layouts/           # 布局组件
│   │   │   ├── MainLayout.vue # 主布局（侧边栏+顶栏+内容区）
│   │   │   └── AuthLayout.vue # 认证页布局（居中卡片）
│   │   ├── stores/            # Pinia 状态管理
│   │   │   ├── auth.ts
│   │   │   ├── items.ts
│   │   │   └── stats.ts
│   │   ├── api/               # ofetch 封装
│   │   │   ├── client.ts      # ofetch 实例（baseURL、拦截器、token注入）
│   │   │   ├── auth.ts
│   │   │   ├── items.ts
│   │   │   └── stats.ts
│   │   ├── views/             # 页面组件
│   │   │   ├── Login.vue
│   │   │   ├── Register.vue
│   │   │   ├── Dashboard.vue
│   │   │   ├── ItemList.vue
│   │   │   ├── ItemDetail.vue
│   │   │   ├── ItemForm.vue
│   │   │   ├── Categories.vue
│   │   │   ├── Tags.vue
│   │   │   └── Stats.vue
│   │   ├── components/
│   │   │   ├── pixel/         # Pixelium 组件封装层（降级替换入口）
│   │   │   │   ├── PButton.vue
│   │   │   │   ├── PTable.vue
│   │   │   │   ├── PForm.vue
│   │   │   │   ├── PDialog.vue
│   │   │   │   ├── PSelect.vue
│   │   │   │   ├── PPagination.vue
│   │   │   │   └── PNotification.ts
│   │   │   ├── ItemCard.vue
│   │   │   ├── CostBreakdown.vue
│   │   │   ├── StatusBadge.vue
│   │   │   └── charts/
│   │   │       ├── PixelPieChart.vue
│   │   │       ├── PixelBarChart.vue
│   │   │       └── PixelLineChart.vue
│   │   ├── styles/
│   │   │   ├── theme.css      # 主题变量 & 自定义配色
│   │   │   ├── fonts.css      # Ark Pixel Font + Press Start 2P 加载
│   │   │   ├── animations.css # 像素动画
│   │   │   └── nes-compat.css # NES.css 引入 & 自定义覆盖
│   │   ├── composables/       # Vue 组合式函数
│   │   │   ├── useAuth.ts
│   │   │   ├── useItems.ts
│   │   │   └── useStats.ts
│   │   ├── assets/
│   │   │   ├── pixel-icons/
│   │   │   └── pixel-images/
│   │   ├── types/             # TypeScript 类型定义
│   │   │   ├── item.ts
│   │   │   ├── user.ts
│   │   │   └── api.ts
│   │   └── utils/
│   │       ├── format.ts      # 金额格式化、日期格式化
│   │       └── calc.ts        # 前端计算辅助（日均成本展示）
│   ├── public/
│   │   └── fonts/             # Ark Pixel Font WOFF2 文件
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── deploy/                     # 部署配置
│   ├── Dockerfile              # 多阶段构建（前端build + 后端）
│   ├── docker-compose.yml
│   └── nginx.conf              # 前端静态文件serve + API反向代理
├── docs/
│   └── technical-plan.md      # 本文档
├── assets/
└── README.md
```

---

## 实施计划（分阶段）

### Phase 1: 基础骨架
1. 初始化后端 FastAPI 项目 + SQLAlchemy + Alembic
2. 初始化前端 Vue 3 + Vite + TypeScript 项目
3. 集成 NES.css + Pixelium Design（锁定版本）+ Ark Pixel Font
4. 实现用户注册/登录/密码修改（JWT + bcrypt）
5. 前端布局组件（MainLayout + AuthLayout）、路由、认证状态管理

### Phase 2: 核心CRUD
6. Item / Category / Tag 模型 + CRUD API（含软删除）
7. 前端物品列表页（筛选、排序、分页）
8. 前端物品新增/编辑表单（含图片上传）
9. 前端物品详情页（日均成本、使用天数、单次成本展示）

### Phase 3: 附加功能
10. AdditionalCost 模型 + API
11. 物品状态变更（状态机流转，含 IDLE 闲置记录）
12. 物品生命周期管理（退役、出售、报废）

### Phase 4: 数据统计
13. 后端统计 API（总览、分类、趋势、排行，支持时间范围筛选）
14. 前端 Dashboard 仪表盘
15. ECharts 像素风自定义主题图表
16. 保修到期提醒

### Phase 5: 优化与部署
17. 响应式布局优化（移动端适配）
18. 数据导出（CSV/Excel）
19. Docker 化部署（Dockerfile + docker-compose + nginx）
20. 性能优化（缓存、懒加载）

---

## 部署架构

```
┌─────────────┐     ┌──────────────────────┐
│   浏览器     │────→│   Nginx              │
└─────────────┘     │   ├── / → 静态文件     │
                    │   └── /api/* → uvicorn │
                    └──────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   FastAPI (uvicorn) │
                    │   ├── SQLite/PG     │
                    │   └── uploads/      │
                    └────────────────────┘
```

- 开发环境：前后端分别启动（Vite dev server + uvicorn），Vite proxy 转发 API
- 生产环境：前端 build 为静态文件，Nginx 同时 serve 静态文件和反向代理 API
- Docker 单容器部署：多阶段构建，Nginx + uvicorn 共存

---

## 验证方式

1. 启动后端: `cd server && uvicorn app.main:app --reload`，访问 `/docs` 验证 API
2. 启动前端: `cd web && npm run dev`，浏览器访问验证页面和像素风视觉效果
3. 端到端测试: 注册 → 登录 → 创建分类 → 添加物品 → 查看详情 → 查看统计
4. 计算验证: 手动计算某物品日均成本，与系统显示对比
5. 边界验证: 购买当天物品（usage_days=1）、无附加费用、IDLE状态物品的计算正确性
6. 视觉验证: 确认所有页面/组件符合像素风设计规范，中文字体正常渲染

---

## 竞品参考

| 应用 | 平台 | 核心功能 | 参考点 |
|------|------|---------|--------|
| [归物](https://guiwuapp.cn/) | iOS/Android | 日均成本、资产统计、生命周期管理 | 功能完整性参考 |
| [Daily Penny](https://apps.apple.com/br/app/daily-penny-show-daily-cost/id1619584088) | iOS | 单次/日均使用成本计算 | 简洁交互参考 |
| [Skip or Buy](https://apps.apple.com/us/app/skip-or-buy-cost-per-use/id6759465475) | iOS | 成本对比、换算工作时长 | 购买决策参考 |
| [记物本](https://www.notion.com/zh-cn/templates/dailycost) | Notion模板 | 物品价格记录、保质期提醒 | 功能点参考 |

---

## 开源资源参考

| 资源 | 用途 | 说明 |
|------|------|------|
| [Pixelium Design](https://github.com/shika-works/pixelium-design) | Vue 3 像素风交互组件 | npm: `@pixelium/web-vue`，锁定版本使用 |
| [NES.css](https://github.com/nostalgic-css/NES.css) | 像素风基础 CSS 样式 | 稳定可靠，20k+ stars |
| [Ark Pixel Font](https://github.com/TakWolf/ark-pixel-font) | 中文像素字体 | OFL-1.1 免费，16px WOFF2 仅 0.48MB |
| [Press Start 2P](https://fonts.google.com/specimen/Press+Start+2P) | 英文像素字体 | Google Fonts CDN |
| [ECharts](https://echarts.apache.org/) | 图表 | 自定义像素风主题 |
