"""Deterministic nutrition imports and calculations. No model-generated values."""
import io
import math
import re
import html
import urllib.parse
import urllib.request
from functools import lru_cache

import pandas as pd
from openpyxl import Workbook

NUTRIENTS = {
    'energy': ('热量', 'kcal'), 'protein': ('蛋白质', 'g'),
    'fat': ('脂肪', 'g'), 'carbs': ('碳水', 'g'),
    'saturated_fat': ('饱和脂肪', 'g'), 'trans_fat': ('反式脂肪', 'g'),
    'sugar': ('糖', 'g'),
    'fiber': ('膳食纤维', 'g'), 'sodium': ('钠', 'mg'),
    'potassium': ('钾', 'mg'), 'calcium': ('钙', 'mg'),
    'cholesterol': ('胆固醇', 'mg'),
}

CFS_BASE = 'https://www.cfs.gov.hk/tc_chi/nutrient/'
CFS_LABELS = {
    '能量': 'energy', '蛋白質': 'protein', '碳水化合物': 'carbs',
    '脂肪': 'fat', '膳食纖維': 'fiber', '糖': 'sugar',
    '飽和脂肪': 'saturated_fat', '反式脂肪': 'trans_fat',
    '膽固醇': 'cholesterol', '鈣': 'calcium', '鉀': 'potassium', '鈉': 'sodium',
}

ALIASES = {
    'name': ['食材名称', '食材名', '名称'], 'state': ['生/熟', '生 / 熟', '生熟', '状态'],
    'energy': ['热量kcal/100g', '热量 kcal/100g', '热量', '能量'],
    'protein': ['蛋白质g', '蛋白质 g', '蛋白质'], 'fat': ['脂肪g', '脂肪 g', '脂肪'],
    'saturated_fat': ['饱和脂肪g', '饱和脂肪 g', '饱和脂肪', '飽和脂肪'],
    'trans_fat': ['反式脂肪g', '反式脂肪 g', '反式脂肪'],
    'sugar': ['糖g', '糖 g', '糖'],
    'carbs': ['碳水g', '碳水 g', '碳水', '碳水化合物'],
    'fiber': ['膳食纤维g', '膳食纤维 g', '膳食纤维'],
    'sodium': ['钠mg', '钠 mg', '钠'], 'potassium': ['钾mg', '钾 mg', '钾'],
    'calcium': ['钙mg', '钙 mg', '钙'], 'cholesterol': ['胆固醇mg', '胆固醇 mg', '胆固醇'],
    'source': ['来源数据库', '数据来源', '来源'],
    'food_code': ['内部食材编码', '食材编码', '系统编码', '编码'],
    'source_id': ['来源食物编号', '来源编号'],
    'source_version': ['数据版本', '来源版本', '版本'],
    'carbs_basis': ['碳水口径', '碳水化合物口径'],
    'fiber_basis': ['膳食纤维口径', '纤维口径'],
    'note': ['备注'],
    'sop_code': ['SOP编码', 'SOP 编码', '编码'], 'dish': ['菜品名称', '菜品名'],
    'method': ['烹饪方式', '做法'], 'yield_rate': ['生熟折算系数', '出品率'],
    'oil': ['标准用油g', '每道菜固定用油 g', '用油g', '用油'],
    'ingredients': ['配方明细', '食材配方'], 'date': ['日期'],
}

def _norm(value):
    return re.sub(r'[\s（）()/_-]+', '', str(value or '')).lower()


def _text(value):
    return '' if value is None or pd.isna(value) else str(value).strip()


def _strip_html(value):
    value = re.sub(r'<script[\s\S]*?</script>', '', value, flags=re.I)
    value = re.sub(r'<[^>]+>', ' ', value)
    return re.sub(r'\s+', ' ', html.unescape(value).replace('\xa0', ' ')).strip()


