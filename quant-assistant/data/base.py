"""
数据采集基类 — 统一错误处理、重试、降级逻辑
"""
import time
import functools
from typing import Optional, Any

from utils.logger import log
from utils.cache import cached


class DataFetchError(Exception):
    """数据采集异常"""
    pass


class BaseFetcher:
    """数据采集器基类"""

    name: str = "base"

    def __init__(self):
        self.log = log

    def _safe_fetch(self, func, fallback_func=None, **kwargs):
        """
        安全执行采集，包含重试和降级
        """
        max_retries = 2
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.log.warning(f"[{self.name}] 第{attempt}次重试...")
                    time.sleep(1 * attempt)
                result = func(**kwargs)
                if result is not None and not (isinstance(result, dict) and not result):
                    return result
            except Exception as e:
                last_error = e
                self.log.warning(f"[{self.name}] 采集失败(attempt {attempt+1}): {e}")

        # 主源失败，尝试备用源
        if fallback_func:
            self.log.info(f"[{self.name}] 主源失败，切换到备用源...")
            try:
                result = fallback_func(**kwargs)
                if result is not None:
                    result["_fallback"] = True
                    return result
            except Exception as e:
                self.log.error(f"[{self.name}] 备用源也失败: {e}")

        # 全部失败
        self.log.error(f"[{self.name}] 数据采集完全失败: {last_error}")
        return {"_error": str(last_error), "_source": self.name}

    def _result_template(self, **kwargs) -> dict:
        """生成标准结果模板"""
        return {
            "_source": self.name,
            "_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "_fallback": False,
            "_error": None,
            **kwargs,
        }
