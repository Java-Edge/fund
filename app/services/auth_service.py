import json
import os
import time
from datetime import datetime
from typing import Any

from loguru import logger

from app.core.config import get_redis_config
from app.core.errors import AppError
from app.schemas.auth import AuthApplyRequest, AuthLoginRequest, AuthReviewRequest, AuthStatusQuery

_redis_client = None
_STATUS_MESSAGES = {
    "pending": "申请正在审核中",
    "approved": "申请已通过",
    "rejected": "申请已被拒绝",
    "banned": "账号已被禁用",
}


def get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            import redis

            _redis_client = redis.Redis(**get_redis_config())
            _redis_client.ping()
            logger.info("Auth Redis connected successfully")
        except Exception as exc:
            logger.error(f"Auth Redis 连接失败: {exc}")
            return None
    return _redis_client


def get_user_key(social_type: str, social_id: str) -> str:
    return f"user:{social_type}:{social_id}"


def _get_all_users() -> list[dict[str, Any]]:
    redis_client = get_redis()
    if not redis_client:
        return []

    users: list[dict[str, Any]] = []
    try:
        for key in redis_client.scan_iter(match="user:*"):
            user_data = redis_client.get(key)
            if user_data:
                users.append(json.loads(user_data))
    except Exception as exc:
        logger.error(f"获取用户列表失败: {exc}")
    return users


def _require_redis():
    redis_client = get_redis()
    if not redis_client:
        raise AppError("服务暂不可用", status_code=503)
    return redis_client


def init_default_admin() -> None:
    redis_client = get_redis()
    if not redis_client:
        logger.warning("Redis 不可用，跳过创建默认管理员")
        return

    admin_social_id = os.getenv("ADMIN_SOCIAL_ID", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin")
    admin_key = get_user_key("wechat", admin_social_id)

    try:
        if redis_client.exists(admin_key):
            logger.debug("默认管理员已存在")
            return

        admin_user = {
            "id": "admin_001",
            "socialType": "wechat",
            "socialId": admin_social_id,
            "nickname": "系统管理员",
            "password": admin_password,
            "status": "approved",
            "isAdmin": True,
            "appliedAt": datetime.now().isoformat(),
            "lastLoginAt": None,
        }
        redis_client.set(admin_key, json.dumps(admin_user))
        logger.info(f"默认管理员已创建: {admin_social_id}")
    except Exception as exc:
        logger.error(f"创建默认管理员失败: {exc}")


def submit_application_service(payload: AuthApplyRequest) -> dict[str, Any]:
    redis_client = _require_redis()
    user_key = get_user_key(payload.socialType, payload.socialId)

    if redis_client.exists(user_key):
        user_data = json.loads(redis_client.get(user_key))
        if user_data["status"] == "approved":
            raise AppError("该账号已通过审核，请直接登录")
        raise AppError("该账号已提交申请，请等待审核")

    new_user = {
        "id": f"user_{int(time.time() * 1000)}",
        "socialType": payload.socialType,
        "socialId": payload.socialId,
        "nickname": payload.nickname,
        "password": payload.password or None,
        "applyReason": payload.applyReason,
        "status": "pending",
        "isAdmin": False,
        "appliedAt": datetime.now().isoformat(),
        "lastLoginAt": None,
    }
    redis_client.set(user_key, json.dumps(new_user))
    logger.info(f"新用户申请: {payload.socialType}:{payload.socialId}")

    return {
        "success": True,
        "message": "申请已提交，请等待管理员审核",
        "data": {"userId": new_user["id"], "status": "pending"},
    }


def login_service(payload: AuthLoginRequest) -> dict[str, Any]:
    redis_client = _require_redis()
    user_key = get_user_key(payload.socialType, payload.socialId)
    user_data = redis_client.get(user_key)

    if not user_data:
        raise AppError("账号不存在，请先提交申请")

    user = json.loads(user_data)
    if user["status"] == "pending":
        raise AppError("申请正在审核中，请耐心等待")
    if user["status"] == "rejected":
        raise AppError("申请已被拒绝")
    if user["status"] == "banned":
        raise AppError("账号已被禁用")
    if user.get("password") and user["password"] != payload.password:
        raise AppError("密码错误")

    user["lastLoginAt"] = datetime.now().isoformat()
    redis_client.set(user_key, json.dumps(user))
    logger.info(f"用户登录: {payload.socialType}:{payload.socialId}")

    return {
        "success": True,
        "message": "登录成功",
        "data": {
            "userId": user["id"],
            "socialId": user["socialId"],
            "socialType": user["socialType"],
            "nickname": user["nickname"],
            "status": user["status"],
            "isAdmin": user.get("isAdmin", False),
        },
    }


def check_status_service(query: AuthStatusQuery) -> dict[str, Any]:
    redis_client = _require_redis()
    user_data = redis_client.get(get_user_key(query.socialType, query.socialId))
    if not user_data:
        return {"success": True, "data": {"exists": False, "status": None, "message": "未找到申请记录"}}

    user = json.loads(user_data)
    return {
        "success": True,
        "data": {
            "exists": True,
            "status": user["status"],
            "message": _STATUS_MESSAGES.get(user["status"], "未知状态"),
        },
    }


def get_applications_service() -> dict[str, Any]:
    _require_redis()
    applications = [
        {
            "id": user["id"],
            "socialType": user["socialType"],
            "socialId": user["socialId"],
            "nickname": user["nickname"],
            "applyReason": user.get("applyReason", ""),
            "status": user["status"],
            "appliedAt": user["appliedAt"],
            "reviewedAt": user.get("reviewedAt"),
            "reviewerNote": user.get("reviewerNote", ""),
            "isAdmin": user.get("isAdmin", False),
        }
        for user in _get_all_users()
    ]
    applications.sort(key=lambda item: item["appliedAt"], reverse=True)
    return {"success": True, "data": applications}


def review_application_service(payload: AuthReviewRequest) -> dict[str, Any]:
    redis_client = _require_redis()

    target_user = None
    target_key = None
    for user in _get_all_users():
        if user["id"] == payload.userId:
            target_user = user
            target_key = get_user_key(user["socialType"], user["socialId"])
            break

    if not target_user or not target_key:
        raise AppError("用户不存在", status_code=404)

    if payload.action == "approve":
        target_user["status"] = "approved"
    elif payload.action == "reject":
        target_user["status"] = "rejected"
    else:
        raise AppError("无效的操作")

    target_user["reviewedAt"] = datetime.now().isoformat()
    target_user["reviewerNote"] = payload.note
    redis_client.set(target_key, json.dumps(target_user))
    logger.info(f"审核用户: {target_user['socialId']} -> {payload.action}")

    return {
        "success": True,
        "message": "审核完成",
        "data": {"userId": target_user["id"], "status": target_user["status"]},
    }


def get_stats_service() -> dict[str, Any]:
    _require_redis()
    users = _get_all_users()
    pending = sum(1 for user in users if user["status"] == "pending")
    approved = sum(1 for user in users if user["status"] == "approved")
    rejected = sum(1 for user in users if user["status"] == "rejected")
    banned = sum(1 for user in users if user["status"] == "banned")

    return {
        "success": True,
        "data": {
            "totalApplications": len(users),
            "pendingApplications": pending,
            "approvedApplications": approved,
            "rejectedApplications": rejected,
            "bannedApplications": banned,
        },
    }
