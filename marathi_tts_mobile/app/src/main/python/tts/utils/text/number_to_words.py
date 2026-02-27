"""
Marathi Number-to-Words Converter for TTS
==========================================
Converts numerals (Devanagari & Arabic) to spoken Marathi words.
Handles integers, decimals, ordinals, currency, dates, times,
phone numbers, and common number patterns found in Marathi text.
"""
import re
import logging
from tts.constants.number_constants import (
    ONES, TEENS, TENS, TWENTIES_TO_NINETIES,
    LARGE_NUMBERS, DEVANAGARI_TO_ARABIC,
    ORDINALS, MONTHS_MARATHI, CURRENCY_SYMBOLS,
)

logger = logging.getLogger(__name__)


def _two_digit_to_words(n: int) -> str:
    """Convert a two-digit number (0-99) to Marathi words."""
    if n == 0:
        return ''
    if n < 10:
        return ONES[n]
    if 10 <= n <= 19:
        return TEENS[n - 10]
    if n in TWENTIES_TO_NINETIES:
        return TWENTIES_TO_NINETIES[n]
    # Fallback for any gaps (shouldn't happen with complete dict)
    tens = n // 10
    ones = n % 10
    if ones == 0:
        return TENS[tens]
    return f"{ONES[ones]}{TENS[tens]}"  # In Marathi, ones come before tens


def number_to_marathi_words(n: int) -> str:
    """Convert an integer to Marathi words.

    Uses the Indian numbering system: हजार, लाख, कोटी, अब्ज, etc.
    """
    if n == 0:
        return 'शून्य'
    if n < 0:
        return 'उणे ' + number_to_marathi_words(-n)

    parts = []
    for value, name in LARGE_NUMBERS:
        if n >= value:
            count = n // value
            n = n % value
            count_words = number_to_marathi_words(count) if count >= 100 else _two_digit_to_words(count)
            if value == 100 and count == 1:
                parts.append('शंभर')
            elif value == 100:
                count_words = _two_digit_to_words(count)
                parts.append(f"{count_words}शे")
            else:
                parts.append(f"{count_words} {name}")

    if n > 0:
        parts.append(_two_digit_to_words(n))

    return ' '.join(parts)


def _decimal_to_words(decimal_str: str) -> str:
    """Convert decimal part digit by digit: 0.45 → शून्य दशांश चार पाच"""
    digit_words = ['शून्य', 'एक', 'दोन', 'तीन', 'चार', 'पाच', 'सहा', 'सात', 'आठ', 'नऊ']
    return ' '.join(digit_words[int(d)] for d in decimal_str)


def _convert_number_match(match: re.Match) -> str:
    """Convert a matched number string to Marathi words."""
    num_str = match.group(0).translate(DEVANAGARI_TO_ARABIC)
    try:
        if '.' in num_str:
            integer_part, decimal_part = num_str.split('.', 1)
            int_val = int(integer_part) if integer_part else 0
            result = number_to_marathi_words(int_val)
            result += ' दशांश ' + _decimal_to_words(decimal_part)
            return result
        else:
            return number_to_marathi_words(int(num_str))
    except (ValueError, OverflowError):
        return match.group(0)  # return original if conversion fails


def convert_currency(text: str) -> str:
    """Convert currency amounts to spoken form.

    ₹500 → पाचशे रुपये
    $10.50 → दहा डॉलर पन्नास सेंट
    """
    for symbol, (main_unit, sub_unit) in CURRENCY_SYMBOLS.items():
        # Handle formats: ₹500, ₹ 500, Rs 500, Rs. 500
        pattern = re.escape(symbol) + r'\s*([०-९\d]+(?:\.[०-९\d]+)?)'
        def _replace_currency(m, mu=main_unit, su=sub_unit):
            num_str = m.group(1).translate(DEVANAGARI_TO_ARABIC)
            if '.' in num_str:
                integer_part, decimal_part = num_str.split('.', 1)
                result = number_to_marathi_words(int(integer_part)) + ' ' + mu
                if decimal_part and int(decimal_part) > 0:
                    result += ' ' + number_to_marathi_words(int(decimal_part)) + ' ' + su
                return result
            else:
                return number_to_marathi_words(int(num_str)) + ' ' + mu
        text = re.sub(pattern, _replace_currency, text)
    return text


