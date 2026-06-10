"""
日志模块
"""
import logging
import sys
from pathlib import Path

from config import LOG_CONFIG


def setup_logger(name: str = "quant") -> logging.Logger:
    """创建日志器"""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_CONFIG.get("level", "INFO")))

    formatter = logging.Formatter(LOG_CONFIG["format"])

    # 文件输出
    log_file = Path(LOG_CONFIG["file"])
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # 控制台输出
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


# 默认日志器
log = setup_logger()
