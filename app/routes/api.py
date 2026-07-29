"""
REST API 路由（门店管理 + 数据查询）

注册为 Flask 蓝图，前缀 /api。
"""
import logging

from flask import Blueprint, jsonify, request

from app.services.store_service import (
    init_db, list_stores, get_store, add_store, update_store, delete_store,
    list_stores_grouped,
)
from app.services.menu_service import list_restaurants
from app.adapters import list_pos_types

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')


# 启动时初始化数据库
init_db()


# ── 门店 ──

@api_bp.route('/stores', methods=['GET'])
def api_list_stores():
    return jsonify(list_stores())


@api_bp.route('/stores/grouped', methods=['GET'])
def api_list_stores_grouped():
    return jsonify(list_stores_grouped())


@api_bp.route('/stores', methods=['POST'])
def api_add_store():
    data = request.get_json(silent=True) or {}
    if not data.get('name', '').strip():
        return jsonify({'error': '门店名不能为空'}), 400
    store = add_store(data)
    logger.info('API 新增门店: %s', store['name'])
    return jsonify(store), 201


@api_bp.route('/stores/<int:store_id>', methods=['GET'])
def api_get_store(store_id):
    store = get_store(store_id)
    if not store:
        return jsonify({'error': '门店不存在'}), 404
    return jsonify(store)


@api_bp.route('/stores/<int:store_id>', methods=['PUT'])
def api_update_store(store_id):
    data = request.get_json(silent=True) or {}
    store = update_store(store_id, data)
    if not store:
        return jsonify({'error': '门店不存在'}), 404
    return jsonify(store)


@api_bp.route('/stores/<int:store_id>', methods=['DELETE'])
def api_delete_store(store_id):
    if delete_store(store_id):
        return jsonify({'status': 'ok'})
    return jsonify({'error': '门店不存在'}), 404


# ── 餐厅 & POS 类型（仅供管理页面下拉框使用）──

# 管理页面下拉框只显示 5 个主品牌
_MAIN_BRANDS = ['tiantian', 'acheng', 'sijifenfang', 'yizheng', 'taicai']

@api_bp.route('/restaurants', methods=['GET'])
def api_list_restaurants():
    all_restaurants = list_restaurants()
    filtered = {k: v for k, v in all_restaurants.items() if k in _MAIN_BRANDS}
    return jsonify(filtered)


@api_bp.route('/pos-types', methods=['GET'])
def api_list_pos_types():
    return jsonify(list_pos_types())
