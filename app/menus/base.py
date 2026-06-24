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

    cat_map: dict = field(default_factory=dict)
    # POS 「菜品大类」→ 菜单分类名 的映射，用于「菜单外的新菜要归到哪个菜单分类」。
    # 值可以是: 菜单分类名 / '__OUT__'（菜單外）/ '__DROP__'（丢弃）。
    # 例（海口）: {'平台套餐': '__OUT__', '新加坡咖喱系列': '猪肉&牛肉系列', '餐具选择': '__DROP__'}
    # 没在 cat_map 里的 POS 大类，新菜默认归「菜單外」。

    force_cat: dict = field(default_factory=dict)
    # POS 菜名 → 菜单分类名 的强制覆盖，**仅对未匹配菜单的"新菜"生效**，优先级高于 cat_map。
    # 用于纠正 POS 把菜放错大类的情况（如海口的 黄咖喱小青龙 实际是龙虾 → '海鲜系列'）。

    drop_names: set = field(default_factory=set)
    # 按 POS 菜名直接丢弃（与分类无关）。
    # 例（海口）: {'打包盒', '纸巾', '虾片0元'} ——「其他」分类里这几项 0 营销值要扔掉。

    main_section: Optional[str] = None
    # 「单品饭/面优先归此分类」机制的目标分类（例：内地天天的 '主食系列'）。
    # 当 cat_map 把某新菜路由到 '__OUT__'（套餐分类）但菜名包含 main_keywords 中任一
    # 且不含 set_keywords 中任一时，强制改路由到 main_section，作为🆕新菜显示。
    # 用途：套餐分类里其实是单品饭/面的菜（如 招牌套餐 下的「冬阴功汤面」「黄咖喱牛脸肉饭」）
    # 应归到主食系列展示；带「+」「套餐」「双人」等套餐字样的留在菜单外。

    main_keywords: set = field(default_factory=set)
    # 「单品主食」识别关键字（如 {'饭','面','粉丝','炒粉','炒米','麵','飯'}）。

    set_keywords: set = field(default_factory=set)
    # 「套餐」识别关键字（如 {'套餐','+','＋','双人','四人','单人','多人','双拼','双飞',
    # 'Plus｜','plus｜','精选','超值','工作日','人气','抖音'}）。
    # 名字含其中任一 = 视为套餐，不走 main_section 重定向。

    pos_native_sections: set = field(default_factory=set)
    # 「POS 原生分类」：菜单 PDF 没有列具体菜品、整段以 POS 实际项目为准的分类。
    # 例（深圳阿城）: {'12元精选卤味', '特色卤味', '麻辣卤味', '手作系列'}
    # 这些分类在 MENU 里 items=[]，所有 cat_map 路由到此的项目作为本段的正式内容显示：
    #   - 不打 🆕 标签 (不是「菜单未列的新菜」，而是该分类的全部内容)
    #   - 行不上黄底
    #   - POS 大类原名作为段标题旁的小灰字注解

    route_rules: list = field(default_factory=list)
    # 「按名字模式归类」规则（force_cat 的批量版，免去一个个列菜名）。
    # 每条 = dict，可含: target(必填,目标分类) / cat(限定POS大类) /
    #   startswith / contains / endswith（名字条件，可多个，全部满足才命中）。
    # 优先级在精确 force_cat 之后、cat_map 之前；按列表顺序第一条命中即用。
    # 例（阿城套餐价滷味）: {'target':'滷味','cat':'1人套餐','startswith':'滷鵝','contains':'$'}
    #   —— POS大类「1人套餐」里、名字以「滷鵝」开头且含「$」的项目，全部归「滷味」。

    extras_merge: dict = field(default_factory=dict)
    # 「菜單外大类合并」：{ 源POS大类: 目标显示大类 }。
    # 菜單外里源大类的项目改挂到目标大类下、同名项按销量求和(目标大类可以是已存在的另一个菜單外大类)。
    # 例（天天）: {'7點後招牌海南雞飯': '午餐'} —— 7點後那段并入午餐，同名菜(午A/午B…)数量金额相加。

    extras_item_merge: dict = field(default_factory=dict)
    # 「按菜名的菜單外路由」：{ 菜名: 目标显示大类 }，优先级高于 extras_merge(按大类)。
    # 用于某道菜不该跟着它的大类走。例（天天）: {'黃金限定2人套餐328': '套餐'}
    #   —— 它虽在「7點後招牌海南雞飯」(整体并入午餐)，但按名归到「套餐」段，与同名项合并。

    strip_tokens: set = field(default_factory=set)
    # 「匹配时忽略的描述词」：匹配前先把这些子串从 POS 项目名称里删掉，
    # 让加了无关后缀的项目能对上菜单标准名。
    # 例（天天）: {'（不能走甜）'} —— 「凍-檸檬薏米水（不能走甜）」去掉后缀=「凍-檸檬薏米水」，匹配上菜单。

    strip_regex: set = field(default_factory=set)
    # 「条件式正则去后缀」：删掉匹配部分后『能对上某菜单POS写法 或 数据里已存在的干净名』才删，否则保留。
    # 用于变化的后缀(如平台价)，只在"干净版存在、可合并"时才去，避免误删孤立的带价名。
    # 例（天天）: {'=?\\d+$'} —— 龍眼冰=20→龍眼冰(菜单有,合并)；星洲甄選2人餐499→星洲甄選2人餐(数据有干净版,合并)；
    #   獅城兩人套餐599→不变(无干净版)。

    pos_renames: dict = field(default_factory=dict)
    # 「统一写法」：{ 原POS写法: 统一成的名字 }。匹配/聚合前先把原写法整体改名，
    # 用于错字、字序颠倒、旧名等无法用去后缀处理的情况（不限菜单内/外，改完一起算）。
    # 例（天天）: {'鮮無果花燉雞湯':'鮮無花果燉雞湯', '鮮無花果雞湯':'鮮無花果燉雞湯'}
    #   —— 两个错写的「無花果燉雞湯」统一成正确写法后，在「湯品」里合并成一行。

    auto_match_category: bool = False
    # 「POS大类同名归菜单」：未匹配项若其 POS 大类名 == 某菜单分类名，自动归入该分类(🆕)，
    # 不必为每个同名大类单独写 cat_map。优先级低于显式 cat_map。
    # 例（天天）: POS大类「湯品/主食/甜品」自动归入菜单同名分类。

    drop_zero_amount: bool = True
    # 「丢弃金额为0的堂食行」：某项有销量但金额=0(白送的赠品/打卡/钱已算进套餐)，剔除不显示。
    # 默认开启，对所有餐厅生效；个别店如需保留 ¥0 行可在 config.csv 写 drop_zero_amount,,0 关闭。
    # 注意：四季芬芳的加料拆分(addon)故意用¥0行表达"套餐内含"，走单独路径(addon_lookup)不受此影响。

    def _menu_cat_names(self) -> set:
        names = getattr(self, '_cat_names_cache', None)
        if names is None:
            names = {cat for cat, _ in self.items}
            self._cat_names_cache = names
        return names

    def _match_rule(self, name: str, pos_cat: str):
        """返回第一条命中的 route_rule 的目标分类；都不中返回 None。"""
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
        """
        判断某 POS 菜（未匹配菜单的新菜）应去向。
        返回:
          - '__DROP__' / None: 应该丢弃
          - '__OUT__': 入「菜單外」（保留原 POS 大类作为段标题）
          - 其他字符串: 入此菜单分类（作为 🆕 新菜）

        优先级:
          1. drop_names 命中 → DROP
          2. force_cat 命中 → 用强制分类（精确菜名，最高优先，纠正 POS 错放）
          3. route_rules 命中 → 用规则目标分类（按名字模式批量归类）
          4. set_keywords 命中 → __OUT__（套餐字样的统一进菜單外，
             即便 cat_map 把大类映到具体菜单分类也强制覆盖）
          5. cat_map → 取大类映射结果（默认 __OUT__）
          6. 若 (5) = __OUT__ 且菜名是「单品饭/面」(含 main_keywords) →
             改路由到 main_section（套餐分类下的单品菜归主食）
        """
        if name in self.drop_names:
            return '__DROP__'
        # force_cat 最高优先级：对具体菜的精确纠正（如 酥炸椒盐板豆腐 强制归前菜）
        if name in self.force_cat:
            return self.force_cat[name]
        # route_rules：按名字模式批量归类（force_cat 的模式版），优先于 cat_map
        rule_target = self._match_rule(name, pos_cat)
        if rule_target:
            return rule_target
        # set_keywords：套餐字样统一进菜单外（不管 cat_map 怎么映）
        if self.set_keywords and any(k in name for k in self.set_keywords):
            return '__OUT__'
        # cat_map：POS 大类 → 菜单分类（显式优先）
        target = self.cat_map.get(pos_cat)
        if target is None:
            # auto_match_category：POS 大类名本身就是某菜单分类名 → 归该分类
            if self.auto_match_category and pos_cat in self._menu_cat_names():
                target = pos_cat
            else:
                target = '__OUT__'
        # 套餐分类下的单品饭/面优先归主食系列
        if (target == '__OUT__' and self.main_section
                and any(k in name for k in self.main_keywords)):
            return self.main_section
        return target

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
