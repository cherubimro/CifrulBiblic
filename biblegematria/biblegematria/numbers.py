"""Extract explicit numbers from biblical texts (NT, LXX, Masoretic).

Numbers in ancient texts are written as words (ἑκατὸν πεντήκοντα τρεῖς = 153).
This module parses them and builds an index: number → [(ref, components)].
"""

import os
import re
import json
import unicodedata

# ═══════════════════════════════════════════════════════════════
# GREEK NUMBER WORDS (covers both NT and LXX forms)
# ═══════════════════════════════════════════════════════════════

_GREEK_NUMS = {}

# Units
for w in ['εἷς','μία','ἕν','ἕνα','ἑνός','ἑνί','μιᾷ','μιᾶς','μίαν',
          'ἓν','Ἓν','Εἷς','Ἕν','Ἑνὶ','ἑνὸς','ἑνὶ']: _GREEK_NUMS[w.lower()] = 1
for w in ['δύο','δυσί','δυσίν','δυσὶ','δυσὶν']: _GREEK_NUMS[w.lower()] = 2
for w in ['τρεῖς','τρία','τριῶν','τρισί','τρισίν','τρισὶν']: _GREEK_NUMS[w.lower()] = 3
for w in ['τέσσαρες','τέσσαρα','τεσσάρων','τέσσαρσι','τέσσαρσιν',
          'τέσσαρας']: _GREEK_NUMS[w.lower()] = 4
for w in ['πέντε','Πέντε']: _GREEK_NUMS[w.lower()] = 5
for w in ['ἕξ','ἓξ','Ἓξ','Ἕξ']: _GREEK_NUMS[w.lower()] = 6
for w in ['ἑπτά','ἑπτὰ','Ἑπτά']: _GREEK_NUMS[w.lower()] = 7
for w in ['ὀκτώ','ὀκτὼ']: _GREEK_NUMS[w.lower()] = 8
for w in ['ἐννέα']: _GREEK_NUMS[w.lower()] = 9

# 11-19
for w in ['δέκα']: _GREEK_NUMS[w.lower()] = 10
for w in ['ἕνδεκα']: _GREEK_NUMS[w.lower()] = 11
for w in ['δώδεκα','Δώδεκα']: _GREEK_NUMS[w.lower()] = 12
for w in ['δεκατρεῖς']: _GREEK_NUMS[w.lower()] = 13
for w in ['δεκατέσσαρες','δεκατεσσάρων']: _GREEK_NUMS[w.lower()] = 14
for w in ['δεκαπέντε']: _GREEK_NUMS[w.lower()] = 15
for w in ['δεκαέξ','δεκαὲξ']: _GREEK_NUMS[w.lower()] = 16
for w in ['δεκαεπτά']: _GREEK_NUMS[w.lower()] = 17
for w in ['δεκαοκτώ','δεκαοκτὼ']: _GREEK_NUMS[w.lower()] = 18

# Tens
for w in ['εἴκοσι','εἴκοσιν']: _GREEK_NUMS[w.lower()] = 20
for w in ['τριάκοντα']: _GREEK_NUMS[w.lower()] = 30
for w in ['τεσσεράκοντα','τεσσαράκοντα','Τεσσεράκοντα']: _GREEK_NUMS[w.lower()] = 40
for w in ['πεντήκοντα','Πεντήκοντα']: _GREEK_NUMS[w.lower()] = 50
for w in ['ἑξήκοντα']: _GREEK_NUMS[w.lower()] = 60
for w in ['ἑβδομήκοντα']: _GREEK_NUMS[w.lower()] = 70
for w in ['ὀγδοήκοντα']: _GREEK_NUMS[w.lower()] = 80
for w in ['ἐνενήκοντα']: _GREEK_NUMS[w.lower()] = 90

# Hundreds
for w in ['ἑκατόν','ἑκατὸν','Ἑκατὸν']: _GREEK_NUMS[w.lower()] = 100
for w in ['διακόσιοι','διακοσίων','διακοσίους','διακόσια',
          'διακοσίας','διακόσιαι','Διακοσίων']: _GREEK_NUMS[w.lower()] = 200
for w in ['τριακόσιοι','τριακοσίων','τριακοσίους','τριακόσια',
          'τριακοσίας']: _GREEK_NUMS[w.lower()] = 300
for w in ['τετρακόσιοι','τετρακοσίων','τετρακόσια',
          'τετρακοσίοις']: _GREEK_NUMS[w.lower()] = 400
for w in ['πεντακόσιοι','πεντακοσίων','πεντακόσια',
          'πεντακοσίοις']: _GREEK_NUMS[w.lower()] = 500
for w in ['ἑξακόσιοι','ἑξακοσίων','ἑξακόσια','ἑξακόσιαι',
          'ἑξακοσίους']: _GREEK_NUMS[w.lower()] = 600

