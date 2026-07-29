"""
POS 适配器统一接口

每个 POS 平台实现一个 PosAdapter 子类，
负责把该平台导出的 Excel 文件统一翻译成 4 列标准 DataFrame:

    [项目名称, 分类, 数量, 金额]

后面所有的引擎逻辑（transformer.py）只认这 4 列，不关心源数据是哪个 POS。
"""
from abc import ABC, abstractmethod
import pandas as pd


STANDARD_COLUMNS = ['项目名称', '分类', '数量', '金额']


def _detect_xlsx_engine():
    try:
        import python_calamine  # noqa: F401
        import io
        try:
            pd.read_excel(io.BytesIO(b''), engine='calamine')
        except ValueError as e:
            if 'Unknown engine' in str(e):
                return None
            return 'calamine'
        except Exception:
            return 'calamine'
        return 'calamine'
    except ImportError:
        return None


XLSX_ENGINE = _detect_xlsx_engine()


def read_xlsx(file_obj, **kwargs):
    if XLSX_ENGINE:
        kwargs.setdefault('engine', XLSX_ENGINE)
    return pd.read_excel(file_obj, **kwargs)


class PosAdapter(ABC):
    NAME: str = ''
    KEY: str = ''

    @abstractmethod
    def load(self, file_obj) -> pd.DataFrame:
        raise NotImplementedError

    def _check(self, df: pd.DataFrame) -> pd.DataFrame:
        missing = [c for c in STANDARD_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"{self.NAME} 适配器输出缺少列: {missing}（必须包含 {STANDARD_COLUMNS}）"
            )
        return df[STANDARD_COLUMNS]
