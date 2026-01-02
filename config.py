import os
from datetime import timedelta

class Config:
    """Configuration for Flask application"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = 'sqlite:///ladder_gg.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'app/static/uploads'
    
    # Admin settings
    ADMIN_LEVELS = {
        0: 'USER',
        1: 'HELPER',
        2: 'JUNIOR',
        3: 'ADMIN',
        4: 'CHEATHUNTER',
        5: 'DEP',
        6: 'OWNER'
    }
    
    # Server list - Majestic RP Servers
    SERVERS = [
        'Portland',
        'Phoenix',
        'Denver',
        'Seattle',
        'Dallas',
        'Chicago',
        'New York',
        'Houston',
        'Los Angeles',
        'Las Vegas',
        'Miami',
        'Detroit',
        'San Diego',
        'Atlanta',
        'San Francisco',
        'Boston',
        'Washington',
        'MCL'
    ]
    
    # Game modes
    GAME_MODES = ['1x1', '2x2', '3x3', '5x5']
    
    # GGP Settings
    GGP_WIN = 50
    GGP_LOSS = -25
    GGP_MIN = 0
    GGP_LEVEL_THRESHOLD = 1000
    MAX_LEVEL = 10
    
    # Match settings
    MAX_PARTY_SIZE = {
        '1x1': 1,
        '2x2': 2,
        '3x3': 3,
        '5x5': 5
    }
    
    # GGP Range for matchmaking
    GGP_RANGE = 250    
    # Discord settings
    DISCORD_SERVER_URL = 'https://discord.gg/laddergg'  # Replace with your actual Discord server invite URL