# 🔬 A股量化分析助手

基于五层数据 + 多因子打分模型的A股综合研判工具。

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动Web界面
```bash
streamlit run run.py
```
浏览器自动打开 → 输入股票代码 → 查看分析结果

### 3. CLI分析
```bash
# 完整分析（Markdown报告）
python run.py analyze 600519

# 快速分析
python run.py analyze 600519 --fast

# 简短摘要
python run.py brief 000858
```

## 数据层级

| 层级 | 主数据源 | 备用数据源 |
|------|---------|-----------|
| 📈 行情层 | mootdx (通达信) | 腾讯财经 |
| 📋 研报层 | 东方财富 | akshare / iwencai |
| 📰 新闻层 | akshare | — |
| 📊 基础数据层 | mootdx | akshare |
| 📝 公告层 | 巨潮资讯网 | mootdx |

## 分析框架

### 四维因子体系

| 维度 | 默认权重 | 核心指标 |
|------|---------|---------|
| 技术面 | 30% | 均线排列、量价关系、RSI、价格位置 |
| 基本面 | 25% | ROE、PE/PB分位、毛利率、EPS |
| 情绪面 | 25% | 新闻情绪、分析师评级、目标价空间 |
| 事件面 | 20% | 公告重要性、重大事项、减持/增持 |

### 评分规则
- 0-100 分制，50分为中性
- 80-100: 强烈看多 | 60-80: 偏多 | 40-60: 中性 | 20-40: 偏空 | 0-20: 强烈看空
- 置信度基于信号一致性、数据完整度和预测强度

## Claude Code Skill

在Claude Code中分析股票：
```bash
python skill/analyze_stock.py 600519
```

## 项目结构
```
quant-assistant/
├── run.py              # 启动入口
├── config.py           # 全局配置
├── data/               # 五层数据采集
│   ├── market_data.py
│   ├── research_data.py
│   ├── news_data.py
│   ├── fundamental_data.py
│   ├── announcement_data.py
│   └── merger.py
├── analysis/           # 分析引擎
│   ├── features.py
│   ├── factors.py
│   ├── weights.py
│   ├── predictor.py
│   └── evidence.py
├── app/                # Streamlit Web
│   ├── main.py
│   └── components/
├── skill/              # Claude Code Skill
│   └── analyze_stock.py
└── utils/              # 工具
    ├── cache.py
    ├── logger.py
    └── validators.py
```

## 免责声明
⚠️ 本工具所有分析结果仅供参考，不构成投资建议。股市有风险，投资需谨慎。
