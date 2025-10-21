from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录', 'error')
                return redirect(url_for('login'))
            
            if not current_user.has_permission(permission):
                flash('您没有权限访问此页面', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def role_required(role_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('请先登录', 'error')
                return redirect(url_for('login'))
            
            if not current_user.has_role(role_name):
                flash('您没有权限访问此页面', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 权限常量
PERMISSION_VIEW_SUPPLIES = 'view_supplies'
PERMISSION_REQUEST_SUPPLIES = 'request_supplies'
PERMISSION_APPROVE_REQUESTS = 'approve_requests'
PERMISSION_ISSUE_SUPPLIES = 'issue_supplies'
PERMISSION_MANAGE_SUPPLIES = 'manage_supplies'
PERMISSION_MANAGE_USERS = 'manage_users'
PERMISSION_PUBLISH_NOTICES = 'publish_notices'
PERMISSION_VIEW_EMPLOYEES = 'view_employees'
PERMISSION_MANAGE_EMPLOYEES = 'manage_employees'
PERMISSION_VIEW_ARCHIVES = 'view_archives'
PERMISSION_MANAGE_ARCHIVES = 'manage_archives'
PERMISSION_VIEW_KNOWLEDGE = 'view_knowledge'
PERMISSION_MANAGE_KNOWLEDGE = 'manage_knowledge'

# 新增用户管理权限
PERMISSION_APPROVE_USERS = 'approve_users'
PERMISSION_RESET_PASSWORDS = 'reset_passwords'
PERMISSION_MANAGE_ROLES = 'manage_roles'

# 新增消息管理权限
PERMISSION_VIEW_MESSAGES = 'view_messages'
PERMISSION_SEND_MESSAGES = 'send_messages'

# 角色常量
ROLE_SUPER_ADMIN = 'super_admin'
ROLE_ADMIN = 'admin'
ROLE_USER = 'user'
ROLE_PENDING = 'pending'

# 角色权限映射（用于数据库初始化）
ROLE_PERMISSIONS = {
    ROLE_SUPER_ADMIN: [
        PERMISSION_VIEW_SUPPLIES,
        PERMISSION_REQUEST_SUPPLIES,
        PERMISSION_APPROVE_REQUESTS,
        PERMISSION_ISSUE_SUPPLIES,
        PERMISSION_MANAGE_SUPPLIES,
        PERMISSION_MANAGE_USERS,
        PERMISSION_PUBLISH_NOTICES,
        PERMISSION_VIEW_EMPLOYEES,
        PERMISSION_MANAGE_EMPLOYEES,
        PERMISSION_VIEW_ARCHIVES,
        PERMISSION_MANAGE_ARCHIVES,
        PERMISSION_VIEW_KNOWLEDGE,
        PERMISSION_MANAGE_KNOWLEDGE,
        PERMISSION_APPROVE_USERS,
        PERMISSION_RESET_PASSWORDS,
        PERMISSION_MANAGE_ROLES,
        PERMISSION_VIEW_MESSAGES,
        PERMISSION_SEND_MESSAGES
    ],
    ROLE_ADMIN: [
        PERMISSION_VIEW_SUPPLIES,
        PERMISSION_REQUEST_SUPPLIES,
        PERMISSION_APPROVE_REQUESTS,
        PERMISSION_ISSUE_SUPPLIES,
        PERMISSION_MANAGE_SUPPLIES,
        PERMISSION_MANAGE_USERS,
        PERMISSION_PUBLISH_NOTICES,
        PERMISSION_VIEW_EMPLOYEES,
        PERMISSION_VIEW_ARCHIVES,
        PERMISSION_VIEW_KNOWLEDGE,
        PERMISSION_MANAGE_KNOWLEDGE,
        PERMISSION_APPROVE_USERS,
        PERMISSION_RESET_PASSWORDS,
        PERMISSION_VIEW_MESSAGES,
        PERMISSION_SEND_MESSAGES
    ],
    ROLE_USER: [
        PERMISSION_VIEW_SUPPLIES,
        PERMISSION_REQUEST_SUPPLIES,
        PERMISSION_VIEW_EMPLOYEES,
        PERMISSION_VIEW_ARCHIVES,
        PERMISSION_VIEW_KNOWLEDGE,
        PERMISSION_VIEW_MESSAGES  # 普通用户可以查看自己的消息
    ],
    ROLE_PENDING: [
        # 待审核用户没有任何权限
    ]
}

# 权限描述映射
PERMISSION_DESCRIPTIONS = {
    PERMISSION_VIEW_SUPPLIES: '查看耗材库存',
    PERMISSION_REQUEST_SUPPLIES: '申请耗材',
    PERMISSION_APPROVE_REQUESTS: '审批耗材申请',
    PERMISSION_ISSUE_SUPPLIES: '发放耗材',
    PERMISSION_MANAGE_SUPPLIES: '管理耗材分类和库存',
    PERMISSION_MANAGE_USERS: '管理用户账户',
    PERMISSION_PUBLISH_NOTICES: '发布通知公告',
    PERMISSION_VIEW_EMPLOYEES: '查看员工信息',
    PERMISSION_MANAGE_EMPLOYEES: '管理员工档案',
    PERMISSION_VIEW_ARCHIVES: '查看档案统计',
    PERMISSION_MANAGE_ARCHIVES: '管理档案文件',
    PERMISSION_VIEW_KNOWLEDGE: '查看知识库',
    PERMISSION_MANAGE_KNOWLEDGE: '管理知识库内容',
    PERMISSION_APPROVE_USERS: '审核用户注册',
    PERMISSION_RESET_PASSWORDS: '重置用户密码',
    PERMISSION_MANAGE_ROLES: '管理角色权限',
    PERMISSION_VIEW_MESSAGES: '查看消息',
    PERMISSION_SEND_MESSAGES: '发送消息'
}

# 角色描述
ROLE_DESCRIPTIONS = {
    ROLE_SUPER_ADMIN: '系统超级管理员 - 拥有所有权限',
    ROLE_ADMIN: '系统管理员 - 拥有大部分管理权限',
    ROLE_USER: '普通用户 - 基础使用权限',
    ROLE_PENDING: '待审核用户 - 无任何操作权限'
}

# 按模块分组的权限
PERMISSION_MODULES = {
    '用户管理': [
        PERMISSION_MANAGE_USERS,
        PERMISSION_APPROVE_USERS,
        PERMISSION_RESET_PASSWORDS,
        PERMISSION_MANAGE_ROLES
    ],
    '通知公告': [
        PERMISSION_PUBLISH_NOTICES
    ],
    '耗材管理': [
        PERMISSION_VIEW_SUPPLIES,
        PERMISSION_REQUEST_SUPPLIES,
        PERMISSION_APPROVE_REQUESTS,
        PERMISSION_ISSUE_SUPPLIES,
        PERMISSION_MANAGE_SUPPLIES
    ],
    '人员档案': [
        PERMISSION_VIEW_EMPLOYEES,
        PERMISSION_MANAGE_EMPLOYEES,
        PERMISSION_VIEW_ARCHIVES,
        PERMISSION_MANAGE_ARCHIVES
    ],
    '知识库': [
        PERMISSION_VIEW_KNOWLEDGE,
        PERMISSION_MANAGE_KNOWLEDGE
    ],
    '消息系统': [
        PERMISSION_VIEW_MESSAGES,
        PERMISSION_SEND_MESSAGES
    ]
}

def get_role_permissions(role_name):
    """获取指定角色的权限列表"""
    return ROLE_PERMISSIONS.get(role_name, [])

def has_any_permission(*permissions):
    """检查用户是否拥有任意一个指定权限"""
    if not current_user.is_authenticated:
        return False
    
    for permission in permissions:
        if current_user.has_permission(permission):
            return True
    
    return False

def has_all_permissions(*permissions):
    """检查用户是否拥有所有指定权限"""
    if not current_user.is_authenticated:
        return False
    
    for permission in permissions:
        if not current_user.has_permission(permission):
            return False
    
    return True

def get_permission_description(permission):
    """获取权限的中文描述"""
    return PERMISSION_DESCRIPTIONS.get(permission, permission)

def get_role_description(role_name):
    """获取角色的中文描述"""
    return ROLE_DESCRIPTIONS.get(role_name, role_name)

def get_permission_module(permission):
    """获取权限所属的模块"""
    for module, permissions in PERMISSION_MODULES.items():
        if permission in permissions:
            return module
    return '其他'

def get_all_permissions():
    """获取所有权限列表"""
    all_permissions = []
    for permissions in PERMISSION_MODULES.values():
        all_permissions.extend(permissions)
    return all_permissions

def get_role_permission_count(role_name):
    """获取角色的权限数量"""
    permissions = ROLE_PERMISSIONS.get(role_name, [])
    return len(permissions)

def get_user_permission_summary(user):
    """获取用户权限摘要"""
    if not user.is_authenticated:
        return "未登录用户"
    
    if not user.roles:
        return "无角色用户"
    
    # 获取用户的所有权限
    all_permissions = set()
    for role in user.roles:
        if role.permissions:
            permissions = role.permissions.split(',')
            all_permissions.update(permissions)
    
    # 按模块统计权限
    module_summary = {}
    for permission in all_permissions:
        module = get_permission_module(permission)
        if module not in module_summary:
            module_summary[module] = []
        module_summary[module].append(get_permission_description(permission))
    
    return module_summary

def check_permission_coverage():
    """检查权限覆盖情况，确保所有定义的权限都在角色中有分配"""
    all_defined_permissions = get_all_permissions()
    all_assigned_permissions = set()
    
    for role_name, permissions in ROLE_PERMISSIONS.items():
        all_assigned_permissions.update(permissions)
    
    unassigned_permissions = set(all_defined_permissions) - all_assigned_permissions
    return {
        'total_defined': len(all_defined_permissions),
        'total_assigned': len(all_assigned_permissions),
        'unassigned_permissions': list(unassigned_permissions)
    }

def update_role_permissions(role_name, new_permissions):
    """更新角色的权限列表"""
    if role_name not in ROLE_PERMISSIONS:
        return False
    
    # 验证权限是否都在定义的权限列表中
    all_permissions = get_all_permissions()
    valid_permissions = [p for p in new_permissions if p in all_permissions]
    
    ROLE_PERMISSIONS[role_name] = valid_permissions
    return True

def get_role_by_name(role_name):
    """根据角色名称获取角色信息"""
    role_info = {
        'name': role_name,
        'description': get_role_description(role_name),
        'permissions': ROLE_PERMISSIONS.get(role_name, []),
        'permission_count': len(ROLE_PERMISSIONS.get(role_name, []))
    }
    return role_info

def reset_role_permissions(role_name):
    """重置角色权限为默认值"""
    if role_name in ROLE_PERMISSIONS:
        # 重新从默认映射中获取权限
        default_permissions = ROLE_PERMISSIONS.get(role_name, [])
        ROLE_PERMISSIONS[role_name] = default_permissions.copy()
        return True
    return False

def can_view_all_notifications():
    """检查用户是否有权限查看所有通知"""
    if not current_user.is_authenticated:
        return False
    
    # 超级管理员可以查看所有通知
    if current_user.has_role(ROLE_SUPER_ADMIN):
        return True
    
    # 管理员可以查看所有通知（如果需要限制管理员，可以修改此条件）
    if current_user.has_role(ROLE_ADMIN):
        return True
    
    return False

def can_view_notification(notification):
    """检查用户是否有权限查看特定通知"""
    if not current_user.is_authenticated:
        return False
    
    # 超级管理员可以查看所有通知
    if current_user.has_role(ROLE_SUPER_ADMIN):
        return True
    
    # 管理员可以查看所有通知
    if current_user.has_role(ROLE_ADMIN):
        return True
    
    # 普通用户只能查看全公司通知或本部门通知
    if notification.department is None or notification.department == '全公司' or notification.department == current_user.department:
        return True
    
    return False

def can_edit_notification(notification):
    """检查用户是否有权限编辑通知"""
    if not current_user.is_authenticated:
        return False
    
    # 超级管理员可以编辑所有通知
    if current_user.has_role(ROLE_SUPER_ADMIN):
        return True
    
    # 管理员可以编辑所有通知
    if current_user.has_role(ROLE_ADMIN):
        return True
    
    # 普通用户只能编辑自己发布的通知
    return notification.publisher_id == current_user.id

def can_delete_notification(notification):
    """检查用户是否有权限删除通知"""
    if not current_user.is_authenticated:
        return False
    
    # 超级管理员可以删除所有通知
    if current_user.has_role(ROLE_SUPER_ADMIN):
        return True
    
    # 管理员可以删除所有通知
    if current_user.has_role(ROLE_ADMIN):
        return True
    
    # 普通用户只能删除自己发布的通知
    return notification.publisher_id == current_user.id