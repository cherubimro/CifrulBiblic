#!/usr/bin/env python3
"""
Parse Delitzsch Hebrew NT OSIS XML into a verse-keyed JSON + word list.

Outputs:
- delitzsch_verses.json: {verse_id: {text, words, consonantal_words}}

Delitzsch format is simpler than OSHB: verses contain raw Hebrew text
without per-word morph tags. We split on whitespace and Maqef (־).
"""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

SOURCE = Path('/home/bu/Documents/Biblia/retroversion_work/sources/HebDelitzsch/base.osis')
OUTPUT = Path('/home/bu/Documents/Biblia/retroversion_work/delitzsch_verses.json')
NS = '{http://www.bibletechnologies.net/2003/OSIS/namespace}'

# Punctuation and separators to remove before tokenization
HEBREW_PUNCT = re.compile(r'[׃׀״׳]')  # Hebrew sof pasuq, paseq, etc.
NIQQUD_RE = re.compile(r'[\u0591-\u05C7]')  # all Hebrew points and cantillation
MAQEF = '־'  # Hebrew compound separator

HEBREW_CONSONANT_RANGE = (0x05D0, 0x05EA)
HEBREW_FINAL_MAP = {'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ'}
GEMATRIA_VALUES = {
    'א': 1, 'ב': 2, 'ג': 3, 'ד': 4, 'ה': 5, 'ו': 6, 'ז': 7, 'ח': 8, 'ט': 9,
    'י': 10, 'כ': 20, 'ל': 30, 'מ': 40, 'נ': 50, 'ס': 60, 'ע': 70, 'פ': 80, 'צ': 90,
    'ק': 100, 'ר': 200, 'ש': 300, 'ת': 400,
}


def to_consonantal(text: str) -> str:
    """Strip niqqud, punctuation, keep only Hebrew consonants; normalize final letters."""
    # Remove cantillation and niqqud
    text = NIQQUD_RE.sub('', text)
    # Remove punctuation
    text = HEBREW_PUNCT.sub('', text)
    result = []
    for ch in text:
        cp = ord(ch)
        if HEBREW_CONSONANT_RANGE[0] <= cp <= HEBREW_CONSONANT_RANGE[1]:
            result.append(HEBREW_FINAL_MAP.get(ch, ch))
    return ''.join(result)


def gematria(consonantal: str) -> int:
    return sum(GEMATRIA_VALUES.get(ch, 0) for ch in consonantal)


def tokenize_verse(raw: str):
    """
    Split Hebrew verse text into words. Maqef (־) joins multi-word compounds —
    we treat these as SEPARATE tokens AND we preserve the unified compound.

    For example, "בַּר־אַבָּא" (Barabbas) yields three tokens:
      - "בר" (sub-token 1)
      - "אבא" (sub-token 2)
      - "בראבא" (unified compound, letters only)
    So both gematria(sub) and gematria(compound) are queryable downstream.
    """
    # Remove sof pasuq and other punctuation
    clean = HEBREW_PUNCT.sub('', raw)
    # Split on whitespace first
    tokens = []
    for chunk in clean.split():
        parts = chunk.split(MAQEF)
        if len(parts) == 1:
            tokens.append(chunk)
        else:
            # Emit the sub-tokens
            for p in parts:
                if p:
                    tokens.append(p)
            # Also emit the unified compound (all parts concatenated)
            compound = ''.join(parts)
            if compound:
                tokens.append(compound)
    return tokens


def main():
    print(f'Parsing {SOURCE.name}...')
    tree = ET.parse(SOURCE)
    root = tree.getroot()

    verses = {}
    for verse in root.iter(f'{NS}verse'):
        vid = verse.get('osisID')
        if vid is None:
            continue
        raw_text = (verse.text or '').strip()
        tokens = tokenize_verse(raw_text)
        consonantal_tokens = []
        gem_values = []
        for tok in tokens:
            cons = to_consonantal(tok)
            if cons:  # skip tokens with no Hebrew letters
                consonantal_tokens.append(cons)
                gem_values.append(gematria(cons))
        verses[vid] = {
            'text': raw_text,
            'words_pointed': tokens,
            'words_consonantal': consonantal_tokens,
            'gematria_per_word': gem_values,
        }

    print(f'Parsed {len(verses)} verses')

    # Stats
    word_count = sum(len(v['words_consonantal']) for v in verses.values())
    print(f'Total words: {word_count}')
    # Top 20 most frequent Hebrew consonantal words
    from collections import Counter
    all_words = []
    for v in verses.values():
        all_words.extend(v['words_consonantal'])
    top = Counter(all_words).most_common(20)
    print(f'\nTop 20 most frequent Hebrew words in Delitzsch NT:')
    for w, c in top:
        print(f"  {w:10} ({gematria(w):>5}): {c}")

    # Write output
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(verses, f, ensure_ascii=False, separators=(',', ':'))
    size_mb = OUTPUT.stat().st_size / 1024 / 1024
    print(f'\nWrote {OUTPUT} ({size_mb:.1f} MB)')

    # Verify key verses
    print('\n--- Key verses verification ---')
    keys = ['Matt.1.1', 'John.1.1', 'John.1.14', 'John.21.11', 'Acts.27.37', 'Rev.13.18']
    for k in keys:
        if k in verses:
            print(f"\n{k}:")
            print(f"  text: {verses[k]['text']}")
            print(f"  consonantal: {' '.join(verses[k]['words_consonantal'])}")
            print(f"  gematria per word: {verses[k]['gematria_per_word']}")


if __name__ == '__main__':
    main()
