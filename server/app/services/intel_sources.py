"""AI 资讯的内容来源层：RSS 发现 + 网页正文抓取。

这两个能力是给 Agent 用的「后端自定义工具」底层实现——因为标准 WebSearch / WebFetch
在 GLM 环境下不可用（见技术方案 §3），联网收敛在 Python 代码里，provider 无关。
"""
import asyncio
import logging
from itertools import islice

import feedparser
import html2text
import httpx

logger = logging.getLogger(__name__)

_UA = "PixelPackIntelBot/1.0 (+https://github.com/krian/PixelPack)"

# ── RSS / Atom 源（中英混合，按需增删；坏源会自动跳过）──────────────────────
# name 仅作展示与归类提示；最终疆域由 Agent 判定。
RSS_SOURCES: list[dict] = [
    # 综合科技 / AI
    {"name": "Hacker News", "url": "https://news.ycombinator.com/rss"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
    # 论文
    {"name": "arXiv cs.AI", "url": "http://export.arxiv.org/rss/cs.AI"},
    {"name": "arXiv cs.CL", "url": "http://export.arxiv.org/rss/cs.CL"},
    {"name": "arXiv cs.LG", "url": "http://export.arxiv.org/rss/cs.LG"},
    {"name": "arXiv cs.CV", "url": "http://export.arxiv.org/rss/cs.CV"},
    # 厂商博客
    {"name": "Anthropic News", "url": "https://www.anthropic.com/news/rss.xml"},
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml"},
    {"name": "Google Research", "url": "https://research.google/blog/rss/"},
    # 中文 AI 媒体
    {"name": "机器之心", "url": "https://www.jiqizhixin.com/rss"},
    {"name": "量子位", "url": "https://www.qbitai.com/feed"},
]


async def fetch_rss_items(limit: int = 40) -> list[dict]:
    """并发拉取所有 RSS 源，返回去重后的候选条目。

    每条：{title, url, source, snippet}。单源失败不影响其它。
    """
    sources = RSS_SOURCES
    per_feed = max(3, limit // max(1, len(sources)) + 2)

    async with httpx.AsyncClient(
        timeout=15, follow_redirects=True, headers={"User-Agent": _UA}
    ) as client:
        responses = await asyncio.gather(
            *[client.get(s["url"]) for s in sources], return_exceptions=True
        )

    out: list[dict] = []
    for src, resp in zip(sources, responses):
        if isinstance(resp, Exception):
            logger.debug("rss source failed: %s (%s)", src["name"], resp)
            continue
        if resp.status_code != 200:
            logger.debug("rss source %s status %s", src["name"], resp.status_code)
            continue
        try:
            feed = feedparser.parse(resp.content)
        except Exception as e:  # noqa: BLE001
            logger.debug("rss parse failed %s: %s", src["name"], e)
            continue
        for entry in islice(feed.entries, per_feed):
            url = getattr(entry, "link", "") or ""
            title = getattr(entry, "title", "") or ""
            if not url or not title:
                continue
            snippet = (getattr(entry, "summary", "") or "").strip()
            # 去掉 HTML 标签的简单处理
            if "<" in snippet:
                import re
                snippet = re.sub(r"<[^>]+>", "", snippet)
            out.append({
                "title": title[:200],
                "url": url[:500],
                "source": src["name"],
                "snippet": snippet[:300],
            })

    # 按 url 去重
    seen: set[str] = set()
    deduped: list[dict] = []
    for it in out:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        deduped.append(it)
        if len(deduped) >= limit:
            break
    logger.info("rss fetched %d items from %d sources", len(deduped), len(sources))
    return deduped


async def fetch_page_text(url: str, max_chars: int = 4000) -> str:
    """抓取单个 URL，HTML 转 Markdown 文本（替代 WebFetch）。失败返回错误串。"""
    async with httpx.AsyncClient(
        timeout=15, follow_redirects=True, headers={"User-Agent": _UA}
    ) as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
        except Exception as e:  # noqa: BLE001
            return f"[fetch failed: {type(e).__name__}: {e}]"
    try:
        md = html2text.html2text(r.text)
    except Exception as e:  # noqa: BLE001
        return f"[convert failed: {e}]"
    return md[:max_chars]
