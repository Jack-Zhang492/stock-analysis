"""
预测结果卡片组件
"""
import streamlit as st


def render_prediction_card(prediction: dict):
    """渲染预测结果核心卡片"""
    score = prediction["composite_score"]
    direction = prediction["direction"]
    emoji = prediction["direction_emoji"]
    confidence = prediction["confidence_pct"]
    confidence_level = prediction["confidence_level"]

    # 颜色方案
    if score >= 60:
        score_color = "#ef5350"  # 红色（看多，A股习惯）
        bg_gradient = "linear-gradient(135deg, #fce4ec 0%, #ffffff 100%)"
    elif score <= 40:
        score_color = "#26a69a"  # 绿色（看空）
        bg_gradient = "linear-gradient(135deg, #e0f2f1 0%, #ffffff 100%)"
    else:
        score_color = "#ff9800"  # 橙色（中性）
        bg_gradient = "linear-gradient(135deg, #fff3e0 0%, #ffffff 100%)"

    # 置信度颜色
    if confidence_level == "高":
        conf_color = "#4caf50"
    elif confidence_level == "中":
        conf_color = "#ff9800"
    else:
        conf_color = "#f44336"

    st.markdown(f"""
    <div style="
        background: {bg_gradient};
        border-radius: 16px;
        padding: 24px;
        margin: 16px 0;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    ">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;">
            <div style="text-align: center; min-width: 120px;">
                <div style="font-size: 12px; color: #888; margin-bottom: 4px;">综合评分</div>
                <div style="font-size: 48px; font-weight: bold; color: {score_color};">{score:.0f}</div>
                <div style="font-size: 12px; color: #888;">/ 100</div>
            </div>
            <div style="text-align: center; min-width: 120px;">
                <div style="font-size: 12px; color: #888; margin-bottom: 4px;">预测方向</div>
                <div style="font-size: 32px;">{emoji}</div>
                <div style="font-size: 18px; font-weight: 600; color: {score_color};">{direction}</div>
            </div>
            <div style="text-align: center; min-width: 120px;">
                <div style="font-size: 12px; color: #888; margin-bottom: 4px;">置信度</div>
                <div style="font-size: 32px; font-weight: bold; color: {conf_color};">{confidence_level}</div>
                <div style="font-size: 14px; color: #888;">{confidence}%</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
