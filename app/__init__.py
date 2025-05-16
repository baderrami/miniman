from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_socketio import SocketIO
from datetime import datetime

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
socketio = SocketIO()

def create_app(config_name='default'):
    """
    Create and configure the Flask application

    Args:
        config_name (str): Configuration name to use

    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)

    # Load configuration
    from app.config import config
    app.config.from_object(config[config_name])

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    csrf.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    # Register blueprints
    from app.controllers.auth import auth_bp
    from app.controllers.network import network_bp
    from app.controllers.commands import commands_bp
    from app.controllers.system import system_bp
    from app.controllers.docker import docker_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(network_bp)
    app.register_blueprint(commands_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(docker_bp)

    # Add root route
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    # Load user model for Flask-Login
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Context processor to add datetime to all templates
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

    # Context processor to make USE_CDN flag available to templates
    @app.context_processor
    def inject_config():
        return {'use_cdn': app.config.get('USE_CDN', False)}

    return app
