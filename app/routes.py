from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import (
    User, UserServer, Match, Party, PartyMember, Lobby, LobbyMember, LobbyMessage, LobbyScreenshot,
    LobbyBan, LobbyInvite, AdminAction, Ban, SupportTicket, SupportMessage, Friend
)
from config import Config
from datetime import datetime, timedelta
from functools import wraps
import os

# Blueprint definitions
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ==================== DECORATORS ====================

def admin_required(min_level=1):
    """Decorator for admin-only routes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.admin_level < min_level:
                flash('У вас нет прав доступа', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def api_login_required(f):
    """Decorator for API authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ==================== AUTH ROUTES ====================

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Validation
        if len(username) < 3:
            flash('Никнейм должен быть минимум 3 символа', 'danger')
            return redirect(url_for('auth.register'))
        
        if len(password) < 6:
            flash('Пароль должен быть минимум 6 символов', 'danger')
            return redirect(url_for('auth.register'))
        
        if password != password_confirm:
            flash('Пароли не совпадают', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(username=username).first():
            flash('Это имя пользователя уже зарегистрировано', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Этот email уже зарегистрирован', 'danger')
            return redirect(url_for('auth.register'))
        
        # Create user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Аккаунт успешно создан! Теперь вы можете войти', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Check if user is banned
            if user.is_banned:
                if user.ban_expires and user.ban_expires > datetime.utcnow():
                    flash(f'Ваш аккаунт забанен до {user.ban_expires.strftime("%d.%m.%Y %H:%M")}', 'danger')
                    return redirect(url_for('auth.login'))
                else:
                    user.is_banned = False
                    user.ban_expires = None
                    db.session.commit()
            
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('Неправильное имя пользователя или пароль', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('Вы вышли из аккаунта', 'info')
    return redirect(url_for('auth.login'))

# ==================== MAIN ROUTES ====================

@main_bp.route('/')
def index():
    """Home page"""
    if current_user.is_authenticated:
        stats = {
            'total_users': User.query.count(),
            'total_matches': Match.query.count(),
            'online_users': User.query.filter(User.last_login > datetime.utcnow() - timedelta(minutes=5)).count()
        }
        return render_template('index.html', stats=stats)
    return redirect(url_for('auth.login'))

@main_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    user = current_user
    user_servers = UserServer.query.filter_by(user_id=user.id).all()
    friends_list = User.query.join(Friend, Friend.friend_id == User.id).filter(Friend.user_id == user.id).all()
    
    # Get current lobby membership
    current_lobby_member = LobbyMember.query.filter_by(user_id=user.id).order_by(LobbyMember.joined_at.desc()).first()
    current_lobby = None
    if current_lobby_member:
        current_lobby = Lobby.query.get(current_lobby_member.lobby_id)
    
    return render_template('profile.html',
                         user=user,
                         user_servers=user_servers,
                         friends=friends_list,
                         all_servers=Config.SERVERS,
                         current_lobby=current_lobby)

@main_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit profile"""
    if request.method == 'POST':
        # Handle server selection
        selected_servers = request.form.getlist('servers')
        
        # Remove servers not selected
        UserServer.query.filter(
            UserServer.user_id == current_user.id,
            ~UserServer.server_name.in_(selected_servers) if selected_servers else True
        ).delete()
        
        # Add new servers
        for server in selected_servers:
            existing = UserServer.query.filter_by(
                user_id=current_user.id,
                server_name=server
            ).first()
            
            if not existing:
                nickname = request.form.get(f'nickname_{server}', server)
                user_server = UserServer(
                    user_id=current_user.id,
                    server_name=server,
                    server_nickname=nickname
                )
                db.session.add(user_server)
            else:
                nickname = request.form.get(f'nickname_{server}', existing.server_nickname)
                existing.server_nickname = nickname
        
        db.session.commit()
        flash('Профиль обновлен', 'success')
        return redirect(url_for('main.profile'))
    
    user_servers = UserServer.query.filter_by(user_id=current_user.id).all()
    selected = [s.server_name for s in user_servers]
    
    return render_template('profile_edit.html',
                         user=current_user,
                         all_servers=Config.SERVERS,
                         selected_servers=selected,
                         user_servers={s.server_name: s for s in user_servers})

@main_bp.route('/leaderboard')
def leaderboard():
    """Leaderboard"""
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', 'ggp')  # ggp or level
    
    if sort_by == 'level':
        users = User.query.order_by(User.level.desc(), User.ggp.desc()).paginate(page=page, per_page=50)
    else:
        users = User.query.order_by(User.ggp.desc()).paginate(page=page, per_page=50)
    
    return render_template('leaderboard.html', users=users, sort_by=sort_by)

@main_bp.route('/servers')
def servers():
    """Server list"""
    return render_template('servers.html', servers=Config.SERVERS)

@main_bp.route('/matchmaking')
@login_required
def matchmaking():
    """Matchmaking page"""
    user_servers = UserServer.query.filter_by(user_id=current_user.id).all()
    if not user_servers:
        flash('Сначала выберите серверы в профиле', 'warning')
        return redirect(url_for('main.profile'))
    
    return render_template('matchmaking.html',
                         modes=Config.GAME_MODES,
                         user_servers=user_servers)

@main_bp.route('/lobbies')
@login_required
def lobbies():
    """Public lobbies list"""
    page = request.args.get('page', 1, type=int)
    lobbies = Lobby.query.filter_by(is_public=True, status='open').paginate(page=page, per_page=20)
    
    return render_template('lobbies.html', lobbies=lobbies, all_servers=Config.SERVERS)

@main_bp.route('/lobby/<int:lobby_id>')
@login_required
def lobby_room(lobby_id):
    """View lobby room"""
    lobby = Lobby.query.get_or_404(lobby_id)
    
    # Check invite code from URL
    invite_code = request.args.get('invite')
    
    # Check if user is banned
    is_banned = LobbyBan.query.filter_by(lobby_id=lobby_id, user_id=current_user.id).first() is not None
    
    members = LobbyMember.query.filter_by(lobby_id=lobby_id).order_by(LobbyMember.joined_at).all()
    messages = LobbyMessage.query.filter_by(lobby_id=lobby_id).order_by(LobbyMessage.created_at).all()
    
    # Check if current user is member of this lobby
    is_member = LobbyMember.query.filter_by(lobby_id=lobby_id, user_id=current_user.id).first() is not None
    is_creator = lobby.creator_id == current_user.id
    
    if not is_member and not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    return render_template('lobby_room.html', 
                         lobby=lobby, 
                         members=members, 
                         messages=messages,
                         is_member=is_member,
                         is_creator=is_creator,
                         is_banned=is_banned,
                         invite_code=invite_code)

@main_bp.route('/support')
@login_required
def support():
    """Support tickets page"""
    page = request.args.get('page', 1, type=int)
    tickets = SupportTicket.query.filter_by(creator_id=current_user.id).paginate(page=page, per_page=10)
    
    return render_template('support/tickets.html', tickets=tickets)

@main_bp.route('/support/new', methods=['GET', 'POST'])
@login_required
def new_ticket():
    """Create new support ticket"""
    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'normal')
        
        if not subject or len(subject) < 5:
            flash('Заголовок должен быть минимум 5 символов', 'danger')
            return redirect(url_for('main.new_ticket'))
        
        if not description or len(description) < 10:
            flash('Описание должно быть минимум 10 символов', 'danger')
            return redirect(url_for('main.new_ticket'))
        
        ticket = SupportTicket(
            creator_id=current_user.id,
            subject=subject,
            description=description,
            priority=priority
        )
        db.session.add(ticket)
        db.session.commit()
        
        flash('Тикет создан', 'success')
        return redirect(url_for('main.support'))
    
    return render_template('support/new_ticket.html')

# ==================== ADMIN ROUTES ====================

@admin_bp.route('/dashboard')
@login_required
@admin_required(min_level=1)
def dashboard():
    """Admin dashboard"""
    stats = {
        'total_users': User.query.count(),
        'total_matches': Match.query.count(),
        'active_bans': Ban.query.filter_by(is_active=True).count(),
        'open_tickets': SupportTicket.query.filter_by(status='open').count(),
        'total_lobbies': Lobby.query.count(),
        'active_lobbies': Lobby.query.filter_by(status='open').count(),
    }
    
    recent_actions = AdminAction.query.order_by(AdminAction.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', stats=stats, recent_actions=recent_actions)

@admin_bp.route('/users')
@login_required
@admin_required(min_level=3)
def users():
    """User management"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = User.query
    if search:
        query = query.filter(User.username.ilike(f'%{search}%'))
    
    users = query.paginate(page=page, per_page=50)
    
    return render_template('admin/users.html', users=users, search=search)

@admin_bp.route('/user/<int:user_id>')
@login_required
@admin_required(min_level=3)
def user_detail(user_id):
    """User detail page"""
    user = User.query.get_or_404(user_id)
    servers = UserServer.query.filter_by(user_id=user_id).all()
    bans = Ban.query.filter_by(user_id=user_id).order_by(Ban.created_at.desc()).all()
    actions = AdminAction.query.filter_by(target_user_id=user_id).order_by(AdminAction.created_at.desc()).all()
    
    return render_template('admin/user_detail.html',
                         user=user,
                         servers=servers,
                         bans=bans,
                         actions=actions)

@admin_bp.route('/ban/<int:user_id>', methods=['POST'])
@login_required
@admin_required(min_level=2)
def ban_user(user_id):
    """Ban user"""
    user = User.query.get_or_404(user_id)
    reason = request.form.get('reason', '')
    ban_type = request.form.get('ban_type', 'temporary')
    duration_hours = int(request.form.get('duration_hours', 24))
    
    # Check admin level permissions
    if ban_type == 'permanent' and current_user.admin_level < 3:
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    # Create ban
    ban = Ban(
        user_id=user_id,
        admin_id=current_user.id,
        reason=reason,
        ban_type=ban_type,
        expires_at=datetime.utcnow() + timedelta(hours=duration_hours) if ban_type == 'temporary' else None
    )
    
    user.is_banned = True
    user.ban_expires = ban.expires_at
    
    # Log action
    action = AdminAction(
        admin_id=current_user.id,
        action='ban',
        target_user_id=user_id,
        reason=reason,
        details={'ban_type': ban_type, 'duration_hours': duration_hours}
    )
    
    db.session.add(ban)
    db.session.add(action)
    db.session.commit()
    
    flash(f'Пользователь {user.username} забанен', 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))

@admin_bp.route('/unban/<int:user_id>', methods=['POST'])
@login_required
@admin_required(min_level=3)
def unban_user(user_id):
    """Unban user"""
    user = User.query.get_or_404(user_id)
    
    user.is_banned = False
    user.ban_expires = None
    
    ban = Ban.query.filter_by(user_id=user_id, is_active=True).first()
    if ban:
        ban.is_active = False
    
    action = AdminAction(
        admin_id=current_user.id,
        action='unban',
        target_user_id=user_id
    )
    
    db.session.add(action)
    db.session.commit()
    
    flash(f'Пользователь {user.username} разбанен', 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))

@admin_bp.route('/assign-role/<int:user_id>', methods=['POST'])
@login_required
@admin_required(min_level=6)  # Only OWNER
def assign_role(user_id):
    """Assign admin role"""
    if current_user.admin_level != 6:
        return jsonify({'error': 'Только OWNER может назначать роли'}), 403
    
    user = User.query.get_or_404(user_id)
    new_role = int(request.form.get('admin_level', 0))
    reason = request.form.get('reason', '')
    
    old_role = user.admin_level
    user.admin_level = new_role
    
    action = AdminAction(
        admin_id=current_user.id,
        action='role_change',
        target_user_id=user_id,
        reason=reason,
        details={'old_role': old_role, 'new_role': new_role}
    )
    
    db.session.add(action)
    db.session.commit()
    
    flash(f'Роль пользователя {user.username} изменена', 'success')
    return redirect(url_for('admin.user_detail', user_id=user_id))

@admin_bp.route('/lobbies')
@login_required
@admin_required(min_level=1)
def admin_lobbies():
    """Admin page to manage lobbies"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    
    query = Lobby.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    lobbies = query.order_by(Lobby.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('admin/lobbies.html', 
                         lobbies=lobbies, 
                         status_filter=status_filter)

@admin_bp.route('/lobbies/<int:lobby_id>/delete', methods=['POST'])
@login_required
@admin_required(min_level=1)
def delete_lobby(lobby_id):
    """Delete a lobby (admin only)"""
    lobby = Lobby.query.get_or_404(lobby_id)
    lobby_name = lobby.name
    creator_username = lobby.creator.username if lobby.creator else 'Unknown'
    
    # Log admin action
    admin_action = AdminAction(
        admin_id=current_user.id,
        action='DELETE_LOBBY',
        target_user_id=lobby.creator_id,
        reason=f'Удалено лобби: {lobby_name}'
    )
    db.session.add(admin_action)
    
    # Delete related records (cascade should handle this, but explicit is better)
    LobbyMember.query.filter_by(lobby_id=lobby_id).delete()
    LobbyMessage.query.filter_by(lobby_id=lobby_id).delete()
    LobbyScreenshot.query.filter_by(lobby_id=lobby_id).delete()
    LobbyBan.query.filter_by(lobby_id=lobby_id).delete()
    LobbyInvite.query.filter_by(lobby_id=lobby_id).delete()
    
    # Delete lobby
    db.session.delete(lobby)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Лобби "{lobby_name}" успешно удалено'
    })

@admin_bp.route('/lobby-screenshots')
@login_required
@admin_required(min_level=1)
def lobby_screenshots():
    """Admin page to view lobby screenshots"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    
    query = LobbyScreenshot.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    screenshots = query.order_by(LobbyScreenshot.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('admin/lobby_screenshots.html', 
                         screenshots=screenshots, 
                         status_filter=status_filter)

@admin_bp.route('/lobby-screenshots/<int:screenshot_id>/review', methods=['POST'])
@login_required
@admin_required(min_level=1)
def review_lobby_screenshot(screenshot_id):
    """Review a lobby screenshot (approve/reject)"""
    screenshot = LobbyScreenshot.query.get_or_404(screenshot_id)
    data = request.get_json()
    
    action = data.get('action')  # 'approve' or 'reject'
    notes = data.get('notes', '')
    
    if action == 'approve':
        screenshot.status = 'approved'
        # Обновляем статистику пользователя
        user = screenshot.user
        if screenshot.result == 'win':
            user.update_ggp(Config.GGP_WIN)
            for server in user.servers:
                server.wins += 1
        elif screenshot.result == 'loss':
            user.update_ggp(Config.GGP_LOSS)
            for server in user.servers:
                server.losses += 1
        
        # Удаляем лобби после одобрения результата
        lobby = screenshot.lobby
        if lobby:
            # Удаляем все связанные записи
            LobbyMember.query.filter_by(lobby_id=lobby.id).delete()
            LobbyMessage.query.filter_by(lobby_id=lobby.id).delete()
            LobbyScreenshot.query.filter_by(lobby_id=lobby.id).delete()
            LobbyBan.query.filter_by(lobby_id=lobby.id).delete()
            LobbyInvite.query.filter_by(lobby_id=lobby.id).delete()
            # Удаляем само лобби
            db.session.delete(lobby)
    elif action == 'reject':
        screenshot.status = 'rejected'
        # Удаляем лобби при отклонении результата
        lobby = screenshot.lobby
        if lobby:
            # Удаляем все связанные записи
            LobbyMember.query.filter_by(lobby_id=lobby.id).delete()
            LobbyMessage.query.filter_by(lobby_id=lobby.id).delete()
            LobbyScreenshot.query.filter_by(lobby_id=lobby.id).delete()
            LobbyBan.query.filter_by(lobby_id=lobby.id).delete()
            LobbyInvite.query.filter_by(lobby_id=lobby.id).delete()
            # Удаляем само лобби
            db.session.delete(lobby)
    else:
        return jsonify({'success': False, 'error': 'Invalid action'}), 400
    
    # Удаляем физический файл скриншота
    if screenshot.image_path:
        screenshot_file_path = os.path.join(Config.UPLOAD_FOLDER, screenshot.image_path)
        try:
            if os.path.exists(screenshot_file_path):
                os.remove(screenshot_file_path)
        except Exception as e:
            print(f"Ошибка при удалении файла {screenshot_file_path}: {e}")
    
    screenshot.reviewed_by = current_user.id
    screenshot.reviewed_at = datetime.utcnow()
    screenshot.notes = notes
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Screenshot {action}d successfully'})

@admin_bp.route('/tickets')
@login_required
@admin_required(min_level=1)
def support_tickets():
    """Support tickets management"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'open')
    
    query = SupportTicket.query
    if status != 'all':
        query = query.filter_by(status=status)
    
    tickets = query.order_by(SupportTicket.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('admin/tickets.html', tickets=tickets, status=status)

@admin_bp.route('/ticket/<int:ticket_id>')
@login_required
@admin_required(min_level=1)
def ticket_detail(ticket_id):
    """Support ticket detail"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    messages = SupportMessage.query.filter_by(ticket_id=ticket_id).order_by(SupportMessage.created_at).all()
    
    return render_template('admin/ticket_detail.html', ticket=ticket, messages=messages)

@admin_bp.route('/ticket/<int:ticket_id>/message', methods=['POST'])
@login_required
@admin_required(min_level=1)
def admin_add_ticket_message(ticket_id):
    """Add message to ticket from admin"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    message_text = request.form.get('message', '').strip()
    
    if not message_text:
        flash('Сообщение не может быть пустым', 'danger')
        return redirect(url_for('admin.ticket_detail', ticket_id=ticket_id))
    
    message = SupportMessage(
        ticket_id=ticket_id,
        user_id=current_user.id,
        message=message_text
    )
    db.session.add(message)
    ticket.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash('Сообщение отправлено', 'success')
    return redirect(url_for('admin.ticket_detail', ticket_id=ticket_id))

# ==================== API ROUTES ====================

@api_bp.route('/user/profile', methods=['GET'])
@api_login_required
def api_get_profile():
    """Get user profile"""
    user = current_user
    user_servers = UserServer.query.filter_by(user_id=user.id).all()
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'ggp': user.ggp,
        'level': user.level,
        'admin_level': user.admin_level,
        'servers': [
            {
                'name': s.server_name,
                'nickname': s.server_nickname,
                'wins': s.wins,
                'losses': s.losses,
                'winrate': s.get_winrate()
            } for s in user_servers
        ]
    })

@api_bp.route('/user/update', methods=['POST'])
@api_login_required
def api_update_profile():
    """Update user profile"""
    data = request.get_json()
    
    user = current_user
    if 'email' in data:
        user.email = data['email']
    
    db.session.commit()
    
    return jsonify({'success': True})

@api_bp.route('/friends/add', methods=['POST'])
@api_login_required
def api_add_friend():
    """Add friend"""
    data = request.get_json()
    friend_id = data.get('friend_id')
    
    friend = User.query.get(friend_id)
    if not friend:
        return jsonify({'error': 'User not found'}), 404
    
    current_user.add_friend(friend)
    
    return jsonify({'success': True})

@api_bp.route('/friends/remove', methods=['POST'])
@api_login_required
def api_remove_friend():
    """Remove friend"""
    data = request.get_json()
    friend_id = data.get('friend_id')
    
    current_user.remove_friend(User.query.get(friend_id))
    
    return jsonify({'success': True})

@api_bp.route('/match/search', methods=['POST'])
@api_login_required
def api_search_match():
    """Search for opponent"""
    data = request.get_json()
    mode = data.get('mode', '').strip()
    server = data.get('server', '').strip()
    
    # Validate mode
    if mode not in Config.GAME_MODES:
        return jsonify({'error': f'Invalid mode: {mode}'}), 400
    
    # Validate server with case-insensitive check
    valid_servers = [s.strip() for s in Config.SERVERS]
    server_lower = server.lower().strip()
    valid_servers_lower = [s.lower() for s in valid_servers]
    
    if server_lower not in valid_servers_lower:
        matching_servers = [s for s in valid_servers if s.lower() == server_lower]
        if matching_servers:
            server = matching_servers[0]
        else:
            return jsonify({'error': f'Invalid server: {server}'}), 400
    
    # Find similar GGP players
    ggp_min = max(0, current_user.ggp - Config.GGP_RANGE)
    ggp_max = current_user.ggp + Config.GGP_RANGE
    
    opponents = User.query.filter(
        User.ggp.between(ggp_min, ggp_max),
        User.id != current_user.id
    ).all()
    
    return jsonify({
        'opponents_count': len(opponents),
        'mode': mode,
        'server': server
    })

@api_bp.route('/party/create', methods=['POST'])
@api_login_required
def api_create_party():
    """Create party"""
    data = request.get_json()
    mode = data.get('mode')
    server = data.get('server')
    
    if mode not in Config.GAME_MODES or server not in Config.SERVERS:
        return jsonify({'error': 'Invalid mode or server'}), 400
    
    party = Party(
        leader_id=current_user.id,
        mode=mode,
        server=server
    )
    
    member = PartyMember(user_id=current_user.id)
    party.members.append(member)
    
    db.session.add(party)
    db.session.commit()
    
    return jsonify({
        'party_id': party.id,
        'leader_id': party.leader_id,
        'mode': party.mode,
        'server': party.server
    })

@api_bp.route('/party/<int:party_id>/invite', methods=['POST'])
@api_login_required
def api_invite_party(party_id):
    """Invite user to party"""
    party = Party.query.get_or_404(party_id)
    
    if party.leader_id != current_user.id:
        return jsonify({'error': 'You are not party leader'}), 403
    
    data = request.get_json()
    friend_id = data.get('friend_id')
    
    friend = User.query.get(friend_id)
    if not friend:
        return jsonify({'error': 'User not found'}), 404
    
    max_size = Config.MAX_PARTY_SIZE.get(party.mode, 1)
    if len(party.members) >= max_size:
        return jsonify({'error': 'Party is full'}), 400
    
    member = PartyMember(party_id=party_id, user_id=friend_id)
    db.session.add(member)
    db.session.commit()
    
    return jsonify({'success': True})

@api_bp.route('/admin/ban', methods=['POST'])
@api_login_required
@admin_required(min_level=2)
def api_ban_user():
    """API ban user"""
    data = request.get_json()
    user_id = data.get('user_id')
    reason = data.get('reason', '')
    ban_type = data.get('ban_type', 'temporary')
    duration_hours = data.get('duration_hours', 24)
    
    return ban_user(user_id)

@api_bp.route('/admin/users', methods=['GET'])
@api_login_required
@admin_required(min_level=3)
def api_get_users():
    """Get users list for admin"""
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=50)
    
    return jsonify({
        'users': [
            {
                'id': u.id,
                'username': u.username,
                'ggp': u.ggp,
                'level': u.level,
                'admin_level': u.admin_level,
                'is_banned': u.is_banned
            } for u in users.items
        ],
        'total': users.total,
        'pages': users.pages
    })

# ==================== SUPPORT TICKET MESSAGES ====================

@main_bp.route('/support/ticket/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def view_ticket(ticket_id):
    """View support ticket detail and add messages"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    # Check if user is creator or admin
    if current_user.id != ticket.creator_id and current_user.admin_level < 1:
        flash('У вас нет доступа к этому тикету', 'danger')
        return redirect(url_for('main.support'))
    
    if request.method == 'POST':
        message_text = request.form.get('message', '').strip()
        
        if not message_text:
            flash('Сообщение не может быть пустым', 'danger')
            return redirect(url_for('main.view_ticket', ticket_id=ticket_id))
        
        # Add message
        message = SupportMessage(
            ticket_id=ticket_id,
            user_id=current_user.id,
            message=message_text
        )
        db.session.add(message)
        
        # Update ticket timestamp
        ticket.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Сообщение отправлено', 'success')
        return redirect(url_for('main.view_ticket', ticket_id=ticket_id))
    
    messages = SupportMessage.query.filter_by(ticket_id=ticket_id).order_by(SupportMessage.created_at).all()
    return render_template('support/ticket_detail.html', ticket=ticket, messages=messages)

@admin_bp.route('/ticket/<int:ticket_id>/status', methods=['POST'])
@login_required
@admin_required(min_level=1)
def update_ticket_status(ticket_id):
    """Update support ticket status"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    status = request.form.get('status', '')
    if status not in ['open', 'in_progress', 'resolved', 'closed']:
        return jsonify({'error': 'Invalid status'}), 400
    
    ticket.status = status
    ticket.updated_at = datetime.utcnow()
    
    # If assigning to admin
    if status == 'in_progress' and ticket.assigned_to_id is None:
        ticket.assigned_to_id = current_user.id
    
    if status == 'resolved':
        ticket.resolved_at = datetime.utcnow()
    
    db.session.commit()
    flash(f'Статус тикета изменён на {status}', 'success')
    return redirect(url_for('admin.ticket_detail', ticket_id=ticket_id))

@api_bp.route('/ticket/<int:ticket_id>/message', methods=['POST'])
@api_login_required
def api_add_ticket_message(ticket_id):
    """Add message to ticket via API"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    # Check if user is creator or admin
    if current_user.id != ticket.creator_id and current_user.admin_level < 1:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    message_text = data.get('message', '').strip()
    
    if not message_text:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    message = SupportMessage(
        ticket_id=ticket_id,
        user_id=current_user.id,
        message=message_text
    )
    db.session.add(message)
    ticket.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message_id': message.id,
        'username': current_user.username,
        'created_at': message.created_at.isoformat()
    })

