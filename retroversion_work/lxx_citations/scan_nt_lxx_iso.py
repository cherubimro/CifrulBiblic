#!/usr/bin/env python3
"""
Scan NT citations of LXX for cases where the NT author replaces a word
from the LXX with a DIFFERENT word that has the SAME isopsephy.

Inputs:
  - blb_parallels.tsv: NT reference → OT reference citation list
  - /home/bu/Documents/Biblia/sblgnt/*.txt: SBLGNT morphgnt text files
  - /home/bu/Documents/Biblia/lxx/*.js: Rahlfs 1935 LXX JSON files

Output:
  - For each citation, list words present in NT but NOT in LXX source
    that have the same isopsephy as a word in the LXX source (or a
    theologically significant value).
  - Reports pairs with different semantic meaning but identical iso.

Note on versification: LXX uses Rahlfs 1935 numbering, which differs
from the Masoretic Text in several books. BLB uses MT numbering. This
script applies known corrections (Ps, Jer).
"""
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, '/home/bu/Documents/Biblia')
from biblegematria.biblegematria import isopsephy

ROOT = Path('/home/bu/Documents/Biblia')
SBLGNT_DIR = ROOT / 'sblgnt'
LXX_DIR = ROOT / 'lxx'
WORK = ROOT / 'retroversion_work' / 'lxx_citations'

# SBLGNT book code map (first 2 digits in verse ID)
SBLGNT_BOOKS = {
    '01': ('Mt',  '61-Mt-morphgnt.txt'),
    '02': ('Mk',  '62-Mk-morphgnt.txt'),
    '03': ('Lk',  '63-Lk-morphgnt.txt'),
    '04': ('Jn',  '64-Jn-morphgnt.txt'),
    '05': ('Ac',  '65-Ac-morphgnt.txt'),
    '06': ('Ro',  '66-Ro-morphgnt.txt'),
    '07': ('1Co', '67-1Co-morphgnt.txt'),
    '08': ('2Co', '68-2Co-morphgnt.txt'),
    '09': ('Ga',  '69-Ga-morphgnt.txt'),
    '10': ('Eph', '70-Eph-morphgnt.txt'),
    '11': ('Php', '71-Php-morphgnt.txt'),
    '12': ('Col', '72-Col-morphgnt.txt'),
    '13': ('1Th', '73-1Th-morphgnt.txt'),
    '14': ('2Th', '74-2Th-morphgnt.txt'),
    '15': ('1Ti', '75-1Ti-morphgnt.txt'),
    '16': ('2Ti', '76-2Ti-morphgnt.txt'),
    '17': ('Tit', '77-Tit-morphgnt.txt'),
    '18': ('Phm', '78-Phm-morphgnt.txt'),
    '19': ('Heb', '79-Heb-morphgnt.txt'),
    '20': ('Jas', '80-Jas-morphgnt.txt'),
    '21': ('1Pe', '81-1Pe-morphgnt.txt'),
    '22': ('2Pe', '82-2Pe-morphgnt.txt'),
    '23': ('1Jn', '83-1Jn-morphgnt.txt'),
    '24': ('2Jn', '84-2Jn-morphgnt.txt'),
    '25': ('3Jn', '85-3Jn-morphgnt.txt'),
    '26': ('Jud', '86-Jud-morphgnt.txt'),
    '27': ('Re',  '87-Re-morphgnt.txt'),
}

# Reverse: BLB abbreviation → SBLGNT book code (01..27)
BLB_TO_SBLGNT = {
    'Mat': '01', 'Mar': '02', 'Luk': '03', 'Jhn': '04', 'Act': '05',
    'Rom': '06', '1Co': '07', '2Co': '08', 'Gal': '09', 'Eph': '10',
    'Phl': '11', 'Col': '12', '1Th': '13', '2Th': '14', '1Ti': '15',
    '2Ti': '16', 'Tit': '17', 'Phm': '18', 'Heb': '19', 'Jas': '20',
    '1Pe': '21', '2Pe': '22', '1Jo': '23', '2Jo': '24', '3Jo': '25',
    'Jde': '26', 'Rev': '27',
}

