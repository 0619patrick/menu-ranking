"""
中環泰菜 Here Thai 菜单配置（第 3 类餐厅）

POS 平台：餐飲王（与天天/阿城共用同一适配器）
外卖标识：分类名含 'Take' 或 'take'（全角/半角均有）
补差价：分类含 '手寫單'（如「外賣手寫單」，金额为负数）

特点：
- 无茶位（直接「大MENU」开始）
- POS 菜名全部英文（与阿城中文不同）
- 显示名 = 菜单 PDF 中英文对照名
- POS 名 = POS 英文简化名（含若干拼写错误，必须按 POS 实际写法匹配）
  已知拼写差异：Wagye（应为 Wagyu）、Lenon（Lemon）、lce（Ice，小写 l）
"""
from .base import Menu


BRAND_NAME = '中環泰菜 Here Thai'


# ===========================================
# 菜单数据
# 每项: (菜名显示, 价格, 单位, [POS项目名变体列表])
# 显示名 = 菜单 PDF 中英文对照名
# POS 名 = POS 系统英文简写（含拼写错误，按实际填写）
# 泰菜无茶位
# ===========================================
MENU = [
    ('前菜小食-凍菜 Cold Dishes', [
        ('泰式雞蛋沙律 Thai Style Egg Salad',                68, '份', ['Egg Salad']),
        ('鹹蛋木瓜沙律 Papaya Salad with Salted Egg',        88, '份', ['Papaya Salad Salted Egg']),
        ('泰式生蝦 Thai Style Raw Shrimp',                   98, '份', ['Thai Style Raw Shrimp']),
        ('香煎扇貝佐椰漿汁 Seared Scallops Coconut Sauce',  108, '份', []),  # 4月无销量
    ]),
    ('前菜小食-熱菜 Hot Dishes', [
        ('泰式醬蝦多士 Thai Shrimp Toast with Chili Dip',          88, '份', ['Thai Shrimp Toast with Chili dip']),
        ('魚露燜雞 Braised Chicken in Fish Sauce',                  88, '份', ['Braised Chicken']),
        ('脆皮豬五花佐海鮮醬 Crisp Pork Belly and Sea Food Sauce',  98, '份', ['Crisp Pork Belly']),
        ('泰式肉碎生菜包 Pork Laab',                                98, '份', ['Pork Laab']),
        ('羅望子脆炸羅氏蝦 Crispy Prawns in Tamarind Sauce',       138, '份', ['Crispy Prawns']),
    ]),
    ('湯 Soup', [
        ('冬蔭功湯 Tom Yum Kung Soup',                  78, '份', ['Tom Yum Kung Soup']),
        ('泰式酸辣牛肉湯 Thai Hot and Sour Beef Soup', 108, '份', ['Thai Hot sour beef soup']),
    ]),
    ('主食麵 Main Noodle', [
        ('泰式豬肉湯麵 Thai Style Pork Noodles',                  98, '份', ['Thai Style Pork Noodles']),
        ('招牌炸雞椰奶雞湯麵 Deep Fried Chicken Tom Kah Noodles',  98, '份', ['Deep Fried Chicken,Tom Kah Noodles']),
        ('海鮮冬蔭功麵 Seafood Tom Yum Goong Noodles',            108, '份', ['Seafood Tom Yum Goong Noodles']),
        ('牛肉船麵 Beef Boat Noodles',                            108, '份', ['Beef Boat Noodles']),
        ('泰式骨髓牛肉拌麵 Beef Bone Marrow Dried Noodles',       168, '份', ['Beef Bone Marrow Dried Noodles']),
        ('招牌牛肋骨船麵 Beef Short Rib Boat Noodles',            228, '份', ['Beef Short Rib Boat Noodle']),
    ]),
    ('主食鑊 Main Wok', [
        ('蔬菜炒寬河粉 Fried Flat Noodles with Vegetables',                 88, '份', ['Fried Flat Noodle with Vegetables']),
        ('雙蛋打拋飯(豬) Ka Prao Minced Pork with Two Duck Eggs',           98, '份', ['Ka Prao Minced Pork, 2 Duck Eggs']),
        ('豬頸肉炒飯 Pork Neck Fried Rice',                                 98, '份', ['Pork Neck Fried Rice']),
        ('雙蛋打拋飯(牛) Ka Prao Minced Beef with Two Duck Eggs',          108, '份', ['Ka Prao Minced Beef, 2 Duck Eggs']),
        ('泰式海鮮炒寬河粉 Thai Style Fried Flat Noodles with Seafood',    128, '份', ['Thai Style Fried Flat Noodle with Seafood']),
        ('泰式羅氏蝦炒金邊粉 Pad Thai with Grilled River Prawns',          138, '份', ['Pad Thai Grilled River Prawn']),
        ('蟹肉炒飯 Crab Fried Rice',                                       168, '份', ['Crab Fried Rice']),
    ]),
    ('精選菜式 Special Dishes', [
        ('泰式海南雞飯 Thai Style Chicken Rice',                98, '份', ['Thai Style Chicken Rice']),
        ('冬蔭功海鮮粥(僅晚餐) Tom Yum Seafood Congee',       188, '份', ['Tom Yam Seafood Congee']),
    ]),
    ('蔬菜 Vegetable', [
        ('泰式炒通菜 Thai Stir Fried Morning Glory',     78, '份', ['Thai Stir Fried Morning Glory']),
        ('蒜香西蘭花苗 Stir Fried Broccoli with Garlic', 88, '份', ['Stir Fried Broccoli With Garlic']),
    ]),
    ('甜品 Dessert', [
        ('椰子紙杯蛋糕 Coconut Cupcake',     48, '份', ['Coconut Cupcake']),
        ('泰式椰奶湯圓 Bua Loi',             68, '份', ['Bua Loi']),
        ('奶凍 Egg Custard',                 68, '份', ['Egg Custard']),
        ('金芒配魚露 Mango with Fish Sauce', 78, '份', ['Mango w/ Fish Sauce']),
    ]),
    ('蓋澆飯(僅午餐) Topped Rice', [
        ('鹹魚肉丸蓋澆飯 Fried Salted Fish Pork Ball',                88, '份', []),   # 4月无销量
        ('香脆雞肉咖喱醬蓋澆飯 Crisp Chicken Ka Prao Sauce',           88, '份', ['Crisp Chicken ka prao sauce']),
        ('魚肉丸綠咖喱醬蓋澆飯 Minced Fish Ball Green Curry Sauce',    98, '份', ['Minced Fish Ball Green Curry']),
        ('香脆五花肉咖喱醬蓋澆飯 Crisp Pork Belly Ka Prao Sauce',      98, '份', ['Crisp Pork Belly  ka prao sauce']),
        ('紅燒牛肉蓋澆飯 Braised Beef',                               108, '份', ['Braised Beef']),
        ('白蝦軟煎蛋蓋澆飯 White Shrimp Soft Omelette',               128, '份', ['White Shrimp Soft Omelette']),
        ('蟹肉軟煎蛋蓋澆飯 Crab Soft Omelette',                       148, '份', ['Crab Soft Omelette']),
    ]),
    # ---- 火鍋（晚餐限定）----
    # 按官方菜單分 5 段：湯底 / 肉海鮮套餐 / 海鮮 / 牛豬 / 蔬菜 / 配菜
    # 注意：POS Vegetables(复数)=炒青菜，Vegetable(单数)=火锅蔬菜，两者不同
    ('泰式火鍋-湯底(僅晚餐) Hot Pot Soup', [
        ('泰式船麵湯 Boat Noodles Soup',            58, '份', ['Boat Noodle Soup']),
        ('泰式豬肉湯 Pork Bone Soup',               58, '份', ['Pork Soup']),
        ('泰式冬蔭功湯 Tom Yum Goong Soup',         58, '份', ['Tom Yum Goong Soup']),
        # POS 实际名含全角右括号）
        ('椰奶雞湯 Tom Kah Coconut Soup',           58, '份', ['Tom Kah(Coconut Soup）']),
        ('礦泉水(湯底) Mineral Water',              58, '份', []),   # 4月无销量
    ]),
    ('火鍋-肉/海鮮套餐 Meat/Seafood Set', [
        ('海鮮套餐 Seafood Set',                              168, '份', ['Seafood']),
        ('日式和牛肩胛肉套餐(150g) Japanese Wagyu Chuck Roll', 208, '份', ['Japanese Wagye Chuck Roll 150g']),
        ('日式和牛肩胛肉套餐(250g) Japanese Wagyu Chuck Roll', 328, '份', ['Japanese Wagye Chuck Roll 250g']),
        ('美國牛板腱肉套餐(150g) US Beef Oyster Blade',        138, '份', ['US Beef Oyster Blade 150g']),
        ('美國牛板腱肉套餐(250g) US Beef Oyster Blade',        238, '份', ['US Beef Oyster Blade 250g']),
        ('美國牛肩胛肉套餐(150g) US Beef Chuck Roll',          128, '份', ['US Beef Chuck Roll 150g']),
        ('美國牛肩胛肉套餐(250g) US Beef Chuck Roll',          208, '份', ['US Beef Chuck Roll 250g']),
        ('牛五花肉套餐(150g) Beef Short Plate',                108, '份', ['Beef Short Plate 150g']),
        ('牛五花肉套餐(250g) Beef Short Plate',                168, '份', ['Beef Short Plate 250g']),
        ('日式豬裏脊肉套餐(150g) Japanese Pork Loin',          108, '份', ['Japanese Pork Loin 150g']),
        ('日式豬裏脊肉套餐(250g) Japanese Pork Loin',          168, '份', ['Japanese Pork Loin 250g']),
        ('蔬菜套餐 Vegetable Set Meal',                         78, '份', ['vegetable']),
    ]),
    ('火鍋-海鮮 Hot Pot Seafood', [
        ('魚丸 Fish Balls',                                   38, '份', ['Fish Balls']),
        ('脆炸鮮蝦魚卷 Minced Shrimp with Capelin Roll',      38, '份', []),   # 4月无销量
        ('牡蠣 Oyster',                                       38, '份', ['Oyster']),
        ('鮑魚 Abalone',                                      38, '份', ['Abalone']),
        ('扇貝 Scallop',                                      38, '份', ['Scallop']),
        ('虎蝦 Tiger Prawn',                                  68, '份', []),   # 4月无销量
    ]),
    ('火鍋-牛豬 Hot Pot Beef/Pork', [
        ('豬肉丸 Pork Meat Balls',  38, '份', ['Pork Meat Balls']),
        ('牛肉丸 Beef Meat Balls',  38, '份', ['Beef Meat Balls']),
        ('牛舌 Beef Tongue',        88, '份', []),   # 4月无销量
    ]),
    ('火鍋-蔬菜 Hot Pot Vegetables', [
        ('雞蛋 Chicken Eggs',                  8, '份', []),   # 4月无销量
        ('豆腐 Tofu',                         18, '份', ['Tofu']),
        ('靈芝菇 Shimeji Mushroom',           18, '份', ['Shimeji Mushroom']),
        ('秀珍菇 Bhutan Oyster Mushroom',     18, '份', []),   # 4月无销量
        ('生菜 Lettuce',                      18, '份', ['Lettuce']),
        ('卷心菜絲 Sliced Cabbage',           18, '份', ['Sliced Cabbage']),
        ('金針菇 Enoki Mushroom',             18, '份', ['enoki mushroom']),
        ('粟米筍 Baby Corn',                  18, '份', ['Baby Corn']),
        ('卷心菜 Cabbage',                    18, '份', ['Cabbage']),
    ]),
    ('火鍋-配菜 Hot Pot Sides', [
        ('粉絲 Vermicelli',           18, '份', ['Vermicelli']),
        ('泰式米粉 Rice Noodles',     18, '份', ['Rice Noodles']),
        ('白飯 Plain Rice',           18, '份', ['Plain Rice']),
        ('雞油飯 Chicken Oil Rice',   28, '份', ['Chicken Rice']),
        ('河粉 Flat Noodles',         18, '份', ['Flat Noodles']),
    ]),
    # ---- 泰式燒烤（晚餐限定）----
    ('泰式燒烤(僅晚餐) Thai BBQ', [
        ('烤翠玉瓜 Grilled Zucchini',                       18, '串', ['Grilled Zucchini']),
        ('烤年糕 Grilled Rice Cake',                         18, '串', ['Grilled Rice Cake']),
        ('烤糯米飯配雞蛋 Grilled Sticky Rice with Egg',     18, '串', ['Grilled Sticky Rice with Egg']),
        ('烤秋葵佐辣椒豆醬 Grilled Okra/Chili Beans Paste', 18, '串', ['Grilled Okra with Chili Bean Paste']),
        ('烤蔬菜串 Vegetable Skewers',                       18, '串', ['Vegetable Skewers']),
        ('烤魚丸 Grilled Fish Ball',                         22, '串', ['Grilled Fish Ball']),
        ('烤雞翅 Grilled Chicken Wing',                      24, '串', ['Grilled Chicken Wing']),
        ('烤雞髀 Grilled Chicken Thighs Tentacles',         24, '串', ['Grilled Chicken Thigh']),
        ('免治雞肉雞軟骨串 Grilled Minced Chicken',          24, '串', ['Grilled Minced Chicken w/ Cartilage']),
        ('京蔥雞腿肉 Grilled Chicken Thigh with Leek',       24, '串', ['Grilled Chicken Tight with Leek']),
        ('烤豬頸肉 Grilled Pork Neck',                       24, '串', ['Grilled Pork Neck']),
        ('免治豬肉大蔥 Grilled Minced Pork',                 28, '串', ['Grilled Chili Minced Pork Skewer']),
        ('烤免治牛肉 Grilled Minced Beef',                   28, '串', []),   # 4月无销量
        ('烤牛柳 Grilled Beef Tenderloin',                   28, '串', ['Grilled Beef Tenderloin']),
        ('香茅烤蝦餅 Grilled Lemongrass Shrimp Cake',        28, '串', ['Grilled Lemongrass Shrimp Cake']),
        ('烤鰻魚 Grilled Eel',                               28, '串', ['Grilled Eel']),
        ('烤小魷魚 Grilled Small Squid',                     28, '串', ['Grilled Small Squid Skewer']),
        ('烤章魚鬚 Grilled Octopus Tentacles',               28, '串', ['Grilled Octopus Tentacles']),
        ('烤生蠔 Grilled Oysters',                           38, '串', ['Grilled Oyster']),
        ('烤鮑魚 Grilled Abalone',                           38, '串', ['Grilled Abalone']),
        ('烤扇貝 Grilled Scallops',                          38, '串', ['Grilled Scallop']),
    ]),
    # ---- 飲品 ----
    # POS 把熱/凍拆开、汽水按品牌细分，菜单一项 → 多 POS 变体合并
    ('飲品 Drinks', [
        ('泰式奶茶 Thai Milk Tea(熱/凍)',
            28, '杯', ['Iced Thai Milk Tea', 'Hot Thai Milk Tea']),
        ('泰式牛奶咖啡 Thai Milk Coffee(熱/凍)',
            28, '杯', ['Iced Thai Milk Coffee', 'Hot Thai Milk Coffee']),
        # POS: Iced/Hot Thai Style Coconut Milk Coffee，价 34
        ('泰式椰奶咖啡 Thai Style Coconut Milk Coffee(熱/凍)',
            34, '杯', ['Iced Thai Style Coconut Milk Coffee', 'Hot Thai Style Coconut Milk Coffee']),
        ('蜂蜜檸檬水 Honey Lemonade(熱/凍)',
            28, '杯', ['Iced Honey Lemonade', 'Hot Honey Lemonade']),
        # POS 拼写 lce（小写 l 非大写 I）
        ('龍眼冰 Longan Ice',                                28, '杯', ['Longan lce']),
        ('菊花冰 Chrysanthemum Ice',                         28, '杯', ['Chrysanthemum lce']),
        # POS 拼写 Lenon（应为 Lemon）
        ('泰式手打檸檬茶 Thai Style Hand-Shaken Lemon Tea', 34, '杯', ['Thai Style Hand-Shaken Lenon Tea']),
        ('鮮椰子水 Fresh Coconut Water',                     38, '份', ['Fresh Coconut Water']),
        ('芒果冰沙 Mango Smoothie',                          48, '杯', ['Mango Smoothie']),
        # 汽水按品牌拆分，合并入一項
        ('汽水 Soft Drink(Coke/Sprite/Tonic/Soda)',          18, '罐', ['Coke', 'coke zero', 'Sprite', 'Soda', 'Tonic']),
        ('果汁 Juice(Orange/Apple/Cranberry)',               18, '杯', ['Orange Juice']),
        ('礦泉水/氣泡水 Acqua Panna/San Pellegrino(750mL)',  58, '瓶', ['Acqua Panna', 'San Pellegrino']),
        # 以下不在官方菜單，POS 独有
        ('泰式梳打青檸 Thai Chang Soda Lime',                22, '杯', ['Thai Chang Soda Water with Lime']),
    ]),
    # ---- 酒類 ----
    ('雞尾酒 Cocktails', [
        ('氈酒(Mix) Gin Mix',                       48, '杯', []),                                    # 4月无销量
        ('伏特加(Mix) Vodka Mix',                   48, '杯', ['Vodka Mix (300ml)']),
        ('蘭姆酒(Mix) Rum Mix',                     48, '杯', []),                                    # 4月无销量
        ('威士忌(Mix) Whisky Mix',                  48, '杯', ['Whisky Mix (300ml)']),
        ('白蘭地(Mix) Brandy Mix',                  48, '杯', []),                                    # 4月无销量
        ('薄荷莫希托(伏特加) Mint Mojito',          58, '杯', ['Mint Mojito(Vodka) (300ml)']),
        ('橙味莫希托(蘭姆酒) Orange Mojito',        58, '杯', []),                                    # 4月无销量
        ('暹羅梅子可林斯(氈酒) Siam Plum Collins',  58, '杯', ['Siam Plum Collins (Gin) (300ml)']),
        ('薑檸高球(威士忌) Ginger & Lime Highball', 58, '杯', ['Ginger & Lime Highball(Whisky) (300ml)']),
        ('考艾酸酒(白蘭地) Khao Yai Sour',          58, '杯', []),                                    # 4月无销量
        # POS 'man-coco' 推测为 Monk's Coco（僧侶椰子酒）
        ('僧侶椰子酒 Monk\'s Coco',                 58, '杯', ['man-coco']),
        ('仕女椰子酒 Lady\'s Coco',                 58, '杯', []),                                    # 4月无销量
    ]),
    ('泰國烈酒 Thai Spirit', [
        ('湄公酒(50mL) Mekhong',             58,  '杯', []),  # 4月无销量
        ('湄公酒(700mL) Mekhong',            398, '瓶', []),
        ('鐵球泰國氈酒(50mL) Iron Balls Gin', 98,  '杯', []),
        ('鐵球泰國氈酒(700mL) Iron Balls Gin', 1098, '瓶', []),
    ]),
    ('泰國葡萄酒 Thai Wine', [
        ('Classic White (150mL)',         48,  '杯', ['Classic White (150ml)']),
        ('Classic White (750mL)',        198,  '瓶', []),
        ('Classic Red (150mL)',           48,  '杯', ['Classic Red (150ml)']),
        ('Classic Red (750mL)',          198,  '瓶', []),
        ('Classic Rose (150mL)',          48,  '杯', []),
        ('Classic Rose (750mL)',         198,  '瓶', []),
        ('Devanom Kiaw Ngoo (150mL)',     88,  '杯', ['Devanom Kiaw Ngoo(150ml)']),
        ('Devanom Kiaw Ngoo (750mL)',    398,  '瓶', []),
        ('Devanom Jasmine (150mL)',       88,  '杯', ['Devanom Jasmine(150ml)']),
        ('Devanom Jasmine (750mL)',      398,  '瓶', []),
        ('Signature Sparkling Wine',     398,  '瓶', []),
        ('Cuvee Rouge Red',              698,  '瓶', ['Cuvee Rouge Red (750ml)']),
        ('Cuvee De Siam Blanc White',    698,  '瓶', []),
    ]),
    ('泰國啤酒 Thai Beer', [
        ('勝獅生啤(300mL) Singha Draft',     48, '杯', ['Singha Draft (300ml)']),
        ('勝獅生啤(500mL) Singha Draft',     68, '杯', ['Singha Draft (500ml)']),
        # 买一送一促销变体与正常价格相同，合并
        ('勝獅樽裝啤酒(330mL) Singha Bottle', 32, '瓶', ['Singha Bottle (330ml)', 'Singha Bottle  buy 1get 1 free']),
    ]),
]


