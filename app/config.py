"""
应用配置

集中管理所有环境配置，避免配置散落在代码各处。
通过 CONFIG_MAP + load_config() 根据环境名加载对应配置类。
"""
import os


class BaseConfig:
    """基础配置（所有环境共用）"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    TEMPLATES_AUTO_RELOAD = True
    LOG_LEVEL = 'INFO'
    LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')


class DevelopmentConfig(BaseConfig):
    """开发环境"""
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(BaseConfig):
    """生产环境"""
    DEBUG = False
    TEMPLATES_AUTO_RELOAD = False
    LOG_LEVEL = 'WARNING'


class TestingConfig(BaseConfig):
    """测试环境"""
    TESTING = True
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024
    LOG_LEVEL = 'CRITICAL'


CONFIG_MAP = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
    None:          DevelopmentConfig,
}


def load_config(config_name: str = None):
    """根据环境名加载配置类，默认 development"""
    env = config_name or os.environ.get('FLASK_ENV', 'development')
    # 也支持 FLASK_CONFIG 环境变量
    env = os.environ.get('FLASK_CONFIG', env)
    cls = CONFIG_MAP.get(env)
    if cls is None:
        raise ValueError(f'未知配置环境: {env}（可选: {", ".join(CONFIG_MAP)}）')
    return cls
