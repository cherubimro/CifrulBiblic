#!/usr/bin/env python3
"""
Atbash-pair scan, zero-residue case.

Two variants:

(A) MULTISET-IDENTITY: pairs (A, B) where the contribution multisets are
    identical → residue = 0. This means every letter of A has a partner in
    B with the same contribution class (η↔σ, ι↔π, ε↔υ, etc.), but letters
    may be rearranged.

(B) LITERAL ATBASH: pairs where Atbash(A) = B letter-by-letter (same order,
    each position substituted with its Atbash mirror). This is the classical
    sense of the cipher (Jer 25:26 ששך = בבל).

Variant (B) is strictly stronger than (A) and rarer.
"""
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

sys.path.insert(0, '/home/bu/Documents/Biblia')
from biblegematria.biblegematria import load_sblgnt, isopsephy

WORK = Path('/home/bu/Documents/Biblia/retroversion_work')

GREEK_ALPHABET = 'αβγδεζηθικλμνξοπρστυφχψω'
ATBASH = {GREEK_ALPHABET[i]: GREEK_ALPHABET[23 - i] for i in range(24)}
ATBASH['ς'] = ATBASH['σ']

EDITORIAL_RE = re.compile(r'[⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸓⸔⸕⸖⸗]')

STOPWORD_LEMMAS = {
    'ὁ', 'ἡ', 'τό', 'αὐτός', 'ἐγώ', 'σύ', 'ἡμεῖς', 'ὑμεῖς', 'οὗτος', 'ἐκεῖνος',
    'ὅς', 'ὅστις', 'ὅδε', 'τις', 'τίς', 'ἄλλος', 'ἕτερος', 'ἑαυτοῦ',
    'καί', 'δέ', 'γάρ', 'οὖν', 'τε', 'ἀλλά', 'ἤ', 'μέν', 'μή',
    'οὐ', 'οὐχί', 'εἰ', 'ἐάν', 'ὅτι', 'ἵνα', 'ὡς', 'ὥστε', 'ὅταν',
    'ὅπως', 'ἄν', 'ἄρα', 'γε', 'ναί', 'οὐδέ', 'μηδέ', 'οὔτε', 'μήτε',
    'καθώς', 'πρίν', 'πλήν', 'πῶς', 'ποῦ', 'πότε', 'ὅπου', 'οὕτως',
    'ἐν', 'εἰς', 'ἐκ', 'ἐπί', 'πρός', 'ἀπό', 'διά', 'περί', 'ὑπό',
    'κατά', 'μετά', 'παρά', 'ὑπέρ', 'πρό', 'σύν',
    'εἰμί', 'γίνομαι', 'ἔχω', 'λέγω', 'ποιέω', 'δίδωμι', 'ὁράω',
    'ἔρχομαι', 'οἶδα', 'θέλω', 'δύναμαι',
    'πᾶς', 'πολύς', 'εἷς', 'μέγας', 'ἰδού', 'ἀμήν',
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
    return Counter(letter_contribution(c) for c in w if letter_contribution(c) > 0)


def atbash_transform(word):
    """Return the literal Atbash transform of a word (strip accents first)."""
    w = strip_accents(word)
    out = []
    for ch in w:
        if ch in ATBASH:
            out.append(ATBASH[ch])
        else:
            return None  # word contains non-Greek; skip
    return ''.join(out)


def main():
    sblgnt = load_sblgnt()

    # Collect unique forms (stripped for canonical representation)
    forms = {}  # stripped_form -> {original, lemma, count, first_ref, multiset, length}
    for w in sblgnt:
        orig = clean_greek(w['word'])
        if not orig:
            continue
        stripped = strip_accents(orig)
        if not stripped:
            continue
        if stripped not in forms:
            mset = contribution_multiset(orig)
            forms[stripped] = {
                'original': orig,
                'lemma': clean_greek(w['lemma']),
                'count': 0,
                'first_ref': f"{w['book']} {w['chapter']}:{w['verse']}",
                'iso': isopsephy(orig),
                'multiset': mset,
                'length': sum(mset.values()),
            }
        forms[stripped]['count'] += 1

    # Filter out stopword lemmas
    def is_stopword_stripped(stripped):
        return forms[stripped]['lemma'] in STOPWORD_LEMMAS

    content_forms = {k: v for k, v in forms.items() if not is_stopword_stripped(k)}
    print(f'Total unique NT forms (accents stripped): {len(forms)}', file=sys.stderr)
    print(f'Content forms (stopword-free): {len(content_forms)}', file=sys.stderr)

    # ====================================================================
    # VARIANT (B) LITERAL ATBASH: Atbash(A) = B letter-by-letter
    # ====================================================================
    print('\n=== VARIANT (B): LITERAL ATBASH — Atbash(A) == B ===', file=sys.stderr)
    literal_pairs = []
    for stripped, info in content_forms.items():
        at = atbash_transform(info['original'])
        if at is None:
            continue
        if at == stripped:
            # Self-atbash (palindrome-like under Atbash)
            literal_pairs.append(('SELF', stripped, stripped, info['count'], info['count']))
            continue
        if at in content_forms:
            # Pair found: A's Atbash = B, and B is also an NT content word
            other = content_forms[at]
            # Avoid reporting (A,B) and (B,A) twice
            if stripped < at:
                literal_pairs.append(('PAIR', stripped, at, info['count'], other['count']))

    # Also check if A's Atbash is a stopword form (weaker hit)
    print(f'\nLiteral-Atbash pairs found: {len(literal_pairs)}')
    for kind, A, B, ca, cb in literal_pairs:
        lemA = forms[A]['lemma'] if A in forms else '?'
        lemB = forms[B]['lemma'] if B in forms else '?'
        origA = forms[A]['original'] if A in forms else A
        origB = forms[B]['original'] if B in forms else B
        isoA = forms[A]['iso'] if A in forms else 0
        isoB = forms[B]['iso'] if B in forms else 0
        refA = forms[A]['first_ref'] if A in forms else ''
        refB = forms[B]['first_ref'] if B in forms else ''
        print(f'  [{kind}] {origA:18}×{ca:<3} (iso {isoA}, {refA}) ↔ '
              f'{origB:18}×{cb:<3} (iso {isoB}, {refB})')

    # Also: include hits where ONE side is stopword but the other is content
    print('\n--- Content form whose Atbash is a (non-content) NT form ---')
    weak_literal = []
    for stripped, info in content_forms.items():
        at = atbash_transform(info['original'])
        if at is None or at == stripped:
            continue
        if at in forms and at not in content_forms:
            # Content form A's atbash hits a stopword form B
            weak_literal.append((stripped, at, info['count'], forms[at]['count']))
    for A, B, ca, cb in weak_literal[:30]:
        origA = forms[A]['original']
        origB = forms[B]['original']
        lemB = forms[B]['lemma']
        print(f'  {origA:16}×{ca:<3} → Atbash = {origB:16}×{cb:<3} (stopword lemma {lemB})')

    # ====================================================================
    # VARIANT (A) MULTISET IDENTITY: same contribution multiset, rearranged
    # ====================================================================
    print('\n=== VARIANT (A): MULTISET IDENTITY — residue = 0 ===', file=sys.stderr)

    # Bucket forms by frozen multiset
    by_multi = defaultdict(list)
    for stripped, info in content_forms.items():
        key = tuple(sorted(info['multiset'].items()))
        by_multi[key].append(stripped)

    multiset_pairs = []
    for key, group in by_multi.items():
        if len(group) < 2:
            continue
        # All pairs in group have same multiset → residue 0
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                A, B = group[i], group[j]
                if forms[A]['lemma'] == forms[B]['lemma']:
                    continue
                multiset_pairs.append((A, B))

    print(f'\nMultiset-identity pairs (residue=0, distinct lemmas): {len(multiset_pairs)}')
    # Rank by combined freq
    def key(p):
        A, B = p
        return -(forms[A]['count'] + forms[B]['count'])
    multiset_pairs.sort(key=key)

    print('\nTop 50 by combined NT frequency:')
    for A, B in multiset_pairs[:50]:
        infoA = forms[A]
        infoB = forms[B]
        asum = sum(k*v for k, v in infoA['multiset'].items())
        print(f'  asum={asum:5}  {infoA["original"]:18}×{infoA["count"]:<4} '
              f'({infoA["lemma"]:12}) ↔ '
              f'{infoB["original"]:18}×{infoB["count"]:<4} '
              f'({infoB["lemma"]:12})')

    # Write xlsx
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Multiset-identity pairs'
    ws.append(['A', 'A lemma', 'A ×', 'A iso', 'A ref',
               'B', 'B lemma', 'B ×', 'B iso', 'B ref',
               'Atbash sum', 'Length'])
    for A, B in multiset_pairs:
        infoA, infoB = forms[A], forms[B]
        asum = sum(k*v for k, v in infoA['multiset'].items())
        ws.append([infoA['original'], infoA['lemma'], infoA['count'],
                   infoA['iso'], infoA['first_ref'],
                   infoB['original'], infoB['lemma'], infoB['count'],
                   infoB['iso'], infoB['first_ref'],
                   asum, infoA['length']])
    ws.freeze_panes = 'A2'
    wb.save(WORK / 'atbash_zero_residue.xlsx')
    print(f'\nWrote atbash_zero_residue.xlsx')


if __name__ == '__main__':
    main()
