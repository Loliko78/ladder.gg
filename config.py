import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ladder-gg-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'ladder.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Admin levels (5 уровней: HELPER, JUNIOR, ADMIN, CHEATHUNTER, OWNER/DEP)
    # OWNER и DEP оба имеют полный доступ, но OWNER максимум 2 и создается через DB
    # DEP назначается OWNER и не может снять OWNER
    ADMIN_LEVELS = {
        'HELPER': 1,
        'JUNIOR': 2,
        'ADMIN': 3,
        'CHEATHUNTER': 4,
        'DEP': 5,
        'OWNER': 6  # Специальный уровень, создается через DB, максимум 2
    }
    
    # GGP settings
    GGP_WIN = 50  # +50 GGP за победу
    GGP_LOSE = 25  # -25 GGP за проигрыш (не может уйти в минус)
    GGP_PER_LEVEL = 1000  # Каждые 1000 GGP = новый уровень
    MAX_LEVEL = 10  # Максимальный уровень 10, потом просто накопление поинтов
    
    # Level colors
    LEVEL_COLORS = {
        1: '#808080',  # серый
        2: '#808080',  # серый
        3: '#4169E1',  # голубой (Royal Blue)
        4: '#4169E1',  # голубой
        5: '#4169E1',  # голубой
        6: '#0000CD',  # синий (Medium Blue)
        7: '#0000CD',  # синий
        8: '#0000CD',  # синий
        9: '#4B0082',  # темно-фиолетовый
        10: '#4B0082'  # темно-фиолетовый
    }
    
    # Match types
    MATCH_TYPES = ['1x1', '2x2', '3x3', '5x5']
    
    # Game servers (17 серверов Majestic RP)
    SERVERS = [
        'Majestic RP #1',
        'Majestic RP #2', 
        'Majestic RP #3',
        'Majestic RP #4',
        'Majestic RP #5',
        'Majestic RP #6',
        'Majestic RP #7',
        'Majestic RP #8',
        'Majestic RP #9',
        'Majestic RP #10',
        'Majestic RP #11',
        'Majestic RP #12',
        'Majestic RP #13',
        'Majestic RP #14',
        'Majestic RP #15',
        'Majestic RP #16',
        'Majestic RP #17'
    ]
    
    # Site colors - серый основной, малиновый дополнительный
    COLOR_PRIMARY = '#808080'      # серый (основной)
    COLOR_SECONDARY = '#DC143C'    # малиновый (дополнительный)
    COLOR_SUCCESS = '#27ae60'      # зеленый
    COLOR_DANGER = '#e74c3c'       # красный
    COLOR_WARNING = '#f39c12'      # оранжевый
    COLOR_INFO = '#808080'         # серый (инфо)
    COLOR_LIGHT = '#b0b0b0'        # светло-серый
    COLOR_DARK = '#505050'         # темно-серый
    
    # Matchmaking settings
    MATCHMAKING_RANGE = 250  # ±250 GGP
    MATCHMAKING_TIMEOUT = 300  # 5 минут
    PARTY_MAX_SIZE = 5
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    # File upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False  # True for production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'