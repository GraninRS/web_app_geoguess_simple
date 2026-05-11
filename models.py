from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    best_score = db.Column(db.Float, default=0.0)
    avatar = db.Column(db.String(256), default='default.png')  # путь к аве

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    country = db.Column(db.String(128))
    continent = db.Column(db.String(64))
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    population = db.Column(db.String(64), default='')
    info = db.Column(db.Text, default='')

class GameResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Float, default=0.0)
    date_played = db.Column(db.DateTime, default=datetime.utcnow)