from flask import Blueprint, render_template, session
from routes.auth import login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/translate')
@login_required
def translate():
    return render_template('translate.html')