#!/usr/bin/env python3
"""
Notarikon scan: find hidden acronyms in the NT Greek text.

For each verse, extract consecutive word sequences (length 3-8) and
check if the first letters form:
  (a) a known NT Greek word (or lemma)
  (b) a theologically significant isopsephy value
  (c) a known acronym (ΙΧΘΥΣ, YHWH transliterations, etc.)

Also checks last letters of consecutive words.
"""
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, '/home/bu/Documents/Biblia')
from biblegematria.biblegematria import load_sblgnt, isopsephy

EDITORIAL_RE = re.compile(r'[⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸓⸔⸕⸖⸗]')

TARGETS = {
    13: 'אחד', 26: 'יהוה', 37: 'factor-37', 74: 'וחס',
    86: 'אלהים', 111: '3×37', 148: 'פסח', 153: 'ΙΧΘΥΣ',
    214: 'רוח', 276: 'עור', 318: 'חנוך', 385: 'שכינה',
    416: 'λεπτά', 444: 'מקדש', 611: 'תורה', 613: 'mitzvot',
    666: 'Beast', 777: 'triple-7', 888: 'Ἰησοῦς',
    911: 'ראשית', 1000: 'χίλιοι', 1118: 'Shema', 1209: 'Gabriel',
}

# Known acronyms to search for
KNOWN_ACRONYMS = {
    'ιχθυς': 'ΙΧΘΥΣ (Ἰησοῦς Χριστός Θεοῦ Υἱός Σωτήρ)',
    'ιχθυ': 'ΙΧΘΥ (first 4 of ΙΧΘΥΣ)',
    'αμην': 'ΑΜΗΝ (amen)',
    'θεος': 'ΘΕΟΣ (God)',
    'ιησ': 'ΙΗΣ (Iesous nomen sacrum)',
    'χρσ': 'ΧΡΣ (Christos nomen sacrum)',
    'κυρ': 'ΚΥΡ (Kyrios nomen sacrum)',
}


def clean(word):
    w = EDITORIAL_RE.sub('', word)
    return w.strip('.,;·:()[]·\u0387').replace('(', '').replace(')', '')


def strip_accents(word):
    w = unicodedata.normalize('NFD', word.lower())
    return ''.join(c for c in w if unicodedata.category(c) != 'Mn')


def first_letter(word):
    """Get the first Greek letter (accent-stripped) of a word."""
    s = strip_accents(clean(word))
    for ch in s:
        if ch.isalpha():
            return ch
    return ''


def last_letter(word):
    """Get the last Greek letter (accent-stripped) of a word."""
    s = strip_accents(clean(word))
    for ch in reversed(s):
        if ch.isalpha():
            return ch
    return ''


