"""
全局配置 — A股量化分析助手
"""
import os
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent
CACHE_DIR = ROOT_DIR / "cache"
LOG_DIR = ROOT_DIR / "logs"

# 自动创建目录
CACHE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ============================================================
# 数据源配置
# ============================================================

# mootdx (通达信) — 主行情+基础数据
TDX_CONFIG = {
    "best_ip": {"ip": "127.0.0.1", "port": 7709},  # 本地通达信
    "fallback_ips": [
        {"ip": "119.147.212.81", "port": 7709},
        {"ip": "121.36.81.195", "port": 7709},
        {"ip": "218.108.98.244", "port": 7709},
    ],
    "timeout": 10,
}

# 腾讯财经 — 备用行情
TENCENT_API = {
    "quote_url": "http://qt.gtimg.cn/q={code}",
    "batch_url": "http://qt.gtimg.cn/q={codes}",
    "timeout": 8,
}

# akshare — 新闻+研报补充
AKSHARE_CONFIG = {
    "rate_limit": 1.5,  # 请求间隔(秒)
    "timeout": 15,
}

# 东方财富 — 研报主源
EASTMONEY_CONFIG = {
    "timeout": 12,
}

# 巨潮资讯网 — 公告主源
CNINFO_CONFIG = {
    "timeout": 15,
}

# ============================================================
# 缓存配置
# ============================================================
CACHE_TTL = {
    "realtime_quote": 300,        # 5分钟
    "kline_daily": 86400,         # 1天
    "kline_weekly": 86400,
    "kline_monthly": 86400,
    "research_report": 43200,     # 12小时
    "news": 3600,                 # 1小时
    "financials": 86400,          # 1天
    "announcement": 7200,         # 2小时
    "stock_list": 86400,
}

# ============================================================
# 分析引擎配置
# ============================================================

# 四维因子默认权重
DEFAULT_WEIGHTS = {
    "technical": 0.30,    # 技术面
    "fundamental": 0.25,  # 基本面
    "sentiment": 0.25,    # 情绪面
    "event": 0.20,        # 事件面
}

# 市场环境 → 权重调整
MARKET_REGIME_ADJUST = {
    "trending": {    # ADX > 25
        "technical": +0.05,
        "fundamental": -0.05,
        "sentiment": 0,
        "event": 0,
    },
    "ranging": {     # ADX < 20
        "technical": 0,
        "fundamental": +0.05,
        "sentiment": +0.05,
        "event": -0.10,
    },
    "extreme_sentiment": {  # 极端情绪
        "technical": 0,
        "fundamental": 0,
        "sentiment": -0.10,
        "event": +0.10,
    },
}

# 评分 → 方向映射
SCORE_TO_DIRECTION = [
    (80, "强烈看多", "📈"),
    (60, "偏多", "📈"),
    (40, "中性/震荡", "📊"),
    (20, "偏空", "📉"),
    (0,  "强烈看空", "📉"),
]

# 置信度阈值
CONFIDENCE_HIGH = 75    # 高置信度
CONFIDENCE_MID = 50     # 中置信度（低于此为低）

# ============================================================
# 回测/交易参数（A股）
# ============================================================
TRADE_PARAMS = {
    "commission": 0.00025,   # 佣金万2.5
    "stamp_tax": 0.001,      # 印花税千1（仅卖出）
    "slippage": 0.001,       # 滑点千1
    "t_plus_1": True,        # T+1制度
    "limit_up_down": {       # 涨跌停幅度
        "main": 0.10,        # 主板
        "gem": 0.20,         # 创业板/科创板
        "bse": 0.30,         # 北交所
        "st": 0.05,          # ST
    },
}

# ============================================================
# 日志配置
# ============================================================
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    "file": str(LOG_DIR / "quant.log"),
    "max_bytes": 10 * 1024 * 1024,  # 10MB
}
