"""
菜单数据结构

每个餐厅一份菜单配置，封装成 Menu 实例供 transformer 使用。
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Menu:
    """一类餐厅的菜单配置"""

    brand: str                       # 餐厅品牌显示名，例如 '天天Authentic'
    items: list                      # MENU 结构：[(分类, [(菜名, 价格, 单位, [POS项目名变体]), ...]), ...]
    drop_categories: set             # 堂食「菜單外」要丢弃的 POS 分类
    short_name: str = ''             # 短名（用于 Excel sheet 命名），例如 '天天'。空 = 用 brand
    store_overrides: dict = field(default_factory=dict)
    delivery_platforms: dict = field(default_factory=lambda: {
        'KT': ['KT'],
        'FP': ['FP'],
    })
    adjust_marker: str = None
    pos_aliases: dict = field(default_factory=dict)
    addon_categories: set = field(default_factory=set)
    addon_section: Optional[str] = None
    cat_map: dict = field(default_factory=dict)
    force_cat: dict = field(default_factory=dict)
    drop_names: set = field(default_factory=set)
    main_section: Optional[str] = None
    main_keywords: set = field(default_factory=set)
    set_keywords: set = field(default_factory=set)
    pos_native_sections: set = field(default_factory=set)
    route_rules: list = field(default_factory=list)
    extras_merge: dict = field(default_factory=dict)
    extras_item_merge: dict = field(default_factory=dict)
    strip_tokens: set = field(default_factory=set)
    strip_regex: set = field(default_factory=set)
    pos_renames: dict = field(default_factory=dict)
    auto_match_category: bool = False
    drop_zero_amount: bool = True

    def _menu_cat_names(self) -> set:
        names = getattr(self, '_cat_names_cache', None)
        if names is None:
            names = {cat for cat, _ in self.items}
            self._cat_names_cache = names
        return names

    def _match_rule(self, name: str, pos_cat: str):
        for r in self.route_rules:
            if r.get('cat') and pos_cat != r['cat']:
                continue
            if r.get('startswith') and not name.startswith(r['startswith']):
                continue
            if r.get('contains') and r['contains'] not in name:
                continue
            if r.get('endswith') and not name.endswith(r['endswith']):
                continue
            return r.get('target')
        return None

    def route_new_item(self, name: str, pos_cat: str) -> Optional[str]:
        if name in self.drop_names:
            return '__DROP__'
        if name in self.force_cat:
            return self.force_cat[name]
        rule_target = self._match_rule(name, pos_cat)
        if rule_target:
            return rule_target
        if self.set_keywords and any(k in name for k in self.set_keywords):
            return '__OUT__'
        target = self.cat_map.get(pos_cat)
        if target is None:
            if self.auto_match_category and pos_cat in self._menu_cat_names():
                target = pos_cat
            else:
                target = '__OUT__'
        if (target == '__OUT__' and self.main_section
                and any(k in name for k in self.main_keywords)):
            return self.main_section
        return target

    @property
    def all_delivery_markers(self) -> list:
        out = []
        for markers in self.delivery_platforms.values():
            out.extend(markers)
        return out

    def is_delivery_category(self, cat: str) -> bool:
        if not isinstance(cat, str):
            return False
        return any(m in cat for m in self.all_delivery_markers)

    def classify_platform(self, cat: str):
        if not isinstance(cat, str):
            return None
        for platform, markers in self.delivery_platforms.items():
            if any(m in cat for m in markers):
                return platform
        return None

    def is_adjust_category(self, cat: str) -> bool:
        if not self.adjust_marker or not isinstance(cat, str):
            return False
        return self.adjust_marker in cat

    def items_for_store(self, shop_name: Optional[str] = None) -> list:
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
        used = set()
        for cat, dishes in self.items_for_store(shop_name):
            for name, price, unit, pos_names in dishes:
                used.update(pos_names)
        return used

    def find_duplicate_pos_names(self, shop_name: Optional[str] = None) -> list:
        """检测同一个 POS 写法被多个菜单项引用的问题（会导致销量/金额重复计算）。

        返回: [{'pos_name': str, 'dishes': [菜名...], 'categories': [分类...]}, ...]
        """
        usage = {}
        for cat, dishes in self.items_for_store(shop_name):
            for name, price, unit, pos_names in dishes:
                for pn in pos_names:
                    usage.setdefault(pn, []).append((cat, name))
        return [
            {'pos_name': pn, 'dishes': [d for _, d in entries],
             'categories': sorted({c for c, _ in entries})}
            for pn, entries in usage.items() if len(entries) > 1
        ]
