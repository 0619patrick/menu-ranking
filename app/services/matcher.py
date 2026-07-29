"""
AI 辅助匹配服务

将未匹配的 POS 菜名与菜单标准菜名做模糊匹配，
提供建议匹配，确认后自动更新 menu.csv。
"""
import csv
import os
import difflib
import logging

from app.services.menu_service import get_menu, MENUS

logger = logging.getLogger(__name__)

_DATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'menus')
_DATA_ROOT = os.path.normpath(_DATA_ROOT)


def _get_menu_items(restaurant_key: str) -> list:
    """
    获取指定餐厅的菜单项列表。

    返回: [(分类, 标准菜名, [POS写法列表]), ...]
    """
    menu = get_menu(restaurant_key)
    items = []
    for cat, dishes in menu.items:
        for name, price, unit, pos_names in dishes:
            items.append((cat, name, list(pos_names)))
    return items


def suggest(unmatched_names: list, restaurant_key: str) -> dict:
    """
    对未匹配的 POS 菜名，给出 top 5 匹配建议。

    参数:
        unmatched_names: 未匹配的 POS 菜名列表
        restaurant_key:  餐厅 key（如 'acheng'）

    返回:
        {
            "未匹配菜名": [
                {"menu_name": "标准菜名", "score": 0.85, "cat": "分类"},
                ...
            ]
        }
    """
    menu_items = _get_menu_items(restaurant_key)
    suggestions = {}

    # 收集所有用于比对的名称
    candidates = []  # [(display_name, cat, source)]
    for cat, name, pos_names in menu_items:
        candidates.append((name, cat, 'menu_name'))
        for pn in pos_names:
            candidates.append((pn, cat, 'pos_writing'))

    for name in unmatched_names:
        scores = []
        seen = set()
        for candidate, cat, source in candidates:
            # 如果候选名与标准菜名不同且已评过分，跳过同名 POS 写法
            key = (candidate, cat)
            if key in seen:
                continue
            seen.add(key)

            score = difflib.SequenceMatcher(None, name, candidate).ratio()

            # POS 写法的匹配应该比标准菜名更可信，加权重
            if source == 'pos_writing':
                score = min(score * 1.1, 1.0)

            if score >= 0.3:
                # 找到对应的标准菜名
                menu_name = candidate
                for cn, ccat, _ in menu_items:
                    if ccat == cat and cn == candidate:
                        menu_name = cn
                        break
                    # 候选是 POS 写法时，找到所属的标准菜名
                    if candidate in [pn for _, _, pns in menu_items for pn in pns]:
                        for ccn, cn2, pns2 in menu_items:
                            if candidate in pns2 and ccn == cat:
                                menu_name = cn2
                                break

                scores.append({
                    'menu_name': menu_name,
                    'score': round(score, 3),
                    'cat': cat,
                })

        # 去重（同名同分类只保留最高分）
        seen_dedup = {}
        for s in scores:
            key = (s['menu_name'], s['cat'])
            if key not in seen_dedup or s['score'] > seen_dedup[key]['score']:
                seen_dedup[key] = s

        suggestions[name] = sorted(seen_dedup.values(), key=lambda x: -x['score'])[:5]

    return suggestions


def confirm_match(restaurant_key: str, menu_name: str, pos_writing: str) -> dict:
    """
    确认匹配：将 POS 写法追加到 menu.csv 对应菜品的 POS 写法列。

    参数:
        restaurant_key: 餐厅 key
        menu_name:      标准菜名
        pos_writing:    要追加的 POS 写法

    返回:
        {"status": "ok", "updated": True/False}
    """
    menu_csv = os.path.join(_DATA_ROOT, restaurant_key, 'menu.csv')
    if not os.path.exists(menu_csv):
        raise FileNotFoundError(f'menu.csv 不存在: {menu_csv}')

    rows = []
    updated = False
    with open(menu_csv, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)  # 保留表头
        rows.append(header)
        for row in reader:
            if len(row) >= 5:
                cat, name, price, unit, pos_col = [c.strip() for c in row[:5]]
                if name == menu_name:
                    # 检查是否已存在该写法
                    existing = [p.strip() for p in pos_col.split('|') if p.strip()]
                    if pos_writing not in existing:
                        existing.append(pos_writing)
                        row[4] = '|'.join(existing)
                        updated = True
                        logger.info('POS 写法已追加: %s → %s (餐厅: %s)', pos_writing, menu_name, restaurant_key)
            rows.append(row)

    if updated:
        with open(menu_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        # 刷新内存中的菜单缓存，下次预览生效
        _refresh_cache(restaurant_key)

    return {'status': 'ok', 'updated': updated}


def _refresh_cache(restaurant_key: str):
    """更新内存中的菜单缓存"""
    from app.services.loader import load_menu_dir
    rest_dir = os.path.join(_DATA_ROOT, restaurant_key)
    if os.path.isdir(rest_dir):
        MENUS[restaurant_key] = load_menu_dir(rest_dir)
        logger.info('菜单缓存已刷新: %s', restaurant_key)
