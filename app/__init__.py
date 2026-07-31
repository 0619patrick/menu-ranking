"""
Flask 应用工厂

使用 create_app() 初始化应用，避免全局状态，便于测试和多实例部署。
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask

# ── ANSI 颜色（行业标准日志配色）──
_LOG_COLORS = {
    'DEBUG':     '\033[36m',      # 青色
    'INFO':      '\033[32m',      # 绿色
    'WARNING':   '\033[33m',      # 黄色
    'ERROR':     '\033[31m',      # 红色
    'CRITICAL':  '\033[35m',      # 品红
}
_RESET = '\033[0m'


class _ColoredFormatter(logging.Formatter):
    """控制台日志：级别和模块名带颜色，保留完整格式（异常 traceback 等）"""

    def format(self, record):
        color = _LOG_COLORS.get(record.levelname, '')
        if not color:
            return super().format(record)
        # 临时替换 record 属性为彩色版本，然后让父类处理完整格式
        orig_level = record.levelname
        orig_module = record.module
        record.levelname = f'{color}{orig_level}{_RESET}'
        record.module = f'{color}{orig_module}{_RESET}'
        try:
            return super().format(record)
        finally:
            record.levelname = orig_level
            record.module = orig_module


def setup_logging(app):
    """配置日志：同时输出到控制台和文件（按大小轮转，保留 7 天）"""
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'), logging.INFO)
    log_dir = app.config.get('LOG_DIR', os.path.join(app.root_path, '..', 'logs'))
    log_dir = os.path.normpath(log_dir)
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, 'app.log')

    # 文件 handler：10MB 轮转，保留 7 份
    file_handler = RotatingFileHandler(
        log_path, maxBytes=10 * 1024 * 1024, backupCount=7, encoding='utf-8'
    )
    file_handler.setLevel(log_level)

    # 控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # 格式：控制台用彩色，文件用纯文本
    file_fmt = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_fmt = _ColoredFormatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_fmt)
    console_handler.setFormatter(console_fmt)

    root = logging.getLogger()
    root.setLevel(log_level)
    # 避免重复添加 handler（reload 时）
    if not root.handlers:
        root.addHandler(file_handler)
        root.addHandler(console_handler)

    app.logger.info('日志初始化完成 (level=%s, file=%s)', log_level, log_path)


def create_app(config_name: str = None) -> Flask:
    """创建并配置 Flask 应用实例"""
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    # Existing monthly SOP workbooks contain embedded dish photos and can exceed 200MB.
    app.config['MAX_CONTENT_LENGTH'] = 350 * 1024 * 1024
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # 加载配置
    from app.config import load_config
    app.config.from_object(load_config(config_name))

    # 初始化日志
    setup_logging(app)

    # 注册路由
    from app.routes.main import register_routes
    register_routes(app)

    # 注册 API 蓝图
    from app.routes.api import api_bp
    app.register_blueprint(api_bp)

    app.logger.info('应用启动完成 (config=%s)', config_name or 'development')
    return app
