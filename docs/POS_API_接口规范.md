# POS 系统数据接口规范

> **版本**: v1.0
> **状态**: 草案（预留设计，待 POS 厂商对接）
> **用途**: 定义 POS 系统需要实现的 API 标准，供本项目自动拉取销量数据

---

## 1. 概述

本项目通过统一的数据接口从各 POS 系统拉取销量数据。POS 厂商只需按本规范实现一个 **HTTP API 端点**，即可接入系统。

所有 POS 系统返回的原始数据经 **AI 清洗层** 自动处理，最终统一为标准 4 列格式：

| 字段 | 类型 | 说明 |
|---|---|---|
| 项目名称 | string | 菜品名称 |
| 分类 | string | POS 里的菜品大类 |
| 数量 | int | 销售份数 |
| 金额 | float | 实收金额（元） |

---

## 2. 接口定义

### 2.1 端点

```
GET /api/v1/sales
```

### 2.2 认证

**方式一：API Key（推荐）**
在请求头中传递：
```
Authorization: Bearer {api_key}
```

**方式二：OAuth 2.0 Client Credentials**
```
Authorization: Bearer {access_token}
```

具体认证方式由双方协商确定。

### 2.3 请求参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `shop_id` | string | 是 | 门店标识（由 POS 系统分配，与本项目门店管理中的 `name` 对应） |
| `start_date` | string | 是 | 开始日期，格式 `YYYY-MM-DD` |
| `end_date` | string | 是 | 结束日期，格式 `YYYY-MM-DD`（含当日） |

请求示例：
```
GET /api/v1/sales?shop_id=HK_TT_001&start_date=2026-07-01&end_date=2026-07-31
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### 2.4 成功响应

**HTTP 状态码**: `200 OK`

**响应体 JSON 格式**：

```json
{
  "shop_id": "HK_TT_001",
  "shop_name": "香港天天太古城",
  "start_date": "2026-07-01",
  "end_date": "2026-07-31",
  "items": [
    {
      "dish_name": "海南雞(中份)",
      "category": "天天海南雞系列",
      "qty": 753,
      "amount": 49294.00
    },
    {
      "dish_name": "海南雞(大份)",
      "category": "天天海南雞系列",
      "qty": 89,
      "amount": 23602.00
    }
  ],
  "summary": {
    "total_qty": 10000,
    "total_amount": 500000.00,
    "item_count": 87
  }
}
```

### 2.5 字段说明

| 字段 | 路径 | 类型 | 说明 |
|---|---|---|---|
| `shop_id` | 顶层 | string | 门店 ID，与请求参数一致 |
| `shop_name` | 顶层 | string | 门店名称（可选） |
| `start_date` | 顶层 | string | 数据起始日期 |
| `end_date` | 顶层 | string | 数据结束日期 |
| `items[].dish_name` | items 数组 | string | **菜品名称** — 需要能在本项目的 menu.csv 的「POS写法」列匹配上 |
| `items[].category` | items 数组 | string | **POS 分类** — POS 里的菜品大类（用于未匹配菜单时的路由） |
| `items[].qty` | items 数组 | integer | **销售数量** |
| `items[].amount` | items 数组 | float | **实收金额**（币种：人民币/港币，由门店地区决定） |
| `summary.total_qty` | summary | integer | 总销售份数（可选，用于校验） |
| `summary.total_amount` | summary | float | 总销售金额（可选，用于校验） |

> **字段名可以不同**：AI 清洗层会自动识别 `dish_name` / `菜品名称` / `项目名称` / `dishName` / `name` 等常见字段名。如果 POS 系统使用不同的字段命名，清洗层会智能映射。

### 2.6 错误响应

| HTTP 状态码 | 说明 |
|---|---|
| `400 Bad Request` | 参数错误（缺少必填参数、日期格式错误等） |
| `401 Unauthorized` | 认证失败（API Key 无效或过期） |
| `403 Forbidden` | 无权限访问该门店数据 |
| `429 Too Many Requests` | 请求频率过高 |
| `500 Internal Server Error` | 服务器内部错误 |

错误响应体：
```json
{
  "error": {
    "code": "INVALID_DATE_FORMAT",
    "message": "日期格式错误，应为 YYYY-MM-DD"
  }
}
```

---

## 3. 数据清洗说明

即使 POS 返回的格式与标准不同，AI 清洗层会做以下处理：

### 3.1 字段名自动识别

支持但不限于以下字段名映射：

| 标准字段 | 可识别的别名 |
|---|---|
| `dish_name` | `菜品名称`、`项目名称`、`dishName`、`name`、`菜名`、`item_name`、`product_name` |
| `category` | `分类`、`菜品大类`、`大类`、`cat`、`category_name`、`department` |
| `qty` | `数量`、`销售数量`、`quantity`、`qty`、`count`、`num` |
| `amount` | `金额`、`实收金额`、`销售额`、`菜品收入`、`total`、`price`、`revenue`、`sales_amount` |

### 3.2 自动处理

- **货币单位**：统一转为「元」（分转元自动除以 100）
- **数据类型**：自动将字符串数字转为 int/float
- **负值处理**：金额为负的行保留（退款/补差价场景），数量为负的行保留
- **空值过滤**：菜品名为空的行自动丢弃

### 3.3 对接流程

```
POS 厂商提供 API 文档/端点
        ↓
在本项目登记 POS 类型（门店管理页面）
        ↓
在 fetcher 层注册对应 POS 的拉取器
        ↓
用户前端选择门店 + 时间段
        ↓
系统自动拉取 → 清洗 → 进入销量排行处理
```

---

## 4. 数据安全

- API Key 仅用于数据拉取，不得超出本项目授权范围
- 传输全程使用 HTTPS 加密
- 拉取的数据仅用于生成销量排行报表，不存储原始数据
- 门店凭证（API Key）存储在项目 SQLite 数据库中，后续可迁移至更安全的凭证管理

---

## 5. 接入清单

| POS 系统 | 状态 | API 端点 | 对接人 |
|---|---|---|---|
| 餐飲王 | ⏳ 待对接 | — | — |
| 美團 | ⏳ 待对接 | — | — |
| 365 | ⏳ 待对接 | — | — |
| Keeta | ⏳ 待对接 | — | — |

---

## 6. 附录

### 6.1 与本项目已有架构的关系

```
POS 系统 HTTP API                本项目
┌──────────┐              ┌──────────────────┐
│ 餐飲王    │ ──JSON──→    │ fetcher.py 拉取器  │
│ API      │              │  → cleaner.py 清洗  │
└──────────┘              │  → transformer.py  │
                          │  → 预览 / Excel    │
┌──────────┐              └──────────────────┘
│ 美團 API │ ──JSON──→          ↑
└──────────┘             现有 adapter 层（Excel 上传）
                         与 fetcher 层（API 拉取）并存，
                         两者输出都是标准 4 列 DataFrame。
```

- **已有 `adapter` 层**：处理手工上传的 Excel 文件 → 标准 4 列
- **新增 `fetcher` 层**：处理 API 自动拉取的 JSON 数据 → 标准 4 列
- 两层的输出汇入同一个 `transformer` 引擎，无需改动核心逻辑

### 6.2 联系方式

- 项目维护：GitHub Issues
- POS 厂商对接：请联系项目管理员
