from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

def init_csrf(app):
    """初始化 CSRF 保护"""
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_SECRET_KEY'] = app.config.get('SECRET_KEY', 'csrf-secret-key')
    csrf.init_app(app)