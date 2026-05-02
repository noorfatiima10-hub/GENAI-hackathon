import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or os.urandom(32)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(app.instance_path, "app.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from . import models  # noqa
    with app.app_context():
        db.create_all()

    from .auth_routes import auth_bp
    from .main_routes import main_bp
    from .admin_routes import admin_bp
    from .chat_routes import chat_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(chat_bp)

    return app
