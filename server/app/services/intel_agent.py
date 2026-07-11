"""Agent 层：用 claude-agent-sdk 跑 GLM，把后端抓到的 RSS 资讯归纳成结构化情报。

设计要点（见技术方案 §3、§6）：
- 标准 WebSearch/WebFetch 在 GLM 不可用，改用两个后端 in-process MCP 工具
  （search_ai_news 发现 + fetch_page 抓正文）。
- 结构化输出用 output_format + Pydantic schema（GLM 下实测可用）。
- 工具 handler 返回必须形如 {"content": [{"type":"text","text": ...}]}。
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ResultMessage,
    create_sdk_mcp_server,
    query,
    tool,
)

from app.config import settings
from app.schemas.intel import ArticleDraft, IntelBatch
from app.services.intel_sources import fetch_page_text, fetch_rss_items

logger = logging.getLogger(__name__)

# 把 .env/Settings 里的 GLM 配置注入 os.environ，确保 Agent SDK 拉起的子进程稳定继承
# （pydantic-settings 读 .env 只写 Settings 对象，不写 os.environ）。
for _k in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL"):
    _v = getattr(settings, _k, None)
    if _v and not os.environ.get(_k):
        os.environ[_k] = _v


# ── in-process MCP 工具 ────────────────────────────────────────────────
@tool(
    name="search_ai_news",
    description=(
        "返回最近 N 条 AI 资讯候选条目（来自后端维护的 RSS 源）。"
        "每条含 title/url/source/snippet。用于发现今日有哪些 AI 动态。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "default": 40, "description": "返回条数，默认 40"},
        },
        "required": [],
    },
)
async def search_ai_news(args):  # noqa: ANN001
    limit = 40
    if isinstance(args, dict) and args.get("limit") is not None:
        try:
            limit = int(args["limit"])
        except (TypeError, ValueError):
            limit = 40
    items = await fetch_rss_items(limit=max(10, limit))
    return {"content": [{"type": "text", "text": json.dumps({"items": items}, ensure_ascii=False)}]}


@tool(
    name="fetch_page",
    description=(
        "抓取指定 URL 的网页正文并转成 Markdown 文本，用于阅读资讯详情。"
        "仅在需要补充正文细节时调用，不要对每条都调。"
    ),
    input_schema={
        "type": "object",
        "properties": {"url": {"type": "string", "description": "要抓取的网页地址"}},
        "required": ["url"],
    },
)
async def fetch_page(args):  # noqa: ANN001
    url = (args.get("url", "") if isinstance(args, dict) else "") or ""
    text = await fetch_page_text(url)
    return {"content": [{"type": "text", "text": text}]}


INTEL_SERVER = create_sdk_mcp_server(
    name="intel", version="1.0.0", tools=[search_ai_news, fetch_page]
)


# ── prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """你是 PixelPack 的 AI 技术情报分析师。任务：把当天的 AI 动态归纳成结构化情报卡。

流程：
1. 先调用 search_ai_news(limit=40) 拿到候选条目（标题/链接/来源/摘要）。
2. 从中挑选 4-6 条最有价值、信息量大的，尽量覆盖不同疆域，避免全部集中在一类。
3. 对摘要不足以写正文的条目，可调用 fetch_page(url) 读原文补充细节；不必每条都读。
4. 每条输出：中文标题、中文一句话摘要、2-4 段中文正文、来源名、原文 URL、阅读时长。
5. 内容必须基于工具返回的真实条目，禁止虚构；URL 用工具返回的真实链接。
6. published_at 由系统填充，你无需输出日期。

疆域定义（region 字段取值之一）：
- llm=大模型 / agent=智能体 / vision=视觉 / infra=基建 / research=研究 / tools=工具

正文风格：像资深技术编辑的速读，有观点、有数据、有「为什么重要」，不要水词。
"""

_REGIONS_HINT = "疆域定义：llm=大模型, agent=智能体, vision=视觉, infra=基建, research=研究, tools=工具。"


def _today_str_weekday() -> tuple[str, str]:
    """返回 (今日 YYYY-MM-DD, 中文星期)，按东八区。"""
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    weekday_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]
    return now.strftime("%Y-%m-%d"), weekday_cn


def build_prompt() -> str:
    today, weekday = _today_str_weekday()
    return (
        f"今天是 {today}（{weekday}）。请检索并归纳最近 1-2 天的 AI 资讯，"
        f"输出 4-6 篇覆盖不同疆域的情报。\n{_REGIONS_HINT}"
    )


def build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"intel": INTEL_SERVER},
        allowed_tools=["search_ai_news", "fetch_page"],
        permission_mode="bypassPermissions",
        max_turns=settings.INTEL_MAX_TURNS,
        max_budget_usd=settings.INTEL_MAX_BUDGET,
        output_format={
            "type": "json_schema",
            "schema": IntelBatch.model_json_schema(),
        },
    )


async def fetch_ai_intel() -> list[ArticleDraft]:
    """跑一次 Agent，返回结构化情报草稿。失败抛异常交由上层处理。"""
    result_msg: ResultMessage | None = None
    async for msg in query(prompt=build_prompt(), options=build_options()):
        if isinstance(msg, ResultMessage):
            result_msg = msg
            logger.info(
                "intel agent result: subtype=%s turns=%s",
                msg.subtype, getattr(msg, "num_turns", None),
            )

    if result_msg is None:
        raise RuntimeError("Agent 未返回结果")
    if result_msg.subtype != "success" or not result_msg.structured_output:
        raise RuntimeError(f"Agent 失败: subtype={result_msg.subtype}")

    batch = IntelBatch.model_validate(result_msg.structured_output)
    logger.info("intel agent produced %d drafts", len(batch.articles))
    return batch.articles
