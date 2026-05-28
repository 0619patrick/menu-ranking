"""
POS 适配器统一接口

每个 POS 平台（餐飲王 / 365 / 美团 / Keeta）实现一个 PosAdapter 子类，
负责把该平台导出的 Excel 文件统一翻译成 4 列标准 DataFrame:

    [项目名称, 分类, 数量, 金额]

后面所有的引擎逻辑（transformer.py）只认这 4 列，不关心源数据是哪个 POS。
"""
from abc import ABC, abstractmethod
import pandas as pd


STANDARD_COLUMNS = ['项目名称', '分类', '数量', '金额']


# ===== 探测最快的 xlsx 引擎（一次性，所有 adapter 共享）=====
# pandas 2.2+ 配 python-calamine 可用 'calamine' 引擎（Rust 实现，比 openpyxl 快 5-10 倍）
# 不可用就 fallback 到 openpyxl（pandas 默认）
def _detect_xlsx_engine():
    try:
        import python_calamine  # noqa: F401
        # 试读一个空 BytesIO，看 pandas 是否认 'calamine' 这个 engine 名
        import io
        try:
            pd.read_excel(io.BytesIO(b''), engine='calamine')
        except ValueError as e:
            if 'Unknown engine' in str(e):
                return None
            return 'calamine'  # 其他错（如解析失败）= 引擎识别 OK
        except Exception:
            return 'calamine'
        return 'calamine'
    except ImportError:
        return None


XLSX_ENGINE = _detect_xlsx_engine()


def read_xlsx(file_obj, **kwargs):
    """带 calamine 加速的 pd.read_excel 包装。pandas 不认 calamine 时自动 fallback。"""
    if XLSX_ENGINE:
        kwargs.setdefault('engine', XLSX_ENGINE)
    return pd.read_excel(file_obj, **kwargs)


class PosAdapter(ABC):
    """所有 POS 适配器的基类"""

    NAME: str = ''           # 显示给用户看的中文名，例如 '餐飲王'
    KEY: str = ''            # 注册表 key，例如 'canyinwang'

    @abstractmethod
    def load(self, file_obj) -> pd.DataFrame:
        """
        读取 POS 导出文件，返回标准化的 DataFrame。

        返回的 DataFrame 必须包含 STANDARD_COLUMNS 全部 4 列：
        - 项目名称: str
        - 分类: str
        - 数量: int
        - 金额: float
        """
        raise NotImplementedError

    def _check(self, df: pd.DataFrame) -> pd.DataFrame:
        """子类 load() 完成后调用，确保返回了标准列"""
        missing = [c for c in STANDARD_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"{self.NAME} 适配器输出缺少列: {missing}（必须包含 {STANDARD_COLUMNS}）"
            )
        return df[STANDARD_COLUMNS]
