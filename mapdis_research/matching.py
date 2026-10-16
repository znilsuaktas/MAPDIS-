"""Unicode-aware phrase matching without matching 'oil' inside 'soil'."""
import re
import unicodedata


def normalized(text):
    value = unicodedata.normalize('NFKD', text.casefold().replace('ı', 'i'))
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', re.sub(r'[-‐‑–—]', ' ', value)).strip()


def contains(text, phrase):
    return bool(re.search(r'(?<!\w)' + re.escape(normalized(phrase)) + r'(?!\w)', normalized(text)))
