"""
Flask Web 服务入口

路由:
- GET  /         首页, 上传表单
- POST /preview  返回 JSON 预览数据
- POST /generate 接收上传, 生成对照表, 返回下载
- GET  /health   健康检查

每家店上传时需要带 3 个信息:
- shop_name_N        店铺名称
- shop_file_N        POS 导出的 Excel 文件
- restaurant_type_N  餐厅类型 key（决定加载哪份菜单）
- pos_type_N         POS 平台 key（决定用哪个适配器）

后两个如果缺省，会回退到 'tiantian' / 'canyinwang'（保持向后兼容）。
"""
import os
import io
import json
from datetime import datetime
from flask import Flask, render_template, request, send_file, jsonify

from app.processors.transformer import (
    generate_excel, generate_excel_grouped, generate_excel_by_brand,
    group_shops_for_export,
    compute_stats, build_preview_data, load_source, apply_deletions,
)
from app.menus import get_menu

app = Flask(__name__,
            template_folder='app/templates',
            static_folder='app/static')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB 上限（7-10 家店混传留余量）
app.config['TEMPLATES_AUTO_RELOAD'] = True   # 开发期: 改 HTML 后浏览器刷新即可, 无需重启 server

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

# 缺省值（兼容旧前端 / 手动加店时）
DEFAULT_RESTAURANT = 'tiantian'
DEFAULT_POS = 'canyinwang'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _read_shop_specs(req):
    """
    从 form 里读出每家店的 (shop_name, file_bytes, restaurant_type, pos_type)。
    如果任何一步失败，抛出 ValueError(message)。
    """
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

        # 提前验证 restaurant_type / pos_type 是否已配置
        try:
            get_menu(restaurant_type)
        except ValueError as e:
            raise ValueError(f'店鋪「{shop_name}」: {e}')

        # 前端 ▶ 里点 × 删的变体行（仅 /generate 用；/preview 不发也没影响）
        deletions_raw = req.form.get(f'deletions_{i}', '').strip()
        deletions = []
        if deletions_raw:
            try:
                deletions = json.loads(deletions_raw) or []
            except json.JSONDecodeError:
                deletions = []

        # 前端 ▶ 里点 ×「拆回原大类」的变体行（/preview 和 /generate 都用）
        unmerges_raw = req.form.get(f'unmerges_{i}', '').strip()
        unmerges = []
        if unmerges_raw:
            try:
                unmerges = json.loads(unmerges_raw) or []
            except json.JSONDecodeError:
                unmerges = []

        # 月份 / 地区（新版多店并排导出按 (地区, 品牌, 月份) 分 sheet）
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


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    try:
        specs = _read_shop_specs(request)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'处理出错: {e}'}), 500

    # 每家店只解析一次, Excel 和 stats 共享同一份 DataFrame
    parsed_specs = []   # 给 grouped 用，含 region/month
    parsed_pairs = []   # 给 stats 用 (shop_name, src, menu)
    for s in specs:
        try:
            src = load_source(io.BytesIO(s['file_bytes']), s['pos_type'])
            src = apply_deletions(src, s['deletions'])   # 用户手动删的行
            src.attrs['unmerges'] = s['unmerges']        # 拆回原大类的项
            menu = get_menu(s['restaurant_type'])
        except Exception as e:
            return jsonify({'error': f'店铺「{s["shop_name"]}」解析失败: {e}'}), 400
        parsed_specs.append({
            'shop_name': s['shop_name'],
            'src': src,
            'menu': menu,
            'region': s['region'],
            'month':  s['month'],
        })
        parsed_pairs.append((s['shop_name'], src, menu))

    try:
        groups = group_shops_for_export(parsed_specs)
        # 多品牌自动拆成多个 .xlsx 打 zip；单品牌直出 .xlsx
        file_io, filename, mimetype = generate_excel_by_brand(groups)
    except Exception as e:
        return jsonify({'error': f'生成 Excel 失败: {e}'}), 400

    stats_summary = []
    for shop_name, src, menu in parsed_pairs:
        try:
            stat = compute_stats(src, menu, shop_name=shop_name)
            stat['shop_name'] = shop_name
            stats_summary.append(stat)
        except Exception as e:
            return jsonify({'error': f'店铺「{shop_name}」统计失败: {e}'}), 400

    response = send_file(
        file_io,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )
    response.headers['X-Stats'] = json.dumps(stats_summary, ensure_ascii=True)
    response.headers['Access-Control-Expose-Headers'] = 'X-Stats, Content-Disposition'
    return response


@app.route('/preview', methods=['POST'])
def preview():
    try:
        specs = _read_shop_specs(request)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'處理出錯: {e}'}), 500

    # 并发处理多家店：pandas/calamine 读 xlsx 大部分时间在 C/Rust 里释放 GIL，
    # 多线程能实打实并行。max_workers=2 与 gunicorn --threads 2 一致，
    # 避免单请求把所有线程吃光、阻塞其他用户的请求。
    from concurrent.futures import ThreadPoolExecutor

    def process_one(s):
        try:
            src = load_source(io.BytesIO(s['file_bytes']), s['pos_type'])
            # 注：/preview 不在后端套用 unmerges——预览的「拆回原大类」由前端实时派生，
            # 这样能保留 ▶ 里的删除线 + 恢復交互。下载 Excel (/generate) 才在后端真正落位。
            menu = get_menu(s['restaurant_type'])
            return ('ok', build_preview_data(s['shop_name'], src, menu))
        except Exception as e:
            return ('err', f'店鋪「{s["shop_name"]}」解析失敗: {e}')

    workers = min(len(specs), 2)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(process_one, specs))

    shops_data = []
    for status, payload in results:
        if status == 'err':
            return jsonify({'error': payload}), 400
        shops_data.append(payload)
    return jsonify({'shops': shops_data})


@app.route('/health')
def health():
    return {'status': 'ok'}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
