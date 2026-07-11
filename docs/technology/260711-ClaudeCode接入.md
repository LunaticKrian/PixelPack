# PixelPack · 接入 Claude Code (Agent SDK) 实现 AI 资讯自动获取

> 日期：2026-07-11
> 模块：世界地图 / 信号台（AI 技术情报每日推送）
> 运行环境：**GLM（`https://open.bigmodel.cn/api/anthropic`）+ `claude-agent-sdk` 0.2.116**（已实测，见 §3）
> 目标：在后端接入 Claude Agent SDK，用 Agent 的能力自动抓取、归纳 AI 资讯，替换前端目前的 Mock 数据。

> **实现状态：✅ 已完成并端到端验证（Phase 1–3）**
> - 后端：model/schema/3 个 service/router/config/main 全部落地，读取 3 端点 + 手动生成端点 + APScheduler 每日定时已接通。
> - Agent 生成：在真实 GLM 跑通——`search_ai_news` 从 12 个 RSS 源抓 35 条候选 → `fetch_page` 读原文 → 结构化输出 6 篇 → 入库，`subtype=success`。
> - 前端：`api/intel.ts` 切真实 ofetch，`WorldMap.vue` 不动；浏览器实测渲染 6 张情报卡 + 统计 `6/7/9/6`，与后端一致。
> - 待办（Phase 4）：Anthropic RSS 源 404（已优雅跳过，可移除/换 URL）；RSS 源健康巡检；成本日志。
> - ⚠️ **运行前提**：后端进程需带 GLM 环境变量（`ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_MODEL`），
>   写进 `server/.env`（已 gitignore）即可——`intel_agent` 启动时会把 `.env` 里的值注入 `os.environ`，供 Agent SDK 子进程继承。

---

## 1. Context（背景）

「世界地图」是 PixelPack 的 AI 技术情报模块，分两幕：

- **信号台（今日推送）**：每天聚合一批 AI 资讯，按六大知识疆域（大模型 / 智能体 / 视觉 / 基建 / 研究 / 工具）分类成情报卡。
- **航海日志（历史归档）**：按月回溯历史情报，支持按疆域筛选。

当前状态（见 `web/src/views/WorldMap.vue` + `web/src/api/intel.ts`）：**前端已完成、数据全为 Mock**，三个数据函数 `listTodayIntel()` / `listArchive(region?)` / `getIntelStats()` 直接返回硬编码 Promise。README 也标注「世界地图（前端 + Mock，后端待接入）」。

后端（`server/app`，FastAPI + SQLAlchemy 2.0 async + SQLite）目前没有任何 AI / 联网 / 定时任务能力。

本次要做的事：**在后端接入 Claude Agent SDK，让一个 Agent 每天定时拿到真实 AI 资讯，归纳成结构化文章入库，供前端无缝替换 Mock。**

### 已确认的关键决策

| 维度 | 决策 | 说明 |
|------|------|------|
| **运行 Provider** | ✅ GLM（复用当前环境配置） | Agent SDK 子进程继承 `ANTHROPIC_BASE_URL=open.bigmodel.cn/api/anthropic` + GLM token + `glm-5.2`。**不用** Anthropic 官方 Key |
| **内容来源** | ✅ 后端自定义工具抓 RSS | 标准 WebSearch/WebFetch 在 GLM 不可用（见 §3），改由后端 in-process MCP 工具拉 RSS 源 + 抓正文，Agent 只做归纳 |
| **触发方式** | ✅ 定时任务·每日生成 | APScheduler，每天 07:00 后台跑一次，文章提前就绪 |
| **数据范围** | ✅ 全局共享 | AI 新闻是公共信息，全局每天只生成一次；`intel_articles` 表无 `user_id` |

### 非目标（本次不做）

- 不做每用户个性化资讯流；不做资讯的评论 / 点赞 / 收藏。
- 不引入消息队列（Celery / Redis）——单进程 APScheduler 足够每日一次。
- 不依赖 Anthropic 官方端点或其服务端工具（WebSearch 等）。

---

## 2. 技术选型

