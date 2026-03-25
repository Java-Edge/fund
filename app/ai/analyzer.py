import datetime

from loguru import logger

from app.ai.context_builder import build_fast_context, build_standard_context
from app.ai.deep_research import run_deep_research
from app.ai.llm import init_langchain_llm
from app.ai.prompts import build_fast_prompt, build_standard_prompts, get_fast_rules, get_standard_rules
from app.ai.reporting import log_analysis_section, save_report
from app.ai.text_utils import clean_ansi_codes, format_text, strip_markdown


class AIAnalyzer:
    def __init__(self):
        self.llm = None

    def init_langchain_llm(self, fast_mode=False, deep_mode=False):
        return init_langchain_llm(fast_mode=fast_mode, deep_mode=deep_mode)

    clean_ansi_codes = staticmethod(clean_ansi_codes)
    strip_markdown = staticmethod(strip_markdown)
    format_text = staticmethod(format_text)

    def analyze(self, data_collector, report_dir="reports"):
        try:
            from langchain_core.output_parsers import StrOutputParser

            logger.debug("正在收集数据进行AI分析...")
            llm = self.init_langchain_llm()
            if llm is None:
                return

            context = build_standard_context(data_collector)
            prompts = build_standard_prompts()
            standard_rules = get_standard_rules()
            output_parser = StrOutputParser()

            logger.info("正在进行市场趋势分析...")
            trend_analysis = (prompts["trend"] | llm | output_parser).invoke({**context, "analysis_rules": standard_rules})

            logger.info("正在进行板块机会分析...")
            sector_analysis = (prompts["sector"] | llm | output_parser).invoke({**context, "analysis_rules": standard_rules})

            logger.info("正在进行基金组合分析...")
            portfolio_analysis = (prompts["portfolio"] | llm | output_parser).invoke({**context, "analysis_rules": standard_rules})

            logger.info("正在进行风险分析...")
            risk_analysis = (prompts["risk"] | llm | output_parser).invoke({**context, "analysis_rules": standard_rules})

            markdown_content = f"""# AI市场深度分析报告

**生成时间**：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 📊 原始数据概览

### 7×24快讯

{context["kx_summary"]}

### 市场指数

{context["market_summary"]}

### 金价走势

{context["gold_summary"]}

{context["realtime_gold_summary"]}

### 市场成交量

{context["seven_a_summary"]}

### 上证指数分时（最近5分钟）

{context["a_summary"]}

### 涨幅领先板块（Top 5）

{context["top_sectors"]}

### 跌幅板块（Bottom 5）

{context["bottom_sectors"]}

### 基金持仓情况

{context["fund_summary"]}

---

## 1️⃣ 市场整体趋势分析

{trend_analysis}

---

## 2️⃣ 行业板块机会分析

{sector_analysis}

---

## 3️⃣ 基金组合投资建议

{portfolio_analysis}

---

## 4️⃣ 风险提示与应对

{risk_analysis}

---

💡 **提示**：以上分析由AI生成，仅供参考，不构成投资建议。投资有风险，入市需谨慎。
"""

            report_filename = save_report(report_dir, "AI市场分析报告", markdown_content)
            if report_filename:
                logger.info(f"✅ AI分析报告已保存至：{report_filename}")

            logger.critical(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} 📊 AI市场深度分析报告")
            logger.info("=" * 80)
            log_analysis_section("1️⃣ 市场整体趋势分析", trend_analysis)
            logger.info("=" * 80)
            log_analysis_section("2️⃣ 行业板块机会分析", sector_analysis)
            logger.info("=" * 80)
            log_analysis_section("3️⃣ 基金组合投资建议", portfolio_analysis)
            logger.info("=" * 80)
            log_analysis_section("4️⃣ 风险提示与应对", risk_analysis)
            logger.info("=" * 80)
            logger.info("💡 提示：以上分析由AI生成，仅供参考，不构成投资建议。投资有风险，入市需谨慎。")
            logger.info("=" * 80)
        except Exception as exc:
            logger.error(f"AI分析过程出错: {exc}")
            import traceback

            logger.error(traceback.format_exc())

    def analyze_fast(self, data_collector, report_dir="reports"):
        try:
            from langchain_core.output_parsers import StrOutputParser

            logger.info("🚀 启动快速分析模式...")
            llm = self.init_langchain_llm(fast_mode=True)
            if llm is None:
                return

            context = build_fast_context(data_collector)
            output_parser = StrOutputParser()
            fast_prompt = build_fast_prompt()
            fast_rules = get_fast_rules()
            analysis_result = (fast_prompt | llm | output_parser).invoke({**context, "analysis_rules": fast_rules})

            markdown_content = f"""# 📊 AI快速市场分析报告

**生成时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

{analysis_result}

---

💡 **提示**：快速分析模式，仅供参考，不构成投资建议。投资有风险，入市需谨慎。
"""
            report_filename = save_report(report_dir, "AI快速分析报告", markdown_content)
            if report_filename:
                logger.info(f"✅ 快速分析报告已保存至：{report_filename}")

            logger.critical(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} 📊 AI快速市场分析报告")
            logger.info("=" * 80)
            for line in self.format_text(analysis_result):
                logger.info(line)
            logger.info("=" * 80)
            logger.info("💡 提示：快速分析模式，仅供参考，不构成投资建议。")
            logger.info("=" * 80)
        except Exception as exc:
            logger.error(f"快速分析过程出错: {exc}")
            import traceback

            logger.error(traceback.format_exc())

    def analyze_deep(self, data_collector, report_dir="reports"):
        try:
            run_deep_research(self, data_collector, report_dir=report_dir)
        except Exception as exc:
            logger.error(f"深度研究模式出错: {exc}")
            import traceback

            logger.error(traceback.format_exc())
