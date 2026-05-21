"""
数据处理核心:
1. 通过 POS 适配器读取源数据 → 标准 4 列 DataFrame
2. 按指定餐厅的菜单分类填充堂食销量（排除 KT/FP）
3. 把 KT/FP 项目单独整理成外卖区（自取分上下）
4. 生成左右并列的 Excel 对照表

不再关心源数据是哪个 POS 系统、属于哪类餐厅——
全部由 (restaurant_type, pos_type) 路由到对应的 menu / adapter。
"""
import io
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

from app.pos_adapters import get_adapter
from app.menus import get_menu
from app.menus.base import Menu


# ============= 样式 =============
BLUE = PatternFill('solid', fgColor='FF8DB4E2')
LIGHT_BLUE = PatternFill('solid', fgColor='FFDAEEF3')
YELLOW = PatternFill('solid', fgColor='FFFFFF00')
GRAY_HEADER = PatternFill('solid', fgColor='FFA6A6A6')
LIGHT_GRAY = PatternFill('solid', fgColor='FFE7E6E6')
F2_GRAY = PatternFill('solid', fgColor='FFF2F2F2')
DELIVERY_BG = PatternFill('solid', fgColor='FFFFF2CC')

FONT_TITLE = Font(name='宋体', size=14, bold=True)
FONT_HEADER = Font(name='宋体', size=11, bold=True)
FONT_SECTION = Font(name='宋体', size=10, bold=True)
FONT_SECTION_W = Font(name='宋体', size=10, bold=True, color='FFFFFFFF')
FONT_CAT = Font(name='宋体', size=11)
FONT_DATA = Font(name='宋体', size=10)
FONT_EXTRA = Font(name='宋体', size=10, color='FF666666', italic=True)

CENTER = Alignment(horizontal='center', vertical='center')
LEFT = Alignment(horizontal='left', vertical='center')

_thin = Side(border_style='thin', color='FFBFBFBF')
BORDER = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)


# ============= 数据加载 =============

def load_source(file_obj, pos_type: str) -> pd.DataFrame:
    """通过指定 POS 适配器加载源数据，返回标准 4 列 DataFrame"""
    adapter = get_adapter(pos_type)
    return adapter.load(file_obj)


def apply_deletions(src: pd.DataFrame, deletions) -> pd.DataFrame:
    """
    用户在前端 ▶ 里点 × 删掉的行，从源数据里剔除后再交给后续逻辑。

    deletions: list of {'name': POS项目名, 'cat': 分类}
    """
    if not deletions:
        return src
    keys = {(d.get('name'), d.get('cat')) for d in deletions}
    if not keys:
        return src
    mask = [(n, c) not in keys
            for n, c in zip(src['项目名称'].values, src['分类'].values)]
    return src[mask]


# ============= 通用聚合（不依赖菜单） =============

def precompute_dinein_by_name(src):
    """
    一次性把堂食（排除 KT/FP）的数据按 (项目名称, 分类) 预聚合好，
    返回 dict: { POS项目名: [(分类, qty, amt), ...] }

    所有 get_dinein_sales / get_dinein_sales_detail / build_dinein_extras
    都基于这个 dict 查询，把过去 O(N×K) 的全表过滤变成 O(K) 的字典查找。
    """
    dinein = src[~src['分类'].str.contains('KT|FP', na=False, regex=True)]
    if dinein.empty:
        return {}
    agg = dinein.groupby(['项目名称', '分类'], as_index=False).agg(
        数量=('数量', 'sum'), 金额=('金额', 'sum')
    )
    by_name = {}
    for name, cat, q, a in zip(agg['项目名称'], agg['分类'], agg['数量'], agg['金额']):
        by_name.setdefault(name, []).append((cat, int(q), int(a)))
    return by_name


def get_dinein_sales(name_list, by_name):
    """加总指定 POS 名列表的堂食 (数量, 金额)。O(K) 字典查找。"""
    q = a = 0
    for n in name_list:
        for _cat, qty, amt in by_name.get(n, ()):
            q += qty
            a += amt
    return q, a


def get_dinein_sales_detail(name_list, by_name):
    """
    返回 (total_qty, total_amt, variants)，按 (POS项目名, 分类) 拆。

    同名跨分类（例如「鮮椰子水」既在「飲品」也在套餐拆解分类「ODO飲品(不能撞餐)」）
    会拆成多条 variant，给前端 ▶ 展开用。
    """
    variants = []
    for n in name_list:
        for cat, qty, amt in by_name.get(n, ()):
            if qty == 0 and amt == 0:
                continue
            variants.append({'name': n, 'cat': cat, 'qty': qty, 'amt': amt})
    # 金额降序；同金额按数量降序
    variants.sort(key=lambda v: (-v['amt'], -v['qty']))
    return (
        sum(v['qty'] for v in variants),
        sum(v['amt'] for v in variants),
        variants,
    )


