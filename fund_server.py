import datetime
import importlib
import re
import threading
import json

import urllib3
from dotenv import load_dotenv
from flask import Flask, request, Response, stream_with_context, jsonify
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from loguru import logger

import fund
from ai_analyzer import AIAnalyzer, search_news, fetch_webpage
from module_html import get_full_page_html

# 加载环境变量
load_dotenv()

# 配置日志：抑制werkzeug的SSL错误噪音
import logging
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)  # 只记录ERROR及以上级别

# 添加自定义过滤器来忽略SSL握手错误
class IgnoreSSLHandshakeFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        # 过滤包含SSL握手特征的错误日志
        if any(pattern in message for pattern in ['\\x16\\x03\\x01', 'Bad request syntax', 'Bad request version', 'Bad HTTP/0.9']):
            return False
        return True

werkzeug_logger.addFilter(IgnoreSSLHandshakeFilter())

urllib3.disable_warnings()
urllib3.util.ssl_.DEFAULT_CIPHERS = ":".join(
    [
        "ECDHE+AESGCM",
        "ECDHE+CHACHA20",
        'ECDHE-RSA-AES128-SHA',
        'ECDHE-RSA-AES256-SHA',
        "RSA+AESGCM",
        'AES128-SHA',
        'AES256-SHA',
    ]
)

app = Flask(__name__)
analyzer = AIAnalyzer()

# 导入并注册蓝图
from auth import auth_bp, init_default_admin
from holdings import holdings_bp, init_holdings_table

app.register_blueprint(auth_bp)
app.register_blueprint(holdings_bp)

# 初始化
init_default_admin()
init_holdings_table()


# 处理恶意/错误的SSL请求
@app.before_request
def detect_ssl_on_http():
    """检测并拒绝SSL/TLS握手请求（发送到HTTP端口的HTTPS请求）"""
    if request.environ.get('werkzeug.request'):
        # 检查原始请求数据是否以TLS握手开始
        try:
            if hasattr(request, 'data') and request.data:
                first_bytes = request.data[:3]
                if first_bytes == b'\x16\x03\x01':  # TLS ClientHello signature
                    logger.warning(f"SSL/TLS request detected on HTTP endpoint from {request.remote_addr}")
                    return jsonify({
                        "error": "SSL/TLS not supported on this endpoint",
                        "message": "This server uses HTTP, not HTTPS. Please use http:// instead of https://"
                    }), 400
        except:
            pass
    return None


# 全局错误处理器
@app.errorhandler(400)
def handle_bad_request(e):
    """统一处理400错误，包括SSL握手等恶意请求"""
    error_description = str(e.description) if hasattr(e, 'description') else str(e)

    # 检测是否为SSL/TLS握手请求
    if any(indicator in error_description for indicator in ['\\x16\\x03\\x01', 'Bad request', 'Bad HTTP']):
        logger.warning(f"Rejected malformed/SSL request from {request.remote_addr}")
        return jsonify({
            "error": "Bad Request",
            "message": "Invalid HTTP request. If you're trying to use HTTPS, please use HTTP instead.",
            "server": "HTTP only (no SSL/TLS)"
        }), 400

    # 其他400错误正常返回
    return jsonify({"error": "Bad Request", "message": error_description}), 400


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    """捕获未处理的异常，防止服务器崩溃"""
    logger.error(f"Unexpected error: {type(e).__name__}: {str(e)}")
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred"
    }), 500


# 添加 CORS 支持
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


