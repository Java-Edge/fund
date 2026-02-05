"""
认证管理 API
提供用户申请、登录、审核等功能，数据存储在 Redis
"""
from flask import Blueprint, request, jsonify
import json
import time
from datetime import datetime
from typing import Optional

from loguru import logger

# 创建蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# 从环境变量读取 Redis 配置，与 fund.py 保持一致
def get_redis_config():
    """获取 Redis 配置"""
    import os
    return {
        'host': os.getenv('REDIS_HOST', 'localhost'),
        'port': int(os.getenv('REDIS_PORT', '6379')),
        'db': int(os.getenv('REDIS_DB', '0')),
        'password': os.getenv('REDIS_PASSWORD') or None,
        'decode_responses': True,
        'socket_connect_timeout': 3,
        'socket_timeout': 3
    }

# 全局 Redis 连接
_redis_client = None

def get_redis():
    """获取 Redis 连接"""
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.Redis(**get_redis_config())
            _redis_client.ping()
            logger.info("Auth Redis connected successfully")
        except Exception as e:
            logger.error(f"Auth Redis 连接失败: {e}")
            return None
    return _redis_client

def get_user_key(social_type: str, social_id: str) -> str:
    """获取用户 Redis key"""
    return f"user:{social_type}:{social_id}"

def get_all_users():
    """获取所有用户"""
    r = get_redis()
    if not r:
        return []
    
    users = []
    try:
        for key in r.scan_iter(match="user:*"):
            user_data = r.get(key)
            if user_data:
                users.append(json.loads(user_data))
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
    return users

def init_default_admin():
    """初始化默认管理员"""
    r = get_redis()
    if not r:
        logger.warning("Redis 不可用，跳过创建默认管理员")
        return
    
    # 默认管理员配置（从环境变量读取，提供默认值）
    import os
    admin_social_id = os.getenv('ADMIN_SOCIAL_ID', 'admin')
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin')
    
    admin_key = f"user:wechat:{admin_social_id}"
    
    try:
        if not r.exists(admin_key):
            admin_user = {
                'id': 'admin_001',
                'socialType': 'wechat',
                'socialId': admin_social_id,
                'nickname': '系统管理员',
                'password': admin_password,
                'status': 'approved',
                'isAdmin': True,
                'appliedAt': datetime.now().isoformat(),
                'lastLoginAt': None
            }
            r.set(admin_key, json.dumps(admin_user))
            logger.info(f"默认管理员已创建: {admin_social_id}")
        else:
            logger.debug("默认管理员已存在")
    except Exception as e:
        logger.error(f"创建默认管理员失败: {e}")

# ============ API 路由 ============

@auth_bp.route('/apply', methods=['POST', 'OPTIONS'])
def submit_application():
    """提交申请"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
        data = request.get_json() or {}
        social_type = data.get('socialType')
        social_id = data.get('socialId')
        password = data.get('password', '')
        nickname = data.get('nickname', '未命名')
        apply_reason = data.get('applyReason', '')
        
        if not social_type or not social_id:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
        r = get_redis()
        if not r:
            return jsonify({'success': False, 'message': '服务暂不可用'}), 503
        
        # 检查是否已存在
        user_key = get_user_key(social_type, social_id)
        if r.exists(user_key):
            user_data = json.loads(r.get(user_key))
            if user_data['status'] == 'approved':
                return jsonify({'success': False, 'message': '该账号已通过审核，请直接登录'})
            return jsonify({'success': False, 'message': '该账号已提交申请，请等待审核'})
        
        # 创建新用户
        new_user = {
            'id': f"user_{int(time.time() * 1000)}",
            'socialType': social_type,
            'socialId': social_id,
            'nickname': nickname,
            'password': password if password else None,
            'applyReason': apply_reason,
            'status': 'pending',
            'isAdmin': False,
            'appliedAt': datetime.now().isoformat(),
            'lastLoginAt': None
        }
        
        r.set(user_key, json.dumps(new_user))
        logger.info(f"新用户申请: {social_type}:{social_id}")
        
        return jsonify({
            'success': True,
            'message': '申请已提交，请等待管理员审核',
            'data': {'userId': new_user['id'], 'status': 'pending'}
        })
        
    except Exception as e:
        logger.error(f"提交申请失败: {e}")
        return jsonify({'success': False, 'message': '提交申请失败'}), 500

@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
def login():
    """登录"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
        data = request.get_json() or {}
        social_type = data.get('socialType')
        social_id = data.get('socialId')
        password = data.get('password', '')
        
        if not social_type or not social_id:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
        r = get_redis()
        if not r:
            return jsonify({'success': False, 'message': '服务暂不可用'}), 503
        
        # 查找用户
        user_key = get_user_key(social_type, social_id)
        user_data = r.get(user_key)
        
        if not user_data:
            return jsonify({'success': False, 'message': '账号不存在，请先提交申请'})
        
        user = json.loads(user_data)
        
        # 检查状态
        if user['status'] == 'pending':
            return jsonify({'success': False, 'message': '申请正在审核中，请耐心等待'})
        
        if user['status'] == 'rejected':
            return jsonify({'success': False, 'message': '申请已被拒绝'})
        
        if user['status'] == 'banned':
            return jsonify({'success': False, 'message': '账号已被禁用'})
        
        # 验证密码
        if user.get('password') and user['password'] != password:
            return jsonify({'success': False, 'message': '密码错误'})
        
        # 更新最后登录时间
        user['lastLoginAt'] = datetime.now().isoformat()
        r.set(user_key, json.dumps(user))
        
        logger.info(f"用户登录: {social_type}:{social_id}")
        
        # 返回用户信息（不包含密码）
        return jsonify({
            'success': True,
            'message': '登录成功',
            'data': {
                'userId': user['id'],
                'socialId': user['socialId'],
                'socialType': user['socialType'],
                'nickname': user['nickname'],
                'status': user['status'],
                'isAdmin': user.get('isAdmin', False)
            }
        })
        
    except Exception as e:
        logger.error(f"登录失败: {e}")
        return jsonify({'success': False, 'message': '登录失败'}), 500

