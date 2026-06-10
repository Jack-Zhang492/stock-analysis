"""
基础数据采集 — akshare (主) + mootdx (辅)
提供: 财务指标、股本结构、分红除权、行业分类
"""
from typing import Optional

import pandas as pd

from data.base import BaseFetcher
from utils.logger import log
from utils.cache import cached
from utils.validators import split_code, get_mootdx_code
from config import TDX_CONFIG


class FundamentalDataFetcher(BaseFetcher):
    """基础数据采集器"""

    name = "fundamental"

    # ================================================================
    # 财务数据
    # ================================================================

    @cached("financials", "financials")
    def get_financials(self, stock_code: str) -> dict:
        """获取财务数据（主要财务指标）"""
        return self._safe_fetch(
            lambda: self._get_financials_akshare(stock_code),
            fallback_func=lambda: self._get_financials_mootdx(stock_code),
        )

    def _get_financials_akshare(self, stock_code: str) -> dict:
        """通过 akshare 获取财务指标"""
        try:
            import akshare as ak
            _, code = split_code(stock_code)

            result = {}

            # 主要财务指标
            try:
                df = ak.stock_financial_abstract_ths(symbol=code, indicator="按报告期")
                if df is not None and not df.empty:
                    result["indicators"] = df.tail(8).to_dict(orient="records")
            except Exception as e:
                log.warning(f"[fundamental] akshare 财务指标获取失败: {e}")

            # 利润表
            try:
                df_income = ak.stock_profit_sheet_by_report_em(symbol=code)
                if df_income is not None and not df_income.empty:
                    result["income"] = df_income.head(8).to_dict(orient="records")
            except Exception:
                pass

            # 资产负债表
            try:
                df_balance = ak.stock_balance_sheet_by_report_em(symbol=code)
                if df_balance is not None and not df_balance.empty:
                    result["balance"] = df_balance.head(8).to_dict(orient="records")
            except Exception:
                pass

            if result:
                return self._result_template(**result)
            return {"_error": "akshare 财务数据获取失败"}

        except Exception as e:
            return {"_error": str(e)}

    def _get_financials_mootdx(self, stock_code: str) -> dict:
        """通过 mootdx 获取财务数据（备用）"""
        try:
            from mootdx.quotes import Quotes
            code, market = get_mootdx_code(stock_code)

            client = Quotes.factory(market="std", timeout=TDX_CONFIG["timeout"])
            # mootdx 0.11+ finance 通过 quotes.finance() 方法
            data = client.finance(symbol=code)
            if data is not None:
                return self._result_template(
                    raw_finance=str(data)[:500],  # 截断以防太大
                    _fallback=True,
                )
            return {"_error": "mootdx 财务数据为空"}
        except Exception as e:
            return {"_error": str(e)}

    # ================================================================
    # 估值指标 + 关键比率
    # ================================================================

    @cached("valuation", "financials")
    def get_valuation(self, stock_code: str) -> dict:
        """获取估值相关指标"""
        return self._safe_fetch(
            lambda: self._get_valuation_akshare(stock_code),
        )

    def _get_valuation_akshare(self, stock_code: str) -> dict:
        """通过 akshare 获取估值数据"""
        try:
            import akshare as ak
            _, code = split_code(stock_code)

            indicators = {}

            # 个股信息（含PE/PB/市值等）
            try:
                df = ak.stock_individual_info_em(symbol=code)
                if df is not None and not df.empty:
                    info_dict = dict(zip(df["item"], df["value"]))
                    indicators = {
                        "pe": _safe_float(info_dict.get("市盈率-动态", 0)),
                        "pb": _safe_float(info_dict.get("市净率", 0)),
                        "total_shares": _safe_float(info_dict.get("总股本", 0)),
                        "float_shares": _safe_float(info_dict.get("流通股", 0)),
                        "total_value": _safe_float(info_dict.get("总市值", 0)),
                        "circ_value": _safe_float(info_dict.get("流通市值", 0)),
                        "eps": _safe_float(info_dict.get("每股收益", 0)),
                        "bps": _safe_float(info_dict.get("每股净资产", 0)),
                        "roe": _safe_float(info_dict.get("净资产收益率", 0)),
                        "gross_margin": _safe_float(info_dict.get("毛利率", 0)),
                        "net_margin": _safe_float(info_dict.get("净利率", 0)),
                    }
            except Exception as e:
                log.warning(f"[fundamental] akshare 个股信息获取失败: {e}")

            # 财务指标补充
            try:
                df_fin = ak.stock_financial_analysis_indicator(symbol=code)
                if df_fin is not None and not df_fin.empty:
                    latest = df_fin.iloc[0]
                    roe_val = _safe_float(latest.get("净资产收益率", 0))
                    if roe_val and not indicators.get("roe"):
                        indicators["roe"] = roe_val
                    eps_val = _safe_float(latest.get("基本每股收益", 0))
                    if eps_val and not indicators.get("eps"):
                        indicators["eps"] = eps_val
                    gross = _safe_float(latest.get("销售毛利率", 0))
                    if gross and not indicators.get("gross_margin"):
                        indicators["gross_margin"] = gross
                    net_m = _safe_float(latest.get("销售净利率", 0))
                    if net_m and not indicators.get("net_margin"):
                        indicators["net_margin"] = net_m
            except Exception:
                pass

            # 股本结构补全
            try:
                if not indicators.get("total_shares"):
                    df_shares = ak.stock_share_change_em(symbol=code)
                    if df_shares is not None and not df_shares.empty:
                        last_row = df_shares.iloc[-1]
                        indicators["total_shares"] = _safe_float(last_row.get("总股本", 0))
                        indicators["float_shares"] = _safe_float(last_row.get("已上市流通A股", 0))
            except Exception:
                pass

            # 计算流通比例
            total = indicators.get("total_shares", 0)
            flt = indicators.get("float_shares", 0)
            indicators["float_ratio"] = (flt / total) if total > 0 else 0

            return self._result_template(**indicators) if indicators else {"_error": "估值数据获取失败"}

        except Exception as e:
            return {"_error": str(e)}

    # ================================================================
    # 行业分类
    # ================================================================

    def get_industry(self, stock_code: str) -> dict:
        """获取行业分类"""
        try:
            import akshare as ak
            _, code = split_code(stock_code)

            df = ak.stock_individual_info_em(symbol=code)
            if df is not None and not df.empty:
                info = dict(zip(df["item"], df["value"]))
                return self._result_template(
                    sector=info.get("行业", ""),
                    sub_sector=info.get("板块", ""),
                    industry=info.get("所处行业", ""),
                )
            return {}
        except Exception as e:
            return {"_error": str(e)}

    # ================================================================
    # 分红除权
    # ================================================================

    @cached("dividend", "financials")
    def get_dividend_history(self, stock_code: str) -> dict:
        """获取分红送转历史"""
        try:
            import akshare as ak
            _, code = split_code(stock_code)

            df = ak.stock_dividents_em(symbol=code)
            if df is not None and not df.empty:
                return self._result_template(
                    dividends=df.tail(10).to_dict(orient="records"),
                )
            return {"dividends": []}
        except Exception as e:
            return {"_error": str(e), "dividends": []}


def _safe_float(val) -> float:
    """安全转换浮点数"""
    if val is None:
        return 0.0
    try:
        # 去除单位（如 "亿"、"万"）
        s = str(val).replace(",", "").replace("%", "")
        if "亿" in s:
            return float(s.replace("亿", "")) * 1e8
        if "万" in s:
            return float(s.replace("万", "")) * 1e4
        return float(s)
    except (ValueError, TypeError):
        return 0.0


# 单例
fundamental_data = FundamentalDataFetcher()