def convert_date(text: str) -> str:
    """Convert common date formats to spoken Marathi.

    26/02/2026 → सव्वीस फेब्रुवारी दोन हजार सव्वीस
    26-02-2026 → same
    02/2026 → फेब्रुवारी दोन हजार सव्वीस
    """
    # DD/MM/YYYY or DD-MM-YYYY
    def _replace_full_date(m):
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        parts = []
        if 1 <= day <= 31:
            parts.append(number_to_marathi_words(day))
        if 1 <= month <= 12:
            parts.append(MONTHS_MARATHI[month])
        parts.append(number_to_marathi_words(year))
        return ' '.join(parts)

    text = re.sub(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', _replace_full_date, text)

    # MM/YYYY
    def _replace_month_year(m):
        month, year = int(m.group(1)), int(m.group(2))
        parts = []
        if 1 <= month <= 12:
            parts.append(MONTHS_MARATHI[month])
        parts.append(number_to_marathi_words(year))
        return ' '.join(parts)

    text = re.sub(r'(\d{1,2})[/\-](\d{4})', _replace_month_year, text)
    return text


def convert_time(text: str) -> str:
    """Convert time formats to spoken Marathi.

    10:30 → दहा वाजून तीस मिनिटे
    2:05 PM → दुपारचे दोन वाजून पाच मिनिटे
    """
    def _replace_time(m):
        hour = int(m.group(1))
        minute = int(m.group(2))
        period = m.group(3) if m.lastindex >= 3 and m.group(3) else ''

        parts = []
        if period:
            period = period.strip().upper()
            if period == 'AM':
                parts.append('सकाळचे' if 6 <= hour <= 11 else 'रात्रीचे')
            elif period == 'PM':
                if hour == 12:
                    parts.append('दुपारचे')
                elif hour <= 4:
                    parts.append('दुपारचे')
                elif hour <= 7:
                    parts.append('संध्याकाळचे')
                else:
                    parts.append('रात्रीचे')

        parts.append(number_to_marathi_words(hour))
        if minute == 0:
            parts.append('वाजले')
        elif minute == 30:
            parts.append('वाजून साडे')
        elif minute == 15:
            parts.append('वाजून सव्वा')
        elif minute == 45:
            parts.append('पावणे ' + number_to_marathi_words(hour + 1))
            return ' '.join(parts[:1] + parts[-1:])  # skip hour word
        else:
            parts.append('वाजून')
            parts.append(number_to_marathi_words(minute))
            parts.append('मिनिटे')

        return ' '.join(parts)

    # HH:MM AM/PM
    text = re.sub(r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm|a\.m\.|p\.m\.)?',
                  _replace_time, text)
    return text


def convert_phone_number(text: str) -> str:
    """Convert phone numbers to digit-by-digit spoken form.

    9876543210 → नऊ आठ सात सहा पाच चार तीन दोन एक शून्य
    +91 98765 43210 → प्लस नऊ एक  नऊ आठ सात सहा पाच  चार तीन दोन एक शून्य
    """
    digit_words = ['शून्य', 'एक', 'दोन', 'तीन', 'चार', 'पाच', 'सहा', 'सात', 'आठ', 'नऊ']

    def _replace_phone(m):
        raw = m.group(0)
        result = []
        for ch in raw:
            if ch.isdigit():
                result.append(digit_words[int(ch)])
            elif ch == '+':
                result.append('प्लस')
            elif ch in ' -':
                result.append(' ')
        return ' '.join(w for w in result if w)

    # Indian mobile: 10 digits, optionally +91 prefix
    text = re.sub(r'\+?\d[\d\s\-]{9,14}\d', _replace_phone, text)
    return text


def convert_percentage(text: str) -> str:
    """Convert percentage to spoken form: 45% → पंचेचाळीस टक्के"""
    def _replace_pct(m):
        num_str = m.group(1).translate(DEVANAGARI_TO_ARABIC)
        if '.' in num_str:
            integer_part, decimal_part = num_str.split('.', 1)
            result = number_to_marathi_words(int(integer_part))
            result += ' दशांश ' + _decimal_to_words(decimal_part)
        else:
            result = number_to_marathi_words(int(num_str))
        return result + ' टक्के'

    text = re.sub(r'([०-९\d]+(?:\.[०-९\d]+)?)\s*%', _replace_pct, text)
    return text


def convert_ordinal(text: str) -> str:
    """Convert ordinal patterns: 1ला → पहिला, 3रा → तिसरा"""
    ordinal_suffixes = r'(ला|रा|रे|री|वा|वी|वे)'

    def _replace_ordinal(m):
        num = int(m.group(1).translate(DEVANAGARI_TO_ARABIC))
        if num in ORDINALS:
            return ORDINALS[num]
        # For larger numbers, add suffix
        return number_to_marathi_words(num) + 'वा'

    text = re.sub(r'([०-९\d]+)' + ordinal_suffixes, _replace_ordinal, text)
    return text


def normalize_numbers_for_tts(text: str) -> str:
    """Master function: normalize ALL number patterns in text for TTS.

    Call order matters — specific patterns (dates, times, currency, phone)
    are matched first, then remaining standalone numbers are converted.
    """
    # First convert Devanagari digits to Arabic for uniform processing
    # (but keep original for patterns that need Devanagari)

    # 1. Protect already-converted patterns with markers
    # 2. Convert specific patterns first (most-specific to least-specific)
    text = convert_currency(text)
    text = convert_date(text)
    text = convert_time(text)
    text = convert_percentage(text)
    text = convert_ordinal(text)
    text = convert_phone_number(text)

    # 3. Convert remaining standalone numbers
    # Match Devanagari or Arabic digit sequences (possibly with decimal point)
    text = re.sub(r'[०-९\d]+(?:\.[०-९\d]+)?', _convert_number_match, text)

    return text
