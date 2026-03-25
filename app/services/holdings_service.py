import time
from typing import Any

from loguru import logger

from app.core.config import get_mysql_config
from app.core.errors import AppError
from app.schemas.holdings import (
    HoldingBatchCreateRequest,
    HoldingCreateRequest,
    HoldingUpdateRequest,
    HoldingUserQuery,
)

_db_pool = None


def get_db_connection():
    global _db_pool
    if _db_pool is None:
        return _create_connection()

    try:
        _db_pool.ping(reconnect=True)
    except Exception:
        logger.warning("MySQL 连接已失效，尝试重新连接...")
        _db_pool = None
        return _create_connection()

    return _db_pool


def _create_connection():
    global _db_pool
    try:
        import pymysql
        from pymysql.cursors import DictCursor

        config = get_mysql_config()
        logger.info(f"连接 MySQL: {config['host']}:{config['port']}/{config['database']}")
        _db_pool = pymysql.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
            charset=config["charset"],
            cursorclass=DictCursor,
            autocommit=True,
            connect_timeout=10,
            read_timeout=30,
            write_timeout=30,
        )
        logger.info("MySQL connected successfully")
        return _db_pool
    except Exception as exc:
        logger.error(f"MySQL 连接失败: {exc}")
        return None


def _require_db():
    db = get_db_connection()
    if not db:
        raise AppError("数据库服务暂不可用", status_code=503)
    return db


def init_holdings_table() -> None:
    db = get_db_connection()
    if not db:
        logger.warning("MySQL 不可用，跳过创建持仓表")
        return

    try:
        with db.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_holdings (
                    id VARCHAR(50) PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    fund_code VARCHAR(10) NOT NULL,
                    fund_name VARCHAR(100) NOT NULL,
                    fund_type VARCHAR(20) DEFAULT 'equity',
                    shares DECIMAL(15, 4) DEFAULT 0,
                    cost_price DECIMAL(10, 4) DEFAULT 0,
                    account_id VARCHAR(50) DEFAULT 'alipay',
                    watch_only TINYINT(1) DEFAULT 0,
                    is_deleted TINYINT(1) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id),
                    UNIQUE KEY uk_user_fund (user_id, fund_code, is_deleted)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            logger.info("持仓表初始化完成")
    except Exception as exc:
        logger.error(f"创建持仓表失败: {exc}")


def get_holdings_service(query: HoldingUserQuery) -> dict[str, Any]:
    db = _require_db()
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, fund_code as code, fund_name as name, fund_type as type,
                   shares, cost_price as cost, account_id as accountId,
                   watch_only as watchOnly
            FROM user_holdings
            WHERE user_id = %s AND is_deleted = 0
            ORDER BY created_at DESC
            """,
            (query.userId,),
        )
        holdings = cursor.fetchall()

    for holding in holdings:
        holding["shares"] = float(holding["shares"]) if holding["shares"] else 0
        holding["cost"] = float(holding["cost"]) if holding["cost"] else 0
        holding["watchOnly"] = bool(holding["watchOnly"])

    return {"success": True, "data": holdings}


def add_holding_service(payload: HoldingCreateRequest) -> dict[str, Any]:
    db = _require_db()
    holding_id = f"hold_{int(time.time() * 1000)}"

    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, is_deleted FROM user_holdings
            WHERE user_id = %s AND fund_code = %s
            """,
            (payload.userId, payload.code),
        )
        existing = cursor.fetchone()

        if existing:
            if existing["is_deleted"] == 0:
                raise AppError("该持仓已存在")

            cursor.execute(
                """
                UPDATE user_holdings
                SET is_deleted = 0, shares = %s, cost_price = %s,
                    account_id = %s, watch_only = %s, fund_name = %s,
                    fund_type = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (
                    payload.shares,
                    payload.cost,
                    payload.accountId,
                    1 if payload.watchOnly else 0,
                    payload.name,
                    payload.type,
                    existing["id"],
                ),
            )
            return {"success": True, "message": "持仓已恢复", "data": {"id": existing["id"]}}

        cursor.execute(
            """
            INSERT INTO user_holdings
            (id, user_id, fund_code, fund_name, fund_type, shares, cost_price, account_id, watch_only)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                holding_id,
                payload.userId,
                payload.code,
                payload.name,
                payload.type,
                payload.shares,
                payload.cost,
                payload.accountId,
                1 if payload.watchOnly else 0,
            ),
        )

    logger.info(f"添加持仓: {payload.userId} -> {payload.code}")
    return {"success": True, "message": "添加成功", "data": {"id": holding_id}}


