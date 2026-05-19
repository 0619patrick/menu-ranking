"""
数据处理核心:
1. 读取 POS 源数据
2. 按菜单分类填充堂食销量(排除 KT/FP)
3. 把 KT/FP 项目单独整理成外卖区(自取分上下)
4. 生成左右并列的 Excel 对照表
"""
import io
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from .menu_config import MENU, DROP_CATEGORIES_DINEIN, collect_used_names


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


def load_source(file_obj_or_path):
    """加载源数据 (支持文件路径或文件对象)"""
    src = pd.read_excel(file_obj_or_path).dropna(subset=['项目名称'])
    src['项目名称'] = src['项目名称'].astype(str).str.strip()
    src['分类'] = src['分类'].astype(str)
    src['数量'] = pd.to_numeric(src['数量'], errors='coerce').fillna(0).astype(int)
    src['金额'] = pd.to_numeric(src['金额'], errors='coerce').fillna(0)
    return src


def get_dinein_sales(name_list, src):
    """获取菜品的堂食销量(排除 KT/FP 分类)"""
    matched = src[
        src['项目名称'].isin(name_list) &
        (~src['分类'].str.contains('KT|FP', na=False, regex=True))
    ]
    return int(matched['数量'].sum()), int(matched['金额'].sum())


def build_dinein_extras(src, used_names):
    """收集堂食「菜單外」的项目"""
    filtered = src[
        (~src['分类'].str.contains('KT|FP', na=False, regex=True)) &
        (~src['分类'].isin(DROP_CATEGORIES_DINEIN))
    ]
    agg = filtered.groupby(['项目名称', '分类']).agg(
        数量=('数量', 'sum'), 金额=('金额', 'sum')).reset_index()
    agg = agg[~agg['项目名称'].isin(used_names)]
    extras = {}
    for _, r in agg.iterrows():
        if r['数量'] == 0 and r['金额'] == 0:
            continue
        extras.setdefault(r['分类'], []).append(
            (r['项目名称'], int(r['数量']), int(r['金额'])))
    for c in extras:
        extras[c].sort(key=lambda x: -x[2])
    return extras


def get_dinein_sales_detail(name_list, src):
    """堂食销量，按每个 POS 变体分开返回 (total_qty, total_amt, variants)"""
    variants = []
    for pn in name_list:
        matched = src[
            (src['项目名称'] == pn) &
            (~src['分类'].str.contains('KT|FP', na=False, regex=True))
        ]
        q = int(matched['数量'].sum())
        a = int(matched['金额'].sum())
        if q != 0 or a != 0:
            variants.append({'name': pn, 'qty': q, 'amt': a})
    return sum(v['qty'] for v in variants), sum(v['amt'] for v in variants), variants


def build_delivery(src):
    """收集所有 KT/FP 分类的项目, 按分类组织"""
    delivery = src[src['分类'].str.contains('KT|FP', na=False, regex=True)]
    agg = delivery.groupby(['分类', '项目名称']).agg(
        数量=('数量', 'sum'), 金额=('金额', 'sum')).reset_index()
    by_cat = {}
    for _, r in agg.iterrows():
        if r['数量'] == 0 and r['金额'] == 0:
            continue
        by_cat.setdefault(r['分类'], []).append(
            (r['项目名称'], int(r['数量']), int(r['金额'])))
    for c in by_cat:
        by_cat[c].sort(key=lambda x: -x[2])
    return by_cat


