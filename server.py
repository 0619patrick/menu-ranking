"""
Flask Web 服务入口

用法:
    python server.py          # 开发模式
    flask run                 # 或通过 flask CLI
"""
import os

from app import create_app

app = create_app(os.environ.get('FLASK_ENV'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8090))
    app.run(host='0.0.0.0', port=port, debug=False)
