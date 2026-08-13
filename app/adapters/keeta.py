"""
Keeta 外卖平台订单导出适配器

源文件特征:
- 单 sheet，每行是一笔订单（不是聚合后的菜品）
- 列: 订单号, 门店名称, 门店ID, 订单状态, ... 商品, 实收金额, ...
- 「商品」列含该笔订单的所有菜品，用 ; 分隔
- 无单品价格，只有订单总金额

处理逻辑:
1. 只保留「已完成」的订单
2. 拆分「商品」列，提取每个菜名
3. 同一订单内多个菜品均分订单金额（近似单品收入）
4. 按菜名聚合：同名菜的数量和金额求和
5. 「订单状态」=「已完成」
"""
import re
import pandas as pd

from .base import PosAdapter, read_xlsx


# Keeta 导出的列索引（基于常见格式）
COL_IDX = {
    '订单号': 0,
    '商品': 8,
    '实收金额': 9,
    '订单状态': 3,
}

# 只处理「已完成」的订单
_COMPLETED_STATUS = '已完成'

# 商品分隔符
_ITEM_SEP = ';'

# 清理菜名：去掉首尾空白、括号内的注释信息
_CLEAN_PATTERNS = [
    (r'\s*\(.*?\)\s*$', ''),   # 行尾括号注释
    (r'\s*（.*?）\s*$', ''),    # 行尾括号注释(中文)
    (r'^\s*', ''),              # 行首空白
    (r'\s*$', ''),              # 行尾空白
]


def _parse_items(cell: str) -> list:
    """拆分商品列，返回菜品名列表"""
    items = str(cell).split(_ITEM_SEP)
    result = []
    for item in items:
        name = item.strip()
        if not name or name == 'nan':
            continue
        # 应用清理规则
        for pattern, replacement in _CLEAN_PATTERNS:
            name = re.sub(pattern, replacement, name)
        name = name.strip()
        if name:
            result.append(name)
    return result


def _is_completed(status) -> bool:
    """判断订单是否已完成"""
    return str(status).strip() == _COMPLETED_STATUS


class KeetaAdapter(PosAdapter):
    NAME = 'Keeta'
    KEY = 'keeta'

    def load(self, file_obj):
        df = read_xlsx(file_obj, header=0)
        return self._transform(df)

    @staticmethod
    def _parse_amount(val) -> float:
        """解析金额：去掉 $, HK$, ¥ 等前缀，转 float"""
        try:
            s = str(val).strip()
            s = s.replace('$', '').replace('HK$', '').replace('¥', '').replace(',', '')
            return float(s)
        except (ValueError, TypeError):
            return 0.0

    def _transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """转换 Keeta 数据为标准 4 列"""
        # 1. 只保留已完成订单
        status_col = df.columns[COL_IDX['订单状态']]
        completed = df[df[status_col].apply(_is_completed)].copy()
        if completed.empty:
            return pd.DataFrame(columns=['项目名称', '分类', '数量', '金额'])

        # 2. 提取商品和金额
        items_col = df.columns[COL_IDX['商品']]
        amt_col = df.columns[COL_IDX['实收金额']]

        # 3. 逐行拆分
        rows = []
        for _, row in completed.iterrows():
            items = _parse_items(row[items_col])
            total_amt = self._parse_amount(row[amt_col])
            if total_amt <= 0:
                continue
            if not items:
                continue

            # 同一订单内多个菜品均分金额
            per_item_amt = round(total_amt / len(items), 2)
            for item_name in items:
                rows.append({
                    '项目名称': item_name,
                    '分类': 'Keeta 外卖',
                    '数量': 1,
                    '金额': per_item_amt,
                })

        if not rows:
            return pd.DataFrame(columns=['项目名称', '分类', '数量', '金额'])

        # 4. 按菜名聚合
        agg_df = pd.DataFrame(rows)
        result = agg_df.groupby('项目名称', as_index=False).agg(
            数量=('数量', 'sum'),
            金额=('金额', 'sum'),
        )
        result['分类'] = 'Keeta 外卖'

        return self._check(result[['项目名称', '分类', '数量', '金额']])
