from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from simple_models import db, User, Role, Notification, Supply, SupplyCategory, SupplyRequest, Employee, EmployeeFile, KnowledgeCategory, KnowledgeArticle, Message
from forms import (
    LoginForm, SupplyRequestForm, ApproveRequestForm, SupplyForm, 
    NotificationForm, SupplyCategoryForm, SupplyInboundForm, 
    EmployeeForm, EmployeeSearchForm, KnowledgeCategoryForm, 
    KnowledgeArticleForm, RegisterForm, UserEditForm, UserRoleForm, 
    ResetPasswordForm, MessageForm, 
    # 新增导入
    RolePermissionsForm
)
from auth import (
    permission_required, role_required, 
    PERMISSION_VIEW_SUPPLIES, PERMISSION_REQUEST_SUPPLIES, PERMISSION_APPROVE_REQUESTS, 
    PERMISSION_ISSUE_SUPPLIES, PERMISSION_MANAGE_SUPPLIES, PERMISSION_MANAGE_USERS, 
    PERMISSION_PUBLISH_NOTICES, PERMISSION_VIEW_EMPLOYEES, PERMISSION_MANAGE_EMPLOYEES, 
    PERMISSION_VIEW_ARCHIVES, PERMISSION_MANAGE_ARCHIVES, PERMISSION_VIEW_KNOWLEDGE, 
    PERMISSION_MANAGE_KNOWLEDGE, PERMISSION_APPROVE_USERS, PERMISSION_RESET_PASSWORDS, 
    PERMISSION_MANAGE_ROLES, PERMISSION_VIEW_MESSAGES, PERMISSION_SEND_MESSAGES, 
    ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER, ROLE_PENDING,
    # 新增导入
    PERMISSION_MODULES, get_permission_description, get_role_description, 
    can_view_all_notifications, can_view_notification, can_edit_notification, can_delete_notification
)
from datetime import datetime, timezone, timedelta
import os

app = Flask(__name__)

def get_local_time():
    """获取本地时间"""
    return datetime.now()

def format_local_time(dt):
    """将时间格式化为本地时间字符串"""
    if dt is None:
        return ""
    return dt.strftime('%Y-%m-%d %H:%M')

# 配置
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化扩展
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录以访问此页面'

@app.route('/debug/time')
def debug_time():
    """调试时间显示"""
    current_utc = datetime.utcnow()
    current_local = datetime.now()
    
    return jsonify({
        'utc_time': current_utc.strftime('%Y-%m-%d %H:%M:%S'),
        'local_time': current_local.strftime('%Y-%m-%d %H:%M:%S'),
        'server_timezone': '需要检查服务器设置'
    })

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 上下文处理器
@app.context_processor
def inject_common_data():
    def get_quick_links():
        links = [
            {"name": "通知公告", "url": url_for('notifications_list'), "icon": "📢"},
            {"name": "耗材管理", "url": url_for('supplies_list'), "icon": "📦"},
            {"name": "流程审批", "url": url_for('request_list'), "icon": "✅"},
            {"name": "知识库", "url": url_for('knowledge_base'), "icon": "📚"},
            {"name": "档案查询", "url": url_for('archives_list'), "icon": "📁"}
        ]
        # 只有有用户管理权限的用户才能看到用户管理链接
        if current_user.is_authenticated and current_user.has_permission(PERMISSION_MANAGE_USERS):
            links.append({"name": "用户管理", "url": url_for('admin_users'), "icon": "👨‍💼"})
        
        # 只有有角色管理权限的用户才能看到权限管理链接
        # if current_user.is_authenticated and current_user.has_permission(PERMISSION_MANAGE_ROLES):
            # links.insert(6, {"name": "权限管理", "url": url_for('admin_permissions'), "icon": "🔐"})

        return links

    # 使用本地时间
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    
    return dict(
        current_user=current_user,
        has_permission=lambda p: current_user.is_authenticated and current_user.has_permission(p),
        get_quick_links=get_quick_links,
        date=current_date,
        format_local_time=format_local_time,
        # 添加权限相关函数到上下文
        get_permission_description=get_permission_description,
        get_role_description=get_role_description
    )

# 首页
@app.route('/')
@login_required
def index():
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    
    # 从数据库获取通知
    if can_view_all_notifications():
        # 超级管理员和管理员可以查看所有通知
        notifications = Notification.query.filter_by(is_active=True).order_by(
            Notification.is_top.desc(), 
            Notification.publish_time.desc()
        ).limit(5).all()
    else:
        # 普通用户只能查看全公司通知或本部门通知
        notifications = Notification.query.filter(
            (Notification.department == '全公司') | 
            (Notification.department == current_user.department) |
            (Notification.department.is_(None))
        ).filter_by(is_active=True).order_by(
            Notification.is_top.desc(), 
            Notification.publish_time.desc()
        ).limit(5).all()
    
    # 获取待办事项数量
    pending_requests_count = 0
    if current_user.has_permission(PERMISSION_APPROVE_REQUESTS):
        if current_user.has_role(ROLE_SUPER_ADMIN) or current_user.has_role(ROLE_ADMIN):
            pending_requests_count = SupplyRequest.query.filter_by(status='pending').count()
        else:
            pending_requests_count = SupplyRequest.query\
                .join(User, SupplyRequest.applicant_id == User.id)\
                .filter(SupplyRequest.status == 'pending')\
                .filter(User.department == current_user.department)\
                .count()
    
    # 获取未读消息数量
    unread_messages_count = Message.query.filter_by(
        recipient_id=current_user.id, 
        is_read=False
    ).count()
    
    # 获取低库存耗材数量
    low_stock_count = Supply.query.filter(
        Supply.current_stock <= Supply.min_stock_threshold,
        Supply.is_available == True
    ).count()
    
    # 获取用户的申请记录
    my_requests = SupplyRequest.query.filter_by(applicant_id=current_user.id)\
        .order_by(SupplyRequest.apply_time.desc())\
        .limit(5).all()
    
    return render_template('index.html', 
                         date=current_date,
                         notifications=notifications,
                         pending_requests_count=pending_requests_count,
                         unread_messages_count=unread_messages_count,
                         low_stock_count=low_stock_count,
                         my_requests=my_requests)

