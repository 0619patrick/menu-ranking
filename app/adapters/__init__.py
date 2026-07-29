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


class _PlaceholderAdapter(PosAdapter):
    """占位适配器，待实装"""
    NAME = ''
    KEY = ''
    def load(self, file_obj):
        raise NotImplementedError(f'POS 适配器「{self.KEY}」尚未实装')


ADAPTERS = {
    'canyinwang': CanyinwangAdapter,
    'meituan':    MeituanAdapter,
    'pos365':     type('Pos365Adapter', (_PlaceholderAdapter,), {'NAME': '365', 'KEY': 'pos365'}),
    'keeta':      type('KeetaAdapter',  (_PlaceholderAdapter,), {'NAME': 'Keeta', 'KEY': 'keeta'}),
}


def list_pos_types() -> dict:
    """返回 {key: name} 字典（所有可用的 POS 平台）"""
    return {k: cls.NAME for k, cls in ADAPTERS.items()}


def get_adapter(pos_type: str) -> PosAdapter:
    if pos_type not in ADAPTERS:
        available = ', '.join(ADAPTERS.keys())
        raise ValueError(
            f"POS 平台「{pos_type}」尚未支持，当前可用: {available}。"
            "请先在 app/adapters/ 下实现该适配器。"
        )
    return ADAPTERS[pos_type]()
