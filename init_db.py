import os
from simple_models import db, User, Role, Notification, SupplyCategory, Supply, SupplyRequest, Employee, EmployeeFile, KnowledgeCategory, KnowledgeArticle, Message
from auth import ROLE_PERMISSIONS, ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER, ROLE_PENDING

# 创建临时应用实例用于初始化数据库
from flask import Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'temp-secret-key'

db.init_app(app)

def init_database():
    # 确保instance目录存在
    os.makedirs('instance', exist_ok=True)
    
    with app.app_context():
        # 删除现有数据库（开发环境用，生产环境不要这样用）
        if os.path.exists('instance/portal.db'):
            os.remove('instance/portal.db')
        
        # 创建所有表
        db.create_all()
        print("数据库表创建成功！")
        
        # 添加角色数据
        roles = []
        for role_name, permissions in ROLE_PERMISSIONS.items():
            if role_name == ROLE_SUPER_ADMIN:
                description = '超级管理员'
                level = 1
            elif role_name == ROLE_ADMIN:
                description = '管理员'
                level = 2
            elif role_name == ROLE_USER:
                description = '普通用户'
                level = 3
            elif role_name == ROLE_PENDING:
                description = '待审核用户'
                level = 4
            else:
                description = role_name
                level = 5
            
            role = Role(
                name=role_name,
                description=description,
                level=level,
                permissions=','.join(permissions) if permissions else ''
            )
            roles.append(role)
        
        db.session.add_all(roles)
        db.session.commit()
        print("角色创建成功！")
        
        # 添加用户数据
        super_admin = User(
            username='superadmin', 
            department='管理员', 
            email='superadmin@company.com',
            real_name='超级管理员',
            status='active',
            is_active=True
        )
        super_admin.set_password('admin123')
        
        admin = User(
            username='admin', 
            department='管理员', 
            email='admin@company.com',
            real_name='系统管理员',
            status='active',
            is_active=True
        )
        admin.set_password('admin123')
        
        user1 = User(
            username='zhangsan', 
            department='技术部', 
            email='zhangsan@company.com',
            real_name='张三',
            status='active',
            is_active=True
        )
        user1.set_password('admin123')
        
        user2 = User(
            username='lisi', 
            department='人事部', 
            email='lisi@company.com',
            real_name='李四',
            status='active',
            is_active=True
        )
        user2.set_password('admin123')
        
        pending_user = User(
            username='wangwu', 
            department='财务部', 
            email='wangwu@company.com',
            real_name='王五',
            status='pending',
            is_active=False
        )
        pending_user.set_password('password123')
        
        db.session.add_all([super_admin, admin, user1, user2, pending_user])
        db.session.commit()
        
        # 分配角色
        super_admin_role = Role.query.filter_by(name=ROLE_SUPER_ADMIN).first()
        admin_role = Role.query.filter_by(name=ROLE_ADMIN).first()
        user_role = Role.query.filter_by(name=ROLE_USER).first()
        pending_role = Role.query.filter_by(name=ROLE_PENDING).first()
        
        super_admin.roles.append(super_admin_role)
        admin.roles.append(admin_role)
        user1.roles.append(user_role)
        user2.roles.append(user_role)
        pending_user.roles.append(pending_role)
        
        db.session.commit()
        print("用户创建和角色分配成功！")
        
        # 创建通知
        notifications = [
            Notification(
                title='春节放假通知',
                content='公司将于2月10日至2月17日放假，共8天。请大家安排好工作。',
                publisher_id=super_admin.id,
                is_top=True
            ),
            Notification(
                title='新员工入职培训',
                content='本周五下午2点将在会议室A举行新员工入职培训，请相关人员准时参加。',
                publisher_id=admin.id,
                department='全公司'
            ),
            Notification(
                title='服务器维护通知',
                content='本周六凌晨2点至4点进行服务器维护，期间系统将无法访问。',
                publisher_id=user1.id,
                department='技术部'
            )
        ]
        
        db.session.add_all(notifications)
        db.session.commit()
        print("测试通知创建成功！")
        
        # 创建示例消息
        messages = [
            Message(
                title='欢迎使用消息系统',
                content='欢迎使用公司内部消息系统！您可以通过此系统接收审批通知、部门消息等重要信息。',
                message_type='system',
                recipient_id=user1.id,
                sender_id=super_admin.id  # 确保有 sender_id
            ),
            Message(
                title='耗材申请已批准',
                content='您的签字笔申请（数量：5支）已被管理员批准，请前往耗材管理处领取。',
                message_type='approval',
                recipient_id=user1.id,
                sender_id=admin.id,  # 确保有 sender_id
                related_url='/requests'
            ),
            Message(
                title='部门会议通知',
                content='本周五下午3点将在会议室B召开技术部部门会议，请准时参加。',
                message_type='department',
                recipient_id=user1.id,
                sender_id=admin.id  # 确保有 sender_id
            )
        ]
        
        db.session.add_all(messages)
        db.session.commit()
        print("示例消息创建成功！")
        
        # 创建耗材分类和物品
        categories = [
            SupplyCategory(name='办公文具', description='笔、纸、文件夹等办公用品'),
            SupplyCategory(name='IT设备', description='电脑配件、耗材等'),
            SupplyCategory(name='生活用品', description='纸巾、饮用水等')
        ]
        
        db.session.add_all(categories)
        db.session.commit()
        print("耗材分类创建成功！")
        
        # 确保分类已提交到数据库，获取它们的ID
        office_category = SupplyCategory.query.filter_by(name='办公文具').first()
        it_category = SupplyCategory.query.filter_by(name='IT设备').first()
        life_category = SupplyCategory.query.filter_by(name='生活用品').first()
        
        supplies = [
            Supply(name='签字笔', category_id=office_category.id, total_stock=100, current_stock=95, unit='支', min_stock_threshold=20),
            Supply(name='A4打印纸', category_id=office_category.id, total_stock=50, current_stock=50, unit='包', min_stock_threshold=10),
            Supply(name='USB闪存盘', category_id=it_category.id, total_stock=20, current_stock=18, unit='个', min_stock_threshold=5),
            Supply(name='瓶装水', category_id=life_category.id, total_stock=200, current_stock=150, unit='瓶', min_stock_threshold=50)
        ]
        
        db.session.add_all(supplies)
        db.session.commit()
        print("耗材物品创建成功！")
        
        # 添加员工数据
        from datetime import datetime, date
        
        employees = [
            Employee(
                employee_id='EMP001',
                name='张三',
                department='技术部',
                position='高级工程师',
                email='zhangsan@company.com',
                phone='13800138001',
                hire_date=date(2020, 5, 10),
                status='在职'
            ),
            Employee(
                employee_id='EMP002',
                name='李四',
                department='人事部',
                position='人事经理',
                email='lisi@company.com',
                phone='13800138002',
                hire_date=date(2019, 3, 15),
                status='在职'
            )
        ]
        
        db.session.add_all(employees)
        db.session.commit()
        print("示例员工数据创建成功！")
        
        # 添加知识库数据
        knowledge_categories = [
            KnowledgeCategory(name='公司制度', description='公司各项规章制度'),
            KnowledgeCategory(name='工作流程', description='各部门工作流程规范'),
            KnowledgeCategory(name='技术文档', description='技术开发相关文档'),
            KnowledgeCategory(name='培训资料', description='员工培训学习资料')
        ]
        
        db.session.add_all(knowledge_categories)
        db.session.commit()
        print("知识库分类创建成功！")
        
        # 添加示例知识文章
        knowledge_articles = [
            KnowledgeArticle(
                title='新员工入职指南',
                content='欢迎新同事加入！本文档将指导您完成入职流程：\n\n1. 办理入职手续\n2. 领取办公用品\n3. 参加入职培训\n4. 熟悉工作环境\n\n如有任何问题，请随时联系人事部。',
                category_id=knowledge_categories[0].id,
                author_id=admin.id,
                tags='入职,指南,新员工',
                is_published=True
            ),
            KnowledgeArticle(
                title='财务报销流程',
                content='公司财务报销的具体流程和注意事项：\n\n1. 填写报销单\n2. 部门经理审批\n3. 财务部审核\n4. 出纳付款\n\n请注意保留所有原始票据。',
                category_id=knowledge_categories[1].id,
                author_id=admin.id,
                tags='财务,报销,流程',
                is_published=True
            )
        ]
        
        db.session.add_all(knowledge_articles)
        db.session.commit()
        print("知识库文章创建成功！")
        
        print("\n数据库初始化完成！")
        print("测试账号：")
        print("  - 超级管理员: superadmin / admin123")
        print("  - 管理员: admin / admin123")
        print("  - 技术部用户: zhangsan / admin123")
        print("  - 人事部用户: lisi / admin123")
        print("  - 待审核用户: wangwu / admin123 (无法登录)")
        print("\n功能说明：")
        print("  - 超级管理员和管理员可以发送和查看所有消息")
        print("  - 普通用户可以查看自己的消息")
        print("  - 待审核用户无任何权限")

if __name__ == '__main__':
    init_database()