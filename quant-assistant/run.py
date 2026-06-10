"""
启动入口 — A股量化分析助手
用法:
    streamlit run run.py              # 启动Web界面
    python run.py analyze 600519      # CLI分析模式
"""
import sys
import os

# Windows终端UTF-8编码修复
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "analyze" and len(sys.argv) > 2:
            # CLI分析模式
            from analysis.predictor import predictor
            stock_code = sys.argv[2]
            fast = "--fast" in sys.argv
            result = predictor.predict(stock_code, fast_mode=fast)
            from analysis.evidence import evidence_builder
            report = evidence_builder.format_markdown_report(result)
            print(report)
            return

        elif cmd == "brief" and len(sys.argv) > 2:
            # 简短模式
            from analysis.predictor import predictor
            print(predictor.predict_brief(sys.argv[2]))
            return

        elif cmd == "test" and len(sys.argv) > 2:
            # 数据采集测试
            from data.merger import merger as m
            from utils.validators import normalize_code
            import json
            code = normalize_code(sys.argv[2])
            data = m.merge_all(code)
            summary = m.get_summary(data)
            print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
            return

        else:
            print("用法:")
            print("  streamlit run run.py                   启动Web界面")
            print("  python run.py analyze <代码>           完整分析（Markdown报告）")
            print("  python run.py analyze <代码> --fast    快速分析")
            print("  python run.py brief <代码>             简短摘要")
            print("  python run.py test <代码>              数据采集测试")
            return

    # 默认：启动 Streamlit
    print("启动 Web 界面...")
    print("请使用: streamlit run run.py")
    print()
    print("或者用CLI模式:")
    print("  python run.py analyze 600519")


if __name__ == "__main__":
    main()
