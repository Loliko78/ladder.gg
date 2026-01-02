# app.py
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///arena.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---------------- MODELS ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='USER')
    ggp = db.Column(db.Integer, default=0)
    banned_until = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_level(self):
        return min(self.ggp // 1000 + 1, 10)

    def get_level_color(self):
        lvl = self.get_level()
        if lvl <= 2:
            return 'gray'
        if lvl <= 5:
            return 'cyan'
        if lvl <= 8:
            return 'blue'
        return 'purple'

class ServerProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    server_name = db.Column(db.String(50))
    nickname = db.Column(db.String(50))
    static = db.Column(db.String(20))

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mode = db.Column(db.String(10))
    server = db.Column(db.String(50))
    status = db.Column(db.String(20), default='waiting')

# ---------------- MATCHMAKING ----------------
def find_match(user, mode):
    min_ggp = max(user.ggp - 250, 0)
    max_ggp = user.ggp + 250
    return User.query.filter(User.ggp.between(min_ggp, max_ggp), User.id != user.id).all()

# ---------------- ROUTES ----------------
from flask import render_template, redirect, url_for, request
from flask_login import login_user, logout_user, login_required, current_user

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User(username=request.form['username'], email=request.form['email'])
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('profile'))
    return render_template('login.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ---------------- ADMIN ----------------
def role_required(roles):
    def wrapper(fn):
        def decorated(*args, **kwargs):
            if current_user.role not in roles:
                return redirect(url_for('index'))
            return fn(*args, **kwargs)
        decorated.__name__ = fn.__name__
        return decorated
    return wrapper

@app.route('/admin')
@login_required
@role_required(['ADMIN', 'CHEATHUNTER', 'OWNER', 'DEP'])
def admin_panel():
    users = User.query.all()
    return render_template('admin.html', users=users)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
