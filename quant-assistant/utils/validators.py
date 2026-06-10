"""
股票代码校验与标准化
"""
import re


# 交易所前缀映射
EXCHANGE_PREFIX = {
    "sh": "上海",
    "sz": "深圳",
    "bj": "北京",
}


def normalize_code(raw: str) -> str:
    """
    标准化股票代码
    支持: 600519, sh600519, 600519.SH, 贵州茅台 等
    返回: sh600519 / sz000858 / bj830799
    """
    raw = raw.strip().upper()

    # 纯数字
    if re.match(r"^\d{6}$", raw):
        code = raw
    # sh/sz/bj + 6位数字
    elif re.match(r"^(SH|SZ|BJ)\d{6}$", raw):
        code = raw[2:]
        prefix = raw[:2].lower()
        return f"{prefix}{code}"
    # 6位数字.SH/SZ/BJ
    elif re.match(r"^\d{6}\.(SH|SZ|BJ)$", raw):
        code, prefix = raw.split(".")
        return f"{prefix.lower()}{code}"
    # 提取6位数字
    else:
        m = re.search(r"\d{6}", raw)
        if m:
            code = m.group()
        else:
            return raw  # 可能是名称，保持原样

    # 根据代码判断交易所
    if code.startswith(("60", "68")):
        return f"sh{code}"
    elif code.startswith(("00", "30", "002", "003")):
        return f"sz{code}"
    elif code.startswith(("8", "4")):
        return f"bj{code}"
    else:
        return f"sz{code}"  # 默认深圳


def split_code(normalized: str) -> tuple:
    """拆分为(市场, 代码)"""
    if len(normalized) >= 8:
        return normalized[:2], normalized[2:]
    return "", normalized


def get_market(normalized: str) -> str:
    """获取市场: sh/sz/bj"""
    prefix, _ = split_code(normalized)
    return prefix


def get_mootdx_code(normalized: str) -> str:
    """转为 mootdx 格式: 市场代码 (如 600519 对应 sh -> 1)"""
    prefix, code = split_code(normalized)
    market_map = {"sh": 1, "sz": 0, "bj": 0}
    return code, market_map.get(prefix, 0)


def get_tencent_code(normalized: str) -> str:
    """转为腾讯财经格式: sh600519"""
    return normalized


def is_valid(normalized: str) -> bool:
    """检查是否为合法股票代码格式"""
    return bool(re.match(r"^(sh|sz|bj)\d{6}$", normalized))


def is_st_stock(normalized: str) -> bool:
    """判断是否为ST股票（简单规则：代码判断）"""
    # ST股票需要从名称判断，这里仅做格式校验
    return False  # 由数据层判断
