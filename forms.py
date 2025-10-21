from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, SelectField, TextAreaField, BooleanField, SelectMultipleField, widgets
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Email, ValidationError
from simple_models import User

class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(message='请输入用户名')])
    password = PasswordField('密码', validators=[
        DataRequired(message='请输入密码'),
        Length(min=6, message='密码长度至少6位')
    ])
    submit = SubmitField('登录')

class RegisterForm(FlaskForm):
    username = StringField('用户名', validators=[
        DataRequired(message='请输入用户名'),
        Length(min=3, max=80, message='用户名长度3-80位')
    ])
    password = PasswordField('密码', validators=[
        DataRequired(message='请输入密码'),
        Length(min=6, message='密码长度至少6位')
    ])
    confirm_password = PasswordField('确认密码', validators=[
        DataRequired(message='请确认密码')
    ])
    real_name = StringField('真实姓名', validators=[DataRequired(message='请输入真实姓名')])
    email = StringField('邮箱', validators=[DataRequired(message='请输入邮箱'), Email()])
    phone = StringField('手机号', validators=[Optional()])
    department = SelectField('部门', choices=[
        ('技术部', '技术部'),
        ('人事部', '人事部'),
        ('财务部', '财务部'),
        ('行政部', '行政部'),
        ('市场部', '市场部')
    ], validators=[DataRequired()])
    submit = SubmitField('注册')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('该用户名已被使用，请选择其他用户名')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('该邮箱已被注册')

class UserEditForm(FlaskForm):
    username = StringField('用户名', validators=[
        DataRequired(message='请输入用户名'),
        Length(min=3, max=80, message='用户名长度3-80位')
    ])
    real_name = StringField('真实姓名', validators=[DataRequired(message='请输入真实姓名')])
    email = StringField('邮箱', validators=[DataRequired(message='请输入邮箱'), Email()])
    phone = StringField('手机号', validators=[Optional()])
    department = SelectField('部门', choices=[
        ('技术部', '技术部'),
        ('人事部', '人事部'),
        ('财务部', '财务部'),
        ('行政部', '行政部'),
        ('市场部', '市场部')
    ], validators=[DataRequired()])
    status = SelectField('状态', choices=[
        ('pending', '待审核'),
        ('active', '已激活'),
        ('inactive', '已停用')
    ], validators=[DataRequired()])
    submit = SubmitField('保存')

class UserRoleForm(FlaskForm):
    roles = SelectMultipleField('角色', choices=[], coerce=int, 
                               option_widget=widgets.CheckboxInput(),
                               widget=widgets.ListWidget(prefix_label=False))
    submit = SubmitField('分配角色')

class ResetPasswordForm(FlaskForm):
    new_password = PasswordField('新密码', validators=[
        DataRequired(message='请输入新密码'),
        Length(min=6, message='密码长度至少6位')
    ])
    confirm_password = PasswordField('确认密码', validators=[
        DataRequired(message='请确认密码')
    ])
    submit = SubmitField('重置密码')

    def validate_confirm_password(self, confirm_password):
        if self.new_password.data != confirm_password.data:
            raise ValidationError('两次输入的密码不一致')

