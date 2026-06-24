# -*- coding: utf-8 -*-
"""
CSV 菜单配置加载器

每家餐厅一个数据目录 app/menus/data/<key>/：
  menu.csv             菜单主表（分类/菜名/价格/单位/POS写法），运营日常维护的就是这张表
  config.csv           其余规则（外卖标记、丢弃分类、cat_map、关键词……），三列：配置项/键/值
  store_overrides.csv  可选。单店特殊 POS 写法补丁（店铺/菜名/补充POS写法）

POS 写法多个变体用 | 分隔。文件编码 UTF-8 with BOM（Excel 双击可直接打开）。

配置继承（同品牌多店、菜单仅轻微不同时用）：
  config.csv 里写一行  extends,,<另一家店的key>   表示「先继承那家店的全部菜单和规则」，
  本目录的 menu.csv / config.csv 只需写出『差异』：
    - menu.csv 列出新增的分类/菜品（同名分类则覆盖该分类）；
    - config.csv 的丢弃项/外卖标记等会与被继承方『合并』，scalar 有值则覆盖。
  新增分类默认插在末尾；要指定位置写  category_after,<新分类>,<锚分类>  插到锚分类之后。
  例（東薈城继承阿城、多一个手作系列、插在飲品后）：
    extends,,acheng
    category_after,手作系列,飲品
"""
import csv
import os

from .base import Menu

POS_SEP = '|'


def _read_rows(path):
    """读 CSV 去表头；整行为空的跳过。"""
    with open(path, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.reader(f))
    return [r for r in rows[1:] if any(c.strip() for c in r)]


def _split_pos(cell):
    return [p.strip() for p in cell.split(POS_SEP) if p.strip()]


def _parse_price(cell, where):
    try:
        f = float(cell)
    except ValueError:
        raise ValueError(f'{where}: 价格「{cell}」不是数字')
    return int(f) if f == int(f) else f


def _load_menu_items(path):
    """menu.csv -> [(分类, [(菜名, 价格, 单位, [POS写法]), ...]), ...] 保持行序"""
    items = []
    index = {}  # 分类 -> dishes list
    for lineno, row in enumerate(_read_rows(path), start=2):
        row = (row + [''] * 5)[:5]
        cat, name, price, unit, pos = (c.strip() for c in row)
        if not cat:
            raise ValueError(f'{path} 第{lineno}行: 分类不能为空')
        if cat not in index:
            index[cat] = []
            items.append((cat, index[cat]))
        if not name:
            continue  # 只声明分类（POS 原生分类占位）
        index[cat].append(
            (name, _parse_price(price, f'{path} 第{lineno}行'), unit, _split_pos(pos))
        )
    return items


# config.csv 各配置项的装配方式
_SCALARS = {'brand', 'short_name', 'adjust_marker', 'addon_section', 'main_section'}
_SETS = {
    'drop_category': 'drop_categories',
    'addon_category': 'addon_categories',
    'drop_name': 'drop_names',
    'main_keyword': 'main_keywords',
    'set_keyword': 'set_keywords',
    'pos_native_section': 'pos_native_sections',
    'strip_token': 'strip_tokens',
    'strip_regex': 'strip_regex',
}
_DICTS = {
    'pos_alias': 'pos_aliases',
    'pos_rename': 'pos_renames',
    'cat_map': 'cat_map',
    'force_cat': 'force_cat',
    'extras_merge': 'extras_merge',
    'extras_item_merge': 'extras_item_merge',
}
_SET_FIELDS = tuple(_SETS.values())
_DICT_FIELDS = tuple(_DICTS.values())

_RULE_KEYS = ('cat', 'startswith', 'contains', 'endswith')


def _parse_rule_spec(target, spec, where):
    """route_rule 的『值』(如 'cat=1人套餐;startswith=滷鵝;contains=$') -> 规则 dict"""
    if not target:
        raise ValueError(f'{where}: route_rule 的目标分类(键)不能为空')
    rule = {'target': target}
    for part in spec.split(';'):
        part = part.strip()
        if not part:
            continue
        if '=' not in part:
            raise ValueError(f'{where}: route_rule 条件「{part}」缺少 =（应形如 startswith=滷鵝）')
        k, v = part.split('=', 1)
        k = k.strip()
        if k not in _RULE_KEYS:
            raise ValueError(
                f'{where}: route_rule 未知条件「{k}」（只支持 {"/".join(_RULE_KEYS)}）')
        rule[k] = v.strip()
    if not any(k in rule for k in ('startswith', 'contains', 'endswith')):
        raise ValueError(f'{where}: route_rule 至少要有一个名字条件(startswith/contains/endswith)')
    return rule


