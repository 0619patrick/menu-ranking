"""
POS 适配器注册表

加新 POS：
1. 在本目录写一个 <name>.py，继承 PosAdapter，实现 load(file_obj) → df
2. 在下面 ADAPTERS 字典加一行
3. 前端 QS_STORES 给对应店铺设置 pos: '<name>'
"""
from .base import PosAdapter
from .canyinwang import CanyinwangAdapter
from .meituan import MeituanAdapter

# TODO: 拿到样本后实现
# from .pos365 import Pos365Adapter        # 365 平台
# from .keeta import KeetaAdapter          # 外卖 keeta


ADAPTERS = {
    'canyinwang': CanyinwangAdapter,
    'meituan':    MeituanAdapter,
    # 'pos365':     Pos365Adapter,
    # 'keeta':      KeetaAdapter,
}


def get_adapter(pos_type: str) -> PosAdapter:
    """根据 POS 类型 key 返回一个适配器实例"""
    if pos_type not in ADAPTERS:
        available = ', '.join(ADAPTERS.keys())
        raise ValueError(
            f"POS 平台「{pos_type}」尚未支持，当前可用: {available}。"
            "请先在 app/pos_adapters/ 下实现该适配器。"
        )
    return ADAPTERS[pos_type]()
