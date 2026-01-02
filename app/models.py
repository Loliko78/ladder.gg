from app import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from config import Config

class User(UserMixin, db.Model):
    """User model"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    ggp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=0)
    admin_level = db.Column(db.Integer, default=0)  # 0=USER, 1=HELPER, 2=JUNIOR, 3=ADMIN, 4=CH, 5=DEP, 6=OWNER
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_banned = db.Column(db.Boolean, default=False)
    ban_expires = db.Column(db.DateTime)
    is_email_verified = db.Column(db.Boolean, default=False)
    
    # Relationships
    servers = db.relationship('UserServer', backref='user', lazy=True, cascade='all, delete-orphan')
    friends = db.relationship('Friend', foreign_keys='Friend.user_id', backref='user', lazy=True)
    friend_of = db.relationship('Friend', foreign_keys='Friend.friend_id', backref='friend_user', lazy=True)
    matches = db.relationship('Match', backref='creator', lazy=True)
    party_memberships = db.relationship('PartyMember', backref='user', lazy=True)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches"""
        return check_password_hash(self.password_hash, password)
    
    def update_ggp(self, amount):
        """Update GGP and level"""
        old_ggp = self.ggp
        old_level = self.level
        self.ggp = max(Config.GGP_MIN, self.ggp + amount)
        # Level calculation: 0-999 GGP = level 0, 1000-1999 = level 1, ..., 10000+ = level 10+
        # Each level requires GGP_LEVEL_THRESHOLD (1000) GGP. Max level is 10
        self.level = min(Config.MAX_LEVEL, self.ggp // Config.GGP_LEVEL_THRESHOLD)
        db.session.commit()
        print(f"Updated GGP: {old_ggp} -> {self.ggp} (+{amount}), Level: {old_level} -> {self.level}")
    
    def add_friend(self, friend):
        """Add friend"""
        if not self.is_friend(friend):
            friend_rel = Friend(user_id=self.id, friend_id=friend.id)
            db.session.add(friend_rel)
            db.session.commit()
    
    def remove_friend(self, friend):
        """Remove friend"""
        Friend.query.filter_by(user_id=self.id, friend_id=friend.id).delete()
        db.session.commit()
    
    def is_friend(self, other):
        """Check if user is friend"""
        return Friend.query.filter_by(user_id=self.id, friend_id=other.id).first() is not None
    
    def get_admin_level_name(self):
        """Get admin level name"""
        return Config.ADMIN_LEVELS.get(self.admin_level, 'USER')
    
    def get_level_color(self):
        """Get level color for display"""
        if self.level <= 2:
            return '#808080'  # gray
        elif self.level <= 5:
            return '#00BFFF'  # light blue
        elif self.level <= 8:
            return '#0000FF'  # blue
        elif self.level <= 10:
            return '#4B0082'  # dark purple
        else:
            return '#4B0082'  # dark purple for 10+
    
    def __repr__(self):
        return f'<User {self.username}>'


class UserServer(db.Model):
    """User server profile"""
    __tablename__ = 'user_servers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    server_name = db.Column(db.String(50), nullable=False)
    server_nickname = db.Column(db.String(80), nullable=False)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'server_name', name='unique_user_server'),)
    
    def get_winrate(self):
        """Calculate winrate"""
        total = self.wins + self.losses
        if total == 0:
            return 0
        return round(self.wins / total * 100, 2)
    
    def __repr__(self):
        return f'<UserServer {self.server_name}>'


class Friend(db.Model):
    """Friend relationship"""
    __tablename__ = 'friends'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),)
    
    def __repr__(self):
        return f'<Friend {self.user_id}->{self.friend_id}>'


class Match(db.Model):
    """Match record"""
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mode = db.Column(db.String(10), nullable=False)  # 1x1, 2x2, 3x3, 5x5
    server = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='searching')  # searching, matched, finished, cancelled
    team1_players = db.Column(db.JSON)
    team2_players = db.Column(db.JSON)
    team1_score = db.Column(db.Integer)
    team2_score = db.Column(db.Integer)
    winner = db.Column(db.Integer)  # user_id of winner
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Match {self.id} {self.mode}>'


class Party(db.Model):
    """Party/Group for matchmaking"""
    __tablename__ = 'parties'
    
    id = db.Column(db.Integer, primary_key=True)
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mode = db.Column(db.String(10), nullable=False)
    server = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='open')  # open, searching, matched, closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    members = db.relationship('PartyMember', backref='party', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Party {self.id}>'