@auth_bp.route('/status', methods=['GET', 'OPTIONS'])
def check_status():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    """检查申请状态"""
    try:
        social_type = request.args.get('socialType')
        social_id = request.args.get('socialId')
        
        if not social_type or not social_id:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
        r = get_redis()
        if not r:
            return jsonify({'success': False, 'message': '服务暂不可用'}), 503
        
        user_key = get_user_key(social_type, social_id)
        user_data = r.get(user_key)
        
        if not user_data:
            return jsonify({
                'success': True,
                'data': {'exists': False, 'status': None, 'message': '未找到申请记录'}
            })
        
        user = json.loads(user_data)
        
        return jsonify({
            'success': True,
            'data': {
                'exists': True,
                'status': user['status'],
                'message': {
                    'pending': '申请正在审核中',
                    'approved': '申请已通过',
                    'rejected': '申请已被拒绝',
                    'banned': '账号已被禁用'
                }.get(user['status'], '未知状态')
            }
        })
        
    except Exception as e:
        logger.error(f"检查状态失败: {e}")
        return jsonify({'success': False, 'message': '检查状态失败'}), 500

@auth_bp.route('/applications', methods=['GET', 'OPTIONS'])
def get_applications():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    """获取所有申请列表（管理员用）"""
    try:
        r = get_redis()
        if not r:
            return jsonify({'success': False, 'message': '服务暂不可用'}), 503
        
        # 获取所有用户
        users = get_all_users()
        
        # 转换为申请列表格式
        applications = []
        for user in users:
            applications.append({
                'id': user['id'],
                'socialType': user['socialType'],
                'socialId': user['socialId'],
                'nickname': user['nickname'],
                'applyReason': user.get('applyReason', ''),
                'status': user['status'],
                'appliedAt': user['appliedAt'],
                'reviewedAt': user.get('reviewedAt'),
                'reviewerNote': user.get('reviewerNote', ''),
                'isAdmin': user.get('isAdmin', False)
            })
        
        # 按申请时间排序
        applications.sort(key=lambda x: x['appliedAt'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': applications
        })
        
    except Exception as e:
        logger.error(f"获取申请列表失败: {e}")
        return jsonify({'success': False, 'message': '获取申请列表失败'}), 500

@auth_bp.route('/review', methods=['POST', 'OPTIONS'])
def review_application():
    """审核申请（管理员用）"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    try:
        data = request.get_json() or {}
        user_id = data.get('userId')
        action = data.get('action')  # 'approve' 或 'reject'
        note = data.get('note', '')
        
        if not user_id or not action:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
        r = get_redis()
        if not r:
            return jsonify({'success': False, 'message': '服务暂不可用'}), 503
        
        # 查找用户
        users = get_all_users()
        target_user = None
        target_key = None
        
        for user in users:
            if user['id'] == user_id:
                target_user = user
                target_key = get_user_key(user['socialType'], user['socialId'])
                break
        
        if not target_user:
            return jsonify({'success': False, 'message': '用户不存在'}), 404
        
        # 更新状态
        if action == 'approve':
            target_user['status'] = 'approved'
        elif action == 'reject':
            target_user['status'] = 'rejected'
        else:
            return jsonify({'success': False, 'message': '无效的操作'}), 400
        
        target_user['reviewedAt'] = datetime.now().isoformat()
        target_user['reviewerNote'] = note
        
        r.set(target_key, json.dumps(target_user))
        
        logger.info(f"审核用户: {target_user['socialId']} -> {action}")
        
        return jsonify({
            'success': True,
            'message': '审核完成',
            'data': {
                'userId': target_user['id'],
                'status': target_user['status']
            }
        })
        
    except Exception as e:
        logger.error(f"审核失败: {e}")
        return jsonify({'success': False, 'message': '审核失败'}), 500

@auth_bp.route('/stats', methods=['GET', 'OPTIONS'])
def get_stats():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    """获取统计信息"""
    try:
        r = get_redis()
        if not r:
            return jsonify({'success': False, 'message': '服务暂不可用'}), 503
        
        users = get_all_users()
        
        pending = sum(1 for u in users if u['status'] == 'pending')
        approved = sum(1 for u in users if u['status'] == 'approved')
        rejected = sum(1 for u in users if u['status'] == 'rejected')
        banned = sum(1 for u in users if u['status'] == 'banned')
        total = len(users)
        
        return jsonify({
            'success': True,
            'data': {
                'totalApplications': total,
                'pendingApplications': pending,
                'approvedApplications': approved,
                'rejectedApplications': rejected,
                'bannedApplications': banned
            }
        })
        
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        return jsonify({'success': False, 'message': '获取统计失败'}), 500
