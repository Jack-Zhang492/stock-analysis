"""
新闻数据采集 — akshare
提供: 个股相关新闻、财经快讯、舆情监控
"""
import time
import hashlib
from typing import Optional

import pandas as pd
import requests

from data.base import BaseFetcher
from utils.logger import log
from utils.cache import cached
from utils.validators import split_code
from config import AKSHARE_CONFIG


# 简单情绪词典
POSITIVE_WORDS = [
    "增长", "盈利", "突破", "签约", "中标", "上调", "增持", "利好",
    "创新", "研发", "扩产", "回购", "分红", "订单", "超预期",
    "净利润", "营业收入", "产能", "国产替代", "政策支持",
    "放量", "涨停", "新高", "龙头", "核心",
]

NEGATIVE_WORDS = [
    "下降", "亏损", "减持", "下调", "利空", "处罚", "违规", "退市",
    "跌停", "新低", "减值", "诉讼", "限售", "解禁", "质押",
    "监管", "问询", "警示", "停产", "诉讼", "暴雷",
    "同比下降", "下滑", "逾期", "违约", "破产",
]


class NewsDataFetcher(BaseFetcher):
    """新闻数据采集器"""

    name = "news"

    @cached("stock_news", "news")
    def get_stock_news(self, stock_code: str, days: int = 30) -> dict:
        """
        获取个股相关新闻
        """
        return self._safe_fetch(
            lambda: self._get_news_akshare(stock_code),
        )

    def _get_news_akshare(self, stock_code: str) -> dict:
        """通过 akshare 获取个股新闻"""
        try:
            import akshare as ak
            _, code = split_code(stock_code)

            df = None
            # 尝试多个接口
            for func_name in ["stock_news_em", "stock_notices_em"]:
                try:
                    func = getattr(ak, func_name, None)
                    if func:
                        df = func(symbol=code)
                        if df is not None and not df.empty:
                            break
                except Exception:
                    continue

            if df is None or df.empty:
                return self._result_template(news=[], count=0, sentiment_score=50)

            news_list = []
            for _, row in df.tail(30).iterrows():
                title = str(row.get("title", "") or row.get("标题", ""))
                content = str(row.get("content", "") or row.get("内容", ""))
                pub_time = str(row.get("pub_time", "") or row.get("发布时间", ""))
                source = str(row.get("source", "") or row.get("来源", ""))

                # 情绪分析
                sentiment = self._analyze_sentiment(title + content)

                news_list.append({
                    "title": title[:100],
                    "content": content[:200] if content else "",
                    "time": pub_time[:19] if pub_time else "",
                    "source": source,
                    "sentiment": sentiment,
                })

            # 计算整体情绪得分
            if news_list:
                avg_sentiment = sum(n["sentiment"] for n in news_list) / len(news_list)
                # 映射到0-100
                sentiment_score = int(50 + avg_sentiment * 50)
            else:
                sentiment_score = 50

            return self._result_template(
                news=news_list,
                count=len(news_list),
                sentiment_score=sentiment_score,
            )

        except Exception as e:
            self.log.error(f"[news] akshare新闻获取失败: {e}")
            return {"_error": str(e), "news": [], "count": 0, "sentiment_score": 50}

    # ================================================================
    # 市场情绪指标
    # ================================================================

    def get_market_sentiment(self) -> dict:
        """获取全市场情绪指标"""

        def fetch():
            try:
                import akshare as ak

                # 涨跌停统计
                limit_df = None
                try:
                    limit_df = ak.stock_zt_pool_em(date=time.strftime("%Y%m%d"))
                except Exception:
                    pass

                up_count = len(limit_df) if limit_df is not None and not limit_df.empty else 0

                # 北向资金
                north_flow = None
                try:
                    north_df = ak.stock_hsgt_north_net_flow_in_em(symbol="北上")
                    if north_df is not None and not north_df.empty:
                        latest = north_df.iloc[-1]
                        north_flow = float(latest.get("value", 0) or latest.get("净流入", 0) or 0)
                except Exception:
                    pass

                return self._result_template(
                    limit_up_count=up_count,
                    north_flow=north_flow,
                )
            except Exception as e:
                return {"_error": str(e)}

        return self._safe_fetch(fetch)

    # ================================================================
    # 情绪分析
    # ================================================================

    def _analyze_sentiment(self, text: str) -> float:
        """
        简单情绪分析
        返回: -1.0 (极度负面) ~ +1.0 (极度正面)
        """
        if not text:
            return 0.0

        text_lower = text.lower()
        pos_count = sum(1 for w in POSITIVE_WORDS if w in text)
        neg_count = sum(1 for w in NEGATIVE_WORDS if w in text)

        total = pos_count + neg_count
        if total == 0:
            return 0.0

        raw = (pos_count - neg_count) / total
        # 平滑映射
        return round(raw * (total / (total + 3)), 3)  # 添加先验


# 单例
news_data = NewsDataFetcher()
