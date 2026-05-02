from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login_manager

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    profile = db.relationship("PersonalityProfile", backref="user", uselist=False, cascade="all,delete")
    runs = db.relationship("SimulationRun", backref="user", cascade="all,delete")
    journal_entries = db.relationship("JournalEntry", backref="user", cascade="all,delete")
    chat_messages = db.relationship("ChatMessage", backref="user", cascade="all,delete")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class PersonalityProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)

    introversion = db.Column(db.Integer, default=50)
    boldness = db.Column(db.Integer, default=50)
    creativity = db.Column(db.Integer, default=50)
    sleep_hours = db.Column(db.Integer, default=7)
    work_hours = db.Column(db.Integer, default=6)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SimulationRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile_snapshot_json = db.Column(db.Text, nullable=False)
    result_json = db.Column(db.Text, nullable=False)

class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(40), default="neutral")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
