# -*- coding: utf-8 -*-
"""
餐厅菜单注册表（配置驱动版）

每家餐厅的全部配置放在 app/data/menus/<key>/ 目录下的 CSV 里：
  menu.csv             菜单主表
  config.csv           其余规则

加新餐厅（不用写代码）：
1. 在 data/menus/ 下新建一个目录（目录名 = 餐厅 key）
2. 参照现有餐厅放入 menu.csv 和 config.csv
3. 前端 QS_STORES 给对应店铺设置 restaurant: '<key>'

启动时自动扫描 data/menus/ 下所有含 menu.csv 的目录完成注册。
"""
import os

from app.models.menu import Menu
from app.services.loader import load_menu_dir

_DATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'menus')
_DATA_ROOT = os.path.normpath(_DATA_ROOT)


def discover_menus() -> dict:
    menus = {}
    if not os.path.isdir(_DATA_ROOT):
        return menus
    for name in sorted(os.listdir(_DATA_ROOT)):
        d = os.path.join(_DATA_ROOT, name)
        if os.path.isdir(d) and os.path.exists(os.path.join(d, 'menu.csv')):
            try:
                menus[name] = load_menu_dir(d)
            except Exception as e:
                raise RuntimeError(f'加载餐厅配置「{name}」失败: {e}') from e
    return menus


MENUS = discover_menus()


def get_menu(restaurant_type: str) -> Menu:
    if restaurant_type not in MENUS:
        available = ', '.join(MENUS.keys())
        raise ValueError(
            f"餐厅类型「{restaurant_type}」尚未配置，当前可用: {available}。"
            "请先在 app/data/menus/ 下添加该餐厅的配置目录。"
        )
    return MENUS[restaurant_type]
