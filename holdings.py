"""
持仓管理 API
提供用户持仓的增删改查功能，数据存储在 MySQL
"""
from flask import Blueprint, request, jsonify
import json
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from loguru import logger

# 创建蓝图
holdings_bp = Blueprint('holdings', __name__, url_prefix='/api/holdings')

# MySQL 固定配置
def get_mysql_config():
    """获取 MySQL 配置"""
    return {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '123456',
        'database': 'jijin_db',
        'charset': 'utf8'
    }

# 全局 MySQL 连接池
_db_pool = None

def get_db_connection():
    """获取数据库连接"""
    global _db_pool
    if _db_pool is None:
        try:
            import pymysql
            from pymysql.cursors import DictCursor
            
            config = get_mysql_config()
            logger.info(f"连接 MySQL: {config['host']}:{config['port']}/{config['database']}")
            _db_pool = pymysql.connect(
                host=config['host'],
                port=config['port'],
                user=config['user'],
                password=config['password'],
                database=config['database'],
                charset=config['charset'],
                cursorclass=DictCursor,
                autocommit=True
            )
            logger.info("MySQL connected successfully")
        except Exception as e:
            logger.error(f"MySQL 连接失败: {e}")
            return None
    return _db_pool

def init_holdings_table():
    """初始化持仓表"""
    db = get_db_connection()
    if not db:
        logger.warning("MySQL 不可用，跳过创建持仓表")
        return
    
    try:
        with db.cursor() as cursor:
            cursor.execute("""
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
            """)
            logger.info("持仓表初始化完成")
    except Exception as e:
        logger.error(f"创建持仓表失败: {e}")

# ============ API 路由 ============

@holdings_bp.route('', methods=['GET', 'OPTIONS'])
def get_holdings():
    """获取持仓列表"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = request.args.get('userId')
        if not user_id:
            return jsonify({'success': False, 'message': '缺少 userId 参数'}), 400
        
        db = get_db_connection()
        if not db:
            return jsonify({'success': False, 'message': '数据库服务暂不可用'}), 503
        
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT id, fund_code as code, fund_name as name, fund_type as type,
                       shares, cost_price as cost, account_id as accountId, 
                       watch_only as watchOnly
                FROM user_holdings 
                WHERE user_id = %s AND is_deleted = 0
                ORDER BY created_at DESC
            """, (user_id,))
            
            holdings = cursor.fetchall()
            
            # 转换数据类型
            for h in holdings:
                h['shares'] = float(h['shares']) if h['shares'] else 0
                h['cost'] = float(h['cost']) if h['cost'] else 0
                h['watchOnly'] = bool(h['watchOnly'])
            
            return jsonify({
                'success': True,
                'data': holdings
            })
            
    except Exception as e:
        logger.error(f"获取持仓列表失败: {e}")
        return jsonify({'success': False, 'message': '获取持仓列表失败'}), 500

