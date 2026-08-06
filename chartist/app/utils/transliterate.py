# Define a mapping for Persian characters to English strings.
persian_to_english = {
    'ا': 'a',
    'ب': 'b',
    'پ': 'p',
    'ت': 't',
    'ث': 's',
    'ج': 'j',
    'چ': 'ch',
    'ح': 'h',
    'خ': 'kh',
    'د': 'd',
    'ذ': 'z',
    'ر': 'r',
    'ز': 'z',
    'ژ': 'zh',
    'س': 's',
    'ش': 'sh',
    'ص': 's',
    'ض': 'z',
    'ط': 't',
    'ظ': 'z',
    'ع': 'a',
    'غ': 'gh',
    'ف': 'f',
    'ق': 'gh',
    'ک': 'k',
    'گ': 'g',
    'ل': 'l',
    'م': 'm',
    'ن': 'n',
    'و': 'v',
    'ه': 'h',
    'ی': 'y'
}

def transliterate(persian_text):
    english_text = ""
    for char in persian_text:
        # Use the mapping; if a character isn't in the dictionary, keep it unchanged.
        english_text += persian_to_english.get(char, char)
    return english_text
