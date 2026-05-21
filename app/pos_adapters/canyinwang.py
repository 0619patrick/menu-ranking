"""
餐飲王 POS 适配器

源文件特征:
- 单 sheet
- 表头在第 1 行
- 列: 项目编码 | 项目名称 | 分类 | 部门 | 价格 | 金额 | 数量 | 改码 | 跟餐项目
- 每条记录 = 某商品在某分类下的合计（不是逐笔订单）
"""
import pandas as pd

from .base import PosAdapter


class CanyinwangAdapter(PosAdapter):
    NAME = '餐飲王'
    KEY = 'canyinwang'

    def load(self, file_obj):
        df = pd.read_excel(file_obj).dropna(subset=['项目名称'])
        df['项目名称'] = df['项目名称'].astype(str).str.strip()
        df['分类'] = df['分类'].astype(str)
        df['数量'] = pd.to_numeric(df['数量'], errors='coerce').fillna(0).astype(int)
        df['金额'] = pd.to_numeric(df['金额'], errors='coerce').fillna(0)
        return self._check(df)
