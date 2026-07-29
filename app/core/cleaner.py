"""
AI 数据清洗层

将 POS API 返回的原始 JSON 数据自动清洗为标准 4 列 DataFrame。
支持自动识别不同字段名（中英文、繁简体）、类型转换、异常过滤。

第一阶段：规则映射（基于已知字段名模式）
后续可升级：接入 LLM 做模糊匹配和异常语义理解
"""
import logging
import pandas as pd

logger = logging.getLogger(__name__)

STANDARD_COLUMNS = ['项目名称', '分类', '数量', '金额']

# 字段名映射字典：标准列名 → 可能的源字段名集合
# 覆盖中英文、繁简体、常见命名风格
_FIELD_ALIASES = {
    '项目名称': {
        '项目名称', '項目名稱', '菜品名称', '菜名', 'dish_name', 'dishName',
        'name', 'item_name', 'itemName', 'product_name', 'productName',
        'dish', 'item',
    },
    '分类': {
        '分类', '分類', '菜品大类', '大类', '大類', '菜品小类',
        'cat', 'category', 'category_name', 'categoryName',
        'department', 'dept',
    },
    '数量': {
        '数量', '數量', '销售数量', '銷售數量', '销量',
        'qty', 'quantity', 'count', 'num', 'sales_qty', 'salesQuantity',
    },
    '金额': {
        '金额', '金額', '实收金额', '實收金額', '销售额', '銷售額',
        '菜品收入', 'amount', 'total', 'price', 'revenue',
        'sales_amount', 'salesAmount', 'amt', 'total_amount',
    },
}

# 时间字段（自动识别的别名，用于时间范围校验）
_DATE_ALIASES = {'date', '日期', '日', 'sale_date', 'saleDate', 'business_date', 'businessDate',
                 'start_date', 'startDate', 'end_date', 'endDate'}

# 店铺字段别名
_SHOP_ALIASES = {'shop_id', 'shopId', 'store_id', 'storeId', '门店', '门店编号',
                 'shop_name', 'shopName', 'store_name', 'storeName', '门店名称'}


def _detect_field(data: dict, standard_field: str) -> str:
    """在 data 中查找能匹配 standard_field 的键名"""
    data_keys = set(data.keys())
    aliases = _FIELD_ALIASES[standard_field]
    matched = data_keys & aliases
    if matched:
        return matched.pop()
    # 不区分大小写再试一次
    lower_keys = {k.lower(): k for k in data.keys()}
    for alias in aliases:
        if alias.lower() in lower_keys:
            return lower_keys[alias.lower()]
    return None


def _detect_records(data: dict) -> list:
    """
    自动定位数据记录列表。
    支持常见结构：
      - { "items": [...] }
      - { "data": [...] }
      - { "records": [...] }
      - { "list": [...] }
      - { "results": [...] }
      - 直接顶层数组
    """
    for key in ('items', 'data', 'records', 'list', 'results', 'sales', 'rows'):
        if key in data and isinstance(data[key], list):
            return data[key]
    # 检查是否有任何值是列表且长度 > 0
    for v in data.values():
        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
            return v
    return []


def clean_raw_data(raw_data: dict, pos_type: str = None) -> pd.DataFrame:
    """
    清洗 POS API 返回的原始数据，输出标准 4 列 DataFrame。

    流程:
    1. 自动定位记录列表（支持常见嵌套结构）
    2. 自动识别字段名（中/英/繁 多种别名）
    3. 类型转换（字符串数字 → int/float）
    4. 异常值过滤
    5. 输出标准 4 列

    参数:
        raw_data: POS API 返回的原始 JSON 字典
        pos_type: POS 类型（预留，后续可用于加载特定 POS 的字段映射规则）

    返回:
        pd.DataFrame: 包含 [项目名称, 分类, 数量, 金额] 4 列
    """
    records = _detect_records(raw_data)

    if not records:
        logger.warning('清洗数据未找到有效记录 (pos=%s)', pos_type)
        return pd.DataFrame(columns=STANDARD_COLUMNS)

    logger.info('清洗 POS 数据: pos=%s, 原始记录数=%d', pos_type, len(records))

    # 用第一条记录检测字段映射
    field_map = {}
    for std_col in STANDARD_COLUMNS:
        src = _detect_field(records[0], std_col)
        if src:
            field_map[std_col] = src

    # 如果没找到任何字段，尝试直接使用标准列名
    if not field_map:
        logger.warning('未检测到已知字段名，尝试直接使用标准列名 (pos=%s)', pos_type)
        for std_col in STANDARD_COLUMNS:
            if std_col in records[0]:
                field_map[std_col] = std_col

    if not field_map:
        logger.error('无法映射字段，原始数据字段: %s', list(records[0].keys()) if records else [])
        raise ValueError(
            f'无法从 POS 数据中识别标准字段。'
            f'原始字段: {list(records[0].keys()) if records else "无数据"}。'
            f'参考 docs/POS_API_接口规范.md 调整数据结构。'
        )

    # 提取数据
    rows = []
    for i, rec in enumerate(records):
        try:
            row = {}
            for std_col, src_key in field_map.items():
                val = rec.get(src_key)
                if val is None:
                    # 尝试从嵌套结构中获取
                    for src_candidates in rec.values():
                        if isinstance(src_candidates, dict) and src_key in src_candidates:
                            val = src_candidates[src_key]
                            break
                row[std_col] = val

            # 类型转换
            name = str(row.get('项目名称', '') or '').strip()
            cat = str(row.get('分类', '') or '').strip()

            # 数量：转 int
            qty = row.get('数量')
            if qty is None:
                qty = 0
            try:
                qty = int(float(str(qty)))
            except (ValueError, TypeError):
                qty = 0

            # 金额：转 float
            amt = row.get('金额')
            if amt is None:
                amt = 0.0
            try:
                amt = float(str(amt))
            except (ValueError, TypeError):
                amt = 0.0

            # 过滤空名称的行
            if not name:
                continue

            rows.append({'项目名称': name, '分类': cat, '数量': qty, '金额': amt})

        except Exception as e:
            logger.debug('清洗第 %d 条记录出错: %s', i, e)
            continue

    df = pd.DataFrame(rows, columns=STANDARD_COLUMNS)
    logger.info('清洗完成: pos=%s, 有效记录=%d', pos_type, len(df))
    return df


def detect_data_summary(raw_data: dict) -> dict:
    """
    检测数据的基本信息（用于前端展示）。
    不尝试完整清洗，只做快速检测。
    """
    records = _detect_records(raw_data)
    if not records:
        return {'record_count': 0, 'detected_fields': [], 'sample': None}

    sample = records[0] if records else {}
    detected = {}
    for std_col in STANDARD_COLUMNS:
        src = _detect_field(sample, std_col)
        if src:
            detected[std_col] = src

    return {
        'record_count': len(records),
        'detected_fields': detected,
        'sample': {k: v for k, v in list(sample.items())[:6]},
    }
