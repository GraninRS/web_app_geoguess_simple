import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    YANDEX_STATIC_KEY = os.getenv('YANDEX_STATIC_KEY')
    YANDEX_GEOCODE_KEY = os.getenv('YANDEX_GEOCODE_KEY')
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'avatars')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024