def _load_config(path):
    """config.csv -> (kw, extends, category_after)

    kw: Menu 构造参数 dict（不含 items / store_overrides）
    extends: 被继承餐厅 key 或 None
    category_after: { 新分类: 锚分类 }（继承时新分类的插入位置）
    """
    kw = {name: set() for name in _SETS.values()}
    kw.update({name: {} for name in _DICTS.values()})
    kw['route_rules'] = []
    delivery = {}
    extends = None
    category_after = {}
    for lineno, row in enumerate(_read_rows(path), start=2):
        row = (row + [''] * 3)[:3]
        item, key, value = (c.strip() for c in row)
        if item == 'extends':
            extends = value
        elif item == 'category_after':
            category_after[key] = value
        elif item == 'route_rule':
            kw['route_rules'].append(
                _parse_rule_spec(key, value, f'{path} 第{lineno}行'))
        elif item == 'auto_match_category':
            kw['auto_match_category'] = value.strip().lower() in ('1', 'true', 'on', 'yes', '是')
        elif item == 'drop_zero_amount':
            kw['drop_zero_amount'] = value.strip().lower() in ('1', 'true', 'on', 'yes', '是')
        elif item in _SCALARS:
            kw[item] = value
        elif item == 'delivery_platform':
            delivery.setdefault(key, []).append(value)
        elif item in _SETS:
            kw[_SETS[item]].add(value)
        elif item in _DICTS:
            kw[_DICTS[item]][key] = value
        else:
            raise ValueError(f'{path} 第{lineno}行: 未知配置项「{item}」')
    if delivery:
        kw['delivery_platforms'] = delivery
    # 空 scalar 不传，沿用 Menu 默认值 / 被继承值
    for s in _SCALARS:
        if s in kw and kw[s] == '':
            del kw[s]
    return kw, extends, category_after


def _load_overrides(path):
    """store_overrides.csv -> { 店铺: { 菜名: [补充POS写法] } }"""
    overrides = {}
    if not os.path.exists(path):
        return overrides
    for lineno, row in enumerate(_read_rows(path), start=2):
        row = (row + [''] * 3)[:3]
        store, dish, pos = (c.strip() for c in row)
        if not store or not dish:
            raise ValueError(f'{path} 第{lineno}行: 店铺和菜名不能为空')
        overrides.setdefault(store, {})[dish] = _split_pos(pos)
    return overrides


def _merge_config(base, child):
    """child 覆盖/扩展 base：set 取并集、dict 合并、scalar 有值则覆盖、外卖标记合并。"""
    merged = dict(base)
    for f in _SET_FIELDS:
        merged[f] = set(base.get(f, set())) | set(child.get(f, set()))
    for f in _DICT_FIELDS:
        merged[f] = {**base.get(f, {}), **child.get(f, {})}
    # route_rules 是列表：子店自己的规则在前(可先命中)，再接基础店的
    merged['route_rules'] = list(child.get('route_rules', [])) + list(base.get('route_rules', []))
    for f in ('auto_match_category', 'drop_zero_amount'):   # bool：子店有写才覆盖
        if f in child:
            merged[f] = child[f]
    for f in _SCALARS:
        if child.get(f):
            merged[f] = child[f]
        elif f in base:
            merged[f] = base[f]
    if 'delivery_platforms' in child:
        dp = {k: list(v) for k, v in base.get('delivery_platforms', {}).items()}
        for k, markers in child['delivery_platforms'].items():
            seen = dp.setdefault(k, [])
            for m in markers:
                if m not in seen:
                    seen.append(m)
        merged['delivery_platforms'] = dp
    elif 'delivery_platforms' in base:
        merged['delivery_platforms'] = base['delivery_platforms']
    return merged


def _merge_items(base_items, child_items, category_after):
    """child 分类合并进 base：同名分类覆盖；新分类插到 category_after 指定锚分类之后（默认末尾）。"""
    result = [[cat, list(dishes)] for cat, dishes in base_items]

    def find_idx(cat):
        for i, (c, _) in enumerate(result):
            if c == cat:
                return i
        return -1

    for ccat, cdishes in child_items:
        idx = find_idx(ccat)
        if idx >= 0:
            result[idx][1] = list(cdishes)  # 覆盖同名分类
        else:
            anchor = category_after.get(ccat)
            ai = find_idx(anchor) if anchor else -1
            if ai >= 0:
                result.insert(ai + 1, [ccat, list(cdishes)])
            else:
                result.append([ccat, list(cdishes)])
    return [(c, d) for c, d in result]


def _resolve_raw(data_dir):
    """读取一个目录的 (kw, items, overrides)，若 config 声明 extends 则先递归继承。"""
    kw, extends, category_after = _load_config(os.path.join(data_dir, 'config.csv'))
    items = _load_menu_items(os.path.join(data_dir, 'menu.csv'))
    overrides = _load_overrides(os.path.join(data_dir, 'store_overrides.csv'))
    if extends:
        base_dir = os.path.join(os.path.dirname(os.path.normpath(data_dir)), extends)
        if not os.path.isdir(base_dir):
            raise ValueError(f'{data_dir}: extends 指向的餐厅「{extends}」目录不存在')
        b_kw, b_items, b_over = _resolve_raw(base_dir)
        kw = _merge_config(b_kw, kw)
        items = _merge_items(b_items, items, category_after)
        overrides = {**b_over, **overrides}
    return kw, items, overrides


def load_menu_dir(data_dir) -> Menu:
    """从一个餐厅数据目录构建 Menu 实例（支持 extends 继承）。"""
    kw, items, overrides = _resolve_raw(data_dir)
    if not kw.get('brand'):
        raise ValueError(f'{data_dir}: 缺少必填配置项 brand（自身或被继承的 config.csv 都没有）')
    kw['items'] = items
    kw['store_overrides'] = overrides
    return Menu(**kw)
