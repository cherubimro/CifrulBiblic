#!/usr/bin/env python3
"""
Build the complete retroversion dictionary.

For each Greek lemma in lexicon_ro.json (5461 authoritative lemmas):
- Enumerate all Greek forms from SBLGNT with per-form isopsephy
- Attach top-ranked Hebrew retroversions from alignment_raw.json
- Strip prefixes to identify canonical Hebrew stems
- Lookup stem in OSHB strongs_he.json for validation and Strong's ID
- Compute gematria for each form (full and stem)

Output: retroversion.json — the complete dictionary for NT scan.
"""
import json
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path

sys.path.insert(0, '/home/bu/Documents/Biblia')
from biblegematria.biblegematria import load_sblgnt, isopsephy, hebrew_gematria

WORK = Path('/home/bu/Documents/Biblia/retroversion_work')

# Load manual overrides (edge cases where alignment ties or misfires)
OVERRIDES_PATH = WORK / 'retroversion_overrides.json'
if OVERRIDES_PATH.exists():
    with open(OVERRIDES_PATH, encoding='utf-8') as f:
        _OVERRIDES = json.load(f)
    _OVERRIDES = {k: v for k, v in _OVERRIDES.items() if not k.startswith('_')}
else:
    _OVERRIDES = {}

# Match scan.py's _clean_greek: strip SBLGNT editorial marks + trailing punct/parens.
# Used so our lookups match what scan.py sees.
_EDITORIAL_RE = re.compile(r'[⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸓⸔⸕⸖⸗]')


def clean_greek(word):
    """Same as biblegematria.scan._clean_greek — produces the canonical form
    used for lexicon lookup. Applied to SBLGNT words AND lemmas."""
    w = _EDITORIAL_RE.sub('', word)
    w = w.strip('.,;·:()[]·\u0387')
    return w

# Hebrew prefix letters that commonly attach to nouns/verbs
HEBREW_PREFIXES = set('והבלמכש')  # wa/ha/be/le/mi/ke/she


def strip_hebrew_prefix(word, stem_to_strongs=None):
    """
    Lazy prefix stripping: try candidate stems from longest to shortest.
    For each candidate, check if it's in the OSHB stem lookup. Return the
    first (longest) match. If no match, return word as-is (no stripping).

    This fixes issues like המשיח → יח (wrongly stripping 'ה' then 'מ' then 'ש').
    Instead: check המשיח itself, then משיח (match! H4899 = Messiah), stop.

    If no OSHB lookup provided, fall back to 'strip at most 2 prefix letters
    only if they are in HEBREW_PREFIXES and stem remains ≥3 chars'.
    """
    if stem_to_strongs is None:
        # Fallback: conservative stripping, max 2 prefix letters
        stem = word
        prefix = ''
        for _ in range(2):
            if len(stem) > 3 and stem[0] in HEBREW_PREFIXES:
                prefix += stem[0]
                stem = stem[1:]
            else:
                break
        return stem, prefix

    # Lazy: try from full word to progressively stripped, stop at first OSHB match
    # Max 3 prefix letters (e.g., ושב, מהב, etc. -- but unusual)
    for strip_count in range(0, min(4, len(word) - 2)):
        candidate_prefix = word[:strip_count]
        candidate_stem = word[strip_count:]
        # Validate: all characters of the proposed prefix must be in HEBREW_PREFIXES
        if strip_count > 0 and not all(c in HEBREW_PREFIXES for c in candidate_prefix):
            continue
        if candidate_stem in stem_to_strongs:
            return candidate_stem, candidate_prefix
    # No match found: return word as-is (probably a proper name or non-biblical)
    return word, ''


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def build_greek_forms_index(sblgnt_words):
    """Build {lemma: Counter(form → count)} with scan.py-compatible cleaning."""
    forms_index = defaultdict(Counter)
    for w in sblgnt_words:
        lemma = clean_greek(w['lemma'])
        form = clean_greek(w['word'])
        forms_index[lemma][form] += 1
    return forms_index


