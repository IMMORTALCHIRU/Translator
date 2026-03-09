from flask import Flask, jsonify, session
from flask_pymongo import PyMongo
from config import Config
from routes.auth import init_auth_routes, login_required
from routes.main import main_bp
from routes.translation import init_translation_routes
from routes.genz_translation import init_genz_routes
import os
import certifi

# Ensure Python/urllib uses the certifi CA bundle for SSL verification.
os.environ.setdefault('SSL_CERT_FILE', certifi.where())

from utils.translator import SpeechTranslator
from utils.genz_translator import GenZTranslator
from utils.audio_processor import AudioProcessor

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize MongoDB
mongo = PyMongo(app)

# Create upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize translators and processors (preload models)
speech_translator = SpeechTranslator()
genz_translator = GenZTranslator()
audio_processor = AudioProcessor()

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(init_auth_routes(mongo), url_prefix='/auth')
app.register_blueprint(init_translation_routes(mongo, speech_translator, audio_processor))
app.register_blueprint(init_genz_routes(mongo, speech_translator, audio_processor, genz_translator))

# Context processor for templates
@app.context_processor
def inject_user():
    return dict(session=session)

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("GenZ Speech Translator")
    print("=" * 50)
    print("Starting Flask application...")
    print(f"Environment: {'Development' if app.debug else 'Production'}")
    print(f"MongoDB: {app.config['MONGO_URI']}")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)