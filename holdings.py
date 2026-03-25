"""
持仓管理 API
提供用户持仓的增删改查功能，数据存储在 MySQL
"""

from flask import Blueprint, request
from loguru import logger

from app.core.errors import AppError
from app.schemas.holdings import (
    HoldingBatchCreateRequest,
    HoldingCreateRequest,
    HoldingUpdateRequest,
    HoldingUserQuery,
)
from app.services.holdings_service import (
    add_holding_service,
    batch_add_holdings_service,
    delete_holding_service,
    get_holdings_service,
    init_holdings_table,
    update_holding_service,
)
from app.utils.http import error_response, json_response, validate_model

holdings_bp = Blueprint("holdings", __name__, url_prefix="/api/holdings")


def _handle_service_error(exc: Exception, *, action: str):
    if isinstance(exc, AppError):
        return error_response(exc.message, exc.status_code, success=exc.success, field=exc.field)

    logger.error(f"{action}: {exc}")
    return error_response(action, 500, success=False)


@holdings_bp.route("", methods=["GET", "OPTIONS"])
def get_holdings():
    try:
        payload = validate_model(
            HoldingUserQuery,
            request.args.to_dict(),
            error_message="缺少 userId 参数",
            success=False,
            field="message",
        )
        return json_response(get_holdings_service(payload))
    except Exception as exc:
        return _handle_service_error(exc, action="获取持仓列表失败")


@holdings_bp.route("", methods=["POST", "OPTIONS"])
def add_holding():
    try:
        payload = validate_model(
            HoldingCreateRequest,
            request.get_json() or {},
            error_message="缺少必要参数",
            success=False,
            field="message",
        )
        return json_response(add_holding_service(payload))
    except Exception as exc:
        return _handle_service_error(exc, action="添加持仓失败")


@holdings_bp.route("/<holding_id>", methods=["DELETE", "OPTIONS"])
def delete_holding(holding_id):
    try:
        payload = validate_model(
            HoldingUserQuery,
            request.args.to_dict(),
            error_message="缺少 userId 参数",
            success=False,
            field="message",
        )
        return json_response(delete_holding_service(holding_id, payload))
    except Exception as exc:
        return _handle_service_error(exc, action="删除持仓失败")


@holdings_bp.route("/<holding_id>", methods=["PUT", "OPTIONS"])
def update_holding(holding_id):
    try:
        payload = validate_model(
            HoldingUpdateRequest,
            request.get_json() or {},
            error_message="缺少 userId 参数",
            success=False,
            field="message",
        )
        return json_response(update_holding_service(holding_id, payload))
    except Exception as exc:
        return _handle_service_error(exc, action="更新持仓失败")


@holdings_bp.route("/batch", methods=["POST", "OPTIONS"])
def batch_add_holdings():
    try:
        payload = validate_model(
            HoldingBatchCreateRequest,
            request.get_json() or {},
            error_message="缺少 userId 参数",
            success=False,
            field="message",
        )
        return json_response(batch_add_holdings_service(payload))
    except Exception as exc:
        return _handle_service_error(exc, action="批量添加持仓失败")
