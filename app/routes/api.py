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


# ── 数据拉取（AI 自动获取）──

@api_bp.route('/fetch', methods=['POST'])
def api_fetch_data():
    """
    触发指定门店在指定时间段的销售数据拉取。

    请求体:
    {
        "stores": [
            {"name": "香港天天太古城", "pos_type": "canyinwang", "shop_id": "xxx"},
            ...
        ],
        "start_date": "2026-07-01",
        "end_date": "2026-07-31"
    }

    返回:
    {
        "status": "ok" | "partial" | "error",
        "results": [...],    // 拉取 + 清洗后的标准数据（复用 preview 结构）
        "errors": [...]      // 失败的店铺及原因
    }
    """
    import io
    from app.core.fetcher import dispatch_fetch
    from app.core.cleaner import clean_raw_data
    from app.core.transformer import build_preview_data
    from app.services.menu_service import get_menu

    data = request.get_json(silent=True) or {}
    stores = data.get('stores', [])
    start_date = (data.get('start_date') or '').strip()
    end_date = (data.get('end_date') or '').strip()

    if not stores:
        return jsonify({'error': '请至少选择一家门店'}), 400
    if not start_date or not end_date:
        return jsonify({'error': '请填写开始日期和结束日期'}), 400

    results = []
    errors = []
    for s in stores:
        shop_name = s.get('name', '')
        pos_type = s.get('pos_type', '')
        shop_id = s.get('shop_id', '') or shop_name

        try:
            # 1. 拉取原始数据
            raw = dispatch_fetch(pos_type, shop_id, start_date, end_date)

            # 2. 清洗为标准 4 列
            df = clean_raw_data(raw, pos_type)

            if df.empty:
                errors.append({'shop': shop_name, 'error': '拉取到 0 条有效数据'})
                continue

            # 3. 查找门店对应的菜单
            store_info = list_stores()
            menu_key = 'tiantian'
            for st in store_info:
                if st['name'] == shop_name:
                    menu_key = st['restaurant']
                    break

            try:
                menu = get_menu(menu_key)
            except ValueError:
                errors.append({'shop': shop_name, 'error': f'未找到菜单配置: {menu_key}'})
                continue

            # 4. 生成预览数据
            preview = build_preview_data(shop_name, df, menu)
            results.append(preview)

        except NotImplementedError as e:
            errors.append({'shop': shop_name, 'error': str(e)})
        except ValueError as e:
            errors.append({'shop': shop_name, 'error': str(e)})
        except Exception as e:
            logger.exception('门店「%s」数据拉取失败', shop_name)
            errors.append({'shop': shop_name, 'error': f'拉取失败: {e}'})

    status = 'ok'
    if errors and results:
        status = 'partial'
    elif errors and not results:
        status = 'error'

    return jsonify({
        'status': status,
        'results': results,
        'errors': errors,
    })


# ── AI 辅助匹配 ──

@api_bp.route('/match-suggestions', methods=['POST'])
def api_match_suggestions():
    """对未匹配的 POS 菜名，返回 AI 匹配建议"""
    from app.services.matcher import suggest as match_suggest

    data = request.get_json(silent=True) or {}
    restaurant = (data.get('restaurant') or '').strip()
    unmatched = data.get('unmatched', [])

    if not restaurant:
        return jsonify({'error': '请指定餐厅'}), 400
    if not unmatched or not isinstance(unmatched, list):
        return jsonify({'error': '请提供未匹配菜名列表'}), 400

    try:
        suggestions = match_suggest(unmatched, restaurant)
        return jsonify({'suggestions': suggestions})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.exception('匹配建议生成失败')
        return jsonify({'error': f'匹配失败: {e}'}), 500


@api_bp.route('/confirm-match', methods=['POST'])
def api_confirm_match():
    """确认匹配：将 POS 写法写入 menu.csv"""
    from app.services.matcher import confirm_match as do_confirm

    data = request.get_json(silent=True) or {}
    restaurant = (data.get('restaurant') or '').strip()
    menu_name = (data.get('menu_name') or '').strip()
    pos_writing = (data.get('pos_writing') or '').strip()

    if not restaurant:
        return jsonify({'error': '请指定餐厅'}), 400
    if not menu_name:
        return jsonify({'error': '请指定标准菜名'}), 400
    if not pos_writing:
        return jsonify({'error': '请提供 POS 写法'}), 400

    try:
        result = do_confirm(restaurant, menu_name, pos_writing)
        if result['updated']:
            logger.info('匹配确认: %s → %s (%s)', pos_writing, menu_name, restaurant)
        else:
            logger.info('POS 写法已存在，无需更新: %s', pos_writing)
        return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.exception('确认匹配失败')
        return jsonify({'error': f'保存失败: {e}'}), 500
