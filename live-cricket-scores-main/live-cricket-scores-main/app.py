import os
from flask import Flask, render_template, redirect, url_for, flash, request
import feedparser
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysupersecretkey123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cricket_db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    favorites = db.relationship('FavoriteTeam', backref='user', lazy=True)

class FavoriteTeam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    team_name = db.Column(db.String(100), nullable=False)
    note = db.Column(db.String(255), default="Add a prediction...")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

RSS_FEED_URL = "https://static.cricinfo.com/rss/livescores.xml"

@app.route('/')
def index():
    feed = feedparser.parse(RSS_FEED_URL, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
    match_keywords = [
        'pakistan', 'lahore', 'karachi', 'islamabad', 'peshawar', 'quetta', 'multan', 'rawalpindi',
        'psl', 'qalandars', 'kings', 'united', 'zalmi', 'gladiators', 'sultans', 'kingsmen', 'lq', 'hhk',
        'india', 'australia', 'england', 'south africa', 'sri lanka', 'bangladesh', 'new zealand', 'west indies',
        'afghanistan', 'ireland', 'icc', 'world cup', 't20', 'odi', 'test', 'ipl', 'bbl', 'cpl'
    ]
    filtered_entries = []
    
    for entry in feed.entries:
        title_lower = entry.title.lower()
        desc_lower = entry.description.lower()
        if any(keyword in title_lower or keyword in desc_lower for keyword in match_keywords):
            filtered_entries.append(entry)
            
    return render_template('index.html', feed=feed, entries=filtered_entries)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please login.', 'danger')
            return redirect(url_for('register'))
        
        is_first_user = User.query.count() == 0
        new_user = User(
            username=username, 
            password_hash=generate_password_hash(password),
            is_admin=is_first_user
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login unsuccessful. Please check username and password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/add_favorite', methods=['POST'])
@login_required
def add_favorite():
    team_name = request.form.get('team_name')
    if team_name:
        new_fav = FavoriteTeam(team_name=team_name, user_id=current_user.id)
        db.session.add(new_fav)
        db.session.commit()
        flash(f'Match Inserted into Database! (CRUD: Create)', 'success')
    return redirect(url_for('index'))

@app.route('/update_note/<int:fav_id>', methods=['POST'])
@login_required
def update_note(fav_id):
    fav = db.session.get(FavoriteTeam, fav_id)
    if fav and fav.user_id == current_user.id:
        new_note = request.form.get('note')
        fav.note = new_note
        db.session.commit()
        flash('Record updated successfully! (CRUD: Update)', 'success')
    return redirect(url_for('index'))

@app.route('/remove_favorite/<int:fav_id>', methods=['POST'])
@login_required
def remove_favorite(fav_id):
    fav = db.session.get(FavoriteTeam, fav_id)
    if fav and fav.user_id == current_user.id:
        db.session.delete(fav)
        db.session.commit()
        flash('Record deleted. (CRUD: Delete)', 'danger')
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('Access Denied. Admins only.', 'danger')
        return redirect(url_for('index'))
        
    all_users = User.query.all()
    all_favorites = FavoriteTeam.query.all()
    return render_template('admin.html', users=all_users, favorites=all_favorites)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
