"""
餐厅菜单注册表

加新餐厅：
1. 在本目录写一个 <name>.py，定义 MENU/DROP_CATEGORIES_DINEIN/STORE_OVERRIDES，
   最后封装成 Menu 实例（参考 tiantian.py）
2. 在下面 MENUS 字典加一行
3. 前端 QS_STORES 给对应店铺设置 restaurant: '<name>'
"""
from .base import Menu
from . import tiantian
from . import tiantian_cn
from . import acheng
from . import acheng_cn
from . import taicai
from . import sijifenfang

# TODO: 拿到菜单 PDF 后实现
# from . import yizheng        # 鮨政


MENUS = {
    'tiantian':     tiantian.menu,
    'tiantian_cn':  tiantian_cn.menu,
    'acheng':       acheng.menu,
    'acheng_cn':    acheng_cn.menu,
    'taicai':       taicai.menu,
    'sijifenfang':  sijifenfang.menu,
    # 'yizheng':      yizheng.menu,
}


def get_menu(restaurant_type: str) -> Menu:
    """根据餐厅类型 key 返回对应的 Menu 实例"""
    if restaurant_type not in MENUS:
        available = ', '.join(MENUS.keys())
        raise ValueError(
            f"餐厅类型「{restaurant_type}」尚未配置，当前可用: {available}。"
            "请先在 app/menus/ 下添加该餐厅的菜单文件。"
        )
    return MENUS[restaurant_type]
