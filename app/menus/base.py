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
    short_name: str = ''             # 短名（用于 Excel sheet 命名），例如 '天天'。空 = 用 brand
    store_overrides: dict = field(default_factory=dict)
    # store_overrides 结构：
    #   { '店铺name': { '菜单显示名': ['补充的 POS 项目名1', '补充2', ...] } }
    # 例: { '香港天天沙田': { '酥炸椒鹽板豆腐': ['酥炸椒鹽豆腐'] } }
    # 表示沙田店在 POS 里把这道菜叫「酥炸椒鹽豆腐」（不带"板"字），
    # 用本字段告诉程序把它合并进「酥炸椒鹽板豆腐」的销量统计。

    delivery_platforms: dict = field(default_factory=lambda: {
        'KT': ['KT'],
        'FP': ['FP'],
    })
    # POS「分类」列里出现 markers 中任意一个，就视为外卖；
    # platform 名（字典 key）会作为右侧外卖区的分组标题。
    # 天天: {'KT':['KT'],'FP':['FP']}
    # 阿城: {'Keeta':['KT','Keeta'],'Foodpanda':['FP','【外']}

    adjust_marker: str = None
    # POS「分类」列含这个子串的行 = 补差价（如阿城的「Keeta 手寫單」）。
    # 不算正常外卖销量、不参与堂食、不丢弃，单列在所属平台末尾的「補差價」段。
    # None = 该餐厅没有补差价概念。

    pos_aliases: dict = field(default_factory=dict)
    # 额外的 POS 项目名 → 显示名映射，用于「菜单未列但希望中文显示」的项目。
    # 典型场景：泰菜 Set 套餐（Ka Prao Pork+ Drink → 雙蛋打拋飯(豬) + 飲料）。
    # 仅影响显示，不参与菜单内 / 菜单外的归类逻辑（菜单未列的依然算菜单外）。

    addon_categories: set = field(default_factory=set)
    # 「点选拆分」的 POS 分类集合（如四季芬芳「米線$6餸」「米線$9餸」…）。
    # 同一 POS 项目在同一分类下会有 价>0（顾客单点收费）和 价=0（套餐内含免费）两行。
    # 设置后，addon_section 菜单段的每个加料会显示：
    #   數量列 = 收费版 qty、金額列 = 收费版 amt、名字后附「套餐內含 N次」
    # 收费与套餐内含两者都计入 dinein 总数。

    addon_section: Optional[str] = None
    # 与 addon_categories 配对的菜单分类名（如 '自選菜式(加料)'）。
    # 该菜单段的每个 item 走拆分显示逻辑。

    @property
    def all_delivery_markers(self) -> list:
        """所有平台 markers 扁平化, 用于「这一行是否属于外卖」的判断。"""
        out = []
        for markers in self.delivery_platforms.values():
            out.extend(markers)
        return out

    def is_delivery_category(self, cat: str) -> bool:
        if not isinstance(cat, str):
            return False
        return any(m in cat for m in self.all_delivery_markers)

    def classify_platform(self, cat: str):
        """该分类属于哪个平台；不属于任何平台返回 None。"""
        if not isinstance(cat, str):
            return None
        for platform, markers in self.delivery_platforms.items():
            if any(m in cat for m in markers):
                return platform
        return None

    def is_adjust_category(self, cat: str) -> bool:
        """这一行是否补差价。需要 adjust_marker 设置过。"""
        if not self.adjust_marker or not isinstance(cat, str):
            return False
        return self.adjust_marker in cat

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