@api_bp.route('/ticket/<int:ticket_id>/status', methods=['POST'])
@api_login_required
def api_update_ticket_status(ticket_id):
    """Update ticket status via API"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    # Check if user is creator or admin
    if current_user.id != ticket.creator_id and current_user.admin_level < 1:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    status = data.get('status', '')
    
    if status not in ['open', 'in_progress', 'resolved', 'closed']:
        return jsonify({'error': 'Invalid status'}), 400
    
    ticket.status = status
    ticket.updated_at = datetime.utcnow()
    
    if status == 'in_progress' and ticket.assigned_to_id is None:
        ticket.assigned_to_id = current_user.id
    
    if status == 'resolved':
        ticket.resolved_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'success': True, 'status': status})

# ==================== LOBBY CREATION ====================

@api_bp.route('/lobby/create', methods=['POST'])
@api_login_required
def api_create_lobby():
    """Create a new lobby"""
    data = request.get_json()
    
    name = data.get('name', '').strip()
    mode = data.get('mode', '').strip()
    server = data.get('server', '').strip()
    max_players = data.get('max_players', 4)
    is_public = data.get('is_public', True)
    password = data.get('password', '')
    
    # Validation
    if not name or len(name) < 3:
        return jsonify({'error': 'Название лобби должно быть минимум 3 символа'}), 400
    
    if mode not in Config.GAME_MODES:
        return jsonify({'error': f'Неверный режим: {mode}'}), 400
    
    # Server validation with better error handling
    valid_servers = [s.strip() for s in Config.SERVERS]
    server_lower = server.lower().strip()
    valid_servers_lower = [s.lower() for s in valid_servers]
    
    if server_lower not in valid_servers_lower:
        # Find the actual server name with correct case
        matching_servers = [s for s in valid_servers if s.lower() == server_lower]
        if matching_servers:
            server = matching_servers[0]
        else:
            return jsonify({'error': f'Неверный сервер: {server}'}), 400
    
    if max_players < 2 or max_players > 10:
        return jsonify({'error': 'Max players must be between 2 and 10'}), 400
    
    # Create lobby
    lobby = Lobby(
        name=name,
        creator_id=current_user.id,
        mode=mode,
        server=server,
        is_public=is_public,
        password=password,
        max_players=max_players,
        current_players=1,
        status='open'
    )
    
    db.session.add(lobby)
    db.session.flush()  # Get the lobby ID
    
    # Add creator as member
    creator_member = LobbyMember(lobby_id=lobby.id, user_id=current_user.id)
    db.session.add(creator_member)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'lobby_id': lobby.id,
        'name': lobby.name,
        'mode': lobby.mode,
        'server': lobby.server,
        'redirect_url': url_for('main.lobby_room', lobby_id=lobby.id)
    })

@api_bp.route('/lobby/<int:lobby_id>/join', methods=['POST'])
@api_login_required
def api_join_lobby(lobby_id):
    """Join a lobby"""
    lobby = Lobby.query.get_or_404(lobby_id)
    data = request.get_json() or {}
    
    # Check if user is banned from this lobby
    ban = LobbyBan.query.filter_by(lobby_id=lobby_id, user_id=current_user.id).first()
    if ban:
        return jsonify({'error': 'Вы забанены в этом лобби'}), 403
    
    if lobby.status == 'full':
        return jsonify({'error': 'Лобби заполнено'}), 400
    
    if lobby.status == 'started':
        return jsonify({'error': 'Лобби уже началось'}), 400
    
    # Check invite code if provided
    invite_code = data.get('invite_code')
    if invite_code:
        invite = LobbyInvite.query.filter_by(invite_code=invite_code, lobby_id=lobby_id).first()
        if not invite:
            return jsonify({'error': 'Неверный код приглашения'}), 400
        if invite.expires_at and invite.expires_at < datetime.utcnow():
            return jsonify({'error': 'Срок действия приглашения истек'}), 400
        if invite.max_uses and invite.uses_count >= invite.max_uses:
            return jsonify({'error': 'Достигнут лимит использований приглашения'}), 400
    
    if not lobby.is_public and not invite_code:
        password = data.get('password', '')
        if password != lobby.password:
            return jsonify({'error': 'Неправильный пароль'}), 401
    
    # Check if already member - allow rejoin if they left
    existing_member = LobbyMember.query.filter_by(lobby_id=lobby_id, user_id=current_user.id).first()
    if existing_member:
        # User is already a member, return success to allow rejoin
        return jsonify({
            'success': True,
            'message': 'Вы уже в этом лобби',
            'lobby_id': lobby_id
        })
    
    # Add player as member
    member = LobbyMember(lobby_id=lobby_id, user_id=current_user.id)
    db.session.add(member)
    
    lobby.current_players += 1
    if lobby.current_players >= lobby.max_players:
        lobby.status = 'full'
    
    # Update invite usage if used
    if invite_code and invite:
        invite.uses_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'current_players': lobby.current_players,
        'status': lobby.status,
        'redirect_url': url_for('main.lobby_room', lobby_id=lobby_id)
    })

@api_bp.route('/lobby/<int:lobby_id>/invite', methods=['GET', 'POST'])
@api_login_required
def api_lobby_invite(lobby_id):
    """Get invite code and URL for lobby"""
    lobby = Lobby.query.get_or_404(lobby_id)
    
    # Проверяем, что пользователь является участником лобби
    is_member = LobbyMember.query.filter_by(
        lobby_id=lobby_id,
        user_id=current_user.id
    ).first()
    
    if not is_member:
        return jsonify({
            'success': False,
            'error': 'Вы не являетесь участником этого лобби'
        }), 403
    
    # Создаем invite code если его нет
    if not lobby.invite_code:
        import secrets
        lobby.invite_code = secrets.token_urlsafe(8)
        db.session.commit()
    
    invite_url = url_for('main.lobby_room', lobby_id=lobby.id, _external=True)
    if lobby.invite_code:
        invite_url += f'?invite={lobby.invite_code}'
    
    return jsonify({
        'success': True,
        'invite_code': lobby.invite_code,
        'invite_url': invite_url
    })

@api_bp.route('/lobby/<int:lobby_id>/message', methods=['POST'])
@api_login_required
def api_lobby_message(lobby_id):
    """Send message in lobby"""
    lobby = Lobby.query.get_or_404(lobby_id)
    
    # Check if user is member
    is_member = LobbyMember.query.filter_by(lobby_id=lobby_id, user_id=current_user.id).first()
    if not is_member:
        return jsonify({'error': 'Вы не в этом лобби'}), 403
    
    data = request.get_json()
    message_text = data.get('message', '').strip()
    
    if not message_text or len(message_text) < 1:
        return jsonify({'error': 'Сообщение не может быть пустым'}), 400
    
    message = LobbyMessage(lobby_id=lobby_id, user_id=current_user.id, message=message_text)
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message_id': message.id,
        'username': current_user.username,
        'message': message_text,
        'created_at': message.created_at.isoformat()
    })

# ==================== MAJESTIC SCREENSHOT ANALYSIS ====================

@api_bp.route('/analyze-screenshot', methods=['POST'])
@api_login_required
def api_analyze_screenshot():
    """
    Анализирует скриншот из Majestic RP для считывания статистики
    POST данные:
    {
        'image_base64': 'base64 encoded image',  # опционально
        'result': 'win' or 'loss',  # результат матча
        'lobby_id': int  # ID лобби (опционально)
    }
    """
    try:
        from app.screenshot_analyzer import MajesticScreenAnalyzer
        import base64
        from PIL import Image
        from io import BytesIO
        import os
        
        analyzer = MajesticScreenAnalyzer()
        
        # Получаем данные из запроса
        data = request.get_json()
        if not data or 'image_base64' not in data:
            return jsonify({
                'success': False,
                'error': 'Изображение не предоставлено'
            }), 400
        
        # Декодируем изображение
        image_data = base64.b64decode(data['image_base64'])
        image = Image.open(BytesIO(image_data))
        analyzer.last_screenshot = image
        
        # Получаем результат и lobby_id
        result_status = data.get('result', 'win')  # win or loss
        lobby_id = data.get('lobby_id')
        
        # Сохраняем скриншот, если передан lobby_id
        screenshot_path = None
        if lobby_id:
            # Проверяем, что лобби существует и пользователь является участником
            lobby = Lobby.query.get(lobby_id)
            if not lobby:
                return jsonify({
                    'success': False,
                    'error': 'Лобби не найдено'
                }), 404
            
            # Проверяем, что пользователь является участником лобби
            is_member = LobbyMember.query.filter_by(
                lobby_id=lobby_id,
                user_id=current_user.id
            ).first()
            
            if not is_member:
                return jsonify({
                    'success': False,
                    'error': 'Вы не являетесь участником этого лобби'
                }), 403
            
            # Создаем директорию для скриншотов, если её нет
            upload_dir = os.path.join(Config.UPLOAD_FOLDER, 'lobby_screenshots')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Сохраняем изображение
            filename = f"lobby_{lobby_id}_user_{current_user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
            screenshot_path = os.path.join(upload_dir, filename)
            image.save(screenshot_path)
            
            # Сохраняем относительный путь для базы данных (с прямыми слэшами для кроссплатформности)
            relative_path = f'lobby_screenshots/{filename}'
            
            # Сохраняем запись в базе данных
            screenshot = LobbyScreenshot(
                lobby_id=lobby_id,
                user_id=current_user.id,
                result=result_status,
                image_path=relative_path,
                status='pending'
            )
            db.session.add(screenshot)
            db.session.commit()
        
        # Анализируем изображение (опционально, для обратной совместимости)
        try:
            analysis_result = analyzer.analyze_screenshot()
            validation = analyzer.validate_result(analysis_result)
        except:
            analysis_result = {}
            validation = {'is_valid': False}
        
        return jsonify({
            'success': True,
            'message': 'Скриншот отправлен на проверку админам',
            'analysis': {
                'status': analysis_result.get('status'),
                'ggp_change': analysis_result.get('ggp_change'),
                'wins': analysis_result.get('wins'),
                'losses': analysis_result.get('losses'),
                'confidence': analysis_result.get('confidence'),
                'raw_text': analysis_result.get('raw_text')[:500] if analysis_result.get('raw_text') else None
            } if analysis_result else None,
            'validation': validation
        })
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Модуль pytesseract не установлен. Выполните: pip install pytesseract pillow'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@main_bp.route('/screenshot-stats')
@login_required
def screenshot_stats():
    """Страница для просмотра анализа скриншотов"""
    return render_template('screenshot_stats.html')


