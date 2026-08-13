# 菜品銷量排行

把餐厅 POS 系统导出的销量 Excel 文件，自动转换成按菜单分类排列的菜品销量排行。

## 在线使用

部署到 Render 后访问：`https://menu-ranking.onrender.com`

## 功能

- 上传 POS 销量 Excel 文件（一家或多家店）
- 自动按菜单结构归类（茶位 / 前菜 / 燒烤 / 海南雞系列 / ... / 酒水）
- 自动合并同一菜品的不同 SKU 写法
- 区分堂食和外卖（KT/FP 平台）
- 每类按金额从高到低排序
- 下载生成的 Excel 对照表
- 多店并排对比（按地区/品牌/月份分 sheet）

## 本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/你的用户名/menu-ranking.git
cd menu-ranking

# 2. 创建虚拟环境
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate   # Mac

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动
python server.py
```

打开浏览器访问 `http://localhost:8090`

## 部署到 Render

1. 把代码 push 到 GitHub
2. 在 Render 创建 Web Service，连接到这个仓库
3. Render 自动检测 `render.yaml` 配置完成部署

## 项目结构

```
menu-ranking/
├── server.py                  # 应用入口
├── requirements.txt           # 生产依赖
├── .gitignore
├── Procfile                   # Render 启动指令
├── render.yaml                # Render 部署配置
├── requirements/
│   ├── base.txt               # 生产依赖（同 requirements.txt）
│   └── dev.txt                # 开发依赖（含 pytest）
├── docs/
│   ├── PRD_产品需求文档.md
│   ├── 产品说明文档.md
│   ├── 菜单配置表说明.md
│   └── 对账校验说明.md        # 输出 vs 源数据差额排查指南
├── tests/
│   ├── conftest.py            # pytest fixtures
│   └── test_routes.py         # 路由测试
├── scripts/                   # 工具脚本
└── app/                       # 应用主包
    ├── __init__.py             # Flask 应用工厂 create_app()
    ├── config.py               # 配置管理（开发/生产/测试）
    ├── routes/
    │   └── main.py             # HTTP 路由定义
    ├── core/
    │   └── transformer.py      # 核心业务逻辑（数据处理引擎 + Excel 生成）
    ├── models/
    │   └── menu.py             # Menu 数据类（归类规则引擎）
    ├── services/
    │   ├── menu_service.py     # 菜单注册表（get_menu）
    │   └── loader.py           # CSV 配置加载器
    ├── adapters/
    │   ├── base.py             # POS 适配器基类
    │   ├── canyinwang.py       # 餐飲王适配器
    │   └── meituan.py          # 美團适配器
    ├── data/
    │   └── menus/<餐厅>/       # 每家餐厅的配置表（menu.csv + config.csv）
    ├── templates/
    │   └── index.html          # 上传页面
    └── static/                 # 静态资源（CSS/JS/图片）
```

## 技术栈

- 后端: Python + Flask
- Excel 处理: openpyxl + pandas (calamine 引擎加速)
- 前端: HTML + Tailwind CSS (CDN)
- 部署: Render (免费层)

## 扩展指南

### 加新 POS 平台
1. 在 `app/adapters/` 下新建 `<name>.py`，继承 `PosAdapter` 实现 `load()`
2. 在 `app/adapters/__init__.py` 的 `ADAPTERS` 字典注册

### 加新餐厅
1. 在 `app/data/menus/` 下新建目录，目录名 = 餐厅 key
2. 放入 `menu.csv`（菜单表）和 `config.csv`（规则配置），格式见 `docs/菜单配置表说明.md`
3. 前端店铺配置设置 `restaurant: '<key>'`