def build_dinein_extras(by_name, used_names, drop_categories):
    """
    收集堂食「菜單外」的项目（POS 有销售但菜单未列出的）。
    从 by_name 中过滤掉已被菜单引用的 POS 名 + 要丢弃的辅助分类。
    """
    extras = {}
    for name, rows in by_name.items():
        if name in used_names:
            continue
        for cat, q, a in rows:
            if cat in drop_categories:
                continue
            if q == 0 and a == 0:
                continue
            extras.setdefault(cat, []).append((name, q, a))
    for c in extras:
        extras[c].sort(key=lambda x: -x[2])
    return extras


def build_delivery(src, menu: Menu):
    """
    收集所有 KT/FP 分类的项目, 按分类组织。

    属于同一道菜单菜品的多个 POS 写法（例如「天天海南雞 （中）」「招牌天天海南雞(中份)」）
    会在同一 KT 子分类内合并到该菜的标准显示名下；
    每行带 'merged' 字段：≥2 个 POS 变体时记录原始拆分（前端会显示 ▶ 展开）。

    返回结构: { 'KT 子分类名': [ {name, qty, amt, merged: [{name,qty,amt}, ...]}, ... ] }
    """
    delivery = src[src['分类'].str.contains('KT|FP', na=False, regex=True)]
    if delivery.empty:
        return {}

    # 反向映射: POS 项目名 → 菜单标准菜名
    pos_to_dish = {}
    for _cat, items in menu.items:
        for dish_name, _p, _u, pos_names in items:
            for pn in pos_names:
                pos_to_dish[pn] = dish_name

    by_cat = {}
    for kt_cat, sub in delivery.groupby('分类'):
        # 同 KT 子分类内: 按 (菜单标准名 or 自身) 分组, 再按 POS 名累加
        groups = {}   # display_key → { pos_name → [qty, amt] }
        for _, r in sub.iterrows():
            q = int(r['数量']); a = int(r['金额'])
            if q == 0 and a == 0:
                continue
            pn = r['项目名称']
            display_key = pos_to_dish.get(pn, pn)
            inner = groups.setdefault(display_key, {})
            if pn in inner:
                inner[pn][0] += q
                inner[pn][1] += a
            else:
                inner[pn] = [q, a]

        rows = []
        for display_key, by_pn in groups.items():
            variants = [{'name': pn, 'qty': q, 'amt': a}
                        for pn, (q, a) in by_pn.items()]
            total_q = sum(v['qty'] for v in variants)
            total_a = sum(v['amt'] for v in variants)
            if len(variants) >= 2:
                # 真正发生合并: 用菜单标准名, 保留变体明细
                display_name = display_key
                merged = variants
            else:
                # 单一 POS 名: 保留原始写法, 不显示 ▶
                display_name = variants[0]['name']
                merged = []
            rows.append({
                'name':   display_name,
                'qty':    total_q,
                'amt':    total_a,
                'merged': merged,
            })

        rows.sort(key=lambda r: -r['amt'])
        by_cat[kt_cat] = rows
    return by_cat


# ============= Excel 输出 =============

