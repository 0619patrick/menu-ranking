"""
POS 数据拉取调度层

从各 POS 系统 API 自动拉取销量数据，与 adapter 层（Excel 上传）并列，
两者的输出都是标准 4 列 DataFrame，汇入同一个 transformer 引擎。

加新 POS API 拉取：
1. 在本文件写一个 Fetcher 子类，实现 fetch() 方法
2. 在 FETCHERS 字典注册
"""
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """POS API 拉取器基类"""

    NAME: str = ''       # 显示名，如 '餐飲王 API'
    KEY: str = ''        # 注册 key，与 pos_type 对应

    @abstractmethod
    def fetch(self, shop_id: str, start_date: str, end_date: str) -> dict:
        """
        从 POS API 拉取原始销量数据。

        参数:
            shop_id:    POS 系统的门店 ID（非本项目的门店名）
            start_date: 起始日期 'YYYY-MM-DD'
            end_date:   结束日期 'YYYY-MM-DD'

        返回:
            dict: 原始 JSON 数据（由 cleaner.py 清洗为标准 4 列 DataFrame）
                  格式不限，cleaner 会自动识别字段
        """
        raise NotImplementedError


class _PlaceholderFetcher(BaseFetcher):
    """占位拉取器，待实装"""
    NAME = ''
    KEY = ''

    def fetch(self, shop_id, start_date, end_date):
        raise NotImplementedError(
            f'POS 拉取器「{self.KEY}」尚未实装，'
            f'请参考 docs/POS_API_接口规范.md 对接 API 后在 fetcher.py 注册'
        )


# 注册表：POS 类型 key → Fetcher 类
# API 拉取与 Excel 上传的 adapter 是两套独立体系，
# 后续 POS 厂商提供 API 后在这里注册即可
FETCHERS: dict = {}


def register_fetcher(pos_type: str, fetcher_cls):
    """注册一个 POS 拉取器"""
    FETCHERS[pos_type] = fetcher_cls
    logger.info('POS 拉取器已注册: %s (%s)', fetcher_cls.NAME, pos_type)


def dispatch_fetch(pos_type: str, shop_id: str, start_date: str, end_date: str) -> dict:
    """
    根据 POS 类型路由到对应的拉取器，返回原始 JSON 数据。

    参数:
        pos_type:   POS 类型 key（如 'canyinwang'）
        shop_id:    POS 系统的门店 ID
        start_date: 起始日期 'YYYY-MM-DD'
        end_date:   结束日期 'YYYY-MM-DD'

    返回:
        dict: POS API 返回的原始 JSON 数据

    抛出:
        ValueError: 该 POS 类型未注册拉取器
        NotImplementedError: 拉取器已注册但未实装
    """
    if pos_type not in FETCHERS:
        available = ', '.join(FETCHERS.keys()) if FETCHERS else '（无已注册的拉取器）'
        raise ValueError(
            f'POS 类型「{pos_type}」未注册 API 拉取器，当前可用: {available}。'
            f'参考 docs/POS_API_接口规范.md 对接 API 后在 fetcher.py 注册。'
        )
    fetcher = FETCHERS[pos_type]()
    logger.info('开始拉取 POS 数据: pos=%s, shop=%s, range=%s ~ %s',
                pos_type, shop_id, start_date, end_date)
    try:
        data = fetcher.fetch(shop_id, start_date, end_date)
        logger.info('POS 数据拉取完成: pos=%s, items=%d',
                    pos_type, len(data.get('items', data.get('data', []))))
        return data
    except Exception as e:
        logger.exception('POS 数据拉取失败: pos=%s, shop=%s', pos_type, shop_id)
        raise