# BLB OT → LXX .js filename
BLB_TO_LXX = {
    'Gen': 'Gen', 'Exo': 'Exod', 'Lev': 'Lev', 'Num': 'Num',
    'Deu': 'Deut', 'Jos': 'Josh', 'Jdg': 'Judg', 'Rut': 'Ruth',
    '1Sa': '1Sam', '2Sa': '2Sam', '1Ki': '1Kgs', '2Ki': '2Kgs',
    '1Ch': '1Chr', '2Ch': '2Chr', 'Ezr': '2Esd', 'Neh': '2Esd',
    'Est': 'Esth', 'Job': 'Job', 'Psa': 'Ps', 'Pro': 'Prov',
    'Ecc': 'Eccl', 'Sng': 'Song', 'Isa': 'Isa', 'Jer': 'Jer',
    'Lam': 'Lam', 'Ezk': 'Ezek', 'Eze': 'Ezek', 'Dan': 'Dan',
    'Hos': 'Hos', 'Joe': 'Joel', 'Amo': 'Amos', 'Oba': 'Obad',
    'Jon': 'Jonah', 'Mic': 'Mic', 'Nah': 'Nah', 'Hab': 'Hab',
    'Zep': 'Zeph', 'Hag': 'Hag', 'Zec': 'Zech', 'Mal': 'Mal',
}

# LXX verse reference prefix (used as key in the LXX JSON)
# matches the JS file name, e.g. "Isa.40.3"
LXX_PREFIX_FROM_BLB = {
    'Gen': 'Gen', 'Exo': 'Exod', 'Lev': 'Lev', 'Num': 'Num',
    'Deu': 'Deut', 'Jos': 'Josh', 'Jdg': 'Judg',
    '1Sa': '1Sam', '2Sa': '2Sam', '1Ki': '1Kgs', '2Ki': '2Kgs',
    'Psa': 'Ps', 'Pro': 'Prov', 'Isa': 'Isa', 'Jer': 'Jer',
    'Lam': 'Lam', 'Ezk': 'Ezek', 'Eze': 'Ezek', 'Dan': 'Dan',
    'Hos': 'Hos', 'Joe': 'Joel', 'Amo': 'Amos', 'Jon': 'Jonah',
    'Mic': 'Mic', 'Nah': 'Nah', 'Hab': 'Hab', 'Zep': 'Zeph',
    'Hag': 'Hag', 'Zec': 'Zech', 'Mal': 'Mal',
    'Job': 'Job', 'Ecc': 'Eccl',
}

# MT→LXX verse offset corrections (applied when fetching LXX)
# Psalms: MT 10-147 are shifted in LXX (Ps 9-10 joined, etc.)
# Jeremiah: chapters 25-52 have different order
# Full mapping would be complex; for now we only adjust the most common cases.

def mt_to_lxx_psalm(ch, verse):
    """Convert MT Psalm (book, chapter, verse) to LXX reference."""
    # MT Ps 10-113 = LXX Ps 9-112 (merged 9-10)
    # MT Ps 115 = LXX Ps 113:9 onwards
    # MT Ps 116 = LXX Ps 114+115
    # MT Ps 117-146 = LXX Ps 116-145
    # MT Ps 147 = LXX Ps 146+147
    # Simplified: for Ps 10-146, shift by -1
    try:
        ch = int(ch)
        if 10 <= ch <= 146:
            return str(ch - 1), verse
    except ValueError:
        pass
    return str(ch), verse


def parse_blb_ref(ref):
    """Parse BLB reference like 'Mat 21:5' or 'Psa 118:22,23' or 'Isa 9:1,2'.

    Returns list of (book_code, chapter, verses) tuples, where verses is
    a list of verse numbers.
    """
    m = re.match(r'^(\w{3})\s+(\d+):([\d,\-]+)$', ref.strip())
    if not m:
        return []
    book, ch, verses_str = m.groups()
    verses = []
    for part in verses_str.split(','):
        if '-' in part:
            a, b = part.split('-')
            verses.extend(range(int(a), int(b) + 1))
        else:
            try:
                verses.append(int(part))
            except ValueError:
                continue
    return [(book, ch, [str(v) for v in verses])]


