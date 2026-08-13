"""
路由定义

所有 HTTP 路由集中在此模块，通过 register_routes(app) 注册到 Flask 实例。
"""
import io
import json
import logging
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from flask import render_template, request, send_file, jsonify

from app.services.menu_service import get_menu
from app.core.transformer import (
    generate_excel, generate_excel_grouped, generate_excel_by_brand,
    group_shops_for_export,
    compute_stats, build_preview_data, load_source, apply_deletions,
)

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
DEFAULT_RESTAURANT = 'tiantian'
DEFAULT_POS = 'canyinwang'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _read_shop_specs(req):
    try:
        shop_count = int(req.form.get('shop_count', 0))
    except (TypeError, ValueError):
        raise ValueError('shop_count 必须是整数')

    if shop_count < 1:
        raise ValueError('至少需要 1 個店鋪')

    specs = []
    for i in range(shop_count):
        shop_name = req.form.get(f'shop_name_{i}', '').strip()
        file = req.files.get(f'shop_file_{i}')
        restaurant_type = req.form.get(f'restaurant_type_{i}', DEFAULT_RESTAURANT).strip() or DEFAULT_RESTAURANT
        pos_type = req.form.get(f'pos_type_{i}', DEFAULT_POS).strip() or DEFAULT_POS

        if not shop_name:
            raise ValueError(f'第 {i+1} 個店鋪名不能為空')
        if not file or file.filename == '':
            raise ValueError(f'店鋪「{shop_name}」未選擇文件')
        if not allowed_file(file.filename):
            raise ValueError(f'店鋪「{shop_name}」文件格式不支持（只支持 .xlsx / .xls）')

        try:
            get_menu(restaurant_type)
        except ValueError as e:
            raise ValueError(f'店鋪「{shop_name}」: {e}')

        deletions_raw = req.form.get(f'deletions_{i}', '').strip()
        deletions = []
        if deletions_raw:
            try:
                deletions = json.loads(deletions_raw) or []
            except json.JSONDecodeError:
                deletions = []

        unmerges_raw = req.form.get(f'unmerges_{i}', '').strip()
        unmerges = []
        if unmerges_raw:
            try:
                unmerges = json.loads(unmerges_raw) or []
            except json.JSONDecodeError:
                unmerges = []

        month_raw = req.form.get(f'shop_month_{i}', '').strip()
        try:
            month = int(month_raw) if month_raw else datetime.now().month
        except ValueError:
            month = datetime.now().month
        region = req.form.get(f'shop_region_{i}', '其他').strip() or '其他'

        specs.append({
            'shop_name': shop_name,
            'file_bytes': file.read(),
            'restaurant_type': restaurant_type,
            'pos_type': pos_type,
            'deletions': deletions,
            'unmerges': unmerges,
            'month': month,
            'region': region,
        })
    return specs


def register_routes(app):

    # ── 请求日志中间件 ──
    @app.before_request
    def log_request_start():
        request._start_time = time.time()

    @app.after_request
    def log_request_end(response):
        duration = time.time() - getattr(request, '_start_time', time.time())
        extra = ''
        if request.method == 'POST' and request.content_length:
            extra = f' ({request.content_length / 1024:.0f} KB)'
        logger.info(
            '%s %s → %s (%.0fms)%s',
            request.method, request.path, response.status_code,
            duration * 1000, extra,
        )
        return response

    # ── 路由 ──

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/nutrition')
    def nutrition():
        return render_template('nutrition.html')

    @app.route('/generate', methods=['POST'])
    def generate():
        try:
            specs = _read_shop_specs(request)
        except ValueError as e:
            logger.warning('/generate 参数错误: %s', e)
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.exception('/generate 未知错误')
            return jsonify({'error': f'处理出错: {e}'}), 500

        shop_names = [s['shop_name'] for s in specs]
        logger.info('/generate 开始处理 %d 家店: %s', len(specs), shop_names)

        parsed_specs = []
        parsed_pairs = []
        for s in specs:
            try:
                src = load_source(io.BytesIO(s['file_bytes']), s['pos_type'])
                src = apply_deletions(src, s['deletions'])
                src.attrs['unmerges'] = s['unmerges']
                menu = get_menu(s['restaurant_type'])
            except Exception as e:
                logger.warning('店铺「%s」解析失败: %s', s['shop_name'], e)
                return jsonify({'error': f'店铺「{s["shop_name"]}」解析失败: {e}'}), 400
            parsed_specs.append({
                'shop_name': s['shop_name'],
                'src': src,
                'menu': menu,
                'region': s['region'],
                'month': s['month'],
            })
            parsed_pairs.append((s['shop_name'], src, menu))

        try:
            groups = group_shops_for_export(parsed_specs)
            file_io, filename, mimetype = generate_excel_by_brand(groups)
        except Exception as e:
            logger.exception('生成 Excel 失败')
            return jsonify({'error': f'生成 Excel 失败: {e}'}), 400

        stats_summary = []
        for shop_name, src, menu in parsed_pairs:
            try:
                stat = compute_stats(src, menu, shop_name=shop_name)
                stat['shop_name'] = shop_name
                stats_summary.append(stat)
            except Exception as e:
                logger.warning('店铺「%s」统计失败: %s', shop_name, e)
                return jsonify({'error': f'店铺「{shop_name}」统计失败: {e}'}), 400

        response = send_file(
            file_io,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename,
        )
        response.headers['X-Stats'] = json.dumps(stats_summary, ensure_ascii=True)
        response.headers['Access-Control-Expose-Headers'] = 'X-Stats, Content-Disposition'
        logger.info('/generate 完成: %s (%d 家店)', filename, len(specs))
        return response

    @app.route('/preview', methods=['POST'])
    def preview():
        try:
            specs = _read_shop_specs(request)
        except ValueError as e:
            logger.warning('/preview 参数错误: %s', e)
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.exception('/preview 未知错误')
            return jsonify({'error': f'處理出錯: {e}'}), 500

        def process_one(s):
            try:
                src = load_source(io.BytesIO(s['file_bytes']), s['pos_type'])
                menu = get_menu(s['restaurant_type'])
                return ('ok', build_preview_data(s['shop_name'], src, menu))
            except Exception as e:
                logger.warning('店铺「%s」预览失败: %s', s['shop_name'], e)
                return ('err', f'店鋪「{s["shop_name"]}」解析失敗: {e}')

        workers = min(len(specs), 2)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            results = list(ex.map(process_one, specs))

        shops_data = []
        for status, payload in results:
            if status == 'err':
                return jsonify({'error': payload}), 400
            shops_data.append(payload)
        logger.info('/preview 完成: %d 家店', len(shops_data))
        return jsonify({'shops': shops_data})

    @app.route('/admin')
    def admin():
        return render_template('admin.html')

    @app.route('/health')
    def health():
        return {'status': 'ok'}
