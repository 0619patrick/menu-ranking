"""
美團 POS 适配器

支持两种美团导出格式：
1. 报表中心「已销售」明细（sheet='已销售'）—— 旧格式
   列: 菜品名称 / 菜品大类 / 销售数量 / 菜品收入（元）
2. 报表中心「品项销售明细」（sheet='品项销售明细'）—— 新格式（鮨政等）
   列: 品项名称 / 菜品大类 / 销售数量 / 退菜数量 / 销售金额(元) / 退菜金额(元)
   口径: 净数量 = 销售数量 - 退菜数量；净金额 = 销售金额(元) - 退菜金额(元)
"""
import pandas as pd

from .base import PosAdapter, read_xlsx


class MeituanAdapter(PosAdapter):
    NAME = '美團'
    KEY = 'meituan'

    def load(self, file_obj):
        sheets = self._sheet_names(file_obj)
        if '已销售' in sheets:
            return self._load_sold_sheet(file_obj)
        if '品项销售明细' in sheets:
            return self._load_item_detail_sheet(file_obj)
        # 兼容：文件只有一个 sheet 且表头含「品项名称」时按新格式处理
        first = sheets[0] if sheets else None
        if first:
            probe = read_xlsx(file_obj, sheet_name=first, header=2, nrows=1)
            if '品项名称' in probe.columns:
                return self._load_item_detail_sheet(file_obj, sheet=first)
        raise ValueError(
            f'美团导出文件未识别：sheet={sheets}，期望「已销售」或「品项销售明细」')

    @staticmethod
    def _sheet_names(file_obj):
        import openpyxl
        file_obj.seek(0)
        wb = openpyxl.load_workbook(file_obj, read_only=True)
        try:
            return wb.sheetnames
        finally:
            wb.close()
            file_obj.seek(0)

    def _load_sold_sheet(self, file_obj):
        """旧格式：报表中心「已销售」"""
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

    def _load_item_detail_sheet(self, file_obj, sheet='品项销售明细'):
        """新格式：报表中心「品项销售明细」（含退菜/赠送列，需净口径）"""
        df = read_xlsx(file_obj, sheet_name=sheet, header=2)
        # 排除「合计」行
        if '营业日期' in df.columns:
            df = df[df['营业日期'] != '合计'].copy()

        # 列名兼容（全角/半角括号差异）
        col_map = {}
        for c in df.columns:
            if c == '品项名称':
                col_map['品项名称'] = '品项名称'
            elif c == '菜品大类':
                col_map['菜品大类'] = '菜品大类'

        df = df.dropna(subset=['品项名称'])
        df['品项名称'] = df['品项名称'].astype(str).str.strip()
        df['菜品大类'] = df['菜品大类'].fillna('未分类').astype(str).str.strip()

        sold = self._num(df, '销售数量')
        refund = self._num(df, '退菜数量')
        amt_sold = self._num(df, '销售金额(元)', '销售金额（元）')
        amt_refund = self._num(df, '退菜金额(元)', '退菜金额（元）')

        df['数量'] = sold - refund
        df['金额'] = amt_sold - amt_refund

        agg = df.groupby(['菜品大类', '品项名称'], as_index=False, dropna=False).agg(
            数量=('数量', 'sum'),
            金额=('金额', 'sum'),
        )
        agg = agg.rename(columns={'品项名称': '项目名称', '菜品大类': '分类'})
        agg['数量'] = agg['数量'].astype(int)
        agg['金额'] = agg['金额'].round(2)
        return self._check(agg)

    @staticmethod
    def _num(df, *names):
        for n in names:
            if n in df.columns:
                return pd.to_numeric(df[n], errors='coerce').fillna(0)
        raise ValueError(f'美团导出缺少数量/金额列: 期望 {names[0]}')
