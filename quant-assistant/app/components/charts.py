"""
K线图 + 技术指标图表组件
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def render_kline_chart(prediction: dict):
    """渲染交互式K线图（含均线+成交量）"""
    raw = prediction.get("_raw", {})
    market = raw.get("market", {}) or {}
    kline = market.get("kline_daily", {}) or {}
    data = kline.get("data", [])

    if not data:
        st.info("暂无K线数据")
        return

    df = pd.DataFrame(data)

    # 确保必要的列
    required_cols = ["date", "open", "high", "low", "close", "volume"]
    available = [c for c in required_cols if c in df.columns]
    if "date" not in available or "close" not in available:
        st.info("K线数据格式不完整")
        return

    # 日期处理
    df["date"] = pd.to_datetime(df["date"])

    # 计算均线
    df["MA5"] = df["close"].rolling(5).mean()
    df["MA10"] = df["close"].rolling(10).mean()
    df["MA20"] = df["close"].rolling(20).mean()
    df["MA60"] = df["close"].rolling(60).mean()

    # 创建双面板图表
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
    )

    # K线
    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"] if "open" in df.columns else df["close"],
            high=df["high"] if "high" in df.columns else df["close"],
            low=df["low"] if "low" in df.columns else df["close"],
            close=df["close"],
            name="K线",
            increasing_line_color="#ef5350",
            decreasing_line_color="#26a69a",
        ),
        row=1, col=1,
    )

    # 均线
    ma_colors = {"MA5": "#ff9800", "MA10": "#2196f3", "MA20": "#9c27b0", "MA60": "#607d8b"}
    for ma_name, color in ma_colors.items():
        if ma_name in df.columns and df[ma_name].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=df["date"], y=df[ma_name],
                    mode="lines",
                    name=ma_name,
                    line=dict(color=color, width=1),
                ),
                row=1, col=1,
            )

    # 成交量
    if "volume" in df.columns:
        colors = ["#ef5350" if c >= o else "#26a69a"
                  for c, o in zip(df["close"], df.get("open", df["close"]))]
        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df["volume"],
                name="成交量",
                marker_color=colors,
                opacity=0.5,
            ),
            row=2, col=1,
        )

    # 布局
    fig.update_layout(
        title=f"{prediction['stock_name']}({prediction['raw_code']}) K线图",
        xaxis_rangeslider_visible=False,
        height=500,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
        template="plotly_white",
    )

    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_xaxes(title_text="日期", row=2, col=1)
    fig.update_yaxes(title_text="价格 (¥)", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)
