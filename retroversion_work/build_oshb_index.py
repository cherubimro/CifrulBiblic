#!/usr/bin/env python3
"""
Build OSHB morphology index from Westminster Leningrad Codex XML files.

Outputs:
- morph_index.json: per-word data for all OT — {verse_id: [word_dicts]}
- strongs_he.json: Strong's Hebrew lemma dictionary — {strongs_id: lemma_info}

Usage: python3 build_oshb_index.py
"""
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

SOURCES_DIR = Path('/home/bu/Documents/Biblia/retroversion_work/sources/morphhb/wlc')
OUTPUT_DIR = Path('/home/bu/Documents/Biblia/retroversion_work')
NS = '{http://www.bibletechnologies.net/2003/OSIS/namespace}'

# Strip niqqud + cantillation. Hebrew consonants are U+05D0 to U+05EA.
# Anything else (points U+05B0–U+05C7, cantillation U+0591–U+05AF) gets removed.
HEBREW_CONSONANT_RANGE = (0x05D0, 0x05EA)
HEBREW_FINAL_MAP = {'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ'}
GEMATRIA_VALUES = {
    'א': 1, 'ב': 2, 'ג': 3, 'ד': 4, 'ה': 5, 'ו': 6, 'ז': 7, 'ח': 8, 'ט': 9,
    'י': 10, 'כ': 20, 'ל': 30, 'מ': 40, 'נ': 50, 'ס': 60, 'ע': 70, 'פ': 80, 'צ': 90,
    'ק': 100, 'ר': 200, 'ש': 300, 'ת': 400,
}


def to_consonantal(text: str) -> str:
    """Strip niqqud, cantillation, and morpheme separators. Keep only consonants."""
    result = []
    for ch in text:
        cp = ord(ch)
        if HEBREW_CONSONANT_RANGE[0] <= cp <= HEBREW_CONSONANT_RANGE[1]:
            # Normalize final letters to medial form for gematria
            result.append(HEBREW_FINAL_MAP.get(ch, ch))
    return ''.join(result)


def gematria(consonantal: str) -> int:
    return sum(GEMATRIA_VALUES.get(ch, 0) for ch in consonantal)


def parse_lemma(lemma_attr: str):
    """
    Parse 'b/7225' → (['b'], '7225')
    Parse 'c/d/776' → (['c','d'], '776')
    Parse '1254 a' → ([], '1254')  (strip disambiguator)
    Parse '430' → ([], '430')
    """
    parts = lemma_attr.split('/')
    stem = parts[-1].split()[0]  # strip disambiguator like ' a' or ' b'
    prefixes = parts[:-1]
    return prefixes, stem


def parse_book(xml_path: Path):
    """Yield (verse_id, word_dicts) tuples for one OSIS book file."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    for verse in root.iter(f'{NS}verse'):
        vid = verse.get('osisID')
        if vid is None:
            continue
        words = []
        for w in verse.findall(f'.//{NS}w'):
            text = w.text or ''
            lemma_attr = w.get('lemma', '')
            morph_attr = w.get('morph', '')
            wid = w.get('id', '')
            prefixes, stem_strongs = parse_lemma(lemma_attr)
            consonantal_full = to_consonantal(text)
            # Extract stem portion of the text (after the last '/' if present)
            text_parts = text.split('/')
            stem_text = text_parts[-1] if text_parts else text
            consonantal_stem = to_consonantal(stem_text)
            words.append({
                'text': text,
                'consonantal_full': consonantal_full,
                'consonantal_stem': consonantal_stem,
                'prefixes': prefixes,
                'stem_strongs': stem_strongs,
                'morph': morph_attr,
                'gematria_full': gematria(consonantal_full),
                'gematria_stem': gematria(consonantal_stem),
                'id': wid,
            })
        yield vid, words


def build_strongs_dict(morph_index: dict) -> dict:
    """For each stem_strongs ID, aggregate all its forms and metadata."""
    strongs = defaultdict(lambda: {
        'stem_forms': Counter(),
        'full_forms': Counter(),
        'morphs': Counter(),
        'gematria_stem_values': Counter(),
        'occurrences': 0,
        'first_verses': [],
    })
    for vid, words in morph_index.items():
        for w in words:
            sid = w['stem_strongs']
            if not sid:
                continue
            s = strongs[sid]
            s['stem_forms'][w['consonantal_stem']] += 1
            s['full_forms'][w['consonantal_full']] += 1
            s['morphs'][w['morph']] += 1
            s['gematria_stem_values'][w['gematria_stem']] += 1
            s['occurrences'] += 1
            if len(s['first_verses']) < 5:
                s['first_verses'].append(vid)

    # Clean up: pick canonical form (most common consonantal_stem)
    clean = {}
    for sid, s in strongs.items():
        canonical_stem = s['stem_forms'].most_common(1)[0][0]
        canonical_gem = gematria(canonical_stem)
        clean[sid] = {
            'canonical_stem': canonical_stem,
            'canonical_gematria': canonical_gem,
            'occurrences': s['occurrences'],
            'top_stem_forms': dict(s['stem_forms'].most_common(5)),
            'top_full_forms': dict(s['full_forms'].most_common(5)),
            'top_morphs': dict(s['morphs'].most_common(3)),
            'first_verses': s['first_verses'],
        }
    return clean


def main():
    xml_files = sorted(SOURCES_DIR.glob('*.xml'))
    print(f'Found {len(xml_files)} OSHB XML files.')
    morph_index = {}
    for xml_path in xml_files:
        print(f'  Parsing {xml_path.name}...', end=' ', flush=True)
        count = 0
        for vid, words in parse_book(xml_path):
            morph_index[vid] = words
            count += 1
        print(f'{count} verses')

    total_verses = len(morph_index)
    total_words = sum(len(ws) for ws in morph_index.values())
    print(f'\nTotal verses: {total_verses}')
    print(f'Total words: {total_words}')

    strongs_dict = build_strongs_dict(morph_index)
    print(f'Unique Strong\'s stem IDs: {len(strongs_dict)}')

    # Write outputs
    morph_out = OUTPUT_DIR / 'morph_index.json'
    strongs_out = OUTPUT_DIR / 'strongs_he.json'
    with open(morph_out, 'w', encoding='utf-8') as f:
        json.dump(morph_index, f, ensure_ascii=False, separators=(',', ':'))
    with open(strongs_out, 'w', encoding='utf-8') as f:
        json.dump(strongs_dict, f, ensure_ascii=False, indent=2)

    morph_size_mb = morph_out.stat().st_size / 1024 / 1024
    strongs_size_kb = strongs_out.stat().st_size / 1024
    print(f'\nWrote {morph_out} ({morph_size_mb:.1f} MB)')
    print(f'Wrote {strongs_out} ({strongs_size_kb:.0f} KB)')

    # Sample: show strongs info for a few famous lemmas
    print('\n--- Sample lookups ---')
    for sid in ['430', '7225', '1254', '216', '1697', '7307', '160']:
        if sid in strongs_dict:
            s = strongs_dict[sid]
            print(f"  Strong's H{sid}: {s['canonical_stem']} (gem={s['canonical_gematria']}, occ={s['occurrences']})")


if __name__ == '__main__':
    main()