# 登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_approved:  # ← 新增检查
                flash('账户未审核，请等待。', 'error')
                return render_template('login.html', form=form)
            
            login_user(user)
            user.last_login = datetime.now()  # ← 新增记录最后登录时间
            db.session.commit()
            
            next_page = request.args.get('next')
            flash(f'欢迎回来，{user.real_name or user.username}！', 'success')
            return redirect(next_page or url_for('index'))
        else:
            flash('用户名或密码错误，请重试', 'error')
    
    return render_template('login.html', form=form)

# 退出登录
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功退出登录', 'success')
    return redirect(url_for('login'))

# 通知列表 - 确保正确排序
@app.route('/notifications')
@login_required
def notifications_list():
    # 使用权限检查函数
    if can_view_all_notifications():
        notifications = Notification.query.filter_by(is_active=True).order_by(
            Notification.is_top.desc(),  # 置顶的排在前面
            Notification.publish_time.desc()  # 然后按发布时间降序
        ).all()
    else:
        notifications = Notification.query.filter(
            (Notification.department == '全公司') | 
            (Notification.department == current_user.department) |
            (Notification.department.is_(None))
        ).filter_by(is_active=True).order_by(
            Notification.is_top.desc(),  # 置顶的排在前面
            Notification.publish_time.desc()  # 然后按发布时间降序
        ).all()
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('notifications.html', 
                         notifications=notifications, 
                         date=current_date)

