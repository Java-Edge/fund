import json
from html.parser import HTMLParser
from typing import Generator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from loguru import logger

import fund
from ai_analyzer import AIAnalyzer, fetch_webpage, search_news
from app.ai.llm import get_prompt_suffix
from app.ai.lmstudio_compat import (
    call_lmstudio_raw,
    extract_html_from_reasoning,
    is_lmstudio_backend,
    should_fallback_to_reasoning,
)

analyzer = AIAnalyzer()


class _HTMLTextExtractor(HTMLParser):
    def __init__(self, joiner: str = " ") -> None:
        super().__init__()
        self.text: list[str] = []
        self.joiner = joiner

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text.append(data.strip())

    def get_text(self) -> str:
        return self.joiner.join(self.text)


def get_real_time_data_context(user_message: str, history: list[dict]) -> str:
    """后端智能获取相关数据，优先从历史对话中提取上下文主题"""
    try:
        my_fund = fund.MaYiFund()
        context_parts: list[str] = []

        data_modules = {
            "kx": {
                "name": "7*24快讯",
                "func": my_fund.kx_html,
                "keywords": ["快讯", "新闻", "news", "消息", "动态"],
            },
            "marker": {
                "name": "全球指数",
                "func": my_fund.marker_html,
                "keywords": ["指数", "上证", "深证", "恒生", "道琼斯", "nasdaq", "纳斯达克", "market", "index"],
            },
            "real_time_gold": {
                "name": "实时贵金属",
                "func": my_fund.real_time_gold_html,
                "keywords": ["黄金", "白银", "贵金属", "gold", "silver", "金价"],
            },
            "gold": {
                "name": "历史金价",
                "func": my_fund.gold_html,
                "keywords": ["历史金价", "金价走势", "金价趋势"],
            },
            "seven_A": {
                "name": "成交量趋势",
                "func": my_fund.seven_A_html,
                "keywords": ["成交量", "交易量", "volume"],
            },
            "A": {
                "name": "上证分时",
                "func": my_fund.A_html,
                "keywords": ["上证分时", "A股分时", "分时图"],
            },
            "fund": {
                "name": "自选基金",
                "func": my_fund.fund_html,
                "keywords": ["基金", "持仓", "自选", "fund", "收益", "净值"],
            },
            "bk": {
                "name": "行业板块",
                "func": my_fund.bk_html,
                "keywords": ["板块", "行业", "sector", "涨跌", "主力", "净流入"],
            },
        }

        history_text = ""
        for msg in history[-5:]:
            content = msg.get("content", "")
            if msg.get("role") == "user":
                history_text += " " + content
            elif msg.get("role") == "assistant":
                parser = _HTMLTextExtractor()
                try:
                    parser.feed(content)
                    extracted = parser.get_text()
                    if len(extracted) > 50 and not any(
                        word in extracted for word in ["AI Analyst is thinking", "⏳", "Processing"]
                    ):
                        history_text += " " + extracted
                except Exception:
                    pass

        combined_text = (history_text + " " + user_message).lower()
        logger.debug(f"Combined text for keyword matching: {combined_text[:200]}...")

        modules_to_fetch = []
        for module_id, module_info in data_modules.items():
            if any(keyword in combined_text for keyword in module_info["keywords"]):
                modules_to_fetch.append((module_id, module_info))

        if not modules_to_fetch:
            modules_to_fetch = [
                ("kx", data_modules["kx"]),
                ("bk", data_modules["bk"]),
                ("fund", data_modules["fund"]),
            ]
            logger.info("未从历史匹配到关键词，获取核心模块")
        else:
            logger.info(f"从历史+当前问题匹配到模块: {[m[0] for m in modules_to_fetch]}")

        for module_id, module_info in modules_to_fetch:
            try:
                html_content = module_info["func"]()
                parser = _HTMLTextExtractor(joiner="\n")
                parser.feed(html_content)
                text_content = parser.get_text()
                context_parts.append(f"\n=== {module_info['name']} ({module_id}) ===\n{text_content}")
                logger.debug(f"✓ 获取 {module_info['name']} 数据成功 ({len(text_content)} chars)")
            except Exception as exc:
                logger.error(f"✗ 获取 {module_info['name']} 数据失败: {exc}")
                context_parts.append(f"\n=== {module_info['name']} ({module_id}) ===\n数据获取失败")

        full_context = "\n".join(context_parts)
        logger.info(f"后端数据获取完成，总长度: {len(full_context)} chars")
        return full_context
    except Exception as exc:
        logger.error(f"Failed to get real-time data: {exc}")
        return "数据获取失败，请稍后重试"


