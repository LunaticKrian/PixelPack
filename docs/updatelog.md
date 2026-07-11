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

