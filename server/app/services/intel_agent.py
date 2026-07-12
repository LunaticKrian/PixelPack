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
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    create_sdk_mcp_server,
    query,
    tool,
)

from app.config import settings
from app.schemas.intel import ArticleDraft, IntelBatch
from app.services.intel_sources import fetch_page_text, fetch_rss_items

logger = logging.getLogger(__name__)


def _trunc(s: str, limit: int = 2000) -> str:
    """超长文本截断，便于日志可读。"""
    if s is None:
        return ""
    s = str(s)
    return s if len(s) <= limit else f"{s[:limit]}…<+{len(s) - limit} chars>"

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
            "limit": {
                "type": "integer",
                "default": settings.INTEL_SEARCH_LIMIT,
                "description": f"返回条数，默认 {settings.INTEL_SEARCH_LIMIT}",
            },
        },
        "required": [],
    },
)
async def search_ai_news(args):  # noqa: ANN001
    logger.info("[tool→search_ai_news] 输入 args=%s", args)
    limit = settings.INTEL_SEARCH_LIMIT
    if isinstance(args, dict) and args.get("limit") is not None:
        try:
            limit = int(args["limit"])
        except (TypeError, ValueError):
            limit = settings.INTEL_SEARCH_LIMIT
    items = await fetch_rss_items(limit=max(10, limit))
    logger.info(
        "[tool←search_ai_news] 输出 %d 条候选 | 示例: %s",
        len(items),
        _trunc(", ".join(f"{it.get('source', '')}:{it.get('title', '')}" for it in items[:5])),
    )
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
    logger.info("[tool→fetch_page] 输入 url=%s", url)
    text = await fetch_page_text(url)
    logger.info("[tool←fetch_page] 输出 %d 字符 | 预览: %s", len(text or ""), _trunc((text or "").strip(), 400))
    return {"content": [{"type": "text", "text": text}]}


INTEL_SERVER = create_sdk_mcp_server(
    name="intel", version="1.0.0", tools=[search_ai_news, fetch_page]
)


# ── prompt ────────────────────────────────────────────────────────────
def build_system_prompt() -> str:
    """系统提示。检索条数与产出篇数区间均来自 config，避免魔法值。"""
    return f"""你是 PixelPack 的 AI 技术情报分析师。任务：把当天的 AI 动态归纳成结构化情报卡。

流程：
1. 先调用 search_ai_news(limit={settings.INTEL_SEARCH_LIMIT}) 拿到候选条目（标题/链接/来源/摘要）。
2. 从中挑选 {settings.INTEL_MIN_ARTICLES}-{settings.INTEL_MAX_ARTICLES} 条最有价值、信息量大的，尽量覆盖不同疆域，避免全部集中在一类。
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
        f"输出 {settings.INTEL_MIN_ARTICLES}-{settings.INTEL_MAX_ARTICLES} 篇覆盖不同疆域的情报。\n{_REGIONS_HINT}"
    )


def build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=build_system_prompt(),
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


def _log_stream_message(msg) -> None:
    """把 Agent 流式产生的每条消息按类型打印输入/输出。"""
    if isinstance(msg, AssistantMessage):
        for block in getattr(msg, "content", []) or []:
            if isinstance(block, TextBlock):
                logger.info("[agent→输出·文本] %s", _trunc(block.text))
            elif isinstance(block, ToolUseBlock):
                logger.info(
                    "[agent→调用工具] %s | 输入=%s",
                    block.name, _trunc(json.dumps(block.input, ensure_ascii=False), 1000),
                )
            elif isinstance(block, ThinkingBlock):
                logger.debug("[agent·思考] %s", _trunc(block.thinking))
            else:
                logger.debug("[agent→块] %s", type(block).__name__)
    elif isinstance(msg, UserMessage):
        # UserMessage 通常是工具结果回填给模型
        content = getattr(msg, "content", None)
        if isinstance(content, list):
            for block in content:
                if isinstance(block, ToolResultBlock):
                    txt = block.content
                    if isinstance(txt, list):
                        txt = " ".join(getattr(b, "text", str(b)) for b in txt)
                    logger.info(
                        "[tool→结果回填] is_error=%s | %s",
                        block.is_error, _trunc(str(txt), 600),
                    )
        elif isinstance(content, str) and content:
            logger.info("[user→输入] %s", _trunc(content))
    elif isinstance(msg, ResultMessage):
        logger.info(
            "[agent·结束] subtype=%s stop=%s turns=%s cost=%.4fUSD",
            msg.subtype, msg.stop_reason, getattr(msg, "num_turns", None),
            getattr(msg, "total_cost_usd", 0) or 0,
        )
    else:
        logger.debug("[agent·消息] %s", type(msg).__name__)


async def fetch_ai_intel() -> list[ArticleDraft]:
    """跑一次 Agent，返回结构化情报草稿。失败抛异常交由上层处理。"""
    prompt = build_prompt()
    options = build_options()

    logger.info("=" * 60)
    logger.info("[agent·启动] model=%s base=%s max_turns=%s",
                os.environ.get("ANTHROPIC_MODEL"), os.environ.get("ANTHROPIC_BASE_URL"),
                settings.INTEL_MAX_TURNS)
    logger.info("[agent·系统提示] %s", _trunc(build_system_prompt(), 1200))
    logger.info("[agent·用户输入] %s", prompt)
    logger.info("-" * 60)

    result_msg: ResultMessage | None = None
    async for msg in query(prompt=prompt, options=options):
        _log_stream_message(msg)
        if isinstance(msg, ResultMessage):
            result_msg = msg

    logger.info("-" * 60)
    if result_msg is None:
        logger.error("[agent·失败] 未返回 ResultMessage")
        raise RuntimeError("Agent 未返回结果")

    if result_msg.subtype != "success" or not result_msg.structured_output:
        logger.error("[agent·失败] subtype=%s errors=%s", result_msg.subtype, getattr(result_msg, "errors", None))
        raise RuntimeError(f"Agent 失败: subtype={result_msg.subtype}")

    raw = result_msg.structured_output
    logger.info("[agent·结构化输出] 原始=%s", _trunc(json.dumps(raw, ensure_ascii=False), 1500))
    batch = IntelBatch.model_validate(raw)
    logger.info(
        "[agent·完成] 产出 %d 篇 | %s",
        len(batch.articles),
        " | ".join(f"{a.region}:{_trunc(a.title, 24)}" for a in batch.articles),
    )
    logger.info("=" * 60)
    return batch.articles
