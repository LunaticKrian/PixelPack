# 仓库更新日志

PS：更新记录以日期倒排更新

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

