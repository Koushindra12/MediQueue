import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    # App Settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'queue-cure-secret-key-2024-professional')
    DEBUG = os.environ.get('DEBUG', 'True') == 'True'
    
    # MongoDB Settings
    MONGO_URI = os.environ.get(
        'MONGO_URI', 
        'mongodb://localhost:27017/queuecure'
    )
    MONGO_DBNAME = os.environ.get('MONGO_DBNAME', 'queuecure')
    
    # SocketIO Settings
    SOCKETIO_ASYNC_MODE = 'threading'
    CORS_ALLOWED_ORIGINS = "*"
    
    # Queue Settings
    MAX_QUEUE_SIZE = int(os.environ.get('MAX_QUEUE_SIZE', 100))
    AVG_CONSULTATION_TIME = int(os.environ.get('AVG_CONSULTATION_TIME', 15))  # minutes
    
    # Clinic Settings
    CLINIC_NAME = os.environ.get('CLINIC_NAME', 'Queue-Cure Medical Center')
    CLINIC_ADDRESS = os.environ.get('CLINIC_ADDRESS', '123 Health Street, Medical District')
    CLINIC_PHONE = os.environ.get('CLINIC_PHONE', '+1-800-QUEUECURE')
    
    # Working Hours
    CLINIC_OPEN_TIME = os.environ.get('CLINIC_OPEN_TIME', '09:00')
    CLINIC_CLOSE_TIME = os.environ.get('CLINIC_CLOSE_TIME', '17:00')
    
    # QR Code Settings
    QR_CODE_DIR = os.path.join(os.path.dirname(__file__), 'static', 'qrcodes')
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}