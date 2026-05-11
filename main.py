from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, City, GameResult
from io import BytesIO
import base64
import random
import os
import uuid
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Создаём папку для аватарок
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Пользователь уже существует', 'danger')
            return redirect(url_for('register'))
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Регистрация успешна!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Неверный логин или пароль', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/profile')
@login_required
def profile():
    results = GameResult.query.filter_by(user_id=current_user.id) \
        .order_by(GameResult.date_played.desc()).limit(20).all()

    print(f"DEBUG PROFILE: user_id={current_user.id}, игр={len(results)}")
    chart = generate_score_chart(current_user.id)
    print(f"DEBUG PROFILE: chart={'OK' if chart else 'None'}")
    return render_template('profile.html', user=current_user, results=results, chart=chart)


@app.route('/profile/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('Файл не выбран', 'danger')
        return redirect(url_for('profile'))

    file = request.files['avatar']
    if file.filename == '':
        flash('Файл не выбран', 'danger')
        return redirect(url_for('profile'))

    if file and allowed_file(file.filename):
        # Удаляем старый аватар,если не дефолтный
        if current_user.avatar != 'default.png':
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.avatar)
            if os.path.exists(old_path):
                os.remove(old_path)

        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        current_user.avatar = filename
        db.session.commit()
        flash('Аватар обновлён!', 'success')
    else:
        flash('Разрешены только PNG, JPG, GIF', 'danger')

    return redirect(url_for('profile'))


# реализация самой игры

@app.route('/game/start')
@login_required
def start_game():
    cities = City.query.all()
    if len(cities) < 10:
        flash('Недостаточно городов. Запустите fill_cities.py', 'warning')
        return redirect(url_for('index'))
    game_cities = random.sample(cities, 10)
    session['game'] = {
        'city_ids': [c.id for c in game_cities],
        'current_index': 0,
        'score': 0.0
    }
    return redirect(url_for('play_round'))


@app.route('/game/play')
@login_required
def play_round():
    game = session.get('game')
    if not game or game['current_index'] >= len(game['city_ids']):
        return redirect(url_for('game_result'))

    city = City.query.get(game['city_ids'][game['current_index']])
    map_url = f"https://static-maps.yandex.ru/1.x/?ll={city.lon},{city.lat}&z=14&size=650,450&l=map&lang=en_US&apikey={app.config['YANDEX_STATIC_KEY']}"
    return render_template('game.html',
                           round_number=game['current_index'] + 1,
                           map_url=map_url)


@app.route('/game/guess', methods=['POST'])
@login_required
def guess():
    game = session.get('game')
    if not game:
        return redirect(url_for('index'))

    city = City.query.get(game['city_ids'][game['current_index']])
    user_guess = request.form.get('guess', '').strip().lower()

    points = 0.0
    guess_type = None

    if user_guess == city.name.lower():
        points = 1.0
        guess_type = 'city'
    elif user_guess == city.country.lower():
        points = 0.5
        guess_type = 'country'
    elif user_guess == city.continent.lower():
        points = 0.25
        guess_type = 'continent'

    game['score'] += points
    game['current_index'] += 1
    session['game'] = game

    return render_template('game.html',
                           round_number=game['current_index'],
                           last_result={
                               'correct': guess_type is not None,
                               'city': city.name,
                               'country': city.country,
                               'continent': city.continent,
                               'points': points,
                               'guess_type': guess_type
                           })


@app.route('/game/next')
@login_required
def next_round():
    game = session.get('game')
    if game and game['current_index'] < len(game['city_ids']):
        return redirect(url_for('play_round'))
    return redirect(url_for('game_result'))


@app.route('/game/result')
@login_required
def game_result():
    game = session.get('game')
    if not game:
        return redirect(url_for('profile'))

    final_score = game['score']
    result = GameResult(user_id=current_user.id, score=final_score)
    db.session.add(result)
    if final_score > current_user.best_score:
        current_user.best_score = final_score
    db.session.commit()
    session.pop('game', None)

    return render_template('result.html', final_score=final_score)


def generate_score_chart(user_id):
    results = GameResult.query.filter_by(user_id=user_id) \
        .order_by(GameResult.date_played.asc()).all()

    print(f"DEBUG: Найдено {len(results)} игр для user_id={user_id}")

    if len(results) < 2:
        return None

    dates = []
    scores = []
    for r in results:
        dates.append(r.date_played.strftime('%d.%m'))
        scores.append(r.score)

    # Динамика результатов в профиле
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(range(len(scores)), scores, 'b-o', linewidth=2, markersize=8)
    ax.set_xticks(range(len(dates)))
    ax.set_xticklabels(dates, rotation=45)
    ax.set_ylim(0, max(10.5, max(scores) + 1))
    ax.set_ylabel('Очки')
    ax.set_xlabel('Дата')
    ax.set_title('Динамика результатов')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    plt.close()
    buf.seek(0)

    return base64.b64encode(buf.getvalue()).decode('utf-8')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
