"""
公告数据采集 — 巨潮资讯网 (主) + mootdx (辅)
提供: 上市公司公告、重大事项、问询函
"""
import re
import time
from typing import Optional

import requests

from data.base import BaseFetcher
from utils.logger import log
from utils.cache import cached
from utils.validators import split_code, get_mootdx_code
from config import CNINFO_CONFIG


# 公告重要性关键词
HIGH_IMPORTANCE_KEYWORDS = [
    "业绩预告", "业绩快报", "年度报告", "半年度报告", "季度报告",
    "重大资产重组", "收购", "并购", "定增", "配股", "增发",
    "回购", "分红", "送转", "高送转",
    "股权激励", "员工持股",
    "实际控制人变更", "控股股东变更",
    "退市风险", "ST", "*ST", "暂停上市", "终止上市",
    "证监会", "行政处罚", "立案调查",
    "重大合同", "中标",
]

MEDIUM_IMPORTANCE_KEYWORDS = [
    "减持", "增持", "限售股", "解禁",
    "对外投资", "设立子公司",
    "董事会决议", "股东大会",
    "变更", "修订", "调整",
    "风险提示", "异常波动",
    "问询函", "关注函", "监管函",
]


class AnnouncementDataFetcher(BaseFetcher):
    """公告数据采集器"""

    name = "announcement"

    @cached("announcement", "announcement")
    def get_announcements(self, stock_code: str, days: int = 30) -> dict:
        """
        获取个股公告
        优先巨潮资讯网，失败降级到 mootdx
        """
        return self._safe_fetch(
            lambda: self._get_announcements_akshare(stock_code, days),
            fallback_func=lambda: self._get_announcements_cninfo(stock_code, days),
        )

    # ================================================================
    # 巨潮资讯网
    # ================================================================

    def _get_announcements_cninfo(self, stock_code: str, days: int = 30) -> dict:
        """巨潮资讯网公告"""
        _, code = split_code(stock_code)

        def fetch():
            base_url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "http://www.cninfo.com.cn/",
                "X-Requested-With": "XMLHttpRequest",
            }

            # 确定板块
            if code.startswith("6"):
                plate = "sh"
            elif code.startswith(("0", "3")):
                plate = "sz"
            elif code.startswith(("8", "4")):
                plate = "bj"
            else:
                plate = "sz"

            params = {
                "pageNum": 1,
                "pageSize": 30,
                "column": plate,
                "tabName": "fulltext",
                "plate": plate,
                "stock": f"{code},{code}",
                "searchkey": "",
                "secid": "",
                "category": "",
                "trade": "",
                "seDate": "",
                "sortName": "",
                "sortType": "",
            }

            resp = requests.post(
                base_url,
                data=params,
                headers=headers,
                timeout=CNINFO_CONFIG["timeout"],
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            if data is None:
                return None

            announcements = data.get("announcements", []) if isinstance(data, dict) else []
            if not announcements and isinstance(data, list):
                announcements = data

            results = []
            for item in announcements[:30]:
                title = item.get("announcementTitle", "") or item.get("title", "")
                ann_date = str(item.get("announcementTime", "") or item.get("adjunctUrl", ""))
                # 提取日期
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", ann_date)
                pub_date = date_match.group(1) if date_match else ann_date[:10]

                # 评估重要性
                importance = self._score_importance(title)

                results.append({
                    "title": title,
                    "date": pub_date,
                    "importance": importance,
                    "importance_label": (
                        "高" if importance >= 7 else "中" if importance >= 4 else "低"
                    ),
                    "url": f"http://static.cninfo.com.cn/{item.get('adjunctUrl', '')}",
                    "type": item.get("announcementType", "") or item.get("type", ""),
                })

            # 按重要性排序
            results.sort(key=lambda x: x["importance"], reverse=True)

            return self._result_template(
                announcements=results,
                count=len(results),
                high_importance_count=sum(1 for r in results if r["importance"] >= 7),
            )

        return fetch()

    # ================================================================
    # mootdx 公告（备用）
    # ================================================================

    def _get_announcements_akshare(self, stock_code: str, days: int = 30) -> dict:
        """akshare 公告数据（主源）"""
        try:
            import akshare as ak
            _, code = split_code(stock_code)

            # akshare 公告接口
            df = ak.stock_notices_em(symbol=code)
            if df is None or df.empty:
                return {"announcements": [], "count": 0, "_fallback": True}

            results = []
            for _, row in df.tail(30).iterrows():
                title = str(row.get("title", "") or row.get("标题", ""))
                date = str(row.get("notice_date", "") or row.get("公告日期", ""))[:10]
                importance = self._score_importance(title)

                results.append({
                    "title": title,
                    "date": date,
                    "importance": importance,
                    "importance_label": "高" if importance >= 7 else "中" if importance >= 4 else "低",
                    "url": "",
                })

            results.sort(key=lambda x: x["importance"], reverse=True)

            return self._result_template(
                announcements=results,
                count=len(results),
                _fallback=True,
            )
        except Exception as e:
            return {"_error": str(e), "announcements": [], "count": 0}

    # ================================================================
    # 公告重要性评分
    # ================================================================

    def _score_importance(self, title: str) -> int:
        """评估公告重要性 (0-10)"""
        score = 1  # 基础分
        for kw in HIGH_IMPORTANCE_KEYWORDS:
            if kw in title:
                score += 3
        for kw in MEDIUM_IMPORTANCE_KEYWORDS:
            if kw in title:
                score += 1

        # 年报/半年报/季报
        if re.search(r"(年度|半年度|季度|第.*季度).*报告", title):
            score += 3

        # 减持/增持
        if "减持" in title:
            score += 2
            if "控股股东" in title or "实际控制人" in title:
                score += 2

        if "增持" in title:
            score += 2

        return min(score, 10)


# 单例
announcement_data = AnnouncementDataFetcher()
