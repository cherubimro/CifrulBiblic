"""Load biblical texts: SBLGNT (Greek NT), Masoretic (Hebrew VT), LXX."""

import os
import re


def _find_data_dir():
    """Find the biblical texts directory relative to this package or in common locations."""
    candidates = [
        os.path.join(os.path.dirname(__file__), '..', '..'),  # biblegematria/../..
        os.path.expanduser('~/Documents/Biblia'),
        '.',
    ]
    for c in candidates:
        if os.path.isdir(os.path.join(c, 'sblgnt')):
            return os.path.abspath(c)
    return None


def load_sblgnt(book: str = None, chapter: int = None, verse: int = None) -> list:
    """Load SBLGNT morphologically tagged Greek NT.

    Returns list of dicts with keys: ref, book, chapter, verse, word, lemma.
    If book is specified, filters to that book (e.g., '64-Jn', '62-Mk').
    """
    base = _find_data_dir()
    if not base:
        raise FileNotFoundError("Cannot find sblgnt/ directory")

    sblgnt_dir = os.path.join(base, 'sblgnt')
    results = []

    for fname in sorted(os.listdir(sblgnt_dir)):
        if not fname.endswith('-morphgnt.txt'):
            continue
        if book and book not in fname:
            continue

        with open(os.path.join(sblgnt_dir, fname), 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 4:
                    continue
                ref = parts[0]
                ch = int(ref[2:4])
                vs = int(ref[4:6])

                if chapter is not None and ch != chapter:
                    continue
                if verse is not None and vs != verse:
                    continue

                word = parts[3].rstrip('.,;·:')
                lemma = parts[-1] if len(parts) > 4 else word

                results.append({
                    'ref': ref,
                    'book': fname.split('-')[1] if '-' in fname else fname,
                    'chapter': ch,
                    'verse': vs,
                    'word': word,
                    'lemma': lemma,
                })
    return results


def load_masoretic(book: str = None) -> list:
    """Load Masoretic Hebrew text.

    Returns list of dicts with keys: book, chapter, verse, word.
    """
    base = _find_data_dir()
    if not base:
        raise FileNotFoundError("Cannot find textul_masoretic/ directory")

    mas_dir = os.path.join(base, 'textul_masoretic')
    results = []

    for fname in sorted(os.listdir(mas_dir)):
        if not fname.endswith('.txt'):
            continue
        if book and book.lower() not in fname.lower():
            continue

        with open(os.path.join(mas_dir, fname), 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 3:
                    ref_parts = parts[0].split(':')
                    ch = int(ref_parts[0]) if ref_parts[0].isdigit() else 0
                    vs = int(ref_parts[1]) if len(ref_parts) > 1 and ref_parts[1].isdigit() else 0
                    text = parts[-1]
                    for word in text.split():
                        word = re.sub(r'[\u0591-\u05C7]', '', word)  # strip cantillation
                        if word:
                            results.append({
                                'book': fname.replace('.txt', ''),
                                'chapter': ch,
                                'verse': vs,
                                'word': word,
                            })
    return results


def load_lxx(book: str = None) -> list:
    """Load LXX (Septuagint) text.

    Returns list of dicts with keys: book, chapter, verse, word.
    """
    base = _find_data_dir()
    if not base:
        raise FileNotFoundError("Cannot find lxx/ directory")

    lxx_dir = os.path.join(base, 'lxx')
    results = []

    for fname in sorted(os.listdir(lxx_dir)):
        if book and book.lower() not in fname.lower():
            continue
        fpath = os.path.join(lxx_dir, fname)
        if os.path.isfile(fpath) and fname.endswith(('.txt', '.json', '.js')):
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
                # Basic word extraction — adapt based on actual format
                words = re.findall(r'[\u0370-\u03FF\u1F00-\u1FFF]+', content)
                for w in words:
                    results.append({
                        'book': fname,
                        'chapter': 0,
                        'verse': 0,
                        'word': w,
                    })
    return results
