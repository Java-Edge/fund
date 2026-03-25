"""
认证管理 API
提供用户申请、登录、审核等功能，数据存储在 Redis
"""

from flask import Blueprint, request
from loguru import logger

from app.core.errors import AppError
from app.schemas.auth import AuthApplyRequest, AuthLoginRequest, AuthReviewRequest, AuthStatusQuery
from app.services.auth_service import (
    check_status_service,
    get_applications_service,
    get_stats_service,
    init_default_admin,
    login_service,
    review_application_service,
    submit_application_service,
)
from app.utils.http import error_response, json_response, validate_model

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _handle_service_error(exc: Exception, *, action: str):
    if isinstance(exc, AppError):
        return error_response(exc.message, exc.status_code, success=exc.success, field=exc.field)

    logger.error(f"{action}: {exc}")
    return error_response(action, 500, success=False)


@auth_bp.route("/apply", methods=["POST", "OPTIONS"])
def submit_application():
    try:
        payload = validate_model(
            AuthApplyRequest,
            request.get_json() or {},
            error_message="缺少必要参数",
            success=False,
            field="message",
        )
        return json_response(submit_application_service(payload))
    except Exception as exc:
        return _handle_service_error(exc, action="提交申请失败")


@auth_bp.route("/login", methods=["POST", "OPTIONS"])
def login():
    try:
        payload = validate_model(
            AuthLoginRequest,
            request.get_json() or {},
            error_message="缺少必要参数",
            success=False,
            field="message",
        )
        return json_response(login_service(payload))
    except Exception as exc:
        return _handle_service_error(exc, action="登录失败")


@auth_bp.route("/status", methods=["GET", "OPTIONS"])
def check_status():
    try:
        payload = validate_model(
            AuthStatusQuery,
            request.args.to_dict(),
            error_message="缺少必要参数",
            success=False,
            field="message",
        )
        return json_response(check_status_service(payload))
    except Exception as exc:
        return _handle_service_error(exc, action="检查状态失败")


@auth_bp.route("/applications", methods=["GET", "OPTIONS"])
def get_applications():
    try:
        return json_response(get_applications_service())
    except Exception as exc:
        return _handle_service_error(exc, action="获取申请列表失败")


@auth_bp.route("/review", methods=["POST", "OPTIONS"])
def review_application():
    try:
        payload = validate_model(
            AuthReviewRequest,
            request.get_json() or {},
            error_message="缺少必要参数",
            success=False,
            field="message",
        )
        return json_response(review_application_service(payload))
    except Exception as exc:
        return _handle_service_error(exc, action="审核失败")


@auth_bp.route("/stats", methods=["GET", "OPTIONS"])
def get_stats():
    try:
        return json_response(get_stats_service())
    except Exception as exc:
        return _handle_service_error(exc, action="获取统计失败")