"""Database initialization and seeding"""

from app import create_app, db
from app.models import User
from config import Config

app = create_app(Config)

def init_db():
    """Initialize database"""
    with app.app_context():
        db.create_all()
        print("✓ Database created successfully")

def seed_db():
    """Seed database with test data"""
    with app.app_context():
        # Clear existing data
        db.session.query(User).delete()
        
        # Create test users
        users_data = [
            ('Azazel', 'admin@ladder.gg', 'Log1progress', 0, 6),
            ('ladder.gg', 'ladder@ladder.gg', 'Travi4steal', 0, 6),
        ]
        
        for username, email, password, ggp, admin_level in users_data:
            user = User(
                username=username,
                email=email,
                ggp=ggp,
                admin_level=admin_level
            )
            user.set_password(password)
            db.session.add(user)
        
        db.session.commit()
        print("✓ Database seeded with test data")
        print("\nTest accounts:")
        print("Username: admin, Password: admin123 (OWNER)")
        print("Username: pro_player, Password: pro123 (DEP)")
        print("Username: casual_gamer, Password: casual123 (JUNIOR)")

if __name__ == '__main__':
    init_db()
    seed_db()
