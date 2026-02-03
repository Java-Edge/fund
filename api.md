# 基金查询API

封装蚂蚁财富API，提供基金实时估值查询服务。

## 功能特性

- 基金实时估值查询（核心功能）
- 日涨幅查询
- 30天趋势统计
- 批量查询支持
- RESTful API设计
- CORS跨域支持

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动服务

```bash
python app.py
```

服务将运行在: `http://0.0.0.0:8311`

## API接口

### 1. 查询单个基金完整信息

```http
GET /api/fund/{fund_code}
```

**参数:**
- `fund_code`: 基金代码，如 `001618`

**响应示例:**
```json
{
  "success": true,
  "fund_code": "001618",
  "fund_name": "天弘沪深300ETF联接A",
  "query_time": "2026-02-02 14:30:25",
  "estimate": {
    "growth": 1.25,
    "growth_str": "+1.25%",
    "time": "2026-02-02 14:29:00",
    "nav": "1.5234",
    "has_data": true
  },
  "day_growth": {
    "value": -0.50,
    "value_str": "-0.50%",
    "net_value_date": "2026-02-01"
  },
  "trend_30d": {
    "up_days": 18,
    "down_days": 12,
    "total_days": 30,
    "total_growth": 5.32,
    "total_growth_str": "+5.32%",
    "consecutive_up_days": 3,
    "consecutive_down_days": 0,
    "latest_trend": "up",
    "recent_10d": [
      {"date": "2026-02-01", "growth": -0.50},
      {"date": "2026-01-31", "growth": 1.20}
    ]
  }
}
```

### 2. 仅查询实时估值（最快）

```http
GET /api/fund/estimate/{fund_code}
```

**响应示例:**
```json
{
  "success": true,
  "fund_code": "001618",
  "fund_name": "天弘沪深300ETF联接A",
  "estimate_growth": 1.25,
  "estimate_growth_str": "+1.25%",
  "estimate_time": "2026-02-02 14:29:00",
  "has_estimate": true
}
```

### 3. 批量查询

```http
POST /api/fund/batch
Content-Type: application/json

{
  "codes": ["001618", "161725", "110011"]
}
```

**响应示例:**
```json
{
  "success": true,
  "count": 3,
  "data": [...],
  "errors": null
}
```

### 4. 健康检查

```http
GET /health
```

## 测试示例

```bash
# 查询单个基金
curl http://localhost:8311/api/fund/001618

# 仅查询估值
curl http://localhost:8311/api/fund/estimate/001618

# 批量查询
curl -X POST http://localhost:8311/api/fund/batch \
  -H "Content-Type: application/json" \
  -d '{"codes":["001618","161725"]}'
```

## 错误码

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 404 | 基金不存在 |
| 500 | 服务器内部错误 |

## 注意事项

1. 基金代码为6位数字
2. 估值数据仅在交易时间段内有效（工作日 9:30-15:00）
3. 非交易时间可能返回 `has_estimate: false`
4. 批量查询最多支持20个基金

## 技术栈

- Python 3.11
- Flask
- Requests
- Loguru
