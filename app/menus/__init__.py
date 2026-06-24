# -*- coding: utf-8 -*-
"""
餐厅菜单注册表（配置驱动版）

每家餐厅的全部配置放在 app/menus/data/<key>/ 目录下的 CSV 里：
  menu.csv             菜单主表（分类/菜名/价格/单位/POS写法）
  config.csv           其余规则（外卖标记、丢弃分类、cat_map、关键词……）
  store_overrides.csv  可选。单店特殊 POS 写法补丁

加新餐厅（不用写代码）：
1. 在 data/ 下新建一个目录（目录名 = 餐厅 key，如 yizheng）
2. 参照现有餐厅放入 menu.csv 和 config.csv（格式见 docs/菜单配置表说明.md）
3. 前端 QS_STORES 给对应店铺设置 restaurant: '<key>'

启动时自动扫描 data/ 下所有含 menu.csv 的目录完成注册。
"""
import os

from .base import Menu
from .loader import load_menu_dir

_DATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def _discover() -> dict:
    menus = {}
    for name in sorted(os.listdir(_DATA_ROOT)):
        d = os.path.join(_DATA_ROOT, name)
        if os.path.isdir(d) and os.path.exists(os.path.join(d, 'menu.csv')):
            try:
                menus[name] = load_menu_dir(d)
            except Exception as e:
                raise RuntimeError(f'加载餐厅配置「{name}」失败: {e}') from e
    return menus


MENUS = _discover()


def get_menu(restaurant_type: str) -> Menu:
    """根据餐厅类型 key 返回对应的 Menu 实例"""
    if restaurant_type not in MENUS:
        available = ', '.join(MENUS.keys())
        raise ValueError(
            f"餐厅类型「{restaurant_type}」尚未配置，当前可用: {available}。"
            "请先在 app/menus/data/ 下添加该餐厅的配置目录。"
        )
    return MENUS[restaurant_type]
