#!/usr/bin/env python
"""
Claude Code Skill — A股量化分析
用法（被Claude Code调用）:
    python skill/analyze_stock.py <股票代码> [--fast]
用途:
    作为Claude Code的自定义Skill，接收股票代码参数，
    调用完整分析引擎并输出结构化报告。
"""
import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.predictor import predictor
from analysis.evidence import evidence_builder
from utils.validators import normalize_code, is_valid


def main():
    if len(sys.argv) < 2:
        print("用法: python skill/analyze_stock.py <股票代码> [--fast]")
        print("示例: python skill/analyze_stock.py 600519")
        print("      python skill/analyze_stock.py 000858 --fast")
        sys.exit(1)

    raw_code = sys.argv[1]
    fast_mode = "--fast" in sys.argv

    # 标准化代码
    stock_code = normalize_code(raw_code)
    if not is_valid(stock_code):
        print(f"❌ 无效的股票代码: {raw_code}")
        sys.exit(1)

    # 执行分析
    print(f"🔍 正在分析 {stock_code}...", file=sys.stderr)
    try:
        prediction = predictor.predict(stock_code, fast_mode=fast_mode)
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        sys.exit(1)

    # 输出 Markdown 报告
    report = evidence_builder.format_markdown_report(prediction)
    print(report)


if __name__ == "__main__":
    main()
