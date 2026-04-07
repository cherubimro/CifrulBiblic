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
import json
import os
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

    _bar_fmt = '\033[32m{desc}: \033[1;33m{percentage:3.0f}%\033[32m|\033[96m{bar}\033[32m| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]\033[0m'

    if workers <= 1:
        for hw, hw_ref in tqdm(hebrew_list, desc="Scanning", unit="words",
                               bar_format=_bar_fmt):
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
                             desc=f"Scanning ({workers} workers)", unit="words",
                             bar_format=_bar_fmt):
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception:
                    pass

    # Sort for deterministic output (parallel workers return in random order)
    all_results.sort(key=lambda r: (r[7], r[1], r[8], r[10], r[0]))  # val, gw, hw, method, type
    cipher_word_results.sort(key=lambda r: (r[4], r[6]))  # hw, method

    return all_results, cipher_word_results


def format_results(direct_results, cipher_word_results, top=None, show_romanian=True, num_index=None):
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
                # Search using Romanian stemmer for better matching
                try:
                    import Stemmer
                    _stemmer = Stemmer.Stemmer('romanian')
                except ImportError:
                    _stemmer = None

                # Build variants from translation (split on /)
                variants = [v.strip() for v in gw_ro.split('/')]
                expanded = []
                for v in variants:
                    expanded.append(v)
                    if v.startswith('a '):
                        expanded.append(v[2:])
                    # Split multi-word translations into individual words
                    words_in_v = v.split()
                    if len(words_in_v) > 1:
                        for w in words_in_v:
                            if len(w) >= 3:  # skip short particles
                                expanded.append(w)

                # Load RoWordNet synonyms (cached)
                if not hasattr(format_results, '_syn_cache'):
                    _syn_path = os.path.join(os.path.dirname(__file__),
                                            'biblegematria', 'synonyms_ro.json')
                    if not os.path.exists(_syn_path):
                        _syn_path = os.path.join(os.path.dirname(__file__),
                                                'synonyms_ro.json')
                    try:
                        with open(_syn_path, 'r', encoding='utf-8') as sf:
                            format_results._syn_cache = json.load(sf)
                    except:
                        format_results._syn_cache = {}

                # Expand with synonyms from RoWordNet
                for v in list(expanded):
                    vl = v.lower().strip()
                    if vl.startswith('a '):
                        vl = vl[2:]
                    for w in vl.split():
                        if w in format_results._syn_cache:
                            for syn in format_results._syn_cache[w]:
                                expanded.append(syn)

                # Stem the translation variants
                stems = set()
                for v in expanded:
                    if _stemmer:
                        st = _stemmer.stemWord(v.lower())
                        stems.add(st[:3] if len(st) >= 3 else st)
                    else:
                        r = v.lower().rstrip('ă').rstrip('e').rstrip('a').rstrip('i')
                        stems.add(r[:3] if len(r) >= 3 else r)

                words_list = verse_text.split()
                found_idx = -1
                for idx, w in enumerate(words_list):
                    w_clean = w.lower().strip('.,;:!?«»„"()—–')
                    if _stemmer:
                        w_stem = _stemmer.stemWord(w_clean)
                    else:
                        w_stem = w_clean
                    # Match if any stem prefix matches
                    for st in stems:
                        if st and len(st) >= 3 and w_stem.startswith(st[:3]):
                            found_idx = idx
                            break
                        elif st and st in w_clean:
                            found_idx = idx
                            break
                    if found_idx >= 0:
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

        if gw_ro:
            pad = 14 - len(gw_ro)
            gw_ro_col = f"\033[1;33m{gw_ro}\033[0m" + ' ' * max(0, pad)
        else:
            gw_ro_col = ' ' * 14
        line = (f"{rtype:<8} {gw:<16} {gw_ro_col} {gref:>9} {val:>5} "
                f"{hw:<16} {hw_ro:<14} {href:>9} {mshort:<10} {fstr:<22} "
                f"{ro_context}")
        lines.append(line)

        # Number index match on separate lines
        if num_index and val in num_index:
            lines.append(f"         \033[1;35m↳ {val} apare ca număr explicit în:\033[0m")
            for loc in num_index[val]:
                lines.append(f"           \033[35m{loc}\033[0m")

    for rtype, gw, gref, val_unused, hw, href, method in cipher_word_results:
        key = f"{hw}-{method}"
        if key not in seen:
            seen.add(key)
            hw_ro = hebrew_to_ro(hw)
            line = (f"{'C_WORD':<8} {'—':<16} {'—':<14} {'—':>9} {'—':>5} "
                    f"{hw:<16} {hw_ro:<14} {href:>9} {method:<10} {'—':<22}")
            lines.append(line)

    if top:
        # Count actual results (not magenta/context lines), keep header
        header = lines[:2]
        result_lines = []
        count = 0
        for line in lines[2:]:
            result_lines.append(line)
            # A result line starts with DIRECT/CIPHER/C_WORD, magenta lines start with spaces
            if not line.startswith(' '):
                count += 1
                if count >= top:
                    break
        lines = header + result_lines

    return lines


