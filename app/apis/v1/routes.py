import datetime
from typing import Any

from flask import Blueprint, Response, redirect, request
from loguru import logger

from app.schemas.fund import FundBatchRequest, FundCodePath
from app.services.fund_service import (
    batch_query_funds_service,
    get_fund_estimate_service,
    get_fund_info_service,
    get_fund_realtime_batch_service,
    get_fund_realtime_service,
    get_sector_funds_service,
    render_fund_dashboard,
)
from app.utils.http import (
    RequestValidationError,
    error_response,
    success_response,
    validate_model,
    with_error_boundary,
)

api_v1_bp = Blueprint("api_v1", __name__)


@api_v1_bp.route("/", methods=["GET"])
def index() -> Response:
    return redirect("/fund")


@api_v1_bp.route("/health", methods=["GET"])
def health_check() -> Response:
    return {
        "status": "ok",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


@api_v1_bp.route("/fund/<fund_code>", methods=["GET", "OPTIONS"])
@api_v1_bp.route("/api/fund/<fund_code>", methods=["GET", "OPTIONS"])
def get_fund_info(fund_code: str) -> tuple[Response, int] | Response:
    def handle() -> tuple[Response, int] | Response:
        payload = validate_model(
            FundCodePath,
            {"fund_code": fund_code},
            error_message="基金代码必须为6位数字",
            success=False,
        )
        result = get_fund_info_service(payload.fund_code)
        if result is None:
            return error_response(f"基金 {payload.fund_code} 不存在或查询失败", 404, success=False)
        return success_response(result)

    return with_error_boundary(handle, log_message=f"查询基金 {fund_code} 失败", logger=logger)


@api_v1_bp.route("/fund/estimate/<fund_code>", methods=["GET", "OPTIONS"])
@api_v1_bp.route("/api/fund/estimate/<fund_code>", methods=["GET", "OPTIONS"])
def get_fund_estimate(fund_code: str) -> tuple[Response, int] | Response:
    def handle() -> tuple[Response, int] | Response:
        payload = validate_model(
            FundCodePath,
            {"fund_code": fund_code},
            error_message="基金代码必须为6位数字",
            success=False,
        )
        result = get_fund_estimate_service(payload.fund_code)
        if result is None:
            return error_response(f"基金 {payload.fund_code} 不存在或查询失败", 404, success=False)
        return success_response(result)

    return with_error_boundary(handle, log_message=f"查询基金估值 {fund_code} 失败", logger=logger)


@api_v1_bp.route("/fund/batch", methods=["POST", "OPTIONS"])
@api_v1_bp.route("/api/fund/batch", methods=["POST", "OPTIONS"])
def batch_query_funds() -> tuple[Response, int] | Response:
    def handle() -> tuple[Response, int] | Response:
        data = request.get_json(silent=True)
        if not data or "codes" not in data:
            raise RequestValidationError("缺少 codes 参数", success=False)

        codes = data["codes"]
        if not isinstance(codes, list):
            raise RequestValidationError("codes 必须是数组", success=False)
        if len(codes) > 20:
            raise RequestValidationError("批量查询最多支持20个基金", success=False)

        payload = validate_model(
            FundBatchRequest,
            {"codes": codes},
            error_message="所有基金代码必须为6位数字",
            success=False,
        )
        results, errors = batch_query_funds_service(payload.codes)
        return success_response(
            {"count": len(results), "data": results, "errors": errors if errors else None}
        )

    return with_error_boundary(handle, log_message="批量查询基金失败", logger=logger)


@api_v1_bp.route("/api/fund/realtime/<fund_code>", methods=["GET", "OPTIONS"])
@api_v1_bp.route("/fund/realtime/<fund_code>", methods=["GET", "OPTIONS"])
def get_fund_realtime(fund_code: str) -> tuple[Response, int] | Response:
    def handle() -> tuple[Response, int] | Response:
        payload = validate_model(
            FundCodePath,
            {"fund_code": fund_code},
            error_message="基金代码必须为6位数字",
            success=False,
        )
        result = get_fund_realtime_service(payload.fund_code)
        if result is None:
            return error_response(f"基金 {payload.fund_code} 查询失败，请确认代码是否正确", 404, success=False)
        return success_response(result)

    return with_error_boundary(handle, log_message=f"[realtime] 查询基金 {fund_code} 失败", logger=logger)


@api_v1_bp.route("/api/fund/realtime/batch", methods=["POST", "OPTIONS"])
@api_v1_bp.route("/fund/realtime/batch", methods=["POST", "OPTIONS"])
def get_fund_realtime_batch() -> tuple[Response, int] | Response:
    def handle() -> tuple[Response, int] | Response:
        body: dict[str, Any] | None = request.get_json(silent=True)
        if not body or "codes" not in body:
            raise RequestValidationError("缺少 codes 参数", success=False)
        if not isinstance(body["codes"], list) or len(body["codes"]) == 0:
            raise RequestValidationError("codes 必须是非空数组", success=False)
        if len(body["codes"]) > 50:
            raise RequestValidationError("批量查询最多支持50个基金", success=False)

        try:
            payload = validate_model(
                FundBatchRequest,
                {"codes": body["codes"]},
                error_message="所有基金代码必须为6位数字",
                success=False,
            )
        except RequestValidationError as exc:
            invalid = [str(code) for code in body["codes"] if not str(code).isdigit() or len(str(code)) != 6]
            raise RequestValidationError(
                f"无效基金代码: {', '.join(invalid)}，所有代码必须为6位数字",
                success=False,
                status_code=exc.status_code,
            ) from exc

        data, errors = get_fund_realtime_batch_service(payload.codes)
        return success_response(
            {"count": len(data), "data": data, "errors": errors if errors else None}
        )

    return with_error_boundary(handle, log_message="[realtime/batch] 批量查询失败", logger=logger)


@api_v1_bp.route("/fund/sector", methods=["GET"])
def get_sector_funds() -> str:
    bk_id = request.args.get("bk_id")
    return get_sector_funds_service(bk_id=bk_id)


@api_v1_bp.route("/fund", methods=["GET"])
def get_fund() -> str:
    add = request.args.get("add")
    delete = request.args.get("delete")
    return render_fund_dashboard(add=add, delete=delete)
