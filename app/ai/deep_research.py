import datetime
import re

from ddgs import DDGS
from langchain.tools import tool

from app.ai.context_builder import build_portfolio_text
from app.ai.prompts import build_react_prompt
from app.ai.text_utils import clean_ansi_codes, format_text
from app.ai.web_tools import fetch_webpage, search_news
from app.ai.reporting import save_report


def build_deep_research_tools(data_collector):
    @tool
    def get_market_indices() -> str:
        """获取市场指数数据（上证、深证、纳指、道指等）"""
        try:
            market_data = data_collector.get_market_info(is_return=True)
            result = "主要市场指数：\n"
            for item in market_data[:12]:
                result += f"- {item[0]}: {item[1]} ({item[2]})\n"
            return result
        except Exception as exc:
            return f"获取市场指数失败: {str(exc)}"

    @tool
    def get_news_flash(count: str = "30") -> str:
        """获取7×24快讯（市场新闻）"""
        try:
            import json

            if isinstance(count, str):
                if count.strip().startswith("{"):
                    try:
                        parsed = json.loads(count)
                        count = parsed.get("count", 30)
                    except Exception:
                        count = 30
                else:
                    try:
                        count = int(count)
                    except Exception:
                        count = 30

            count = min(int(count), 50)
            kx_data = data_collector.kx(is_return=True, count=count)
            result = f"7×24快讯（最新{len(kx_data)}条）：\n\n"
            for index, item in enumerate(kx_data[:count], 1):
                evaluate = item.get("evaluate", "")
                evaluate_tag = f"【{evaluate}】" if evaluate else ""
                title = item.get("title", item.get("content", {}).get("items", [{}])[0].get("data", ""))
                publish_time = datetime.datetime.fromtimestamp(int(item["publish_time"])).strftime("%Y-%m-%d %H:%M:%S")
                entity = item.get("entity", [])
                if entity:
                    entity_str = ", ".join([f"{x['code']}-{x['name']}" for x in entity[:3]])
                    result += f"{index}. {publish_time} {evaluate_tag}{title}\n   影响: {entity_str}\n\n"
                else:
                    result += f"{index}. {publish_time} {evaluate_tag}{title}\n\n"
            return result
        except Exception as exc:
            return f"获取7×24快讯失败: {str(exc)}"

    @tool
    def get_sector_performance() -> str:
        """获取行业板块表现（涨跌幅、资金流向等）"""
        try:
            bk_data = data_collector.bk(is_return=True)
            result = "涨幅前10板块：\n"
            for index, item in enumerate(bk_data[:10], 1):
                result += f"{index}. {item[0]}: {item[1]}, 主力净流入{item[2]}, 流入占比{item[3]}\n"
            result += "\n跌幅后10板块：\n"
            for index, item in enumerate(bk_data[-10:], 1):
                result += f"{index}. {item[0]}: {item[1]}, 主力净流入{item[2]}, 流入占比{item[3]}\n"
            return result
        except Exception as exc:
            return f"获取板块数据失败: {str(exc)}"

    @tool
    def get_gold_prices() -> str:
        """获取黄金价格数据（近期金价和实时金价）"""
        try:
            gold_data = data_collector.gold(is_return=True)
            result = "近期金价（最近7天）：\n"
            for item in gold_data[:7]:
                result += f"- {item[0]}: 中国黄金{item[1]}, 周大福{item[2]}, 涨跌({item[3]}, {item[4]})\n"

            realtime_gold_data = data_collector.real_time_gold(is_return=True)
            result += "\n实时金价：\n"
            if realtime_gold_data and len(realtime_gold_data) == 2:
                for row in realtime_gold_data:
                    if row:
                        result += f"- {row[0]}: 最新价{row[1]}, 涨跌幅{row[3]}\n"
            return result
        except Exception as exc:
            return f"获取金价数据失败: {str(exc)}"

    @tool
    def get_realtime_precious_metals() -> str:
        """获取实时贵金属价格数据（黄金9999、现货黄金、现货白银）"""
        try:
            realtime_gold_data = data_collector.real_time_gold(is_return=True)
            if not realtime_gold_data or len(realtime_gold_data) != 3:
                return "实时贵金属数据获取失败或数据不完整"

            result = "实时贵金属价格（详细数据）：\n\n"
            columns = ["名称", "最新价", "涨跌额", "涨跌幅", "开盘价", "最高价", "最低价", "昨收价", "更新时间", "单位"]
            result += "| " + " | ".join(columns) + " |\n"
            result += "|" + "|".join(["---" for _ in columns]) + "|\n"
            for row in realtime_gold_data:
                if row and len(row) == len(columns):
                    result += "| " + " | ".join(str(cell) for cell in row) + " |\n"

            result += "\n当前市场状态：\n"
            for row in realtime_gold_data:
                if row:
                    trend = "上涨" if "-" not in str(row[3]) and str(row[3]) != "0%" else "下跌" if "-" in str(row[3]) else "平稳"
                    result += f"- {row[0]}: {row[3]} ({trend})\n"
            return result
        except Exception as exc:
            return f"获取实时贵金属数据失败: {str(exc)}"

    @tool
    def get_trading_volume() -> str:
        """获取近7日市场成交量数据"""
        try:
            seven_a_data = data_collector.seven_A(is_return=True)
            result = "近7日成交量：\n"
            for item in seven_a_data[:7]:
                result += f"- {item[0]}: 总成交{item[1]}, 上交所{item[2]}, 深交所{item[3]}, 北交所{item[4]}\n"
            return result
        except Exception as exc:
            return f"获取成交量数据失败: {str(exc)}"

    @tool
    def get_shanghai_intraday() -> str:
        """获取上证指数近30分钟分时数据"""
        try:
            a_data = data_collector.A(is_return=True)
            result = "上证指数近30分钟分时（最新10分钟）：\n"
            for item in a_data[-10:]:
                result += f"- {item[0]}: {item[1]}, 涨跌额{item[2]}, 涨跌幅{item[3]}, 成交量{item[4]}, 成交额{item[5]}\n"
            return result
        except Exception as exc:
            return f"获取上证分时数据失败: {str(exc)}"

    @tool
    def get_fund_portfolio() -> str:
        """获取自选基金组合的详细数据"""
        try:
            return build_portfolio_text(data_collector)
        except Exception as exc:
            return f"获取基金组合数据失败: {str(exc)}"

    @tool
    def get_current_time() -> str:
        """获取当前日期和时间"""
        return f"当前时间: {datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}"

    @tool
    def analyze_holdings_news() -> str:
        """分析持仓基金（打星基金）相关的最新新闻"""
        try:
            result_dict = {fund[0]: fund for fund in data_collector.result}
            hold_funds = []
            missing_funds = []

            for fund_code, fund_info in data_collector.CACHE_MAP.items():
                if fund_info.get("is_hold", False):
                    if fund_code in result_dict:
                        fund = result_dict[fund_code]
                        hold_funds.append({"code": fund_code, "name": clean_ansi_codes(fund[1].replace("⭐ ", ""))})
                    else:
                        missing_funds.append(fund_code)

            if missing_funds:
                from loguru import logger

                logger.warning(f"持仓基金中有 {len(missing_funds)} 只在result中未找到: {missing_funds}")

            if not hold_funds:
                return "当前没有打星/持仓基金，无法分析持仓新闻。请先通过 get_fund_portfolio 查看基金组合。"

            result = f"## 持仓基金新闻分析\n\n**持仓基金数量**：{len(hold_funds)}只\n\n"
            keyword_map = {
                "量化": "量化投资",
                "制造": "制造业",
                "先进制造": "先进制造业",
                "智选": "智能制造",
                "创新": "科技创新",
                "成长": "成长股",
                "科技": "科技股",
                "半导体": "半导体芯片",
                "芯片": "半导体芯片",
                "新能源": "新能源",
                "医药": "医药生物",
                "消费": "消费行业",
                "白酒": "白酒行业",
                "光伏": "光伏产业",
                "军工": "军工国防",
                "人工智能": "人工智能",
                "机器人": "机器人",
                "纳斯达克": "美股科技",
                "恒生": "港股",
            }

            for fund in hold_funds:
                fund_name = fund["name"]
                result += f"### 📌 {fund_name}（{fund['code']}）\n\n"
                try:
                    ddgs = DDGS(verify=False)
                except Exception as exc:
                    result += f"**搜索服务暂时不可用**: {str(exc)}\n\n---\n\n"
                    continue

                try:
                    search_name = re.sub(r"(混合|股票|债券|指数|ETF联接|联接)?[A-Z]?$", "", fund_name).strip()
                    news_results = ddgs.text(
                        query=f"{search_name} 基金 最新",
                        region="cn-zh",
                        safesearch="off",
                        timelimit="w",
                        max_results=5,
                    )
                    if news_results:
                        result += "**基金相关新闻**：\n\n"
                        for index, news in enumerate(news_results, 1):
                            title = news.get("title", "无标题")
                            body = news.get("body", "无内容")
                            url = news.get("href", "")
                            result += f"{index}. [{title}]({url})\n   > {body[:100]}...\n\n"
                    else:
                        result += "**基金相关新闻**：暂无相关新闻\n\n"
                except Exception as exc:
                    result += f"**基金相关新闻**：搜索失败 - {str(exc)}\n\n"

                try:
                    industry_keywords = []
                    name_lower = fund_name.lower()
                    for keyword, search_term in keyword_map.items():
                        if keyword in name_lower or keyword in fund_name:
                            industry_keywords.append(search_term)

                    if industry_keywords:
                        industry_query = " ".join(industry_keywords[:2])
                        industry_results = ddgs.text(
                            query=f"{industry_query} 市场动态 投资",
                            region="cn-zh",
                            safesearch="off",
                            timelimit="w",
                            max_results=3,
                        )
                        if industry_results:
                            result += f"**行业动态**（{industry_query}）：\n\n"
                            for index, news in enumerate(industry_results, 1):
                                title = news.get("title", "无标题")
                                body = news.get("body", "无内容")
                                url = news.get("href", "")
                                result += f"{index}. [{title}]({url})\n   > {body[:100]}...\n\n"
                except Exception as exc:
                    result += f"**行业动态**：搜索失败 - {str(exc)}\n\n"

                result += "---\n\n"

            result += "\n💡 **提示**：以上新闻来自网络搜索，请结合市场数据综合判断。\n"
            return result
        except Exception as exc:
            return f"分析持仓基金新闻失败: {str(exc)}"

    return [
        get_market_indices,
        get_news_flash,
        get_sector_performance,
        get_gold_prices,
        get_realtime_precious_metals,
        get_trading_volume,
        get_shanghai_intraday,
        get_fund_portfolio,
        search_news,
        fetch_webpage,
        get_current_time,
        analyze_holdings_news,
    ]


