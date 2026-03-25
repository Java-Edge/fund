"""
兼容入口。

实际实现已拆分到 app.ai 下，保留这里仅用于兼容旧引用路径。
"""

from app.ai import AIAnalyzer, fetch_webpage, search_news

__all__ = ["AIAnalyzer", "search_news", "fetch_webpage"]
