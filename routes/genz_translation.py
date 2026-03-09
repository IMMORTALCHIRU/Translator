from flask import Blueprint, request, jsonify, session, render_template
from routes.auth import login_required
from models.user import Translation
from utils.translator import SpeechTranslator
from utils.audio_processor import AudioProcessor
from utils.genz_translator import GenZTranslator

genz_bp = Blueprint('genz', __name__)

def init_genz_routes(mongo, speech_translator, audio_processor, genz_translator):
    translation_model = Translation(mongo)
    
    @genz_bp.route('/genz-translate')
    @login_required
    def genz_translate():
        return render_template('genz_translate.html')
    
    @genz_bp.route('/api/genz/translate-text', methods=['POST'])
    @login_required
    def translate_text():
        """Translate GenZ slang text to English or vice versa"""
        try:
            data = request.get_json()
            if data is None:
                return jsonify({'success': False, 'error': 'Invalid or missing JSON body'}), 400
            text = data.get('text', '').strip()
            mode = data.get('mode', 'auto')  # auto, to_english, to_genz
            
            if not text:
                return jsonify({'success': False, 'error': 'No text provided'}), 400
            
            # Use bidirectional translation with auto-detection
            result = genz_translator.bidirectional_translate(text, target_mode=mode)
            
            # Save to database
            translation_model.save_translation(
                user_id=session['user_id'],
                original_text=result['original_text'],
                translated_text=result.get('translated_text', ''),
                source_lang='genz' if result.get('detected_mode') == 'slang_to_english' else 'en',
                target_lang='en' if result.get('detected_mode') == 'slang_to_english' else 'genz'
            )
            
            return jsonify({
                'success': True,
                'original_text': result['original_text'],
                'translated_text': result.get('translated_text', ''),
                'explanations': result.get('explanations', []),
                'substitutions': result.get('substitutions', []),
                'mode': result.get('mode', 'Unknown'),
                'detected_mode': result.get('detected_mode', '')
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @genz_bp.route('/api/genz/translate-audio', methods=['POST'])
    @login_required
    def translate_audio():
        """Transcribe audio and translate GenZ slang"""
        try:
            if 'audio' not in request.files:
                return jsonify({'success': False, 'error': 'No audio file provided'}), 400
            
            audio_file = request.files['audio']
            mode = request.form.get('mode', 'auto')  # auto, to_english, to_genz
            
            # Save uploaded audio
            save_result = audio_processor.save_uploaded_audio(audio_file)
            if not save_result['success']:
                return jsonify(save_result), 500
            
            audio_path = save_result['path']
            
            # Transcribe audio to text
            transcription_result = speech_translator.transcribe_audio(audio_path)
            if not transcription_result['success']:
                return jsonify(transcription_result), 500
            
            original_text = transcription_result['text']
            
            # Translate using bidirectional translation
            result = genz_translator.bidirectional_translate(original_text, target_mode=mode)
            
            # Save to database
            translation_model.save_translation(
                user_id=session['user_id'],
                original_text=result['original_text'],
                translated_text=result.get('translated_text', ''),
                source_lang='genz' if result.get('detected_mode') == 'slang_to_english' else 'en',
                target_lang='en' if result.get('detected_mode') == 'slang_to_english' else 'genz',
                audio_path=audio_path
            )
            
            return jsonify({
                'success': True,
                'original_text': result['original_text'],
                'translated_text': result.get('translated_text', ''),
                'explanations': result.get('explanations', []),
                'substitutions': result.get('substitutions', []),
                'mode': result.get('mode', 'Unknown'),
                'detected_mode': result.get('detected_mode', '')
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @genz_bp.route('/api/genz/dictionary', methods=['GET'])
    @login_required
    def get_dictionary():
        """Get all GenZ slang terms"""
        try:
            slang_list = genz_translator.get_all_slang()
            return jsonify({
                'success': True,
                'slang_list': slang_list
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @genz_bp.route('/api/genz/search', methods=['GET'])
    @login_required
    def search_slang():
        """Search for slang terms"""
        try:
            query = request.args.get('q', '')
            if not query:
                return jsonify({'success': False, 'error': 'No query provided'}), 400
            
            results = genz_translator.search_slang(query)
            return jsonify({
                'success': True,
                'results': results
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @genz_bp.route('/api/genz/explain/<slang_term>', methods=['GET'])
    @login_required
    def explain_slang(slang_term):
        """Get explanation for a specific slang term"""
        try:
            result = genz_translator.explain_slang(slang_term)
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return genz_bp