def load_sblgnt():
    """Load SBLGNT into {(book_code, chapter, verse): [words]} dict."""
    verses = defaultdict(list)
    for code, (abbr, filename) in SBLGNT_BOOKS.items():
        path = SBLGNT_DIR / filename
        if not path.exists():
            continue
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 6:
                    continue
                verse_id = parts[0]  # e.g. "010101"
                if len(verse_id) != 6:
                    continue
                book_code = verse_id[:2]
                chapter = str(int(verse_id[2:4]))
                verse = str(int(verse_id[4:6]))
                word = parts[-2]  # normalized form
                verses[(book_code, chapter, verse)].append(word)
    return verses


def load_lxx_book(blb_book):
    """Load a single LXX book JSON. Returns {(chapter, verse): [word_forms]}."""
    lxx_file = LXX_PREFIX_FROM_BLB.get(blb_book)
    if not lxx_file:
        return {}
    path = LXX_DIR / f'{lxx_file}.js'
    if not path.exists():
        return {}
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    verses = {}
    prefix = f'{lxx_file}.'
    for key, tokens in data.items():
        if not key.startswith(prefix):
            continue
        rest = key[len(prefix):]
        try:
            ch, verse = rest.split('.', 1)
        except ValueError:
            continue
        forms = [t['form'] for t in tokens if 'form' in t]
        verses[(ch, verse)] = forms
    return verses


def strip_accents(word):
    w = unicodedata.normalize('NFD', word.lower())
    return ''.join(c for c in w if unicodedata.category(c) != 'Mn')


EDITORIAL_RE = re.compile(r'[⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸓⸔⸕⸖⸗]')
STRIP_CHARS = '.,;·:[]·\u0387'  # NOT () — they come in the middle

def clean(word):
    """Strip editorial markers AND the parentheses used for movable nu
    (e.g. εἶπε(ν → εἶπεν); also strip leading/trailing punctuation."""
    w = EDITORIAL_RE.sub('', word)
    # Remove parentheses entirely (they mark optional letters in SBLGNT)
    w = w.replace('(', '').replace(')', '')
    return w.strip(STRIP_CHARS)


