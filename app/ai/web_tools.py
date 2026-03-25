import json

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from langchain.tools import tool


def _parse_json_arg(value: str, field: str) -> str:
    if isinstance(value, str) and value.strip().startswith("{"):
        try:
            parsed = json.loads(value)
            return parsed.get(field, "")
        except Exception:
            return value
    return value


@tool
def search_news(query: str) -> str:
    """搜索最新金融新闻和市场动态（最近一周内）"""
    try:
        query = _parse_json_arg(query, "query")
        ddgs = DDGS(verify=False)
        results = ddgs.text(
            query=query,
            region="cn-zh",
            safesearch="off",
            timelimit="w",
            max_results=10,
        )

        if not results:
            return f"未找到关于'{query}'的相关新闻"

        output = f"关于'{query}'的搜索结果（最近一周）：\n\n"
        for index, result in enumerate(results, 1):
            title = result.get("title", "无标题")
            body = result.get("body", "无内容")
            url = result.get("href", "")
            output += f"{index}. 标题: {title}\n摘要: {body}\n来源链接: [{title}]({url})\n\n"
        return output
    except Exception as exc:
        return f"搜索失败: {str(exc)}"


@tool
def fetch_webpage(url: str) -> str:
    """获取网页完整内容并提取文本（用于深度阅读新闻文章）"""
    try:
        import urllib3

        url = _parse_json_arg(url, "url")
        urllib3.disable_warnings()

        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=10,
            verify=False,
        )
        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, "lxml")
        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)

        if len(text) > 3000:
            text = text[:3000] + "...(内容过长已截断)"
        return f"网页内容：\n{text}"
    except Exception as exc:
        return f"获取网页失败: {str(exc)}"
