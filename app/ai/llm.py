import os

from loguru import logger


def init_langchain_llm(*, fast_mode: bool = False, deep_mode: bool = False):
    try:
        from langchain_openai import ChatOpenAI

        api_base = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("LLM_API_KEY", "")
        model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

        if not api_key:
            logger.warning("未配置LLM_API_KEY环境变量，跳过AI分析")
            return None

        if deep_mode:
            timeout = 120
        else:
            timeout = 60

        temperature = 0.2 if fast_mode or deep_mode else 0.2

        return ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=temperature,
            request_timeout=timeout,
        )
    except Exception as exc:
        logger.error(f"初始化LangChain LLM失败: {exc}")
        return None
