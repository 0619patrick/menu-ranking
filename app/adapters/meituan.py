"""
美團 POS 适配器
"""
import pandas as pd

from .base import PosAdapter, read_xlsx


COLUMN_MAP = {
    '菜品名称':       '项目名称',
    '菜品大类':       '分类',
    '销售数量':       '数量',
    '菜品收入（元）': '金额',
}


class MeituanAdapter(PosAdapter):
    NAME = '美團'
    KEY = 'meituan'

    def load(self, file_obj):
        df = read_xlsx(file_obj, sheet_name='已销售', header=2)
        df = df.dropna(subset=['菜品名称'])
        df['菜品名称'] = df['菜品名称'].astype(str).str.strip()
        df['菜品大类'] = df['菜品大类'].fillna('未分类').astype(str).str.strip()
        df['规格'] = df['规格'].fillna('').astype(str).str.strip()
        df['销售数量'] = pd.to_numeric(df['销售数量'], errors='coerce').fillna(0)
        df['菜品收入（元）'] = pd.to_numeric(df['菜品收入（元）'], errors='coerce').fillna(0)

        agg = df.groupby(['菜品大类', '菜品名称', '规格'],
                         as_index=False, dropna=False).agg(
            销售数量=('销售数量', 'sum'),
            菜品收入=('菜品收入（元）', 'sum'),
        )

        agg = agg.rename(columns={
            '菜品名称': '项目名称',
            '菜品大类': '分类',
            '销售数量': '数量',
            '菜品收入': '金额',
        })
        agg['数量'] = agg['数量'].astype(int)
        agg['金额'] = agg['金额'].round(2)
        return self._check(agg)