def build_sheet(ws, shop_name, src, menu: Menu):
    """在 sheet 里建好该店的对照表"""

    # 取应用了门店补丁后的菜单
    items_patched = menu.items_for_store(shop_name)
    used_names = menu.collect_used_names(shop_name)

    # 一次性预聚合堂食数据；后面所有 get_dinein_sales 都从这里查
    by_name = precompute_dinein_by_name(src)

    # 列宽（堂食 B-G，删除了 單位 列；外賣 J-N 不变）
    widths = {
        'A': 2, 'B': 13, 'C': 4.5, 'D': 36, 'E': 8, 'F': 8, 'G': 10,
        'I': 2, 'J': 22, 'K': 4.5, 'L': 36, 'M': 8, 'N': 10
    }
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    # 行 1: 总标题
    ws.row_dimensions[1].height = 28
    ws.merge_cells('B1:N1')
    ws.cell(row=1, column=2, value=f'{menu.brand} × {shop_name} 銷量對照').font = FONT_TITLE
    ws.cell(row=1, column=2).alignment = CENTER
    for col in range(2, 15):
        ws.cell(row=1, column=col).fill = BLUE

    # 行 2: 区域标题
    ws.merge_cells('B2:G2')
    ws.cell(row=2, column=2, value='堂食 (按菜單分類)').font = FONT_HEADER
    ws.cell(row=2, column=2).alignment = CENTER
    for col in range(2, 8):
        ws.cell(row=2, column=col).fill = LIGHT_BLUE

    ws.merge_cells('J2:N2')
    ws.cell(row=2, column=10, value='外賣 (KT/FP分類)').font = FONT_SECTION_W
    ws.cell(row=2, column=10).alignment = CENTER
    for col in range(10, 15):
        ws.cell(row=2, column=col).fill = GRAY_HEADER

    # 行 3: 字段头
    dinein_headers = [('B', '分類'), ('C', '排序'), ('D', '品名'),
                      ('E', '菜單價'), ('F', '數量'), ('G', '金額')]
    for col_letter, h in dinein_headers:
        c = ws[f'{col_letter}3']
        c.value = h
        c.font = FONT_HEADER
        c.fill = BLUE
        c.alignment = CENTER
        c.border = BORDER

    delivery_headers = [('J', '外賣分類'), ('K', '排序'),
                        ('L', '品名'), ('M', '數量'), ('N', '金額')]
    for col_letter, h in delivery_headers:
        c = ws[f'{col_letter}3']
        c.value = h
        c.font = FONT_HEADER
        c.fill = GRAY_HEADER
        c.alignment = CENTER
        c.border = BORDER

    merge_ranges = []

    # ===== 写堂食区 =====
    def write_dinein_row(r, vals, fill=None, font=None):
        cols = [2, 3, 4, 5, 6, 7]   # B-G: 分類/排序/品名/菜單價/數量/金額
        for col, val in zip(cols, vals):
            c = ws.cell(row=r, column=col, value=val)
            if fill:
                c.fill = fill
            c.font = font if font else FONT_DATA
            c.alignment = LEFT if col == 4 else CENTER
            c.border = BORDER

    current_row_dinein = 4

    # 茶位
    tea_cat, tea_items = items_patched[0]
    for idx, (name, price, unit, pos_names) in enumerate(tea_items):
        q, a = get_dinein_sales(pos_names, by_name)
        write_dinein_row(current_row_dinein,
                         [tea_cat, idx+1, name, price, q, a],
                         fill=YELLOW, font=FONT_CAT if idx == 0 else FONT_DATA)
        current_row_dinein += 1

    # 大MENU 标题
    ws.merge_cells(start_row=current_row_dinein, start_column=2,
                   end_row=current_row_dinein, end_column=7)
    ws.cell(row=current_row_dinein, column=2, value='大MENU').font = FONT_SECTION
    ws.cell(row=current_row_dinein, column=2).alignment = CENTER
    for col in range(2, 8):
        ws.cell(row=current_row_dinein, column=col).fill = LIGHT_BLUE
        ws.cell(row=current_row_dinein, column=col).border = BORDER
    current_row_dinein += 1

    # 各分类(按金额降序)
    for cat, items in items_patched[1:]:
        items_with_sales = []
        for name, price, unit, pos_names in items:
            q, a = get_dinein_sales(pos_names, by_name)
            items_with_sales.append((name, price, unit, q, a))
        items_with_sales.sort(key=lambda x: -x[4])

        start = current_row_dinein
        for idx, (name, price, unit, q, a) in enumerate(items_with_sales):
            cat_val = cat if idx == 0 else ''
            font = FONT_CAT if idx == 0 else FONT_DATA
            write_dinein_row(current_row_dinein,
                             [cat_val, idx+1, name, price, q, a],
                             font=font)
            current_row_dinein += 1
        if len(items_with_sales) > 1:
            merge_ranges.append(f'B{start}:B{current_row_dinein-1}')
        current_row_dinein += 1  # 空一行

    # 堂食菜單外
    extras = build_dinein_extras(by_name, used_names, menu.drop_categories)
    if extras:
        for col in range(2, 8):
            ws.cell(row=current_row_dinein, column=col).fill = LIGHT_GRAY
            ws.cell(row=current_row_dinein, column=col).border = BORDER
        ws.merge_cells(start_row=current_row_dinein, start_column=2,
                       end_row=current_row_dinein, end_column=7)
        ws.cell(row=current_row_dinein, column=2,
                value='堂食菜單外（POS有銷售但菜單未列）').font = FONT_SECTION
        ws.cell(row=current_row_dinein, column=2).alignment = CENTER
        current_row_dinein += 1

        for src_cat in sorted(extras.keys(), key=lambda c: -sum(x[2] for x in extras[c])):
            items = extras[src_cat]
            start = current_row_dinein
            for idx, (name, q, a) in enumerate(items):
                cat_val = src_cat if idx == 0 else ''
                write_dinein_row(current_row_dinein,
                                 [cat_val, idx+1, name, '', q, a],
                                 fill=F2_GRAY, font=FONT_EXTRA)
                current_row_dinein += 1
            if len(items) > 1:
                merge_ranges.append(f'B{start}:B{current_row_dinein-1}')
            current_row_dinein += 1

    # ===== 写外卖区(右侧) =====
    def write_delivery_row(r, vals, font=None):
        cols = [10, 11, 12, 13, 14]
        for col, val in zip(cols, vals):
            c = ws.cell(row=r, column=col, value=val)
            c.fill = DELIVERY_BG
            c.font = font if font else FONT_DATA
            c.alignment = LEFT if col == 12 else CENTER
            c.border = BORDER

    delivery = build_delivery(src, menu)
    normal_cats = [c for c in delivery.keys() if '自取' not in c]
    self_take_cats = [c for c in delivery.keys() if '自取' in c]

    normal_kt = sorted([c for c in normal_cats if c.startswith('KT')],
                       key=lambda c: -sum(x['amt'] for x in delivery[c]))
    normal_fp = sorted([c for c in normal_cats if c.startswith('FP')],
                       key=lambda c: -sum(x['amt'] for x in delivery[c]))
    st_kt = sorted([c for c in self_take_cats if c.startswith('KT')],
                   key=lambda c: -sum(x['amt'] for x in delivery[c]))
    st_fp = sorted([c for c in self_take_cats if c.startswith('FP')],
                   key=lambda c: -sum(x['amt'] for x in delivery[c]))

    current_row_dlv = 4

    # 上半段: 普通
    for src_cat in normal_kt + normal_fp:
        items = delivery[src_cat]
        start = current_row_dlv
        for idx, item in enumerate(items):
            cat_val = src_cat if idx == 0 else ''
            font = FONT_CAT if idx == 0 else FONT_DATA
            write_delivery_row(current_row_dlv,
                               [cat_val, idx+1, item['name'], item['qty'], item['amt']],
                               font=font)
            current_row_dlv += 1
        if len(items) > 1:
            merge_ranges.append(f'J{start}:J{current_row_dlv-1}')
        current_row_dlv += 1

    # 分隔标题: 自取
    if st_kt or st_fp:
        for col in range(10, 15):
            ws.cell(row=current_row_dlv, column=col).fill = GRAY_HEADER
            ws.cell(row=current_row_dlv, column=col).border = BORDER
        ws.merge_cells(start_row=current_row_dlv, start_column=10,
                       end_row=current_row_dlv, end_column=14)
        ws.cell(row=current_row_dlv, column=10, value='─── 自取 ───').font = FONT_SECTION_W
        ws.cell(row=current_row_dlv, column=10).alignment = CENTER
        current_row_dlv += 1

    # 下半段: 自取
    for src_cat in st_kt + st_fp:
        items = delivery[src_cat]
        start = current_row_dlv
        for idx, item in enumerate(items):
            cat_val = src_cat if idx == 0 else ''
            font = FONT_CAT if idx == 0 else FONT_DATA
            write_delivery_row(current_row_dlv,
                               [cat_val, idx+1, item['name'], item['qty'], item['amt']],
                               font=font)
            current_row_dlv += 1
        if len(items) > 1:
            merge_ranges.append(f'J{start}:J{current_row_dlv-1}')
        current_row_dlv += 1

    # 应用合并
    for mr in merge_ranges:
        ws.merge_cells(mr)
        first_cell = mr.split(':')[0]
        ws[first_cell].alignment = CENTER


