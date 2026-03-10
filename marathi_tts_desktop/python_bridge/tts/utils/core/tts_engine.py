#!/usr/bin/env python3
import os
import uuid
import math
import logging
from typing import Dict, Any, Optional, List, Tuple
from django.conf import settings
from gtts import gTTS # type: ignore
from pydub import AudioSegment # type: ignore
import re
import shutil
import json
import glob

from ..text.text_processor import TextProcessor
from ..emotion.emotion_analyzer import EmotionAnalyzer
from ..voice.voice_modulator import VoiceModulator
from ..audio.prosody_engine import MarathiProsodyEngine, PauseType
from ..text.text_normalizer import MarathiTextNormalizer
from ..text.marathi_grammar import MarathiGrammarEngine
from ..phonetic.g2p_engine import MarathiG2PEngine
from ..phonetic.marathi_phonetics import (
    apply_sanskrit_phonetics,
    apply_marathi_phonetics,
    apply_old_marathi_phonetics,
)
from tts.constants.tts_config import SUPPORTED_LANGUAGES
from tts.constants.audio_constants import VERSE_MIN_LINES

# Configure logging
logger = logging.getLogger('tts.engine')

# Global singleton instance
_engine_instance = None

# Create a custom gTTS class to avoid language checking
from gtts.lang import tts_langs # type: ignore

class OptimizedTTS(gTTS):
    """Optimized version of gTTS that skips redundant language validation"""
    
    # Cache the languages once (from centralized constants)
    _LANGUAGES = SUPPORTED_LANGUAGES
    
    def __init__(self, text, lang='mr', slow=False, lang_check=False, **kwargs):
        # Override lang_check to always be False to skip validation
        super().__init__(text, lang=lang, slow=slow, lang_check=False, **kwargs)
    
    def _fetch_langs(self):
        """Return only our supported languages"""
        return self._LANGUAGES

