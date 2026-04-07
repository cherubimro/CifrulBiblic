#!/usr/bin/env python3
"""Full cross-language scan: all NT Greek words × all VT Hebrew words × all 23 methods × all ciphers.

Usage:
    python scan.py                        # full scan, output to stdout
    python scan.py -o results.tsv         # save to file
    python scan.py --book 64-Jn           # scan only Gospel of John
    python scan.py --top 50              # show top 50 results
    python scan.py -j 4                  # use 4 parallel workers
    python scan.py --strict              # only strong methods + theological factors
    python scan.py --book 64-Jn -j 8 --strict -o john_scan.tsv
"""

import argparse
import sys
import re
from concurrent.futures import ProcessPoolExecutor, as_completed

from biblegematria import load_sblgnt, load_masoretic, isopsephy
from biblegematria.gematria import factorize_theological
from biblegematria.ciphers import atbash_hebrew, albam, avgad
from hebrew import Hebrew, GematriaTypes

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **kw):
        total = kw.get('total', '?')
        desc = kw.get('desc', '')
        print(f"{desc} ({total} items)...", file=sys.stderr)
        return it

# NT book names: SBLGNT code → Romanian full, Romanian short
_NT_BOOKS = {
    'Mt': ('Matei', 'Mt'), 'Mk': ('Marcu', 'Mc'), 'Lk': ('Luca', 'Lc'),
    'Jn': ('Ioan', 'In'), 'Ac': ('Fapte', 'Fa'),
    'Ro': ('Romani', 'Rm'), '1Co': ('1Cor', '1Co'), '2Co': ('2Cor', '2Co'),
    'Ga': ('Galateni', 'Ga'), 'Eph': ('Efeseni', 'Ef'),
    'Php': ('Filipeni', 'Fl'), 'Col': ('Coloseni', 'Col'),
    '1Th': ('1Tes', '1Ts'), '2Th': ('2Tes', '2Ts'),
    '1Ti': ('1Tim', '1Ti'), '2Ti': ('2Tim', '2Ti'),
    'Tit': ('Tit', 'Tt'), 'Phm': ('Filimon', 'Fm'),
    'Heb': ('Evrei', 'Ev'), 'Jas': ('Iacov', 'Ic'),
    '1Pe': ('1Petru', '1Pt'), '2Pe': ('2Petru', '2Pt'),
    '1Jn': ('1Ioan', '1In'), '2Jn': ('2Ioan', '2In'),
    '3Jn': ('3Ioan', '3In'), 'Jud': ('Iuda', 'Id'),
    'Re': ('Apocalipsa', 'Ap'),
}

# VT book names: filename → Romanian full, Romanian short
_VT_BOOKS = {
    'Genesis': ('Facerea', 'Fc'), 'Exodus': ('Ieșirea', 'Iș'),
    'Leviticus': ('Leviticul', 'Lv'), 'Numbers': ('Numeri', 'Nm'),
    'Deuteronomy': ('Deuteronom', 'Dt'),
    'Joshua': ('Iosua', 'Is'), 'Judges': ('Judecători', 'Jd'),
    'I_Samuel': ('1Samuel', '1S'), 'II_Samuel': ('2Samuel', '2S'),
    'I_Kings': ('3Regi', '3R'), 'II_Kings': ('4Regi', '4R'),
    'Isaiah': ('Isaia', 'Is'), 'Jeremiah': ('Ieremia', 'Ir'),
    'Ezekiel': ('Iezechiel', 'Iz'),
    'Hosea': ('Osea', 'Os'), 'Joel': ('Ioel', 'Il'), 'Amos': ('Amos', 'Am'),
    'Obadiah': ('Avdie', 'Av'), 'Jonah': ('Iona', 'Io'),
    'Micah': ('Miheia', 'Mi'), 'Nahum': ('Naum', 'Na'),
    'Habakkuk': ('Avacum', 'Avc'), 'Zephaniah': ('Sofonie', 'Sf'),
    'Haggai': ('Agheu', 'Ag'), 'Zechariah': ('Zaharia', 'Za'),
    'Malachi': ('Maleahi', 'Ml'),
    'Psalms': ('Psalmi', 'Ps'), 'Proverbs': ('Proverbe', 'Pr'),
    'Job': ('Iov', 'Iv'),
    'Song_of_Songs': ('Cânt', 'Cc'), 'Ruth': ('Rut', 'Rt'),
    'Lamentations': ('Plângeri', 'Pl'), 'Ecclesiastes': ('Ecleziast', 'Ec'),
    'Esther': ('Estera', 'Est'), 'Daniel': ('Daniel', 'Dn'),
    'Ezra': ('Ezdra', 'Ezd'), 'Nehemiah': ('Neemia', 'Ne'),
    'I_Chronicles': ('1Paralipomena', '1Pa'), 'II_Chronicles': ('2Paralipomena', '2Pa'),
}

