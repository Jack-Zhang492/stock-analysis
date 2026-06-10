"""
搜索栏组件 — 支持股票代码/拼音/名称搜索
"""
import streamlit as st
from utils.validators import normalize_code, is_valid


def render_search_bar() -> str:
    """
    渲染搜索栏
    返回: 标准化股票代码，或空字符串
    """
    col1, col2 = st.columns([4, 1])

    with col1:
        query = st.text_input(
            "股票代码 / 名称 / 拼音",
            placeholder="例: 600519 / 贵州茅台 / gzmt",
            key="stock_query",
            label_visibility="collapsed",
        )

    with col2:
        search_clicked = st.button(
            "🔍 分析",
            use_container_width=True,
            type="primary",
            key="search_btn",
        )

    # 快速代码按钮
    quick_codes = ["600519 茅台", "000858 五粮液", "300750 宁德", "601318 平安", "002594 比亚迪"]
    cols = st.columns(len(quick_codes))
    for i, qc in enumerate(quick_codes):
        with cols[i]:
            if st.button(qc, key=f"quick_{i}", use_container_width=True):
                query = qc.split()[0]
                st.session_state.stock_query = query
                search_clicked = True

    if search_clicked and query:
        return normalize_code(query.strip())

    return ""