| 项 | 选型 | 理由 |
|----|------|------|
| **AI SDK** | [`claude-agent-sdk`](https://pypi.org/project/claude-agent-sdk/) 0.2.116（Python） | Claude Code 官方 Python SDK，自带 Agent 循环、上下文管理。旧的 `claude-code-sdk` 已废弃。Python 3.10+，打包原生二进制，**无需 Node.js**。 |
| **Provider** | GLM via `open.bigmodel.cn/api/anthropic` | 复用当前已验证可用的环境；SDK 子进程继承 `ANTHROPIC_*` 环境变量即连。 |
| **联网能力** | **后端自定义 in-process MCP 工具**（`@tool` + `create_sdk_mcp_server`） | 标准 WebSearch/WebFetch 在 GLM 不可用（见 §3）。改由 Python 工具拉 RSS + 抓页面，provider 无关、完全可控。 |
| **结构化输出** | SDK 内置 `output_format` + Pydantic JSON Schema | **已在 GLM 实测可用**（见 §3 T4）。结果落在 `ResultMessage.structured_output`，无需自己 parse。 |
| **调度** | [`APScheduler`](https://apscheduler.readthedocs.io/) `AsyncIOScheduler` | 纯 Python、原生 async，与 FastAPI lifespan 契合；每日一次无需 Celery。 |
| **RSS 解析** | [`feedparser`](https://feedparser.readthedocs.io/) | Python RSS/Atom 解析事实标准。 |
| **正文抓取** | `httpx` + [`html2text`](https://github.com/Alir3z4/html2text) | 自定义 `fetch_page` 工具用，把 HTML 转干净文本喂给 Agent（替代 WebFetch）。 |
| **存储** | SQLite（沿用 `data.db`） | 低频写入（每天 1 次），`create_all` 自动建表，零迁移。 |

### 为什么用 Agent SDK 而不是裸 GLM Chat API？

「拿到一批资讯 → 归类到 6 疆域 → 写中文摘要正文 → 结构化输出」是个**多步、带工具调用、需要结构化约束**的任务。裸 Chat API 要自己实现工具循环、JSON 校验重试、上下文裁剪；Agent SDK 的 `query()` 一行起 Agent 循环，配合 `output_format` 自动校验重试，且 in-process MCP 工具让「联网」完全收敛在后端代码里。

---

## 3. GLM 环境兼容性实测结论（冒烟测试）

在动手前，已用 `claude-agent-sdk` 0.2.116 在**真实 GLM 环境**（继承当前 `ANTHROPIC_*`）跑过冒烟测试，逐项验证：

| 能力 | 实测结果 | 结论 |
|------|:--:|------|
| 基础 `query` 生成 | ✅ `subtype=success` | Agent SDK 通过 GLM 跑通 |
| **`output_format` 结构化输出** | ✅ `structured=True`（轨迹含 `ToolUseBlock`，SDK 用「强制工具调用」实现，GLM 支持 tool use） | **结构化输出可直接用，无需降级为手写 JSON 解析** |
| **自定义 in-process MCP 工具** | ✅ 被 Agent 调用（`mcp__intel__get_latest_news`）且数据正确回传 | **RSS 发现工具这条路完全可行** |
| 标准 `WebFetch` | ❌ Agent 明确回复「我没有 WebFetch」 | 不可用 → 用自定义 `fetch_page` 工具替代 |
| 标准 `WebSearch` | ❌ 服务端工具，GLM 未实现（官方文档 `feature-availability` 确认） | 不可用 → 用 RSS 自定义工具替代 |
| Z.ai 内置 `web_reader` MCP | ⚠️ 可用，但属发行包附带（`~/.claude.json` / `.mcp.json` 均无配置） | **不可依赖，方案中忽略** |

**核心启示**：把「发现 + 抓取」从 Agent 内置工具里拿出来，交给**后端自定义 MCP 工具**，跑在 GLM 上的只剩「纯生成 + tool use + 结构化输出」——这三项全部实测可用。这是本方案能在 GLM 上成立的根基。

> 自定义工具的两个实现要点（实测所得，写进代码即可）：
> 1. 用 `@tool(name, description, input_schema)` + `create_sdk_mcp_server(name, tools=[...])` + `ClaudeAgentOptions(mcp_servers={"intel": server}, allowed_tools=["search_ai_news"])` 注册。
> 2. 工具 handler 返回值必须是 MCP 内容块：`return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}]}`（返回裸 dict 会被判为「no output」）。

---

## 4. 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI (server/app)                      │
│                                                               │
│   lifespan 启动                                               │
│   ├── create_all()  ← intel_articles 表自动建                 │
│   └── AsyncIOScheduler.start()                                │
│              │  cron 07:00 (Asia/Shanghai)                    │
│              ▼                                                │
│   ┌─────────────────────────────────────────────┐             │
│   │  services/intel_agent.py                    │  ← claude-agent-sdk → GLM
│   │  fetch_ai_intel()                           │             │
│   │   Agent 拿到两个 in-process MCP 工具:        │             │
│   │   ├─ search_ai_news(limit)  发现(RSS)        │  后端 Python │
│   │   └─ fetch_page(url)        抓正文(html2text)│  后端 Python │
│   │   → 归类 6 疆域 + 写中文摘要正文             │             │
│   │   → output_format 结构化输出 ArticleDraft[]  │             │
│   └───────────────┬─────────────────────────────┘             │
│                   ▼                                           │
│   ┌─────────────────────────────────────────────┐             │
│   │  services/intel.py · generate_daily_intel()  │             │
│   │   ArticleDraft → IntelArticle，published_at=今日，入库 │    │
│   └───────────────┬─────────────────────────────┘             │
│                   ▼                                           │
│   ┌─────────────────────────────────────────────┐             │
│   │  SQLite: intel_articles (全局，无 user_id)   │             │
│   └───────────────┬─────────────────────────────┘             │
│                   ▲                                           │
│   ┌───────────────┴─────────────────────────────┐             │
│   │  routers/intel.py  (REST)                   │             │
│   │   GET  /api/intel/today                     │             │
│   │   GET  /api/intel/archive?region=           │             │
│   │   GET  /api/intel/stats                     │             │
│   │   POST /api/intel/generate (手动/补跑)       │             │
│   └───────────────┬─────────────────────────────┘             │
└───────────────────┼──────────────────────────────────────────┘
                    │  ofetch (替换现有 Mock)
                    ▼
            web/src/api/intel.ts  →  /api/intel/*
            web/src/views/WorldMap.vue（不改）
```

**数据流要点**
1. **写入路径**（每日一次）：Scheduler → Agent（带两个后端工具）→ DB。
2. **读取路径**（用户打开世界地图）：纯 DB 查询，**不触发 Agent**，毫秒级返回。Agent 的延迟被调度器吸收。
3. **失败隔离**：Agent 失败不影响读取——今日为空就返回空，前端已有空态。
4. **GLM 隔离**：所有联网都在后端 Python 工具里；GLM 只负责生成，不碰任何内置联网工具。

---

## 5. 数据模型

新增 `IntelArticle`（全局表，**无 `user_id`**）。字段对齐前端 `web/src/types/intel.ts` 的 `Article` 接口。

```
IntelArticle（AI 资讯文章）
├── id              INTEGER PK autoincrement
├── region          VARCHAR(16)   疆域 slug: llm/agent/vision/infra/research/tools（索引）
├── title           VARCHAR(200)  标题（中文）
├── summary         VARCHAR(500)  一句话摘要（中文）
├── body            TEXT          正文 2–4 段（中文，换行用 \n）
├── source          VARCHAR(200)  来源名（如 "Anthropic" / "机器之心"）
├── url             VARCHAR(500)  原文外链（可空）
├── read_time       VARCHAR(16)   阅读时长展示串（如 "8 min"）
├── published_at    DATE          推送日期 YYYY-MM-DD（= 生成当天，索引）
└── created_at      DATETIME      入库时间
```

**字段映射（DB ↔ 前端 Article）**：`readTime↔read_time`、`publishedAt↔published_at` 做 snake↔camel 转换（schema 层），其余同名。

**设计说明**
- `published_at` 存**推送日（生成当天）**而非原文真实发布日——契合「每日批次」语义，前端按月分组归档以此为准。
- `region` 与 `published_at` 加索引（archive 按疆域筛选、按月分组是高频查询）。
- 不做软删除；如需清理加一个保留天数（如 90 天）的定时清理。

---

## 6. Agent 设计（核心）

### 6.1 两个后端自定义工具（替代 WebSearch / WebFetch）

**工具 1 · `search_ai_news`（发现）**——拉后端维护的 RSS 源列表：

```python
# services/intel_sources.py —— RSS 源维护 + 抓取
import feedparser, asyncio
from itertools import islice

# AI 资讯 RSS 源（中英混合，按需增删）。key=默认疆域倾向（仅提示，最终由 Agent 判定）
RSS_SOURCES: list[dict] = [
    {"name": "Hacker News",       "url": "https://news.ycombinator.com/rss"},
    {"name": "arXiv cs.AI",       "url": "http://export.arxiv.org/rss/cs.AI"},
    {"name": "arXiv cs.CL",       "url": "http://export.arxiv.org/rss/cs.CL"},
    {"name": "Anthropic News",    "url": "https://www.anthropic.com/news/rss.xml"},
    {"name": "OpenAI Blog",       "url": "https://openai.com/blog/rss.xml"},
    {"name": "Google Research",   "url": "https://research.google/blog/rss/"},
    {"name": "机器之心",           "url": "https://www.jiqizhixin.com/rss"},
    {"name": "量子位",             "url": "https://www.qbitai.com/feed"},
    # ... 按需补充：DeepMind、The Batch、TechCrunch AI、VentureBeat AI 等
]

def _parse_one(src: dict, per_feed: int) -> list[dict]:
    try:
        feed = feedparser.parse(src["url"])
    except Exception:
        return []
    items = []
    for e in islice(feed.entries, per_feed):
        items.append({
            "title": getattr(e, "title", ""),
            "url": getattr(e, "link", ""),
            "source": src["name"],
            "snippet": (getattr(e, "summary", "") or "")[:300],
        })
    return items

async def fetch_rss_items(limit: int = 40) -> list[dict]:
    per_feed = max(3, limit // max(1, len(RSS_SOURCES)) + 2)
    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(
        None, lambda: [it for s in RSS_SOURCES for it in _parse_one(s, per_feed)]
    )
    # 按 url 去重，截断到 limit
    seen, out = set(), []
    for it in results:
        if it["url"] and it["url"] not in seen:
            seen.add(it["url"]); out.append(it)
        if len(out) >= limit:
            break
    return out
```

**工具 2 · `fetch_page`（抓正文）**——替代 WebFetch，把指定 URL 转 clean text：

```python
# services/intel_sources.py（续）
import httpx, html2text

async def fetch_page_text(url: str, max_chars: int = 4000) -> str:
    con = httpx.AsyncClient(timeout=15, follow_redirects=True,
                            headers={"User-Agent": "PixelPackIntelBot/1.0"})
    try:
        r = await con.get(url)
        r.raise_for_status()
    except Exception as e:
        return f"[fetch failed: {e}]"
    finally:
        await con.aclose()
    md = html2text.html2text(r.text)
    return md[:max_chars]
```

**注册成 in-process MCP 工具**（实测可用的 API）：

```python
# services/intel_agent.py
import json
from claude_agent_sdk import tool, create_sdk_mcp_server
from app.services.intel_sources import fetch_rss_items, fetch_page_text

@tool(
    name="search_ai_news",
    description="返回最近 N 条 AI 资讯候选(标题/链接/来源/摘要)，来自后端维护的 RSS 源。limit=条数(默认40)。",
    input_schema={"limit": int},
)
async def search_ai_news(args):
    limit = int(args.get("limit", 40)) if isinstance(args, dict) else 40
    items = await fetch_rss_items(limit=limit)
    return {"content": [{"type": "text", "text": json.dumps({"items": items}, ensure_ascii=False)}]}

@tool(
    name="fetch_page",
    description="抓取指定 URL 的网页正文(转 Markdown 文本)，用于阅读详情。url=网址。",
    input_schema={"url": str},
)
async def fetch_page(args):
    url = args.get("url", "") if isinstance(args, dict) else ""
    text = await fetch_page_text(url)
    return {"content": [{"type": "text", "text": text}]}

INTEL_SERVER = create_sdk_mcp_server(name="intel", version="1.0.0",
                                     tools=[search_ai_news, fetch_page])
```

### 6.2 结构化输出 Schema（实测可用，无需降级）

```python
from typing import Literal
from pydantic import BaseModel, Field

Region = Literal["llm", "agent", "vision", "infra", "research", "tools"]

class ArticleDraft(BaseModel):
    region: Region = Field(..., description="知识疆域 slug")
    title: str = Field(..., max_length=200, description="中文标题")
    summary: str = Field(..., max_length=200, description="一句话中文摘要")
    body: str = Field(..., description="2-4 段中文正文，段间用 \\n 分隔")
    source: str = Field(..., max_length=100, description="来源名")
    url: str | None = Field(None, description="原文外链")
    read_time: str = Field(..., description='阅读时长展示串，如 "8 min"')

class IntelBatch(BaseModel):
    articles: list[ArticleDraft] = Field(..., description="今日情报，建议 4-6 篇，尽量覆盖不同疆域")
```

### 6.3 Options 与 Prompt

```python
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from app.config import settings

def build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        mcp_servers={"intel": INTEL_SERVER},
        allowed_tools=["search_ai_news", "fetch_page"],
        permission_mode="bypassPermissions",
        max_turns=settings.INTEL_MAX_TURNS,        # ~12
        max_budget_usd=settings.INTEL_MAX_BUDGET,  # ~0.5（GLM 侧计费，仅作软上限）
        output_format={"type": "json_schema", "schema": IntelBatch.model_json_schema()},
    )

SYSTEM_PROMPT = """你是 PixelPack 的 AI 技术情报分析师。任务：把当天的 AI 动态归纳成结构化情报。
流程：
1. 先调用 search_ai_news(limit=40) 拿到候选条目（标题/链接/来源/摘要）。
2. 挑选 4-6 条最有价值的，尽量覆盖不同疆域。对拿不准详情的条目，可用 fetch_page(url) 读原文。
3. 每条输出：中文标题、中文一句话摘要、2-4 段中文正文、来源名、原文 URL、阅读时长。
4. 内容必须基于工具返回的真实条目，不得虚构；URL 用工具返回的真实链接。
5. published_at 由系统填充，你无需输出日期。"""

def build_prompt(today: str, weekday: str) -> str:
    return (f"今天是 {today}（{weekday}）。请检索归纳最近 1-2 天的 AI 资讯。\n"
            f"疆域定义：llm=大模型, agent=智能体, vision=视觉, "
            f"infra=基建, research=研究, tools=工具。")
```

> **为什么不限制 Agent 用 `disallowed_tools` 硬拒绝 Bash/Write**：GLM 环境下标准工具本就只剩 Read/Edit/Write/Bash/WebFetch/WebSearch 等内置项，而 WebSearch/WebFetch 已不可用；这里 `mcp_servers` 只注入两个自建工具，`allowed_tools` 仅放行这两个，`permission_mode=bypassPermissions` 免确认。Agent 没有路径去碰文件系统（任务也不需要）。如要额外保险，可加 `disallowed_tools=["Bash","Write","Edit"]`。

### 6.4 调用与解析

```python
async def fetch_ai_intel() -> list[ArticleDraft]:
    result_msg: ResultMessage | None = None
    async for msg in query(prompt=build_prompt(*today_str_weekday()), options=build_options()):
        if isinstance(msg, ResultMessage):
            result_msg = msg
            logger.info("intel agent: subtype=%s turns=%s", msg.subtype, getattr(msg, "num_turns", None))
    if result_msg is None:
        raise RuntimeError("Agent 未返回结果")
    if result_msg.subtype != "success" or not result_msg.structured_output:
        raise RuntimeError(f"Agent 失败: {result_msg.subtype}")
    return IntelBatch.model_validate(result_msg.structured_output).articles
```

### 6.5 成本与延迟预期
- **延迟**：一次 search_ai_news（RSS 并发拉取）+ 若干 fetch_page + 归纳，通常 4–8 轮，**约 20–60s**。故必须放定时任务，绝不进请求路径。
- **成本**：RSS 抓取在后端（免费）；GLM 只计生成 + tool use token。每天 1 次，月成本极低。

---

## 7. 定时任务与调度

在 `server/app/main.py` 的 `lifespan` 里启动调度器：

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.intel import scheduled_generate_intel

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if settings.INTEL_ENABLED:
        scheduler = AsyncIOScheduler(timezone=settings.INTEL_TZ)
        scheduler.add_job(
            scheduled_generate_intel,
            CronTrigger(hour=settings.INTEL_CRON_HOUR, minute=settings.INTEL_CRON_MINUTE),
            id="intel_daily", coalesce=True, max_instances=1, misfire_grace_time=3600,
        )
        scheduler.start()
    try:
        yield
    finally:
        if settings.INTEL_ENABLED:
            scheduler.shutdown(wait=False)
```

调度任务自建 session（脱离请求上下文），失败只记日志不抛穿：

```python
async def scheduled_generate_intel() -> None:
    from app.database import async_session_factory
    try:
        drafts = await fetch_ai_intel()
        async with async_session_factory() as db:
            await store_daily_intel(db, drafts)   # 今日已有则跳过
            await db.commit()
        logger.info("intel generated: %d articles", len(drafts))
    except Exception:
        logger.exception("daily intel generation failed")
```

**关键细节**
- `max_instances=1` + `coalesce=True`：绝不并发跑两个 Agent 子进程。
- **去重**：入库前查今日是否已有，有则跳过；`POST /api/intel/generate` 可强制覆盖。
- **失败不抛穿**：catch 住，明天照常再试。

---

## 8. API 设计

完全对齐前端现有三个函数的调用契约，前端只换实现不改逻辑。

```
AI 资讯
  GET    /api/intel/today              今日推送（信号台）   → list[ArticleResponse]
  GET    /api/intel/archive            历史归档（航海日志）
    ?region=  ?limit=20                → list[ArticleResponse]   按 published_at desc
  GET    /api/intel/stats              顶部统计 → IntelStatsResponse
  POST   /api/intel/generate           手动触发生成（开发/补跑，asyncio.Lock 防并发）
```

**鉴权**：全部走 `Depends(get_current_user)`。

**响应 Schema**（`schemas/intel.py`，camelCase 与前端 `Article` 严格一致）：

```python
class ArticleResponse(BaseModel):
    id: int
    region: str
    title: str
    summary: str
    body: str
    source: str
    readTime: str | None
    url: str | None = None
    publishedAt: str

class IntelStatsResponse(BaseModel):
    todayCount: int
    weekCount: int       # 最近 7 天
    archivedCount: int   # 全表总数
    unreadCount: int     # = todayCount（前端「今日即未读」视觉）
```

---

## 9. 配置项

`server/app/config.py` 增补。**GLM 凭证继承部署环境变量**，可不写进 `.env`（避免泄密）；也可显式落 `.env`：

```python
class Settings(BaseSettings):
    # ... 现有字段 ...

    # ── Claude Agent SDK / GLM（继承环境变量；此处仅声明默认，便于本地覆盖）──
    # ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN / ANTHROPIC_MODEL 由部署环境注入，
    # Agent SDK 子进程自动继承，无需在代码里显式传递。

    INTEL_MODEL: str = "glm-5.2"                 # 仅记录用，实际 model 走环境变量
    INTEL_MAX_TURNS: int = 12
    INTEL_MAX_BUDGET: float = 0.5

    # ── 调度 ──
    INTEL_TZ: str = "Asia/Shanghai"
    INTEL_CRON_HOUR: int = 7
    INTEL_CRON_MINUTE: int = 0
    INTEL_ENABLED: bool = True
```

`server/.env`（可选，gitignore 已忽略）：

```env
# GLM 凭证（若不在部署环境注入，则在此显式写）
ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic
ANTHROPIC_AUTH_TOKEN=<your_glm_token>
ANTHROPIC_MODEL=glm-5.2
INTEL_CRON_HOUR=7
INTEL_CRON_MINUTE=0
```

**RSS 源列表**维护在代码 `services/intel_sources.py` 的 `RSS_SOURCES`（见 §6.1），按需增删，无需重启配置。

---

## 10. 前端改造（极小）

前端**类型与页面零改动**，只把 Mock 换成真实 ofetch 调用。`web/src/api/intel.ts` 重写：

```typescript
import { api } from './client'              // 复用现有 ofetch 实例（带 JWT）
import type { Article, IntelStats, RegionSlug } from '../types/intel'

export function listTodayIntel(): Promise<Article[]> {
  return api('/intel/today')
}
export function listArchive(region?: RegionSlug | null): Promise<Article[]> {
  return api('/intel/archive', { params: region ? { region } : {} })
}
export function getIntelStats(): Promise<IntelStats> {
  return api('/intel/stats')
}
```

`WorldMap.vue` 不动——三个函数签名没变，替换透明。`types/intel.ts` 的 `REGIONS` 常量也不动。

---

## 11. 项目结构变更

```
server/
├── app/
│   ├── main.py                # 改：lifespan 接入 APScheduler
│   ├── config.py              # 改：增补 INTEL_* 配置
│   ├── models/
│   │   ├── __init__.py        # 改：导出 IntelArticle
│   │   └── intel.py           # 新增：IntelArticle
│   ├── schemas/
│   │   └── intel.py           # 新增：ArticleResponse / IntelStatsResponse / ArticleDraft / IntelBatch
│   ├── services/
│   │   ├── intel.py           # 新增：list_today / list_archive / get_stats / store_daily_intel / scheduled_generate_intel
│   │   ├── intel_agent.py     # 新增：fetch_ai_intel() + 两个 @tool + MCP server 注册 + prompt
│   │   └── intel_sources.py   # 新增：RSS_SOURCES 列表 + fetch_rss_items + fetch_page_text
│   └── routers/
│       └── intel.py           # 新增：4 个端点
└── requirements.txt           # 改：+ claude-agent-sdk, + apscheduler, + feedparser, + html2text
```

**依赖新增**（`server/requirements.txt`）：

```
claude-agent-sdk
apscheduler
feedparser
html2text
```

---

## 12. 实施计划（分阶段）

### Phase 1 · 数据层与 API 骨架（先通读取，不碰 GLM）
1. `models/intel.py` + 注册（`create_all` 自动建表）。
2. `schemas/intel.py` 响应模型。
3. `services/intel.py`：`list_today` / `list_archive` / `get_stats`（纯查询）。
4. `routers/intel.py`：3 个 GET 端点，注册到 `main.py`。
5. 前端 `api/intel.ts` 切真实调用。
6. 手插几条测试数据，验证前端世界地图三处渲染。

### Phase 2 · 资讯抓取（后端工具 + Agent，走 GLM）
7. `services/intel_sources.py`：`RSS_SOURCES` + `fetch_rss_items` + `fetch_page_text`。
8. `services/intel_agent.py`：两个 `@tool` + `create_sdk_mcp_server` + `fetch_ai_intel()`。
9. `services/intel.py` 补 `store_daily_intel()`（今日去重入库）。
10. `POST /api/intel/generate`（asyncio.Lock 防并发）。
11. **复用本次冒烟测试**（`/tmp/intel_smoke*.py` 已验证 T1/T2/T4）→ curl 调 `/api/intel/generate`，端到端验 RSS→Agent→入库→前端展示。

### Phase 3 · 定时调度
12. `config.py` + `requirements.txt` 增补。
13. `main.py` lifespan 接入 APScheduler。
14. cron 临时调近（当前+2 分钟）验证触发，再改回 07:00。

### Phase 4 · 加固
15. 成本/轮次日志（`num_turns`、失败 subtype）。
16. RSS 源健康检查（坏源自动跳过/告警）。
17. 历史保留策略（定时清理 N 天前）。

---

## 13. 风险与注意事项

### ✅ R1 / R2 · GLM 兼容性（已实测解决）
- **认证**：GLM `ANTHROPIC_AUTH_TOKEN` 是 API-key 形式凭证，Agent SDK 接受，**不需要 OAuth、不需要 Anthropic 官方 Key**。
- **连通性**：Agent SDK 子进程继承 GLM 环境变量即连，本会话与冒烟测试双重证实。
- **WebSearch/WebFetch 不可用**：已用后端自定义 MCP 工具（`search_ai_news` + `fetch_page`）完全绕开。
- **结构化输出**：`output_format` 实测可用（`structured=True`），无需降级为手写 JSON 解析。
- 详见 §3 实测结论表。

### 🟠 R3 · RSS 源质量与可达性
- RSS 源偶尔失效/改版。`fetch_rss_items` 已对单源 `try/except` 容错（坏源跳过不影响其它）。需在 Phase 4 定期巡检源列表，必要时补充（中英文 AI 媒体 RSS 较多）。
- `fetch_page` 受目标站点反爬影响，失败时返回 `[fetch failed: ...]`，Agent 可基于摘要继续写（降级而非中断）。

### 🟠 R4 · 成本与资源
- Agent 每次拉起 Claude Code 子进程，`max_instances=1` 锁定调度不并发；手动端点用 asyncio.Lock。
- `max_turns` 兜底；建议每次记 `num_turns` 监控。

### 🟡 R5 · 时区
APScheduler 必须显式 `timezone`（默认 UTC），已配 `INTEL_TZ=Asia/Shanghai`。

### 🟡 R6 · SQLite 并发
每日 1 次写入几条，写锁影响可忽略；上量再迁 PostgreSQL（技术栈本就规划 PG）。

### 🟡 R7 · 内容时效性
RSS 给的是「最近条目」，可能跨 1-2 天。prompt 注入「今天日期 + 最近 1-2 天」锚定；如需严格「今日」，可在 `search_ai_news` 里按 entry 的 `published_parsed` 过滤当天。

---

## 14. 验证方式

1. **建表**：启动后端，确认 `intel_articles` 自动创建。
2. **读取链路**：手插数据 → 前端今日/归档/统计三处渲染正确。
3. **冒烟测试（已完成）**：`/tmp/intel_smoke.py` + `/tmp/intel_smoke_t2.py` 在 GLM 下验证了 query / output_format / 自定义工具三项可用、WebFetch/WebSearch 不可用。
4. **Agent 抓取**（Phase 2 关键）：
   ```bash
   curl -X POST http://127.0.0.1:8000/api/intel/generate -H "Authorization: Bearer <token>"
   ```
   预期 20–60s 返回，DB 多出 4–6 条今日文章，`region` 合法、`url` 来自真实 RSS 条目、可点。
5. **结构化输出**：返回文章字段完整、类型正确（schema 校验生效）。
6. **调度**：cron 设为当前+2 分钟重启，到点自动生成；查日志 `intel generated: N articles`。
7. **失败演练**：临时改错 `ANTHROPIC_AUTH_TOKEN`，确认 `/api/intel/generate` 报错而 `/api/intel/today` 仍正常；次日恢复后自动成功。
8. **前端无感切换**：`WorldMap.vue` 不改一行，Mock→真实接口表现一致。

---

## 15. 参考链接

- [Claude Agent SDK · Overview](https://code.claude.com/docs/en/agent-sdk/overview)
- [Claude Agent SDK · Python Reference](https://code.claude.com/docs/en/agent-sdk/python.md)
- [Claude Agent SDK · Structured Outputs](https://code.claude.com/docs/en/agent-sdk/structured-outputs.md)
- [Claude Agent SDK · Custom Tools（`@tool` / `create_sdk_mcp_server`）](https://code.claude.com/docs/en/agent-sdk/custom-tools.md)
- [Claude Agent SDK · MCP](https://code.claude.com/docs/en/agent-sdk/mcp.md)
- [Feature Availability（哪些特性需 Anthropic 后端）](https://code.claude.com/docs/en/feature-availability.md)
- [anthropics/claude-agent-sdk-python (GitHub)](https://github.com/anthropics/claude-agent-sdk-python)
- [APScheduler · Docs](https://apscheduler.readthedocs.io/)
- [feedparser · Docs](https://feedparser.readthedocs.io/)
- GLM Anthropic 兼容端点：`https://open.bigmodel.cn/api/anthropic`
- 旧包迁移：[`claude-code-sdk`（已废弃）](https://pypi.org/project/claude-code-sdk/) → `claude-agent-sdk`
