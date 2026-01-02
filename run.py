#!/usr/bin/env python3
"""Main application entry point"""

from app import create_app, db
from app.models import User, UserServer, Match, Party, Lobby, AdminAction, Ban, SupportTicket, Friend
import os
from config import Config

app = create_app(Config)

@app.shell_context_processor
def make_shell_context():
    """Context for flask shell"""
    return {
        'db': db,
        'User': User,
        'UserServer': UserServer,
        'Match': Match,
        'Party': Party,
        'Lobby': Lobby,
        'AdminAction': AdminAction,
        'Ban': Ban,
        'SupportTicket': SupportTicket,
        'Friend': Friend
    }

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Run the application
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=5000, debug=debug)
