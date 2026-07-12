# 仓库更新日志

PS：更新记录以日期倒排更新

## 2026年07月12日

### 重构：每日任务系统 V1.0（手动自定义 + AI 自然语言生成）

把原本「硬编码 `QUEST_DEFS` + 每日随机抽样」的固定任务系统，重构为「手动自定义 + AI 对话生成 + 等级经验联动 + 任务核心成就」的可成长任务系统。技术方案见 `docs/technology/060712-每日任务系统.md`，设计稿见 `design/260712-dailytask/`。

**设计稿**（`design/260712-dailytask/`，静态原型 + 交互演示）
- 委托大厅（任务页）：分类瓷砖 + 难度星 + 完成印章 + 浮动经验；侧栏等级/打卡/成就格
- NEXA 任务内核（对话页）：未来科技设定，CSS 绘制内核头像 + 命令行输入 + 任务即时插入卡
- 拉丁/数字用 Chakra Petch（清爽），中文回退像素字体；图标用单色几何 dingbat（移除彩色 emoji）

**后端核心**（`server/app/`）
- `models/task.py`：新增 `Task` 表（title/description/category/source/target/progress/completed/exp_reward/due_date/recurrence…），每日清单 = `due_date == today`
- `models/user.py` + `utils/migrate.py` + `main.py`：`User` 加 `exp` 独立列，启动时 `ensure_column` 幂等迁移（`create_all` 不 ALTER 已存表）
- `services/task.py`：任务 CRUD + `complete_task`（加经验→写日志→判成就→升级日志）+ 撤销 + 多步进度
- `services/quest.py`：重写为**任务核心 12 成就**（初试身手 / 坚持十连 / 半百里程 / 百炼成钢 / 三日不辍 / 一周不缺 / 月度勤勉 / 完美一天 / 学者 / 智者辅佐 / 自律工匠 / 百日征途）+ exp 等级（`exp // 50 + 1`）+ 连续打卡计算
- `routers/tasks.py`：`/api/tasks` 全套（list/create/patch/delete/complete/uncomplete/progress）
- 移除物品增删改的旧任务埋点（`routers/items.py`），物品不再驱动任务系统

**AI 对话生成**（复用 intel 的 `claude-agent-sdk` + GLM 模式）
- `models/chat.py`：`ChatSession` / `ChatMessage`（对话入库）
- `services/task_agent.py`：per-request MCP 工具工厂（`list_today_tasks` 查重 + `create_task` **function call 直接写库**）+ `run_agent()` 流式生成器
- `services/chat.py`：会话/消息持久化、首条消息自动生成标题
- `routers/chat.py`：会话 CRUD + `POST /messages` **SSE 流式**（事件 `start/delta/tool/task_created/done/end`），per-session `asyncio.Lock` 防并发，独立 session 落库助手消息规避 `get_db` 流式关闭陷阱
- 实测：GLM 6 轮 ~26s，`list_today_tasks` → 4× `create_task`（source=ai）→ 总结，事件流 + 任务入库 + 消息持久化全通

**Web 实现**
- `views/Quests.vue` 重写为「委托大厅」任务页：今日清单 + 完成印章 + 新增/编辑/删除 + 多步进度 + 侧栏（等级经验条/连续打卡/今日进度/成就格），沿用 `--pixel-*` / `.pixel-border` / Press Start 2P 数字 / `var(--font-pixel)` 中文
- `views/Chat.vue` 新增 NEXA 对话页：会话侧栏 + 消息流 + 流式打字机（闪烁光标）+ `task_created` 即时插入卡 + `tool` 状态行，文本色统一白色
- `utils/sse.ts`：带 JWT 的 SSE 客户端（`fetch` + `ReadableStream` + 401 自动刷新，替代不能带头的 `EventSource`）
- `api/tasks.ts` / `api/chat.ts` / `types/task.ts` / `types/chat.ts` 新增；`api/quests.ts` / `types/quest.ts` 改为新 summary 结构
- 顶部导航新增「委托大厅」「AI 对话」入口；路由 `/quests` `/chat`

### 修复：经验不持久化 + 成就死代码（任务系统重构附带）
- 经验原本存 `User.settings` JSON 的 `quest_exp`/`daily_completed`，该 JSON 列未用 `MutableDict`，SQLAlchemy 检测不到原地修改 → 实测 `users.settings` 全空、经验从未真正写入。改为 `User.exp` 独立列持久化（验证：完成任务后 `user.exp` 正确累加）
- `WARRANTY_WATCHER` 成就在 `check_achievements` 无判定条件 → 永不解锁；随成就体系整体重设计移除

