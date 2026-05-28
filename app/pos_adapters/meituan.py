"""
美團 POS 适配器（第 2 种 POS，继餐飲王之后）

源文件特征:
- 两个 sheet: 「已销售」「退菜」
  - 只读「已销售」，退菜整张忽略（金额已归零，对数字零贡献，详见 spec 第 4 节）
- 已销售表头在**第 3 行**（前 2 行是标题和筛选条件，header=2）
- 32 列，关键列名:
    菜品名称, 菜品大类, 菜品小类, 规格,
    销售数量, 销售额(元), 菜品优惠(元), 菜品收入(元), 标记
- 每条记录 = 一笔订单里的一道菜（粒度细，需要按菜聚合）
- 末尾常有 1 行「合计」行: 菜品名称=NaN, 大类=NaN, 销售数量=总数, 必须 drop
- 「标记」列值: 改/套/改、套/NaN，不做筛选（套餐 sub-item 的 ¥0 行随聚合）
- 金额必须用「菜品收入(元)」（= 销售额 − 菜品优惠 = 实收）
- 外卖识别:
    菜品名称 含「（外賣）」前缀  OR  菜品大类 == '外賣'
  与餐飲王的 KT/FP 不同，由菜单 DELIVERY_PLATFORMS 加 '外賣' marker 兼容
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
        # 表头在第 3 行（index=2），只读「已销售」sheet
        # read_xlsx 自动用 calamine(Rust, 5-10× 加速), 不可用时 fallback openpyxl
        df = read_xlsx(file_obj, sheet_name='已销售', header=2)

        # 删除合计行（菜品名称 / 大类 任一为空）
        df = df.dropna(subset=['菜品名称'])

        # 清洗
        df['菜品名称'] = df['菜品名称'].astype(str).str.strip()
        df['菜品大类'] = df['菜品大类'].fillna('未分类').astype(str).str.strip()
        df['规格']     = df['规格'].fillna('').astype(str).str.strip()
        df['销售数量'] = pd.to_numeric(df['销售数量'], errors='coerce').fillna(0)
        df['菜品收入（元）'] = pd.to_numeric(df['菜品收入（元）'], errors='coerce').fillna(0)

        # ⭐ 按 (大类, 菜名, 规格) 聚合（餐飲王不需要这步）
        # 规格不同 = 不同菜品（如「天天海南雞」中份/大份），不要合并
        agg = df.groupby(['菜品大类', '菜品名称', '规格'],
                         as_index=False, dropna=False).agg(
            销售数量=('销售数量', 'sum'),
            菜品收入=('菜品收入（元）', 'sum'),
        )

        # 把 规格 拼到菜名后（让菜名能跟天天菜单的「(中份)/(大份)」匹配）
        # 仅当 POS 菜名本身不含规格信息时拼；菜名带括号一般已含
        # 实测美團大量菜名（茶位/前菜小食/飲品）本来就不需要规格区分（规格是「份/碗/杯」），
        # 暂时不拼。如果之后某些菜要靠规格分辨，再在菜单里补变体名。

        # 重命名到标准列
        agg = agg.rename(columns={
            '菜品名称': '项目名称',
            '菜品大类': '分类',
            '销售数量': '数量',
            '菜品收入': '金额',
        })

        # 数量取整，金额保留两位
        agg['数量'] = agg['数量'].astype(int)
        agg['金额'] = agg['金额'].round(2)

        # 丢弃规格列（标准化为 4 列：项目名称 / 分类 / 数量 / 金额）
        return self._check(agg)