_ALL_METHODS = list(GematriaTypes)
_CIPHERS = {'ATBASH': atbash_hebrew, 'ALBAM': albam, 'AVGAD': avgad}

# Strict mode: only these well-established methods
_STRICT_METHODS = {
    'MISPAR_HECHRACHI',  # standard
    'MISPAR_GADOL',      # large (final letters)
    'MISPAR_SIDURI',     # ordinal
    'MISPAR_KATAN',      # small/reduced
    'ATBASH',            # atbash value
    'ALBAM',             # albam value
    'AVGAD',             # avgad value
}

# Strict mode: result must have at least one of these factors
_STRICT_FACTORS = {7, 14, 26, 37}


def _clean_hebrew(word):
    """Strip vowels, cantillation, and HTML artifacts from Hebrew word.
    Returns a LIST of clean consonantal words (splits on maqaf).
    """
    w = word.replace('&nbsp;', ' ').replace('&thinsp;', ' ')
    w = w.replace('\u00a0', ' ').replace('\u2009', ' ')
    w = re.sub(r'&[a-z]+;', ' ', w)            # HTML entities → space
    w = re.sub(r'\{[^}]*\}', '', w)            # remove {פ} etc.
    w = w.replace('\u05BE', ' ')               # maqaf → space (split words!)
    w = w.replace('׀', ' ')                    # paseq → space
    w = re.sub(r'[\u0591-\u05C7]', '', w)      # cantillation + vowels
    w = re.sub(r'[׃]', '', w)                  # sof pasuq
    # Split into individual words
    parts = []
    for p in w.split():
        p = p.strip()
        if p and len(p) >= 2:
            parts.append(p)
    return parts


# SBLGNT editorial marks to strip (not part of the original manuscript)
_EDITORIAL = re.compile(r'[⸀⸁⸂⸃⸄⸅⸆⸇⸈⸉⸊⸋⸌⸍⸎⸏⸐⸑⸒⸓⸔⸕⸖⸗]')


def _clean_greek(word):
    """Strip SBLGNT editorial marks, punctuation, brackets — keep only the manuscript text."""
    w = _EDITORIAL.sub('', word)
    w = w.strip('.,;·:()[]·\u0387')  # Greek ano teleia, brackets, punctuation
    return w


def extract_greek_vocabulary(book=None):
    """Extract unique Greek word forms (not lemmas!) with first occurrence reference.

    Classical isopsephy uses the exact word from the manuscript, not the dictionary form.
    E.g., βαΐα (plural, as written) = 14 = David, but βάϊον (lemma) = 133.
    SBLGNT editorial marks (⸀⸁⸂⸃) are stripped — they are modern annotations.
    """
    all_words = load_sblgnt(book=book)
    forms = {}  # {word_form: (isopsephy, short_ref, full_book, chapter, verse, lemma)}
    for w in all_words:
        word = _clean_greek(w['word'])
        if word and word not in forms:
            val = isopsephy(word)
            if val > 0:
                full, short = _NT_BOOKS.get(w['book'], (w['book'], w['book']))
                ref = f"{short}{w['chapter']}:{w['verse']}"
                lemma = _clean_greek(w.get('lemma', ''))
                forms[word] = (val, ref, full, w['chapter'], w['verse'], lemma)
    return forms


def extract_hebrew_vocabulary(book=None):
    """Extract unique Hebrew words with first occurrence reference."""
    verses = load_masoretic(book=book)
    words = {}
    for v in verses:
        for w in v['words']:
            for clean in _clean_hebrew(w):  # now returns list
                if clean not in words:
                    try:
                        val = Hebrew(clean).gematria(GematriaTypes.MISPAR_HECHRACHI)
                        if val > 0:
                            full, short = _VT_BOOKS.get(v['book'], (v['book'], v['book']))
                            ref = f"{short}{v['chapter']}:{v['verse']}"
                            words[clean] = (val, ref)
                    except Exception:
                        pass
    return words


