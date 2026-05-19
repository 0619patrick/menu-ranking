"""
Flask Web 服务入口
功能:
- GET  /          首页, 上传表单
- POST /generate  接收上传, 生成对照表, 返回下载
"""
import os
import io
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime

from app.processors.transformer import generate_excel, get_stats, build_preview_data, load_source

app = Flask(__name__,
            template_folder='app/templates',
            static_folder='app/static')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 上限

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    """
    接收上传的店铺文件, 生成对照表
    表单字段:
      shop_count: 店铺数量(整数)
      shop_name_0, shop_file_0, shop_name_1, shop_file_1, ...
    """
    try:
        shop_count = int(request.form.get('shop_count', 0))
        if shop_count < 1:
            return jsonify({'error': '至少需要 1 个店铺'}), 400

        shop_files = []
        stats_summary = []

        for i in range(shop_count):
            shop_name = request.form.get(f'shop_name_{i}', '').strip()
            file = request.files.get(f'shop_file_{i}')

            if not shop_name:
                return jsonify({'error': f'第 {i+1} 个店铺名不能为空'}), 400
            if not file or file.filename == '':
                return jsonify({'error': f'店铺「{shop_name}」未选择文件'}), 400
            if not allowed_file(file.filename):
                return jsonify({'error': f'店铺「{shop_name}」的文件格式不支持(只支持 .xlsx / .xls)'}), 400

            # 读到内存 (因为 generate_excel 和 get_stats 都要用一次)
            file_bytes = file.read()
            shop_files.append((shop_name, io.BytesIO(file_bytes)))

            # 统计
            try:
                s = get_stats(io.BytesIO(file_bytes))
                s['shop_name'] = shop_name
                stats_summary.append(s)
            except Exception as e:
                return jsonify({
                    'error': f'店铺「{shop_name}」的文件解析失败: {str(e)}。'
                             '请确认文件包含「项目名称」「分类」「数量」「金额」等列。'
                }), 400

        # 生成 Excel
        excel_io = generate_excel(shop_files)

        # 拼下载文件名
        today = datetime.now().strftime('%Y%m%d')
        filename = f'銷量對照表_{today}.xlsx'

        response = send_file(
            excel_io,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename,
        )

        # 把统计信息塞进响应头(前端可读)
        import json
        response.headers['X-Stats'] = json.dumps(stats_summary, ensure_ascii=True)
        response.headers['Access-Control-Expose-Headers'] = 'X-Stats, Content-Disposition'

        return response

    except Exception as e:
        return jsonify({'error': f'处理出错: {str(e)}'}), 500


@app.route('/preview', methods=['POST'])
def preview():
    try:
        shop_count = int(request.form.get('shop_count', 0))
        if shop_count < 1:
            return jsonify({'error': '至少需要 1 個店鋪'}), 400

        shops_data = []
        for i in range(shop_count):
            shop_name = request.form.get(f'shop_name_{i}', '').strip()
            file = request.files.get(f'shop_file_{i}')

            if not shop_name:
                return jsonify({'error': f'第 {i+1} 個店鋪名不能為空'}), 400
            if not file or file.filename == '':
                return jsonify({'error': f'店鋪「{shop_name}」未選擇文件'}), 400
            if not allowed_file(file.filename):
                return jsonify({'error': f'店鋪「{shop_name}」文件格式不支持（只支持 .xlsx / .xls）'}), 400

            file_bytes = file.read()
            try:
                src = load_source(io.BytesIO(file_bytes))
                data = build_preview_data(shop_name, src)
                shops_data.append(data)
            except Exception as e:
                return jsonify({
                    'error': f'店鋪「{shop_name}」解析失敗: {str(e)}。'
                             '請確認文件包含「項目名稱」「分類」「數量」「金額」等列。'
                }), 400

        return jsonify({'shops': shops_data})

    except Exception as e:
        return jsonify({'error': f'處理出錯: {str(e)}'}), 500


@app.route('/health')
def health():
    return {'status': 'ok'}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
