#!/usr/bin/env python3
"""
Atbash-pair scan: scan the NT for pairs of Greek forms (A, B) such that
iso(A) + atbash_iso(A) == iso(B) + atbash_iso(B), AND some letters are
shared by contribution-value between the two words. The 'residue' (value
contributed by the unshared letters) is then checked against an index of
NT and Hebrew-retroversion values to find cases like Ἰησοῦς ↔ Πέτρος
where the residue 416 = λεπτά (widow's mites).

Rationale: the Jesus/Peter pattern (Matt 17:24-27) shows that when two
words have equal Atbash sum, the 'unpaired' letters on each side must
contribute the same amount (this is forced by the total equality). The
interesting question is whether that residue value has independent
theological meaning — which was the case for 416 (= λεπτά, μαθητήν,
'disciple loved').
"""
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

sys.path.insert(0, '/home/bu/Documents/Biblia')
from biblegematria.biblegematria import load_sblgnt, isopsephy, hebrew_gematria

WORK = Path('/home/bu/Documents/Biblia/retroversion_work')

GREEK_ALPHABET = 'αβγδεζηθικλμνξοπρστυφχψω'
ATBASH = {GREEK_ALPHABET[i]: GREEK_ALPHABET[23 - i] for i in range(24)}
ATBASH['ς'] = ATBASH['σ']

EDITORIAL_RE = re.compile(r'[⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸓⸔⸕⸖⸗]')

# Function-word blacklist (accents stripped): articles, pronouns, particles,
# prepositions, conjunctions, copula, common negations. These dominate the
# bucket scan by frequency but are theologically meaningless as "name-like"
# pair components.
STOPWORD_LEMMAS = {
    # articles
    'ὁ', 'ἡ', 'τό',
    # personal/demonstrative pronouns
    'αὐτός', 'ἐγώ', 'σύ', 'ἡμεῖς', 'ὑμεῖς', 'οὗτος', 'ἐκεῖνος',
    'ὅς', 'ὅστις', 'ὅδε', 'τις', 'τίς', 'ἄλλος', 'ἕτερος', 'ἑαυτοῦ',
    # particles/conjunctions
    'καί', 'δέ', 'γάρ', 'οὖν', 'τε', 'ἀλλά', 'ἤ', 'μέν', 'μή',
    'οὐ', 'οὐχί', 'εἰ', 'ἐάν', 'ὅτι', 'ἵνα', 'ὡς', 'ὥστε', 'ὅταν',
    'ὅπως', 'ἄν', 'ἄρα', 'γε', 'ναί', 'οὐδέ', 'μηδέ', 'οὔτε', 'μήτε',
    'καθώς', 'πρίν', 'πλήν', 'πῶς', 'ποῦ', 'πότε', 'ὅπου', 'οὕτως',
    # prepositions
    'ἐν', 'εἰς', 'ἐκ', 'ἐπί', 'πρός', 'ἀπό', 'διά', 'περί', 'ὑπό',
    'κατά', 'μετά', 'παρά', 'ὑπέρ', 'πρό', 'σύν', 'ἄνευ', 'ἄχρι',
    'ἕως', 'ἔμπροσθεν', 'ὀπίσω', 'ἐνώπιον',
    # copulas / common verbs (extremely frequent, near-function)
    'εἰμί', 'γίνομαι', 'ἔχω', 'λέγω', 'ποιέω', 'δίδωμι', 'ὁράω',
    'ἔρχομαι', 'οἶδα', 'θέλω', 'δύναμαι',
    # common adjectives / numerals used as function
    'πᾶς', 'πολύς', 'εἷς', 'μέγας', 'ἅγιος',
    # address markers
    'ἰδού', 'ἀμήν',
}

# Theological constants with short glosses
THEOLOGICAL = {
    13: 'אחד/אהבה (ehad/ahava)',
    26: 'יהוה (YHWH)',
    37: 'Christ-factor (888/24)',
    74: 'וחס (spared)',
    86: 'אלהים (Elohim)',
    112: 'יהוה+אדני',
    148: 'פסח (Pesaḥ)',
    153: 'ΙΧΘΥΣ / בני האלהים',
    214: 'רוח (ruach)',
    276: 'רע/עור (Gen 6:5)',
    318: 'חנוך (Enoch 1 / Gen 14:14)',
    354: 'שנה (year)',
    416: 'λεπτά / μαθητήν (widow\'s mites)',
    430: 'שקל (shekel)',
    444: 'דמשק',
    479: 'ישראל (Israel)',
    611: 'תורה (Torah)',
    613: 'mitzvot',
    666: 'number of the beast',
    775: 'ירושלים',
    777: 'triple seven',
    888: 'Ἰησοῦς',
    911: 'ראשית (beginning)',
    1118: 'דברי ימים (chronicles)',
    1209: 'Ἰησοῦς + Πέτρος Atbash-sum / גבריאל',
    1260: 'Rev 12:6',
}