def _scan_one_hebrew(hw, hw_ref, greek_by_value, min_value, strict):
    """Scan one Hebrew word against all Greek values. Called in parallel."""
    results = []
    h = Hebrew(hw)

    methods = [gt for gt in _ALL_METHODS if gt.name in _STRICT_METHODS] if strict else _ALL_METHODS

    # Direct: selected methods
    for gt in methods:
        try:
            hv = h.gematria(gt)
            if hv >= min_value and hv in greek_by_value:
                if strict:
                    factors = factorize_theological(hv)
                    if not any(f in _STRICT_FACTORS for f in
                              [v for v in factors.values()]):
                        has_factor = any(hv % f == 0 for f in _STRICT_FACTORS)
                        if not has_factor:
                            continue
                for gw, gref, full_bk, ch, vs, lemma in greek_by_value[hv]:
                    results.append(('DIRECT', gw, lemma, gref, full_bk, ch, vs, hv, hw, hw_ref, gt.name))
        except Exception:
            pass

    # Cipher → gematria → cross-language
    for cipher_name, cipher_fn in _CIPHERS.items():
        try:
            cipher_result = cipher_fn(hw)
            hc = Hebrew(cipher_result)
            for gt in methods:
                try:
                    hv = hc.gematria(gt)
                    if hv >= min_value and hv in greek_by_value:
                        if strict:
                            has_factor = any(hv % f == 0 for f in _STRICT_FACTORS)
                            if not has_factor:
                                continue
                        for gw, gref, full_bk, ch, vs, lemma in greek_by_value[hv]:
                            results.append(('CIPHER', gw, lemma, gref, full_bk, ch, vs, hv,
                                          f"{hw}→{cipher_name}→{cipher_result}",
                                          hw_ref, gt.name))
                except Exception:
                    pass
        except Exception:
            pass

    return results


def run_scan_parallel(greek_forms, hebrew_words, min_value=10, workers=4, strict=False):
    """Run cross-language scan with parallel workers and progress bar."""

    greek_by_value = {}
    for gw, info in greek_forms.items():
        gv = info[0]      # isopsephy value
        gref = info[1]    # short reference
        full_bk = info[2] # full book name (for Romanian lookup)
        ch = info[3]      # chapter
        vs = info[4]      # verse
        lemma = info[5]   # lemma (for lexicon lookup)
        if gv >= min_value:
            greek_by_value.setdefault(gv, []).append((gw, gref, full_bk, ch, vs, lemma))

    hebrew_list = [(hw, info[1]) for hw, info in hebrew_words.items()]
    all_results = []

    # Cipher word matches
    cipher_word_results = []
    heb_set = set(hebrew_words.keys())
    for hw, (_, hw_ref) in hebrew_words.items():
        for cipher_name, cipher_fn in _CIPHERS.items():
            try:
                result = cipher_fn(hw)
                if result in heb_set and result != hw:
                    r_ref = hebrew_words[result][1]
                    cipher_word_results.append(
                        ('CIPHER_WORD', '', '', 0, hw, hw_ref,
                         f"{cipher_name}→{result} ({r_ref})"))
            except Exception:
                pass

    if workers <= 1:
        for hw, hw_ref in tqdm(hebrew_list, desc="Scanning", unit="words"):
            results = _scan_one_hebrew(hw, hw_ref, greek_by_value, min_value, strict)
            all_results.extend(results)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_scan_one_hebrew, hw, hw_ref, greek_by_value,
                              min_value, strict): hw
                for hw, hw_ref in hebrew_list
            }
            for future in tqdm(as_completed(futures), total=len(futures),
                             desc=f"Scanning ({workers} workers)", unit="words"):
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception:
                    pass

    return all_results, cipher_word_results


