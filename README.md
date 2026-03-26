# 基金市场辅助工具(实时估值正常显示)


fund（数据监控层）
  ├── 多源实时数据抓取
  ├── Web 展示界面
  └── 用户认证 + 持仓管理
  

![Star History Chart](https://api.star-history.com/svg?repos=lanZzV/fund&type=Date)

一个功能强大的金融市场实时监控工具，支持命令行和Web两种模式，可追踪基金估值、市场指数、黄金价格、行业板块和市场快讯。

## 功能特性

### 数据监控
- **基金实时估值**：实时更新基金估值、日涨幅、近30天涨跌趋势
- **市场指数**：上证指数、深证指数、创业板指、纳斯达克、道琼斯等
- **黄金价格**：中国黄金基础金价、周大福金价及历史数据
- **行业板块**：各行业板块涨跌幅、主力资金流入情况
- **7×24快讯**：实时金融市场新闻

### 智能分析
- **连涨/连跌分析**：自动计算基金连续涨跌天数和幅度
- **30天趋势**：展示近30天涨跌分布，一目了然
- **持仓标记**：支持标记持有基金（⭐显示），快速关注重点
- **彩色显示**：终端下红涨绿跌，直观易读

### 双模式运行
- **命令行模式**：快速查看，适合终端用户
- **Web界面模式**：可视化展示，支持表格排序，适合浏览器访问

## 安装

### 依赖安装

```bash
pip install -r requirements.txt
```

### 依赖包说明
- `loguru` - 日志输出
- `requests` - HTTP请求
- `tabulate` - 表格格式化
- `flask` - Web服务器（仅Web模式需要）
- `curl-cffi` - 浏览器模拟请求

## 使用方法

### 命令行模式

#### 查看所有信息
```bash
python fund.py
```
或使用编译好的可执行文件：
```bash
./dist/fund.exe  # Windows
```

显示内容包括：
- 7×24快讯
- 行业板块排行
- 实时金价
- 黄金历史价格
- 近7日A股成交量
- 近30分钟上证指数
- 市场指数汇总
- 自选基金估值

#### 管理自选基金

**添加基金**
```bash
python fund.py -a
# 根据提示输入基金代码，多个代码用英文逗号分隔
# 例如：001618,161725,110011
```

**删除基金**
```bash
python fund.py -d
# 根据提示输入要删除的基金代码
```

**标记持有基金**
```bash
python fund.py -c
# 标记后的基金会在名称前显示 ⭐
```

**取消持有标记**
```bash
python fund.py -b
# 移除基金的持有标记
```

**标记基金板块**（独立功能）
```bash
python fund.py -e
# 为基金添加板块标签，独立于持有标记
# 标记后会在基金名称中显示板块信息
```

**删除板块标记**
```bash
python fund.py -u
# 删除基金的板块标签
```

**查询基金板块**
```bash
python fund.py -s
# 输入板块名称关键词，程序会列出相关的板块
# 然后可以选择具体的板块查看该板块下的基金列表
```

### Web服务器模式

#### 启动服务
```bash
python fund_server.py
```

服务默认运行在：`http://0.0.0.0:8311`

#### 访问地址
浏览器访问：`http://localhost:8311/fund`

#### Web API

**添加基金（通过URL）**
```
http://localhost:8311/fund?add=001618,161725
```

**删除基金（通过URL）**
```
http://localhost:8311/fund?delete=001618
```

**查询单个基金完整信息**
```http
GET /api/fund/{fund_code}
```

响应示例：
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

**仅查询实时估值**
```http
GET /api/fund/estimate/{fund_code}
```

响应示例：
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

**批量查询基金**
```http
POST /api/fund/batch
Content-Type: application/json

{
  "codes": ["001618", "161725", "110011"]
}
```

响应示例：
```json
{
  "success": true,
  "count": 3,
  "data": [...],
  "errors": null
}
```

**健康检查**
```http
GET /health
```

**调用示例**
```bash
curl http://localhost:8311/api/fund/001618

curl http://localhost:8311/api/fund/estimate/001618

curl -X POST http://localhost:8311/api/fund/batch \
  -H "Content-Type: application/json" \
  -d '{"codes":["001618","161725"]}'
```

**错误码**

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 404 | 基金不存在 |
| 500 | 服务器内部错误 |

**注意事项**

1. 基金代码必须为6位数字。
2. 估值数据通常仅在交易时间段内有效。
3. 非交易时间可能返回 `has_estimate: false`。
4. `/api/fund/batch` 最多支持20个基金。

#### Web功能特性
- 所有数据表格化展示
- 支持点击表头排序（升序/降序）
- 现代化UI设计（白底蓝色主题）
- 响应式布局
- 多线程并发获取数据，加载快速

## 打包为可执行文件

使用 PyInstaller 将程序打包为独立的可执行文件：

```bash
pyinstaller fund.spec
```

打包完成后，可执行文件位于 `dist/fund.exe`（Windows）或 `dist/fund`（Linux/Mac）。

## 数据展示说明

### 终端显示（CLI模式）

**颜色说明：**
- 红色：上涨/涨幅为正
- 绿色：下跌/跌幅为负

**基金数据列：**
1. **基金代码** - 6位数字代码
2. **基金名称** - 带⭐表示持有
3. **估值时间** - 最新估值的时间
4. **估值** - 当日实时估值涨跌幅
5. **日涨幅** - 前一交易日涨跌幅
6. **连涨天数** - 正数表示连涨，负数表示连跌
7. **连涨幅** - 连涨/连跌的累计幅度
8. **涨/总 (近30天)** - 近30天上涨天数/总天数
9. **总涨幅** - 近30天累计涨跌幅

### Web界面

**交互功能：**
- 点击表头可排序（再次点击切换升序/降序）
- 可排序的列会显示排序箭头指示器
- 表格使用现代化设计，白底蓝色边框

## 免责声明

本工具仅提供数据展示功能，不构成任何投资建议。投资有风险，入市需谨慎。
