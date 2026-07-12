"""任务规划 Agent：用 claude-agent-sdk 跑 GLM，通过 function call 直接把任务写入数据库。

复用 intel 模块已验证的 SDK 模式：
- 字符串 prompt（GLM 可用）+ system_prompt。
- in-process MCP 工具（@tool + create_sdk_mcp_server），工具返回 MCP 内容块。
- 工具 handler 按请求绑定 user_id（per-request 工厂），不把 user_id 暴露给模型。

对外暴露 run_agent(user_id, prompt) 异步生成器，逐条 yield 事件 dict：
  {type: delta|tool|task_created|done|error, ...}
"""
import json
import logging
import os
from collections.abc import AsyncGenerator

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

from app.config import settings
from app.database import async_session_factory
from app.schemas.task import TaskCreate
from app.services import task as task_svc

logger = logging.getLogger(__name__)

# 把 .env/Settings 的 GLM 配置注入 os.environ，确保 Agent SDK 子进程继承（同 intel）
for _k in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL"):
    _v = getattr(settings, _k, None)
    if _v and not os.environ.get(_k):
        os.environ[_k] = _v


SYSTEM_PROMPT = """你是 PixelPack 的每日任务规划助手「NEXA」。用户用自然语言描述今天的学习 / 工作 / 生活计划，\
你要把它拆解成 3-8 个具体、可执行、可勾选的今日任务，并通过工具直接写入用户清单。

规则：
1. 先调用 list_today_tasks 查看用户今日已有任务，避免重复创建。
2. 对每个拆解出的任务，调用 create_task 写入数据库（不要只口头列举）。
3. 经验按难度：简单 10、中等 20、困难 30。
4. category 从 study(学习)/work(工作)/life(生活)/health(健康)/other(其他) 中选最贴切的。
5. title 用动宾短语、可执行（如「读完高数第 3 章并整理 3 条笔记」，不要只写「学习」）。
6. 多步任务用 target 表示步数（如「做 3 道题」target=3）。
7. 全部创建后，用一段简洁的中文总结：今天排了哪些任务、总经验、建议从哪一项开始。

注意：任务是否已写入以工具返回结果为准；不要虚构结果。
"""


def _build_tools(user_id: int, created: list[dict]):
    """per-request 构造 MCP 工具，闭包绑定 user_id。返回 MCP server。"""

    @tool(
        name="list_today_tasks",
        description="返回当前用户今日已有任务清单（标题/分类/是否完成/目标/进度），用于避免重复创建。",
        input_schema={"type": "object", "properties": {}, "required": []},
    )
    async def list_today_tasks(args):  # noqa: ANN001
        async with async_session_factory() as db:
            tasks = await task_svc.list_tasks(db, user_id)
            data = [
                {
                    "title": t.title,
                    "category": t.category,
                    "completed": t.completed,
                    "target": t.target,
                    "progress": t.progress,
                }
                for t in tasks
            ]
        return {"content": [{"type": "text", "text": json.dumps({"today_tasks": data}, ensure_ascii=False)}]}

    @tool(
        name="create_task",
        description=(
            "为用户今日清单创建一个任务并立即写入数据库。"
            "title 必填（简洁可执行）；category: study/work/life/health/other；"
            "target 目标步数默认 1；exp_reward 经验默认按难度；due_date 可选默认今天。"
        ),
        input_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "category": {"type": "string"},
                "target": {"type": "integer"},
                "exp_reward": {"type": "integer"},
                "due_date": {"type": "string"},
            },
            "required": ["title"],
        },
    )
    async def create_task(args):  # noqa: ANN001
        a = args if isinstance(args, dict) else {}
        title = (a.get("title") or "").strip()
        if not title:
            return {"content": [{"type": "text", "text": json.dumps({"error": "title required"}, ensure_ascii=False)}]}
        try:
            tc = TaskCreate(
                title=title[:120],
                description=a.get("description"),
                category=(a.get("category") or "study"),
                target=int(a.get("target", 1) or 1),
                exp_reward=a.get("exp_reward"),
                due_date=a.get("due_date"),
            )
        except Exception as e:  # pydantic 校验失败
            logger.warning("[tool·create_task] invalid input: %s", e)
            return {"content": [{"type": "text", "text": json.dumps({"error": str(e)}, ensure_ascii=False)}]}

        try:
            async with async_session_factory() as db:
                t = await task_svc.create_task(db, user_id, tc, source="ai")
                await db.commit()
                created.append({
                    "id": t.id, "title": t.title, "category": t.category,
                    "exp_reward": t.exp_reward, "target": t.target,
                })
            logger.info("[tool·create_task] -> id=%s title=%s", t.id, t.title)
            return {"content": [{"type": "text", "text": json.dumps({"id": t.id, "title": t.title}, ensure_ascii=False)}]}
        except Exception as e:
            logger.exception("[tool·create_task] failed")
            return {"content": [{"type": "text", "text": json.dumps({"error": str(e)}, ensure_ascii=False)}]}

    return create_sdk_mcp_server(
        name="taskkit", version="1.0.0", tools=[list_today_tasks, create_task],
    )


def _build_options(server) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"taskkit": server},
        allowed_tools=["list_today_tasks", "create_task"],
        permission_mode="bypassPermissions",
        max_turns=settings.TASK_AGENT_MAX_TURNS,
    )


async def run_agent(user_id: int, prompt: str) -> AsyncGenerator[dict, None]:
    """跑一次任务规划 Agent，流式 yield 事件 dict。

    prompt 为拼接好的对话历史字符串（见 chat.history_prompt）。
    """
    created: list[dict] = []
    server = _build_tools(user_id, created)
    options = _build_options(server)

    logger.info("[task-agent] start user=%s turns=%s", user_id, settings.TASK_AGENT_MAX_TURNS)
    full_text: list[str] = []
    seen_created = 0
    result_subtype = "unknown"

    try:
        async for msg in query(prompt=prompt, options=options):
            if isinstance(msg, AssistantMessage):
                for block in getattr(msg, "content", []) or []:
                    if isinstance(block, TextBlock) and block.text:
                        full_text.append(block.text)
                        yield {"type": "delta", "text": block.text}
                    elif isinstance(block, ToolUseBlock):
                        yield {"type": "tool", "name": block.name}
            # 工具 handler 在两条消息之间执行；这里把新创建的任务即时推送出去
            while len(created) > seen_created:
                yield {"type": "task_created", "task": created[seen_created]}
                seen_created += 1
            if isinstance(msg, ResultMessage):
                result_subtype = msg.subtype or "unknown"
                logger.info("[task-agent] done subtype=%s turns=%s", result_subtype, getattr(msg, "num_turns", None))
    except Exception as e:
        logger.exception("[task-agent] run failed")
        yield {"type": "error", "message": f"agent 运行失败: {e}"}

    yield {"type": "done", "text": "".join(full_text), "subtype": result_subtype,
           "tasks_created": len(created)}
