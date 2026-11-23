import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'capstone-attendance-super-secret-key-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "attendance.db")}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Attendance Configuration
    DEFAULT_ATTENDANCE_THRESHOLD = 75.0  # 75% minimum requirement
    
    # Mail & Notification Settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'attendance-portal@university.edu')
    
    # If True, emails are rendered and logged into the DB without throwing SMTP errors
    MAIL_SIMULATION_MODE = os.environ.get('MAIL_SIMULATION_MODE', 'true').lower() in ['true', 'on', '1']