# Thousands
for w in ['χίλιοι','χιλίων','χίλια','χιλίους','χιλίας',
          'χιλιάδες','χιλιάδων']: _GREEK_NUMS[w.lower()] = 1000
for w in ['δισχίλιοι','δισχιλίων']: _GREEK_NUMS[w.lower()] = 2000
for w in ['τρισχίλιοι','τρισχιλίων','τρισχίλιαι']: _GREEK_NUMS[w.lower()] = 3000
for w in ['τετρακισχίλιοι','τετρακισχιλίων',
          'τετρακισχιλίους']: _GREEK_NUMS[w.lower()] = 4000
for w in ['πεντακισχίλιοι','πεντακισχιλίων',
          'πεντακισχιλίους']: _GREEK_NUMS[w.lower()] = 5000
for w in ['μύριοι','μυρίων','μυριάδες','μυριάδων',
          'μυριάσιν','μυριάδας','μυρίους']: _GREEK_NUMS[w.lower()] = 10000

# ═══════════════════════════════════════════════════════════════
# HEBREW NUMBER WORDS
# ═══════════════════════════════════════════════════════════════

_HEBREW_NUMS = {
    'אחד':1,'אחת':1,'שנים':2,'שתים':2,'שני':2,'שתי':2,
    'שלש':3,'שלשה':3,'שלשת':3,
    'ארבע':4,'ארבעה':4,'ארבעת':4,
    'חמש':5,'חמשה':5,'חמשת':5,
    'שש':6,'ששה':6,'ששת':6,
    'שבע':7,'שבעה':7,'שבעת':7,
    'שמנה':8,'שמנת':8,
    'תשע':9,'תשעה':9,'תשעת':9,
    'עשר':10,'עשרה':10,'עשרת':10,
    'עשרים':20,'שלשים':30,'ארבעים':40,
    'חמשים':50,'ששים':60,'שבעים':70,
    'שמנים':80,'תשעים':90,
    'מאה':100,'מאת':100,'מאתים':200,
    'אלף':1000,'אלפים':2000,
    'רבבה':10000,'רבבות':10000,
}


def _group_consecutive(num_positions):
    """Group consecutive number words into composite numbers.

    Greek/Hebrew additive system: larger values come first (100+50+3 = 153).
    Groups consecutive number words where values are descending, with max gap of 3.
    """
    if not num_positions:
        return []

    groups = [[num_positions[0]]]
    for j in range(1, len(num_positions)):
        prev_pos = groups[-1][-1][0]
        curr_pos = num_positions[j][0]
        prev_val = groups[-1][-1][1]
        curr_val = num_positions[j][1]

        if curr_pos - prev_pos <= 3 and curr_val < prev_val:
            groups[-1].append(num_positions[j])
        else:
            groups.append([num_positions[j]])

    return groups


def extract_nt_numbers(min_value=1):
    """Extract all explicit numbers from NT (SBLGNT).

    Returns list of (value, ref, components_str).
    """
    from .texts import load_sblgnt

    editorial = re.compile(r'[⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸓⸔⸕⸖⸗]')
    def clean(w):
        return editorial.sub('', w).strip('.,;·:()[]·\u0387')

    nt_bk = {'Mt':'Matei','Mk':'Marcu','Lk':'Luca','Jn':'Ioan','Ac':'Fapte',
              'Ro':'Romani','1Co':'1Cor','2Co':'2Cor','Ga':'Galateni',
              'Eph':'Efeseni','Php':'Filipeni','Col':'Coloseni',
              'Heb':'Evrei','Jas':'Iacov','1Pe':'1Petru','2Pe':'2Petru',
              '1Jn':'1Ioan','Jud':'Iuda','Re':'Apocalipsa'}

    verses = {}
    for w in load_sblgnt():
        bk = nt_bk.get(w['book'], w['book'])
        ref = f"{bk} {w['chapter']}:{w['verse']}"
        verses.setdefault(ref, []).append(clean(w['word']))

    results = []
    for ref, words in verses.items():
        num_pos = []
        for i, word in enumerate(words):
            wl = word.lower()
            if wl in _GREEK_NUMS:
                num_pos.append((i, _GREEK_NUMS[wl], word))

        if not num_pos:
            continue

        for group in _group_consecutive(num_pos):
            total = sum(v for _, v, _ in group)
            desc = '+'.join(f'{w}({v})' for _, v, w in group)
            if total >= min_value:
                results.append((total, ref, desc))

    return sorted(results)


