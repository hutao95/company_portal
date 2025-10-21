from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# 角色常量定义（与 auth.py 保持一致）
ROLE_SUPER_ADMIN = 'super_admin'
ROLE_ADMIN = 'admin'
ROLE_USER = 'user'
ROLE_PENDING = 'pending'

# 用户角色关联表
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.Column(db.Text)  # 使用Text类型存储权限列表
    level = db.Column(db.Integer, default=0)  # 角色层级，数字越小权限越高
    
    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(100), nullable=False, default='通用')
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=False)  # 改为默认未激活
    status = db.Column(db.String(20), default='pending')  # 新增：用户状态 pending/active/inactive
    real_name = db.Column(db.String(100))  # 新增：真实姓名
    phone = db.Column(db.String(20))  # 新增：电话号码
    last_login = db.Column(db.DateTime)  # 新增：最后登录时间
    
    # 多对多关系：用户-角色
    roles = db.relationship('Role', secondary=user_roles, backref=db.backref('users', lazy='dynamic'))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role_name):
        """检查用户是否拥有指定角色"""
        return any(role.name == role_name for role in self.roles)
    
    def has_permission(self, permission):
        """检查用户是否拥有指定权限"""
        # 超级管理员自动拥有所有权限
        if self.has_role(ROLE_SUPER_ADMIN):
            return True 
        for role in self.roles:
            if role.permissions and permission in role.permissions.split(','):
                return True
        return False
    
    @property
    def is_approved(self):
        """检查用户是否已审核通过"""
        return self.status == 'active' and self.is_active
    
    def approve(self):
        """审核通过用户"""
        self.status = 'active'
        self.is_active = True
    
    def reject(self):
        """拒绝用户"""
        self.status = 'inactive'
        self.is_active = False
    
    def __repr__(self):
        return f'<User {self.username}>'

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    publisher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    publish_time = db.Column(db.DateTime, default=datetime.utcnow)
    is_top = db.Column(db.Boolean, default=False)
    department = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    
    # 添加与发布者的关系
    publisher = db.relationship('User', backref='published_notifications', foreign_keys=[publisher_id])
    
    def __repr__(self):
        return f'<Notification {self.title}>'

class SupplyCategory(db.Model):
    __tablename__ = 'supply_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    def __repr__(self):
        return f'<SupplyCategory {self.name}>'

class Supply(db.Model):
    __tablename__ = 'supplies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('supply_categories.id'))
    total_stock = db.Column(db.Integer, default=0)
    current_stock = db.Column(db.Integer, default=0)
    unit = db.Column(db.String(50), default='个')
    min_stock_threshold = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_available = db.Column(db.Boolean, default=True)
    
    # 添加与分类的关系
    category = db.relationship('SupplyCategory', backref='supplies')
    
    @property
    def is_low_stock(self):
        """检查是否库存不足"""
        return self.current_stock <= self.min_stock_threshold
    
    def add_stock(self, quantity):
        """增加库存"""
        self.current_stock += quantity
        self.total_stock += quantity
    
    def __repr__(self):
        return f'<Supply {self.name}>'

class SupplyRequest(db.Model):
    __tablename__ = 'supply_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    supply_id = db.Column(db.Integer, db.ForeignKey('supplies.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')
    apply_time = db.Column(db.DateTime, default=datetime.utcnow)
    approve_time = db.Column(db.DateTime)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reject_reason = db.Column(db.Text)
    issue_time = db.Column(db.DateTime)
    issuer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # 添加关系
    applicant = db.relationship('User', foreign_keys=[applicant_id], backref='supply_requests')
    supply = db.relationship('Supply', backref='requests')
    approver = db.relationship('User', foreign_keys=[approver_id])
    issuer = db.relationship('User', foreign_keys=[issuer_id])
    
    @property
    def can_approve(self):
        """检查申请是否可以被审批（待审批状态）"""
        return self.status == 'pending'
    
    @property
    def can_issue(self):
        """检查申请是否可以被发放（已批准状态）"""
        return self.status == 'approved'
    
    def __repr__(self):
        return f'<SupplyRequest {self.id}>'

# ============ 新增模型：人员信息和知识库 ============

class Employee(db.Model):
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    hire_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='在职')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Employee {self.name} ({self.employee_id})>'

class EmployeeFile(db.Model):
    __tablename__ = 'employee_files'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)
    
    # 关系
    employee = db.relationship('Employee', backref='files')
    uploader = db.relationship('User', backref='uploaded_files')
    
    def __repr__(self):
        return f'<EmployeeFile {self.file_name}>'

class KnowledgeCategory(db.Model):
    __tablename__ = 'knowledge_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('knowledge_categories.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 自引用关系
    parent = db.relationship('KnowledgeCategory', remote_side=[id], backref='subcategories')
    
    def __repr__(self):
        return f'<KnowledgeCategory {self.name}>'

class KnowledgeArticle(db.Model):
    __tablename__ = 'knowledge_articles'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('knowledge_categories.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    publish_time = db.Column(db.DateTime, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=True)
    view_count = db.Column(db.Integer, default=0)
    tags = db.Column(db.String(255))
    
    # 关系
    category = db.relationship('KnowledgeCategory', backref='articles')
    author = db.relationship('User', backref='knowledge_articles')
    
    def __repr__(self):
        return f'<KnowledgeArticle {self.title}>'
    
class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 消息相关字段
    message_type = db.Column(db.String(20), default='system') # 保持原字段，用于细分类别
    is_read = db.Column(db.Boolean, default=False)
    related_url = db.Column(db.String(500), nullable=True)
    
    # --- 新增字段开始 ---
    # 用于区分是个人消息还是系统通知。'personal'为个人消息，'notification'为系统通知
    category = db.Column(db.String(20), default='personal')
    # 用于部门筛选。NULL表示全公司，其他值则表示针对特定部门
    target_department = db.Column(db.String(100), nullable=True)
    # --- 新增字段结束 ---
    
    # 发送者关系
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    
    # 接收者关系  
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')

    def __init__(self, **kwargs):
        # 确保 sender_id 不为空
        if 'sender_id' not in kwargs:
            raise ValueError("sender_id is required for Message")
        super().__init__(**kwargs)
    
    def __repr__(self):
        return f'<Message {self.title}>'