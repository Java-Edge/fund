import datetime
from typing import Any

from app.ai.text_utils import clean_ansi_codes


def _get_fund_entries(data_collector, *, include_extended_fields: bool) -> list[dict[str, Any]]:
    fund_entries: list[dict[str, Any]] = []
    result_dict = {fund[0]: fund for fund in data_collector.result}

    for fund_code, fund_info in data_collector.CACHE_MAP.items():
        fund = result_dict.get(fund_code)
        if not fund:
            continue

        entry: dict[str, Any] = {
            "code": fund[0],
            "name": clean_ansi_codes(fund[1].replace("⭐ ", "")),
            "forecast": clean_ansi_codes(fund[3]),
            "growth": clean_ansi_codes(fund[4]),
            "is_hold": fund_info.get("is_hold", False),
        }
        if include_extended_fields:
            entry.update(
                {
                    "consecutive": clean_ansi_codes(fund[5]),
                    "consecutive_growth": clean_ansi_codes(fund[6]),
                    "month_stats": clean_ansi_codes(fund[7]),
                    "month_growth": clean_ansi_codes(fund[8]),
                }
            )
        fund_entries.append(entry)

    return fund_entries


def build_standard_context(data_collector) -> dict[str, str]:
    market_data = data_collector.get_market_info(is_return=True)
    market_summary = "主要市场指数：\n"
    for item in market_data[:10]:
        market_summary += f"- {item[0]}: {item[1]} ({item[2]})\n"

    kx_data = data_collector.kx(is_return=True)
    kx_summary = "7×24快讯（最新10条）：\n"
    for index, item in enumerate(kx_data[:10], 1):
        evaluate = item.get("evaluate", "")
        evaluate_tag = f"【{evaluate}】" if evaluate else ""
        title = item.get("title", item.get("content", {}).get("items", [{}])[0].get("data", ""))
        publish_time = datetime.datetime.fromtimestamp(int(item["publish_time"])).strftime("%Y-%m-%d %H:%M:%S")
        entity = item.get("entity", [])
        if entity:
            entity_str = ", ".join([f"{x['code']}-{x['name']}" for x in entity[:3]])
            kx_summary += f"{index}. {publish_time} {evaluate_tag}{title} (影响: {entity_str})\n"
        else:
            kx_summary += f"{index}. {publish_time} {evaluate_tag}{title}\n"

    gold_data = data_collector.gold(is_return=True)
    gold_summary = "近期金价（最近5天）：\n"
    for item in gold_data[:5]:
        gold_summary += f"- {item[0]}: 中国黄金{item[1]}, 周大福{item[2]}, 涨跌({item[3]}, {item[4]})\n"

    realtime_gold_data = data_collector.real_time_gold(is_return=True)
    realtime_gold_summary = "实时金价：\n"
    if realtime_gold_data and len(realtime_gold_data) == 2:
        for row in realtime_gold_data:
            if row:
                realtime_gold_summary += f"- {row[0]}: 最新价{row[1]}, 涨跌幅{row[3]}\n"

    seven_a_data = data_collector.seven_A(is_return=True)
    seven_a_summary = "近7日成交量（最近3天）：\n"
    for item in seven_a_data[:3]:
        seven_a_summary += f"- {item[0]}: 总成交{item[1]}, 上交所{item[2]}, 深交所{item[3]}, 北交所{item[4]}\n"

    a_data = data_collector.A(is_return=True)
    a_summary = "近30分钟上证指数（最近5分钟）：\n"
    for item in a_data[-5:]:
        a_summary += f"- {item[0]}: {item[1]}, 涨跌额{item[2]}, 涨跌幅{item[3]}, 成交量{item[4]}, 成交额{item[5]}\n"

    bk_data = data_collector.bk(is_return=True)
    top_sectors = "涨幅前5板块：\n"
    for index, item in enumerate(bk_data[:5], 1):
        top_sectors += f"{index}. {item[0]}: {item[1]}, 主力净流入{item[2]}, 主力流入占比{item[3]}\n"

    bottom_sectors = "跌幅后5板块：\n"
    for index, item in enumerate(bk_data[-5:], 1):
        bottom_sectors += f"{index}. {item[0]}: {item[1]}, 主力净流入{item[2]}, 主力流入占比{item[3]}\n"

    fund_data = _get_fund_entries(data_collector, include_extended_fields=True)
    fund_summary = f"自选基金总数: {len(fund_data)}只\n\n"

    hold_funds = [fund for fund in fund_data if fund["is_hold"]]
    if hold_funds:
        fund_summary += "持有基金：\n"
        for index, fund in enumerate(hold_funds, 1):
            fund_summary += (
                f"{index}. {fund['name']}: 估值{fund['forecast']}, 日涨幅{fund['growth']}, "
                f"连续{fund['consecutive']}天, 近30天{fund['month_stats']}\n"
            )
        fund_summary += "\n"

    top_funds = sorted(
        fund_data,
        key=lambda item: float(item["forecast"].replace("%", "")) if item["forecast"] != "N/A" else -999,
        reverse=True,
    )[:5]
    fund_summary += "今日涨幅前5的基金：\n"
    for index, fund in enumerate(top_funds, 1):
        hold_mark = "【持有】" if fund["is_hold"] else ""
        fund_summary += f"{index}. {hold_mark}{fund['name']}: 估值{fund['forecast']}, 日涨幅{fund['growth']}\n"

    return {
        "market_summary": market_summary,
        "kx_summary": kx_summary,
        "gold_summary": gold_summary,
        "realtime_gold_summary": realtime_gold_summary,
        "seven_a_summary": seven_a_summary,
        "a_summary": a_summary,
        "top_sectors": top_sectors,
        "bottom_sectors": bottom_sectors,
        "fund_summary": fund_summary,
    }