def main():
    print('Loading SBLGNT...', file=sys.stderr)
    sblgnt = load_sblgnt()
    print(f'  {len(sblgnt)} NT verses loaded', file=sys.stderr)

    # Cache LXX books on demand
    lxx_cache = {}

    def get_lxx(book, chapter, verse):
        """Fetch a LXX verse as list of word forms (accent-stripped for matching)."""
        if book not in lxx_cache:
            lxx_cache[book] = load_lxx_book(book)
        verses = lxx_cache[book]
        # apply Ps MT→LXX shift
        if book == 'Psa':
            chapter, verse = mt_to_lxx_psalm(chapter, verse)
        return verses.get((chapter, verse), [])

    # Load citation list (merged BLB + openBible)
    citations = []
    merged = WORK / 'merged_citations.tsv'
    fallback = WORK / 'blb_parallels.tsv'
    citation_file = merged if merged.exists() else fallback
    with open(citation_file, encoding='utf-8') as f:
        next(f)  # skip header
        for line in f:
            line = line.strip()
            if not line:
                continue
            nt, ot = line.split('\t', 1)
            citations.append((nt, ot))
    print(f'  {len(citations)} citations loaded', file=sys.stderr)

    # For each citation, collect all NT words and all LXX words, find
    # lexical differences with same iso
    findings = []
    not_found_nt = 0
    not_found_lxx = 0

    for nt_ref, ot_ref in citations:
        nt_parsed = parse_blb_ref(nt_ref)
        ot_parsed = parse_blb_ref(ot_ref)
        if not nt_parsed or not ot_parsed:
            continue

        nt_words = []
        for book, ch, verses in nt_parsed:
            code = BLB_TO_SBLGNT.get(book)
            if not code:
                continue
            for v in verses:
                words = sblgnt.get((code, ch, v), [])
                nt_words.extend(words)

        lxx_words = []
        for book, ch, verses in ot_parsed:
            for v in verses:
                words = get_lxx(book, ch, v)
                lxx_words.extend(words)

        if not nt_words:
            not_found_nt += 1
            continue
        if not lxx_words:
            not_found_lxx += 1
            continue

        # Clean and strip accents for matching
        nt_clean = [(clean(w), strip_accents(clean(w))) for w in nt_words]
        lxx_clean = [(clean(w), strip_accents(clean(w))) for w in lxx_words]

        nt_stripped_set = {s for _, s in nt_clean if s}
        lxx_stripped_set = {s for _, s in lxx_clean if s}

        # Words in NT but NOT in LXX source (candidate replacements)
        nt_only = [(orig, stripped) for orig, stripped in nt_clean
                   if stripped and stripped not in lxx_stripped_set]
        lxx_only = [(orig, stripped) for orig, stripped in lxx_clean
                    if stripped and stripped not in nt_stripped_set]

        # Build iso maps
        lxx_iso = {}
        for orig, _ in lxx_only:
            iso = isopsephy(orig)
            if iso <= 0:
                continue
            lxx_iso.setdefault(iso, []).append(orig)

        # For each NT-only word, check if iso matches any LXX-only word
        for orig, _ in nt_only:
            iso = isopsephy(orig)
            if iso <= 0:
                continue
            if iso in lxx_iso:
                findings.append({
                    'nt_ref': nt_ref,
                    'ot_ref': ot_ref,
                    'nt_word': orig,
                    'lxx_words': lxx_iso[iso],
                    'iso': iso,
                    'nt_text': ' '.join(clean(w) for w in nt_words),
                    'lxx_text': ' '.join(clean(w) for w in lxx_words),
                })

    print(f'\nLookup failures: NT={not_found_nt}, LXX={not_found_lxx}', file=sys.stderr)
    print(f'Total isopsephy-match findings: {len(findings)}', file=sys.stderr)

    # Deduplicate and rank
    # Filter: exclude cases where NT word and LXX word are just stopwords
    STOPWORDS = {
        'καί', 'δέ', 'γάρ', 'οὖν', 'ἐν', 'εἰς', 'ἐκ', 'ἐπί', 'πρός',
        'ἀπό', 'διά', 'περί', 'ὑπό', 'κατά', 'μετά', 'παρά', 'ὑπέρ',
        'τῷ', 'τοῦ', 'τήν', 'τόν', 'τῆς', 'τό', 'τά', 'τῆ',
        'αὐτοῦ', 'αὐτῷ', 'αὐτόν', 'αὐτῆς', 'αὐτῶν', 'αὐτῇ',
        'ὁ', 'ἡ', 'τό', 'ὅς', 'οὗ', 'ᾧ', 'ὅν', 'ἥ',
    }

    def is_stopword(w):
        w_stripped = strip_accents(w)
        return any(strip_accents(s) == w_stripped for s in STOPWORDS)

    print('\n=== Findings (NT word ↔ LXX word, same iso, different word) ===\n')
    seen = set()
    kept = []
    for f in findings:
        if is_stopword(f['nt_word']):
            continue
        lxx_non_stop = [w for w in f['lxx_words'] if not is_stopword(w)]
        if not lxx_non_stop:
            continue
        key = (f['nt_ref'], f['nt_word'], tuple(sorted(lxx_non_stop)))
        if key in seen:
            continue
        seen.add(key)
        kept.append({**f, 'lxx_words': lxx_non_stop})

    print(f'After dedup and stopword filter: {len(kept)}\n')
    for f in kept:
        lxx_str = ', '.join(f['lxx_words'])
        print(f"  {f['nt_ref']:18} ← {f['ot_ref']:18}  {f['nt_word']:16} = {lxx_str:30} (iso {f['iso']})")
        print(f"    NT:  {f['nt_text'][:140]}")
        print(f"    LXX: {f['lxx_text'][:140]}")
        print()

    # Save to JSON
    with open(WORK / 'findings.json', 'w', encoding='utf-8') as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)
    print(f'\nSaved to {WORK / "findings.json"}', file=sys.stderr)


if __name__ == '__main__':
    main()
