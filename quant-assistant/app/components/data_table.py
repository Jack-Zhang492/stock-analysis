"""
五层数据明细表格 — 可折叠展开
"""
import streamlit as st
import pandas as pd


def render_data_tables(prediction: dict):
    """渲染五层数据明细（可展开）"""
    raw = prediction.get("_raw", {})
    st.subheader("📑 五层数据明细")

    tabs = st.tabs(["📈 行情", "📋 研报", "📰 新闻", "📊 基础", "📝 公告"])

    # 行情层
    with tabs[0]:
        market = raw.get("market", {}) or {}
        realtime = market.get("realtime", {}) or {}
        if realtime and not realtime.get("_error"):
            cols = st.columns(4)
            items = [
                ("名称", realtime.get("name", "N/A")),
                ("现价", f"¥{realtime.get('price', 0):.2f}"),
                ("今开", f"¥{realtime.get('open', 0):.2f}"),
                ("昨收", f"¥{realtime.get('pre_close', 0):.2f}"),
                ("最高", f"¥{realtime.get('high', 0):.2f}"),
                ("最低", f"¥{realtime.get('low', 0):.2f}"),
                ("涨跌幅", f"{realtime.get('change_pct', 0):+.2f}%"),
                ("换手率", f"{realtime.get('turnover', 0):.2f}%"),
                ("PE(TTM)", f"{realtime.get('pe', 0):.1f}"),
                ("PB", f"{realtime.get('pb', 0):.2f}"),
                ("总市值", f"¥{realtime.get('total_value', 0)/1e8:.1f}亿" if realtime.get('total_value') else "N/A"),
                ("流通市值", f"¥{realtime.get('circ_value', 0)/1e8:.1f}亿" if realtime.get('circ_value') else "N/A"),
            ]
            for i, (label, value) in enumerate(items):
                with cols[i % 4]:
                    st.metric(label, value)

        kline = market.get("kline_daily", {}) or {}
        if kline.get("data"):
            st.caption(f"K线数据: {kline.get('count', 0)} 条日线")

    # 研报层
    with tabs[1]:
        research = raw.get("research", {}) or {}
        reports = research.get("reports", [])
        if reports:
            df = pd.DataFrame(reports)
            cols_show = [c for c in ["title", "org", "date", "rating", "target_price"] if c in df.columns]
            if cols_show:
                st.dataframe(df[cols_show].head(15), use_container_width=True, hide_index=True)
            st.caption(f"共 {len(reports)} 篇研报")
        else:
            st.info("暂无研报数据")

    # 新闻层
    with tabs[2]:
        news = raw.get("news", {}) or {}
        news_list = news.get("news", [])
        if news_list:
            for n in news_list[:15]:
                sentiment_emoji = "🟢" if n.get("sentiment", 0) > 0.2 else "🔴" if n.get("sentiment", 0) < -0.2 else "⚪"
                st.markdown(
                    f"{sentiment_emoji} **{n.get('title', '')}**  \n"
                    f"*{n.get('time', '')} | {n.get('source', '')}*"
                )
            st.caption(f"共 {news.get('count', 0)} 条新闻，情绪分 {news.get('sentiment_score', 50)}")
        else:
            st.info("暂无新闻数据")

    # 基础数据层
    with tabs[3]:
        fundamental = raw.get("fundamental", {}) or {}
        valuation = fundamental.get("valuation", {}) or {}
        if valuation and not valuation.get("_error"):
            cols = st.columns(4)
            fund_items = [
                ("ROE", f"{valuation.get('roe', 0):.2f}%"),
                ("EPS", f"{valuation.get('eps', 0):.3f}"),
                ("BPS", f"{valuation.get('bps', 0):.2f}"),
                ("毛利率", f"{valuation.get('gross_margin', 0):.1f}%"),
                ("净利率", f"{valuation.get('net_margin', 0):.1f}%"),
                ("总股本", f"{valuation.get('total_shares', 0)/1e8:.2f}亿" if valuation.get('total_shares') else "N/A"),
                ("流通股本", f"{valuation.get('float_shares', 0)/1e8:.2f}亿" if valuation.get('float_shares') else "N/A"),
                ("流通比例", f"{valuation.get('float_ratio', 0)*100:.1f}%"),
            ]
            for i, (label, value) in enumerate(fund_items):
                with cols[i % 4]:
                    st.metric(label, value)

        # 财务数据
        income = fundamental.get("income")
        if income is not None:
            with st.expander("利润表（最近8期）"):
                st.dataframe(pd.DataFrame(income) if isinstance(income, list) else income, use_container_width=True)
        else:
            st.info("暂无详细财务数据")

    # 公告层
    with tabs[4]:
        announcement = raw.get("announcement", {}) or {}
        ann_list = announcement.get("announcements", [])
        if ann_list:
            for ann in ann_list[:20]:
                imp = ann.get("importance_label", "低")
                imp_color = "🔴" if imp == "高" else "🟡" if imp == "中" else "⚪"
                st.markdown(
                    f"{imp_color} [{imp}] **{ann.get('title', '')}**  \n"
                    f"*{ann.get('date', '')}*"
                )
            st.caption(f"共 {announcement.get('count', 0)} 条公告，其中重要 {announcement.get('high_importance_count', 0)} 条")
        else:
            st.info("暂无公告数据")
