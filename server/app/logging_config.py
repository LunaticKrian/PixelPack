"""统一日志配置。

uvicorn 自带一套 LOGGING_CONFIG，但其默认 root 级别为 WARNING，会让 `app.*` 下的
INFO 级业务日志（尤其是 Agent 交互）静默丢失。这里显式为 `app` logger 挂一个带格式的
StreamHandler 并固定到 INFO，与 uvicorn 解耦，确保业务日志稳定输出到 stderr。
"""
import logging
import os

_FMT = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"
# 与 uvicorn_log_config.json 的 datefmt 对齐，全链路日志时间格式一致
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    level = logging.getLevelName(os.environ.get("APP_LOG_LEVEL", "INFO").upper())

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_FMT, _DATEFMT))

    app_logger = logging.getLogger("app")
    app_logger.setLevel(level)
    if not app_logger.handlers:
        app_logger.addHandler(handler)
    # 不向 root 冒泡，避免与 uvicorn 的 handler 重复输出
    app_logger.propagate = False

    # SDK 内部也有 logger，调到 WARNING 避免刷屏（我们自己在业务层记录 Agent 细节）
    logging.getLogger("claude_agent_sdk").setLevel(logging.WARNING)