class TTSEngine:
    """Core TTS engine handling audio generation with natural Marathi prosody"""
    
    def __init__(self):
        """Initialize TTS Engine with required components"""
        logger.info("Initializing TTS Engine")
        
        # Set up directories
        self.output_dir = os.path.join(settings.MEDIA_ROOT, 'tts')
        self.temp_dir = os.path.join(settings.MEDIA_ROOT, 'tts', 'temp')
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Initialize components
        self.grammar_engine = MarathiGrammarEngine()
        self.emotion_analyzer = EmotionAnalyzer()
        self.voice_modulator = VoiceModulator()
        self.text_processor = TextProcessor()
        self.prosody_engine = MarathiProsodyEngine()
        self.text_normalizer = MarathiTextNormalizer()
        
        # Initialize G2P engine with dictionary for word validation
        dict_path = os.path.join(settings.BASE_DIR, 'dict', 'marathi_dictionary.txt')
        self.g2p_engine = MarathiG2PEngine(dictionary_path=dict_path)
        
        logger.info("TTS Engine initialization complete")

    def preprocess_marathi_text(self, text: str) -> str:
        """Full Marathi text preprocessing pipeline:
        
        1. Grammar engine — extract, clean, fix spelling/grammar/word-order
        2. Normalizer — visarga, abbreviations, numbers → words
        3. G2P engine — conjunct preservation, anusvara/visarga context rules
        4. Pronunciation — remaining regex-based fixes (safe patterns only)
        """
        logger.debug(f"Original text: {text}")
        
        # Step 1: Grammar — clean junk, fix spelling, sandhi, vibhakti,
        #         gender agreement, word order, add missing punctuation
        text = self.grammar_engine.process(text)
        
        # Step 2: Normalize (abbreviations, numbers → words, Unicode NFC)
        text = self.text_normalizer.normalize_text(text)
        
        # Step 3: G2P engine — context-aware phoneme processing
        #   - Conjunct preservation (fixes च्या→चा, झ्या→झा)
        #   - Anusvara assimilation (context-dependent nasalization)
        #   - Visarga sandhi (context-dependent sibilant mapping)
        #   - Exception lexicon lookups
        text = self.g2p_engine.process(text)
        
        # Step 4: Remaining safe pronunciation fixes (no conjunct-stripping)
        text = self.text_processor._fix_pronunciation(text)
        text = self.text_processor._process_marathi(text)
        
        logger.debug(f"Processed text: {text}")
        return text

    def preprocess_verse_text(self, text: str) -> str:
        """Lighter preprocessing for verse/shloka text.
        
        Verses should NOT be grammar-corrected (no spelling changes,
        no word-order fixes, no sandhi splitting). Only:
        1. Basic cleanup (junk removal)
        2. Normalize (abbreviations, numbers, visarga)
        3. G2P (pronunciation rules)
        4. Language-specific phonetics (Sanskrit / Old Marathi / Modern Marathi)
        
        Preserves newline structure for verse segmentation.
        """
        logger.debug(f"Verse preprocessing: {text[:100]}...")
        
        # Light cleanup only — no grammar corrections
        from tts.utils.text.marathi_grammar import extract_and_clean
        text = extract_and_clean(text)
        
        # Normalize
        text = self.text_normalizer.normalize_text(text)
        
        # G2P
        text = self.g2p_engine.process(text)
        
        # Pronunciation fixes
        text = self.text_processor._fix_pronunciation(text)
        text = self.text_processor._process_marathi(text)

        # ── Language-specific phonetics ──────────────────────────────────
        # Sanskrit: strip Vedic accents, expand avagraha, fix visarga+vowel
        #           sandhi, anusvara assimilation — all in apply_sanskrit_phonetics
        # Old Marathi: preserve metre syllables, apply Sant-literature lexicon,
        #              keep anusvara nasalization — all in apply_old_marathi_phonetics
        # Modern Marathi verse: apply standard Marathi phonetics
        lang = getattr(self, '_current_language', 'mr')
        if lang == 'sa':
            text = apply_sanskrit_phonetics(text)
            logger.debug('Sanskrit phonetics applied to verse')
        elif lang in ('hi', 'mr'):
            # Check for Sanskrit-heavy stotras (many visarga + dandas)
            # Even in Marathi scripts, stotras are often Sanskrit => detect
            from tts.utils.phonetic.sandhi_engine import is_predominantly_sanskrit
            if is_predominantly_sanskrit(text):
                text = apply_sanskrit_phonetics(text)
                logger.debug('Sanskrit phonetics applied (auto-detected in mr verse)')
            else:
                # Check if it looks like Old Marathi (classical forms)
                _old_markers = ['चि', 'तें', 'हें', 'जें', 'करितাं', 'असतাं']
                _old_count = sum(text.count(m) for m in _old_markers)
                if _old_count >= 2:
                    text = apply_old_marathi_phonetics(text)
                    logger.debug('Old Marathi phonetics applied (%d markers)', _old_count)
                else:
                    text = apply_marathi_phonetics(text)
                    logger.debug('Modern Marathi phonetics applied to verse')
        
        return text

    @staticmethod
    def _detect_verse_blocks(text: str) -> bool:
        """Detect if text is predominantly verse/shloka structure.

        Two detection strategies:
          1. Multi-line text: count lines that END with ॥ (classic newline-based stotra format).
          2. Flat single-line text: count inline ॥ occurrences (prose-formatted verse,
             common when stotras are stored as a single paragraph with embedded dandas).

        Returns True if EITHER strategy finds >= VERSE_MIN_LINES occurrences.
        This mirrors the identical logic in prosody_engine._is_verse_block().
        """
        # Strategy 1: newline-separated lines ending in ॥
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        danda_lines = sum(1 for l in lines if l.rstrip().endswith('॥'))
        if danda_lines >= VERSE_MIN_LINES:
            return True
        # Strategy 2: flat text — count ॥ occurrences (same as prosody_engine._is_verse_block)
        return text.count('॥') >= VERSE_MIN_LINES

    def generate_tts_audio(self, text: str, voice_params: Dict[str, Any], streaming: bool = False) -> Optional[str]:
        """Generate TTS audio with natural Marathi prosody — segment-based with pauses.
        
        Verse Detection: if the text has 2+ lines ending with ॥, it's treated
        as verse/shloka/stotra — lighter preprocessing (no grammar corrections)
        and recitation-style generation (slow=True, verse pauses).
        
        voice_params can contain:
          - language: str   (mr/hi/sa/en)
          - engine: str     (auto/google/local)
          - verse_mode: bool
        """
        try:
            # Extract language, gender, and verse_mode from voice_params
            language = voice_params.pop('language', 'mr') if voice_params else 'mr'
            engine_choice = voice_params.pop('engine', 'auto') if voice_params else 'auto'
            gender = voice_params.pop('gender', 'female') if voice_params else 'female'
            user_verse = voice_params.pop('verse_mode', False) if voice_params else False

            # Store language and gender for use in _generate_base_audio
            self._current_language = language
            self._current_engine = engine_choice
            self._current_gender = gender

            # Detect verse mode BEFORE preprocessing (grammar engine destroys line structure)
            is_verse = user_verse or self._detect_verse_blocks(text)
            
            if is_verse:
                logger.info("Verse mode detected — using recitation pipeline")
                text = self.preprocess_verse_text(text)
            else:
                text = self.preprocess_marathi_text(text)
            
            logger.info(f"Processing text of length: {len(text)}, lang={language}, engine={engine_choice}, gender={gender}, verse={is_verse}")
            
            if not text or not text.strip():
                logger.error("Empty text provided for TTS generation")
                return None
            
            # Step 2: Detect dominant emotion for voice modulation
            emotion_result = self.emotion_analyzer.analyze(text)
            detected_emotion = emotion_result.get('emotion', 'neutral')
            detected_params = self.emotion_analyzer.voice_params.get(
                detected_emotion,
                self.emotion_analyzer.voice_params['neutral']
            ).copy()
            
            # Merge caller-provided params (they take precedence)
            if voice_params:
                for key, value in voice_params.items():
                    detected_params[key] = value
            
            # Apply gender-based pitch shift:
            # gTTS produces a female-sounding voice by default.
            # Male voice = pitch shift down ~4 semitones (factor ~0.79)
            if gender == 'male':
                base_pitch = detected_params.get('pitch', 1.0)
                # Convert pitch to a factor if it's in semitones (0-based)
                if isinstance(base_pitch, (int, float)) and base_pitch == 0:
                    base_pitch = 1.0
                detected_params['pitch'] = base_pitch * 0.79  # ~4 semitones down
                logger.info(f"Male voice: pitch factor set to {detected_params['pitch']:.2f}")
            
            # Step 3: Generate audio with prosody-aware segmentation
            return self._generate_complete_audio(text, detected_params)
            
        except Exception as e:
            logger.error(f"TTS generation failed: {str(e)}", exc_info=True)
            return None

    def _generate_complete_audio(self, text: str, voice_params: Dict[str, Any]) -> Optional[str]:
        """Generate TTS audio with natural pauses between segments.
        
        Instead of generating one monolithic audio blob, this method:
        1. Splits text into natural segments (clauses, sentences, paragraphs)
        2. Batches small segments to reduce API calls
        3. Generates audio for each batch via gTTS
        4. Stitches them together with calibrated silence gaps
        5. Applies voice modulation to the final audio
        """
        temp_paths = []
        try:
            # Use prosody engine to segment text
            segments = self.prosody_engine.segment_text(text)
            
            if not segments:
                logger.warning("Prosody engine returned no segments")
                return self._generate_fallback_audio(text, voice_params)
            
            logger.info(f"Prosody: {len(segments)} segments, "
                        f"~{self.prosody_engine.get_total_duration_estimate(segments):.1f}s pauses")
            logger.debug("Segments:\n" + self.prosody_engine.describe_segments(segments))
            
            # Filter out non-speakable segments early
            speakable_segments = []
            for seg in segments:
                seg_text = seg.text.strip()
                if seg_text and re.search(r'[\u0900-\u097F\u0980-\u09FFa-zA-Z0-9]', seg_text):
                    speakable_segments.append(seg)
            
            if not speakable_segments:
                logger.warning("No speakable segments found")
                return self._generate_fallback_audio(text, voice_params)
            
            # Batch segments to reduce gTTS API calls.
            # Group consecutive segments together until we hit a substantial
            # pause (sentence/paragraph boundary) or a character limit.
            # VERSE segments are NOT batched — each verse line is generated
            # individually with slow=True for recitation quality.
            MAX_BATCH_CHARS = 500  # max characters per API call
            BATCH_PAUSE_THRESHOLD = PauseType.SENTENCE  # don't merge across sentence breaks
            
            batches = []  # list of (combined_text, list_of_segments, is_verse)
            current_texts = []
            current_segs = []
            current_len = 0
            
            def flush_batch():
                nonlocal current_texts, current_segs, current_len
                if current_texts:
                    is_batch_verse = any(s.is_verse for s in current_segs)
                    batches.append((' '.join(current_texts), list(current_segs), is_batch_verse))
                    current_texts = []
                    current_segs = []
                    current_len = 0
            
            for seg in speakable_segments:
                seg_text = seg.text.strip()
                
                # Verse segments: generate each line individually (don't batch)
                if seg.is_verse:
                    flush_batch()  # flush any pending prose batch
                    batches.append((seg_text, [seg], True))
                    continue
                
                # Prose mode: batch normally
                # Would adding this segment exceed the batch limit?
                if current_len + len(seg_text) > MAX_BATCH_CHARS and current_texts:
                    flush_batch()
                
                current_texts.append(seg_text)
                current_segs.append(seg)
                current_len += len(seg_text)
                
                # Split batch at sentence/paragraph boundaries
                if seg.pause_after_ms >= BATCH_PAUSE_THRESHOLD:
                    flush_batch()
            
            # Don't forget the last batch
            flush_batch()
            
            logger.info(f"Batched {len(speakable_segments)} segments into {len(batches)} API calls")
            
            # Build final audio by concatenating batch audio + silence
            combined = AudioSegment.empty()
            
            verse_count = sum(1 for _, _, is_v in batches if is_v)
            prose_count = len(batches) - verse_count
            if verse_count > 0:
                logger.info(f"Verse mode: {verse_count} verse lines, {prose_count} prose batches")
            
            for batch_idx, (batch_text, batch_segs, is_verse) in enumerate(batches):
                # Generate audio: verse lines use slow=True for recitation.
                # If the MetreEngine has set a tts_rate < 0.92 on the first
                # segment, honour that as a slow-mode signal too.
                first_rate = batch_segs[0].tts_rate if batch_segs else 1.0
                use_slow = is_verse or (first_rate < 0.92)
                seg_audio_path = self._generate_base_audio(
                    batch_text, slow=use_slow
                )
                if not seg_audio_path:
                    # First failure: retry once with a fallback language.
                    # Sanskrit (lang='sa') is flaky on gTTS and can return
                    # errors for certain words or clusters, silently dropping
                    # the entire segment from the audio.  Fall back to
                    # Hindi ('hi') which uses the same Devanagari script and
                    # is far more reliable, then Marathi ('mr') as last resort.
                    effective = getattr(self, '_current_language', 'mr')
                    fallbacks = {
                        'sa': ['hi', 'mr'],
                        'hi': ['mr'],
                    }.get(effective, [])
                    for fb_lang in fallbacks:
                        logger.warning(
                            f"Batch {batch_idx} failed with lang='{effective}', "
                            f"retrying with lang='{fb_lang}': '{batch_text[:60]}'"
                        )
                        orig_lang = self._current_language
                        self._current_language = fb_lang
                        seg_audio_path = self._generate_base_audio(batch_text, slow=use_slow)
                        self._current_language = orig_lang
                        if seg_audio_path:
                            break
                if not seg_audio_path:
                    logger.error(f"Permanently failed batch {batch_idx}: '{batch_text[:60]}' — skipping")
                    continue
                temp_paths.append(seg_audio_path)
                
                # Load batch audio
                seg_audio = AudioSegment.from_mp3(seg_audio_path)
                
                # Apply emphasis if any segment in this batch is emphasized
                max_emphasis = max(s.emphasis for s in batch_segs)
                if max_emphasis > 1.0:
                    db_boost = (max_emphasis - 1.0) * 10
                    seg_audio = seg_audio + db_boost
                
                # Append batch audio
                combined += seg_audio
                
                # Use the pause from the last segment in this batch
                last_pause = batch_segs[-1].pause_after_ms
                if last_pause > 0:
                    silence = AudioSegment.silent(duration=last_pause)
                    combined += silence
            
            if len(combined) == 0:
                logger.error("No audio segments were generated")
                return self._generate_fallback_audio(text, voice_params)
            
            # Apply voice modulation to the complete audio
            modified_audio = self.voice_modulator.modulate_voice(
                audio=combined,
                options=voice_params
            )
            
            # Save final audio
            output_path = os.path.join(self.output_dir, f'tts_{uuid.uuid4()}.wav')
            modified_audio.export(output_path, format='wav')
            
            logger.info(f"Generated audio: {output_path} ({len(modified_audio)}ms, "
                        f"{len(segments)} segments)")
            return output_path
            
        except Exception as e:
            logger.error(f"Segment-based TTS generation failed: {str(e)}", exc_info=True)
            # Fall back to monolithic generation
            return self._generate_fallback_audio(text, voice_params)
        finally:
            # Cleanup all temp files
            for tp in temp_paths:
                try:
                    if tp and os.path.exists(tp):
                        os.remove(tp)
                except OSError:
                    pass

    def _generate_fallback_audio(self, text: str, voice_params: Dict[str, Any]) -> Optional[str]:
        """Fallback: generate audio without segmentation (old monolithic approach)."""
        try:
            temp_path = self._generate_base_audio(text)
            if not temp_path:
                return None
            audio = AudioSegment.from_mp3(temp_path)
            modified_audio = self.voice_modulator.modulate_voice(audio=audio, options=voice_params)
            output_path = os.path.join(self.output_dir, f'tts_{uuid.uuid4()}.wav')
            modified_audio.export(output_path, format='wav')
            os.remove(temp_path)
            return output_path
        except Exception as e:
            logger.error(f"Fallback TTS generation also failed: {str(e)}", exc_info=True)
            return None

    def _generate_base_audio(self, text: str, lang: str = 'mr', slow: bool = False) -> Optional[str]:
        """Generate base audio using TTS API with optimized language handling.
        
        Args:
            text: Text to synthesize
            lang: Language code (default 'mr' for Marathi)
            slow: If True, use slow speech for verse/recitation mode
        """
        try:
            # Use language from current generation context if available
            effective_lang = getattr(self, '_current_language', None) or lang

            # Safety: skip if text has no speakable characters
            if not text or not re.search(r'[\u0900-\u097F\u0980-\u09FFa-zA-Z0-9]', text):
                logger.debug(f"Skipping non-speakable text: '{text[:40]}'")
                return None

            # Generate base audio file
            base_filename = f"base_{uuid.uuid4()}.mp3"
            base_filepath = os.path.join(self.temp_dir, base_filename)
            
            # Use optimized TTS (slow=True for recitation/chanting mode)
            tts = OptimizedTTS(text=text, lang=effective_lang, slow=slow, lang_check=False)
            tts.save(base_filepath)
            
            # Convert to WAV for further processing
            audio = AudioSegment.from_mp3(base_filepath)
            
            return base_filepath
        except Exception as e:
            logger.error(f"Error generating base audio: {str(e)}", exc_info=True)
            return None

    def fix_marathi_pronunciation(self, text):
        """Fix specific Marathi pronunciation issues with regex patterns.
        
        NOTE: This method is largely superseded by the G2P engine and
        text_processor._fix_pronunciation(). Kept for legacy compatibility.
        Hyphen-to-eyelash-ra is now handled in the normalizer.
        """
        return text

    def _handle_special_pronunciations(self, text: str) -> str:
        """Handle special pronunciation cases — delegates to G2P engine.
        
        This method is kept for backward compatibility. All context-aware
        phoneme processing (conjuncts, anusvara, visarga) is now handled
        by the MarathiG2PEngine.
        """
        try:
            return self.g2p_engine.process(text)
        except Exception as e:
            logger.error(f"Error in special pronunciation handling: {str(e)}")
            return text