# 通知详情页
@app.route('/notification/<int:notification_id>')
@login_required
def notification_detail(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    
    # 使用权限检查函数
    if not can_view_notification(notification):
        flash('您没有权限查看此通知', 'error')
        return redirect(url_for('index'))
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('notification_detail.html', 
                         notification=notification, 
                         date=current_date)


# 发布通知
@app.route('/notification/create', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_PUBLISH_NOTICES)
def create_notification():
    form = NotificationForm()
    
    if form.validate_on_submit():
        # 提前保存 current_user.id 到局部变量
        current_user_id = current_user.id
        
        # 使用本地时间
        notification = Notification(
            title=form.title.data,
            content=form.content.data,
            publisher_id=current_user_id,
            department=form.department.data or None,
            is_top=form.is_top.data,
            publish_time=datetime.now()
        )
        
        db.session.add(notification)
        db.session.commit()
        
        # +++ 修改：只为当前用户创建一条消息记录 +++
        message = Message(
            title=f"通知发布成功: {form.title.data}",
            content=f"您已成功发布通知：{form.title.data}。该通知将显示给相关用户。",
            message_type='system',
            category='personal',  # 个人消息，不是系统通知
            recipient_id=current_user_id,  # 只发给发布者自己
            sender_id=current_user_id,
            related_url=url_for('notifications_list')
        )
        db.session.add(message)
        db.session.commit()
        # +++ 修改结束 +++
        
        flash('通知发布成功！', 'success')
        return redirect(url_for('notifications_list'))
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('create_notification.html', form=form, date=current_date)

# 编辑通知
@app.route('/notification/<int:notification_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    
    # 使用新的权限检查函数
    if not can_edit_notification(notification):
        flash('您没有权限编辑此通知', 'error')
        return redirect(url_for('notifications_list'))
    
    form = NotificationForm(obj=notification)
    
    if form.validate_on_submit():
        notification.title = form.title.data
        notification.content = form.content.data
        notification.department = form.department.data or None
        notification.is_top = form.is_top.data
        
        db.session.commit()
        
        flash('通知更新成功！', 'success')
        return redirect(url_for('notifications_list'))
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('edit_notification.html', form=form, date=current_date, notification=notification)

# 删除通知
@app.route('/notification/<int:notification_id>/delete', methods=['POST'])
@login_required
def delete_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    
    # 使用新的权限检查函数
    if not can_delete_notification(notification):
        flash('您没有权限删除此通知', 'error')
        return redirect(url_for('notifications_list'))
    
    db.session.delete(notification)
    db.session.commit()
    
    flash('通知已删除！', 'success')
    return redirect(url_for('notifications_list'))

# 耗材列表
@app.route('/supplies')
@login_required
@permission_required(PERMISSION_VIEW_SUPPLIES)
def supplies_list():
    supplies = Supply.query.filter_by(is_available=True).all()
    categories = SupplyCategory.query.all()
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('supplies.html', 
                         supplies=supplies, 
                         categories=categories,
                         date=current_date)

# 申请列表
@app.route('/requests')
@login_required
def request_list():
    if current_user.has_permission(PERMISSION_APPROVE_REQUESTS):
        if current_user.has_role(ROLE_ADMIN):
            requests = SupplyRequest.query.order_by(SupplyRequest.apply_time.desc()).all()
        else:
            requests = SupplyRequest.query\
                .join(User, SupplyRequest.applicant_id == User.id)\
                .filter(User.department == current_user.department)\
                .order_by(SupplyRequest.apply_time.desc()).all()
    else:
        requests = SupplyRequest.query.filter_by(applicant_id=current_user.id)\
            .order_by(SupplyRequest.apply_time.desc()).all()
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('request_list.html', 
                         requests=requests,
                         date=current_date)

# 耗材申领
@app.route('/supply/request', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_REQUEST_SUPPLIES)
def supply_request():
    form = SupplyRequestForm()
    
    form.supply_id.choices = [(s.id, f"{s.name} (库存: {s.current_stock}{s.unit})") 
                             for s in Supply.query.filter_by(is_available=True).all()]
    
    if form.validate_on_submit():
        supply = Supply.query.get(form.supply_id.data)
        
        if supply.current_stock < form.quantity.data:
            flash(f'库存不足！当前库存：{supply.current_stock}{supply.unit}', 'error')
            return render_template('supply_request.html', form=form)
        
        request = SupplyRequest(
            applicant_id=current_user.id,
            supply_id=form.supply_id.data,
            quantity=form.quantity.data
        )
        
        db.session.add(request)
        db.session.commit()  # 先提交以获取request.id
        
        # 发送通知给有审批权限的管理员
        # 找到所有有审批权限的用户
        approvers = User.query.filter(User.is_active == True).all()
        approvers = [user for user in approvers if user.has_permission(PERMISSION_APPROVE_REQUESTS)]
        
        for approver in approvers:
            # 只发送给同部门的管理员，除非是超级管理员
            if approver.has_role(ROLE_SUPER_ADMIN) or approver.department == current_user.department:
                message = Message(
                    title='新的耗材申请待审批',
                    content=f'用户 {current_user.real_name} 提交了耗材申请：{supply.name} x {form.quantity.data}，请及时审批。',
                    message_type='approval',
                    recipient_id=approver.id,
                    sender_id=current_user.id,
                    related_url=url_for('request_list')
                )
                db.session.add(message)
        
        db.session.commit()
        
        flash('耗材申请提交成功，等待审批！', 'success')
        return redirect(url_for('supplies_list'))
    
    return render_template('supply_request.html', form=form)

# 审批申请
@app.route('/request/<int:request_id>/approve', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_APPROVE_REQUESTS)
def approve_request(request_id):
    supply_request = SupplyRequest.query.get_or_404(request_id)
    
    if not current_user.has_role(ROLE_ADMIN):
        if supply_request.applicant.department != current_user.department:
            flash('您只能审批本部门的申请', 'error')
            return redirect(url_for('request_list'))
    
    form = ApproveRequestForm()
    
    if form.validate_on_submit():
        if form.action.data == 'approve':
            supply_request.status = 'approved'
            supply_request.approver_id = current_user.id
            supply_request.approve_time = datetime.now()
            
            # 创建审批通过消息 - 修复：添加 sender_id
            message = Message(
                title='耗材申请已批准',
                content=f'您的耗材申请（{supply_request.supply.name} x {supply_request.quantity}）已获批准。',
                message_type='approval',
                recipient_id=supply_request.applicant_id,
                sender_id=current_user.id,  # 添加这一行
                related_url=url_for('request_list')
            )
            db.session.add(message)
            
            flash('申请已批准！', 'success')
        else:
            supply_request.status = 'rejected'
            supply_request.approver_id = current_user.id
            supply_request.approve_time = datetime.now()
            supply_request.reject_reason = form.reject_reason.data
            
            # 创建审批拒绝消息 - 修复：添加 sender_id
            message = Message(
                title='耗材申请被拒绝',
                content=f'您的耗材申请（{supply_request.supply.name} x {supply_request.quantity}）已被拒绝。原因：{form.reject_reason.data}',
                message_type='approval',
                recipient_id=supply_request.applicant_id,
                sender_id=current_user.id,  # 添加这一行
                related_url=url_for('request_list')
            )
            db.session.add(message)
            
            flash('申请已拒绝！', 'success')
        
        db.session.commit()
        return redirect(url_for('request_list'))
    
    return render_template('approve_request.html', form=form, supply_request=supply_request)

# 发放耗材
@app.route('/request/<int:request_id>/issue', methods=['POST'])
@login_required
@permission_required(PERMISSION_ISSUE_SUPPLIES)
def issue_request(request_id):
    supply_request = SupplyRequest.query.get_or_404(request_id)
    
    if supply_request.status != 'approved':
        flash('只能发放已批准的申请', 'error')
        return redirect(url_for('request_list'))
    
    if supply_request.supply.current_stock < supply_request.quantity:
        flash('库存不足，无法发放！', 'error')
        return redirect(url_for('request_list'))
    
    supply_request.supply.current_stock -= supply_request.quantity
    supply_request.status = 'issued'
    supply_request.issue_time = datetime.now()
    supply_request.issuer_id = current_user.id
    
    db.session.commit()
    
    flash('耗材发放成功！', 'success')
    return redirect(url_for('request_list'))

# 管理员功能
@app.route('/admin/supplies')
@login_required
@permission_required(PERMISSION_MANAGE_SUPPLIES)
def admin_supplies():
    supplies = Supply.query.all()
    categories = SupplyCategory.query.all()
    return render_template('admin_supplies.html', supplies=supplies, categories=categories)

# 创建耗材 - 修复权限检查
@app.route('/admin/supply/create', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_MANAGE_SUPPLIES)
def create_supply():
    form = SupplyForm()
    form.category_id.choices = [(c.id, c.name) for c in SupplyCategory.query.all()]
    
    if form.validate_on_submit():
        supply = Supply(
            name=form.name.data,
            category_id=form.category_id.data,
            total_stock=form.total_stock.data,
            current_stock=form.current_stock.data,
            unit=form.unit.data,
            min_stock_threshold=form.min_stock_threshold.data,
            description=form.description.data
        )
        
        db.session.add(supply)
        db.session.commit()
        
        flash('耗材添加成功！', 'success')
        return redirect(url_for('admin_supplies'))
    
    return render_template('create_supply.html', form=form)


# 编辑耗材 - 修复权限检查
@app.route('/admin/supply/<int:supply_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_MANAGE_SUPPLIES)
def edit_supply(supply_id):
    supply = Supply.query.get_or_404(supply_id)
    form = SupplyForm(obj=supply)
    form.category_id.choices = [(c.id, c.name) for c in SupplyCategory.query.all()]
    
    if form.validate_on_submit():
        supply.name = form.name.data
        supply.category_id = form.category_id.data
        supply.total_stock = form.total_stock.data
        supply.current_stock = form.current_stock.data
        supply.unit = form.unit.data
        supply.min_stock_threshold = form.min_stock_threshold.data
        supply.description = form.description.data
        
        db.session.commit()
        
        flash('耗材更新成功！', 'success')
        return redirect(url_for('admin_supplies'))
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('edit_supply.html', form=form, date=current_date, supply=supply)

# 停用耗材
@app.route('/admin/supply/<int:supply_id>/disable', methods=['POST'])
@login_required
@role_required(ROLE_ADMIN)
def disable_supply(supply_id):
    supply = Supply.query.get_or_404(supply_id)
    supply.is_available = False
    db.session.commit()
    
    flash('耗材已停用！', 'success')
    return redirect(url_for('admin_supplies'))

# 启用耗材
@app.route('/admin/supply/<int:supply_id>/enable', methods=['POST'])
@login_required
@role_required(ROLE_ADMIN)
def enable_supply(supply_id):
    supply = Supply.query.get_or_404(supply_id)
    supply.is_available = True
    db.session.commit()
    
    flash('耗材已启用！', 'success')
    return redirect(url_for('admin_supplies'))

# 入库耗材
@app.route('/supply/inbound', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_MANAGE_SUPPLIES)
def supply_inbound():
    form = SupplyInboundForm()
    
    form.supply_id.choices = [(s.id, f"{s.name} (当前库存: {s.current_stock}{s.unit})") 
                             for s in Supply.query.filter_by(is_available=True).all()]
    
    if form.validate_on_submit():
        supply = Supply.query.get(form.supply_id.data)
        
        # 使用新添加的方法增加库存
        supply.add_stock(form.quantity.data)
        
        db.session.commit()
        
        flash(f'成功入库 {form.quantity.data}{supply.unit} {supply.name}！', 'success')
        return redirect(url_for('supplies_list'))
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('supply_inbound.html', form=form, date=current_date)

# 耗材分类管理
@app.route('/supply/categories')
@login_required
@permission_required(PERMISSION_MANAGE_SUPPLIES)
def supply_categories():
    categories = SupplyCategory.query.all()
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('supply_categories.html', 
                         categories=categories,
                         date=current_date)

# 添加耗材分类
@app.route('/supply/category/create', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_MANAGE_SUPPLIES)
def create_supply_category():
    form = SupplyCategoryForm()
    
    if form.validate_on_submit():
        category = SupplyCategory(
            name=form.name.data,
            description=form.description.data
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash('耗材分类添加成功！', 'success')
        return redirect(url_for('supply_categories'))
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('create_supply_category.html', form=form, date=current_date)

# 编辑耗材分类
@app.route('/supply/category/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_MANAGE_SUPPLIES)
def edit_supply_category(category_id):
    category = SupplyCategory.query.get_or_404(category_id)
    form = SupplyCategoryForm(obj=category)
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        
        db.session.commit()
        
        flash('耗材分类更新成功！', 'success')
        return redirect(url_for('supply_categories'))
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('edit_supply_category.html', form=form, date=current_date, category=category)

# 删除耗材分类
@app.route('/supply/category/<int:category_id>/delete', methods=['POST'])
@login_required
@permission_required(PERMISSION_MANAGE_SUPPLIES)
def delete_supply_category(category_id):
    category = SupplyCategory.query.get_or_404(category_id)
    
    # 检查是否有耗材使用此分类
    if category.supplies:
        flash('该分类下还有耗材，无法删除！', 'error')
        return redirect(url_for('supply_categories'))
    
    db.session.delete(category)
    db.session.commit()
    
    flash('耗材分类已删除！', 'success')
    return redirect(url_for('supply_categories'))


# ============ 人员信息管理 ============

@app.route('/employees')
@login_required
@permission_required(PERMISSION_VIEW_EMPLOYEES)
def employees_list():
    form = EmployeeSearchForm()
    department = request.args.get('department', '')
    keyword = request.args.get('keyword', '')
    
    query = Employee.query
    
    if department:
        query = query.filter(Employee.department == department)
    
    if keyword:
        query = query.filter(
            db.or_(
                Employee.name.contains(keyword),
                Employee.employee_id.contains(keyword),
                Employee.position.contains(keyword)
            )
        )
    
    employees = query.order_by(Employee.department, Employee.name).all()
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('employees.html', 
                         employees=employees, 
                         form=form,
                         date=current_date)

@app.route('/employee/<int:employee_id>')
@login_required
@permission_required(PERMISSION_VIEW_EMPLOYEES)
def employee_detail(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    files = EmployeeFile.query.filter_by(employee_id=employee_id).all()
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('employee_detail.html', 
                         employee=employee, 
                         files=files,
                         date=current_date)

@app.route('/employee/create', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_MANAGE_EMPLOYEES)
def create_employee():
    form = EmployeeForm()
    
    if form.validate_on_submit():
        # 转换日期字符串为日期对象
        hire_date = datetime.strptime(form.hire_date.data, '%Y-%m-%d').date()
        
        employee = Employee(
            employee_id=form.employee_id.data,
            name=form.name.data,
            department=form.department.data,
            position=form.position.data,
            email=form.email.data,
            phone=form.phone.data,
            hire_date=hire_date,
            status=form.status.data
        )
        
        db.session.add(employee)
        db.session.commit()
        
        flash(f'员工 {employee.name} 添加成功！', 'success')
        return redirect(url_for('employees_list'))
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('create_employee.html', form=form, date=current_date)

@app.route('/employee/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_MANAGE_EMPLOYEES)
def edit_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    form = EmployeeForm(obj=employee)
    
    # 将日期对象转换为字符串用于表单显示
    form.hire_date.data = employee.hire_date.strftime('%Y-%m-%d')
    
    if form.validate_on_submit():
        hire_date = datetime.strptime(form.hire_date.data, '%Y-%m-%d').date()
        
        employee.employee_id = form.employee_id.data
        employee.name = form.name.data
        employee.department = form.department.data
        employee.position = form.position.data
        employee.email = form.email.data
        employee.phone = form.phone.data
        employee.hire_date = hire_date
        employee.status = form.status.data
        
        db.session.commit()
        
        flash(f'员工 {employee.name} 信息更新成功！', 'success')
        return redirect(url_for('employee_detail', employee_id=employee.id))
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('edit_employee.html', form=form, date=current_date, employee=employee)

# ============ 档案查询 ============

@app.route('/archives')
@login_required
@permission_required(PERMISSION_VIEW_ARCHIVES)
def archives_list():
    # 计算统计数据
    total_employees = Employee.query.count()
    active_employees = Employee.query.filter_by(status='在职').count()
    
    # 计算部门数量
    departments = db.session.query(Employee.department).distinct().all()
    department_count = len(departments)
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('archives.html', 
                         date=current_date,
                         total_employees=total_employees,
                         active_employees=active_employees,
                         department_count=department_count)

# ============ 知识库管理 ============

@app.route('/knowledge')
@login_required
@permission_required(PERMISSION_VIEW_KNOWLEDGE)
def knowledge_base():
    categories = KnowledgeCategory.query.filter_by(parent_id=None).all()
    recent_articles = KnowledgeArticle.query.filter_by(is_published=True)\
        .order_by(KnowledgeArticle.publish_time.desc())\
        .limit(10).all()
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('knowledge_base.html', 
                         categories=categories,
                         recent_articles=recent_articles,
                         date=current_date)

@app.route('/knowledge/category/<int:category_id>')
@login_required
@permission_required(PERMISSION_VIEW_KNOWLEDGE)
def knowledge_category(category_id):
    category = KnowledgeCategory.query.get_or_404(category_id)
    articles = KnowledgeArticle.query.filter_by(
        category_id=category_id, 
        is_published=True
    ).order_by(KnowledgeArticle.publish_time.desc()).all()
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('knowledge_category.html', 
                         category=category,
                         articles=articles,
                         date=current_date)

@app.route('/knowledge/article/<int:article_id>')
@login_required
@permission_required(PERMISSION_VIEW_KNOWLEDGE)
def knowledge_article(article_id):
    article = KnowledgeArticle.query.get_or_404(article_id)
    
    # 增加浏览次数
    article.view_count += 1
    db.session.commit()
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('knowledge_article.html', 
                         article=article,
                         date=current_date)

@app.route('/knowledge/article/create', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_MANAGE_KNOWLEDGE)
def create_knowledge_article():
    form = KnowledgeArticleForm()
    form.category_id.choices = [(c.id, c.name) for c in KnowledgeCategory.query.all()]
    
    if form.validate_on_submit():
        article = KnowledgeArticle(
            title=form.title.data,
            content=form.content.data,
            category_id=form.category_id.data,
            author_id=current_user.id,
            tags=form.tags.data,
            is_published=form.is_published.data
        )
        
        db.session.add(article)
        db.session.commit()
        
        flash('知识文章发布成功！', 'success')
        return redirect(url_for('knowledge_article', article_id=article.id))
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('create_knowledge_article.html', form=form, date=current_date)

@app.route('/knowledge/category/create', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_MANAGE_KNOWLEDGE)
def create_knowledge_category():
    form = KnowledgeCategoryForm()
    form.parent_id.choices = [(0, '无')] + [(c.id, c.name) for c in KnowledgeCategory.query.all()]
    
    if form.validate_on_submit():
        category = KnowledgeCategory(
            name=form.name.data,
            description=form.description.data,
            parent_id=form.parent_id.data if form.parent_id.data != 0 else None
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash('知识分类创建成功！', 'success')
        return redirect(url_for('knowledge_base'))
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('create_knowledge_category.html', form=form, date=current_date)

# 编辑知识分类
@app.route('/knowledge/category/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_MANAGE_KNOWLEDGE)
def edit_knowledge_category(category_id):
    category = KnowledgeCategory.query.get_or_404(category_id)
    form = KnowledgeCategoryForm(obj=category)
    form.parent_id.choices = [(0, '无')] + [(c.id, c.name) for c in KnowledgeCategory.query.all()]

    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        category.parent_id = form.parent_id.data if form.parent_id.data != 0 else None
        
        db.session.commit()
        flash('知识分类更新成功！', 'success')
        return redirect(url_for('knowledge_base'))
    
    return render_template('create_knowledge_category.html', form=form, category=category)

# 删除知识分类
@app.route('/knowledge/category/<int:category_id>/delete', methods=['POST'])
@login_required
@permission_required(PERMISSION_MANAGE_KNOWLEDGE)
def delete_knowledge_category(category_id):
    category = KnowledgeCategory.query.get_or_404(category_id)
    
    # 检查是否有子分类或文章
    if category.subcategories:
        flash('该分类下存在子分类，无法删除！', 'error')
        return redirect(url_for('knowledge_base'))
    
    if category.articles:
        flash('该分类下存在文章，无法删除！', 'error')
        return redirect(url_for('knowledge_base'))
    
    db.session.delete(category)
    db.session.commit()
    flash('知识分类已删除！', 'success')
    return redirect(url_for('knowledge_base'))

# 编辑知识文章
@app.route('/knowledge/article/<int:article_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_knowledge_article(article_id):
    article = KnowledgeArticle.query.get_or_404(article_id)
    
    # 权限检查：作者、管理员或超级管理员可以编辑
    if article.author_id != current_user.id and not (current_user.has_role(ROLE_SUPER_ADMIN) or current_user.has_role(ROLE_ADMIN)):
        flash('您没有权限编辑此文章', 'error')
        return redirect(url_for('knowledge_article', article_id=article_id))
    
    form = KnowledgeArticleForm(obj=article)
    form.category_id.choices = [(c.id, c.name) for c in KnowledgeCategory.query.all()]
    
    if form.validate_on_submit():
        article.title = form.title.data
        article.content = form.content.data
        article.category_id = form.category_id.data
        article.tags = form.tags.data
        article.is_published = form.is_published.data
        article.update_time = datetime.now()
        
        db.session.commit()
        flash('文章更新成功！', 'success')
        return redirect(url_for('knowledge_article', article_id=article.id))
    
    return render_template('create_knowledge_article.html', form=form, article=article)

# 删除知识文章
@app.route('/knowledge/article/<int:article_id>/delete', methods=['POST'])
@login_required
@permission_required(PERMISSION_MANAGE_KNOWLEDGE)
def delete_knowledge_article(article_id):
    article = KnowledgeArticle.query.get_or_404(article_id)
    
    db.session.delete(article)
    db.session.commit()
    flash('文章已删除！', 'success')
    return redirect(url_for('knowledge_base'))

# 调试路由
@app.route('/debug/routes')
def debug_routes():
    import urllib.parse
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods - set(['OPTIONS', 'HEAD'])))
        line = urllib.parse.unquote(f"{rule.endpoint:50} {methods:20} {rule}")
        output.append(line)
    
    return "<pre>" + "\n".join(sorted(output)) + "</pre>"

# 用户注册
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegisterForm()
    
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            real_name=form.real_name.data,
            email=form.email.data,
            phone=form.phone.data,
            department=form.department.data,
            status='pending',  # 注册后状态为待审核
            is_active=False   # 未激活
        )
        user.set_password(form.password.data)
        
        # 分配默认角色（普通用户）
        user_role = Role.query.filter_by(name=ROLE_USER).first()
        if user_role:
            user.roles.append(user_role)
        
        db.session.add(user)
        db.session.commit()
        
        flash('注册成功！请等待管理员审核。审核通过后即可登录。', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

# 用户管理列表
@app.route('/admin/users')
@login_required
@permission_required(PERMISSION_MANAGE_USERS)
def admin_users():
    status_filter = request.args.get('status', 'all')
    
    query = User.query
    
    if status_filter != 'all':
        query = query.filter(User.status == status_filter)
    
    users = query.order_by(User.created_at.desc()).all()
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('admin_users.html', 
                         users=users, 
                         status_filter=status_filter,
                         date=current_date)

# 审核用户
@app.route('/admin/user/<int:user_id>/approve', methods=['POST'])
@login_required
@permission_required(PERMISSION_APPROVE_USERS)
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.status == 'pending':
        user.approve()
        
        # 创建用户审核通过消息 - 修复：添加 sender_id
        message = Message(
            title='账户审核通过',
            content='您的账户已通过管理员审核，现在可以登录系统了。',
            message_type='system',
            recipient_id=user.id,
            sender_id=current_user.id  # 添加这一行
        )
        db.session.add(message)
        
        db.session.commit()
        flash(f'用户 {user.username} 已审核通过！', 'success')
    else:
        flash('只能审核待审核状态的用户', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/reject', methods=['POST'])
@login_required
@permission_required(PERMISSION_APPROVE_USERS)
def reject_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.status == 'pending':
        user.reject()
        
        # 创建用户审核拒绝消息 - 修复：添加 sender_id
        message = Message(
            title='账户审核未通过',
            content='您的账户审核未通过，请联系管理员了解详情。',
            message_type='system',
            recipient_id=user.id,
            sender_id=current_user.id  # 添加这一行
        )
        db.session.add(message)
        
        db.session.commit()
        flash(f'用户 {user.username} 已拒绝！', 'success')
    else:
        flash('只能拒绝待审核状态的用户', 'error')
    
    return redirect(url_for('admin_users'))

# 编辑用户
@app.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_MANAGE_USERS)
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.real_name = form.real_name.data
        user.email = form.email.data
        user.phone = form.phone.data
        user.department = form.department.data
        user.status = form.status.data
        user.is_active = (form.status.data == 'active')
        
        db.session.commit()
        flash(f'用户 {user.username} 信息更新成功！', 'success')
        return redirect(url_for('admin_users'))
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('edit_user.html', form=form, user=user, date=current_date)

# 分配角色
@app.route('/admin/user/<int:user_id>/roles', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_MANAGE_ROLES)
def user_roles(user_id):
    user = User.query.get_or_404(user_id)
    form = UserRoleForm()
    
    # 动态设置角色选项
    all_roles = Role.query.all()  # 获取所有角色
    form.roles.choices = [(role.id, role.name) for role in all_roles]
    
    if form.validate_on_submit():
        # 清除现有角色
        user.roles = []
        
        # 添加新角色
        for role_id in form.roles.data:
            role = Role.query.get(role_id)
            if role:
                user.roles.append(role)
        
        db.session.commit()
        flash(f'用户 {user.username} 角色分配成功！', 'success')
        return redirect(url_for('admin_users'))
    
    # 设置当前选中的角色
    form.roles.data = [role.id for role in user.roles]
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('user_roles.html', form=form, user=user, all_roles=all_roles, date=current_date)  # 添加 all_roles

# 重置密码
@app.route('/admin/user/<int:user_id>/reset_password', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_RESET_PASSWORDS)
def reset_user_password(user_id):
    user = User.query.get_or_404(user_id)
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        user.set_password(form.new_password.data)
        db.session.commit()
        flash(f'用户 {user.username} 密码重置成功！', 'success')
        return redirect(url_for('admin_users'))
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('reset_password.html', form=form, user=user, date=current_date)

# 创建用户（管理员直接创建）
@app.route('/admin/user/create', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_MANAGE_USERS)
def create_user():
    form = RegisterForm()
    
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            real_name=form.real_name.data,
            email=form.email.data,
            phone=form.phone.data,
            department=form.department.data,
            status='active',  # 管理员创建的用户直接激活
            is_active=True
        )
        user.set_password(form.password.data)
        
        # 分配默认角色（普通用户）
        user_role = Role.query.filter_by(name=ROLE_USER).first()
        if user_role:
            user.roles.append(user_role)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'用户 {user.username} 创建成功！', 'success')
        return redirect(url_for('admin_users'))
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('create_user.html', form=form, date=current_date)

@app.route('/messages')
@login_required
def messages_list():
    # 获取筛选参数
    filter_type = request.args.get('filter', 'all')
    
    # 基础查询：获取当前用户个人消息，以及其有权限查看的系统通知
    query = Message.query.filter(
        # 消息的接收者是当前用户
        (Message.recipient_id == current_user.id) |
        # 或者是系统通知，并且符合部门条件
        (
            (Message.category == 'notification') &
            (
                (Message.target_department.is_(None)) |  # 全公司通知
                (Message.target_department == '全公司') |  # 全公司通知
                (Message.target_department == current_user.department)  # 本部门通知
            )
        )
    )
    
    # 根据筛选条件进一步过滤
    if filter_type == 'personal':
        query = query.filter(Message.category != 'notification')
    elif filter_type == 'notification':
        query = query.filter(Message.category == 'notification')
    elif filter_type == 'unread':
        query = query.filter(Message.is_read == False)
    
    messages = query.order_by(Message.is_read.asc(), Message.created_at.desc()).all()
    
    # 获取未读消息数量（只计算个人消息）
    unread_count = Message.query.filter_by(
        recipient_id=current_user.id, 
        is_read=False
    ).count()
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('messages_list.html', 
                         messages=messages,
                         unread_count=unread_count,
                         date=current_date)

# 查看消息详情
@app.route('/message/<int:message_id>')
@login_required
def message_detail(message_id):
    message = Message.query.get_or_404(message_id)
    
    # 检查权限，只能查看自己的消息
    if message.recipient_id != current_user.id:
        flash('您没有权限查看此消息', 'error')
        return redirect(url_for('messages_list'))
    
    # 标记为已读
    if not message.is_read:
        message.is_read = True
        db.session.commit()
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('message_detail.html', 
                         message=message,
                         date=current_date)

# 标记消息为已读
@app.route('/message/<int:message_id>/read', methods=['POST'])
@login_required
def mark_message_read(message_id):
    message = Message.query.get_or_404(message_id)
    
    # 检查权限
    if message.recipient_id != current_user.id:
        return jsonify({'success': False, 'error': '无权操作'})
    
    message.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})

# 发送消息
@app.route('/message/send', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_SEND_MESSAGES)
def send_message():
    form = MessageForm()
    
    # 动态设置接收人选项
    form.recipient_id.choices = [(user.id, f"{user.username} ({user.department})") 
                                for user in User.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        message = Message(
            title=form.title.data,
            content=form.content.data,
            message_type=form.message_type.data,
            recipient_id=form.recipient_id.data,
            sender_id=current_user.id
        )
        
        db.session.add(message)
        db.session.commit()
        
        flash('消息发送成功！', 'success')
        return redirect(url_for('messages_list'))
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('send_message.html', form=form, date=current_date)

# 删除消息
@app.route('/message/<int:message_id>/delete', methods=['POST'])
@login_required
@permission_required(PERMISSION_VIEW_MESSAGES)
def delete_message(message_id):
    message = Message.query.get_or_404(message_id)
    
    # 检查权限，只能删除自己的消息
    if message.recipient_id != current_user.id:
        flash('您没有权限删除此消息', 'error')
        return redirect(url_for('messages_list'))
    
    db.session.delete(message)
    db.session.commit()
    
    flash('消息已删除！', 'success')
    return redirect(url_for('messages_list'))

@app.route('/api/unread_messages_count')
@login_required
def unread_messages_count():
    count = Message.query.filter_by(recipient_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

# 权限管理页面
@app.route('/admin/permissions')
@login_required
@permission_required(PERMISSION_MANAGE_ROLES)
def admin_permissions():
    """权限管理页面"""
    # 获取所有角色及其权限
    roles = Role.query.order_by(Role.level).all()
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('admin_permissions.html', 
                         roles=roles,
                         permission_modules=PERMISSION_MODULES,
                         get_permission_description=get_permission_description,
                         get_role_description=get_role_description,
                         date=current_date)

# 角色权限管理页面
@app.route('/admin/role/<role_name>/permissions', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSION_MANAGE_ROLES)
def edit_role_permissions(role_name):
    """编辑角色权限"""
    # 验证角色名称
    if role_name not in [ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER, ROLE_PENDING]:
        flash('无效的角色名称', 'error')
        return redirect(url_for('admin_permissions'))
    
    # 获取角色信息
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        flash('角色不存在', 'error')
        return redirect(url_for('admin_permissions'))
    
    # 创建表单并设置权限选项
    form = RolePermissionsForm()
    
    if request.method == 'GET':
        # 设置当前权限为选中状态
        current_permissions = role.permissions.split(',') if role.permissions else []
        form.permissions.data = current_permissions
    
    if form.validate_on_submit():
        try:
            # 更新角色权限
            new_permissions = form.permissions.data
            
            print(f"提交的新权限: {new_permissions}")
            
            # 过滤掉分隔符
            new_permissions = [p for p in new_permissions if p != '---separator---']
            
            print(f"过滤后的权限: {new_permissions}")
            
            # 更新数据库中的角色权限
            role.permissions = ','.join(new_permissions)
            
            print(f"更新前的角色权限: {role.permissions}")
            
            db.session.commit()
            
            # 重新查询确认更新
            updated_role = Role.query.filter_by(name=role_name).first()
            print(f"更新后的角色权限: {updated_role.permissions}")
            
            flash(f'角色 {role_name} 的权限已更新！', 'success')
            return redirect(url_for('admin_permissions'))
            
        except Exception as e:
            db.session.rollback()
            print(f"更新权限时出错: {str(e)}")
            flash(f'更新权限时出错: {str(e)}', 'error')
    
    current_date = get_local_time().strftime("%Y年%m月%d日 %H:%M")
    return render_template('edit_role_permissions.html', 
                         form=form, 
                         role=role,
                         role_name=role_name,
                         get_permission_description=get_permission_description,
                         get_role_description=get_role_description,
                         date=current_date)

# 重置角色权限
@app.route('/admin/role/<role_name>/reset', methods=['POST'])
@login_required
@permission_required(PERMISSION_MANAGE_ROLES)
def reset_role_permissions(role_name):
    """重置角色权限为默认值"""
    if role_name not in [ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER, ROLE_PENDING]:
        flash('无效的角色名称', 'error')
        return redirect(url_for('admin_permissions'))
    
    try:
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            flash('角色不存在', 'error')
            return redirect(url_for('admin_permissions'))
        
        # 从默认配置中获取权限
        from auth import ROLE_PERMISSIONS, reset_role_permissions
        default_permissions = ROLE_PERMISSIONS.get(role_name, [])
        
        # 更新数据库
        role.permissions = ','.join(default_permissions)
        db.session.commit()
        
        # 更新内存映射
        reset_role_permissions(role_name)
        
        flash(f'角色 {role_name} 的权限已重置为默认值！', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'重置权限时出错: {str(e)}', 'error')
    
    return redirect(url_for('admin_permissions'))

# 调试路由 - 检查角色权限
@app.route('/debug/role/<role_name>')
@login_required
@permission_required(PERMISSION_MANAGE_ROLES)
def debug_role_permissions(role_name):
    """调试角色权限"""
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        return jsonify({'error': '角色不存在'})
    
    return jsonify({
        'role_name': role.name,
        'permissions_in_db': role.permissions,
        'permissions_list': role.permissions.split(',') if role.permissions else []
    })

if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists('instance/portal.db'):
            print("数据库不存在，请先运行 init_db.py 初始化数据库")
        else:
            app.run(debug=True, host='0.0.0.0', port=5000)