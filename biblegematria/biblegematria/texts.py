"""Load biblical texts: SBLGNT (Greek NT), Masoretic (Hebrew VT), LXX.

Data is bundled as data.zip in the package. On first use, it's extracted to ~/.biblegematria/.
If data.zip is missing, falls back to downloading from GitHub/Sefaria.
"""

import os
import re
import zipfile

_PACKAGE_DIR = os.path.dirname(__file__)
_DATA_ZIP = os.path.join(_PACKAGE_DIR, 'data.zip')
_DEFAULT_DATA = os.path.join(os.path.expanduser('~'), '.biblegematria')


def _ensure_data(data_dir: str = None) -> str:
    """Ensure biblical texts are available. Extract from ZIP or download."""
    base = data_dir or _DEFAULT_DATA

    # Check if already extracted
    sblgnt_dir = os.path.join(base, 'sblgnt')
    if os.path.isdir(sblgnt_dir) and len(os.listdir(sblgnt_dir)) >= 27:
        return base

    # Try extracting from bundled ZIP
    if os.path.exists(_DATA_ZIP):
        print(f'Extracting biblical texts from data.zip to {base}/ ...')
        os.makedirs(base, exist_ok=True)
        with zipfile.ZipFile(_DATA_ZIP, 'r') as zf:
            zf.extractall(base)
        print(f'  Done: SBLGNT + Masoretic + LXX extracted.')
        return base

    # Fallback: download
    from .download import download_all
    print('data.zip not found. Downloading texts from internet...')
    download_all(data_dir=base)
    return base


def load_sblgnt(book: str = None, chapter: int = None, verse: int = None,
                data_dir: str = None) -> list:
    """Load SBLGNT morphologically tagged Greek NT.

    Returns list of dicts with keys: ref, book, chapter, verse, word, lemma.
    If book is specified, filters to that book (e.g., '64-Jn', '62-Mk').
    """
    base = _ensure_data(data_dir)
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


def load_masoretic(book: str = None, data_dir: str = None) -> list:
    """Load Masoretic Hebrew text.

    Returns list of dicts with keys: book, chapter, verse, text, words.
    """
    base = _ensure_data(data_dir)
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
                if len(parts) >= 2:
                    ref_parts = parts[0].split(':')
                    ch = int(ref_parts[0]) if ref_parts[0].isdigit() else 0
                    vs = int(ref_parts[1]) if len(ref_parts) > 1 and ref_parts[1].isdigit() else 0
                    text = parts[-1]
                    # Strip cantillation marks, keep consonants + vowels
                    words = []
                    for w in text.split():
                        clean = re.sub(r'[\u0591-\u05AF\u05BD\u05BF\u05C0\u05C3-\u05C7]', '', w)
                        if clean:
                            words.append(clean)
                    results.append({
                        'book': fname.replace('.txt', ''),
                        'chapter': ch,
                        'verse': vs,
                        'text': text,
                        'words': words,
                    })
    return results


def load_lxx(book: str = None, data_dir: str = None) -> list:
    """Load LXX (Septuagint) text.

    Returns list of dicts with keys: ref, word, lemma.
    """
    import json

    base = _ensure_data(data_dir)
    lxx_dir = os.path.join(base, 'lxx')
    results = []

    for fname in sorted(os.listdir(lxx_dir)):
        if not fname.endswith('.js'):
            continue
        if book and book.lower() not in fname.lower():
            continue

        fpath = os.path.join(lxx_dir, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        try:
            data = json.loads(content)
            for ref, words in data.items():
                if isinstance(words, list):
                    for entry in words:
                        if isinstance(entry, dict):
                            results.append({
                                'ref': ref,
                                'word': entry.get('key', ''),
                                'lemma': entry.get('lemma', ''),
                            })
        except json.JSONDecodeError:
            pass

    return results