def get_real_time_data_context(user_message, history):
    """后端智能获取相关数据，优先从历史对话中提取上下文主题"""
    try:
        my_fund = fund.MaYiFund()
        context_parts = []

        # 定义所有数据模块
        data_modules = {
            'kx': {
                'name': '7*24快讯',
                'func': my_fund.kx_html,
                'keywords': ['快讯', '新闻', 'news', '消息', '动态']
            },
            'marker': {
                'name': '全球指数',
                'func': my_fund.marker_html,
                'keywords': ['指数', '上证', '深证', '恒生', '道琼斯', 'nasdaq', '纳斯达克', 'market', 'index']
            },
            'real_time_gold': {
                'name': '实时贵金属',
                'func': my_fund.real_time_gold_html,
                'keywords': ['黄金', '白银', '贵金属', 'gold', 'silver', '金价']
            },
            'gold': {
                'name': '历史金价',
                'func': my_fund.gold_html,
                'keywords': ['历史金价', '金价走势', '金价趋势']
            },
            'seven_A': {
                'name': '成交量趋势',
                'func': my_fund.seven_A_html,
                'keywords': ['成交量', '交易量', 'volume']
            },
            'A': {
                'name': '上证分时',
                'func': my_fund.A_html,
                'keywords': ['上证分时', 'A股分时', '分时图']
            },
            'fund': {
                'name': '自选基金',
                'func': my_fund.fund_html,
                'keywords': ['基金', '持仓', '自选', 'fund', '收益', '净值']
            },
            'bk': {
                'name': '行业板块',
                'func': my_fund.bk_html,
                'keywords': ['板块', '行业', 'sector', '涨跌', '主力', '净流入']
            },
        }

        # 从历史对话中提取主题关键词（最近5条）
        history_text = ""
        user_questions = []  # 保存用户历史问题

        for msg in history[-5:]:
            content = msg.get('content', '')
            if msg.get('role') == 'user':
                user_questions.append(content)
                history_text += " " + content
            elif msg.get('role') == 'assistant':
                # 从HTML中提取纯文本
                from html.parser import HTMLParser

                class HTMLTextExtractor(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.text = []

                    def handle_data(self, data):
                        if data.strip():
                            self.text.append(data.strip())

                    def get_text(self):
                        return ' '.join(self.text)

                parser = HTMLTextExtractor()
                try:
                    parser.feed(content)
                    extracted = parser.get_text()
                    # 过滤掉状态消息
                    if len(extracted) > 50 and not any(word in extracted for word in ['AI Analyst is thinking', '⏳', 'Processing']):
                        history_text += " " + extracted
                except:
                    pass

        # 合并当前问题和历史文本进行分析
        combined_text = (history_text + " " + user_message).lower()

        logger.debug(f"Combined text for keyword matching: {combined_text[:200]}...")


        # 智能判断需要获取哪些模块
        modules_to_fetch = []
        for module_id, module_info in data_modules.items():
            # 从历史+当前问题中检查关键词
            if any(keyword in combined_text for keyword in module_info['keywords']):
                modules_to_fetch.append((module_id, module_info))

        # 如果没有匹配到任何关键词，获取核心模块
        if not modules_to_fetch:
            modules_to_fetch = [
                ('kx', data_modules['kx']),
                ('bk', data_modules['bk']),
                ('fund', data_modules['fund']),
            ]
            logger.info(f"未从历史匹配到关键词，获取核心模块")
        else:
            logger.info(f"从历史+当前问题匹配到模块: {[m[0] for m in modules_to_fetch]}")

        # 获取匹配的模块数据
        from html.parser import HTMLParser

        class HTMLTextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []

            def handle_data(self, data):
                if data.strip():
                    self.text.append(data.strip())

            def get_text(self):
                return '\n'.join(self.text)

        for module_id, module_info in modules_to_fetch:
            try:
                html_content = module_info['func']()
                parser = HTMLTextExtractor()
                parser.feed(html_content)
                text_content = parser.get_text()
                context_parts.append(f"\n=== {module_info['name']} ({module_id}) ===\n{text_content}")
                logger.debug(f"✓ 获取 {module_info['name']} 数据成功 ({len(text_content)} chars)")
            except Exception as e:
                logger.error(f"✗ 获取 {module_info['name']} 数据失败: {e}")
                context_parts.append(f"\n=== {module_info['name']} ({module_id}) ===\n数据获取失败")

        full_context = '\n'.join(context_parts)
        logger.info(f"后端数据获取完成，总长度: {len(full_context)} chars")

        return full_context

    except Exception as e:
        logger.error(f"Failed to get real-time data: {e}")
        return "数据获取失败，请稍后重试"


@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data = request.json
    user_message = data.get('message')
    history = data.get('history', [])
    # 不再使用前端传递的context，全部由后端获取

    def generate():
        try:
            llm = analyzer.init_langchain_llm(fast_mode=True)
            if not llm:
                yield f"data: {json.dumps({'error': 'LLM not initialized. Please check your API keys in .env file.'}, ensure_ascii=False)}\n\n"
                return

            # 后端智能获取相关数据
            yield f"data: {json.dumps({'type': 'status', 'message': '正在获取相关数据...'}, ensure_ascii=False)}\n\n"
            backend_context = get_real_time_data_context(user_message, history)

            # Bind tools to LLM
            tools = [search_news, fetch_webpage]
            llm_with_tools = llm.bind_tools(tools)

            messages = [
                SystemMessage(content="""Financial analyst assistant. Answer questions directly with analysis.

⛔ FORBIDDEN - Never output these:
"正在搜索" "正在分析" "正在获取" "正在查询"
<div>正在...</div> ← THIS BREAKS EVERYTHING!

✅ CORRECT output example:
<p style='color:#e0e0e0;margin:1px 0;line-height:1.2'>国金量化基金配置科技和医药板块，今日涨<span style='color:#4caf50;font-weight:bold'>+0.5%</span></p>

❌ WRONG output example:
<div>正在搜索基金信息...</div> ← NEVER DO THIS!

Your FIRST word must be actual content, not status!

Format (dark theme, compact):
- Text: <p style="color:#e0e0e0;margin:1px 0;line-height:1.2">
- Good: <span style="color:#4caf50;font-weight:bold">
- Bad: <span style="color:#f44336;font-weight:bold">
- List: <ul style="margin:1px 0;padding-left:14px;line-height:1.2"><li style="margin:0">

Context has: 基金(fund), 板块(bk), 快讯(kx), 指数, 金价

Provide insights, not raw tables. Use context data. If user says "它", check history.""")
            ]

            # 处理历史消息 - 前端现在会发送正确的内容
            logger.debug(f"Processing {len(history)} history messages")

            from html.parser import HTMLParser

            class HTMLTextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []

                def handle_data(self, data):
                    if data.strip():
                        self.text.append(data.strip())

                def get_text(self):
                    return ' '.join(self.text)

            # 直接处理历史消息，提取HTML为纯文本
            for idx, msg in enumerate(history[-10:]):  # 取最近10条
                role = msg.get('role', '')
                content = msg.get('content', '')

                if not content or not content.strip():
                    continue

                if role == 'user':
                    messages.append(HumanMessage(content=content))
                    logger.debug(f"[{idx}] Added user: {content[:50]}...")

                elif role == 'assistant':
                    # 如果是HTML，提取纯文本；否则直接使用
                    clean_content = content
                    if '<' in content and '>' in content:
                        parser = HTMLTextExtractor()
                        try:
                            parser.feed(content)
                            extracted = parser.get_text()
                            if extracted and len(extracted) > 10:
                                clean_content = extracted
                        except:
                            pass  # 保留原始内容

                    messages.append(AIMessage(content=clean_content))
                    logger.debug(f"[{idx}] Added assistant: {clean_content[:50]}...")

            logger.info(f"📊 Loaded {len([m for m in messages if isinstance(m, HumanMessage)])} user messages, "
                       f"{len([m for m in messages if isinstance(m, AIMessage)])} assistant messages")


            # Add current context and user message
            combined_input = f"CONTEXT FROM PAGE (后端实时数据):\n{backend_context}\n\nUSER QUESTION: {user_message}"
            messages.append(HumanMessage(content=combined_input))

            # Multi-turn tool calling loop
            max_iterations = 5
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Send status update
                yield f"data: {json.dumps({'type': 'status', 'message': f'Processing (step {iteration})...'}, ensure_ascii=False)}\n\n"

                # On last iteration, force answer without tools
                if iteration == max_iterations:
                    logger.debug(f"\n[Iteration {iteration}] Final iteration - forcing answer without tools")
                    # Add instruction to answer without more tool calls
                    messages.append(HumanMessage(content="Please provide your final answer now based on all the information gathered. Do not call any more tools."))
                    response = llm.invoke(messages)  # Use llm without tools
                else:
                    response = llm_with_tools.invoke(messages)

                # Check if LLM wants to call tools
                if response.tool_calls and iteration < max_iterations:
                    logger.debug(f"\n[Iteration {iteration}] LLM requested {len(response.tool_calls)} tool call(s)")

                    # Send tool call notification
                    tool_names = [tc["name"] for tc in response.tool_calls]
                    yield f"data: {json.dumps({'type': 'tool_call', 'tools': tool_names}, ensure_ascii=False)}\n\n"

                    messages.append(response)

                    # Execute all tool calls
                    for tool_call in response.tool_calls:
                        tool_name = tool_call["name"]
                        logger.debug(f"  → Calling {tool_name} with args: {tool_call['args']}")

                        if tool_name == "search_news":
                            tool_result = search_news.invoke(tool_call["args"])
                        elif tool_name == "fetch_webpage":
                            tool_result = fetch_webpage.invoke(tool_call["args"])
                        else:
                            tool_result = f"Unknown tool: {tool_name}"

                        logger.debug(f"  → Result preview: {str(tool_result)[:100]}...")

                        messages.append(ToolMessage(
                            content=str(tool_result),
                            tool_call_id=tool_call["id"],
                            name=tool_name
                        ))

                    continue

                else:
                    # No more tool calls, stream the final answer
                    logger.debug(f"\n[Iteration {iteration}] LLM generated final answer")

                    # Validate that the response is not a status message
                    content = response.content
                    content_length = len(content)

                    # Check if AI output contains forbidden status messages
                    forbidden_phrases = ['正在搜索', '正在分析', '正在获取', '正在查询', '正在调用']
                    is_status_message = any(phrase in content for phrase in forbidden_phrases)

                    if is_status_message and iteration < max_iterations:
                        logger.warning(f"⚠️ AI output contains status message, rejecting and requesting proper analysis")
                        # Add a strong correction message
                        messages.append(AIMessage(content=content))
                        messages.append(HumanMessage(content="""STOP! Your previous response contained status messages like "正在搜索..." which is FORBIDDEN.
                        
You must provide ACTUAL ANALYSIS, not status messages. 

Example of what you should output:
<p style='color: #e0e0e0; margin: 1px 0; line-height: 1.2;'>国金量化基金今日表现稳健，主要配置电子、医药等成长板块...</p>

Now provide your REAL analysis without any status messages."""))
                        # Force one more iteration
                        continue

                    # Content is valid, proceed with streaming
                    # Dynamic chunk size: longer content = larger chunks
                    if content_length < 500:
                        chunk_size = 30  # Small content, smaller chunks for effect
                    elif content_length < 2000:
                        chunk_size = 80  # Medium content
                    else:
                        chunk_size = 150  # Large content, bigger chunks for speed

                    logger.debug(f"Streaming {content_length} chars with chunk_size={chunk_size}")

                    for i in range(0, content_length, chunk_size):
                        chunk = content[i:i+chunk_size]
                        yield f"data: {json.dumps({'type': 'content', 'chunk': chunk}, ensure_ascii=False)}\n\n"

                    # Send completion signal
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    return

            # Max iterations reached
            logger.debug(f"\n[Warning] Max iterations ({max_iterations}) reached")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Maximum iterations reached. Please try rephrasing your question.'})}\n\n"

        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Error: {str(e)}'})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    })


@app.route('/', methods=['GET'])
def index():
    """根路径重定向到 /fund"""
    from flask import redirect
    return redirect('/fund')


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({"status": "ok", "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})


@app.route('/fund/<fund_code>', methods=['GET', 'OPTIONS'])
@app.route('/api/fund/<fund_code>', methods=['GET', 'OPTIONS'])
def get_fund_info(fund_code):
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    """查询单个基金完整信息"""
    if not re.match(r'^\d{6}$', fund_code):
        return jsonify({"success": False, "error": "基金代码必须为6位数字"}), 400

    try:
        importlib.reload(fund)
        my_fund = fund.MaYiFund()
        result = my_fund.get_fund_info(fund_code)

        if result is None:
            return jsonify({"success": False, "error": f"基金 {fund_code} 不存在或查询失败"}), 404

        return jsonify({"success": True, **result})
    except Exception as e:
        logger.error(f"查询基金 {fund_code} 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/fund/estimate/<fund_code>', methods=['GET', 'OPTIONS'])
@app.route('/api/fund/estimate/<fund_code>', methods=['GET', 'OPTIONS'])
def get_fund_estimate(fund_code):
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    """仅查询基金实时估值（最快）"""
    if not re.match(r'^\d{6}$', fund_code):
        return jsonify({"success": False, "error": "基金代码必须为6位数字"}), 400

    try:
        importlib.reload(fund)
        my_fund = fund.MaYiFund()
        result = my_fund.get_fund_info(fund_code)

        if result is None:
            return jsonify({"success": False, "error": f"基金 {fund_code} 不存在或查询失败"}), 404

        # 只返回估值相关字段
        return jsonify({
            "success": True,
            "fund_code": result["fund_code"],
            "fund_name": result["fund_name"],
            "estimate_growth": result["estimate"]["growth"],
            "estimate_growth_str": result["estimate"]["growth_str"],
            "estimate_time": result["estimate"]["time"],
            "has_estimate": result["estimate"]["has_data"]
        })
    except Exception as e:
        logger.error(f"查询基金估值 {fund_code} 失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/fund/batch', methods=['POST', 'OPTIONS'])
@app.route('/api/fund/batch', methods=['POST', 'OPTIONS'])
def batch_query_funds():
    """批量查询基金信息"""
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json()
    if not data or 'codes' not in data:
        return jsonify({"success": False, "error": "缺少 codes 参数"}), 400

    codes = data['codes']
    if not isinstance(codes, list):
        return jsonify({"success": False, "error": "codes 必须是数组"}), 400

    if len(codes) > 20:
        return jsonify({"success": False, "error": "批量查询最多支持20个基金"}), 400

    if not all(re.match(r'^\d{6}$', str(code)) for code in codes):
        return jsonify({"success": False, "error": "所有基金代码必须为6位数字"}), 400

    results = []
    errors = []

    try:
        importlib.reload(fund)
        my_fund = fund.MaYiFund()

        for code in codes:
            try:
                result = my_fund.get_fund_info(code)
                if result:
                    results.append(result)
                else:
                    errors.append({"code": code, "error": "查询失败或基金不存在"})
            except Exception as e:
                errors.append({"code": code, "error": str(e)})

        return jsonify({
            "success": True,
            "count": len(results),
            "data": results,
            "errors": errors if errors else None
        })
    except Exception as e:
        logger.error(f"批量查询基金失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/fund/sector', methods=['GET'])
def get_sector_funds():
    """获取指定板块的基金列表"""
    bk_id = request.args.get("bk_id")
    importlib.reload(fund)
    my_fund = fund.MaYiFund()
    return my_fund.select_fund_html(bk_id=bk_id)


@app.route('/fund', methods=['GET'])
def get_fund():
    add = request.args.get("add")
    delete = request.args.get("delete")
    importlib.reload(fund)
    my_fund = fund.MaYiFund()
    if add:
        my_fund.add_code(add)
    if delete:
        my_fund.delete_code(delete)
    results = {}

    def fetch_html(_name, _func):
        try:
            results[_name] = _func()
            logger.debug(f"✓ Successfully fetched {_name}")
        except Exception as e:
            logger.error(f"✗ Failed to fetch {_name}: {e}")
            results[_name] = f"<p style='color:#f44336;'>数据加载失败: {str(e)}</p>"

    threads = []
    tasks = {
        'marker': my_fund.marker_html,
        'gold': my_fund.gold_html,
        "real_time_gold": my_fund.real_time_gold_html,
        'A': my_fund.A_html,
        'fund': my_fund.fund_html,
        "seven_A": my_fund.seven_A_html,
        "bk": my_fund.bk_html,
        "kx": my_fund.kx_html,
        "select_fund": my_fund.select_fund_html,
    }
    for name, func in tasks.items():
        thread = threading.Thread(target=fetch_html, args=(name, func))
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()

    # Ensure all keys exist with fallback content
    for name in tasks.keys():
        if name not in results:
            logger.warning(f"⚠️ Missing result for {name}, using fallback")
            results[name] = f"<p style='color:#ff9800;'>数据未加载</p>"

    tabs_data = [
        {"id": "kx", "title": "7*24快讯", "content": results["kx"]},
        {"id": "marker", "title": "全球指数", "content": results["marker"]},
        {"id": "real_time_gold", "title": "实时贵金属", "content": results["real_time_gold"]},
        {"id": "gold", "title": "历史金价", "content": results["gold"]},
        {"id": "seven_A", "title": "成交量趋势", "content": results["seven_A"]},
        {"id": "A", "title": "上证分时", "content": results["A"]},
        {"id": "fund", "title": "自选基金", "content": results["fund"]},
        {"id": "bk", "title": "行业板块", "content": results["bk"]},
        {"id": "select_fund", "title": "板块基金查询", "content": results["select_fund"]},
    ]
    html = get_full_page_html(tabs_data)
    return html


if __name__ == '__main__':
    app.run(host='localhost', port=8311)
