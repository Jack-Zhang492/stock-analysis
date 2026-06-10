"""
特征工程 — 从原始数据提取四维特征向量
技术面 / 基本面 / 情绪面 / 事件面
"""
import math
from typing import Dict, List, Optional, Any

import pandas as pd
import numpy as np


class FeatureEngineer:
    """特征工程器：将原始数据转为标准化特征向量"""

    # ================================================================
    # 技术面特征
    # ================================================================

    def extract_technical_features(self, market_data: dict) -> Dict[str, float]:
        """
        从行情数据提取技术面特征
        返回: 特征名 → 特征值（尽量归一化到 -1 ~ 1 范围）
        """
        features = {}
        realtime = market_data.get("realtime", {}) or {}
        kline = market_data.get("kline_daily", {}) or {}

        if not realtime and not kline:
            return features

        # 涨跌幅
        features["change_pct"] = realtime.get("change_pct", 0) / 10.0  # 归一化（假设10%涨停）
        features["change_pct"] = max(-1.0, min(1.0, features.get("change_pct", 0)))

        # 换手率
        turnover = realtime.get("turnover", 0)
        features["turnover"] = min(turnover / 20.0, 1.0)  # 20%以上换手视为极端

        # 量比 (当日成交量 / 5日均量)
        kline_data = kline.get("data", [])
        if kline_data and len(kline_data) >= 6:
            df = pd.DataFrame(kline_data)
            if "volume" in df.columns and "close" in df.columns:
                # 量比
                vol_today = df["volume"].iloc[-1] if len(df) > 0 else 0
                vol_ma5 = df["volume"].iloc[-6:-1].mean() if len(df) >= 6 else vol_today
                features["volume_ratio"] = (vol_today / vol_ma5 - 1) if vol_ma5 > 0 else 0
                features["volume_ratio"] = max(-1.0, min(1.0, features["volume_ratio"]))

                # 趋势强度 — 均线排列
                close = df["close"].values
                features["ma_score"] = self._calc_ma_score(close)

                # RSI (14日)
                features["rsi"] = self._calc_rsi(close, period=14)

                # 价格位置 (当前价在N日内的百分位)
                if len(close) >= 20:
                    high_n = df["high"].iloc[-20:].max() if "high" in df.columns else close[-20:].max()
                    low_n = df["low"].iloc[-20:].min() if "low" in df.columns else close[-20:].min()
                    price_range = high_n - low_n
                    if price_range > 0:
                        features["price_position"] = (close[-1] - low_n) / price_range
                    else:
                        features["price_position"] = 0.5

                # 波动率 (20日)
                if len(close) >= 20:
                    returns = np.diff(close[-21:]) / close[-21:-1]
                    features["volatility"] = min(np.std(returns) * math.sqrt(252) / 0.5, 1.0)  # 年化波动率，50%封顶

        return features

    def _calc_ma_score(self, close: np.ndarray) -> float:
        """
        计算均线排列得分 (-1 ~ 1)
        正值 = 多头排列，负值 = 空头排列
        """
        if len(close) < 60:
            return 0.0

        try:
            ma5 = np.mean(close[-5:])
            ma10 = np.mean(close[-10:])
            ma20 = np.mean(close[-20:])
            ma60 = np.mean(close[-60:]) if len(close) >= 60 else ma20

            current = close[-1]

            # 价格与各均线的关系
            scores = []
            for ma, weight in [(ma5, 0.3), (ma10, 0.25), (ma20, 0.25), (ma60, 0.2)]:
                if ma > 0:
                    dev = (current / ma - 1) * 100
                    scores.append(np.tanh(dev / 5) * weight)  # tanh 压缩到 [-1, 1]

            # 均线排列加分
            if ma5 > ma10 > ma20 > ma60:
                scores.append(0.3)  # 完美多头
            elif ma5 < ma10 < ma20 < ma60:
                scores.append(-0.3)  # 完美空头

            return float(np.clip(sum(scores), -1.0, 1.0))
        except Exception:
            return 0.0

    def _calc_rsi(self, close: np.ndarray, period: int = 14) -> float:
        """计算RSI，归一化到 -1~1"""
        if len(close) < period + 1:
            return 0.0

        try:
            deltas = np.diff(close[-period-1:])
            gains = np.sum(deltas[deltas > 0]) if np.any(deltas > 0) else 0
            losses = -np.sum(deltas[deltas < 0]) if np.any(deltas < 0) else 0

            if losses == 0:
                rsi = 100.0 if gains > 0 else 50.0
            else:
                rs = gains / losses
                rsi = 100.0 - (100.0 / (1.0 + rs))

            # 归一化: RSI 50 → 0, RSI 70 → 0.5, RSI 30 → -0.5
            return float((rsi - 50) / 40)
        except Exception:
            return 0.0

    # ================================================================
    # 基本面特征
    # ================================================================

    def extract_fundamental_features(self, fundamental_data: dict, market_data: dict = None) -> Dict[str, float]:
        """
        从基础数据提取基本面特征
        """
        features = {}
        valuation = fundamental_data.get("valuation", {}) or {}

        # ROE 质量
        roe = valuation.get("roe", 0)
        features["roe_score"] = min(roe / 20.0, 1.0) if roe > 0 else max(roe / 10.0, -1.0)

        # EPS
        eps = valuation.get("eps", 0)
        features["eps_score"] = np.tanh(eps) if eps else 0

        # 毛利率
        gross = valuation.get("gross_margin", 0)
        features["gross_margin"] = gross / 100.0 if gross else 0

        # 净利率
        net_margin = valuation.get("net_margin", 0)
        features["net_margin"] = net_margin / 100.0 if net_margin else 0

        # PE历史分位（简化：用当前PE判断）
        realtime = (market_data or {}).get("realtime", {}) or {}
        pe = valuation.get("pe", 0) or realtime.get("pe", 0)
        pb = valuation.get("pb", 0) or realtime.get("pb", 0)
        features["pe"] = min(pe / 60.0, 1.0) if pe > 0 else 0.5
        features["pb"] = min(pb / 10.0, 1.0) if pb > 0 else 0.5

        # 流通比例
        features["float_ratio"] = valuation.get("float_ratio", 0.5)

        return features

    # ================================================================
    # 情绪面特征
    # ================================================================

    def extract_sentiment_features(self, news_data: dict, research_data: dict = None) -> Dict[str, float]:
        """
        从新闻和研报提取情绪特征
        """
        features = {}

        # 新闻情绪
        sentiment_score = news_data.get("sentiment_score", 50)
        features["news_sentiment"] = (sentiment_score - 50) / 50.0  # 归一化到 -1~1

        # 新闻密度
        news_count = news_data.get("count", 0)
        features["news_density"] = min(news_count / 20.0, 1.0)  # 20条以上视为高密度

        # 研报评级
        research = research_data or {}
        reports = research.get("reports", [])
        if reports:
            # 统计买入/增持比例
            bullish = 0
            for r in reports:
                rating = r.get("rating", "")
                if any(kw in rating for kw in ["买入", "增持", "推荐", "强烈推荐", "优于大市", "Buy", "Overweight"]):
                    bullish += 1

            features["analyst_bullish_ratio"] = bullish / len(reports) if reports else 0.5

            # 目标价上涨空间
            targets = [r.get("target_price", 0) for r in reports if r.get("target_price", 0) > 0]
            current = r.get("current_price", 0) if reports else 0
            if targets and current > 0:
                avg_target = sum(targets) / len(targets)
                features["target_upside"] = min((avg_target / current - 1) / 0.3, 1.0)  # 30%上涨空间视为满分
            else:
                features["target_upside"] = 0
        else:
            features["analyst_bullish_ratio"] = 0.5
            features["target_upside"] = 0

        return features

    # ================================================================
    # 事件面特征
    # ================================================================

    def extract_event_features(self, announcement_data: dict) -> Dict[str, float]:
        """
        从公告数据提取事件特征
        """
        features = {}
        announcements = announcement_data.get("announcements", [])

        if not announcements:
            features["event_impact"] = 0
            features["event_count"] = 0
            features["event_max_importance"] = 0
            return features

        # 事件数量
        features["event_count"] = min(announcement_data.get("count", 0) / 15.0, 1.0)

        # 最高重要性
        max_imp = max((a.get("importance", 0) for a in announcements), default=0)
        features["event_max_importance"] = max_imp / 10.0

        # 综合影响：考虑最近的高重要公告
        recent_high = [a for a in announcements if a.get("importance", 0) >= 5]
        if recent_high:
            # 利好/利空判断（简化：关键词匹配）
            impact_scores = []
            for a in recent_high:
                title = a.get("title", "")
                score = 0
                if any(kw in title for kw in ["业绩预增", "回购", "中标", "增持", "分红", "送转"]):
                    score = a["importance"] / 10.0
                elif any(kw in title for kw in ["业绩预亏", "减持", "处罚", "退市", "ST", "诉讼"]):
                    score = -a["importance"] / 10.0
                impact_scores.append(score)

            features["event_impact"] = np.mean(impact_scores) if impact_scores else 0
        else:
            features["event_impact"] = 0

        return features

    # ================================================================
    # 综合提取
    # ================================================================

    def extract_all(self, merged_data: dict) -> Dict[str, Dict[str, float]]:
        """
        从合并后的数据提取所有特征
        返回: {维度名: {特征名: 特征值}}
        """
        return {
            "technical": self.extract_technical_features(merged_data.get("market", {})),
            "fundamental": self.extract_fundamental_features(
                merged_data.get("fundamental", {}),
                merged_data.get("market", {}),
            ),
            "sentiment": self.extract_sentiment_features(
                merged_data.get("news", {}),
                merged_data.get("research", {}),
            ),
            "event": self.extract_event_features(merged_data.get("announcement", {})),
        }


# 单例
feature_engineer = FeatureEngineer()
