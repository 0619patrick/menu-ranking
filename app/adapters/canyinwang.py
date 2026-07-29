"""
餐飲王 POS 适配器
"""
import pandas as pd

from .base import PosAdapter, read_xlsx


TW_TO_CN_COLS = {
    '項目編碼': '项目编码',
    '項目名稱': '项目名称',
    '分類':     '分类',
    '部門':     '部门',
    '價格':     '价格',
    '金額':     '金额',
    '數量':     '数量',
    '改碼':     '改码',
    '跟餐項目': '跟餐项目',
}


class CanyinwangAdapter(PosAdapter):
    NAME = '餐飲王'
    KEY = 'canyinwang'

    def load(self, file_obj):
        df = read_xlsx(file_obj)
        df = df.rename(columns=TW_TO_CN_COLS)
        df = df.dropna(subset=['项目名称'])
        df['项目名称'] = df['项目名称'].astype(str).str.strip()
        df['分类'] = df['分类'].astype(str)
        df['数量'] = pd.to_numeric(df['数量'], errors='coerce').fillna(0).astype(int)
        df['金额'] = pd.to_numeric(df['金额'], errors='coerce').fillna(0)
        return self._check(df)
