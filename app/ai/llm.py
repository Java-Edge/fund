import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from app.ai.lmstudio_compat import get_lmstudio_chat_options, is_lmstudio_backend

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)


def get_prompt_suffix() -> str:
    explicit = os.getenv("LLM_PROMPT_SUFFIX")
    if explicit is not None:
        return explicit

    api_base = os.getenv("LLM_API_BASE", "")
    model = os.getenv("LLM_MODEL", "")
    is_lmstudio = ":1234" in api_base or "lmstudio" in api_base.lower()
    is_qwen_reasoning = model.startswith("qwen/qwen3") or model.startswith("qwen3")
    if is_lmstudio and is_qwen_reasoning:
        return "/no_think"
    return ""


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

        extra_body = get_lmstudio_chat_options() if is_lmstudio_backend() else {}

        return ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=temperature,
            request_timeout=timeout,
            extra_body=extra_body or None,
        )
    except Exception as exc:
        logger.error(f"初始化LangChain LLM失败: {exc}")
        return None
