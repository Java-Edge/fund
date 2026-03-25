from collections.abc import Callable
from typing import Any, TypeVar

from flask import Response, jsonify
from pydantic import BaseModel, ValidationError

from app.core.errors import AppError

ModelT = TypeVar("ModelT", bound=BaseModel)


def json_response(payload: dict[str, Any], status_code: int = 200) -> tuple[Response, int] | Response:
    return jsonify(payload), status_code

# 成功响应
def success_response(payload: dict[str, Any] | None = None, status_code: int = 200) -> tuple[Response, int] | Response:
    body = {"success": True}
    if payload:
        body.update(payload)
    return json_response(body, status_code)

# 错误包装
def error_response(
    message: str,
    status_code: int = 400,
    *,
    success: bool | None = None,
    field: str = "error",
    extra: dict[str, Any] | None = None,
) -> tuple[Response, int] | Response:
    body: dict[str, Any] = {}
    if success is not None:
        body["success"] = success
    body[field] = message
    if extra:
        body.update(extra)
    return json_response(body, status_code)

# 重复校验
def empty_options_response() -> tuple[Response, int]:
    return jsonify({}), 200


def validate_model(
    model_cls: type[ModelT],
    data: dict[str, Any],
    *,
    error_message: str,
    status_code: int = 400,
    success: bool | None = None,
    field: str = "error",
) -> ModelT:
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        raise RequestValidationError(
            error_message,
            status_code=status_code,
            success=success,
            field=field,
        ) from exc


class RequestValidationError(AppError):
    def __init__(self, message: str, *, status_code: int = 400, success: bool | None = None, field: str = "error"):
        super().__init__(message, status_code=status_code, success=success, field=field)


def with_error_boundary(
    func: Callable[[], tuple[Response, int] | Response],
    *,
    log_message: str,
    fallback_status: int = 500,
    success: bool | None = False,
    field: str = "error",
    logger: Any,
) -> tuple[Response, int] | Response:
    try:
        return func()
    except AppError as exc:
        return error_response(exc.message, exc.status_code, success=exc.success, field=exc.field)
    except Exception as exc:
        logger.error(f"{log_message}: {exc}")
        return error_response(str(exc), fallback_status, success=success, field=field)
