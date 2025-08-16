# models.py
from datetime import datetime
import pytz
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

IST = pytz.timezone("Asia/Kolkata")


class Update(db.Model):
    __tablename__ = "updates"
    id = db.Column(db.String(32), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    process = db.Column(db.String(32), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

    read_logs = db.relationship(
        'ReadLog',
        backref='update',
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def to_dict(self):
        utc_ts = self.timestamp.replace(tzinfo=pytz.UTC)
        ist_ts = utc_ts.astimezone(IST)
        return {
            "id": self.id,
            "name": self.name,
            "process": self.process,
            "message": self.message,
            "timestamp": ist_ts.strftime("%d/%m/%Y, %H:%M:%S"),
        }


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')

    read_logs = db.relationship(
        'ReadLog',
        backref='user',
        cascade="all, delete-orphan"
    )

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class ReadLog(db.Model):
    __tablename__ = 'read_logs'

    id = db.Column(db.Integer, primary_key=True)
    update_id = db.Column(db.String(32), db.ForeignKey('updates.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    guest_name = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def reader_display(self):
        return self.user.display_name if self.user_id else self.guest_name


class SOPSummary(db.Model):
    __tablename__ = "sop_summaries"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    summary_text = db.Column(db.Text, nullable=False)
    department = db.Column(db.String(100), nullable=True)
    tags = db.Column(db.ARRAY(db.String), nullable=True)  # PostgreSQL array of tags
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "summary_text": self.summary_text,
            "department": self.department,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
        }


class LessonLearned(db.Model):
    __tablename__ = "lessons_learned"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)  # Full text of the lesson learned
    summary = db.Column(db.Text, nullable=True)  # Optional short summary
    author = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    tags = db.Column(db.ARRAY(db.String), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "author": self.author,
            "department": self.department,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
        }