_USAGE = """
\033[1mbiblegematria scanner v0.3.3\033[0m — Cross-language biblical gematria

\033[1;33mUTILIZARE:\033[0m
  python scan.py --book 64-Jn --strict --top 50       # Ioan, filtrat, top 50
  python scan.py --book 62-Mk --hebrew-book Isaiah     # Marcu × Isaia
  python scan.py --strict -j 8 -o rezultate.tsv        # tot NT × tot VT, strict
  python scan.py --fullscan -j 8 -o full.tsv           # TOATE metodele, fără filtre

\033[1;33mCĂRȚI NT (--book):\033[0m
  61-Mt  Matei          66-Ro  Romani         75-1Ti 1Timotei
  62-Mk  Marcu          67-1Co 1Corinteni     76-2Ti 2Timotei
  63-Lk  Luca           68-2Co 2Corinteni     77-Tit Tit
  64-Jn  Ioan           69-Ga  Galateni       78-Phm Filimon
  65-Ac  Fapte          70-Eph Efeseni        79-Heb Evrei
                        71-Php Filipeni       80-Jas Iacov
                        72-Col Coloseni       81-1Pe 1Petru
                        73-1Th 1Tesaloniceni  82-2Pe 2Petru
                        74-2Th 2Tesaloniceni  83-1Jn 1Ioan
                                              84-2Jn 2Ioan
                                              85-3Jn 3Ioan
                                              86-Jud Iuda
                                              87-Re  Apocalipsa

\033[1;33mCĂRȚI VT (--hebrew-book):\033[0m
  Genesis    Exodus     Leviticus   Numbers      Deuteronomy
  Joshua     Judges     I_Samuel    II_Samuel    I_Kings      II_Kings
  Isaiah     Jeremiah   Ezekiel     Hosea        Joel         Amos
  Obadiah    Jonah      Micah       Nahum        Habakkuk     Zephaniah
  Haggai     Zechariah  Malachi     Psalms       Proverbs     Job
  Song_of_Songs  Ruth   Lamentations  Ecclesiastes  Esther   Daniel
  Ezra       Nehemiah   I_Chronicles  II_Chronicles

\033[1;33mOPȚIUNI:\033[0m
  --strict      Doar 7 metode atestate + factori teologici (×7,×14,×26,×37)
  --fullscan    Toate 23 metodele, fără filtre (atenție: multe rezultate!)
  --numbers     Caută doar cuvinte a căror valoare = un număr explicit din Biblie
                (necesită numbers.txt generat de numbers.py)
  --top N       Afișează doar primele N rezultate
  --min-value N Valoare minimă (implicit: 10)
  -j N          Workeri paraleli (implicit: 4)
  -o FIȘIER     Salvează în fișier
"""


