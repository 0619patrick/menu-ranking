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

打开浏览器访问 `http://localhost:5000`

## 部署到 Render

1. 把代码 push 到 GitHub
2. 在 Render 创建 Web Service，连接到这个仓库
3. Render 自动检测 `render.yaml` 配置完成部署

## 项目结构

```
menu-ranking/
├── server.py               # Flask 入口
├── requirements.txt        # Python 依赖
├── render.yaml             # Render 部署配置
├── Procfile                # 备用启动指令
├── README.md
├── docs/
│   └── 菜单配置表说明.md    # 配置表格式 / 加新店流程
└── app/
    ├── menus/
    │   ├── base.py         # Menu 数据结构（归类规则引擎）
    │   ├── loader.py       # CSV 配置加载器
    │   └── data/<餐厅>/     # 每家餐厅的配置表（menu.csv + config.csv）
    │                       #   改菜单/加别名/加新店只需编辑 CSV，不用改代码
    ├── pos_adapters/       # POS 平台适配器（餐飲王 / 美团 → 标准 4 列）
    ├── processors/
    │   └── transformer.py  # 数据处理引擎
    └── templates/
        └── index.html      # 上传页
```

## 技术栈

- 后端: Python + Flask
- Excel 处理: openpyxl + pandas
- 前端: HTML + Tailwind CSS (CDN)
- 部署: Render (免费层)
