from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

class User:
    def __init__(self, mongo):
        self.collection = mongo.db.users
    
    def create_user(self, username, email, password):
        user_data = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'created_at': datetime.utcnow(),
            'last_login': None
        }
        result = self.collection.insert_one(user_data)
        return result.inserted_id
    
    def find_by_email(self, email):
        return self.collection.find_one({'email': email})
    
    def find_by_username(self, username):
        return self.collection.find_one({'username': username})
    
    def find_by_id(self, user_id):
        return self.collection.find_one({'_id': ObjectId(user_id)})
    
    def verify_password(self, user, password):
        return check_password_hash(user['password'], password)
    
    def update_last_login(self, user_id):
        # Ensure we have an ObjectId instance
        obj_id = user_id if isinstance(user_id, ObjectId) else ObjectId(user_id)

        self.collection.update_one(
            {'_id': obj_id},
            {'$set': {'last_login': datetime.utcnow()}}
        )


class Translation:
    def __init__(self, mongo):
        self.collection = mongo.db.translations
    
    def save_translation(self, user_id, original_text, translated_text, 
                        source_lang, target_lang, audio_path=None):
        translation_data = {
            'user_id': ObjectId(user_id),
            'original_text': original_text,
            'translated_text': translated_text,
            'source_language': source_lang,
            'target_language': target_lang,
            'audio_path': audio_path,
            'created_at': datetime.utcnow()
        }
        result = self.collection.insert_one(translation_data)
        return result.inserted_id
    
    def get_user_translations(self, user_id, limit=50, skip=0):
        translations = self.collection.find(
            {'user_id': ObjectId(user_id)}
        ).sort('created_at', -1).skip(skip).limit(limit)
        return list(translations)
    
    def count_user_translations(self, user_id):
        return self.collection.count_documents({'user_id': ObjectId(user_id)})
    
    def delete_translation(self, translation_id, user_id):
        result = self.collection.delete_one({
            '_id': ObjectId(translation_id),
            'user_id': ObjectId(user_id)
        })
        return result.deleted_count > 0