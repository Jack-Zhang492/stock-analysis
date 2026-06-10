"""
综合预测引擎 — 多维因子加权合成，输出预测方向+置信度
"""
import time
from typing import Dict, Optional, Any

from data.merger import DataMerger, merger as data_merger
from analysis.features import FeatureEngineer, feature_engineer
from analysis.factors import FactorScorer, factor_scorer
from analysis.weights import WeightManager, weight_manager
from analysis.evidence import EvidenceBuilder, evidence_builder
from utils.validators import normalize_code, split_code
from utils.logger import log
from config import SCORE_TO_DIRECTION, CONFIDENCE_HIGH, CONFIDENCE_MID


class StockPredictor:
    """股票综合预测器"""

    def __init__(self):
        self.merger = data_merger
        self.features = feature_engineer
        self.scorer = factor_scorer
        self.weights = weight_manager
        self.evidence = evidence_builder

    def predict(self, raw_code: str, fast_mode: bool = False) -> Dict[str, Any]:
        """
        对一只股票进行全面分析和预测
        参数:
            raw_code: 用户输入的股票代码（支持各种格式）
            fast_mode: 快速模式（减少数据量，适合实时查询）
        返回: 结构化预测结果
        """
        start_time = time.time()

        # 1. 标准化代码
        stock_code = normalize_code(raw_code)
        _, code = split_code(stock_code)

        # 2. 数据采集
        log.info(f"[predictor] 开始分析 {stock_code}")
        merged = self.merger.merge_all(stock_code, fast_mode=fast_mode)
        completeness = merged["_meta"]["completeness"]

        # 3. 特征提取
        all_features = self.features.extract_all(merged)

        # 4. 因子打分
        scores, evidence_lists = self.scorer.get_scores_and_evidence(all_features)

        # 5. 权重计算
        final_weights = self.weights.get_weights(
            scores=scores,
            features=all_features,
            completeness=completeness,
        )

        # 6. 综合得分
        composite_score = sum(
            scores[dim] * final_weights.get(dim, 0.25)
            for dim in scores
        )

        # 7. 方向判定
        direction, emoji = self._score_to_direction(composite_score)

        # 8. 置信度
        conf_factors = self.weights.get_confidence_factors(
            scores, final_weights, completeness
        )
        confidence_pct, confidence_level = self._calc_confidence(conf_factors)

        # 9. 构建证据链
        summary = self.merger.get_summary(merged)
        key_evidence, risk_warnings = self.evidence.build(
            scores, evidence_lists, all_features, final_weights, summary
        )

        # 10. 组装输出
        elapsed = time.time() - start_time

        result = {
            "stock_code": stock_code,
            "raw_code": code,
            "stock_name": summary.get("realtime", {}).get("name", ""),
            "current_price": summary.get("realtime", {}).get("price", 0),
            "change_pct": summary.get("realtime", {}).get("change_pct", 0),
            "fetch_time": merged["_meta"]["fetch_time"],
            "analysis_time": f"{elapsed:.1f}s",
            "fast_mode": fast_mode,
            "completeness": completeness,
            # 核心预测
            "composite_score": round(composite_score, 1),
            "direction": direction,
            "direction_emoji": emoji,
            "confidence_pct": confidence_pct,
            "confidence_level": confidence_level,
            # 各维度得分
            "dimension_scores": {
                "technical": {"score": scores.get("technical", 50), "weight": final_weights.get("technical", 0.25)},
                "fundamental": {"score": scores.get("fundamental", 50), "weight": final_weights.get("fundamental", 0.25)},
                "sentiment": {"score": scores.get("sentiment", 50), "weight": final_weights.get("sentiment", 0.25)},
                "event": {"score": scores.get("event", 50), "weight": final_weights.get("event", 0.20)},
            },
            # 证据
            "key_evidence": key_evidence,
            "risk_warnings": risk_warnings,
            # 底层数据引用
            "data_summary": summary,
            # 置信度分解
            "confidence_factors": conf_factors,
            # 原始采集数据（供详细展示用）
            "_raw": merged,
        }

        return result

    def _score_to_direction(self, score: float) -> tuple:
        """综合得分 → 方向标签"""
        for threshold, label, emoji in SCORE_TO_DIRECTION:
            if score >= threshold:
                return label, emoji
        return "中性/震荡", "📊"

    def _calc_confidence(self, factors: dict) -> tuple:
        """
        计算置信度
        返回: (百分比, 高中低)
        """
        consistency = factors.get("signal_consistency", 0.3)
        data_quality = factors.get("data_quality", 0.5)
        strength = factors.get("prediction_strength", 0)

        # 加权合成置信度
        confidence = (
            consistency * 0.40 +
            data_quality * 0.35 +
            strength * 0.25
        ) * 100

        confidence = round(confidence, 1)

        if confidence >= CONFIDENCE_HIGH:
            level = "高"
        elif confidence >= CONFIDENCE_MID:
            level = "中"
        else:
            level = "低"

        return confidence, level

    def predict_brief(self, raw_code: str) -> str:
        """
        简短预测摘要（适合快速查看）
        """
        result = self.predict(raw_code, fast_mode=True)
        return (
            f"{result['direction_emoji']} {result['stock_name']}({result['raw_code']}) "
            f"综合评分 {result['composite_score']:.0f}/100 "
            f"→ {result['direction']} "
            f"[置信度: {result['confidence_level']}({result['confidence_pct']}%)]"
        )


# 单例
predictor = StockPredictor()


# ================================================================
# CLI测试入口
# ================================================================
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) > 1:
        code = sys.argv[1]
    else:
        code = "600519"

    p = StockPredictor()
    result = p.predict(code)

    print("\n" + "=" * 65)
    print(f"  🔬 A股量化分析 — {result['stock_name']}({result['raw_code']})")
    print("=" * 65)
    print(f"  现价: ¥{result['current_price']:.2f}  "
          f"涨跌幅: {result['change_pct']:+.2f}%")
    print(f"  采集时间: {result['fetch_time']}  "
          f"耗时: {result['analysis_time']}  "
          f"数据完整度: {result['completeness']}%")
    print()
    print(f"  ┌─────────────────────────────────────┐")
    print(f"  │  综合评分: {result['composite_score']:5.1f} / 100           │")
    print(f"  │  预测方向: {result['direction_emoji']} {result['direction']:12s}            │")
    print(f"  │  置信度:   {result['confidence_level']} ({result['confidence_pct']:.0f}%)              │")
    print(f"  └─────────────────────────────────────┘")
    print()
    print("  四维因子得分:")
    for dim, info in result["dimension_scores"].items():
        bar = "█" * int(info["score"] / 5) + "░" * (20 - int(info["score"] / 5))
        labels = {"technical": "技术面", "fundamental": "基本面", "sentiment": "情绪面", "event": "事件面"}
        print(f"    {labels.get(dim, dim):6s} [{info['weight']*100:3.0f}%] {bar} {info['score']:.0f}")

    print()
    print("  📋 关键依据:")
    for ev in result["key_evidence"]:
        print(f"    • {ev}")

    if result["risk_warnings"]:
        print()
        print("  ⚠️ 风险提示:")
        for rw in result["risk_warnings"]:
            print(f"    • {rw}")

    print()
    print("=" * 65)
