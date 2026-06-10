"""
权重配置与动态调整
根据市场环境和信号质量动态调整四维因子权重
"""
from typing import Dict
import numpy as np

from config import DEFAULT_WEIGHTS, MARKET_REGIME_ADJUST


class WeightManager:
    """权重管理器"""

    def __init__(self):
        self.base_weights = DEFAULT_WEIGHTS.copy()

    def get_weights(
        self,
        scores: Dict[str, float] = None,
        features: dict = None,
        completeness: float = 100.0,
    ) -> Dict[str, float]:
        """
        获取最终权重（动态调整后）
        参数:
            scores: 各维度得分 {维度: 分数}
            features: 特征向量（用于判断市场环境）
            completeness: 数据完整度百分比
        """
        weights = self.base_weights.copy()

        # 1. 根据市场环境调整
        if features:
            tech_features = features.get("technical", {})
            adx = tech_features.get("volatility", 0.2)  # 用波动率近似ADX

            if adx > 0.4:  # 高波动/趋势市
                self._apply_regime(weights, "trending")
            elif adx < 0.15:  # 低波动/震荡市
                self._apply_regime(weights, "ranging")

            # 极端情绪判断
            sent_features = features.get("sentiment", {})
            news_sent = sent_features.get("news_sentiment", 0)
            if abs(news_sent) > 0.6:  # 情绪极端
                self._apply_regime(weights, "extreme_sentiment")

        # 2. 根据数据完整度调整：缺失数据的维度降低权重
        if scores:
            for dim, score in scores.items():
                if score == 50.0:  # 默认中性分 = 大概率数据缺失
                    weights[dim] *= 0.5  # 降权

        # 3. 归一化
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        # 4. 限制单维度权重范围 [0.10, 0.45]
        for dim in weights:
            weights[dim] = max(0.10, min(0.45, weights[dim]))

        # 再次归一化
        total = sum(weights.values())
        weights = {k: round(v / total, 4) for k, v in weights.items()}

        return weights

    def _apply_regime(self, weights: dict, regime: str):
        """应用市场环境调整"""
        adjust = MARKET_REGIME_ADJUST.get(regime, {})
        for dim, delta in adjust.items():
            if dim in weights:
                weights[dim] += delta

    def get_confidence_factors(
        self, scores: Dict[str, float], weights: Dict[str, float], completeness: float
    ) -> Dict[str, float]:
        """
        计算置信度相关因子
        返回:
            - signal_consistency: 信号一致性 (越高越一致)
            - data_quality: 数据质量
            - prediction_strength: 预测强度
        """
        factors = {}

        # 信号一致性：各维度得分离散度的反函数
        if scores and len(scores) >= 2:
            score_values = list(scores.values())
            std = np.std(score_values)
            # std=0 完全一致 → 1.0, std=20 极度分歧 → 0.2
            factors["signal_consistency"] = round(max(0.1, 1.0 - std / 25.0), 3)
        else:
            factors["signal_consistency"] = 0.3

        # 数据质量 = 完整度
        factors["data_quality"] = completeness / 100.0

        # 预测强度 = 加权得分偏离50的程度
        if scores:
            composite = sum(scores[d] * weights.get(d, 0.25) for d in scores)
            factors["prediction_strength"] = min(abs(composite - 50) / 30.0, 1.0)
        else:
            factors["prediction_strength"] = 0

        return factors


# 单例
weight_manager = WeightManager()
