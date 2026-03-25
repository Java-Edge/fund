from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

from app.ai.rules_loader import load_rules


def _join_rules(*filenames: str) -> str:
    sections = [load_rules(filename) for filename in filenames]
    return "\n\n".join(section for section in sections if section)


def get_standard_rules() -> str:
    return _join_rules(
        "core_principles.md",
        "entry_rules.md",
        "reduction_rules.md",
        "position_sizing_rules.md",
        "risk_exceptions.md",
        "output_format_rules.md",
    )


def get_fast_rules() -> str:
    return _join_rules(
        "core_principles.md",
        "entry_rules.md",
        "position_sizing_rules.md",
        "risk_exceptions.md",
        "output_format_rules.md",
    )


def get_deep_rules() -> str:
    return _join_rules(
        "core_principles.md",
        "entry_rules.md",
        "reduction_rules.md",
        "position_sizing_rules.md",
        "risk_exceptions.md",
        "output_format_rules.md",
    )


def build_standard_prompts() -> dict[str, ChatPromptTemplate]:
    return {
        "trend": ChatPromptTemplate.from_messages([
            ("system", "你是一位资深金融分析师，擅长宏观市场分析和趋势判断。请从专业角度深入分析市场走势。"),
            ("user", """请基于以下完整的市场数据，进行深入的市场趋势分析：

【7×24快讯】
{kx_summary}

【市场指数】
{market_summary}

【金价走势】
{gold_summary}

{realtime_gold_summary}

【市场成交量】
{seven_a_summary}

【上证分时数据】
{a_summary}

【领涨板块】
{top_sectors}

请从以下角度进行分析（输出300-400字）：
1. 结合7×24快讯，分析当前市场热点和重要事件
2. 分析主要指数的走势特征和相互关系
3. 判断当前市场所处的阶段（上涨/震荡/调整）
4. 分析市场情绪和资金流向特征（结合成交量和分时数据）
5. 对比国内外市场表现，指出关键影响因素
6. 分析金价走势对市场的影响

【分析规则】
{analysis_rules}

请用专业、客观的语言输出，使用markdown格式（可使用##、###标题，**加粗**，列表，表格等），输出结构化、易读的专业分析报告。"""),
        ]),
        "sector": ChatPromptTemplate.from_messages([
            ("system", "你是一位行业研究专家，精通各个行业板块的投资逻辑和周期规律。"),
            ("user", """请基于以下板块数据和市场环境，深入分析行业投资机会：

【涨幅领先板块】
{top_sectors}

【跌幅板块】
{bottom_sectors}

【市场成交量】
{seven_a_summary}

【上证分时】
{a_summary}

请从以下角度进行分析（输出300-400字）：
1. 分析领涨板块的共同特征和驱动因素
2. 判断这些板块的行情可持续性（结合成交量和资金流向）
3. 结合资金流入情况，评估板块强度
4. 提示哪些板块值得重点关注，给出配置建议
5. 分析弱势板块是否存在反转机会

【分析规则】
{analysis_rules}

请用专业、深入的语言输出，使用markdown格式（可使用##、###标题，**加粗**，列表，表格等），输出结构化、易读的专业分析报告。"""),
        ]),
        "portfolio": ChatPromptTemplate.from_messages([
            ("system", "你是一位专业的基金投资顾问，擅长基金组合配置和风险管理。"),
            ("user", """请基于以下基金持仓和完整市场环境，给出投资建议：

【基金持仓】
{fund_summary}

【市场环境】
{market_summary}

【市场成交量】
{seven_a_summary}

【板块表现】
{top_sectors}

请从以下角度给出建议（输出300-400字）：
1. 评估当前持仓基金的表现和风险特征
2. 分析持仓基金与市场环境的匹配度（结合成交量和板块轮动）
3. 给出具体的调仓建议（增持/减持/持有）
4. 对表现优异的基金，分析背后原因和可持续性
5. 提示仓位配置和风险敞口的优化方向

【分析规则】
{analysis_rules}

请给出具体、可操作的建议，使用markdown格式（可使用##、###标题，**加粗**，列表，表格等），输出结构化、易读的专业分析报告。"""),
        ]),
        "risk": ChatPromptTemplate.from_messages([
            ("system", "你是一位风险管理专家，擅长识别市场风险和制定风控策略。"),
            ("user", """请基于当前完整的市场数据，进行全面的风险分析：

【市场指数】
{market_summary}

【金价走势】
{gold_summary}

【市场成交量】
{seven_a_summary}

【上证分时】
{a_summary}

【板块表现】
{top_sectors}
{bottom_sectors}

【基金持仓】
{fund_summary}

请从以下角度进行风险分析（输出250-350字）：
1. 识别当前市场的主要风险点（结合成交量萎缩/放大、分时走势等）
2. 分析可能引发调整的触发因素
3. 评估持仓基金的风险暴露
4. 给出风险防控建议和应对策略
5. 提示需要关注的风险信号（包括技术面和资金面）

【分析规则】
{analysis_rules}

请客观、谨慎地提示风险，使用markdown格式（可使用##、###标题，**加粗**，列表，表格等），输出结构化、易读的专业分析报告。"""),
        ]),
    }


