"""Download biblical texts: SBLGNT (Greek NT), Masoretic (Hebrew VT), LXX."""

import os
import urllib.request
import json

# Default data directory
_DEFAULT_DATA = os.path.join(os.path.expanduser('~'), '.biblegematria')

# SBLGNT source: MorphGNT on GitHub (public domain)
_SBLGNT_BASE = 'https://raw.githubusercontent.com/morphgnt/sblgnt/master'
_SBLGNT_BOOKS = [
    '61-Mt', '62-Mk', '63-Lk', '64-Jn', '65-Ac',
    '66-Ro', '67-1Co', '68-2Co', '69-Ga', '70-Eph',
    '71-Php', '72-Col', '73-1Th', '74-2Th', '75-1Ti',
    '76-2Ti', '77-Tit', '78-Phm', '79-Heb', '80-Jas',
    '81-1Pe', '82-2Pe', '83-1Jn', '84-2Jn', '85-3Jn',
    '86-Jud', '87-Re',
]

# Masoretic source: Sefaria API
_SEFARIA_API = 'https://www.sefaria.org/api/texts/'
_MASORETIC_BOOKS = {
    'Genesis': 50, 'Exodus': 40, 'Leviticus': 27, 'Numbers': 36,
    'Deuteronomy': 34, 'Joshua': 24, 'Judges': 21,
    'I_Samuel': 31, 'II_Samuel': 24, 'I_Kings': 22, 'II_Kings': 25,
    'Isaiah': 66, 'Jeremiah': 52, 'Ezekiel': 48,
    'Hosea': 14, 'Joel': 4, 'Amos': 9, 'Obadiah': 1,
    'Jonah': 4, 'Micah': 7, 'Nahum': 3, 'Habakkuk': 3,
    'Zephaniah': 3, 'Haggai': 2, 'Zechariah': 14, 'Malachi': 3,
    'Psalms': 150, 'Proverbs': 31, 'Job': 42,
    'Song_of_Songs': 8, 'Ruth': 4, 'Lamentations': 5,
    'Ecclesiastes': 12, 'Esther': 10, 'Daniel': 12,
    'Ezra': 10, 'Nehemiah': 13, 'I_Chronicles': 29, 'II_Chronicles': 36,
}

# LXX source: OpenScriptures on GitHub
_LXX_BASE = 'https://raw.githubusercontent.com/openscriptures/GreekResources/master/morphgnt-lxx'


def get_data_dir(data_dir: str = None) -> str:
    """Get or create the data directory."""
    d = data_dir or _DEFAULT_DATA
    os.makedirs(d, exist_ok=True)
    return d


def _download(url: str, dest: str, verbose: bool = True):
    """Download a URL to a local file if not already present."""
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return False  # already exists
    if verbose:
        print(f'  Downloading {os.path.basename(dest)}...')
    try:
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as e:
        if verbose:
            print(f'    ERROR: {e}')
        return False


def download_sblgnt(data_dir: str = None, verbose: bool = True) -> str:
    """Download SBLGNT (MorphGNT) Greek NT — 27 books.

    Returns path to the sblgnt/ directory.
    """
    base = get_data_dir(data_dir)
    sblgnt_dir = os.path.join(base, 'sblgnt')
    os.makedirs(sblgnt_dir, exist_ok=True)

    if verbose:
        print(f'Downloading SBLGNT to {sblgnt_dir}/')

    count = 0
    for book in _SBLGNT_BOOKS:
        fname = f'{book}-morphgnt.txt'
        url = f'{_SBLGNT_BASE}/{fname}'
        dest = os.path.join(sblgnt_dir, fname)
        if _download(url, dest, verbose):
            count += 1

    if verbose:
        if count == 0:
            print(f'  All {len(_SBLGNT_BOOKS)} books already present.')
        else:
            print(f'  Downloaded {count} new book(s).')

    return sblgnt_dir


def download_masoretic(data_dir: str = None, verbose: bool = True, books: list = None) -> str:
    """Download Masoretic Hebrew text from Sefaria API.

    Returns path to the textul_masoretic/ directory.
    Note: Sefaria API may rate-limit; be patient.
    """
    base = get_data_dir(data_dir)
    mas_dir = os.path.join(base, 'textul_masoretic')
    os.makedirs(mas_dir, exist_ok=True)

    if verbose:
        print(f'Downloading Masoretic text to {mas_dir}/')

    target_books = books or list(_MASORETIC_BOOKS.keys())
    count = 0

    for book in target_books:
        if book not in _MASORETIC_BOOKS:
            continue
        chapters = _MASORETIC_BOOKS[book]
        dest = os.path.join(mas_dir, f'{book}.txt')

        if os.path.exists(dest) and os.path.getsize(dest) > 100:
            continue

        if verbose:
            print(f'  Downloading {book} ({chapters} chapters)...')

        lines = []
        for ch in range(1, chapters + 1):
            sefaria_name = book.replace('_', ' ')
            url = f'{_SEFARIA_API}{sefaria_name}.{ch}?context=0&language=he'
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'biblegematria/0.1'})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    he_text = data.get('he', [])
                    if isinstance(he_text, list):
                        for vs, verse in enumerate(he_text, 1):
                            if isinstance(verse, str):
                                lines.append(f'{ch}:{vs}\t{verse}')
            except Exception as e:
                if verbose:
                    print(f'    Ch.{ch} error: {e}')

        if lines:
            with open(dest, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
            count += 1

    if verbose:
        if count == 0:
            print(f'  All books already present.')
        else:
            print(f'  Downloaded {count} new book(s).')

    return mas_dir


def download_all(data_dir: str = None, verbose: bool = True) -> dict:
    """Download all available texts.

    Returns dict with paths to each corpus directory.
    """
    return {
        'sblgnt': download_sblgnt(data_dir, verbose),
        'masoretic': download_masoretic(data_dir, verbose),
    }


def status(data_dir: str = None) -> dict:
    """Check which texts are available locally."""
    base = get_data_dir(data_dir)
    result = {}

    sblgnt_dir = os.path.join(base, 'sblgnt')
    if os.path.isdir(sblgnt_dir):
        files = [f for f in os.listdir(sblgnt_dir) if f.endswith('.txt')]
        result['sblgnt'] = {'path': sblgnt_dir, 'books': len(files)}
    else:
        result['sblgnt'] = {'path': None, 'books': 0}

    mas_dir = os.path.join(base, 'textul_masoretic')
    if os.path.isdir(mas_dir):
        files = [f for f in os.listdir(mas_dir) if f.endswith('.txt')]
        result['masoretic'] = {'path': mas_dir, 'books': len(files)}
    else:
        result['masoretic'] = {'path': None, 'books': 0}

    return result