def build_retroversion():
    print('Loading inputs...')
    lexicon_ro = load_json('/home/bu/Documents/Biblia/biblegematria/biblegematria/lexicon_ro.json')
    strongs_ro = load_json('/home/bu/Documents/Biblia/biblegematria/biblegematria/strongs_ro.json')
    alignment = load_json(WORK / 'alignment_raw.json')
    strongs_he = load_json(WORK / 'strongs_he.json')
    print(f'  lexicon_ro: {len(lexicon_ro)} Greek lemmas')
    print(f'  alignment: {len(alignment)} lemmas with Hebrew candidates')
    print(f'  strongs_he: {len(strongs_he)} Hebrew Strong\'s IDs')

    print('Loading SBLGNT for Greek forms...')
    sblgnt = load_sblgnt()
    forms_index = build_greek_forms_index(sblgnt)
    print(f'  {len(forms_index)} lemmas with form data')

    # Build consonantal-stem → Strong's HE lookup
    stem_to_strongs = {}
    for sid, info in strongs_he.items():
        stem = info['canonical_stem']
        if stem not in stem_to_strongs:
            stem_to_strongs[stem] = {
                'strongs_id': sid,
                'gematria': info['canonical_gematria'],
                'occurrences_ot': info['occurrences'],
            }

    print('Building retroversion entries...')
    retroversion = {}
    no_alignment = 0
    no_match_oshb = 0
    for greek_lemma in lexicon_ro:
        entry = {
            'ro': lexicon_ro.get(greek_lemma, ''),
            'en': strongs_ro.get(greek_lemma, ''),  # actually also Romanian; will fix
        }

        # Greek forms + isopsephy per form
        greek_forms_counter = forms_index.get(greek_lemma, Counter())
        entry['isopsephy_lemma'] = isopsephy(greek_lemma)
        entry['greek_forms'] = [
            {
                'form': form,
                'iso': isopsephy(form),
                'count': count,
            }
            for form, count in greek_forms_counter.most_common()
        ]

        # Hebrew candidates from alignment
        candidates = alignment.get(greek_lemma, [])
        if not candidates:
            no_alignment += 1
            retroversion[greek_lemma] = entry
            continue

        # Process top candidates: strip prefix (lazy, OSHB-validated), identify stem
        hebrew_entries = []
        for cand in candidates[:10]:
            heb_full = cand['hebrew']
            stem, prefix = strip_hebrew_prefix(heb_full, stem_to_strongs=stem_to_strongs)
            gem_full = hebrew_gematria(heb_full) if heb_full else 0
            gem_stem = hebrew_gematria(stem) if stem else 0
            oshb_lookup = stem_to_strongs.get(stem)
            hebrew_entries.append({
                'form': heb_full,
                'stem': stem,
                'prefix': prefix,
                'gematria_full': gem_full,
                'gematria_stem': gem_stem,
                'delitzsch_count': cand['count'],
                'pmi': cand['pmi'],
                'score': cand['score'],
                'oshb_strongs': oshb_lookup['strongs_id'] if oshb_lookup else None,
                'oshb_ot_occurrences': oshb_lookup['occurrences_ot'] if oshb_lookup else 0,
                'biblical_hebrew': oshb_lookup is not None,
            })
            if oshb_lookup is None:
                no_match_oshb += 1

        entry['hebrew_candidates'] = hebrew_entries

        # Identify primary canonical Hebrew stem.
        # Strategy:
        #   1. For PROPER NAMES (Greek lemma starts with uppercase): prefer the
        #      highest-scored candidate even without OSHB match. Delitzsch
        #      transliterates proper names, and compound names like Barabbas
        #      retrovert to compounds (bar-abba = 206). The fallback to a short
        #      biblical stem (bar = grain) is misleading.
        #   2. For COMMON WORDS: prefer the highest-scored biblical match
        #      (so logos -> davar H1697 = word, not some random stem).
        canonical = None
        is_proper_name = bool(greek_lemma) and greek_lemma[0].isupper()
        oshb_matches = [h for h in hebrew_entries if h['biblical_hebrew']]

        if is_proper_name and hebrew_entries:
            # For proper names: prefer highest score, tiebreak by stem length
            # (compound names like עמנואל > עלמה when tied)
            top_score = hebrew_entries[0]['score']
            near_top = [h for h in hebrew_entries if h['score'] >= 0.95 * top_score]
            near_top.sort(key=lambda h: (-len(h['stem']), -h['score']))
            canonical = near_top[0]
        elif oshb_matches:
            canonical = oshb_matches[0]
        elif hebrew_entries:
            canonical = hebrew_entries[0]

        # Apply manual override if one exists for this lemma
        if greek_lemma in _OVERRIDES:
            ov = _OVERRIDES[greek_lemma]
            override_stem = ov['stem']
            override_gem = ov.get('gematria', hebrew_gematria(override_stem))
            # Find matching entry in hebrew_entries or construct one
            matched = None
            for h in hebrew_entries:
                if h['stem'] == override_stem:
                    matched = h
                    break
            if matched is None:
                matched = {
                    'form': override_stem,
                    'stem': override_stem,
                    'prefix': '',
                    'gematria_full': override_gem,
                    'gematria_stem': override_gem,
                    'delitzsch_count': 0,
                    'pmi': 0,
                    'score': 0,
                    'oshb_strongs': None,
                    'oshb_ot_occurrences': 0,
                    'biblical_hebrew': False,
                    'source': 'manual_override',
                }
                hebrew_entries.insert(0, matched)
                entry['hebrew_candidates'] = hebrew_entries
            canonical = matched
        if canonical:
            entry['hebrew_canonical'] = {
                'stem': canonical['stem'],
                'gematria': canonical['gematria_stem'],
                'form_most_common': canonical['form'],
                'form_gematria': canonical['gematria_full'],
                'strongs_he': canonical['oshb_strongs'],
                'confidence': 'high' if canonical['biblical_hebrew'] else 'medium',
            }

        retroversion[greek_lemma] = entry

    print(f'  Total entries: {len(retroversion)}')
    print(f'  Without alignment (particles/rare): {no_alignment}')
    print(f'  With Delitzsch forms not in biblical OSHB (non-biblical Hebrew): {no_match_oshb}')

    out = WORK / 'retroversion.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(retroversion, f, ensure_ascii=False, indent=2)
    size_mb = out.stat().st_size / 1024 / 1024
    print(f'\nWrote {out} ({size_mb:.1f} MB)')

    return retroversion


