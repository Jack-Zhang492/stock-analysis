"""
五层数据合并与标准化
将所有数据源采集到的原始数据整合为统一的分析数据结构
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any

from data.market_data import market_data
from data.research_data import research_data
from data.news_data import news_data
from data.fundamental_data import fundamental_data
from data.announcement_data import announcement_data
from utils.logger import log
from utils.validators import split_code


class DataMerger:
    """五层数据合并器"""

    def __init__(self):
        self.market = market_data
        self.research = research_data
        self.news = news_data
        self.fundamental = fundamental_data
        self.announcement = announcement_data

    def merge_all(self, stock_code: str, fast_mode: bool = False) -> Dict[str, Any]:
        """
        并行采集五层数据并合并
        参数:
            stock_code: 标准化股票代码 (如 sh600519)
            fast_mode: 快速模式，减少采集天数
        返回: 统一数据结构
        """
        start_time = time.time()
        _, code = split_code(stock_code)

        results = {
            "_meta": {
                "stock_code": stock_code,
                "raw_code": code,
                "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "fast_mode": fast_mode,
                "errors": [],
                "completeness": 0,  # 数据完整度 0-100
            },
            "market": None,
            "research": None,
            "news": None,
            "fundamental": None,
            "announcement": None,
        }

        days = 10 if fast_mode else 30

        # 并行采集（行情K线较慢，单独列出）
        tasks = {
            "realtime": lambda: self.market.get_realtime_quote(stock_code),
            "kline_daily": lambda: self.market.get_daily_kline(stock_code, days=250 if not fast_mode else 60),
            "research": lambda: self.research.get_research_reports(stock_code, days=days),
            "news": lambda: self.news.get_stock_news(stock_code, days=days),
            "fundamental": lambda: self.fundamental.get_financials(stock_code),
            "valuation": lambda: self.fundamental.get_valuation(stock_code),
            "announcement": lambda: self.announcement.get_announcements(stock_code, days=days),
        }

        with ThreadPoolExecutor(max_workers=6) as executor:
            future_map = {
                executor.submit(func): name
                for name, func in tasks.items()
            }

            for future in as_completed(future_map):
                name = future_map[future]
                try:
                    result = future.result(timeout=30)
                    self._store_result(results, name, result)
                except Exception as e:
                    log.error(f"[merger] {name} 采集超时或异常: {e}")
                    results["_meta"]["errors"].append(f"{name}: {e}")

        # 计算完整度
        self._calc_completeness(results)

        elapsed = time.time() - start_time
        log.info(f"[merger] {stock_code} 数据采集完成, 耗时 {elapsed:.1f}s, 完整度 {results['_meta']['completeness']}%")

        return results

    def _store_result(self, results: dict, name: str, data: dict):
        """将各层结果存入对应位置"""
        if name in ("realtime", "kline_daily"):
            if "market" not in results or results["market"] is None:
                results["market"] = {}
            if isinstance(results["market"], dict):
                results["market"][name] = data
        elif name in ("valuation",):
            if "fundamental" not in results or results["fundamental"] is None:
                results["fundamental"] = {}
            if isinstance(results["fundamental"], dict):
                results["fundamental"]["valuation"] = data
        else:
            results[name] = data

    def _calc_completeness(self, results: dict):
        """计算数据完整度"""
        layers = 0
        present = 0

        # 行情层: realtime + kline
        market = results.get("market", {}) or {}
        if market.get("realtime") and not market["realtime"].get("_error"):
            present += 1
        layers += 1
        if market.get("kline_daily") and not market["kline_daily"].get("_error"):
            present += 1
        layers += 1

        # 研报层
        research = results.get("research", {}) or {}
        if research and not research.get("_error") and research.get("reports"):
            present += 1
        layers += 1

        # 新闻层
        news = results.get("news", {}) or {}
        if news and not news.get("_error"):
            present += 1
        layers += 1

        # 基础数据层
        fundamental = results.get("fundamental", {}) or {}
        if fundamental and not fundamental.get("_error"):
            present += 1
        layers += 1

        # 公告层
        announcement = results.get("announcement", {}) or {}
        if announcement and not announcement.get("_error"):
            present += 1
        layers += 1

        results["_meta"]["completeness"] = round(present / max(layers, 1) * 100)

    def get_summary(self, merged: dict) -> dict:
        """生成数据摘要，供分析引擎使用"""
        summary = {
            "code": merged["_meta"]["stock_code"],
            "fetch_time": merged["_meta"]["fetch_time"],
            "completeness": merged["_meta"]["completeness"],
        }

        # 行情摘要
        market = merged.get("market", {}) or {}
        realtime = market.get("realtime", {}) or {}
        kline = market.get("kline_daily", {}) or {}

        summary["realtime"] = {
            "price": realtime.get("price", 0),
            "name": realtime.get("name", ""),
            "change_pct": realtime.get("change_pct", 0),
            "volume": realtime.get("volume", 0),
            "turnover": realtime.get("turnover", 0),
            "pe": realtime.get("pe", 0),
            "pb": realtime.get("pb", 0),
        }
        summary["kline_count"] = kline.get("count", 0)

        # 研报摘要
        research = merged.get("research", {}) or {}
        reports = research.get("reports", [])
        summary["research"] = {
            "report_count": len(reports),
            "latest_ratings": [r.get("rating", "") for r in reports[:5]],
            "has_target_price": any(r.get("target_price", 0) > 0 for r in reports),
        }

        # 新闻摘要
        news = merged.get("news", {}) or {}
        summary["news"] = {
            "news_count": news.get("count", 0),
            "sentiment_score": news.get("sentiment_score", 50),
        }

        # 基础数据摘要
        fundamental = merged.get("fundamental", {}) or {}
        valuation = fundamental.get("valuation", {}) or {}
        summary["fundamental"] = {
            "pe": valuation.get("pe", realtime.get("pe", 0)),
            "pb": valuation.get("pb", realtime.get("pb", 0)),
            "roe": valuation.get("roe", 0),
            "eps": valuation.get("eps", 0),
        }

        # 公告摘要
        announcement = merged.get("announcement", {}) or {}
        summary["announcement"] = {
            "total_count": announcement.get("count", 0),
            "high_importance": announcement.get("high_importance_count", 0),
            "latest": announcement.get("announcements", [])[:3],
        }

        return summary


# 单例
merger = DataMerger()


# ================================================================
# CLI 测试入口
# ================================================================
if __name__ == "__main__":
    import sys
    from utils.validators import normalize_code

    if len(sys.argv) > 1:
        stock_code = normalize_code(sys.argv[1])
    else:
        stock_code = "sh600519"  # 默认: 贵州茅台

    print(f"正在采集 {stock_code} 的五层数据...")
    print("=" * 60)

    m = DataMerger()
    data = m.merge_all(stock_code)

    # 打印摘要
    print(f"\n数据采集完成!")
    print(f"  股票代码: {data['_meta']['stock_code']}")
    print(f"  采集时间: {data['_meta']['fetch_time']}")
    print(f"  数据完整度: {data['_meta']['completeness']}%")
    print(f"  错误数: {len(data['_meta']['errors'])}")
    if data["_meta"]["errors"]:
        for e in data["_meta"]["errors"]:
            print(f"    ⚠ {e}")

    # 各层统计
    market = data.get("market", {}) or {}
    if market.get("realtime") and not market["realtime"].get("_error"):
        rt = market["realtime"]
        print(f"\n📈 行情层: {rt.get('name', '?')} 现价 {rt.get('price', 0):.2f} "
              f"涨跌幅 {rt.get('change_pct', 0):.2f}% PE {rt.get('pe', 0):.1f}")

    kline = market.get("kline_daily", {}) or {}
    if kline.get("data"):
        print(f"   K线: {kline.get('count', 0)} 条日线数据")

    research = data.get("research", {}) or {}
    if research.get("reports"):
        print(f"\n📋 研报层: {research.get('count', 0)} 篇研报")

    news = data.get("news", {}) or {}
    if news.get("news"):
        print(f"\n📰 新闻层: {news.get('count', 0)} 条新闻, 情绪分 {news.get('sentiment_score', 50)}")

    fundamental = data.get("fundamental", {}) or {}
    if fundamental and not fundamental.get("_error"):
        print(f"\n📊 基础数据层: 已获取")
        valuation = fundamental.get("valuation", {}) or {}
        if valuation:
            print(f"   ROE: {valuation.get('roe', 0):.2f}% EPS: {valuation.get('eps', 0):.3f}")

    announcement = data.get("announcement", {}) or {}
    if announcement.get("announcements"):
        print(f"\n📝 公告层: {announcement.get('count', 0)} 条公告, "
              f"其中重要 {announcement.get('high_importance_count', 0)} 条")

    print("\n" + "=" * 60)
    print("数据采集完成!")