def _cfs_post(endpoint, data):
    request_data = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(CFS_BASE + endpoint, data=request_data,
        headers={'User-Agent': 'MenuNutritionTool/1.0', 'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.read().decode('utf-8', errors='replace')
    except Exception as exc:
        raise ValueError(f'香港食安中心查询暂时不可用：{exc}') from exc


@lru_cache(maxsize=512)
def search_cfs_food(query):
    query = str(query or '').strip()
    if not query:
        raise ValueError('请输入食材关键词')
    page = _cfs_post('search3.php', {'keylang': 'C', 'inShortMode': '0', 'fg_id': '',
        'fsg_id': '', 'keyword': query, 'keyword2': '', 'searchcriteria': 'and'})
    pattern = re.compile(r'<a[^>]*href=["\']javascript:tosubmit\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)[^>]*>([\s\S]*?)</a>', re.I)
    results = []
    for match in pattern.finditer(page):
        item = {'fg_id': match.group(1), 'fsg_id': match.group(2),
                'food_id': match.group(3), 'name': _strip_html(match.group(4))}
        if item['name'] and not any(x['food_id'] == item['food_id'] for x in results): results.append(item)
    return results[:30]


@lru_cache(maxsize=2048)
def get_cfs_food(fg_id, fsg_id, food_id):
    page = _cfs_post('fc-myreport.php', {'fg_id': fg_id, 'fsg_id': fsg_id,
        'food_id': food_id, 'inShortMode': '0'})
    rows = [_strip_html(x) for x in re.findall(r'<tr[^>]*>([\s\S]*?)</tr>', page, re.I)]
    result = {key: None for key in NUTRIENTS}
    result.update({'source_id': food_id, 'source_version': 'CFS online',
                   'carbs_basis': '', 'fiber_basis': '', 'data_flags': {}})
    for row in rows:
        for prefix, field in [('食物名稱:', 'name'), ('資料來源:', 'source')]:
            if row.startswith(prefix): result[field] = row[len(prefix):].strip().split('(')[0].strip()
        for label, key in CFS_LABELS.items():
            if not re.match(r'^' + re.escape(label) + r'\*?\s', row): continue
            tail = row.replace(label, '', 1).replace('*', '').strip()
            match = re.search(r'(-?\d+(?:\.\d+)?)\s*$', tail)
            if match: result[key] = float(match.group(1))
            elif re.search(r'\bND\b|Trace|微量', tail, re.I):
                result[key] = 0.0; result['data_flags'][key] = 'ND/Trace'
            else: result['data_flags'][key] = 'NA'
    if not result.get('name'):
        raise ValueError('香港食安中心没有返回该食材详情')
    if 'FoodData Central' in result.get('source', '') or '中國疾病' in result.get('source', ''):
        result['carbs_basis'] = '总碳水化合物'
    else: result['carbs_basis'] = '可利用碳水化合物'
    result['fiber_basis'] = '不溶性膳食纤维' if '中國疾病' in result.get('source', '') else '总膳食纤维'
    return result

def _column_map(columns):
    normalized = {_norm(c): c for c in columns}
    result = {}
    for key, aliases in ALIASES.items():
        for alias in aliases:
            if _norm(alias) in normalized:
                result[key] = normalized[_norm(alias)]
                break
    return result

def _number(value, field, row, allow_blank=False):
    if pd.isna(value) or str(value).strip() == '':
        if allow_blank:
            return 0.0
        raise ValueError(f'第 {row} 行“{field}”为空')
    match = re.search(r'-?\d+(?:\.\d+)?', str(value).replace(',', ''))
    if not match:
        raise ValueError(f'第 {row} 行“{field}”不是有效数字')
    result = float(match.group())
    if not math.isfinite(result) or result < 0:
        raise ValueError(f'第 {row} 行“{field}”必须是非负数')
    return result

def _read(uploaded):
    name = uploaded.filename.lower()
    raw = uploaded.read()
    try:
        if name.endswith('.csv'):
            for encoding in ('utf-8-sig', 'gb18030'):
                try:
                    return pd.read_csv(io.BytesIO(raw), encoding=encoding)
                except UnicodeDecodeError:
                    pass
        elif name.endswith(('.xlsx', '.xls')):
            return pd.read_excel(io.BytesIO(raw), engine='calamine')
    except Exception as exc:
        raise ValueError(f'文件读取失败：{exc}') from exc
    raise ValueError('仅支持 .xlsx、.xls、.csv 文件')


def _read_sheets(uploaded):
    """Read all relevant sheets while ignoring embedded workbook images."""
    name = uploaded.filename.lower()
    raw = uploaded.read()
    if name.endswith('.csv'):
        uploaded.stream.seek(0)
        return {'CSV': _read(uploaded)}
    if not name.endswith(('.xlsx', '.xls')):
        raise ValueError('仅支持 .xlsx、.xls、.csv 文件')
    try:
        book = pd.ExcelFile(io.BytesIO(raw), engine='calamine')
        return {sheet: pd.read_excel(book, sheet_name=sheet, header=None)
                for sheet in book.sheet_names}
    except Exception as exc:
        raise ValueError(f'菜单文件读取失败：{exc}') from exc


def _parse_native_sops(uploaded):
    all_sheets = _read_sheets(uploaded)
    sheets = {name: df for name, df in all_sheets.items() if '配料sop' in str(name).lower()}
    if not sheets:
        df = next(iter(all_sheets.values()), pd.DataFrame())
        if df.empty:
            raise ValueError('文件中没有可导入的数据')
        df.columns = [_text(v) for v in df.iloc[0].tolist()]
        df = df.iloc[1:].reset_index(drop=True); cols = _column_map(df.columns)
        required = ['sop_code', 'dish', 'yield_rate', 'oil']
        missing = [x for x in required if x not in cols]
        if missing:
            raise ValueError('没有找到“配料sop”工作表，且文件不符合通用SOP模板')
        rows = []
        for idx, src in df.iterrows():
            rate = _number(src[cols['yield_rate']], '生熟折算系数', idx + 2)
            rows.append({'sop_code': _text(src[cols['sop_code']]), 'dish': _text(src[cols['dish']]),
                         'method': _text(src.get(cols.get('method'), '')), 'yield_rate': rate,
                         'oil': _number(src[cols['oil']], '标准用油', idx + 2, True),
                         'ingredients': _text(src.get(cols.get('ingredients'), ''))})
        return {'kind': 'sops', 'format': 'generic', 'rows': rows, 'errors': [],
                'total': len(rows), 'accepted': len(rows)}
    dishes, errors = [], []
    for sheet_name, df in sheets.items():
        if df.empty or df.shape[1] < 7:
            continue
        current = None
        for idx in range(1, len(df)):
            row = df.iloc[idx]
            dish_name = _text(row.iloc[1]) if len(row) > 1 else ''
            ingredient = _text(row.iloc[3]) if len(row) > 3 else ''
            if dish_name:
                if current and current['ingredients']:
                    dishes.append(current)
                current = {'sop_code': f'{sheet_name}-{idx + 1}', 'dish': dish_name,
                           'meal': re.search(r'([A-E])餐', sheet_name).group(1) if re.search(r'([A-E])餐', sheet_name) else '',
                           'sheet': sheet_name, 'ingredients': []}
            if current and ingredient and '合計生重' not in ingredient:
                try:
                    grams = _number(row.iloc[5], '人均用量', idx + 1)
                except ValueError as exc:
                    errors.append(f'{sheet_name}：{exc}')
                    continue
                current['ingredients'].append({'name': ingredient, 'weight': grams,
                    'code': _text(row.iloc[6]) if len(row) > 6 else ''})
        if current and current['ingredients']:
            dishes.append(current)
    return {'kind': 'sops', 'format': 'native_menu', 'rows': dishes, 'errors': errors,
            'total': len(dishes), 'accepted': len(dishes)}


def _parse_historical(uploaded):
    name = uploaded.filename.lower(); raw = uploaded.read()
    try:
        if name.endswith('.csv'):
            frames = {'CSV': pd.read_csv(io.BytesIO(raw), encoding='utf-8-sig', header=None)}
        elif name.endswith(('.xlsx', '.xls')):
            book = pd.ExcelFile(io.BytesIO(raw), engine='calamine')
            frames = {s: pd.read_excel(book, sheet_name=s, header=None) for s in book.sheet_names}
        else:
            raise ValueError('仅支持 .xlsx、.xls、.csv 文件')
    except Exception as exc:
        raise ValueError(f'历史文件读取失败：{exc}') from exc
    patterns = {
        'energy': r'能量\s*([0-9.]+)', 'protein': r'蛋白[質质]\s*([0-9.]+)',
        'fat': r'[總总]脂肪\s*([0-9.]+)', 'saturated_fat': r'[飽饱]和脂肪\s*([0-9.]+)',
        'trans_fat': r'反式脂肪\s*[^0-9]*([0-9.]+)', 'carbs': r'碳水化合物\s*([0-9.]+)',
        'sugar': r'糖\s*([0-9.]+)', 'sodium': r'[鈉钠]\s*[^0-9]*([0-9.]+)',
    }
    rows = []
    for sheet, df in frames.items():
        for idx, source in df.iterrows():
            text_value = ' '.join(_text(v) for v in source.tolist())
            found = {k: float(m.group(1)) for k, p in patterns.items()
                     if (m := re.search(p, text_value.replace('（', ' ').replace('(', ' ')))}
            if len(found) >= 5:
                raw_name = _text(source.iloc[0]); clean_name = re.sub(r'^[A-E][（(]?\d+[）)]?', '', raw_name).strip()
                rows.append({'date': '', 'dish': clean_name or raw_name, 'sheet': sheet,
                             'source_row': idx + 1, **found})
    if not rows:
        raise ValueError('未识别到历史营养结果，请检查文件格式')
    return {'kind': 'history', 'format': 'historical_results', 'rows': rows, 'errors': [],
            'total': len(rows), 'accepted': len(rows)}

def parse_upload(uploaded, kind):
    if kind == 'sops' and uploaded.filename.lower().endswith(('.xlsx', '.xls')):
        return _parse_native_sops(uploaded)
    if kind == 'history':
        return _parse_historical(uploaded)
    df = _read(uploaded).dropna(how='all')
    if df.empty:
        raise ValueError('文件中没有可导入的数据')
    cols = _column_map(df.columns)
    required = {'foods': ['name', *NUTRIENTS], 'sops': ['sop_code', 'dish', 'yield_rate', 'oil'],
                'history': ['date', 'dish', *NUTRIENTS]}[kind]
    missing = [x for x in required if x not in cols]
    if missing:
        labels = [NUTRIENTS[x][0] if x in NUTRIENTS else x for x in missing]
        raise ValueError('缺少必填列：' + '、'.join(labels) + '。请先下载对应模板。')
    rows, errors = [], []
    for idx, src in df.iterrows():
        row_no = idx + 2
        try:
            if kind == 'foods':
                item = {
                    'name': _text(src[cols['name']]),
                    'state': _text(src.get(cols.get('state'), '')),
                    'food_code': _text(src.get(cols.get('food_code'), '')),
                    'source': _text(src.get(cols.get('source'), '')),
                    'source_id': _text(src.get(cols.get('source_id'), '')),
                    'source_version': _text(src.get(cols.get('source_version'), '')),
                    'carbs_basis': _text(src.get(cols.get('carbs_basis'), '')),
                    'fiber_basis': _text(src.get(cols.get('fiber_basis'), '')),
                    'note': _text(src.get(cols.get('note'), '')),
                }
                if not item['name']: raise ValueError(f'第 {row_no} 行食材名称为空')
                for key, (label, _) in NUTRIENTS.items(): item[key] = _number(src[cols[key]], label, row_no)
                rows.append(item)
            elif kind == 'sops':
                rate = _number(src[cols['yield_rate']], '生熟折算系数', row_no)
                if rate <= 0: raise ValueError(f'第 {row_no} 行生熟折算系数必须大于 0')
                rows.append({'sop_code': str(src[cols['sop_code']]).strip(), 'dish': str(src[cols['dish']]).strip(),
                             'method': str(src.get(cols.get('method'), '')).strip(), 'yield_rate': rate,
                             'oil': _number(src[cols['oil']], '标准用油', row_no, True),
                             'ingredients': str(src.get(cols.get('ingredients'), '')).strip()})
            else:
                item = {'date': str(src[cols['date']]).strip(), 'dish': str(src[cols['dish']]).strip()}
                for key, (label, _) in NUTRIENTS.items(): item[key] = _number(src[cols[key]], label, row_no)
                rows.append(item)
        except ValueError as exc:
            errors.append(str(exc))
    return {'kind': kind, 'rows': rows, 'errors': errors, 'total': len(df), 'accepted': len(rows)}

def calculate_nutrition(payload):
    foods = {f"{str(x.get('name','')).strip()}|{str(x.get('state','')).strip()}": x for x in payload.get('foods', [])}
    items = payload.get('items', [])
    if not items: raise ValueError('请至少添加一种食材')
    totals = {key: 0.0 for key in NUTRIENTS}; details = []; rejected = []
    for pos, item in enumerate(items, 1):
        name, state = str(item.get('name', '')).strip(), str(item.get('state', '')).strip()
        food = foods.get(f'{name}|{state}') or foods.get(f'{name}|')
        if not food:
            rejected.append(f'{name or "第%d项" % pos}：无权威成分数据，无法计算')
            continue
        gross = _number(item.get('weight'), '重量', pos)
        waste = _number(item.get('waste', 0), '不可食用占比', pos, True)
        if waste > 100: raise ValueError(f'{name} 的不可食用占比不能超过 100%')
        edible = gross * (1 - waste / 100)
        factor = edible / 100
        values = {k: float(food.get(k, 0) or 0) * factor for k in NUTRIENTS}
        for k in totals: totals[k] += values[k]
        details.append({'name': name, 'state': state, 'gross_weight': gross, 'waste': waste,
                        'edible_weight': round(edible, 2), 'factor': round(factor, 4), 'values': values,
                        'source': food.get('source', ''),
                        'source_id': food.get('source_id', ''),
                        'source_version': food.get('source_version', ''),
                        'carbs_basis': food.get('carbs_basis', ''),
                        'fiber_basis': food.get('fiber_basis', '')})
    if not details: raise ValueError('没有可计算的食材；请先导入权威食材营养库并核对名称与生熟状态')
    return {'totals': {k: round(v, 1) for k, v in totals.items()}, 'details': details, 'rejected': rejected,
            'method': payload.get('method', '生重计算'), 'nutrients': NUTRIENTS}


def calculate_dishes(payload):
    foods = payload.get('foods', []); dishes = payload.get('dishes', [])
    by_code = {str(x.get('food_code', '')).strip(): x for x in foods if str(x.get('food_code', '')).strip()}
    by_name = {str(x.get('name', '')).strip(): x for x in foods}
    history = {str(x.get('dish', '')).strip(): x for x in payload.get('history', [])}
    results = []
    for dish in dishes:
        totals = {key: 0.0 for key in NUTRIENTS}; matched = []; unmatched = []
        for ing in dish.get('ingredients', []):
            food = by_code.get(str(ing.get('code', '')).strip()) or by_name.get(str(ing.get('name', '')).strip())
            if not food:
                if not re.search(r'清水|水$', str(ing.get('name', ''))): unmatched.append(ing)
                continue
            factor = float(ing.get('weight', 0)) / 100
            for key in totals: totals[key] += float(food.get(key, 0) or 0) * factor
            matched.append({'ingredient': ing, 'food': food})
        old = history.get(str(dish.get('dish', '')).strip())
        comparison = {k: round(totals[k] - float(old.get(k, 0)), 1) for k in NUTRIENTS if old and k in old}
        results.append({'dish': dish.get('dish'), 'meal': dish.get('meal'),
                        'totals': {k: round(v, 1) for k, v in totals.items()},
                        'matched_count': len(matched), 'unmatched': unmatched,
                        'complete': not unmatched, 'history': old, 'comparison': comparison})
    return {'results': results, 'nutrients': NUTRIENTS}

def build_template(kind):
    headers = {
        'foods': ['食材名称', '内部食材编码', '生/熟', '热量 kcal/100g', '蛋白质 g', '脂肪 g', '饱和脂肪 g', '反式脂肪 g', '碳水 g', '糖 g', '膳食纤维 g', '钠 mg', '钾 mg', '钙 mg', '胆固醇 mg', '来源数据库', '来源食物编号', '数据版本', '碳水口径', '膳食纤维口径', '备注'],
        'sops': ['SOP编码', '菜品名称', '烹饪方式', '生熟折算系数', '标准用油g', '配方明细'],
        'history': ['日期', '菜品名称', '热量 kcal/100g', '蛋白质 g', '脂肪 g', '碳水 g', '膳食纤维 g', '钠 mg', '钾 mg', '钙 mg', '胆固醇 mg'],
    }[kind]
    wb = Workbook(); ws = wb.active; ws.title = '导入模板'; ws.append(headers)
    ws.freeze_panes = 'A2'; ws.auto_filter.ref = f'A1:{chr(64+len(headers))}1'
    for cell in ws[1]: cell.font = cell.font.copy(bold=True)
    stream = io.BytesIO(); wb.save(stream); stream.seek(0)
    return stream, {'foods':'食材营养库模板.xlsx','sops':'菜品SOP模板.xlsx','history':'历史营养台账模板.xlsx'}[kind]
