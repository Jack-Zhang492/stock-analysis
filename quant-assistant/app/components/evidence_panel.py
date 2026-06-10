"""
证据详情面板 + 因子得分展示
"""
import streamlit as st
import pandas as pd


def render_evidence_panel(prediction: dict):
    """渲染证据详情和因子得分"""

    # 四维因子得分 — 横向进度条
    st.subheader("📊 四维因子得分")

    dim_labels = {
        "technical": "技术面",
        "fundamental": "基本面",
        "sentiment": "情绪面",
        "event": "事件面",
    }

    dim_scores = prediction.get("dimension_scores", {})

    for dim_key, label in dim_labels.items():
        info = dim_scores.get(dim_key, {"score": 50, "weight": 0.25})
        score = info["score"]
        weight = info["weight"]

        # 进度条颜色
        if score >= 60:
            bar_color = "#ef5350"
        elif score <= 40:
            bar_color = "#26a69a"
        else:
            bar_color = "#ff9800"

        col1, col2, col3 = st.columns([2, 6, 1])
        with col1:
            st.markdown(f"**{label}** ({weight*100:.0f}%)")
        with col2:
            st.progress(score / 100)
        with col3:
            st.markdown(
                f"<span style='color:{bar_color};font-weight:bold;font-size:16px;'>{score:.0f}</span>",
                unsafe_allow_html=True,
            )

    # 分隔线
    st.divider()

    # 关键依据
    st.subheader("📋 关键依据")
    evidence = prediction.get("key_evidence", [])
    if evidence:
        for ev in evidence:
            st.markdown(f"- {ev}")
    else:
        st.info("暂无突出信号")

    # 风险提示
    st.divider()
    st.subheader("⚠️ 风险提示")
    risks = prediction.get("risk_warnings", [])
    if risks:
        for rw in risks:
            st.warning(rw)
    else:
        st.success("暂无显著风险信号")

    # 置信度分解
    st.divider()
    st.subheader("🔬 置信度分解")
    cf = prediction.get("confidence_factors", {})
    cf_data = {
        "因子": ["信号一致性", "数据质量", "预测强度"],
        "值": [
            f"{cf.get('signal_consistency', 0)*100:.0f}%",
            f"{cf.get('data_quality', 0)*100:.0f}%",
            f"{cf.get('prediction_strength', 0)*100:.0f}%",
        ],
        "说明": [
            "各维度方向是否一致",
            "五层数据采集完整度",
            "综合得分偏离中性程度",
        ],
    }
    st.dataframe(
        pd.DataFrame(cf_data),
        use_container_width=True,
        hide_index=True,
    )


def render_data_summary(prediction: dict):
    """渲染数据摘要信息"""
    summary = prediction.get("data_summary", {})
    realtime = summary.get("realtime", {}) or {}

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("现价", f"¥{realtime.get('price', 0):.2f}")
    with col2:
        delta = realtime.get("change_pct", 0)
        st.metric("涨跌幅", f"{delta:+.2f}%", delta=f"{delta:+.2f}%")
    with col3:
        st.metric("换手率", f"{realtime.get('turnover', 0):.2f}%")
    with col4:
        st.metric("PE(TTM)", f"{realtime.get('pe', 0):.1f}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("数据完整度", f"{prediction['completeness']}%")
    with col2:
        st.metric("K线数据", f"{summary.get('kline_count', 0)}条")
    with col3:
        st.metric("新闻情绪", f"{summary.get('news', {}).get('sentiment_score', 50)}分")
    with col4:
        st.metric("耗时", prediction.get("analysis_time", "N/A"))
