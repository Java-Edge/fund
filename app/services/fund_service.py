import importlib
import threading
from typing import Any

from loguru import logger

import fund
from module_html import get_full_page_html


def get_fund_info_service(fund_code: str) -> dict[str, Any] | None:
    importlib.reload(fund)
    my_fund = fund.MaYiFund()
    return my_fund.get_fund_info(fund_code)


def get_fund_estimate_service(fund_code: str) -> dict[str, Any] | None:
    result = get_fund_info_service(fund_code)
    if result is None:
        return None
    return {
        "fund_code": result["fund_code"],
        "fund_name": result["fund_name"],
        "estimate_growth": result["estimate"]["growth"],
        "estimate_growth_str": result["estimate"]["growth_str"],
        "estimate_time": result["estimate"]["time"],
        "has_estimate": result["estimate"]["has_data"],
    }


def batch_query_funds_service(codes: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    importlib.reload(fund)
    my_fund = fund.MaYiFund()

    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for code in codes:
        try:
            result = my_fund.get_fund_info(code)
            if result:
                results.append(result)
            else:
                errors.append({"code": code, "error": "查询失败或基金不存在"})
        except Exception as exc:
            errors.append({"code": code, "error": str(exc)})
    return results, errors


def get_fund_realtime_service(fund_code: str) -> dict[str, Any] | None:
    my_fund = fund.MaYiFund()
    return my_fund.get_fund_realtime_estimate(fund_code)


def get_fund_realtime_batch_service(codes: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    my_fund = fund.MaYiFund()
    raw_results = my_fund.get_fund_realtime_estimate_batch(codes)

    data: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for code, result in zip(codes, raw_results):
        if result is not None:
            data.append(result)
        else:
            errors.append({"code": code, "error": "查询失败或基金代码不存在"})
    return data, errors


def get_sector_funds_service(bk_id: str | None) -> str:
    importlib.reload(fund)
    my_fund = fund.MaYiFund()
    return my_fund.select_fund_html(bk_id=bk_id)


def render_fund_dashboard(add: str | None, delete: str | None) -> str:
    importlib.reload(fund)
    my_fund = fund.MaYiFund()
    if add:
        my_fund.add_code(add)
    if delete:
        my_fund.delete_code(delete)

    results: dict[str, str] = {}

    def fetch_html(name: str, func: Any) -> None:
        try:
            results[name] = func()
            logger.debug(f"✓ Successfully fetched {name}")
        except Exception as exc:
            logger.error(f"✗ Failed to fetch {name}: {exc}")
            results[name] = f"<p style='color:#f44336;'>数据加载失败: {str(exc)}</p>"

    tasks = {
        "marker": my_fund.marker_html,
        "gold": my_fund.gold_html,
        "real_time_gold": my_fund.real_time_gold_html,
        "A": my_fund.A_html,
        "fund": my_fund.fund_html,
        "seven_A": my_fund.seven_A_html,
        "bk": my_fund.bk_html,
        "kx": my_fund.kx_html,
        "select_fund": my_fund.select_fund_html,
    }
    threads: list[threading.Thread] = []
    for name, func in tasks.items():
        thread = threading.Thread(target=fetch_html, args=(name, func))
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()

    for name in tasks.keys():
        if name not in results:
            logger.warning(f"⚠️ Missing result for {name}, using fallback")
            results[name] = "<p style='color:#ff9800;'>数据未加载</p>"

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
    return get_full_page_html(tabs_data)
