#!/usr/bin/env python3
"""
Verse-level alignment: SBLGNT (Greek) ↔ Delitzsch Hebrew NT.

Strategy (Method 1 — co-occurrence frequency):
1. Group SBLGNT words by verse.
2. Map SBLGNT book codes to Delitzsch OSIS book IDs.
3. For each aligned verse pair, collect (greek_lemma, hebrew_consonantal_word) co-occurrences.
4. For each Greek lemma, aggregate across all verses.
5. Score each (Greek, Hebrew) pair by: P(H|G) × log(count(G,H))
6. Output: greek_lemma → ranked list of Hebrew candidates.

Output file: alignment_raw.json
"""
import json
import math
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path

sys.path.insert(0, '/home/bu/Documents/Biblia')
from biblegematria.biblegematria import load_sblgnt

WORK = Path('/home/bu/Documents/Biblia/retroversion_work')

# Mirror scan.py's _clean_greek so lemmas match lexicon_ro.json keys
_EDITORIAL_RE = re.compile(r'[⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸓⸔⸕⸖⸗]')


def clean_greek(word):
    w = _EDITORIAL_RE.sub('', word)
    w = w.strip('.,;·:()[]·\u0387')
    return w

# SBLGNT book code → Delitzsch OSIS book ID
BOOK_MAP = {
    'Mt': 'Matt', 'Mk': 'Mark', 'Lk': 'Luke', 'Jn': 'John',
    'Ac': 'Acts', 'Ro': 'Rom',
    '1Co': '1Cor', '2Co': '2Cor',
    'Ga': 'Gal', 'Eph': 'Eph', 'Php': 'Phil', 'Col': 'Col',
    '1Th': '1Thess', '2Th': '2Thess',
    '1Ti': '1Tim', '2Ti': '2Tim', 'Tit': 'Titus', 'Phm': 'Phlm',
    'Heb': 'Heb', 'Jas': 'Jas',
    '1Pe': '1Pet', '2Pe': '2Pet',
    '1Jn': '1John', '2Jn': '2John', '3Jn': '3John',
    'Jud': 'Jude', 'Re': 'Rev',
}


def group_sblgnt_by_verse(sblgnt_words):
    """Group into {verse_id: [(form, lemma), ...]} with scan.py-compatible cleaning."""
    verses = defaultdict(list)
    skipped_books = Counter()
    for w in sblgnt_words:
        gbook = w['book']
        dbook = BOOK_MAP.get(gbook)
        if dbook is None:
            skipped_books[gbook] += 1
            continue
        vid = f"{dbook}.{w['chapter']}.{w['verse']}"
        verses[vid].append((clean_greek(w['word']), clean_greek(w['lemma'])))
    if skipped_books:
        print(f'Skipped books not mapped: {dict(skipped_books)}', file=sys.stderr)
    return verses


def load_delitzsch():
    with open(WORK / 'delitzsch_verses.json', encoding='utf-8') as f:
        return json.load(f)


def build_cooccurrence(greek_verses, delitzsch_verses):
    """For each (greek_lemma, hebrew_word) pair, count co-occurrences."""
    # greek_lemma → Counter of hebrew words
    lemma_heb_counts = defaultdict(Counter)
    # For normalization
    lemma_verse_count = Counter()   # how many verses contain lemma
    hebrew_verse_count = Counter()  # how many verses contain hebrew word
    total_verses = 0
    missing_delitzsch = 0

    for vid, greek_words in greek_verses.items():
        d_verse = delitzsch_verses.get(vid)
        if d_verse is None:
            missing_delitzsch += 1
            continue
        total_verses += 1
        hebrew_set = set(d_verse['words_consonantal'])
        greek_lemma_set = set(lemma for (form, lemma) in greek_words)
        for lemma in greek_lemma_set:
            lemma_verse_count[lemma] += 1
        for hword in hebrew_set:
            hebrew_verse_count[hword] += 1
        # Co-occurrences (set-based, not weighted by count within verse)
        for lemma in greek_lemma_set:
            for hword in hebrew_set:
                lemma_heb_counts[lemma][hword] += 1

    print(f'  Aligned verses: {total_verses}')
    print(f'  Verses missing in Delitzsch: {missing_delitzsch}')
    print(f'  Unique Greek lemmas: {len(lemma_verse_count)}')
    print(f'  Unique Hebrew words: {len(hebrew_verse_count)}')
    return lemma_heb_counts, lemma_verse_count, hebrew_verse_count, total_verses