def _clean_history_messages(history: list[dict]) -> list[tuple[str, str]]:
    cleaned: list[tuple[str, str]] = []
    seen_user = False

    for msg in history[-10:]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if not content or not content.strip():
            continue

        if role == "user":
            seen_user = True
            cleaned.append(("user", content))
            continue

        if role == "assistant" and seen_user:
            clean_content = content
            if "<" in content and ">" in content:
                parser = _HTMLTextExtractor()
                try:
                    parser.feed(content)
                    extracted = parser.get_text()
                    if extracted and len(extracted) > 10:
                        clean_content = extracted
                except Exception:
                    pass
            cleaned.append(("assistant", clean_content))

    return cleaned


def _build_lmstudio_prompt(user_message: str, backend_context: str, history: list[dict], prompt_suffix: str) -> str:
    history_lines: list[str] = []
    for role, content in _clean_history_messages(history):
        prefix = "用户" if role == "user" else "助手"
        history_lines.append(f"{prefix}: {content}")

    history_block = "\n".join(history_lines) if history_lines else "无有效历史上下文"

    prompt = f"""你是一位金融分析助手。请直接输出分析内容，不要输出状态信息，不要输出“正在分析/正在搜索”。

输出要求：
- 使用简洁 HTML 片段输出，适合深色主题
- 文本使用 <p style="color:#e0e0e0;margin:1px 0;line-height:1.2">
- 看多/正面可用 <span style="color:#4caf50;font-weight:bold">
- 看空/风险可用 <span style="color:#f44336;font-weight:bold">
- 如果引用列表，使用紧凑 <ul> / <li>
- 直接给结论、依据和风险，不要复述任务

历史上下文：
{history_block}

页面实时数据：
{backend_context}

当前用户问题：
{user_message}
"""
    if prompt_suffix:
        prompt = f"{prompt}\n\n{prompt_suffix}"
    return prompt


def _stream_text_chunks(content: str) -> Generator[str, None, None]:
    chunk_size = 80 if len(content) < 2000 else 150
    for i in range(0, len(content), chunk_size):
        chunk = content[i : i + chunk_size]
        yield f"data: {json.dumps({'type': 'content', 'chunk': chunk}, ensure_ascii=False)}\n\n"