def build_fast_context(data_collector) -> dict[str, str]:
    market_data = data_collector.get_market_info(is_return=True)
    market_summary = "主要市场指数：\n"
    for item in market_data[:8]:
        market_summary += f"- {item[0]}: {item[1]} ({item[2]})\n"

    kx_data = data_collector.kx(is_return=True)
    kx_summary = "最新快讯（前5条）：\n"
    for index, item in enumerate(kx_data[:5], 1):
        evaluate = item.get("evaluate", "")
        evaluate_tag = f"【{evaluate}】" if evaluate else ""
        title = item.get("title", item.get("content", {}).get("items", [{}])[0].get("data", ""))
        kx_summary += f"{index}. {evaluate_tag}{title}\n"

    bk_data = data_collector.bk(is_return=True)
    top_sectors = "涨幅前5板块：\n"
    for index, item in enumerate(bk_data[:5], 1):
        top_sectors += f"{index}. {item[0]}: {item[1]}, 主力净流入{item[2]}\n"

    fund_data = _get_fund_entries(data_collector, include_extended_fields=False)
    fund_summary = f"自选基金总数: {len(fund_data)}只\n"
    hold_funds = [fund for fund in fund_data if fund["is_hold"]]
    if hold_funds:
        fund_summary += f"持有基金数: {len(hold_funds)}只\n"

    top_funds = sorted(
        fund_data,
        key=lambda item: float(item["forecast"].replace("%", "")) if item["forecast"] != "N/A" else -999,
        reverse=True,
    )[:3]
    fund_summary += "今日涨幅前3的基金：\n"
    for index, fund in enumerate(top_funds, 1):
        hold_mark = "【持有】" if fund["is_hold"] else ""
        fund_summary += f"{index}. {hold_mark}{fund['name']}: 估值{fund['forecast']}\n"

    return {
        "market_summary": market_summary,
        "kx_summary": kx_summary,
        "top_sectors": top_sectors,
        "fund_summary": fund_summary,
    }


def build_portfolio_text(data_collector) -> str:
    fund_data = _get_fund_entries(data_collector, include_extended_fields=True)
    result = f"自选基金总数: {len(fund_data)}只\n\n"

    hold_funds = [fund for fund in fund_data if fund["is_hold"]]
    if hold_funds:
        result += f"持有基金（{len(hold_funds)}只）：\n"
        for index, fund in enumerate(hold_funds, 1):
            result += (
                f"{index}. {fund['name']}({fund['code']}): 估值{fund['forecast']}, 日涨幅{fund['growth']}, "
                f"连续{fund['consecutive']}天, 近30天{fund['month_stats']}\n"
            )
        result += "\n"

    top_funds = sorted(
        fund_data,
        key=lambda item: float(item["forecast"].replace("%", "")) if item["forecast"] != "N/A" else -999,
        reverse=True,
    )[:8]
    result += "今日涨幅前8的基金：\n"
    for index, fund in enumerate(top_funds, 1):
        hold_mark = "【持有】" if fund["is_hold"] else ""
        result += (
            f"{index}. {hold_mark}{fund['name']}({fund['code']}): 估值{fund['forecast']}, "
            f"日涨幅{fund['growth']}, 近30天{fund['month_stats']}\n"
        )
    return result
