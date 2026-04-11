#!/usr/bin/env python3
"""
Direct retroversion scan: for each NT Greek form, compare its isopsephy
against the gematria of its OWN canonical Hebrew retroversion.

Cases:
  (a) iso(form) == gem(retroversion_canonical)  → EXACT CROSS-LANG
  (b) iso(form) == gem(retroversion_any_form)   → weaker match

(a) is particularly interesting because it means the Greek writer chose a
form whose isopsephy matches the standard Hebrew word for the same concept.
This is a "self-referential" cross-language encoding: the Greek numerically
encodes its own Hebrew translation.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, '/home/bu/Documents/Biblia')
import openpyxl
from biblegematria.biblegematria import load_sblgnt, isopsephy

WORK = Path('/home/bu/Documents/Biblia/retroversion_work')

_EDITORIAL_RE = __import__('re').compile(r'[⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸓⸔⸕⸖⸗]')


def clean_greek(word):
    w = _EDITORIAL_RE.sub('', word)
    return w.strip('.,;·:()[]·\u0387')


def main():
    print('Loading retroversion + SBLGNT...', file=sys.stderr)
    with open(WORK / 'retroversion.json', encoding='utf-8') as f:
        retroversion = json.load(f)
    sblgnt = load_sblgnt()

    exact_matches = []  # iso(form) == gem(canonical)
    candidate_matches = []  # iso(form) == gem(some candidate, not canonical)

    from collections import Counter
    nt_forms = {}
    for w in sblgnt:
        form = clean_greek(w['word'])
        lemma = clean_greek(w['lemma'])
        if not form:
            continue
        iso = isopsephy(form)
        if iso <= 0:
            continue
        key = form
        if key not in nt_forms:
            nt_forms[key] = {
                'lemma': lemma, 'iso': iso, 'count': 0,
                'first_ref': f"{w['book']} {w['chapter']}:{w['verse']}"
            }
        nt_forms[key]['count'] += 1

    print(f'  {len(nt_forms)} unique NT forms', file=sys.stderr)

    for form, info in nt_forms.items():
        iso = info['iso']
        lemma = info['lemma']
        entry = retroversion.get(lemma, {})
        can = entry.get('hebrew_canonical', {})
        can_gem = can.get('gematria', 0)

        if can_gem and can_gem == iso:
            exact_matches.append({
                'form': form, 'iso': iso, 'lemma': lemma,
                'ro': entry.get('ro', ''),
                'count': info['count'], 'first_ref': info['first_ref'],
                'heb_stem': can.get('stem', ''),
                'heb_form': can.get('form_most_common', ''),
                'strongs': can.get('strongs_he', ''),
            })
        else:
            # Check candidates too
            for c in entry.get('hebrew_candidates', [])[:10]:
                if c.get('gematria_stem') == iso:
                    candidate_matches.append({
                        'form': form, 'iso': iso, 'lemma': lemma,
                        'ro': entry.get('ro', ''),
                        'count': info['count'], 'first_ref': info['first_ref'],
                        'heb_stem': c.get('stem', ''),
                        'heb_form': c.get('form', ''),
                        'strongs': c.get('oshb_strongs', ''),
                        'source': 'candidate',
                    })
                    break  # only first match per form

    # Rank
    exact_matches.sort(key=lambda x: -x['count'])
    candidate_matches.sort(key=lambda x: -x['count'])

    print(f'\n=== EXACT MATCHES: iso(form) == gem(canonical) ===')
    print(f'Total: {len(exact_matches)}')
    print(f'\nTop 30 by NT frequency:')
    for m in exact_matches[:30]:
        print(f"  {m['iso']:>5} | {m['form']:18} ×{m['count']:<3} "
              f"({m['lemma']:12} = {m['ro'][:18]:18}) "
              f"↔ {m['heb_stem']:10} ({m['heb_form']:12}) H{m['strongs'] or '-'}")

    print(f'\n=== CANDIDATE MATCHES: iso(form) == gem(non-canonical candidate) ===')
    print(f'Total: {len(candidate_matches)}')
    print(f'\nTop 20 by NT frequency:')
    for m in candidate_matches[:20]:
        print(f"  {m['iso']:>5} | {m['form']:18} ×{m['count']:<3} "
              f"({m['lemma']:12} = {m['ro'][:18]:18}) "
              f"↔ {m['heb_stem']:10} ({m['heb_form']:12})")

    # Write both xlsx
    def write_xlsx(matches, path, title):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = title
        ws.append(['NT Form', 'Iso', 'Greek Lemma', 'RO', 'NT #', 'First ref',
                   'Hebrew stem', 'Hebrew form', 'Strongs H'])
        for m in matches:
            ws.append([m['form'], m['iso'], m['lemma'], m['ro'], m['count'],
                       m['first_ref'], m['heb_stem'], m['heb_form'], m['strongs']])
        ws.freeze_panes = 'A2'
        for col in ws.columns:
            try:
                max_len = max(len(str(c.value or '')) for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)
            except (ValueError, AttributeError):
                pass
        wb.save(path)

    write_xlsx(exact_matches, WORK / 'nt_direct_retroversion_exact.xlsx', 'Exact')
    write_xlsx(candidate_matches, WORK / 'nt_direct_retroversion_candidate.xlsx', 'Candidate')
    print(f'\nWrote nt_direct_retroversion_exact.xlsx ({len(exact_matches)} rows)')
    print(f'Wrote nt_direct_retroversion_candidate.xlsx ({len(candidate_matches)} rows)')


if __name__ == '__main__':
    main()