def clean_greek(word):
    w = EDITORIAL_RE.sub('', word)
    return w.strip('.,;·:()[]·\u0387')


def strip_accents(word):
    w = unicodedata.normalize('NFD', word.lower())
    return ''.join(c for c in w if unicodedata.category(c) != 'Mn')


def letter_contribution(ch):
    if ch not in ATBASH:
        return 0
    return isopsephy(ch) + isopsephy(ATBASH[ch])


def contribution_multiset(word):
    w = strip_accents(word)
    counter = Counter()
    for ch in w:
        c = letter_contribution(ch)
        if c > 0:
            counter[c] += 1
    return counter


def multiset_sum(m):
    return sum(k * v for k, v in m.items())


def common_multiset(m1, m2):
    keys = set(m1) & set(m2)
    return Counter({k: min(m1[k], m2[k]) for k in keys})


def residue_letters(word, common):
    """Return the list of letters in `word` not consumed by the common multiset."""
    w = strip_accents(word)
    remaining = Counter(common)
    residue = []
    for ch in w:
        c = letter_contribution(ch)
        if c <= 0:
            continue
        if remaining.get(c, 0) > 0:
            remaining[c] -= 1
        else:
            residue.append(ch)
    return residue


def main():
    print('Loading SBLGNT...', file=sys.stderr)
    sblgnt = load_sblgnt()

    # Collect unique forms
    forms = {}
    for w in sblgnt:
        form = clean_greek(w['word'])
        if not form:
            continue
        iso = isopsephy(form)
        if iso <= 0:
            continue
        if form not in forms:
            mset = contribution_multiset(form)
            forms[form] = {
                'lemma': clean_greek(w['lemma']),
                'count': 0,
                'first_ref': f"{w['book']} {w['chapter']}:{w['verse']}",
                'iso': iso,
                'atbash_sum': multiset_sum(mset),
                'multiset': mset,
            }
        forms[form]['count'] += 1

    print(f'  {len(forms)} unique forms', file=sys.stderr)

    # Index forms by isopsephy (to look up residue → word)
    iso_index = defaultdict(list)
    for f, info in forms.items():
        iso_index[info['iso']].append(f)

    # Load retroversion (Hebrew side) for optional residue match
    retro_by_gem = defaultdict(list)
    retro_path = WORK / 'retroversion.json'
    if retro_path.exists():
        with open(retro_path, encoding='utf-8') as fh:
            retro = json.load(fh)
        for lemma, entry in retro.items():
            can = entry.get('hebrew_canonical', {})
            g = can.get('gematria', 0)
            if g:
                retro_by_gem[g].append((lemma, can.get('stem', ''), entry.get('ro', '')))

    # Filter out function-word forms (via lemma blacklist)
    def is_stopword(form):
        return forms[form]['lemma'] in STOPWORD_LEMMAS

    # Count NT frequency per isopsephy value → rarity filter for residue
    iso_freq_total = defaultdict(int)
    for f, info in forms.items():
        iso_freq_total[info['iso']] += info['count']

    # Bucket forms by atbash_sum (content words only)
    buckets = defaultdict(list)
    for f, info in forms.items():
        if is_stopword(f):
            continue
        buckets[info['atbash_sum']].append(f)

    print(f'  {len(buckets)} atbash_sum buckets (content words only)', file=sys.stderr)
    multi = sum(1 for b in buckets.values() if len(b) >= 2)
    print(f'  {multi} buckets with >= 2 forms', file=sys.stderr)

    # Scan pairs
    results = []
    processed = 0
    for asum, bucket in buckets.items():
        if len(bucket) < 2:
            continue
        if asum < 500:
            continue  # skip very short / trivial buckets
        n = len(bucket)
        for i in range(n):
            A = bucket[i]
            mA = forms[A]['multiset']
            for j in range(i + 1, n):
                B = bucket[j]
                processed += 1
                mB = forms[B]['multiset']
                common = common_multiset(mA, mB)
                common_sum = multiset_sum(common)
                residue = asum - common_sum

                if residue == 0:
                    continue  # identical multisets (anagram-ish)
                if residue < 50:
                    continue
                if common_sum < asum * 0.4:
                    continue

                # Require at least 1 residue letter on each side (always true if residue > 0)
                resA = residue_letters(A, common)
                resB = residue_letters(B, common)
                if not resA or not resB:
                    continue

                # Check residue value matches (skip stopword iso-matches)
                iso_matches = [
                    f for f in iso_index.get(residue, [])
                    if f not in (A, B) and not is_stopword(f)
                ]
                heb_matches = retro_by_gem.get(residue, [])
                theo = THEOLOGICAL.get(residue, '')

                # SIGNIFICANCE FILTER:
                # (a) residue is a known theological constant, OR
                # (b) residue's NT iso-frequency is low (<= 20 occurrences total)
                #     AND matches a non-stopword NT form, OR
                # (c) residue matches a Hebrew retroversion entry (rare).
                residue_freq = iso_freq_total.get(residue, 0)
                significant = (
                    bool(theo)
                    or (residue_freq <= 20 and bool(iso_matches))
                    or bool(heb_matches)
                )
                if not significant:
                    continue

                # Rank: prefer pairs where A, B are distinct lemmas (not just form variants)
                if forms[A]['lemma'] == forms[B]['lemma']:
                    continue

                results.append({
                    'A': A,
                    'B': B,
                    'A_lemma': forms[A]['lemma'],
                    'B_lemma': forms[B]['lemma'],
                    'A_count': forms[A]['count'],
                    'B_count': forms[B]['count'],
                    'A_iso': forms[A]['iso'],
                    'B_iso': forms[B]['iso'],
                    'A_ref': forms[A]['first_ref'],
                    'B_ref': forms[B]['first_ref'],
                    'asum': asum,
                    'common_sum': common_sum,
                    'residue': residue,
                    'res_letters_A': ''.join(resA),
                    'res_letters_B': ''.join(resB),
                    'iso_matches': iso_matches[:5],
                    'heb_matches': heb_matches[:3],
                    'theological': theo,
                })

    print(f'  scanned {processed:,} pairs → {len(results):,} candidate hits', file=sys.stderr)

    # Rank: prefer theological residues first, then by combined frequency
    def rank_key(r):
        theo_weight = 0 if r['theological'] else 1
        return (theo_weight, -(r['A_count'] + r['B_count']), r['residue'])
    results.sort(key=rank_key)

    # Print top 40
    print('\n=== TOP 40 by theological-residue priority, then NT frequency ===\n')
    for r in results[:40]:
        iso_m = ','.join(r['iso_matches'][:3]) if r['iso_matches'] else '-'
        heb_m = ','.join(f"{h[0]}/{h[1]}" for h in r['heb_matches'][:2]) if r['heb_matches'] else '-'
        theo = f" [{r['theological']}]" if r['theological'] else ''
        print(f"  sum={r['asum']:5}  {r['A']:16}×{r['A_count']:<4} ↔ "
              f"{r['B']:16}×{r['B_count']:<4}  "
              f"residue={r['residue']:5} ({r['res_letters_A']}|{r['res_letters_B']}) "
              f"→ NT:{iso_m} | HEB:{heb_m}{theo}")

    # Write xlsx
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Atbash-pair residue'
    ws.append([
        'Form A', 'A lemma', 'A ×', 'A iso', 'A first ref',
        'Form B', 'B lemma', 'B ×', 'B iso', 'B first ref',
        'Atbash sum', 'Common sum', 'Residue',
        'Res letters A', 'Res letters B',
        'NT iso-matches', 'Hebrew retroversion', 'Theological',
    ])
    for r in results[:3000]:
        iso_m = ', '.join(r['iso_matches'][:5])
        heb_m = ', '.join(f"{h[0]}={h[1]} ({h[2]})" for h in r['heb_matches'][:3])
        ws.append([
            r['A'], r['A_lemma'], r['A_count'], r['A_iso'], r['A_ref'],
            r['B'], r['B_lemma'], r['B_count'], r['B_iso'], r['B_ref'],
            r['asum'], r['common_sum'], r['residue'],
            r['res_letters_A'], r['res_letters_B'],
            iso_m, heb_m, r['theological'],
        ])
    ws.freeze_panes = 'A2'
    for col in ws.columns:
        try:
            max_len = max(len(str(c.value or '')) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 45)
        except (ValueError, AttributeError):
            pass
    out = WORK / 'atbash_pair_scan.xlsx'
    wb.save(out)
    print(f'\nWrote {out} ({len(results)} pairs total; first 3000 written)')


if __name__ == '__main__':
    main()