class SupplyRequestForm(FlaskForm):
    supply_id = SelectField('选择耗材', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('数量', validators=[
        DataRequired(message='请输入数量'),
        NumberRange(min=1, message='数量必须大于0')
    ])
    submit = SubmitField('提交申请')

class ApproveRequestForm(FlaskForm):
    action = SelectField('操作', choices=[
        ('approve', '批准'),
        ('reject', '拒绝')
    ], validators=[DataRequired()])
    reject_reason = TextAreaField('拒绝原因', validators=[Optional()])
    submit = SubmitField('确认')

class SupplyForm(FlaskForm):
    name = StringField('耗材名称', validators=[DataRequired()])
    category_id = SelectField('分类', coerce=int, validators=[DataRequired()])
    total_stock = IntegerField('总库存', validators=[DataRequired()])
    current_stock = IntegerField('当前库存', validators=[DataRequired()])
    unit = StringField('单位', validators=[DataRequired()])
    min_stock_threshold = IntegerField('最低库存阈值', validators=[DataRequired()])
    description = TextAreaField('描述', validators=[Optional()])
    submit = SubmitField('保存')

class NotificationForm(FlaskForm):
    title = StringField('通知标题', validators=[DataRequired(message='请输入通知标题')])
    content = TextAreaField('通知内容', validators=[DataRequired(message='请输入通知内容')])
    department = SelectField('可见部门', choices=[
        ('', '全公司'),
        ('技术部', '技术部'),
        ('人事部', '人事部'),
        ('财务部', '财务部'),
        ('行政部', '行政部')
    ], validators=[Optional()])
    is_top = BooleanField('置顶通知')
    submit = SubmitField('发布通知')

class SupplyCategoryForm(FlaskForm):
    name = StringField('分类名称', validators=[DataRequired(message='请输入分类名称')])
    description = TextAreaField('分类描述', validators=[Optional()])
    submit = SubmitField('保存')

class SupplyInboundForm(FlaskForm):
    supply_id = SelectField('选择耗材', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('入库数量', validators=[
        DataRequired(message='请输入数量'),
        NumberRange(min=1, message='数量必须大于0')
    ])
    submit = SubmitField('确认入库')

class EmployeeForm(FlaskForm):
    employee_id = StringField('工号', validators=[DataRequired(message='请输入工号')])
    name = StringField('姓名', validators=[DataRequired(message='请输入姓名')])
    department = SelectField('部门', choices=[
        ('技术部', '技术部'),
        ('人事部', '人事部'),
        ('财务部', '财务部'),
        ('行政部', '行政部'),
        ('市场部', '市场部')
    ], validators=[DataRequired()])
    position = StringField('职位', validators=[DataRequired(message='请输入职位')])
    email = StringField('邮箱', validators=[Optional()])
    phone = StringField('电话', validators=[Optional()])
    hire_date = StringField('入职日期', validators=[DataRequired(message='请输入入职日期')])
    status = SelectField('状态', choices=[
        ('在职', '在职'),
        ('离职', '离职'),
        ('休假', '休假'),
        ('调岗', '调岗')
    ], validators=[DataRequired()])
    submit = SubmitField('保存')

class EmployeeSearchForm(FlaskForm):
    keyword = StringField('关键词', validators=[Optional()])
    department = SelectField('部门', choices=[
        ('', '所有部门'),
        ('技术部', '技术部'),
        ('人事部', '人事部'),
        ('财务部', '财务部'),
        ('行政部', '行政部'),
        ('市场部', '市场部')
    ], validators=[Optional()])
    submit = SubmitField('搜索')

class KnowledgeCategoryForm(FlaskForm):
    name = StringField('分类名称', validators=[DataRequired(message='请输入分类名称')])
    description = TextAreaField('分类描述', validators=[Optional()])
    parent_id = SelectField('父级分类', coerce=int, validators=[Optional()])
    submit = SubmitField('保存')

class KnowledgeArticleForm(FlaskForm):
    title = StringField('文章标题', validators=[DataRequired(message='请输入文章标题')])
    content = TextAreaField('文章内容', validators=[DataRequired(message='请输入文章内容')])
    category_id = SelectField('文章分类', coerce=int, validators=[DataRequired()])
    tags = StringField('标签', validators=[Optional()])
    is_published = BooleanField('立即发布')
    submit = SubmitField('发布文章')

class MessageForm(FlaskForm):
    title = StringField('消息标题', validators=[DataRequired(message='请输入消息标题')])
    content = TextAreaField('消息内容', validators=[DataRequired(message='请输入消息内容')])
    recipient_id = SelectField('接收人', coerce=int, validators=[DataRequired()])
    message_type = SelectField('消息类型', choices=[
        ('system', '系统消息'),
        ('approval', '审批通知'),
        ('department', '部门通知'),
        ('reminder', '提醒通知')
    ], validators=[DataRequired()])
    submit = SubmitField('发送消息')

class RolePermissionsForm(FlaskForm):
    permissions = SelectMultipleField('权限', 
                                    choices=[], 
                                    coerce=str,
                                    option_widget=widgets.CheckboxInput(),
                                    widget=widgets.ListWidget(prefix_label=False))
    submit = SubmitField('保存权限')
    
    def __init__(self, *args, **kwargs):
        super(RolePermissionsForm, self).__init__(*args, **kwargs)
        # 在初始化时设置权限选项
        self.set_permission_choices()
    
    def set_permission_choices(self, permission_modules=None, get_permission_description=None):
        """动态设置权限选项"""
        # 如果没有传入参数，使用默认值
        if permission_modules is None:
            from auth import PERMISSION_MODULES
            permission_modules = PERMISSION_MODULES
        
        if get_permission_description is None:
            from auth import get_permission_description
        
        choices = []
        
        for module, perms in permission_modules.items():
            # 添加模块标题作为分隔符
            choices.append(('---separator---', f"--- {module} ---"))
            # 添加该模块下的权限
            for perm in perms:
                desc = get_permission_description(perm)
                choices.append((perm, f"{desc}"))
        
        self.permissions.choices = choices