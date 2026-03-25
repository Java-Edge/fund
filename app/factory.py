from flask import Flask

from app.apis.v1 import api_v1_bp
from app.core.bootstrap import configure_runtime, register_common_handlers

configure_runtime()

# 应用工厂模式（Application Factory Pattern）
# 定义一个函数（通常叫 create_app），用来动态创建、配置和初始化 Flask 应用实例
# 而不是在全局作用域直接实例化 app = Flask(__name__)

# 为啥用工厂模式？（主要优势）
# 小项目直接在 __init__.py 或 main.py 写 app = Flask(__name__) 没问题。
# 但中大型项目，factory.py 至关重要：
# A. 避免循环导入 (Circular Imports)
# 问题：如果 app 是全局变量，你在 models.py 或 views.py 中导入 app，而 __init__.py 又导入 models 和 views，就会形成循环依赖，导致报错。
# 解决：工厂模式下，扩展对象（如 db = SQLAlchemy()）在 factory.py 外部定义，在 create_app 内部通过 db.init_app(app) 绑定。视图函数不需要直接导入 app 实例，从而打破循环。
# B. 便于测试 (Testing)
# 问题：测试时需要一个干净、独立的应用实例，且配置需要指向测试数据库。
# 解决：测试代码可以多次调用 create_app(test_config)，每次都能获得一个全新的、配置隔离的 app 实例，测试完即销毁，互不干扰。
# C. 多实例运行 (Multiple Instances)
# 如果你需要在同一个进程中运行同一个应用的多个实例（例如多租户系统，每个租户一个独立的配置），工厂模式允许你创建多个不同的 app 对象。
# D. 动态配置 (Dynamic Configuration)
# 可以根据传入的参数决定加载哪种配置（开发、生产、测试），而不需要修改代码。

def create_app() -> Flask:
    # 通常执行以下步骤：
    # 创建实例：实例化Flask对象
    # 加载配置：根据环境变量（如开发、测试、生产）加载不同的配置文件
    # 初始化扩展：初始化数据库（SQLAlchemy）、迁移（Migrate）、登录管理（LoginManager）等插件

    app = Flask(__name__)
    register_common_handlers(app)

    from auth import auth_bp, init_default_admin
    from holdings import holdings_bp, init_holdings_table

    # 注册蓝图：将项目中的各个模块（Blueprints）注册到app上
    # 注册钩子：配置错误处理器、请求钩子等
    # 返回应用：最后返回配置好的app对象
    app.register_blueprint(auth_bp)
    app.register_blueprint(holdings_bp)
    app.register_blueprint(api_v1_bp)

    init_default_admin()
    init_holdings_table()
    return app