def main():
    print('Loading SBLGNT...', file=sys.stderr)
    sblgnt = load_sblgnt()

    # Build known words set (for checking if acronym = real word)
    known_words = set()
    known_lemmas = set()
    for w in sblgnt:
        c = strip_accents(clean(w['word']))
        if c:
            known_words.add(c)
        l = strip_accents(clean(w['lemma']))
        if l:
            known_lemmas.add(l)

    print(f'  {len(known_words)} unique word forms, {len(known_lemmas)} lemmas',
          file=sys.stderr)

    # Group tokens by verse
    verses = defaultdict(list)
    for w in sblgnt:
        ref = f"{w['book']} {w['chapter']}:{w['verse']}"
        word = clean(w['word'])
        if word:
            verses[ref].append(word)

    print(f'  {len(verses)} verses', file=sys.stderr)

    # Scan for acronyms
    findings_first = []  # first-letter acronyms
    findings_last = []   # last-letter acronyms

    for ref, words in verses.items():
        n = len(words)
        for start in range(n):
            for length in range(3, min(9, n - start + 1)):
                seq = words[start:start + length]

                # First letters
                fl = ''.join(first_letter(w) for w in seq)
                if len(fl) == length:
                    iso_fl = isopsephy(''.join(fl))  # rough iso from letter string

                    # Check known acronyms
                    if fl in KNOWN_ACRONYMS:
                        findings_first.append({
                            'ref': ref, 'type': 'KNOWN',
                            'acronym': fl, 'iso': iso_fl,
                            'name': KNOWN_ACRONYMS[fl],
                            'words': seq, 'length': length,
                        })

                    # Check if = real NT word
                    if fl in known_words and len(fl) >= 4:
                        findings_first.append({
                            'ref': ref, 'type': 'WORD',
                            'acronym': fl, 'iso': iso_fl,
                            'name': f'NT word: {fl}',
                            'words': seq, 'length': length,
                        })

                    # Check theological target
                    if iso_fl in TARGETS and len(fl) >= 4:
                        findings_first.append({
                            'ref': ref, 'type': 'TARGET',
                            'acronym': fl, 'iso': iso_fl,
                            'name': TARGETS[iso_fl],
                            'words': seq, 'length': length,
                        })

                # Last letters
                ll = ''.join(last_letter(w) for w in seq)
                if len(ll) == length:
                    iso_ll = isopsephy(''.join(ll))

                    if ll in KNOWN_ACRONYMS:
                        findings_last.append({
                            'ref': ref, 'type': 'KNOWN',
                            'acronym': ll, 'iso': iso_ll,
                            'name': KNOWN_ACRONYMS[ll],
                            'words': seq, 'length': length,
                        })

                    if ll in known_words and len(ll) >= 4:
                        findings_last.append({
                            'ref': ref, 'type': 'WORD',
                            'acronym': ll, 'iso': iso_ll,
                            'name': f'NT word: {ll}',
                            'words': seq, 'length': length,
                        })

                    if iso_ll in TARGETS and len(ll) >= 4:
                        findings_last.append({
                            'ref': ref, 'type': 'TARGET',
                            'acronym': ll, 'iso': iso_ll,
                            'name': TARGETS[iso_ll],
                            'words': seq, 'length': length,
                        })

    print(f'\nFirst-letter findings: {len(findings_first)}', file=sys.stderr)
    print(f'Last-letter findings: {len(findings_last)}', file=sys.stderr)

    # Print KNOWN acronyms first
    print('\n=== KNOWN ACRONYMS FOUND ===\n')
    for f in findings_first + findings_last:
        if f['type'] == 'KNOWN':
            direction = 'FIRST' if f in findings_first else 'LAST'
            words_str = ' '.join(f['words'])
            print(f"  [{direction}] {f['ref']:18} {f['acronym']:8} = {f['name']}")
            print(f"    Words: {words_str[:120]}")
            print()

    # Print WORD matches (acronym = real NT word), top 30 by word length
    print('\n=== ACRONYM = REAL NT WORD (first letters), top 30 ===\n')
    word_findings = [f for f in findings_first if f['type'] == 'WORD']
    word_findings.sort(key=lambda f: (-f['length'], f['ref']))
    seen = set()
    shown = 0
    for f in word_findings:
        key = (f['ref'], f['acronym'])
        if key in seen:
            continue
        seen.add(key)
        words_str = ' | '.join(f['words'])
        print(f"  {f['ref']:18} [{f['acronym']:8} iso={f['iso']:4}] ← {words_str[:100]}")
        shown += 1
        if shown >= 30:
            break

    # Print TARGET matches, top 30
    print('\n=== ACRONYM ISO = THEOLOGICAL TARGET (first letters), top 30 ===\n')
    target_findings = [f for f in findings_first if f['type'] == 'TARGET']
    # Prefer high-value targets and longer acronyms
    target_findings.sort(key=lambda f: (-f['iso'], -f['length']))
    seen = set()
    shown = 0
    for f in target_findings:
        key = (f['ref'], f['acronym'])
        if key in seen:
            continue
        seen.add(key)
        words_str = ' | '.join(f['words'])
        print(f"  {f['ref']:18} [{f['acronym']:8} iso={f['iso']:4} = {f['name']:18}] ← {words_str[:100]}")
        shown += 1
        if shown >= 30:
            break


if __name__ == '__main__':
    main()
