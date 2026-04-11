#!/usr/bin/env python3
"""
Cross-language cipher scan: NT Greek form isopsephy → OT Hebrew word gematria,
filtered to ONLY semantically divergent matches.

For each NT Greek form F:
  V = isopsephy(F)
  R = retroversion stem (Delitzsch's Hebrew for F's lemma)
  Candidates = {OT Hebrew words W : gematria_stem(W) == V}
  Divergent = Candidates - {R and its Strong's variants}

The "divergent" matches are the cipher: same number, different meaning,
attested independently in OT.

Output: nt_ot_cipher.xlsx with columns:
  Greek form | Iso | Greek lemma | RO meaning | Retroversion (R) | R gematria
  | OT Hebrew word (W) | W Strong's | W gloss | W OT occurrences
  | Semantic divergence flag | Score
"""
import json
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path

sys.path.insert(0, '/home/bu/Documents/Biblia')
from biblegematria.biblegematria import load_sblgnt, isopsephy, hebrew_gematria

try:
    import openpyxl
    HAS_XLSX = True
except ImportError:
    HAS_XLSX = False

WORK = Path('/home/bu/Documents/Biblia/retroversion_work')

_EDITORIAL_RE = re.compile(r'[⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸓⸔⸕⸖⸗]')


def clean_greek(word):
    w = _EDITORIAL_RE.sub('', word)
    w = w.strip('.,;·:()[]·\u0387')
    return w


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def build_ot_gematria_index():
    """
    Returns: {gematria_value: {stem: {'strongs': sid, 'glosses': set(), 'occurrences': count}}}
    Uses morph_index.json (OT words per verse) and strongs_he.json (lemma info).
    """
    print('Loading OT morph index...', file=sys.stderr)
    morph_index = load_json(WORK / 'morph_index.json')
    strongs_he = load_json(WORK / 'strongs_he.json')

    print('Building OT gematria index...', file=sys.stderr)
    # {gem: {stem: {"strongs": sid, "count": n}}}
    ot_index = defaultdict(dict)
    for vid, words in morph_index.items():
        for w in words:
            gem = w['gematria_stem']
            stem = w['consonantal_stem']
            sid = w['stem_strongs']
            if gem <= 0 or not stem:
                continue
            if stem not in ot_index[gem]:
                ot_index[gem][stem] = {
                    'strongs': sid,
                    'count': 0,
                    'first_verse': vid,
                }
            ot_index[gem][stem]['count'] += 1

    # Add Strong's info (canonical form, gematria check)
    for gem, stems in ot_index.items():
        for stem, info in stems.items():
            sid = info['strongs']
            if sid in strongs_he:
                s = strongs_he[sid]
                info['ot_occurrences'] = s['occurrences']
                info['canonical_form'] = s['canonical_stem']

    total_gematria = sum(sum(s['count'] for s in stems.values()) for stems in ot_index.values())
    unique_stems = sum(len(stems) for stems in ot_index.values())
    print(f'  {len(ot_index)} unique gematria values', file=sys.stderr)
    print(f'  {unique_stems} unique stem-gematria pairs', file=sys.stderr)
    print(f'  {total_gematria} total OT word occurrences indexed', file=sys.stderr)
    return ot_index


def get_retroversion_set(entry):
    """Return set of Hebrew stems that Delitzsch uses for this Greek lemma
    (canonical + top candidates), to EXCLUDE from divergent matches."""
    excluded = set()
    can = entry.get('hebrew_canonical', {})
    if can.get('stem'):
        excluded.add(can['stem'])
    for c in entry.get('hebrew_candidates', [])[:5]:  # top 5
        if c.get('stem'):
            excluded.add(c['stem'])
    return excluded


