"""
菜单数据结构

每个餐厅一份菜单配置文件（app/menus/<restaurant>.py），
里面定义 MENU / DROP_CATEGORIES_DINEIN / STORE_OVERRIDES 三块数据，
最后封装成一个 Menu 实例供 transformer 使用。
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Menu:
    """一类餐厅的菜单配置"""

    brand: str                       # 餐厅品牌显示名，例如 '天天Authentic'
    items: list                      # MENU 结构：[(分类, [(菜名, 价格, 单位, [POS项目名变体]), ...]), ...]
    drop_categories: set             # 堂食「菜單外」要丢弃的 POS 分类
    store_overrides: dict = field(default_factory=dict)
    # store_overrides 结构：
    #   { '店铺name': { '菜单显示名': ['补充的 POS 项目名1', '补充2', ...] } }
    # 例: { '香港天天沙田': { '酥炸椒鹽板豆腐': ['酥炸椒鹽豆腐'] } }
    # 表示沙田店在 POS 里把这道菜叫「酥炸椒鹽豆腐」（不带"板"字），
    # 用本字段告诉程序把它合并进「酥炸椒鹽板豆腐」的销量统计。

    def items_for_store(self, shop_name: Optional[str] = None) -> list:
        """
        返回应用了门店补丁后的 MENU 结构，
        外形和 self.items 完全一致：[(分类, [(菜名, 价格, 单位, [POS项目名变体]), ...]), ...]
        transformer 直接用返回值替代原来的 MENU 常量即可。
        """
        overrides = self.store_overrides.get(shop_name, {}) if shop_name else {}
        result = []
        for cat, dishes in self.items:
            patched_dishes = []
            for name, price, unit, pos_names in dishes:
                extra = overrides.get(name, [])
                patched_pos = list(pos_names) + list(extra)
                patched_dishes.append((name, price, unit, patched_pos))
            result.append((cat, patched_dishes))
        return result

    def collect_used_names(self, shop_name: Optional[str] = None) -> set:
        """收集所有菜单菜品引用的 POS 项目名（含门店补丁）"""
        used = set()
        for cat, dishes in self.items_for_store(shop_name):
            for name, price, unit, pos_names in dishes:
                used.update(pos_names)
        return used