# ===========================================
# 堂食「菜單外」要丢弃的 POS 分类
# MISC：49项零散简写代码（s/1/j/b等），¥7409，无意义
# General Meal Set Item：套餐内含项（¥5368）
# Drink Mod / Spice Level / No...：饮料改码/辣度/走料，金额均为0
# 注意：泰菜的改码类用英文命名，不像中文 POS 那样统一带「改碼」二字
# ===========================================
DROP_CATEGORIES_DINEIN = {
    'MISC',
    'General Meal Set Item',
    'Drink Mod',
    'Spice Level',
    'No...',
    # 零金额套餐占位分类
    'noodle shrimp cake set',
    'papaya green cury set',
    'tea set drink',
}


# 泰菜目前只有中環一家店，暂无 override
STORE_OVERRIDES: dict = {}


# ===========================================
# POS 套餐别名（菜单未列、但希望中文显示的项目）
# Set 套餐 = 主食 + 飲料，POS 用简写如 'Ka Prao Pork+ Drink'
# 这里映射成「菜單對應菜名 + 飲料」形式，让外卖区和堂食菜單外都用中文显示
# ===========================================
POS_ALIASES = {
    # 外卖 Set（Take）
    'Ka Prao Pork+ Drink':         '雙蛋打拋飯(豬) + 飲料',
    'Pad Thai+ Drink':             '泰式羅氏蝦炒金邊粉 + 飲料',
    'Chicken Rice+ Drink':         '泰式海南雞飯 + 飲料',
    'Beef Boat Noodles + Drink':   '牛肉船麵 + 飲料',
    'Tom Yum Goong Noodles+Drink': '海鮮冬蔭功麵 + 飲料',
    'ka prao Chicken + Drink':     '香脆雞肉咖喱醬蓋澆飯 + 飲料',
    'ka prao Pork Belly + Drink':  '香脆五花肉咖喱醬蓋澆飯 + 飲料',
    'Green Curry beef+ Drink':     '青咖喱牛肉 + 飲料',
    'Green Curry chicken+ Drink':  '青咖喱雞肉 + 飲料',
    'Braised Beef + Drink':        '紅燒牛肉蓋澆飯 + 飲料',
    # 堂食 Set（简写版，不带具体主料）
    'Ka Prao+ Drink':              '打拋飯 + 飲料',
    'Boat Noodles+Drink':          '船麵 + 飲料',
    'Chicken Rice+Drink':          '海南雞飯 + 飲料',
    'Pork Noodles+ Drink':         '泰式豬肉湯麵 + 飲料',
}


# 暴露给注册表的 Menu 实例
# 外卖标识：分类名含 'Take' 或 'take'（全角/半角均有，如 Set（Take）/ Drinks (Take)）
# 补差价：分类含 '手寫單'（如「外賣手寫單」，金额负数，单列在外卖末尾）
menu = Menu(
    brand=BRAND_NAME,
    short_name='泰菜',
    items=MENU,
    drop_categories=DROP_CATEGORIES_DINEIN,
    store_overrides=STORE_OVERRIDES,
    delivery_platforms={
        # 外卖标识：分类含 Take/take（全/半角均有）
        # '外賣手寫單' 补差价分类不含 Take，需单独列为 marker 以便 classify_platform 识别
        '外賣': ['Take', 'take', '外賣手寫單'],
    },
    adjust_marker='手寫單',
    pos_aliases=POS_ALIASES,
)
