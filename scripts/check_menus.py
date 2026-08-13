# -*- coding: utf-8 -*-
"""
菜单配置体检

改完 menu.csv / config.csv 后跑一次，检查表格自身的逻辑矛盾。
这些问题程序运行时不会报错，但会让数字悄悄算错。

    python scripts/check_menus.py

没问题返回 0，有问题返回 1。
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.menu_service import MENUS

SPECIAL = {'__OUT__', '__DROP__'}


def check(menu):
    """返回 [(问题类型, 说明), ...]"""
    found = []
    cats = {c for c, _ in menu.items}

    pos_owner = {}
    name_cats = {}
    for cat, dishes in menu.items:
        for name, _price, _unit, pos_names in dishes:
            name_cats.setdefault(name, []).append(cat)
            for pn in pos_names:
                pos_owner.setdefault(pn, set()).add(f'{cat}/{name}')

    for pn, owners in sorted(pos_owner.items()):
        if len(owners) > 1:
            found.append(('重复计数',
                          f'POS写法「{pn}」被这几道菜同时认领，销量会算两遍: '
                          + ' 、 '.join(sorted(owners))))

    for name, in_cats in sorted(name_cats.items()):
        if len(in_cats) > 1:
            found.append(('菜名重复',
                          f'「{name}」出现在 ' + ' 、 '.join(in_cats)))

    def check_target(where, target):
        if target not in SPECIAL and target not in cats:
            found.append(('静默丢数据',
                          f'{where} 指向「{target}」，但菜单里没有这个分类，命中的菜会消失'))

    for pos_cat, target in sorted(menu.cat_map.items()):
        check_target(f'cat_map「{pos_cat}」', target)
    for dish, target in sorted(menu.force_cat.items()):
        check_target(f'force_cat「{dish}」', target)
    for rule in menu.route_rules:
        check_target('route_rule', rule.get('target'))
    if menu.main_section:
        check_target('main_section', menu.main_section)
    if menu.addon_section:
        check_target('addon_section', menu.addon_section)
    for section in sorted(menu.pos_native_sections):
        check_target('pos_native_section', section)

    for name in sorted(menu.drop_names):
        if name in name_cats:
            found.append(('自相矛盾', f'「{name}」既列在菜单里，又被 drop_name 丢弃'))

    return found


def main():
    total = 0
    for key in sorted(MENUS):
        problems = check(MENUS[key])
        if not problems:
            print(f'  OK   {key}')
            continue
        total += len(problems)
        print(f'  !!   {key}  ({len(problems)} 处)')
        for kind, msg in problems:
            print(f'         [{kind}] {msg}')

    print()
    if total:
        print(f'{len(MENUS)} 套菜单配置，发现 {total} 处问题')
        return 1
    print(f'{len(MENUS)} 套菜单配置，全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())