def build_sheet(ws, shop_name, src):
    """在 sheet 里建好该店的对照表"""

    # 列宽
    widths = {
        'A': 2, 'B': 13, 'C': 4.5, 'D': 36, 'E': 9, 'F': 8, 'G': 8, 'H': 10,
        'I': 2, 'J': 22, 'K': 4.5, 'L': 36, 'M': 8, 'N': 10
    }
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    # 行 1: 总标题
    ws.row_dimensions[1].height = 28
    ws.merge_cells('B1:N1')
    ws.cell(row=1, column=2, value=f'天天Authentic × {shop_name} 銷量對照').font = FONT_TITLE
    ws.cell(row=1, column=2).alignment = CENTER
    for col in range(2, 15):
        ws.cell(row=1, column=col).fill = BLUE

    # 行 2: 区域标题
    ws.merge_cells('B2:H2')
    ws.cell(row=2, column=2, value='堂食 (按菜單分類)').font = FONT_HEADER
    ws.cell(row=2, column=2).alignment = CENTER
    for col in range(2, 9):
        ws.cell(row=2, column=col).fill = LIGHT_BLUE

    ws.merge_cells('J2:N2')
    ws.cell(row=2, column=10, value='外賣 (KT/FP分類)').font = FONT_SECTION_W
    ws.cell(row=2, column=10).alignment = CENTER
    for col in range(10, 15):
        ws.cell(row=2, column=col).fill = GRAY_HEADER

    # 行 3: 字段头
    dinein_headers = [('B', '分類'), ('C', '排序'), ('D', '品名'),
                      ('E', '單位'), ('F', '菜單價'), ('G', '數量'), ('H', '金額')]
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
        cols = [2, 3, 4, 5, 6, 7, 8]
        for col, val in zip(cols, vals):
            c = ws.cell(row=r, column=col, value=val)
            if fill:
                c.fill = fill
            c.font = font if font else FONT_DATA
            c.alignment = LEFT if col == 4 else CENTER
            c.border = BORDER

    current_row_dinein = 4

    # 茶位
    tea_cat, tea_items = MENU[0]
    for idx, (name, price, unit, pos_names) in enumerate(tea_items):
        q, a = get_dinein_sales(pos_names, src)
        write_dinein_row(current_row_dinein,
                         [tea_cat, idx+1, name, unit, price, q, a],
                         fill=YELLOW, font=FONT_CAT if idx == 0 else FONT_DATA)
        current_row_dinein += 1

    # 大MENU 标题
    ws.merge_cells(start_row=current_row_dinein, start_column=2,
                   end_row=current_row_dinein, end_column=8)
    ws.cell(row=current_row_dinein, column=2, value='大MENU').font = FONT_SECTION
    ws.cell(row=current_row_dinein, column=2).alignment = CENTER
    for col in range(2, 9):
        ws.cell(row=current_row_dinein, column=col).fill = LIGHT_BLUE
        ws.cell(row=current_row_dinein, column=col).border = BORDER
    current_row_dinein += 1

    # 各分类(按金额降序)
    for cat, items in MENU[1:]:
        items_with_sales = []
        for name, price, unit, pos_names in items:
            q, a = get_dinein_sales(pos_names, src)
            items_with_sales.append((name, price, unit, q, a))
        items_with_sales.sort(key=lambda x: -x[4])

        start = current_row_dinein
        for idx, (name, price, unit, q, a) in enumerate(items_with_sales):
            cat_val = cat if idx == 0 else ''
            font = FONT_CAT if idx == 0 else FONT_DATA
            write_dinein_row(current_row_dinein,
                             [cat_val, idx+1, name, unit, price, q, a],
                             font=font)
            current_row_dinein += 1
        if len(items_with_sales) > 1:
            merge_ranges.append(f'B{start}:B{current_row_dinein-1}')
        current_row_dinein += 1  # 空一行

    # 堂食菜單外
    used_names = collect_used_names()
    extras = build_dinein_extras(src, used_names)
    if extras:
        for col in range(2, 9):
            ws.cell(row=current_row_dinein, column=col).fill = LIGHT_GRAY
            ws.cell(row=current_row_dinein, column=col).border = BORDER
        ws.merge_cells(start_row=current_row_dinein, start_column=2,
                       end_row=current_row_dinein, end_column=8)
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
                                 [cat_val, idx+1, name, '', '', q, a],
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

    delivery = build_delivery(src)
    normal_cats = [c for c in delivery.keys() if '自取' not in c]
    self_take_cats = [c for c in delivery.keys() if '自取' in c]

    normal_kt = sorted([c for c in normal_cats if c.startswith('KT')],
                       key=lambda c: -sum(x[2] for x in delivery[c]))
    normal_fp = sorted([c for c in normal_cats if c.startswith('FP')],
                       key=lambda c: -sum(x[2] for x in delivery[c]))
    st_kt = sorted([c for c in self_take_cats if c.startswith('KT')],
                   key=lambda c: -sum(x[2] for x in delivery[c]))
    st_fp = sorted([c for c in self_take_cats if c.startswith('FP')],
                   key=lambda c: -sum(x[2] for x in delivery[c]))

    current_row_dlv = 4

    # 上半段: 普通
    for src_cat in normal_kt + normal_fp:
        items = delivery[src_cat]
        start = current_row_dlv
        for idx, (name, q, a) in enumerate(items):
            cat_val = src_cat if idx == 0 else ''
            font = FONT_CAT if idx == 0 else FONT_DATA
            write_delivery_row(current_row_dlv, [cat_val, idx+1, name, q, a], font=font)
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
        for idx, (name, q, a) in enumerate(items):
            cat_val = src_cat if idx == 0 else ''
            font = FONT_CAT if idx == 0 else FONT_DATA
            write_delivery_row(current_row_dlv, [cat_val, idx+1, name, q, a], font=font)
            current_row_dlv += 1
        if len(items) > 1:
            merge_ranges.append(f'J{start}:J{current_row_dlv-1}')
        current_row_dlv += 1

    # 应用合并
    for mr in merge_ranges:
        ws.merge_cells(mr)
        first_cell = mr.split(':')[0]
        ws[first_cell].alignment = CENTER


