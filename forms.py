from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional, NumberRange
from database import User

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(message="Введите имя пользователя")
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message="Введите пароль")
    ])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class RegisterForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(message="Введите имя пользователя"),
        Length(min=3, max=64, message="Имя пользователя должно быть от 3 до 64 символов")
    ])
    email = StringField('Email', validators=[
        DataRequired(message="Введите email"),
        Email(message="Введите корректный email", check_deliverability=False)
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(message="Введите пароль"),
        Length(min=6, message="Пароль должен быть не менее 6 символов")
    ])
    confirm_password = PasswordField('Подтвердите пароль', validators=[
        DataRequired(message="Подтвердите пароль"),
        EqualTo('password', message="Пароли не совпадают")
    ])
    submit = SubmitField('Зарегистрироваться')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Это имя пользователя уже занято')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Этот email уже используется')

class ServerInfoForm(FlaskForm):
    server_name = SelectField('Сервер', choices=[], validators=[DataRequired()])
    nickname = StringField('Ник на сервере', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    submit = SubmitField('Сохранить')

class LobbyForm(FlaskForm):
    name = StringField('Название лобби', validators=[
        DataRequired(),
        Length(min=3, max=100)
    ])
    password = PasswordField('Пароль (опционально)', validators=[
        Optional(),
        Length(min=4, max=50)
    ])
    match_type = SelectField('Тип матча', choices=[
        ('1x1', '1x1 - Дуэль'),
        ('2x2', '2x2 - Командный бой'),
        ('3x3', '3x3 - Командный бой'),
        ('5x5', '5x5 - Командный бой')
    ], validators=[DataRequired()])
    server = SelectField('Сервер', validators=[DataRequired()])
    submit = SubmitField('Создать лобби')

class MatchForm(FlaskForm):
    match_type = SelectField('Тип матча', choices=[
        ('1x1', '1x1'),
        ('2x2', '2x2'),
        ('3x3', '3x3'),
        ('5x5', '5x5')
    ], validators=[DataRequired()])
    server = SelectField('Сервер', choices=[], validators=[DataRequired()])
    submit = SubmitField('Начать поиск')

class SupportTicketForm(FlaskForm):
    subject = StringField('Тема', validators=[
        DataRequired(message="Введите тему обращения"),
        Length(min=5, max=200, message="Тема должна быть от 5 до 200 символов")
    ])
    message = TextAreaField('Сообщение', validators=[
        DataRequired(message="Введите сообщение"),
        Length(min=10, max=5000, message="Сообщение должно быть от 10 до 5000 символов")
    ])
    category = SelectField('Категория', choices=[
        ('bug', 'Ошибка/Баг'),
        ('suggestion', 'Предложение'),
        ('question', 'Вопрос'),
        ('account', 'Аккаунт'),
        ('match', 'Проблема с матчем'),
        ('other', 'Другое')
    ], validators=[DataRequired()])
    priority = SelectField('Приоритет', choices=[
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий')
    ], default='medium')
    submit = SubmitField('Отправить')