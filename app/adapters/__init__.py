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


ADAPTERS = {
    'canyinwang': CanyinwangAdapter,
    'meituan':    MeituanAdapter,
}


def get_adapter(pos_type: str) -> PosAdapter:
    if pos_type not in ADAPTERS:
        available = ', '.join(ADAPTERS.keys())
        raise ValueError(
            f"POS 平台「{pos_type}」尚未支持，当前可用: {available}。"
            "请先在 app/adapters/ 下实现该适配器。"
        )
    return ADAPTERS[pos_type]()