def build_preview_data(shop_name, src):
    """构建预览用结构化数据（供前端渲染表格）"""
    used_names = collect_used_names()

    tea_cat, tea_items_raw = MENU[0]
    tea_rows = []
    for name, price, unit, pos_names in tea_items_raw:
        q, a, variants = get_dinein_sales_detail(pos_names, src)
        tea_rows.append({'name': name, 'price': price, 'unit': unit,
                         'qty': q, 'amt': a,
                         'merged': variants if len(variants) > 1 else []})

    menu_sections = []
    for cat, items_raw in MENU[1:]:
        rows = []
        for name, price, unit, pos_names in items_raw:
            q, a, variants = get_dinein_sales_detail(pos_names, src)
            rows.append({'name': name, 'price': price, 'unit': unit,
                         'qty': q, 'amt': a,
                         'merged': variants if len(variants) > 1 else []})
        rows.sort(key=lambda x: -x['amt'])
        menu_sections.append({'cat': cat, 'items': rows})

    extras = build_dinein_extras(src, used_names)
    extras_sections = [
        {'cat': c, 'items': [{'name': n, 'qty': q, 'amt': a} for n, q, a in extras[c]]}
        for c in sorted(extras, key=lambda c: -sum(x[2] for x in extras[c]))
    ]

    delivery = build_delivery(src)
    normal_cats = [c for c in delivery if '自取' not in c]
    self_take_cats = [c for c in delivery if '自取' in c]
    normal_kt = sorted([c for c in normal_cats if c.startswith('KT')],
                       key=lambda c: -sum(x[2] for x in delivery[c]))
    normal_fp = sorted([c for c in normal_cats if c.startswith('FP')],
                       key=lambda c: -sum(x[2] for x in delivery[c]))
    st_kt = sorted([c for c in self_take_cats if c.startswith('KT')],
                   key=lambda c: -sum(x[2] for x in delivery[c]))
    st_fp = sorted([c for c in self_take_cats if c.startswith('FP')],
                   key=lambda c: -sum(x[2] for x in delivery[c]))

    def dlv_section(cat):
        return {'cat': cat,
                'items': [{'name': n, 'qty': q, 'amt': a} for n, q, a in delivery[cat]]}

    return {
        'shop_name': shop_name,
        'tea': tea_rows,
        'menu': menu_sections,
        'extras': extras_sections,
        'dlv_normal': [dlv_section(c) for c in normal_kt + normal_fp],
        'dlv_selftake': [dlv_section(c) for c in st_kt + st_fp],
    }


def generate_excel(shop_files):
    """
    生成对照表 Excel
    
    shop_files: list of tuples [(shop_name, file_obj_or_path), ...]
    返回: BytesIO 对象 (Excel 内容)
    """
    wb = Workbook()
    # 删默认 sheet
    default = wb.active
    wb.remove(default)

    for shop_name, file_obj in shop_files:
        ws = wb.create_sheet(shop_name)
        src = load_source(file_obj)
        build_sheet(ws, shop_name, src)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def get_stats(file_obj):
    """获取一家店的统计摘要"""
    src = load_source(file_obj)
    used = collect_used_names()

    dinein_q = 0
    dinein_a = 0
    matched_items = 0
    for cat, items in MENU:
        for name, price, unit, pos_names in items:
            q, a = get_dinein_sales(pos_names, src)
            dinein_q += q
            dinein_a += a
            if q > 0 or a > 0:
                matched_items += 1

    extras = build_dinein_extras(src, used)
    extras_q = sum(x[1] for v in extras.values() for x in v)
    extras_a = sum(x[2] for v in extras.values() for x in v)

    delivery = build_delivery(src)
    dlv_q = sum(x[1] for v in delivery.values() for x in v)
    dlv_a = sum(x[2] for v in delivery.values() for x in v)

    total_menu = sum(len(items) for cat, items in MENU)

    return {
        'menu_total': total_menu,
        'menu_matched': matched_items,
        'dinein_qty': dinein_q,
        'dinein_amt': dinein_a,
        'extras_qty': extras_q,
        'extras_amt': extras_a,
        'delivery_qty': dlv_q,
        'delivery_amt': dlv_a,
        'delivery_cats': len(delivery),
    }
