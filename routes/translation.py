from flask import Blueprint, request, jsonify, session
from routes.auth import login_required
from models.user import Translation
from utils.translator import SpeechTranslator
from utils.audio_processor import AudioProcessor

translation_bp = Blueprint('translation', __name__)

def init_translation_routes(mongo, speech_translator, audio_processor):
    translation_model = Translation(mongo)
    
    @translation_bp.route('/api/translate', methods=['POST'])
    @login_required
    def translate_audio():
        try:
            if 'audio' not in request.files:
                return jsonify({'success': False, 'error': 'No audio file provided'}), 400
            
            audio_file = request.files['audio']
            target_lang = request.form.get('target_language', 'es')
            
            # Save uploaded audio
            save_result = audio_processor.save_uploaded_audio(audio_file)
            if not save_result['success']:
                return jsonify(save_result), 500
            
            audio_path = save_result['path']
            
            # Check if audio file has content
            import os
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 100:  # Minimum size for a valid audio file
                return jsonify({'success': False, 'error': 'Audio file is empty or too small'}), 400
            
            # Transcribe audio to text
            transcription_result = speech_translator.transcribe_audio(audio_path)
            if not transcription_result['success']:
                return jsonify(transcription_result), 500
            
            original_text = transcription_result.get('text', '').strip()
            
            if not original_text:
                return jsonify({'success': False, 'error': 'No speech detected in the audio file'}), 400
            
            source_lang = transcription_result.get('language', 'en') or 'en'
            
            # Translate text
            translation_result = speech_translator.translate_text(
                original_text,
                source_lang='en',  # Force English source for consistency
                target_lang=target_lang
            )
            
            if not translation_result['success']:
                return jsonify(translation_result), 500
            
            translated_text = translation_result.get('translated_text', '').strip()
            # Generate TTS for the translated text so client can play audio
            tts_result = speech_translator.text_to_speech(translated_text)
            tts_url = tts_result.get('url') if tts_result and tts_result.get('success') else None

            # Save to database
            translation_model.save_translation(
                user_id=session['user_id'],
                original_text=original_text,
                translated_text=translated_text,
                source_lang=source_lang,
                target_lang=target_lang,
                audio_path=audio_path
            )
            
            return jsonify({
                'success': True,
                'original_text': original_text,
                'translated_text': translated_text,
                'source_language': source_lang,
                'target_language': target_lang,
                'tts_url': tts_url
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @translation_bp.route('/api/translate-text', methods=['POST'])
    @login_required
    def translate_text_only():
        try:
            data = request.get_json()
            if data is None:
                return jsonify({'success': False, 'error': 'Invalid or missing JSON body'}), 400
            text = data.get('text', '').strip()
            target_lang = data.get('target_language', 'es')
            
            if not text:
                return jsonify({'success': False, 'error': 'No text provided'}), 400
            
            # Translate text
            translation_result = speech_translator.translate_text(
                text,
                source_lang='en',
                target_lang=target_lang
            )
            
            if not translation_result['success']:
                return jsonify(translation_result), 500
            
            translated_text = translation_result.get('translated_text', '').strip()

            # Generate TTS for the translated text
            tts_result = speech_translator.text_to_speech(translated_text)
            tts_url = tts_result.get('url') if tts_result and tts_result.get('success') else None
            
            # Save to database
            translation_model.save_translation(
                user_id=session['user_id'],
                original_text=text,
                translated_text=translated_text,
                source_lang='en',
                target_lang=target_lang
            )
            
            return jsonify({
                'success': True,
                'original_text': text,
                'translated_text': translated_text,
                'source_language': 'en',
                'target_language': target_lang,
                'tts_url': tts_url
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @translation_bp.route('/api/text-to-speech', methods=['POST'])
    @login_required
    def text_to_speech():
        try:
            data = request.get_json()
            if data is None:
                return jsonify({'success': False, 'error': 'Invalid or missing JSON body'}), 400
            text = data.get('text', '')
            
            if not text:
                return jsonify({'success': False, 'error': 'No text provided'}), 400
            
            # Generate speech
            result = speech_translator.text_to_speech(text)
            
            return jsonify(result)
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @translation_bp.route('/api/languages', methods=['GET'])
    @login_required
    def get_languages():
        languages = speech_translator.get_available_languages()
        return jsonify({'success': True, 'languages': languages})
    
    @translation_bp.route('/history')
    @login_required
    def history():
        from flask import render_template
        return render_template('history.html')
    
    @translation_bp.route('/api/history', methods=['GET'])
    @login_required
    def get_history():
        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            
            skip = (page - 1) * per_page
            
            translations = translation_model.get_user_translations(
                user_id=session['user_id'],
                limit=per_page,
                skip=skip
            )
            
            total = translation_model.count_user_translations(session['user_id'])
            
            # Convert ObjectId to string for JSON serialization
            for trans in translations:
                trans['_id'] = str(trans['_id'])
                trans['user_id'] = str(trans['user_id'])
                trans['created_at'] = trans['created_at'].isoformat()
            
            return jsonify({
                'success': True,
                'translations': translations,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            })
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @translation_bp.route('/api/history/<translation_id>', methods=['DELETE'])
    @login_required
    def delete_history(translation_id):
        try:
            success = translation_model.delete_translation(
                translation_id,
                session['user_id']
            )
            
            if success:
                return jsonify({'success': True, 'message': 'Translation deleted'})
            else:
                return jsonify({'success': False, 'error': 'Translation not found'}), 404
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return translation_bp