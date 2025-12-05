# choco install ffmpeg
import logging
import re
from typing import List

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

from data.slang_map import DEFAULT_SLANG_MAP


class GenZTranslator:
    def __init__(self):
        self.slang_to_english = {
            str(term).lower(): meaning for term, meaning in DEFAULT_SLANG_MAP.items()
        }

        # Build reverse mapping for English terms → slang suggestions
        # Map both whole meanings and component words to slang terms so that
        # English input (single words or sentences) can be mapped back to slang.
        self.english_to_slang = {}
        for slang, meaning in self.slang_to_english.items():
            meaning_text = str(meaning).lower()
            # full-meaning phrase -> slang
            self.english_to_slang.setdefault(meaning_text, []).append(slang)

            # individual words from the meaning -> slang (ignore very short words)
            key_words = re.findall(r"\b\w+\b", meaning_text)
            for word in key_words:
                if len(word) > 2:
                    self.english_to_slang.setdefault(word, []).append(slang)

        # Embedding-related state (lazy initialized)
        self.embedding_model_name = EMBEDDING_MODEL_NAME
        self._embedding_model = None
        self._embedding_matrix = None
        self._embedding_terms: List[str] = []

        logging.getLogger(__name__).info(
            'Loaded %d GenZ slang entries from built-in dataset',
            len(self.slang_to_english)
        )

    def _ensure_embeddings(self):
        if SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers is required for semantic slang search. "
                "Install it with `pip install sentence-transformers`."
            )

        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(self.embedding_model_name)

        if self._embedding_matrix is None:
            self._embedding_terms = list(self.slang_to_english.keys())
            definitions = [self.slang_to_english[term] for term in self._embedding_terms]
            embeddings = self._embedding_model.encode(
                definitions,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            self._embedding_matrix = embeddings.astype('float32')
        # If the mapping changed size since last build, rebuild embeddings
        if self._embedding_matrix is not None and len(self._embedding_terms) != len(self.slang_to_english):
            self._embedding_terms = list(self.slang_to_english.keys())
            definitions = [self.slang_to_english[term] for term in self._embedding_terms]
            embeddings = self._embedding_model.encode(
                definitions,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            self._embedding_matrix = embeddings.astype('float32')

    def semantic_lookup(self, query, top_k=5, min_score=0.35):
        query = (query or '').strip()
        if not query:
            return []

        self._ensure_embeddings()
        query_vector = self._embedding_model.encode(
            query,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False
        ).astype('float32')

        scores = np.dot(self._embedding_matrix, query_vector)
        ranked = sorted(
            (
                {
                    'slang': term,
                    'meaning': self.slang_to_english[term],
                    'score': float(score),
                    'match_type': 'semantic'
                }
                for term, score in zip(self._embedding_terms, scores)
            ),
            key=lambda item: item['score'],
            reverse=True
        )

        return [item for item in ranked if item['score'] >= min_score][:top_k]
    
    def translate_to_english(self, text):
        # Remove punctuation for matching but preserve for output
        words_with_punct = re.findall(r'\b\w+\b|[^\w\s]', text.lower())
        words = [w for w in words_with_punct if w.isalnum()]
        
        result = []
        explanations = []
        i = 0
        
        while i < len(words):
            # Check for multi-word slang (up to 5 words)
            found = False
            for length in range(5, 0, -1):
                if i + length <= len(words):
                    phrase = ' '.join(words[i:i+length])
                    if phrase in self.slang_to_english:
                        meaning = self.slang_to_english[phrase]
                        result.append(f"[{meaning}]")
                        explanations.append({
                            'slang': phrase,
                            'meaning': meaning
                        })
                        i += length
                        found = True
                        break
            
            if not found:
                result.append(words[i])
                i += 1
        
        return {
            'translated_text': ' '.join(result),
            'explanations': explanations,
            'substitutions': [],  # Empty for GenZ→English (use explanations instead)
            'original_text': text
        }
    
    def explain_slang(self, slang_term):
        slang_lower = slang_term.lower().strip()
        if slang_lower in self.slang_to_english:
            return {
                'success': True,
                'slang': slang_term,
                'meaning': self.slang_to_english[slang_lower],
                'example': self._get_example(slang_lower)
            }
        else:
            suggestions = []
            try:
                suggestions = self.semantic_lookup(slang_term, top_k=3, min_score=0.4)
            except Exception as exc:
                logging.getLogger(__name__).debug('Suggestion lookup failed: %s', exc)

            return {
                'success': False,
                'error': f'Slang term "{slang_term}" not found',
                'suggestions': suggestions
            }
    
    def _get_example(self, slang):
        examples = {
            'lit': 'That party was lit!',
            'slay': 'You totally slayed that presentation!',
            'cap': 'That sounds like cap to me.',
            'no cap': 'This is the best pizza, no cap.',
            'bussin': 'This food is bussin!',
            'bet': 'Want to hang out later? - Bet!',
            'sus': 'That excuse sounds pretty sus.',
            'vibe': 'I love the vibe of this place.',
            'tea': 'Spill the tea, what happened?',
            'rizz': 'He has so much rizz.',
            'mid': 'That movie was mid, nothing special.',
            'fire': 'Your outfit is fire!',
            'drip': 'Check out my drip today.',
            'ate': 'She ate that performance!',
            'periodt': 'I\'m not changing my mind, periodt.',
            'deadass': 'I\'m deadass serious right now.',
        }
        return examples.get(slang, f'Example: That\'s so {slang}!')
    
    def get_all_slang(self):
        return [
            {'slang': slang, 'meaning': meaning}
            for slang, meaning in sorted(self.slang_to_english.items())
        ]
    
    def search_slang(self, query):
        query_lower = query.lower()
        results = []

        # Text-based filtering
        for slang, meaning in self.slang_to_english.items():
            if query_lower in slang or query_lower in meaning.lower():
                results.append({
                    'slang': slang,
                    'meaning': meaning,
                    'match_type': 'text'
                })

        # Semantic augmentation (ignore failures silently to keep search usable)
        try:
            semantic_hits = self.semantic_lookup(query, top_k=5)
        except Exception as exc:
            logging.getLogger(__name__).warning('Semantic lookup unavailable: %s', exc)
            semantic_hits = []

        merged = []
        seen = set()
        for item in results + semantic_hits:
            key = item['slang']
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)

        return merged
    
    def translate_to_genz(self, text):
        result_text = text
        substitutions = []

        # Prefer semantic matching when available to map an English phrase
        # or sentence to the closest slang entry.
        if SentenceTransformer is not None:
            try:
                self._ensure_embeddings()
                query_vec = self._embedding_model.encode(
                    text,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False
                ).astype('float32')

                scores = np.dot(self._embedding_matrix, query_vec)
                ranked_idx = np.argsort(scores)[::-1]
                for idx in ranked_idx[:5]:
                    score = float(scores[idx])
                    if score < 0.28:
                        break
                    slang_term = self._embedding_terms[idx]
                    substitutions.append({
                        'original': text,
                        'replacement': slang_term,
                        'score': score
                    })

                if substitutions:
                    # Replace entire text with top slang suggestion
                    result_text = substitutions[0]['replacement']
                    return {
                        'translated_text': result_text,
                        'substitutions': substitutions,
                        'original_text': text,
                        'success': True
                    }
            except Exception as sem_exc:
                logging.getLogger(__name__).debug('Semantic matching failed: %s', sem_exc)

        # Heuristic token/substring matching: try to find words or phrases in the
        # meaning→slang reverse map built at init time.
        lowered = text.lower()

        # Exact phrase match first
        if lowered in self.english_to_slang:
            choices = self.english_to_slang[lowered]
            replacement = choices[0]
            substitutions.append({'original': lowered, 'replacement': replacement})
            result_text = replacement
            return {
                'translated_text': result_text,
                'substitutions': substitutions,
                'original_text': text,
                'success': True
            }

        # Word-level matching: prefer longer matches (n-grams)
        words = re.findall(r"\b\w+\b", lowered)
        n = len(words)
        matched = False
        for size in range(min(4, n), 0, -1):
            for i in range(0, n - size + 1):
                phrase = ' '.join(words[i:i+size])
                if phrase in self.english_to_slang:
                    replacement = self.english_to_slang[phrase][0]
                    substitutions.append({'original': phrase, 'replacement': replacement})
                    # replace the phrase in the original text (preserve spacing roughly)
                    pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                    result_text = pattern.sub(replacement, result_text, count=1)
                    matched = True

        # If any substitutions were applied, return result
        if matched:
            return {
                'translated_text': result_text,
                'substitutions': substitutions,
                'original_text': text,
                'success': True
            }

        # Fallback: simple word mapping using contained words
        for w in words:
            if w in self.english_to_slang:
                replacement = self.english_to_slang[w][0]
                substitutions.append({'original': w, 'replacement': replacement})
                result_text = re.sub(r'\b' + re.escape(w) + r'\b', replacement, result_text, flags=re.IGNORECASE)

        return {
            'translated_text': result_text,
            'substitutions': substitutions,
            'original_text': text,
            'success': True
        }
    
    def bidirectional_translate(self, text, target_mode='auto'):
        # Detect if text is predominantly GenZ slang or English
        if target_mode == 'auto':
            slang_count = 0
            text_lower = text.lower()
            words = text_lower.split()
            
            # First check for complete multi-word slang phrases in the full text
            for slang in self.slang_to_english.keys():
                if ' ' in slang:
                    # Check if multi-word phrase exists in the text (word boundaries)
                    if re.search(r'\b' + re.escape(slang) + r'\b', text_lower):
                        # Count how many times this phrase appears
                        count = len(re.findall(r'\b' + re.escape(slang) + r'\b', text_lower))
                        slang_count += count
            
            # Then check individual words for single-word slang
            for word in words:
                word_clean = word.strip('.,!?;:\'"')
                if word_clean in self.slang_to_english:
                    slang_count += 1
            
            # If more than 20% slang words found, assume it's GenZ
            slang_ratio = slang_count / max(len(words), 1)
            target_mode = 'to_english' if slang_ratio > 0.2 else 'to_genz'
        
        if target_mode == 'to_english':
            result = self.translate_to_english(text)
            return {
                **result,
                'mode': 'GenZ → English',
                'detected_mode': 'slang_to_english'
            }
        else:
            result = self.translate_to_genz(text)
            return {
                **result,
                'mode': 'English → GenZ',
                'detected_mode': 'english_to_slang'
            }