def run_deep_research(analyzer, data_collector, report_dir="reports"):
    from loguru import logger
    from langchain.agents import AgentExecutor, create_react_agent

    logger.info("🚀 启动深度研究模式...")
    llm = analyzer.init_langchain_llm(fast_mode=False, deep_mode=True)
    if llm is None:
        return

    tools = build_deep_research_tools(data_collector)
    current_date = datetime.datetime.now().strftime("%Y年%m月%d日")
    react_prompt = build_react_prompt(current_date)

    agent = create_react_agent(llm=llm, tools=tools, prompt=react_prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=50,
        max_execution_time=900,
        return_intermediate_steps=True,
    )

    logger.info("🔍 Agent开始自主研究和数据收集...")
    result = agent_executor.invoke(
        {
            "input": f"""请生成一份关于当前市场（{current_date}）的深度分析报告。

【报告要求】必须包含以下章节，并使用丰富的Markdown格式（表格、列表、加粗、引用块、Emoji等）：
1. 市场整体趋势分析（包含指数表格、热点列表）
2. 行业板块机会分析（包含领涨/跌板块表格）
3. 基金组合投资建议（包含持仓表格、调仓建议列表）
4. 风险提示与应对（包含风险表格，含信息来源说明）

【引用规范】
- 对于网络搜索获得的信息，务必以Markdown格式 `[标题](URL)` 在文中或段落末尾注明来源地址，以增强可信性。

【深度解读建议】针对7×24快讯中的重要事件：
- 可使用 search_news 搜索相关详细报道（如："政策名称 详情"、"事件名 分析"）
- 可使用 fetch_webpage 获取完整新闻文章内容，深入了解事件背景

务必使用Markdown表格展示所有数据，确保报告字数达到10000字以上！""",
            "current_date": current_date,
        }
    )

    final_report = result.get("output", "")
    if not final_report or final_report == "Agent stopped due to iteration limit or time limit.":
        logger.warning("⚠️ Agent未返回完整输出，尝试从中间步骤提取内容...")
        intermediate_steps = result.get("intermediate_steps", [])
        collected_info = []
        for step in intermediate_steps:
            if len(step) >= 2:
                action, observation = step[0], step[1]
                if observation and isinstance(observation, str) and len(observation) > 50:
                    collected_info.append(f"### {action.tool if hasattr(action, 'tool') else '数据收集'}\n\n{observation}\n")

        if collected_info:
            final_report = "\n\n".join(collected_info)
            final_report += "\n\n---\n\n⚠️ **注意**：由于Agent执行时间限制，本报告由中间数据自动组合生成。建议增加迭代次数或执行时间限制。"
        else:
            final_report = "Agent stopped due to iteration limit or time limit."

    markdown_content = f"""# 🔬 AI深度研究报告

**生成时间**：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**研究模式**：ReAct Agent 自主研究

---

{final_report}

---

💡 **提示**：本报告由AI深度研究生成，Agent自主决定数据收集策略。仅供参考，不构成投资建议。投资有风险，入市需谨慎。
"""

    report_filename = save_report(report_dir, "AI市场深度研究报告", markdown_content)
    if report_filename:
        logger.info(f"✅ 深度研究报告已保存至：{report_filename}")

    logger.critical(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} 🔬 AI深度研究报告")
    logger.info("=" * 80)
    for line in format_text(final_report, max_width=70):
        logger.info(line)
    logger.info("=" * 80)
    logger.info("💡 提示：本报告由AI深度研究生成，仅供参考，不构成投资建议。")
    logger.info("=" * 80)