# ============= 预览数据（供前端 JS 渲染） =============

def build_preview_data(shop_name, src, menu: Menu):
    """构建预览用结构化数据（供前端渲染表格）"""
    items_patched = menu.items_for_store(shop_name)
    used_names = menu.collect_used_names(shop_name)

    # 一次性预聚合
    by_name = precompute_dinein_by_name(src)

    tea_cat, tea_items_raw = items_patched[0]
    tea_rows = []
    for name, price, unit, pos_names in tea_items_raw:
        q, a, variants = get_dinein_sales_detail(pos_names, by_name)
        tea_rows.append({'name': name, 'price': price, 'unit': unit,
                         'qty': q, 'amt': a,
                         'merged': variants if len(variants) > 1 else []})

    menu_sections = []
    for cat, items_raw in items_patched[1:]:
        rows = []
        for name, price, unit, pos_names in items_raw:
            q, a, variants = get_dinein_sales_detail(pos_names, by_name)
            rows.append({'name': name, 'price': price, 'unit': unit,
                         'qty': q, 'amt': a,
                         'merged': variants if len(variants) > 1 else []})
        rows.sort(key=lambda x: -x['amt'])
        menu_sections.append({'cat': cat, 'items': rows})

    extras = build_dinein_extras(by_name, used_names, menu.drop_categories)
    extras_sections = [
        {'cat': c, 'items': [{'name': n, 'qty': q, 'amt': a} for n, q, a in extras[c]]}
        for c in sorted(extras, key=lambda c: -sum(x[2] for x in extras[c]))
    ]

    delivery = build_delivery(src, menu)
    normal_cats = [c for c in delivery if '自取' not in c]
    self_take_cats = [c for c in delivery if '自取' in c]
    normal_kt = sorted([c for c in normal_cats if c.startswith('KT')],
                       key=lambda c: -sum(x['amt'] for x in delivery[c]))
    normal_fp = sorted([c for c in normal_cats if c.startswith('FP')],
                       key=lambda c: -sum(x['amt'] for x in delivery[c]))
    st_kt = sorted([c for c in self_take_cats if c.startswith('KT')],
                   key=lambda c: -sum(x['amt'] for x in delivery[c]))
    st_fp = sorted([c for c in self_take_cats if c.startswith('FP')],
                   key=lambda c: -sum(x['amt'] for x in delivery[c]))

    def dlv_section(cat):
        # 直接复用 build_delivery 返回的 dict（含 name/qty/amt/merged 4 个字段）
        return {'cat': cat, 'items': delivery[cat]}

    return {
        'shop_name': shop_name,
        'brand': menu.brand,
        'tea': tea_rows,
        'menu': menu_sections,
        'extras': extras_sections,
        'dlv_normal': [dlv_section(c) for c in normal_kt + normal_fp],
        'dlv_selftake': [dlv_section(c) for c in st_kt + st_fp],
    }