def sanity_check(retroversion):
    """Show key lemmas in the final output format."""
    print('\n--- Sanity check: final output format ---')
    keys = ['Ἰησοῦς', 'Χριστός', 'λόγος', 'σταυρός', 'ἀγάπη', 'Πέτρος', 'Βαραββᾶς']
    for k in keys:
        entry = retroversion.get(k)
        if not entry:
            print(f"\n{k}: NOT FOUND")
            continue
        print(f"\n{k}  ({entry.get('ro', '')})")
        print(f"  iso(lemma)={entry.get('isopsephy_lemma')}")
        gf = entry.get('greek_forms', [])[:3]
        for f in gf:
            print(f"  Greek form: {f['form']:12} iso={f['iso']:>5} ×{f['count']}")
        can = entry.get('hebrew_canonical')
        if can:
            print(f"  Hebrew canonical: stem={can['stem']:12} gem={can['gematria']:>5} "
                  f"form={can['form_most_common']:12} gem={can['form_gematria']:>5} "
                  f"strongs=H{can['strongs_he']}")
        hc = entry.get('hebrew_candidates', [])[:3]
        for h in hc:
            bib = '📖' if h['biblical_hebrew'] else '❓'
            print(f"    {bib} {h['form']:12} → stem={h['stem']:8} "
                  f"gem={h['gematria_full']:>5}/{h['gematria_stem']:>5} "
                  f"×{h['delitzsch_count']:>3} pmi={h['pmi']:>5.2f}")


if __name__ == '__main__':
    retroversion = build_retroversion()
    sanity_check(retroversion)
