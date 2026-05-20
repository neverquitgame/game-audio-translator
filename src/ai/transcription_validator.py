"""
Transcription confidence and validity checking to prevent LLM API waste.
"""
import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class TranscriptionValidator:
    """
    Validates transcription results before sending to LLM.
    Prevents wasting API calls on garbage, short, or repetitive text.
    """

    # Patterns that indicate garbage or non-speech
    GARBAGE_PATTERNS = [
        r"^\s*[.,;:!?-]+\s*$",  # Only punctuation
        r"^\s*(\w)\1{4,}\s*$",  # Repeated single character
        r"^\s*(hmm+|um+m|uh+|err+|uhh+|ahhh+|ohhh+)\s*$",  # Filler sounds only
        r"^\s*\d{10,}\s*$",  # Only numbers (likely time stamps or codes)
        r"^\s*[a-z]{1,2}\s*$",  # Single letters only
    ]

    # Common meaningless outputs from Whisper
    MEANINGLESS_WORDS = {
        "mmm", "hmm", "uhm", "um", "uh", "ah", "oh", "eh", "huh", "yeah",
        "yes", "no", "okay", "ok", "wait", "uh-huh", "uh huh"
    }

    # Patterns that suggest poor transcription quality
    LOW_QUALITY_INDICATORS = [
        r"\w{20,}",  # Very long nonsense words (>20 chars)
        r"[^\w\s\.\,\!\?-]",  # Too many special characters
    ]

    @staticmethod
    def is_garbage(text: str) -> bool:
        """
        Check if transcription is garbage/noise.
        Returns True if should be skipped.
        """
        if not text:
            return True

        text_stripped = text.strip().lower()

        # Too short
        if len(text_stripped) < 2:
            return True

        # Check garbage patterns
        for pattern in TranscriptionValidator.GARBAGE_PATTERNS:
            if re.match(pattern, text_stripped, re.IGNORECASE):
                return True

        # Only filler words
        words = text_stripped.split()
        if len(words) > 0 and all(w in TranscriptionValidator.MEANINGLESS_WORDS for w in words):
            return True

        return False

    @staticmethod
    def get_confidence_score(text: str) -> float:
        """
        Estimate transcription confidence (0.0-1.0).
        Higher = more likely to be real, meaningful speech.
        """
        if not text or TranscriptionValidator.is_garbage(text):
            return 0.0

        text_stripped = text.strip()
        words = text_stripped.split()
        word_count = len(words)

        # Scoring factors
        score = 0.5  # Base score

        # Factor 1: Word count (longer = more likely meaningful)
        if word_count >= 5:
            score += 0.25
        elif word_count >= 3:
            score += 0.15

        # Factor 2: Average word length (real words are typically 4-10 chars)
        avg_word_len = sum(len(w) for w in words) / len(words) if words else 0
        if 3 <= avg_word_len <= 12:
            score += 0.15
        elif avg_word_len > 15:  # Suspiciously long words (gibberish)
            score -= 0.3

        # Factor 3: Vowel ratio (speech has more vowels than pure noise)
        vowel_count = sum(1 for c in text_stripped.lower() if c in 'aeiou')
        vowel_ratio = vowel_count / len(text_stripped) if text_stripped else 0
        if 0.25 <= vowel_ratio <= 0.45:
            score += 0.1

        # Factor 4: Punctuation (natural speech has some punctuation)
        punctuation_count = sum(1 for c in text_stripped if c in '.,!?-')
        if 0 < punctuation_count <= 3:
            score += 0.05

        # Clamp to [0, 1]
        return min(1.0, max(0.0, score))

    @staticmethod
    def validate(
        text: Optional[str],
        min_confidence: float = 0.4
    ) -> Tuple[bool, float, str]:
        """
        Validate transcription for LLM translation.

        Args:
            text: Transcribed text
            min_confidence: Minimum confidence threshold (0.0-1.0)

        Returns:
            (is_valid, confidence_score, reason)
            - is_valid: Whether text should be sent to LLM
            - confidence_score: Confidence score (0.0-1.0)
            - reason: Human-readable validation result
        """
        if not text:
            return False, 0.0, "Empty transcription"

        if TranscriptionValidator.is_garbage(text):
            return False, 0.0, f"Garbage text: {text[:50]}"

        confidence = TranscriptionValidator.get_confidence_score(text)

        if confidence < min_confidence:
            return False, confidence, f"Low confidence ({confidence:.2f}) - skipping LLM"

        return True, confidence, f"Valid transcription (confidence: {confidence:.2f})"