class PartyMember(db.Model):
    """Party member"""
    __tablename__ = 'party_members'
    
    id = db.Column(db.Integer, primary_key=True)
    party_id = db.Column(db.Integer, db.ForeignKey('parties.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('party_id', 'user_id', name='unique_party_member'),)
    
    def __repr__(self):
        return f'<PartyMember {self.party_id}-{self.user_id}>'


class Lobby(db.Model):
    """Custom lobby room"""
    __tablename__ = 'lobbies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mode = db.Column(db.String(10), nullable=False)
    server = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, default='')  # Описание лобби от создателя
    invite_code = db.Column(db.String(20), nullable=True)  # Уникальный код приглашения
    is_public = db.Column(db.Boolean, default=True)
    password = db.Column(db.String(50))
    max_players = db.Column(db.Integer, nullable=False)
    current_players = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='open')  # open, full, started, finished
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    creator = db.relationship('User', backref='lobbies')
    members = db.relationship('LobbyMember', backref='lobby', cascade='all, delete-orphan')
    messages = db.relationship('LobbyMessage', backref='lobby', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Lobby {self.name}>'


class LobbyMember(db.Model):
    """Lobby member - tracks who is in the lobby"""
    __tablename__ = 'lobby_members'
    
    id = db.Column(db.Integer, primary_key=True)
    lobby_id = db.Column(db.Integer, db.ForeignKey('lobbies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    team_number = db.Column(db.Integer, default=1)  # For team games: 1 or 2 (for 2x2, 3x3, 5x5)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='lobby_memberships')
    
    __table_args__ = (db.UniqueConstraint('lobby_id', 'user_id', name='unique_lobby_member'),)
    
    def __repr__(self):
        return f'<LobbyMember {self.lobby_id}-{self.user_id} Team:{self.team_number}>'


class LobbyMessage(db.Model):
    """Chat message in lobby"""
    __tablename__ = 'lobby_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    lobby_id = db.Column(db.Integer, db.ForeignKey('lobbies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='lobby_messages')
    
    def __repr__(self):
        return f'<LobbyMessage {self.id}>'


class LobbyScreenshot(db.Model):
    """Screenshot submitted from lobby for admin review"""
    __tablename__ = 'lobby_screenshots'
    
    id = db.Column(db.Integer, primary_key=True)
    lobby_id = db.Column(db.Integer, db.ForeignKey('lobbies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    result = db.Column(db.String(10), nullable=False)  # 'win' or 'loss'
    image_path = db.Column(db.String(255), nullable=False)  # Path to saved image
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)  # Admin notes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    lobby = db.relationship('Lobby', backref='screenshots')
    user = db.relationship('User', foreign_keys=[user_id], backref='lobby_screenshots')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    
    def __repr__(self):
        return f'<LobbyScreenshot {self.id} - {self.result}>'


class LobbyBan(db.Model):
    """Ban from specific lobby"""
    __tablename__ = 'lobby_bans'
    
    id = db.Column(db.Integer, primary_key=True)
    lobby_id = db.Column(db.Integer, db.ForeignKey('lobbies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    banned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    lobby = db.relationship('Lobby', backref='bans')
    user = db.relationship('User', foreign_keys=[user_id], backref='lobby_bans')
    banner = db.relationship('User', foreign_keys=[banned_by])
    
    __table_args__ = (db.UniqueConstraint('lobby_id', 'user_id', name='unique_lobby_ban'),)
    
    def __repr__(self):
        return f'<LobbyBan {self.lobby_id}-{self.user_id}>'


class LobbyInvite(db.Model):
    """Invite link for lobby"""
    __tablename__ = 'lobby_invites'
    
    id = db.Column(db.Integer, primary_key=True)
    lobby_id = db.Column(db.Integer, db.ForeignKey('lobbies.id'), nullable=False)
    invite_code = db.Column(db.String(32), unique=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    max_uses = db.Column(db.Integer, default=None)  # None = unlimited
    uses_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    lobby = db.relationship('Lobby', backref='invites')
    creator = db.relationship('User', backref='lobby_invites_created')
    
    def __repr__(self):
        return f'<LobbyInvite {self.invite_code}>'


class AdminAction(db.Model):
    """Admin action log"""
    __tablename__ = 'admin_actions'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # ban, unban, role_change, etc.
    target_user_id = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text)
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    admin = db.relationship('User', foreign_keys=[admin_id], backref='actions_log')


class Ban(db.Model):
    """Ban record"""
    __tablename__ = 'bans'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    ban_type = db.Column(db.String(20), nullable=False)  # temporary, permanent
    expires_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    banned_user = db.relationship('User', foreign_keys=[user_id], backref='bans')
    admin = db.relationship('User', foreign_keys=[admin_id], backref='bans_issued')


class SupportTicket(db.Model):
    """Support ticket"""
    __tablename__ = 'support_tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')  # open, in_progress, resolved, closed
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    resolution = db.Column(db.Text)
    
    creator = db.relationship('User', foreign_keys=[creator_id], backref=db.backref('support_tickets', cascade='all, delete-orphan'))
    assigned_admin = db.relationship('User', foreign_keys=[assigned_to_id], backref='assigned_tickets')
    
    def __repr__(self):
        return f'<SupportTicket {self.id}>'


class SupportMessage(db.Model):
    """Support ticket message"""
    __tablename__ = 'support_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    ticket = db.relationship('SupportTicket', backref='messages')
    user = db.relationship('User')
    
    def __repr__(self):
        return f'<SupportMessage {self.id}>'


@login_manager.user_loader
def load_user(id):
    """Load user by id"""
    return User.query.get(int(id))
