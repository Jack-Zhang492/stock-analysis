"""
因子构建与打分 — 将特征向量映射为 0-100 分数
"""
from typing import Dict, List, Tuple
import numpy as np


class FactorScorer:
    """因子打分器：四维特征 → 四个维度得分 (0-100)"""

    # ================================================================
    # 技术面打分
    # ================================================================

    def score_technical(self, features: Dict[str, float]) -> Tuple[float, List[str]]:
        """
        技术面打分
        输入特征 → 0-100分 + 关键依据
        """
        if not features:
            return 50.0, ["技术面数据缺失"]

        score = 50.0
        evidence = []

        # 趋势得分 (权重40%)
        ma_score = features.get("ma_score", 0)
        trend_score = 50 + ma_score * 40
        score += (trend_score - 50) * 0.4

        if ma_score > 0.3:
            evidence.append(f"均线多头排列(得分{ma_score:.2f})")
        elif ma_score < -0.3:
            evidence.append(f"均线空头排列(得分{ma_score:.2f})")

        # 量价得分 (权重25%)
        vol_ratio = features.get("volume_ratio", 0)
        change_pct = features.get("change_pct", 0)

        # 放量上涨 = 强势，放量下跌 = 弱势
        if vol_ratio > 0.15 and change_pct > 0:
            vol_score = 70
            evidence.append("放量上涨，量价配合良好")
        elif vol_ratio > 0.15 and change_pct < 0:
            vol_score = 30
            evidence.append("放量下跌，抛压明显")
        elif vol_ratio < -0.15 and change_pct > 0:
            vol_score = 55
            evidence.append("缩量上涨，需关注持续性")
        elif vol_ratio < -0.15 and change_pct < 0:
            vol_score = 40
            evidence.append("缩量下跌，空方力量减弱")
        else:
            vol_score = 50

        score += (vol_score - 50) * 0.25

        # RSI得分 (权重20%)
        rsi = features.get("rsi", 0)
        if rsi > 0.5:
            rsi_score = 70
            evidence.append("RSI偏强，多头主导")
        elif rsi < -0.5:
            rsi_score = 30
            evidence.append("RSI偏弱，空头主导")
        elif rsi > 0.25:
            rsi_score = 60
        elif rsi < -0.25:
            rsi_score = 40
        else:
            rsi_score = 50
        score += (rsi_score - 50) * 0.20

        # 价格位置 (权重15%)
        position = features.get("price_position", 0.5)
        if position > 0.8:
            pos_score = 45  # 高位风险
            evidence.append("价格处于近期高位")
        elif position < 0.2:
            pos_score = 45  # 低位但有反弹可能
            evidence.append("价格处于近期低位")
        else:
            pos_score = 55
        score += (pos_score - 50) * 0.15

        return round(max(10, min(90, score)), 1), evidence[:3]

    # ================================================================
    # 基本面打分
    # ================================================================

    def score_fundamental(self, features: Dict[str, float]) -> Tuple[float, List[str]]:
        """基本面打分"""
        if not features:
            return 50.0, ["基本面数据缺失"]

        score = 50.0
        evidence = []

        # ROE (权重30%)
        roe = features.get("roe_score", 0)
        if roe > 0.5:
            roe_score = 75
            evidence.append("ROE优秀，盈利能力突出")
        elif roe > 0.25:
            roe_score = 60
            evidence.append("ROE良好")
        elif roe < -0.3:
            roe_score = 30
            evidence.append("ROE为负，盈利能力差")
        else:
            roe_score = 50
        score += (roe_score - 50) * 0.30

        # PE估值 (权重25%)
        pe = features.get("pe", 0.5)
        if pe < 0.25:  # PE < 15
            pe_score = 65
            evidence.append("PE处于低位，估值合理")
        elif pe > 0.75:  # PE > 45
            pe_score = 35
            evidence.append("PE偏高，估值压力较大")
        else:
            pe_score = 50
        score += (pe_score - 50) * 0.25

        # PB估值 (权重15%)
        pb = features.get("pb", 0.5)
        if pb < 0.2:
            pb_score = 60
            evidence.append("PB较低，安全边际充足")
        elif pb > 0.8:
            pb_score = 40
            evidence.append("PB偏高")
        else:
            pb_score = 50
        score += (pb_score - 50) * 0.15

        # 毛利率+净利率 (权重20%)
        gross = features.get("gross_margin", 0)
        net = features.get("net_margin", 0)
        margin_score = 50
        if gross > 0.3:
            margin_score += 15
            evidence.append(f"毛利率{gross*100:.1f}%，竞争力强")
        elif gross < 0.1:
            margin_score -= 10

        if net > 0.15:
            margin_score += 10
        elif net < 0:
            margin_score -= 15

        score += (margin_score - 50) * 0.20

        # EPS (权重10%)
        eps = features.get("eps_score", 0)
        eps_score = 50 + eps * 20
        score += (eps_score - 50) * 0.10

        return round(max(10, min(90, score)), 1), evidence[:4]

    # ================================================================
    # 情绪面打分
    # ================================================================

    def score_sentiment(self, features: Dict[str, float]) -> Tuple[float, List[str]]:
        """情绪面打分"""
        if not features:
            return 50.0, ["情绪面数据缺失"]

        score = 50.0
        evidence = []

        # 新闻情绪 (权重40%)
        news_sent = features.get("news_sentiment", 0)
        sent_score = 50 + news_sent * 35
        score += (sent_score - 50) * 0.40

        if news_sent > 0.3:
            evidence.append(f"新闻情绪正面(得分{news_sent:.2f})")
        elif news_sent < -0.2:
            evidence.append(f"新闻情绪偏负面(得分{news_sent:.2f})")

        # 分析师评级 (权重35%)
        bullish = features.get("analyst_bullish_ratio", 0.5)
        if bullish > 0.7:
            analyst_score = 70
            evidence.append(f"分析师普遍看好(看好比例{bullish*100:.0f}%)")
        elif bullish > 0.5:
            analyst_score = 55
        elif bullish < 0.3:
            analyst_score = 35
            evidence.append(f"分析师偏谨慎(看好比例{bullish*100:.0f}%)")
        else:
            analyst_score = 50
        score += (analyst_score - 50) * 0.35

        # 目标价上涨空间 (权重25%)
        upside = features.get("target_upside", 0)
        if upside > 0.5:
            upside_score = 70
            evidence.append("机构目标价显著高于现价")
        elif upside > 0.15:
            upside_score = 58
            evidence.append("机构目标价略高于现价")
        elif upside < -0.2:
            upside_score = 38
        else:
            upside_score = 50
        score += (upside_score - 50) * 0.25

        return round(max(10, min(90, score)), 1), evidence[:3]

    # ================================================================
    # 事件面打分
    # ================================================================

    def score_event(self, features: Dict[str, float]) -> Tuple[float, List[str]]:
        """事件面打分"""
        if not features:
            return 50.0, ["事件面数据缺失"]

        score = 50.0
        evidence = []

        impact = features.get("event_impact", 0)
        max_imp = features.get("event_max_importance", 0)
        count = features.get("event_count", 0)

        # 事件影响 (权重60%)
        event_score = 50 + impact * 35
        score += (event_score - 50) * 0.60

        if impact > 0.2:
            evidence.append("近期公告整体偏利好")
        elif impact < -0.15:
            evidence.append("近期公告偏利空，需关注风险")

        # 事件重要性 (权重25%)
        if max_imp > 0.8:
            imp_score = 75 if impact >= 0 else 25
            evidence.append("有重大事项公告")
        elif max_imp > 0.5:
            imp_score = 60 if impact >= 0 else 40
        else:
            imp_score = 50
        score += (imp_score - 50) * 0.25

        # 事件数量 (权重15%)
        if count > 0.5:
            count_score = 55
            evidence.append("公告密集，公司处于活跃期")
        else:
            count_score = 50
        score += (count_score - 50) * 0.15

        return round(max(10, min(90, score)), 1), evidence[:3]

    # ================================================================
    # 综合打分
    # ================================================================

    def score_all(self, features: dict) -> Dict[str, dict]:
        """
        四维特征 → 四维得分
        返回: {维度名: {"score": float, "evidence": [...]}}
        """
        return {
            "technical": {
                "score": self.score_technical(features.get("technical", {})),
            },
            "fundamental": {
                "score": self.score_fundamental(features.get("fundamental", {})),
            },
            "sentiment": {
                "score": self.score_sentiment(features.get("sentiment", {})),
            },
            "event": {
                "score": self.score_event(features.get("event", {})),
            },
        }

    def get_scores_and_evidence(self, features: dict) -> Tuple[Dict[str, float], Dict[str, list]]:
        """获取得分字典和证据字典"""
        raw = self.score_all(features)
        scores = {}
        evidence = {}
        for dim, data in raw.items():
            s, ev_list = data["score"]
            scores[dim] = s
            evidence[dim] = ev_list
        return scores, evidence


# 单例
factor_scorer = FactorScorer()
