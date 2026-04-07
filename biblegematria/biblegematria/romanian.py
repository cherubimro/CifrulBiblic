"""Load Romanian Bible text from local bibliaortodoxa.ro HTML files."""

import os
import re

_PACKAGE_DIR = os.path.dirname(__file__)
_DEFAULT_BIBLE_DIR = os.path.join(
    os.path.dirname(_PACKAGE_DIR), '..', 'biblia_ortodoxa_html', 'carti')

# Map our book names to HTML filename prefixes
_BOOK_TO_FILE = {
    # NT
    'Matei': 'Matei', 'Marcu': 'Marcu', 'Luca': 'Luca', 'Ioan': 'Ioan',
    'Fapte': 'Faptele_Apostolilor',
    'Romani': 'Romani', '1Cor': 'I_Corinteni', '2Cor': 'II_Corinteni',
    'Galateni': 'Galateni', 'Efeseni': 'Efeseni', 'Filipeni': 'Filipeni',
    'Coloseni': 'Coloseni', '1Tes': 'I_Tesaloniceni', '2Tes': 'II_Tesaloniceni',
    '1Tim': 'I_Timotei', '2Tim': 'II_Timotei', 'Tit': 'Tit', 'Filimon': 'Filimon',
    'Evrei': 'Evrei', 'Iacov': 'Iacov', '1Petru': 'I_Petru', '2Petru': 'II_Petru',
    '1Ioan': 'I_Ioan', '2Ioan': 'II_Ioan', '3Ioan': 'III_Ioan',
    'Iuda': 'Iuda', 'Apocalipsa': 'Apocalipsa',
    # VT
    'Facerea': 'Facerea', 'Ieșirea': 'Iesirea', 'Leviticul': 'Leviticul',
    'Numeri': 'Numerii', 'Deuteronom': 'Deuteronomul',
    'Iosua': 'Iosua_Navi', 'Judecători': 'Judecatori',
    '1Samuel': 'I_Regi', '2Samuel': 'II_Regi',
    '3Regi': 'III_Regi', '4Regi': 'IV_Regi',
    'Isaia': 'Isaia', 'Ieremia': 'Ieremia', 'Iezechiel': 'Iezechiel',
    'Osea': 'Osea', 'Ioel': 'Ioel', 'Amos': 'Amos', 'Avdie': 'Avdie',
    'Iona': 'Iona', 'Miheia': 'Miheia', 'Naum': 'Naum',
    'Avacum': 'Avacum', 'Sofonie': 'Sofonie',
    'Agheu': 'Agheu', 'Zaharia': 'Zaharia', 'Maleahi': 'Maleahi',
    'Psalmi': 'Psalmii', 'Proverbe': 'Proverbele', 'Iov': 'Iov',
    'Cânt': 'Cantarea_Cantarilor', 'Rut': 'Rut', 'Plângeri': 'Plangerile',
    'Ecleziast': 'Eclesiastul', 'Estera': 'Estera', 'Daniel': 'Daniel',
    'Ezdra': 'Ezdra', 'Neemia': 'Neemia',
    '1Paralipomena': 'I_Paralipomena', '2Paralipomena': 'II_Paralipomena',
}

# Cache loaded verses
_cache = {}


def _load_chapter(book: str, chapter: int, bible_dir: str = None) -> dict:
    """Load a chapter from the Romanian Bible HTML. Returns {verse_num: text}."""
    bdir = bible_dir or _DEFAULT_BIBLE_DIR
    bdir = os.path.abspath(bdir)

    file_prefix = _BOOK_TO_FILE.get(book, book)
    fname = f"{file_prefix}_cap{chapter}.html"
    fpath = os.path.join(bdir, fname)

    if not os.path.exists(fpath):
        return {}

    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    verses = {}
    # Pattern: <tr id=versetN> ... <td>TEXT</td> </tr>
    pattern = re.compile(
        r'<tr\s+id=verset(\d+)>.*?<td>(.*?)</td>\s*</tr>',
        re.DOTALL)

    for match in pattern.finditer(content):
        vnum = int(match.group(1))
        text = match.group(2)
        # Clean HTML tags
        text = re.sub(r'<[^>]+>', '', text).strip()
        # Clean HTML entities
        text = text.replace('&#259;', 'ă').replace('&#226;', 'â')
        text = text.replace('&#238;', 'î').replace('&#351;', 'ș')
        text = text.replace('&#355;', 'ț').replace('&#350;', 'Ș')
        text = text.replace('&#354;', 'Ț').replace('&#194;', 'Â')
        text = text.replace('&raquo;', '»').replace('&laquo;', '«')
        if text:
            verses[vnum] = text

    return verses


def get_verse(book: str, chapter: int, verse: int, bible_dir: str = None,
              max_len: int = 80) -> str:
    """Get Romanian text of a specific verse.

    Args:
        book: Romanian book name (e.g., 'Ioan', 'Facerea')
        chapter: chapter number
        verse: verse number
        max_len: truncate to this length (0 = no truncation)

    Returns verse text or '' if not found.
    """
    cache_key = f"{book}:{chapter}"
    if cache_key not in _cache:
        _cache[cache_key] = _load_chapter(book, chapter, bible_dir)

    text = _cache[cache_key].get(verse, '')
    if max_len and len(text) > max_len:
        text = text[:max_len-1] + '…'
    return text


def parse_ref(ref: str):
    """Parse a reference like 'Ioan 11:25' into (book, chapter, verse)."""
    match = re.match(r'(\S+)\s+(\d+):(\d+)', ref)
    if match:
        return match.group(1), int(match.group(2)), int(match.group(3))
    return None, None, None