def extract_lxx_numbers(min_value=1):
    """Extract all explicit numbers from LXX (Rahlfs 1935).

    Returns list of (value, ref, components_str).
    """
    data_dir = os.path.join(os.path.expanduser('~'), '.biblegematria', 'lxx')
    results = []

    for fname in sorted(os.listdir(data_dir)):
        if not fname.endswith('.js'):
            continue
        try:
            with open(os.path.join(data_dir, fname), 'r') as f:
                data = json.load(f)
        except:
            continue

        for ref, words in data.items():
            forms = [w.get('form', w.get('key', '')) for w in words]

            num_pos = []
            for i, form in enumerate(forms):
                fl = form.lower()
                if fl in _GREEK_NUMS:
                    num_pos.append((i, _GREEK_NUMS[fl], form))

            if not num_pos:
                continue

            norm_ref = ref.replace('.', ' ', 1).replace('.', ':')
            for group in _group_consecutive(num_pos):
                total = sum(v for _, v, _ in group)
                desc = '+'.join(f'{w}({v})' for _, v, w in group)
                if total >= min_value:
                    results.append((total, norm_ref, desc))

    return sorted(results)


def extract_masoretic_numbers(min_value=1):
    """Extract all explicit numbers from Masoretic Hebrew text.

    Returns list of (value, ref, components_str).
    """
    mas_dir = os.path.join(os.path.expanduser('~'), '.biblegematria', 'textul_masoretic')

    book_names = {
        'Genesis':'Facerea','Exodus':'Ieșirea','Leviticus':'Leviticul',
        'Numbers':'Numeri','Deuteronomy':'Deuteronom',
        'Joshua':'Iosua','Judges':'Judecători','Ruth':'Rut',
        'I_Samuel':'1Samuel','II_Samuel':'2Samuel',
        'I_Kings':'3Regi','II_Kings':'4Regi',
        'I_Chronicles':'1Paralipomena','II_Chronicles':'2Paralipomena',
        'Ezra':'Ezdra','Nehemiah':'Neemia','Esther':'Estera',
        'Job':'Iov','Psalms':'Psalmi','Proverbs':'Proverbe',
        'Ecclesiastes':'Ecleziast','Song_of_Songs':'Cânt',
        'Isaiah':'Isaia','Jeremiah':'Ieremia','Lamentations':'Plângeri',
        'Ezekiel':'Iezechiel','Daniel':'Daniel',
        'Hosea':'Osea','Joel':'Ioel','Amos':'Amos','Obadiah':'Avdie',
        'Jonah':'Iona','Micah':'Miheia','Nahum':'Naum',
        'Habakkuk':'Avacum','Zephaniah':'Sofonie',
        'Haggai':'Agheu','Zechariah':'Zaharia','Malachi':'Maleahi',
    }

    def clean_heb(word):
        w = word.replace('&nbsp;', ' ').replace('&thinsp;', ' ')
        w = re.sub(r'&[a-z]+;', ' ', w)
        w = re.sub(r'\{[^}]*\}', '', w)
        w = w.replace('\u05BE', ' ').replace('׀', ' ')
        w = re.sub(r'[\u0591-\u05C7׃]', '', w)
        return [p for p in w.split() if len(p.strip()) >= 2]

    results = []
    for fname in sorted(os.listdir(mas_dir)):
        if not fname.endswith('.txt'):
            continue
        book = fname.replace('.txt', '')
        ro_book = book_names.get(book, book)

        with open(os.path.join(mas_dir, fname), 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) < 2:
                    continue
                ref_parts = parts[0].split(':')
                if len(ref_parts) != 2:
                    continue
                ref = f"{ro_book} {ref_parts[0]}:{ref_parts[1]}"

                words = []
                for raw in parts[-1].split():
                    words.extend(clean_heb(raw))

                num_pos = []
                for i, w in enumerate(words):
                    if w in _HEBREW_NUMS:
                        num_pos.append((i, _HEBREW_NUMS[w], w))

                if not num_pos:
                    continue

                for group in _group_consecutive(num_pos):
                    total = sum(v for _, v, _ in group)
                    desc = '+'.join(f'{w}({v})' for _, v, w in group)
                    if total >= min_value:
                        results.append((total, ref, desc))

    return sorted(results)


def build_number_index(min_value=12):
    """Build complete index of explicit numbers across all three texts.

    Returns dict: {value: {'nt': [(ref, desc)], 'lxx': [(ref, desc)], 'mas': [(ref, desc)]}}
    """
    index = {}

    for val, ref, desc in extract_nt_numbers(min_value):
        index.setdefault(val, {'nt': [], 'lxx': [], 'mas': []})['nt'].append((ref, desc))

    for val, ref, desc in extract_lxx_numbers(min_value):
        index.setdefault(val, {'nt': [], 'lxx': [], 'mas': []})['lxx'].append((ref, desc))

    for val, ref, desc in extract_masoretic_numbers(min_value):
        index.setdefault(val, {'nt': [], 'lxx': [], 'mas': []})['mas'].append((ref, desc))

    return index