def delete_holding_service(holding_id: str, query: HoldingUserQuery) -> dict[str, Any]:
    db = _require_db()
    with db.cursor() as cursor:
        cursor.execute(
            """
            UPDATE user_holdings
            SET is_deleted = 1, updated_at = NOW()
            WHERE id = %s AND user_id = %s AND is_deleted = 0
            """,
            (holding_id, query.userId),
        )
        if cursor.rowcount == 0:
            raise AppError("持仓不存在或无权限", status_code=404)

    logger.info(f"删除持仓: {holding_id}")
    return {"success": True, "message": "删除成功"}


def update_holding_service(holding_id: str, payload: HoldingUpdateRequest) -> dict[str, Any]:
    updates = payload.to_updates()
    if not updates:
        raise AppError("没有需要更新的字段")

    fields = []
    values = []
    for key, value in updates.items():
        fields.append(f"{key} = %s")
        values.append(value)
    values.extend([holding_id, payload.userId])

    db = _require_db()
    with db.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE user_holdings
            SET {", ".join(fields)}, updated_at = NOW()
            WHERE id = %s AND user_id = %s AND is_deleted = 0
            """,
            tuple(values),
        )
        if cursor.rowcount == 0:
            raise AppError("持仓不存在或无权限", status_code=404)

    logger.info(f"更新持仓: {holding_id}")
    return {"success": True, "message": "更新成功"}


def batch_add_holdings_service(payload: HoldingBatchCreateRequest) -> dict[str, Any]:
    if not payload.holdings or len(payload.holdings) > 50:
        raise AppError("持仓数量必须在 1-50 之间")

    db = _require_db()
    success_count = 0
    failed_items: list[dict[str, Any]] = []

    with db.cursor() as cursor:
        for item in payload.holdings:
            try:
                if not item.code or not item.name:
                    failed_items.append({"code": item.code, "reason": "缺少 code 或 name"})
                    continue

                holding_id = f"hold_{int(time.time() * 1000)}_{success_count}"
                cursor.execute(
                    """
                    INSERT INTO user_holdings
                    (id, user_id, fund_code, fund_name, fund_type, shares, cost_price, account_id, watch_only)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    is_deleted = 0, shares = VALUES(shares), cost_price = VALUES(cost_price),
                    account_id = VALUES(account_id), watch_only = VALUES(watch_only),
                    fund_name = VALUES(fund_name), fund_type = VALUES(fund_type),
                    updated_at = NOW()
                    """,
                    (
                        holding_id,
                        payload.userId,
                        item.code,
                        item.name,
                        item.type,
                        item.shares,
                        item.cost,
                        item.accountId,
                        1 if item.watchOnly else 0,
                    ),
                )
                success_count += 1
            except Exception as exc:
                failed_items.append({"code": item.code, "reason": str(exc)})

    logger.info(f"批量添加持仓: {payload.userId} 成功 {success_count}/{len(payload.holdings)}")
    return {
        "success": True,
        "message": f"成功添加 {success_count} 个持仓",
        "data": {
            "total": len(payload.holdings),
            "success": success_count,
            "failed": len(failed_items),
            "failedItems": failed_items if failed_items else None,
        },
    }