def score_alignments(lemma_heb_counts, lemma_verse_count, hebrew_verse_count, total_verses,
                     min_lemma_count=1, min_hebrew_count=1, top_k=10):
    """
    Score each (lemma, hebrew) pair using Pointwise Mutual Information (PMI)
    weighted by log(count).
    """
    alignments = {}
    for lemma, heb_counter in lemma_heb_counts.items():
        L_total = lemma_verse_count[lemma]
        if L_total < min_lemma_count:
            continue
        scored = []
        for hword, count in heb_counter.items():
            H_total = hebrew_verse_count[hword]
            if H_total < min_hebrew_count:
                continue
            if count < min_lemma_count:
                continue
            # PMI: log( P(L,H) / (P(L)*P(H)) )
            #    = log( (count/total) / ((L_total/total)*(H_total/total)) )
            #    = log( count*total / (L_total*H_total) )
            p_joint = count / total_verses
            p_lemma = L_total / total_verses
            p_hebrew = H_total / total_verses
            if p_lemma * p_hebrew == 0:
                continue
            pmi = math.log(p_joint / (p_lemma * p_hebrew))
            # Weighted PMI (Normalized by log-count to favor frequent pairs)
            score = pmi * math.log(1 + count)
            scored.append({
                'hebrew': hword,
                'count': count,
                'lemma_total': L_total,
                'hebrew_total': H_total,
                'pmi': round(pmi, 3),
                'score': round(score, 3),
            })
        scored.sort(key=lambda x: -x['score'])
        alignments[lemma] = scored[:top_k]
    return alignments


def main():
    print('Loading SBLGNT...')
    sblgnt = load_sblgnt()
    print(f'  {len(sblgnt)} word tokens')

    print('Grouping by verse...')
    greek_verses = group_sblgnt_by_verse(sblgnt)
    print(f'  {len(greek_verses)} Greek verses')

    print('Loading Delitzsch...')
    delitzsch_verses = load_delitzsch()
    print(f'  {len(delitzsch_verses)} Hebrew verses')

    print('Building co-occurrence...')
    counts, lemma_vc, heb_vc, total = build_cooccurrence(greek_verses, delitzsch_verses)

    print('Scoring alignments...')
    alignments = score_alignments(counts, lemma_vc, heb_vc, total)
    print(f'  {len(alignments)} Greek lemmas with candidate Hebrew retroversions')

    out = WORK / 'alignment_raw.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(alignments, f, ensure_ascii=False, indent=2)
    size_mb = out.stat().st_size / 1024 / 1024
    print(f'\nWrote {out} ({size_mb:.1f} MB)')

    # Sanity check: look at key lemmas
    print('\n--- Sanity check: top retroversions for key Greek lemmas ---')
    key_lemmas = ['Ἰησοῦς', 'Χριστός', 'κύριος', 'θεός', 'λόγος', 'φῶς', 'ζωή',
                  'ἀγάπη', 'πνεῦμα', 'βασιλεύς', 'ἁμαρτία', 'σταυρός', 'Πέτρος']
    for lemma in key_lemmas:
        if lemma in alignments:
            candidates = alignments[lemma]
            top3 = candidates[:3]
            print(f"\n  {lemma:15} ({lemma_vc[lemma]:>4} verses)")
            for c in top3:
                heb = c['hebrew']
                print(f"    → {heb:15} count={c['count']:>4} pmi={c['pmi']:>6.2f} score={c['score']:>6.2f}")
        else:
            print(f"\n  {lemma:15} NOT FOUND")


if __name__ == '__main__':
    main()