def stream_chat_sse(user_message: str, history: list[dict]) -> Generator[str, None, None]:
    try:
        llm = analyzer.init_langchain_llm(fast_mode=True)
        if not llm:
            yield f"data: {json.dumps({'error': 'LLM not initialized. Please check your API keys in .env file.'}, ensure_ascii=False)}\n\n"
            return

        yield f"data: {json.dumps({'type': 'status', 'message': '正在获取相关数据...'}, ensure_ascii=False)}\n\n"
        backend_context = get_real_time_data_context(user_message, history)
        prompt_suffix = get_prompt_suffix()

        if is_lmstudio_backend():
            lmstudio_prompt = _build_lmstudio_prompt(user_message, backend_context, history, prompt_suffix)
            raw_response = call_lmstudio_raw([{"role": "user", "content": lmstudio_prompt}], max_tokens=1200)
            content = raw_response["content"] or ""

            if not content.strip():
                extracted_html = extract_html_from_reasoning(raw_response["reasoning_content"] or "")
                if extracted_html:
                    logger.warning("LM Studio content empty, using extracted HTML from reasoning_content")
                    content = extracted_html

            if not content.strip() and should_fallback_to_reasoning():
                reasoning = raw_response["reasoning_content"] or ""
                if reasoning.strip():
                    content = (
                        "<p style=\"color:#ff9800;margin:1px 0;line-height:1.2\">"
                        "调试模式：模型未返回正式 content，以下为 reasoning_content 回退输出。</p>"
                        f"<pre style=\"white-space:pre-wrap;color:#e0e0e0;line-height:1.2\">{reasoning}</pre>"
                    )

            if not content.strip():
                logger.error(
                    "LM Studio returned empty content. finish_reason={} usage={}",
                    raw_response["finish_reason"],
                    raw_response["usage"],
                )
                yield f"data: {json.dumps({'type': 'error', 'message': 'LM Studio returned empty content. Please check model thinking/template settings.'}, ensure_ascii=False)}\n\n"
                return

            for chunk in _stream_text_chunks(content):
                yield chunk
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        tools = [search_news, fetch_webpage]
        llm_with_tools = llm.bind_tools(tools)

        messages = [
            SystemMessage(
                content="""Financial analyst assistant. Answer questions directly with analysis.

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

Provide insights, not raw tables. Use context data. If user says "它", check history."""
            )
        ]

        logger.debug(f"Processing {len(history)} history messages")
        for idx, msg in enumerate(history[-10:]):
            role = msg.get("role", "")
            content = msg.get("content", "")

            if not content or not content.strip():
                continue

            if role == "user":
                messages.append(HumanMessage(content=content))
                logger.debug(f"[{idx}] Added user: {content[:50]}...")
            elif role == "assistant":
                clean_content = content
                if "<" in content and ">" in content:
                    parser = _HTMLTextExtractor()
                    try:
                        parser.feed(content)
                        extracted = parser.get_text()
                        if extracted and len(extracted) > 10:
                            clean_content = extracted
                    except Exception:
                        pass
                messages.append(AIMessage(content=clean_content))
                logger.debug(f"[{idx}] Added assistant: {clean_content[:50]}...")

        logger.info(
            f"📊 Loaded {len([m for m in messages if isinstance(m, HumanMessage)])} user messages, "
            f"{len([m for m in messages if isinstance(m, AIMessage)])} assistant messages"
        )

        combined_input = f"CONTEXT FROM PAGE (后端实时数据):\n{backend_context}\n\nUSER QUESTION: {user_message}"
        if prompt_suffix:
            combined_input = f"{combined_input}\n\n{prompt_suffix}"
        messages.append(HumanMessage(content=combined_input))

        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            yield f"data: {json.dumps({'type': 'status', 'message': f'Processing (step {iteration})...'}, ensure_ascii=False)}\n\n"

            if iteration == max_iterations:
                logger.debug(f"\n[Iteration {iteration}] Final iteration - forcing answer without tools")
                messages.append(
                    HumanMessage(
                        content=f"Please provide your final answer now based on all the information gathered. Do not call any more tools.\n\n{prompt_suffix}"
                    )
                )
                response = llm.invoke(messages)
            else:
                response = llm_with_tools.invoke(messages)

            if response.tool_calls and iteration < max_iterations:
                logger.debug(f"\n[Iteration {iteration}] LLM requested {len(response.tool_calls)} tool call(s)")
                tool_names = [tc["name"] for tc in response.tool_calls]
                yield f"data: {json.dumps({'type': 'tool_call', 'tools': tool_names}, ensure_ascii=False)}\n\n"
                messages.append(response)

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
                    messages.append(
                        ToolMessage(
                            content=str(tool_result),
                            tool_call_id=tool_call["id"],
                            name=tool_name,
                        )
                    )
                continue

            logger.debug(f"\n[Iteration {iteration}] LLM generated final answer")
            content = response.content
            content_length = len(content)
            forbidden_phrases = ["正在搜索", "正在分析", "正在获取", "正在查询", "正在调用"]
            is_status_message = any(phrase in content for phrase in forbidden_phrases)

            if is_status_message and iteration < max_iterations:
                logger.warning("⚠️ AI output contains status message, rejecting and requesting proper analysis")
                messages.append(AIMessage(content=content))
                messages.append(
                    HumanMessage(
                        content="""STOP! Your previous response contained status messages like "正在搜索..." which is FORBIDDEN.

You must provide ACTUAL ANALYSIS, not status messages.

Example of what you should output:
<p style='color: #e0e0e0; margin: 1px 0; line-height: 1.2;'>国金量化基金今日表现稳健，主要配置电子、医药等成长板块...</p>

Now provide your REAL analysis without any status messages.

"""
                        + (f"\n\n{prompt_suffix}" if prompt_suffix else "")
                    )
                )
                continue

            if content_length < 500:
                chunk_size = 30
            elif content_length < 2000:
                chunk_size = 80
            else:
                chunk_size = 150

            logger.debug(f"Streaming {content_length} chars with chunk_size={chunk_size}")
            for i in range(0, content_length, chunk_size):
                chunk = content[i : i + chunk_size]
                yield f"data: {json.dumps({'type': 'content', 'chunk': chunk}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        logger.debug(f"\n[Warning] Max iterations ({max_iterations}) reached")
        yield f"data: {json.dumps({'type': 'error', 'message': 'Maximum iterations reached. Please try rephrasing your question.'})}\n\n"
    except Exception as exc:
        logger.error(f"Chat error: {str(exc)}")
        yield f"data: {json.dumps({'type': 'error', 'message': f'Error: {str(exc)}'})}\n\n"
