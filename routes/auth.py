from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.user import User
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def init_auth_routes(mongo):
    user_model = User(mongo)
    
    @auth_bp.route('/register', methods=['GET', 'POST'])
    def register():
        if 'user_id' in session:
            return redirect(url_for('main.translate'))
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validation
            if not username or not email or not password:
                flash('All fields are required.', 'danger')
                return render_template('register.html')
            
            if len(username) < 3:
                flash('Username must be at least 3 characters long.', 'danger')
                return render_template('register.html')
            
            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'danger')
                return render_template('register.html')
            
            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('register.html')
            
            # Check if user already exists
            if user_model.find_by_email(email):
                flash('Email already registered.', 'danger')
                return render_template('register.html')
            
            if user_model.find_by_username(username):
                flash('Username already taken.', 'danger')
                return render_template('register.html')
            
            # Create user
            user_id = user_model.create_user(username, email, password)
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        
        return render_template('register.html')
    
    @auth_bp.route('/login', methods=['GET', 'POST'])
    def login():
        if 'user_id' in session:
            return redirect(url_for('main.translate'))
        
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            
            if not email or not password:
                flash('Please enter both email and password.', 'danger')
                return render_template('login.html')
            
            user = user_model.find_by_email(email)
            
            if user and user_model.verify_password(user, password):
                session['user_id'] = str(user['_id'])
                session['username'] = user['username']
                session.permanent = True
                
                user_model.update_last_login(user['_id'])
                
                flash(f'Welcome back, {user["username"]}!', 'success')
                return redirect(url_for('main.translate'))
            else:
                flash('Invalid email or password.', 'danger')
                return render_template('login.html')
        
        return render_template('login.html')
    
    @auth_bp.route('/logout')
    def logout():
        session.clear()
        flash('You have been logged out successfully.', 'info')
        return redirect(url_for('main.index'))
    
    return auth_bp