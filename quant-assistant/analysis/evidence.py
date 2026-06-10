"""
证据链构建 — 将因子得分和特征转化为可读的关键依据和风险提示
"""
from typing import Dict, List, Tuple


class EvidenceBuilder:
    """证据链构建器"""

    def build(
        self,
        scores: Dict[str, float],
        evidence_lists: Dict[str, List[str]],
        features: dict,
        weights: Dict[str, float],
        summary: dict,
    ) -> Tuple[List[str], List[str]]:
        """
        构建关键证据和风险提示
        返回: (key_evidence, risk_warnings)
        """
        key_evidence = []
        risk_warnings = []

        # 1. 从各维度收集证据
        dim_labels = {
            "technical": "技术面",
            "fundamental": "基本面",
            "sentiment": "情绪面",
            "event": "事件面",
        }

        for dim, ev_list in evidence_lists.items():
            score = scores.get(dim, 50)
            weight = weights.get(dim, 0)

            # 高分维度优先展示
            if score >= 65 and weight >= 0.15:
                for ev in ev_list[:2]:
                    key_evidence.append(f"[{dim_labels.get(dim, dim)}] {ev}")
            elif score <= 35 and weight >= 0.15:
                for ev in ev_list[:1]:
                    risk_warnings.append(f"[{dim_labels.get(dim, dim)}] {ev}")

        # 2. 行情面特殊分析
        realtime = summary.get("realtime", {}) or {}
        price = realtime.get("price", 0)
        change_pct = realtime.get("change_pct", 0)
        turnover = realtime.get("turnover", 0)

        if abs(change_pct) > 5:
            direction = "大涨" if change_pct > 0 else "大跌"
            key_evidence.append(f"[行情] 当日{direction} {change_pct:+.2f}%，注意短期波动风险")

        if turnover > 15:
            risk_warnings.append(f"[行情] 换手率高达 {turnover:.1f}%，筹码交换剧烈")

        # 3. PE/PB风险
        pe = realtime.get("pe", 0)
        pb = realtime.get("pb", 0)
        if pe > 100:
            risk_warnings.append(f"[估值] PE高达 {pe:.0f}，估值压力显著")
        elif pe > 50:
            risk_warnings.append(f"[估值] PE={pe:.0f}，处于较高水平")
        if pb > 10:
            risk_warnings.append(f"[估值] PB={pb:.1f}，远高于净资产")

        # 4. 公告风险
        announcement = summary.get("announcement", {}) or {}
        high_imp = announcement.get("high_importance", 0)
        latest = announcement.get("latest", [])
        for ann in latest[:3]:
            title = ann.get("title", "")
            if any(kw in title for kw in ["减持", "处罚", "退市", "ST", "诉讼", "立案"]):
                risk_warnings.append(f"[公告] {title[:60]}")
            elif any(kw in title for kw in ["回购", "增持", "中标", "业绩预增"]):
                key_evidence.append(f"[公告] {title[:60]}")

        # 5. 信号分歧检测
        score_values = [scores.get(d, 50) for d in ["technical", "fundamental", "sentiment", "event"]]
        if score_values:
            max_score = max(score_values)
            min_score = min(score_values)
            if max_score - min_score > 25:
                risk_warnings.append(f"[信号] 各维度信号分歧较大（最高{max_score:.0f} vs 最低{min_score:.0f}），预测可靠性下降")

        # 6. 数据完整度警告
        completeness = summary.get("completeness", 100)
        if completeness < 60:
            risk_warnings.append(f"[数据] 数据完整度仅{completeness}%，预测结果仅供参考")

        # 去重
        key_evidence = list(dict.fromkeys(key_evidence))
        risk_warnings = list(dict.fromkeys(risk_warnings))

        return key_evidence[:8], risk_warnings[:6]

    def format_markdown_report(self, prediction: dict) -> str:
        """
        生成结构化Markdown报告（与CLAUDE.md第六条格式一致）
        """
        lines = []
        lines.append(f"## 研判结论")
        lines.append(f"{prediction['direction_emoji']} **{prediction['stock_name']}({prediction['raw_code']})** "
                     f"综合评分 {prediction['composite_score']:.0f}/100 → **{prediction['direction']}** "
                     f"[置信度: {prediction['confidence_level']}({prediction['confidence_pct']}%)]")
        lines.append("")

        lines.append("## 核心逻辑")
        for i, ev in enumerate(prediction.get("key_evidence", [])[:5], 1):
            lines.append(f"{i}. {ev}")
        lines.append("")

        lines.append("## 风险提示")
        if prediction.get("risk_warnings"):
            for rw in prediction["risk_warnings"]:
                lines.append(f"- ⚠️ {rw}")
        else:
            lines.append("- 暂无显著风险信号")
        lines.append("")

        lines.append("## 数据依据")
        lines.append(f"- 现价: ¥{prediction['current_price']:.2f}，涨跌幅: {prediction['change_pct']:+.2f}%")
        lines.append(f"- 数据采集时间: {prediction['fetch_time']}")
        lines.append(f"- 数据完整度: {prediction['completeness']}%")
        lines.append(f"- 分析耗时: {prediction['analysis_time']}")
        lines.append("")

        lines.append("### 四维因子得分")
        for dim_key, info in prediction.get("dimension_scores", {}).items():
            labels = {"technical": "技术面", "fundamental": "基本面", "sentiment": "情绪面", "event": "事件面"}
            lines.append(f"- {labels.get(dim_key, dim_key)}: **{info['score']:.0f}/100** (权重 {info['weight']*100:.0f}%)")
        lines.append("")

        lines.append("## 置信度")
        cf = prediction.get("confidence_factors", {})
        lines.append(f"- 信号一致性: {cf.get('signal_consistency', 0):.2f}")
        lines.append(f"- 数据质量: {cf.get('data_quality', 0):.2f}")
        lines.append(f"- 综合置信度: {prediction['confidence_level']}（{prediction['confidence_pct']}%）")
        lines.append("")

        lines.append("## 操作建议")
        lines.append("> ⚠️ 以上分析仅供参考，不构成投资建议。请结合自身风险偏好和市场实际情况做出决策。")
        lines.append("> 所有最终交易决策由您本人作出。")

        return "\n".join(lines)


# 单例
evidence_builder = EvidenceBuilder()