## 2026年07月11日

### 新增：世界地图模块（AI 技术情报每日推送与历史查看）

顶部导航「角色信息」右侧新增「❖ 世界地图」入口，用于 AI 技术文章的每日推送与历史回溯。

**设计稿**（`design/world-map/`，静态原型）
- 像素 RPG 风格静态页面：信号台（每日推送）+ 像素世界地图 + 航海日志（历史）
- 文件：`world-map.html` / `styles.css` / `main.js`

**Web 实现**（纯前端 + Mock，后端待接入）
- 路由 `/world-map`（`web/src/router/index.ts`）+ 顶部导航项（`web/src/layouts/MainLayout.vue`）
- `web/src/types/intel.ts`：六大知识疆域常量（大模型 / 智能体 / 视觉 / 基建 / 研究 / 工具）与类型定义
- `web/src/api/intel.ts`：Mock 数据层（`listTodayIntel` / `listArchive` / `getIntelStats`），返回 Promise 便于后续替换为真实 API
- `web/src/views/WorldMap.vue`：信号台（ON AIR 广播 + 打字机 + 统计卡 + 今日情报卡）+ 航海日志（按月分组 + 疆域筛选 + 未读徽标）+ 阅读模态

**迭代**
- 经反馈移除「像素世界地图」版块（其筛选功能与日志 chips 重复、占空间过大），未读计数合并进航海日志的筛选 chips，信息零丢失

### 接入：Claude Agent SDK（经 GLM 代理）驱动真实情报抓取
世界地图从 Mock 切换为真实后端。Agent 走 GLM 的 Anthropic 兼容端点（`open.bigmodel.cn/api/anthropic`），不依赖官方 Anthropic Key。

**后端**（`server/app/`）
- `services/intel_agent.py`：用 `claude-agent-sdk` 的 `query()` + `output_format`（JSON Schema 结构化输出）驱动 Agent；内置进程内 MCP 工具 `search_ai_news`（RSS 聚合，feedparser+httpx）与 `fetch_page`（html2text 抓全文），规避 GLM 不支持的 WebSearch/WebFetch
- `services/intel.py`：`generate_intel_now`（`asyncio.Lock` 防并发）/ `scheduled_generate_intel` / `store_daily_intel` / `list_today` / `list_archive`（一天一页）/ `get_stats`
- `routers/intel.py`：`GET /today` `GET /archive` `GET /stats` `POST /generate`（手动触发，`overwrite` 参数）
- APScheduler 定时任务（`INTEL_CRON_HOUR/MINUTE`）每日自动抓取；GLM 配置写入 `server/.env`（已 gitignore），`intel_agent` 启动时把 Settings 注入 `os.environ` 供子进程继承
- 技术方案文档：`docs/technology/260711-ClaudeCode接入.md`

**Web 对接**
- `api/intel.ts` / `types/intel.ts` 由 Mock 切真实接口；`generateIntel` 超时 300s（Agent 含 RSS 抓取实测约 2–3 分钟）

### 迭代：航海日志分页与侦测交互
- **一天一分页**：`ArchivePageResponse` 改为日维度（`date / page / totalPages / dates`），按 `DISTINCT` 日期定位，疆域筛选自动跳过空天；pager 改为日导航（「第 X / Y 天」+ 前/后一天日期标注）
- **侦测控制台**（主动发起检索）：信号台底部新增雷达扫描动画 + 「发起侦测」按钮，点击触发 `POST /generate` 并循环状态文案 + 计时，成功后刷新今日情报与统计
- **翻页抖动修复**：翻页/切疆域改用保留旧内容 + 半透明蒙层（不再整块塌陷为 spinner），pager.y 采样波动 0px
- **渲染闪烁修复**：`stagger-list` 入场动画只在首次加载播一次，翻页不再重播
- **日期日历**：分页器日期选择改用项目像素日历组件 `PixelDatePicker`（新增 `dropUp` 向上展开 / `markedDates` 标记有情报日 / `restrictToMarked` 置灰空日三个可选 prop，默认关闭不影响其余调用），有情报日点哪跳哪、空日不可选
- **移除空页占位**：删掉「该疆域暂无历史记录」空状态块
- 路由调整为 `/260711-world-map`