@holdings_bp.route('', methods=['POST', 'OPTIONS'])
def add_holding():
    """添加持仓"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        data = request.get_json() or {}
        user_id = data.get('userId')
        code = data.get('code')
        name = data.get('name')
        fund_type = data.get('type', 'equity')
        shares = data.get('shares', 0)
        cost = data.get('cost', 0)
        account_id = data.get('accountId', 'alipay')
        watch_only = data.get('watchOnly', False)
        
        if not user_id or not code or not name:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
        db = get_db_connection()
        if not db:
            return jsonify({'success': False, 'message': '数据库服务暂不可用'}), 503
        
        holding_id = f"hold_{int(time.time() * 1000)}"
        
        with db.cursor() as cursor:
            # 检查是否已存在（软删除的也算）
            cursor.execute("""
                SELECT id, is_deleted FROM user_holdings 
                WHERE user_id = %s AND fund_code = %s
            """, (user_id, code))
            
            existing = cursor.fetchone()
            
            if existing:
                if existing['is_deleted'] == 0:
                    return jsonify({'success': False, 'message': '该持仓已存在'}), 400
                else:
                    # 恢复已删除的持仓
                    cursor.execute("""
                        UPDATE user_holdings 
                        SET is_deleted = 0, shares = %s, cost_price = %s,
                            account_id = %s, watch_only = %s, fund_name = %s,
                            fund_type = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (shares, cost, account_id, 1 if watch_only else 0, name, fund_type, existing['id']))
                    
                    return jsonify({
                        'success': True,
                        'message': '持仓已恢复',
                        'data': {'id': existing['id']}
                    })
            else:
                # 新建持仓
                cursor.execute("""
                    INSERT INTO user_holdings 
                    (id, user_id, fund_code, fund_name, fund_type, shares, cost_price, account_id, watch_only)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (holding_id, user_id, code, name, fund_type, shares, cost, account_id, 1 if watch_only else 0))
                
                logger.info(f"添加持仓: {user_id} -> {code}")
                
                return jsonify({
                    'success': True,
                    'message': '添加成功',
                    'data': {'id': holding_id}
                })
                
    except Exception as e:
        logger.error(f"添加持仓失败: {e}")
        return jsonify({'success': False, 'message': '添加持仓失败'}), 500

@holdings_bp.route('/<holding_id>', methods=['DELETE', 'OPTIONS'])
def delete_holding(holding_id):
    """删除持仓（软删除）"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        user_id = request.args.get('userId')
        if not user_id:
            return jsonify({'success': False, 'message': '缺少 userId 参数'}), 400
        
        db = get_db_connection()
        if not db:
            return jsonify({'success': False, 'message': '数据库服务暂不可用'}), 503
        
        with db.cursor() as cursor:
            # 软删除
            cursor.execute("""
                UPDATE user_holdings 
                SET is_deleted = 1, updated_at = NOW()
                WHERE id = %s AND user_id = %s AND is_deleted = 0
            """, (holding_id, user_id))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': '持仓不存在或无权限'}), 404
            
            logger.info(f"删除持仓: {holding_id}")
            
            return jsonify({
                'success': True,
                'message': '删除成功'
            })
            
    except Exception as e:
        logger.error(f"删除持仓失败: {e}")
        return jsonify({'success': False, 'message': '删除持仓失败'}), 500

@holdings_bp.route('/<holding_id>', methods=['PUT', 'OPTIONS'])
def update_holding(holding_id):
    """更新持仓"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        data = request.get_json() or {}
        user_id = data.get('userId')
        
        if not user_id:
            return jsonify({'success': False, 'message': '缺少 userId 参数'}), 400
        
        # 可更新的字段
        updates = {}
        if 'shares' in data:
            updates['shares'] = data['shares']
        if 'cost' in data:
            updates['cost_price'] = data['cost']
        if 'accountId' in data:
            updates['account_id'] = data['accountId']
        if 'watchOnly' in data:
            updates['watch_only'] = 1 if data['watchOnly'] else 0
        
        if not updates:
            return jsonify({'success': False, 'message': '没有需要更新的字段'}), 400
        
        db = get_db_connection()
        if not db:
            return jsonify({'success': False, 'message': '数据库服务暂不可用'}), 503
        
        # 构建 SQL
        fields = []
        values = []
        for key, value in updates.items():
            fields.append(f"{key} = %s")
            values.append(value)
        values.append(holding_id)
        values.append(user_id)
        
        with db.cursor() as cursor:
            cursor.execute(f"""
                UPDATE user_holdings 
                SET {', '.join(fields)}, updated_at = NOW()
                WHERE id = %s AND user_id = %s AND is_deleted = 0
            """, tuple(values))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': '持仓不存在或无权限'}), 404
            
            logger.info(f"更新持仓: {holding_id}")
            
            return jsonify({
                'success': True,
                'message': '更新成功'
            })
            
    except Exception as e:
        logger.error(f"更新持仓失败: {e}")
        return jsonify({'success': False, 'message': '更新持仓失败'}), 500

@holdings_bp.route('/batch', methods=['POST', 'OPTIONS'])
def batch_add_holdings():
    """批量添加持仓"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        data = request.get_json() or {}
        user_id = data.get('userId')
        holdings = data.get('holdings', [])
        
        if not user_id:
            return jsonify({'success': False, 'message': '缺少 userId 参数'}), 400
        
        if not holdings or len(holdings) > 50:
            return jsonify({'success': False, 'message': '持仓数量必须在 1-50 之间'}), 400
        
        db = get_db_connection()
        if not db:
            return jsonify({'success': False, 'message': '数据库服务暂不可用'}), 503
        
        success_count = 0
        failed_items = []
        
        with db.cursor() as cursor:
            for item in holdings:
                try:
                    code = item.get('code')
                    name = item.get('name')
                    if not code or not name:
                        failed_items.append({'code': code, 'reason': '缺少 code 或 name'})
                        continue
                    
                    fund_type = item.get('type', 'equity')
                    shares = item.get('shares', 0)
                    cost = item.get('cost', 0)
                    account_id = item.get('accountId', 'alipay')
                    watch_only = item.get('watchOnly', False)
                    
                    holding_id = f"hold_{int(time.time() * 1000)}_{success_count}"
                    
                    cursor.execute("""
                        INSERT INTO user_holdings 
                        (id, user_id, fund_code, fund_name, fund_type, shares, cost_price, account_id, watch_only)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        is_deleted = 0, shares = VALUES(shares), cost_price = VALUES(cost_price),
                        account_id = VALUES(account_id), watch_only = VALUES(watch_only),
                        fund_name = VALUES(fund_name), fund_type = VALUES(fund_type),
                        updated_at = NOW()
                    """, (holding_id, user_id, code, name, fund_type, shares, cost, account_id, 1 if watch_only else 0))
                    
                    success_count += 1
                    
                except Exception as e:
                    failed_items.append({'code': item.get('code'), 'reason': str(e)})
        
        logger.info(f"批量添加持仓: {user_id} 成功 {success_count}/{len(holdings)}")
        
        return jsonify({
            'success': True,
            'message': f'成功添加 {success_count} 个持仓',
            'data': {
                'total': len(holdings),
                'success': success_count,
                'failed': len(failed_items),
                'failedItems': failed_items if failed_items else None
            }
        })
        
    except Exception as e:
        logger.error(f"批量添加持仓失败: {e}")
        return jsonify({'success': False, 'message': '批量添加持仓失败'}), 500