def main():
    parser = argparse.ArgumentParser(
        description='Cross-language biblical gematria scanner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Exemple: python scan.py --book 64-Jn --strict --top 50')
    parser.add_argument('-o', '--output', help='Output file')
    parser.add_argument('--book', help='SBLGNT book code (e.g., 64-Jn, 62-Mk)')
    parser.add_argument('--hebrew-book', help='Masoretic book (e.g., Genesis, Isaiah)')
    parser.add_argument('--top', type=int, help='Show only top N results')
    parser.add_argument('--min-value', type=int, default=10,
                        help='Minimum value to report (default: 10)')
    parser.add_argument('-j', '--workers', type=int, default=4,
                        help='Number of parallel workers (default: 4)')
    parser.add_argument('--strict', action='store_true',
                        help='Only strong methods + theological factors')
    parser.add_argument('--fullscan', action='store_true',
                        help='All 23 methods, no filters (overrides --strict)')
    parser.add_argument('--numbers', nargs='?', const='all', default=None,
                        metavar='MIN-MAX',
                        help='Show only values matching biblical numbers. '
                             'Optional range: --numbers 100-200, --numbers 153-153')
    args = parser.parse_args()

    # No arguments at all → show usage
    if not args.book and not args.hebrew_book and not args.fullscan and args.numbers is None:
        print(_USAGE, file=sys.stderr)
        sys.exit(0)

    # --fullscan overrides --strict
    if args.fullscan:
        args.strict = False

    # --numbers mode: load number index
    num_index = None
    if args.numbers is not None:
        num_txt = os.path.join(os.path.dirname(__file__), 'numbers.txt')
        if not os.path.exists(num_txt):
            print(f"⚠  numbers.txt nu există. Rulează mai întâi: python numbers.py", file=sys.stderr)
            sys.exit(1)

        # Parse range if given
        num_min, num_max = 0, 999999999
        if args.numbers != 'all':
            try:
                range_parts = args.numbers.split('-')
                num_min = int(range_parts[0])
                num_max = int(range_parts[1]) if len(range_parts) > 1 else num_min
            except ValueError:
                print(f"⚠  Format incorect. Folosește: --numbers 100-200", file=sys.stderr)
                sys.exit(1)

        num_index = {}
        with open(num_txt, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    val = int(parts[0])
                    if num_min <= val <= num_max:
                        num_index.setdefault(val, []).append(f"{parts[1]}:{parts[2]}")

        print(f"Numbers index: {len(num_index)} valori în range [{num_min}-{num_max}]", file=sys.stderr)

    print(f"biblegematria scanner v0.3.3", file=sys.stderr)
    mode = "NUMBERS" if args.numbers else ("FULLSCAN (23 metode)" if args.fullscan else ("STRICT (7 metode)" if args.strict else "NORMAL (23 metode)"))
    print(f"Mod: {mode}, Workers: {args.workers}", file=sys.stderr)

    print("\n--- Loading texts ---", file=sys.stderr)
    greek = extract_greek_vocabulary(book=args.book)
    hebrew = extract_hebrew_vocabulary(book=args.hebrew_book)
    print(f"Greek forms: {len(greek)}, Hebrew words: {len(hebrew)}", file=sys.stderr)

    direct, cipher_words = run_scan_parallel(
        greek, hebrew, args.min_value, args.workers, args.strict)

    # Filter by numbers if --numbers
    if num_index:
        direct = [r for r in direct if r[7] in num_index]  # r[7] = val
        print(f"\nFiltered by numbers.txt: {len(direct)} potriviri", file=sys.stderr)

    n_results = len(direct) + len(cipher_words)
    print(f"\nResults: {len(direct)} direct/cipher-cross, "
          f"{len(cipher_words)} cipher-words", file=sys.stderr)

    if n_results > 50000 and not args.strict and not args.fullscan and not args.numbers:
        print(f"\n⚠  {n_results:,} rezultate — prea mult zgomot. "
              f"Recomandare: adaugă --strict pentru filtrare.", file=sys.stderr)

    lines = format_results(direct, cipher_words, top=args.top, num_index=num_index)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        for line in lines:
            print(line)


if __name__ == '__main__':
    main()
