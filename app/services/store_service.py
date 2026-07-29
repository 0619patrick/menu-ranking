"""
门店数据服务（SQLite 版）

提供门店 CRUD 操作，数据持久化存储在 SQLite 数据库中。
"""
import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'stores.db')
_DB_PATH = os.path.normpath(_DB_PATH)

# 硬编码种子数据（现有门店，仅在首次建库时导入一次）
_SEED_STORES = [
    # 天天 - 香港
    {'name': '香港天天銅鑼灣', 'label': '銅鑼灣', 'restaurant': 'tiantian', 'pos': 'meituan', 'region': '香港'},
    {'name': '香港天天圓方',   'label': '圓方',   'restaurant': 'tiantian', 'pos': 'meituan', 'region': '香港'},
    {'name': '香港天天沙田',   'label': '沙田',   'restaurant': 'tiantian', 'pos': 'canyinwang', 'region': '香港'},
    {'name': '香港天天太古城', 'label': '太古城', 'restaurant': 'tiantian', 'pos': 'canyinwang', 'region': '香港'},
    # 天天 - 内地
    {'name': '海口天天', 'label': '海口天天', 'restaurant': 'tiantian_cn', 'pos': 'meituan', 'region': '内地'},
    {'name': '南京天天', 'label': '南京天天', 'restaurant': 'tiantian_cn', 'pos': 'meituan', 'region': '内地'},
    {'name': '上海天天', 'label': '上海天天', 'restaurant': 'tiantian_cn', 'pos': 'meituan', 'region': '内地'},
    # 阿城 - 香港
    {'name': '香港阿城淘大',   'label': '淘大',   'restaurant': 'acheng', 'pos': 'canyinwang', 'region': '香港'},
    {'name': '香港阿城太古',   'label': '太古',   'restaurant': 'acheng', 'pos': 'canyinwang', 'region': '香港'},
    {'name': '香港阿城東涌',   'label': '東涌',   'restaurant': 'acheng_donghui', 'pos': 'canyinwang', 'region': '香港'},
    # 阿城 - 内地
    {'name': '深圳阿城', 'label': '深圳阿城', 'restaurant': 'acheng_cn', 'pos': 'meituan', 'region': '内地'},
    # 四季芬芳
    {'name': '香港四季芬芳沙田', 'label': '沙田', 'restaurant': 'sijifenfang', 'pos': 'canyinwang', 'region': '香港'},
    # 泰菜
    {'name': '香港泰菜中環', 'label': '中環', 'restaurant': 'taicai', 'pos': 'canyinwang', 'region': '香港'},
    {'name': '香港泰菜沙田', 'label': '沙田', 'restaurant': 'taicai_shatian', 'pos': 'canyinwang', 'region': '香港'},
]


def _get_conn():
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def init_db():
    """建表（如不存在），并导入种子数据"""
    conn = _get_conn()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS stores (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                label       TEXT NOT NULL DEFAULT '',
                restaurant  TEXT NOT NULL,
                pos         TEXT NOT NULL DEFAULT 'canyinwang',
                region      TEXT NOT NULL DEFAULT '香港',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # 表为空时导入种子数据
        count = conn.execute('SELECT COUNT(*) FROM stores').fetchone()[0]
        if count == 0:
            for s in _SEED_STORES:
                conn.execute(
                    'INSERT INTO stores (name, label, restaurant, pos, region) VALUES (?, ?, ?, ?, ?)',
                    (s['name'], s['label'], s['restaurant'], s['pos'], s['region'])
                )
            logger.info('种子数据已导入: %d 家门店', len(_SEED_STORES))
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row):
    """sqlite3.Row → dict"""
    if row is None:
        return None
    return dict(row)


def list_stores() -> list:
    """返回所有门店"""
    conn = _get_conn()
    try:
        rows = conn.execute('SELECT * FROM stores ORDER BY restaurant, region, id').fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_store(store_id: int) -> dict:
    """按 id 查找门店"""
    conn = _get_conn()
    try:
        row = conn.execute('SELECT * FROM stores WHERE id = ?', (store_id,)).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


def add_store(data: dict) -> dict:
    """新增门店，返回完整记录"""
    conn = _get_conn()
    try:
        cur = conn.execute(
            'INSERT INTO stores (name, label, restaurant, pos, region) VALUES (?, ?, ?, ?, ?)',
            (
                data.get('name', '').strip(),
                data.get('label', '').strip() or data.get('name', '').strip(),
                data.get('restaurant', '').strip(),
                data.get('pos', 'canyinwang').strip(),
                data.get('region', '香港').strip(),
            )
        )
        conn.commit()
        store_id = cur.lastrowid
        logger.info('新增门店: id=%d, name=%s', store_id, data.get('name'))
        return get_store(store_id)
    finally:
        conn.close()


def update_store(store_id: int, data: dict) -> dict:
    """更新门店，返回更新后的记录"""
    conn = _get_conn()
    try:
        fields = []
        values = []
        for key in ('name', 'label', 'restaurant', 'pos', 'region'):
            if key in data and data[key]:
                fields.append(f'{key} = ?')
                values.append(data[key].strip())
        if not fields:
            return get_store(store_id)
        values.append(store_id)
        conn.execute(f'UPDATE stores SET {", ".join(fields)} WHERE id = ?', values)
        conn.commit()
        logger.info('更新门店: id=%d', store_id)
        return get_store(store_id)
    finally:
        conn.close()


def delete_store(store_id: int) -> bool:
    """删除门店"""
    conn = _get_conn()
    try:
        cur = conn.execute('DELETE FROM stores WHERE id = ?', (store_id,))
        conn.commit()
        deleted = cur.rowcount > 0
        if deleted:
            logger.info('删除门店: id=%d', store_id)
        return deleted
    finally:
        conn.close()


# 子品牌 → 所属主品牌 tab 映射
# 例如 tiantian_cn（内地天天）的门店显示在「天天」tab 下
_TAB_GROUP = {
    'tiantian_cn': 'tiantian',
    'acheng_cn': 'acheng',
    'acheng_donghui': 'acheng',
    'taicai_shatian': 'taicai',
}


def list_stores_grouped() -> dict:
    """
    按 (tab 分组, region) 分组，返回首页渲染所需的嵌套结构。
    子品牌门店会归到所属主品牌的 tab 下，但 rest 字段保持原始值（用于菜单选择）。
    输出格式：
    {
      'tiantian': {
        '香港': [...],
        '内地': [
          {'label': '海口天天', 'name': '海口天天', 'pos': 'meituan', 'rest': 'tiantian_cn'},
          ...
        ],
      },
      ...
    }
    """
    stores = list_stores()
    groups = {}
    for s in stores:
        tab_key = _TAB_GROUP.get(s['restaurant'], s['restaurant'])
        region = s['region']
        if tab_key not in groups:
            groups[tab_key] = {}
        if region not in groups[tab_key]:
            groups[tab_key][region] = []
        groups[tab_key][region].append({
            'label': s['label'],
            'name': s['name'],
            'pos': s['pos'],
            'rest': s['restaurant'],
        })
    return groups
