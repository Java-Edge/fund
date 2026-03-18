import datetime
from typing import Any

from flask import Blueprint, Response, jsonify, redirect, request, stream_with_context
from loguru import logger
from pydantic import ValidationError

from app.schemas.chat import ChatRequest
from app.schemas.fund import FundBatchRequest, FundCodePath
from app.services.chat_service import stream_chat_sse
from app.services.fund_service import (
    batch_query_funds_service,
    get_fund_estimate_service,
    get_fund_info_service,
    get_fund_realtime_batch_service,
    get_fund_realtime_service,
    get_sector_funds_service,
    render_fund_dashboard,
)

api_v1_bp = Blueprint("api_v1", __name__)


@api_v1_bp.route("/api/chat", methods=["POST", "OPTIONS"])
def chat() -> Response:
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        payload = ChatRequest.model_validate(request.get_json() or {})
    except ValidationError:
        return jsonify({"error": "Bad Request", "message": "Invalid request payload"}), 400

    return Response(
        stream_with_context(stream_chat_sse(payload.message, payload.history_as_dicts())),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@api_v1_bp.route("/", methods=["GET"])
def index() -> Response:
    return redirect("/fund")


@api_v1_bp.route("/health", methods=["GET"])
def health_check() -> Response:
    return jsonify({"status": "ok", "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})


@api_v1_bp.route("/fund/<fund_code>", methods=["GET", "OPTIONS"])
@api_v1_bp.route("/api/fund/<fund_code>", methods=["GET", "OPTIONS"])
def get_fund_info(fund_code: str) -> tuple[Response, int] | Response:
    if request.method == "OPTIONS":
        return jsonify({}), 200
    try:
        payload = FundCodePath.model_validate({"fund_code": fund_code})
    except ValidationError:
        return jsonify({"success": False, "error": "基金代码必须为6位数字"}), 400

    try:
        result = get_fund_info_service(payload.fund_code)
        if result is None:
            return jsonify({"success": False, "error": f"基金 {payload.fund_code} 不存在或查询失败"}), 404
        return jsonify({"success": True, **result})
    except Exception as exc:
        logger.error(f"查询基金 {payload.fund_code} 失败: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@api_v1_bp.route("/fund/estimate/<fund_code>", methods=["GET", "OPTIONS"])
@api_v1_bp.route("/api/fund/estimate/<fund_code>", methods=["GET", "OPTIONS"])
def get_fund_estimate(fund_code: str) -> tuple[Response, int] | Response:
    if request.method == "OPTIONS":
        return jsonify({}), 200
    try:
        payload = FundCodePath.model_validate({"fund_code": fund_code})
    except ValidationError:
        return jsonify({"success": False, "error": "基金代码必须为6位数字"}), 400

    try:
        result = get_fund_estimate_service(payload.fund_code)
        if result is None:
            return jsonify({"success": False, "error": f"基金 {payload.fund_code} 不存在或查询失败"}), 404
        return jsonify({"success": True, **result})
    except Exception as exc:
        logger.error(f"查询基金估值 {payload.fund_code} 失败: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@api_v1_bp.route("/fund/batch", methods=["POST", "OPTIONS"])
@api_v1_bp.route("/api/fund/batch", methods=["POST", "OPTIONS"])
def batch_query_funds() -> tuple[Response, int] | Response:
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data = request.get_json(silent=True)
    if not data or "codes" not in data:
        return jsonify({"success": False, "error": "缺少 codes 参数"}), 400

    codes = data["codes"]
    if not isinstance(codes, list):
        return jsonify({"success": False, "error": "codes 必须是数组"}), 400
    if len(codes) > 20:
        return jsonify({"success": False, "error": "批量查询最多支持20个基金"}), 400

    try:
        payload = FundBatchRequest.model_validate({"codes": codes})
    except ValidationError:
        return jsonify({"success": False, "error": "所有基金代码必须为6位数字"}), 400

    try:
        results, errors = batch_query_funds_service(payload.codes)
        return jsonify(
            {"success": True, "count": len(results), "data": results, "errors": errors if errors else None}
        )
    except Exception as exc:
        logger.error(f"批量查询基金失败: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@api_v1_bp.route("/api/fund/realtime/<fund_code>", methods=["GET", "OPTIONS"])
@api_v1_bp.route("/fund/realtime/<fund_code>", methods=["GET", "OPTIONS"])
def get_fund_realtime(fund_code: str) -> tuple[Response, int] | Response:
    if request.method == "OPTIONS":
        return jsonify({}), 200
    try:
        payload = FundCodePath.model_validate({"fund_code": fund_code})
    except ValidationError:
        return jsonify({"success": False, "error": "基金代码必须为6位数字"}), 400

    try:
        result = get_fund_realtime_service(payload.fund_code)
        if result is None:
            return jsonify({"success": False, "error": f"基金 {payload.fund_code} 查询失败，请确认代码是否正确"}), 404
        return jsonify({"success": True, **result})
    except Exception as exc:
        logger.error(f"[realtime] 查询基金 {payload.fund_code} 失败: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@api_v1_bp.route("/api/fund/realtime/batch", methods=["POST", "OPTIONS"])
@api_v1_bp.route("/fund/realtime/batch", methods=["POST", "OPTIONS"])
def get_fund_realtime_batch() -> tuple[Response, int] | Response:
    if request.method == "OPTIONS":
        return jsonify({}), 200

    body: dict[str, Any] | None = request.get_json(silent=True)
    if not body or "codes" not in body:
        return jsonify({"success": False, "error": "缺少 codes 参数"}), 400
    if not isinstance(body["codes"], list) or len(body["codes"]) == 0:
        return jsonify({"success": False, "error": "codes 必须是非空数组"}), 400
    if len(body["codes"]) > 50:
        return jsonify({"success": False, "error": "批量查询最多支持50个基金"}), 400

    try:
        payload = FundBatchRequest.model_validate({"codes": body["codes"]})
    except ValidationError:
        invalid = [str(code) for code in body["codes"] if not str(code).isdigit() or len(str(code)) != 6]
        return jsonify(
            {"success": False, "error": f"无效基金代码: {', '.join(invalid)}，所有代码必须为6位数字"}
        ), 400

    try:
        data, errors = get_fund_realtime_batch_service(payload.codes)
        return jsonify(
            {
                "success": True,
                "count": len(data),
                "data": data,
                "errors": errors if errors else None,
            }
        )
    except Exception as exc:
        logger.error(f"[realtime/batch] 批量查询失败: {exc}")
        return jsonify({"success": False, "error": str(exc)}), 500


@api_v1_bp.route("/fund/sector", methods=["GET"])
def get_sector_funds() -> str:
    bk_id = request.args.get("bk_id")
    return get_sector_funds_service(bk_id=bk_id)


@api_v1_bp.route("/fund", methods=["GET"])
def get_fund() -> str:
    add = request.args.get("add")
    delete = request.args.get("delete")
    return render_fund_dashboard(add=add, delete=delete)
