import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.llm import get_prompt_suffix, init_langchain_llm
from app.ai.lmstudio_compat import call_lmstudio_raw, is_lmstudio_backend
from app.ai.prompts import build_fast_prompt, get_fast_rules


CASES = [
    {
        "name": "bullish_with_risk",
        "kx_summary": "最新快讯（前5条）：\n1. 机器人板块活跃，政策支持智能制造\n2. 半导体板块走强，资金持续流入",
        "market_summary": "主要市场指数：\n- 上证指数: 3350 (+0.8%)\n- 创业板: 2100 (+1.5%)",
        "top_sectors": "涨幅前5板块：\n1. 机器人: +4.2%, 主力净流入12亿\n2. 半导体: +3.8%, 主力净流入9亿",
        "fund_summary": "自选基金总数: 3只\n持有基金数: 1只\n今日涨幅前3的基金：\n1. 【持有】机器人ETF联接: 估值+2.1%",
    },
    {
        "name": "conflicting_signals",
        "kx_summary": "最新快讯（前5条）：\n1. 科技利好政策发布\n2. 海外市场扰动加剧，避险情绪升温",
        "market_summary": "主要市场指数：\n- 上证指数: 3320 (-0.4%)\n- 创业板: 2050 (-1.1%)",
        "top_sectors": "涨幅前5板块：\n1. 黄金: +2.5%, 主力净流入6亿\n2. 公用事业: +1.1%, 主力净流入2亿",
        "fund_summary": "自选基金总数: 4只\n持有基金数: 2只\n今日涨幅前3的基金：\n1. 【持有】科技成长混合: 估值-1.3%",
    },
]


def _to_openai_role(message_type: str) -> str:
    if message_type == "human":
        return "user"
    if message_type == "ai":
        return "assistant"
    return message_type


def main():
    prompt = build_fast_prompt()
    rules = get_fast_rules()
    prompt_suffix = get_prompt_suffix()
    llm = init_langchain_llm(fast_mode=True)
    if not llm:
        raise SystemExit("LLM init failed")
    llm = llm.bind(max_tokens=220)

    for case in CASES:
        prompt_value = prompt.invoke(
            {
                "kx_summary": case["kx_summary"],
                "market_summary": case["market_summary"],
                "top_sectors": case["top_sectors"],
                "fund_summary": case["fund_summary"],
                "analysis_rules": rules,
                "prompt_suffix": prompt_suffix,
            }
        )
        response = llm.invoke(prompt_value)
        print(f"\n===== CASE: {case['name']} =====\n")
        print("[LangChain content]")
        print(response.content or "<empty>")

        if is_lmstudio_backend():
            raw_messages = [
                {
                    "role": _to_openai_role(message.type),
                    "content": message.content,
                }
                for message in prompt_value.to_messages()
            ]
            raw = call_lmstudio_raw(raw_messages, max_tokens=350)
            print("\n[LM Studio normalized content]")
            print(raw["content"] or "<empty>")
            print("\n[LM Studio reasoning_content]")
            print(raw["reasoning_content"] or "<empty>")
            print("\n[LM Studio finish_reason]")
            print(raw["finish_reason"])
            print("\n[LM Studio usage]")
            print(raw["usage"])
        print("\n===== END =====\n")


if __name__ == "__main__":
    main()
