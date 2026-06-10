"""
行情数据采集 — mootdx (主) + 腾讯财经 (备用)
提供: K线(日/周/月)、实时行情、分时数据
"""
import time
import re
from typing import Optional

import pandas as pd
import requests
from mootdx.quotes import Quotes
from mootdx import consts

from data.base import BaseFetcher, DataFetchError
from utils.validators import split_code, get_mootdx_code, get_tencent_code
from utils.logger import log
from utils.cache import cached
from config import TDX_CONFIG, TENCENT_API


class MarketDataFetcher(BaseFetcher):
    """行情数据采集器"""

    name = "market"

    def __init__(self):
        super().__init__()
        self._tdx_client = None
        self._tdx_available = None

    @property
    def tdx_client(self):
        """懒加载通达信客户端"""
        if self._tdx_client is None:
            try:
                self._tdx_client = Quotes.factory(
                    market="std",
                    multithread=True,
                    heartbeat=True,
                    bestip=True,
                    timeout=TDX_CONFIG["timeout"],
                )
                # 快速测试连接
                self._tdx_client.stocks(market=1)[:1]
                self._tdx_available = True
                self.log.info("[market] mootdx 连接成功")
            except Exception as e:
                self.log.warning(f"[market] mootdx 连接失败: {e}，将使用腾讯财经作为主源")
                self._tdx_available = False
        return self._tdx_client if self._tdx_available else None

    # ================================================================
    # 实时行情
    # ================================================================

    def get_realtime_quote(self, stock_code: str) -> dict:
        """
        获取实时行情
        优先 mootdx，失败降级到腾讯财经
        """
        client = self.tdx_client
        if client:
            return self._get_realtime_tdx(stock_code)
        return self._get_realtime_tencent(stock_code)

    def _get_realtime_tdx(self, stock_code: str) -> dict:
        """通过 mootdx 获取实时行情"""
        code, market = get_mootdx_code(stock_code)

        def fetch():
            data = self.tdx_client.quotes(
                market=market,
                code=code,
            )
            if data is None or data.empty:
                return None

            row = data.iloc[0] if len(data) > 0 else None
            if row is None:
                return None

            return self._result_template(
                code=code,
                name=row.get("name", ""),
                price=float(row.get("price", 0)),
                open=float(row.get("open", 0)),
                high=float(row.get("high", 0)),
                low=float(row.get("low", 0)),
                pre_close=float(row.get("last_close", 0)),
                volume=float(row.get("volume", 0)),
                amount=float(row.get("amount", 0)),
                change_pct=float(row.get("rise_per", 0) or row.get("涨幅", 0)),
                turnover=float(row.get("hs", 0) or row.get("换手率", 0)),
                pe=float(row.get("pe", 0) or 0),
                pb=float(row.get("pb", 0) or 0),
                total_value=float(row.get("gx_type", 0) or row.get("总市值", 0)),
                circ_value=float(row.get("ltsz", 0) or row.get("流通市值", 0)),
            )

        return self._safe_fetch(
            fetch,
            fallback_func=lambda: self._get_realtime_tencent(stock_code),
        )

    def _get_realtime_tencent(self, stock_code: str) -> dict:
        """通过腾讯财经API获取实时行情"""
        tencent_code = get_tencent_code(stock_code)

        def fetch():
            url = TENCENT_API["quote_url"].format(code=tencent_code)
            resp = requests.get(url, timeout=TENCENT_API["timeout"])
            resp.encoding = "gbk"

            if resp.status_code != 200:
                return None

            # 解析腾讯返回格式
            content = resp.text
            if "~" not in content:
                return None

            # 提取数据段
            match = re.search(r'="([^"]+)"', content)
            if not match:
                return None

            fields = match.group(1).split("~")
            if len(fields) < 50:
                return None

            return self._result_template(
                code=fields[2],
                name=fields[1],
                price=float(fields[3]) if fields[3] else 0,
                pre_close=float(fields[4]) if fields[4] else 0,
                open=float(fields[5]) if fields[5] else 0,
                volume=float(fields[6]) if fields[6] else 0,  # 手
                high=float(fields[33]) if fields[33] else 0,
                low=float(fields[34]) if fields[34] else 0,
                amount=float(fields[37]) if fields[37] else 0,  # 万元
                change_pct=float(fields[32]) if fields[32] else 0,
                turnover=float(fields[38]) if fields[38] else 0,
                pe=float(fields[39]) if fields[39] else 0,
                pb=float(fields[46]) if fields[46] else 0,
                total_value=float(fields[45]) if fields[45] else 0,
                circ_value=float(fields[44]) if fields[44] else 0,
            )

        return self._safe_fetch(fetch)

    # ================================================================
    # 历史K线
    # ================================================================

    @cached("kline_daily", "kline_daily")
    def get_daily_kline(self, stock_code: str, days: int = 250) -> dict:
        """获取日K线数据"""
        return self._get_kline(stock_code, consts.KLINE_DAILY, days)

    @cached("kline_weekly", "kline_weekly")
    def get_weekly_kline(self, stock_code: str, days: int = 100) -> dict:
        """获取周K线数据"""
        return self._get_kline(stock_code, consts.KLINE_WEEKLY, days)

    @cached("kline_monthly", "kline_monthly")
    def get_monthly_kline(self, stock_code: str, months: int = 36) -> dict:
        """获取月K线数据"""
        return self._get_kline(stock_code, consts.KLINE_MONTHLY, months)

    def _get_kline(self, stock_code: str, frequency: int, count: int) -> dict:
        """通用K线获取 (mootdx 0.11+ uses bars() with frequency)"""
        code, market = get_mootdx_code(stock_code)
        client = self.tdx_client

        if not client:
            # mootdx 不可用时，尝试用腾讯财经获取日K
            if frequency == consts.KLINE_DAILY:
                return self._get_kline_tencent(stock_code, count)
            return {"_error": "mootdx不可用，无法获取周/月K线", "data": None}

        def fetch():
            data = client.bars(
                symbol=code,
                frequency=frequency,
                start=0,
                offset=count,
            )
            if data is None or data.empty:
                return None

            # 标准化列名 (mootdx 0.11+ bars() 返回大写列名)
            if data is not None and not data.empty:
                # 尝试映射列名
                col_rename = {}
                for col in data.columns:
                    col_upper = str(col).upper()
                    if col_upper in ("OPEN",):
                        col_rename[col] = "open"
                    elif col_upper in ("HIGH",):
                        col_rename[col] = "high"
                    elif col_upper in ("LOW",):
                        col_rename[col] = "low"
                    elif col_upper in ("CLOSE",):
                        col_rename[col] = "close"
                    elif col_upper in ("VOL", "VOLUME"):
                        col_rename[col] = "volume"
                    elif col_upper in ("AMOUNT",):
                        col_rename[col] = "amount"
                    elif col_upper in ("DATE", "DAY"):
                        col_rename[col] = "date"
                    elif col_upper in ("CODE",):
                        col_rename[col] = "code"
                if col_rename:
                    data = data.rename(columns=col_rename)

            # 保留需要的列（去重）
            keep_cols = ["date", "open", "high", "low", "close", "volume", "amount"]
            # 先删除重复列
            data = data.loc[:, ~data.columns.duplicated()]
            available = [c for c in keep_cols if c in data.columns]
            if not available:
                # 如果没有匹配的列，保留原始数据
                records = data.tail(count).to_dict(orient="records")
            else:
                df_out = data[available].tail(count).copy()
                # 日期格式化
                if "date" in df_out.columns:
                    df_out["date"] = pd.to_datetime(df_out["date"]).dt.strftime("%Y-%m-%d")
                records = df_out.to_dict(orient="records")

            return self._result_template(
                data=records,
                count=len(records),
                kline_type=str(frequency),
            )

        return self._safe_fetch(fetch)

    def _get_kline_tencent(self, stock_code: str, days: int = 250) -> dict:
        """腾讯财经日K线（备用）"""
        tencent_code = get_tencent_code(stock_code)

        def fetch():
            url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={tencent_code},day,,,{days},qfq"
            resp = requests.get(url, timeout=TENCENT_API["timeout"])
            if resp.status_code != 200:
                return None

            j = resp.json()
            klines = j.get("data", {}).get(tencent_code, {}).get("day", []) or j.get("data", {}).get(tencent_code, {}).get("qfqday", [])

            if not klines:
                return None

            records = []
            for row in klines:
                records.append({
                    "date": row[0],
                    "open": float(row[1]),
                    "close": float(row[2]),
                    "high": float(row[3]),
                    "low": float(row[4]),
                    "volume": float(row[5]),
                })

            return self._result_template(
                data=records,
                count=len(records),
                kline_type="daily",
                _fallback=True,
            )

        return self._safe_fetch(fetch)

    # ================================================================
    # 股票列表
    # ================================================================

    @cached("stock_list", "stock_list")
    def get_stock_list(self) -> dict:
        """获取全市场股票列表"""
        client = self.tdx_client
        if not client:
            return {"_error": "mootdx不可用", "data": []}

        def fetch():
            stocks_list = []
            for market_id in [0, 1]:  # 深圳、上海
                data = client.stocks(market=market_id)
                if data is not None and not data.empty:
                    for _, row in data.iterrows():
                        stocks_list.append({
                            "code": str(row.get("code", "")).zfill(6),
                            "name": row.get("name", ""),
                            "market": "sh" if market_id == 1 else "sz",
                            "volume": int(row.get("volume", 0)),
                        })
            return self._result_template(data=stocks_list, count=len(stocks_list))

        return self._safe_fetch(fetch)


# 单例
market_data = MarketDataFetcher()