# ============= 入口函数 =============

def generate_excel(parsed_shops):
    """
    生成对照表 Excel

    parsed_shops: list of (shop_name: str, src: DataFrame, menu: Menu)
    返回: BytesIO 对象
    """
    wb = Workbook()
    wb.remove(wb.active)
    for shop_name, src, menu in parsed_shops:
        ws = wb.create_sheet(shop_name)
        build_sheet(ws, shop_name, src, menu)
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def compute_stats(src, menu: Menu, shop_name: str = None):
    """从已解析的 src + menu 算统计摘要。传 shop_name 让 STORE_OVERRIDES 生效。"""
    items_patched = menu.items_for_store(shop_name)
    used = menu.collect_used_names(shop_name)
    by_name = precompute_dinein_by_name(src)

    dinein_q = dinein_a = matched_items = 0
    for cat, items in items_patched:
        for name, price, unit, pos_names in items:
            q, a = get_dinein_sales(pos_names, by_name)
            dinein_q += q
            dinein_a += a
            if q > 0 or a > 0:
                matched_items += 1

    extras = build_dinein_extras(by_name, used, menu.drop_categories)
    extras_q = sum(x[1] for v in extras.values() for x in v)
    extras_a = sum(x[2] for v in extras.values() for x in v)

    delivery = build_delivery(src, menu)
    dlv_q = sum(x['qty'] for v in delivery.values() for x in v)
    dlv_a = sum(x['amt'] for v in delivery.values() for x in v)

    total_menu = sum(len(items) for cat, items in items_patched)

    return {
        'menu_total':    total_menu,
        'menu_matched':  matched_items,
        'dinein_qty':    dinein_q,
        'dinein_amt':    dinein_a,
        'extras_qty':    extras_q,
        'extras_amt':    extras_a,
        'delivery_qty':  dlv_q,
        'delivery_amt':  dlv_a,
        'delivery_cats': len(delivery),
    }


# 便利封装: 单文件入口（保留给可能的脚本/测试用）
def get_stats(file_obj, restaurant_type: str, pos_type: str):
    src = load_source(file_obj, pos_type)
    menu = get_menu(restaurant_type)
    return compute_stats(src, menu)