def get_engine_instance():
    """Get or create the TTSEngine singleton instance"""
    global _engine_instance
    if (_engine_instance is None):
        _engine_instance = TTSEngine()
    return _engine_instance

def generate_tts_audio(text: str, **kwargs) -> Optional[str]:
    """Global function to generate TTS audio"""
    engine = get_engine_instance()
    return engine.generate_tts_audio(text=text, voice_params=kwargs)

# Add this alias for backward compatibility
generate_audio = generate_tts_audio

# Add this to TextProcessor class
def split_into_streamable_chunks(self, text, target_chunk_size=1000):
    """Split text into streamable chunks of appropriate size"""
    # First try to split by paragraphs
    paragraphs = re.split(r'\n\s*\n', text)
    
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If adding this paragraph exceeds target size and we already have content
        if len(current_chunk) + len(paragraph) > target_chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = paragraph
        else:
            # For first paragraph or if current chunk is still small enough
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
    
    # Add the last chunk if not empty
    if current_chunk:
        chunks.append(current_chunk)
    
    # For very large paragraphs, split further by sentences
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= target_chunk_size:
            final_chunks.append(chunk)
        else:
            # Split this large chunk by sentences
            sentences = re.split(r'([।॥!?])', chunk)
            sentence_chunks = []
            current_sentence_chunk = ""
            
            for i in range(0, len(sentences), 2):
                sentence = sentences[i]
                # Add punctuation if available
                if i+1 < len(sentences):
                    sentence += sentences[i+1]
                
                if len(current_sentence_chunk) + len(sentence) > target_chunk_size and current_sentence_chunk:
                    sentence_chunks.append(current_sentence_chunk)
                    current_sentence_chunk = sentence
                else:
                    if current_sentence_chunk:
                        current_sentence_chunk += " " + sentence
                    else:
                        current_sentence_chunk = sentence
            
            if current_sentence_chunk:
                sentence_chunks.append(current_sentence_chunk)
            
            final_chunks.extend(sentence_chunks)
    
    return final_chunks