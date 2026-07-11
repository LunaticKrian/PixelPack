from typing import Literal

from pydantic import BaseModel, Field

Region = Literal["llm", "agent", "vision", "infra", "research", "tools"]


# ── Agent 结构化输出（claude-agent-sdk output_format 用）─────────────────
class ArticleDraft(BaseModel):
    region: Region = Field(..., description="知识疆域 slug: llm/agent/vision/infra/research/tools")
    title: str = Field(..., max_length=200, description="中文标题")
    summary: str = Field(..., max_length=300, description="一句话中文摘要")
    body: str = Field(..., description="2-4 段中文正文，段间用 \\n 分隔")
    source: str = Field(..., max_length=100, description="来源名")
    url: str | None = Field(None, description="原文外链，无则留空")
    read_time: str = Field("5 min", max_length=16, description='阅读时长展示串，如 "8 min"')


class IntelBatch(BaseModel):
    articles: list[ArticleDraft] = Field(..., description="今日情报，建议 4-6 篇，尽量覆盖不同疆域")


# ── API 响应（camelCase，与前端 Article / IntelStats 严格一致）─────────────
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
    weekCount: int
    archivedCount: int
    unreadCount: int


class ArchivePageResponse(BaseModel):
    """航海日志分页响应（一天一页）。"""
    items: list[ArticleResponse]
    date: str | None  # 当前页日期 ISO (YYYY-MM-DD)，空结果时为 None
    page: int  # 第几页（= 第几天，1 起）
    totalPages: int  # 总天数
    total: int  # 当前页条数（= len(items)）
    dates: list[str]  # 所有日期 ISO DESC，供前端标注 前一天/后一天
