"""
研报数据采集 — 东方财富 (主) + akshare (辅) + iwencai (补充)
提供: 分析师评级、目标价、盈利预测、一致预期
"""
import time
import re
from typing import Optional

import pandas as pd
import requests
from utils.logger import log
from utils.cache import cached
from data.base import BaseFetcher
from utils.validators import split_code
from config import EASTMONEY_CONFIG, AKSHARE_CONFIG


class ResearchDataFetcher(BaseFetcher):
    """研报数据采集器"""

    name = "research"

    # ================================================================
    # 东方财富 — 研报摘要 + 评级
    # ================================================================

    @cached("research_report", "research_report")
    def get_research_reports(self, stock_code: str, days: int = 30) -> dict:
        """
        获取个股研报
        优先东方财富，失败降级到 akshare
        """
        return self._safe_fetch(
            lambda: self._get_reports_eastmoney(stock_code, days),
            fallback_func=lambda: self._get_reports_akshare(stock_code, days),
        )

    def _get_reports_eastmoney(self, stock_code: str, days: int = 30) -> dict:
        """东方财富研报数据"""
        _, code = split_code(stock_code)

        def fetch():
            # 东方财富研报接口
            url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
            params = {
                "reportName": "RPT_INDIVIDUALSERACH",
                "columns": "ALL",
                "filter": f'(SECURITY_CODE="{
                    code}")',
                "pageNumber": 1,
                "pageSize": 20,
                "sortTypes": -1,
                "sortColumns": "NOTICE_DATE",
                "source": "WEB",
                "client": "WEB",
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://data.eastmoney.com/",
            }

            resp = requests.get(url, params=params, headers=headers, timeout=EASTMONEY_CONFIG["timeout"])
            if resp.status_code != 200:
                return None

            data = resp.json()
            if not data.get("success"):
                return None

            reports = []
            raw_list = data.get("result", {}).get("data", [])
            for item in raw_list:
                reports.append({
                    "title": item.get("NOTICE_NAME", "") or item.get("TITLE", ""),
                    "org": item.get("ORGAN_NAME", "") or item.get("ORG_NAME", ""),
                    "author": item.get("ANALYST_NAME", ""),
                    "date": str(item.get("NOTICE_DATE", ""))[:10],
                    "rating": item.get("RATING_NAME", "") or item.get("RATING", ""),
                    "rating_change": item.get("RATING_CHANGE_NAME", ""),
                    "target_price": float(item.get("TARGET_PRICE", 0) or 0),
                    "current_price": float(item.get("CLOSE_PRICE", 0) or 0),
                    "summary": item.get("ABSTRACT", "") or item.get("SUMMARY", "") or "",
                })

            return self._result_template(reports=reports, count=len(reports))

        return fetch()

    def _get_reports_akshare(self, stock_code: str, days: int = 30) -> dict:
        """akshare 研报（备用）"""
        try:
            import akshare as ak
            _, code = split_code(stock_code)

            df = ak.stock_research_report_em(symbol=code)
            if df is None or df.empty:
                return None

            reports = []
            for _, row in df.tail(20).iterrows():
                reports.append({
                    "title": str(row.get("researchReportTitle", "")),
                    "org": str(row.get("organName", "")),
                    "date": str(row.get("noticeDate", ""))[:10] if row.get("noticeDate") else "",
                    "rating": str(row.get("ratingName", "")),
                    "target_price": float(row.get("targetPrice", 0) or 0),
                })

            return self._result_template(reports=reports, count=len(reports), _fallback=True)
        except Exception as e:
            return {"_error": str(e), "reports": []}

    # ================================================================
    # 一致预期 (Consensus) - 东方财富
    # ================================================================

    @cached("consensus", "research_report")
    def get_consensus(self, stock_code: str) -> dict:
        """获取一致预期数据"""

        def fetch():
            _, code = split_code(stock_code)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://data.eastmoney.com/",
            }

            # 盈利预测
            url = f"https://datacenter.eastmoney.com/securities/api/data/v1/get"
            params = {
                "reportName": "RPT_PC_PERFORMANCETARGET",
                "columns": "ALL",
                "filter": f'(SECURITY_CODE="{code}")',
                "pageNumber": 1,
                "pageSize": 10,
                "sortTypes": -1,
                "sortColumns": "NOTICE_DATE",
                "source": "WEB",
                "client": "WEB",
            }

            resp = requests.get(url, params=params, headers=headers, timeout=EASTMONEY_CONFIG["timeout"])
            if resp.status_code != 200:
                return None

            data = resp.json()
            if not data.get("success"):
                return None

            forecasts = []
            for item in data.get("result", {}).get("data", []):
                forecasts.append({
                    "year": str(item.get("PREDICT_NET_YEAR", "")),
                    "eps": float(item.get("PREDICT_NET_EPS", 0) or 0),
                    "revenue": float(item.get("PREDICT_NET_INCOME", 0) or 0),
                    "org_count": int(item.get("ORG_COUNT", 0) or 0),
                })

            return self._result_template(consensus=forecasts, count=len(forecasts))

        return self._safe_fetch(fetch)

    # ================================================================
    # 机构评级汇总 - iwencai
    # ================================================================

    def get_rating_summary(self, stock_code: str) -> dict:
        """通过 iwencai 获取评级汇总"""
        try:
            import akshare as ak

            _, code = split_code(stock_code)

            # 用问财查询评级
            df = ak.stock_professional_rating_em(symbol=code)
            if df is None or df.empty:
                return {"ratings": [], "summary": "暂无评级数据"}

            # 统计评级分布
            rating_col = None
            for col in ["评级", "rating", "RATING", "投资评级"]:
                if col in df.columns:
                    rating_col = col
                    break

            if rating_col:
                rating_counts = df[rating_col].value_counts().to_dict()
            else:
                rating_counts = {}

            return self._result_template(
                ratings=df.tail(10).to_dict(orient="records"),
                rating_distribution=rating_counts,
                latest_rating=str(df.iloc[-1].get(rating_col, "")) if rating_col else "",
            )
        except Exception as e:
            return {"_error": str(e), "ratings": [], "summary": ""}


# 单例
research_data = ResearchDataFetcher()