def scan_cipher(retroversion, ot_index, sblgnt_words,
                min_ot_occurrences=3,
                max_per_form=5):
    """
    For each unique Greek form in NT:
      - Compute isopsephy
      - Find OT Hebrew words with matching gematria
      - Exclude retroversion words (not divergent)
      - Report remainders as cipher matches
    """
    # Build: {greek_form: {'lemma': str, 'iso': int, 'count': int}}
    print('Aggregating NT forms...', file=sys.stderr)
    nt_forms = {}
    for w in sblgnt_words:
        form = clean_greek(w['word'])
        lemma = clean_greek(w['lemma'])
        if not form:
            continue
        iso = isopsephy(form)
        if iso <= 0:
            continue
        key = form
        if key not in nt_forms:
            nt_forms[key] = {'lemma': lemma, 'iso': iso, 'count': 0, 'first_ref': f"{w['book']} {w['chapter']}:{w['verse']}"}
        nt_forms[key]['count'] += 1
    print(f'  {len(nt_forms)} unique NT forms', file=sys.stderr)

    # Scan each form
    matches = []
    skipped_no_ot = 0
    skipped_only_retroversion = 0
    for form, info in nt_forms.items():
        iso = info['iso']
        lemma = info['lemma']
        ret_entry = retroversion.get(lemma, {})
        excluded = get_retroversion_set(ret_entry)

        # Get OT candidates at this value
        ot_candidates = ot_index.get(iso, {})
        if not ot_candidates:
            skipped_no_ot += 1
            continue

        # Filter: divergent = candidates NOT in excluded (retroversion) set
        divergent = [
            (stem, d) for stem, d in ot_candidates.items()
            if stem not in excluded and d.get('ot_occurrences', 0) >= min_ot_occurrences
        ]
        if not divergent:
            skipped_only_retroversion += 1
            continue

        # Sort by OT frequency desc, keep top N
        divergent.sort(key=lambda x: -x[1].get('ot_occurrences', 0))
        divergent = divergent[:max_per_form]

        for stem, d in divergent:
            matches.append({
                'greek_form': form,
                'iso': iso,
                'greek_lemma': lemma,
                'ro': ret_entry.get('ro', ''),
                'nt_count': info['count'],
                'first_ref': info['first_ref'],
                'retroversion_stem': next(iter(excluded)) if excluded else '',
                'ot_hebrew_stem': stem,
                'ot_hebrew_strongs': d.get('strongs', ''),
                'ot_occurrences': d.get('ot_occurrences', 0),
                'ot_first_verse': d.get('first_verse', ''),
            })

    print(f'  Raw matches (divergent): {len(matches)}', file=sys.stderr)
    print(f'  Skipped (no OT word at this value): {skipped_no_ot}', file=sys.stderr)
    print(f'  Skipped (OT only contains retroversion word): {skipped_only_retroversion}', file=sys.stderr)
    return matches


def score_and_rank(matches):
    for m in matches:
        # Higher NT frequency × OT frequency = stronger
        s = 0
        s += min(m['nt_count'], 100) // 5
        s += min(m['ot_occurrences'], 1000) // 20
        # Bonus for matching known theological values
        if m['iso'] in (148, 153, 276, 385, 613, 666, 888, 103, 206, 911, 1209):
            s += 20
        # Bonus for factor 37
        if m['iso'] % 37 == 0 and m['iso'] > 37:
            s += 5
        m['score'] = s
    matches.sort(key=lambda m: (-m['score'], -m['nt_count']))


def write_xlsx(matches, path):
    if not HAS_XLSX:
        return
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'NT↔OT Cipher'
    headers = [
        'Score', 'NT Form', 'Iso', 'Factor37', 'Greek Lemma', 'RO',
        'NT #', 'First NT ref',
        'Retroversion stem', 'OT Hebrew word', 'Strongs H', 'OT #', 'OT first verse',
    ]
    ws.append(headers)
    for m in matches:
        ws.append([
            m['score'],
            m['greek_form'],
            m['iso'],
            'Y' if m['iso'] % 37 == 0 and m['iso'] > 37 else '',
            m['greek_lemma'],
            m['ro'],
            m['nt_count'],
            m['first_ref'],
            m['retroversion_stem'],
            m['ot_hebrew_stem'],
            m['ot_hebrew_strongs'],
            m['ot_occurrences'],
            m['ot_first_verse'],
        ])
    ws.freeze_panes = 'A2'
    for col in ws.columns:
        try:
            max_len = max(len(str(c.value or '')) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)
        except (ValueError, AttributeError):
            pass
    wb.save(path)


def main():
    print('Loading retroversion.json...', file=sys.stderr)
    retroversion = load_json(WORK / 'retroversion.json')

    ot_index = build_ot_gematria_index()

    print('Loading SBLGNT...', file=sys.stderr)
    sblgnt = load_sblgnt()
    print(f'  {len(sblgnt)} NT word tokens', file=sys.stderr)

    matches = scan_cipher(retroversion, ot_index, sblgnt)

    score_and_rank(matches)

    out_xlsx = WORK / 'nt_ot_cipher.xlsx'
    write_xlsx(matches, out_xlsx)
    print(f'\nWrote {out_xlsx}', file=sys.stderr)
    print(f'Total cipher matches: {len(matches)}', file=sys.stderr)

    # Show top 30
    print('\n=== Top 30 cipher matches ===')
    for m in matches[:30]:
        f37 = '★37' if m['iso'] % 37 == 0 and m['iso'] > 37 else '   '
        print(f"  [{m['score']:>3}] {f37} {m['iso']:>5} | "
              f"{m['greek_form']:15} ({m['greek_lemma']:12} = {m['ro'][:18]:18}) "
              f"↔ OT: {m['ot_hebrew_stem']:10} "
              f"(H{m['ot_hebrew_strongs']}, ×{m['ot_occurrences']}) "
              f"@ {m['ot_first_verse']}")


if __name__ == '__main__':
    main()