def format_results(direct_results, cipher_word_results, top=None, show_romanian=True):
    """Format and deduplicate results as fixed-width columns."""
    from biblegematria.romanian import get_verse

    lines = []

    from biblegematria.lexicon import greek_to_ro, hebrew_to_ro

    # Header
    hdr = (f"{'TIP':<8} {'GREACĂ':<16} {'(ro)':<14} {'REF':>9} {'VAL':>5} "
           f"{'EBRAICĂ':<16} {'(ro)':<14} {'REF':>9} {'METODA':<10} {'FACTORI':<22} "
           f"{'VERSETUL (Biblia Ortodoxă)'}")
    lines.append(hdr)
    lines.append("─" * 200)

    seen = set()
    for rtype, gw, lemma, gref, full_bk, ch, vs, val, hw, href, method in direct_results:
        key = f"{rtype}-{gw}-{hw}-{method}"
        if key in seen:
            continue
        seen.add(key)
        factors = factorize_theological(val) if val > 0 else {}
        fstr = ', '.join(f"{v}×{k}" for k, v in factors.items()) if factors else ''
        mshort = method.replace('MISPAR_', '')

        # Romanian translations from lexicon (form → lemma → Strong's)
        gw_ro = greek_to_ro(gw, lemma)
        hw_clean = hw.split('→')[0] if '→' in hw else hw
        hw_ro = hebrew_to_ro(hw_clean)

        # Romanian verse context: find the word, show 2 before + BOLD + 2 after
        ro_context = ''
        if show_romanian and full_bk and gw_ro:
            verse_text = get_verse(full_bk, ch, vs, max_len=0)
            if verse_text:
                # Search for the Romanian translation root in the verse
                root = gw_ro.lower().rstrip('ă').rstrip('e').rstrip('a')
                if len(root) < 3:
                    root = gw_ro.lower()
                words_list = verse_text.split()
                found_idx = -1
                for idx, w in enumerate(words_list):
                    if root in w.lower():
                        found_idx = idx
                        break
                if found_idx >= 0:
                    start = max(0, found_idx - 2)
                    end = min(len(words_list), found_idx + 3)
                    snippet = words_list[start:end]
                    # Bold the matched word
                    rel_idx = found_idx - start
                    snippet[rel_idx] = f"\033[1;33m{snippet[rel_idx]}\033[0m"
                    ro_context = '…' + ' '.join(snippet) + '…'
                else:
                    # No root match — show first 40 chars
                    ro_context = verse_text[:40] + '…'

        line = (f"{rtype:<8} {gw:<16} {gw_ro:<14} {gref:>9} {val:>5} "
                f"{hw:<16} {hw_ro:<14} {href:>9} {mshort:<10} {fstr:<22} "
                f"{ro_context}")
        lines.append(line)

    for rtype, gw, gref, val_unused, hw, href, method in cipher_word_results:
        key = f"{hw}-{method}"
        if key not in seen:
            seen.add(key)
            hw_ro = hebrew_to_ro(hw)
            line = (f"{'C_WORD':<8} {'—':<16} {'—':<14} {'—':>9} {'—':>5} "
                    f"{hw:<16} {hw_ro:<14} {href:>9} {method:<10} {'—':<22}")
            lines.append(line)

    if top:
        lines = lines[:2] + lines[2:top+2]

    return lines


def main():
    parser = argparse.ArgumentParser(
        description='Cross-language biblical gematria scanner')
    parser.add_argument('-o', '--output', help='Output file')
    parser.add_argument('--book', help='SBLGNT book code (e.g., 64-Jn, 62-Mk)')
    parser.add_argument('--hebrew-book', help='Masoretic book (e.g., Genesis, Isaiah)')
    parser.add_argument('--top', type=int, help='Show only top N results')
    parser.add_argument('--min-value', type=int, default=10,
                        help='Minimum value to report (default: 10)')
    parser.add_argument('-j', '--workers', type=int, default=4,
                        help='Number of parallel workers (default: 4)')
    parser.add_argument('--strict', action='store_true',
                        help='Only strong methods (STD,GADOL,SIDURI,KATAN,ATBASH,ALBAM,AVGAD) '
                             'and results with theological factors (×7,×14,×26,×37)')
    args = parser.parse_args()

    print(f"biblegematria scanner v0.2.0", file=sys.stderr)
    print(f"Workers: {args.workers}, Strict: {args.strict}", file=sys.stderr)

    print("\n--- Loading texts ---", file=sys.stderr)
    greek = extract_greek_vocabulary(book=args.book)
    hebrew = extract_hebrew_vocabulary(book=args.hebrew_book)
    print(f"Greek forms: {len(greek)}, Hebrew words: {len(hebrew)}", file=sys.stderr)

    direct, cipher_words = run_scan_parallel(
        greek, hebrew, args.min_value, args.workers, args.strict)

    n_results = len(direct) + len(cipher_words)
    print(f"\nResults: {len(direct)} direct/cipher-cross, "
          f"{len(cipher_words)} cipher-words", file=sys.stderr)

    if n_results > 50000 and not args.strict:
        print(f"\n⚠  {n_results:,} rezultate — prea mult zgomot. "
              f"Recomandare: adaugă --strict pentru filtrare.", file=sys.stderr)

    lines = format_results(direct, cipher_words, top=args.top)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        for line in lines:
            print(line)


if __name__ == '__main__':
    main()
