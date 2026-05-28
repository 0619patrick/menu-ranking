"""
餐飲王 POS 适配器

源文件特征:
- 单 sheet
- 表头在第 1 行
- 列: 项目编码 | 项目名称 | 分类 | 部门 | 价格 | 金额 | 数量 | 改码 | 跟餐项目
  （部分门店导出用繁体列名: 項目編碼/項目名稱/分類/部門/價格/金額/數量/改碼/跟餐項目，
   本适配器读到繁体会自动归一到简体）
- 每条记录 = 某商品在某分类下的合计（不是逐笔订单）
"""
import pandas as pd

from .base import PosAdapter, read_xlsx


# 繁体列名 → 简体列名（部分门店餐飲王导出用繁体表头，如香港阿城 3 月）
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
        # read_xlsx 自动用 calamine 引擎(Rust, 比 openpyxl 快 5-10 倍), 不可用时 fallback openpyxl
        df = read_xlsx(file_obj)
        # 列名繁→简归一（如果文件用繁体表头）
        df = df.rename(columns=TW_TO_CN_COLS)
        df = df.dropna(subset=['项目名称'])
        df['项目名称'] = df['项目名称'].astype(str).str.strip()
        df['分类'] = df['分类'].astype(str)
        df['数量'] = pd.to_numeric(df['数量'], errors='coerce').fillna(0).astype(int)
        df['金额'] = pd.to_numeric(df['金额'], errors='coerce').fillna(0)
        return self._check(df)
