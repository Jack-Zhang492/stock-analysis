"""
A股量化分析助手 — Streamlit Web 主界面
"""
import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from app.components.search_bar import render_search_bar
from app.components.prediction_card import render_prediction_card
from app.components.evidence_panel import render_evidence_panel, render_data_summary
from app.components.charts import render_kline_chart
from app.components.data_table import render_data_tables
from analysis.predictor import predictor
from utils.validators import is_valid, normalize_code

# 页面配置
st.set_page_config(
    page_title="A股量化分析助手",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ================================================================
# 自定义CSS
# ================================================================
st.markdown("""
<style>
    /* 主标题 */
    .main-title {
        font-size: 2rem;
        font-weight: bold;
        background: linear-gradient(135deg, #ef5350, #ff7043);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .subtitle {
        color: #888;
        font-size: 0.9rem;
        margin-top: -10px;
        margin-bottom: 20px;
    }
    /* 数据指标 */
    div[data-testid="stMetricValue"] {
        font-size: 1.2rem;
    }
    /* 按钮 */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
    }
    /* 进度条 */
    div[data-testid="stProgress"] > div {
        background-color: #e0e0e0;
    }
    /* 侧边栏 */
    section[data-testid="stSidebar"] {
        background-color: #fafafa;
    }
    /* 风险提示 */
    div[data-testid="stWarning"] {
        background-color: #fff3e0;
    }
</style>
""", unsafe_allow_html=True)

# ================================================================
# 侧边栏
# ================================================================
with st.sidebar:
    st.markdown("### ⚙️ 设置")

    fast_mode = st.toggle("快速模式", value=False, help="减少数据量，加快分析速度")
    show_raw_data = st.toggle("显示原始数据", value=False, help="展开五层数据明细")

    st.divider()

    st.markdown("### 📊 分析框架")
    st.markdown("""
    | 维度 | 权重 |
    |------|------|
    | 技术面 | 30% |
    | 基本面 | 25% |
    | 情绪面 | 25% |
    | 事件面 | 20% |
    """)

    st.divider()

    st.markdown("### ℹ️ 关于")
    st.markdown("""
    **A股量化分析助手 v1.0**

    基于五层数据 + 多因子模型的
    综合研判工具

    ⚠️ 所有分析仅供参考
    不构成投资建议
    """)

    st.divider()
    st.caption(f"数据源: mootdx | akshare | 腾讯财经 | 东方财富 | 巨潮资讯")

# ================================================================
# 主内容区
# ================================================================
st.markdown('<p class="main-title">🔬 A股量化分析助手</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">基于五层数据 · 多因子打分 · 综合研判</p>', unsafe_allow_html=True)

# 搜索栏
stock_code = render_search_bar()

# 结果区
if not stock_code:
    # 空状态
    st.info("👆 请输入股票代码或名称开始分析\n\n"
            "支持格式: 600519 / 贵州茅台 / sh600519 / 600519.SH")
    st.stop()

if not is_valid(stock_code):
    st.error(f"❗ 无效的股票代码: `{stock_code}`，请输入6位数字代码或股票名称")
    st.stop()

# 执行分析
with st.spinner(f"🔍 正在分析 {stock_code}，采集五层数据中..."):
    try:
        prediction = predictor.predict(stock_code, fast_mode=fast_mode)
    except Exception as e:
        st.error(f"❌ 分析失败: {e}")
        st.stop()

# ================================================================
# 结果展示
# ================================================================

# 标题行
st.markdown(f"## {prediction['stock_name']} ({prediction['raw_code']})")
st.caption(f"数据采集: {prediction['fetch_time']} | 分析耗时: {prediction['analysis_time']} | "
           f"完整度: {prediction['completeness']}% {'⚡快速模式' if fast_mode else ''}")

# 核心预测卡片
render_prediction_card(prediction)

# 数据摘要
render_data_summary(prediction)

# 两栏布局：证据+K线
st.divider()
col_left, col_right = st.columns([1, 1.2])

with col_left:
    render_evidence_panel(prediction)

with col_right:
    st.subheader("📈 K线图 + 技术指标")
    render_kline_chart(prediction)

# 五层数据明细
if show_raw_data:
    st.divider()
    render_data_tables(prediction)

# ================================================================
# 免责声明
# ================================================================
st.divider()
st.caption(
    "⚠️ **免责声明**: 本工具所有分析结果仅供参考，不构成任何投资建议。"
    "股市有风险，投资需谨慎。所有最终交易决策由您本人作出。"
    "数据来源: mootdx、akshare、腾讯财经、东方财富、巨潮资讯网。"
)