def build_fast_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", "你是一位资深金融分析师，擅长快速抓住市场要点。"),
        ("user", """请基于以下市场数据，生成简明扼要的市场分析报告：

【7×24快讯】
{kx_summary}

【市场指数】
{market_summary}

【领涨板块】
{top_sectors}

【基金持仓】
{fund_summary}

请生成一份简明的市场分析报告，包含以下4个部分（总共400-500字）：

## 1. 市场趋势（100字）
简要分析当前市场热点、整体走势和市场情绪。

## 2. 板块机会（80字）
指出领涨板块的特征和值得关注的投资机会。

## 3. 基金建议（80字）
评估持仓基金表现，给出简要的配置建议。

## 4. 风险提示（80字）
提示当前主要风险点和应对策略。

【快速分析规则】
{analysis_rules}

输出要求：使用markdown格式，简洁明了，要点突出。"""),
    ])


def build_react_prompt(current_date: str) -> PromptTemplate:
    return PromptTemplate.from_template("""你是一位资深金融研究分析师，擅长深度市场研究和数据可视化。今天是{current_date}。

你的任务是：通过自主调用工具收集数据，生成一份**格式丰富、结构清晰、数据详实**的市场分析报告。

**工具使用说明**：
- 📰 **get_news_flash**：获取7×24快讯列表（包含标题和摘要）
- 🔍 **search_news**：根据关键词搜索快讯的详细内容和相关报道
- 📄 **fetch_webpage**：获取完整新闻文章的详细内容
- 📈 **get_market_indices**：获取市场指数数据（上证、深证、纳指、道指等）
- 📊 **get_sector_performance**：获取行业板块表现（涨跌幅、资金流向等）
- 💰 **get_gold_prices**：获取黄金价格数据（近期金价和实时金价）
- 🥇 **get_realtime_precious_metals**：获取实时贵金属详细数据（黄金9999、现货黄金、现货白银，含开盘价、最高价、最低价等完整信息）
- 📉 **get_trading_volume**：获取近7日市场成交量数据
- 📊 **get_shanghai_intraday**：获取上证指数近30分钟分时数据
- 📋 **get_fund_portfolio**：获取自选基金组合的详细数据
- 🕐 **get_current_time**：获取当前日期和时间
- ⭐ **analyze_holdings_news**：【重要】分析持仓基金（打星基金）相关的最新新闻，自动搜索每只持仓基金的相关报道和行业动态
- 💡 **建议流程**：先用get_news_flash获取快讯列表，再针对重要事件用search_news和fetch_webpage获取详情

**研究流程建议**：
1. 首先调用 get_current_time 确认当前时间
2. 收集基础数据（指数、板块、基金、黄金等）
3. 调用 get_news_flash 获取7×24快讯列表
4. **【可选步骤 - 深度解读】** 针对快讯中的重要事件：
   - 使用 search_news 搜索相关的详细报道（如："政策名称 详情"、"事件名 市场影响"）
   - 使用 fetch_webpage 获取完整文章内容，深入了解事件背景
5. **【推荐步骤 - 持仓分析】** 调用 analyze_holdings_news 获取持仓基金的相关新闻和行业动态，了解持仓基金的最新市场消息和风险提示
6. 综合所有数据，生成**数据详实、分析深入、风险充分提示**的报告

**可用工具**：
{tools}

工具名称: {tool_names}

**报告生成要求**：

你是一位资深金融分析师，需要生成一份**详尽的专业行业研究报告**。

**核心要求**：
1. ⭐ **报告总字数必须达到10000字以上** - 这是最重要的要求
2. 📊 **内容必须详实深入** - 每个分析点都要展开详细论述，不能浅尝辄止
3. 🔍 **数据支撑充分** - 所有判断必须有具体数据和案例支持
4. 📈 **格式丰富清晰** - 使用表格、列表、加粗等Markdown格式增强可读性
5. 🔗 **引用来源** - 对于来自网络搜索的信息，必须以Markdown链接格式 `[标题](URL)` 注明来源

**深度解读建议**：
- 针对7×24快讯中的重要事件，可使用 search_news 搜索相关详细报道
- 对搜索到的重要文章，可使用 fetch_webpage 获取原文完整内容
- 结合快讯信息和详细报道，提供更深入的分析和解读
- **【持仓分析】** 使用 analyze_holdings_news 获取持仓基金的最新新闻，结合基金表现和行业动态给出投资建议

**报告内容建议**：
- 宏观市场环境（全球市场联动、A股技术面、成交量分析、市场情绪）
- 重大事件深度解读（每个重要快讯都要详细分析500-1000字：事件背景+市场影响+投资启示）
- 行业板块机会挖掘（强势板块的驱动因素、持续性判断、龙头标的分析，每个板块300-500字）
- 弱势板块风险提示（下跌原因、底部判断、反弹时机）
- **持仓基金新闻解读**（根据 analyze_holdings_news 返回的新闻，分析每只持仓基金的最新动态、行业趋势和风险提示）
- 基金组合诊断（每只持仓基金的详细分析：业绩、持仓、风险、操作建议，每只500-800字）
- 调仓建议（推荐基金+理由+风险提示，每个推荐300-500字）
- 多维度风险分析（系统性风险、政策风险、市场情绪、行业风险，每类风险300-500字）
- 投资策略（短期/中期/长期策略，具体可执行的操作计划）
- 信息来源说明（列出所有使用的工具和数据来源）

**格式建议**（Markdown）：
- 使用表格展示结构化数据（指数、板块、基金等）
- 使用列表组织要点
- 使用加粗突出关键信息
- 使用引用块突出核心结论
- 使用分隔线分隔章节
- 适当使用Emoji增强可读性

**写作风格**：
- 专业严谨，数据详实
- 逻辑清晰，层次分明
- 语言流畅，易于理解
- 分析深入，见解独到
- **重点：内容要充实，不要惜字如金，要像写一本小册子一样详细**

**重要提示**：
- 每次只调用一个工具，观察结果后再决定下一步
- 可以使用 search_news 和 fetch_webpage 获取7×24快讯的详细内容
- **建议使用 analyze_holdings_news 分析持仓基金的相关新闻和行业动态，为投资决策提供参考**
- 确保报告**字数达到10000字以上**，内容详实、数据充分、建议具体
- 充分提示风险，避免过度乐观或悲观
- 对于网络搜索获得的信息，要以markdown格式给出来源地址 `[标题](URL)`，以增强可信性

【深度研究规则】
{analysis_rules}

使用以下格式：

Question: 要解决的问题
Thought: 你应该思考要做什么
Action: 要采取的行动，必须是 [{tool_names}] 中的一个
Action Input: 行动的输入
Observation: 行动的结果
... (这个 Thought/Action/Action Input/Observation 可以重复N次)
Thought: 我现在知道最终答案了
Final Answer: 最终答案（完整的markdown格式报告，内容详实，字数10000字以上）

开始！

Question: {input}
Thought: {agent_scratchpad}""")
