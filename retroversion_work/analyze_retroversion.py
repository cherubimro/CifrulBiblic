#!/usr/bin/env python3
"""
Analyze retroversion.json: statistics + discover interesting numerical findings.

Looks for:
- Cross-language matches: isopsephy(greek_form) == gematria(hebrew_form)
- Factor-37 presence in Greek lemmas (Christ factor)
- Matches with "theological base values": 888, 666, 153, 276, 385, 103, 613, ...
- Values that appear in multiple lemmas (convergence)
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

WORK = Path('/home/bu/Documents/Biblia/retroversion_work')

# Base values with theological significance
BASE_VALUES = {
    13: "אחד/אהבה (one/love)",
    14: "דוד (David)",
    17: "יבח/טוב (sacrifice/good)",
    26: "יהוה (YHWH)",
    37: "factor-Iisus (888 = 24×37)",
    86: "אלהים (Elohim)",
    88: "factor (888/37 = 24)",
    103: "Δανιηλ LXX (Daniel)",
    120: "upper room (Acts 1:15), life-limit (Gen 6:3), T(15)",
    148: "פסח (Pesach/Passover)",
    153: "John 21:11 fish / T(17) / H(9)",
    158: "factor",
    186: "H(9) (hexagonal)",
    203: "ברא (bara, create, Gen 1:1)",
    206: "דבר (davar, Word)",
    207: "אור (or, light)",
    211: "הדבר (the Word)",
    214: "רוח (ruach, spirit)",
    248: "אברהם (Abraham), positive mitzvot",
    276: "Acts 27:37 / T(23) / H(12) / רוע (wickedness) / עור (skin/blind)",
    318: "Barnabas 9:7–9 (IH + T)",
    358: "משיח (Messiah) / נחש (serpent)",
    370: "שכן (shakhan, dwell, lemma)",
    385: "שכינה (Shekinah) / σινδόνα",
    391: "ישועה (salvation)",
    450: "T(—)",
    613: "taryag mitzvot (Torah count) / γέγραφα",
    616: "variant Beast",
    666: "Fiara / Neron Qesar / Lateinos",
    753: "",
    800: "ω (Omega) / κύριος / πίστις",
    888: "Ἰησοῦς (8 × 111)",
    911: "ראשית (reshit, beginning)",
    1209: "Atbash sum Ἰησοῦς/Πέτρος/Γαβριήλ (our Finding 6)",
    1260: "Rev 11, 12 (42 months)",
    1480: "Χριστός = 40×37",
    2368: "Ἰησοῦς+Χριστός = 64×37",
}


def load_retroversion():
    with open(WORK / 'retroversion.json', encoding='utf-8') as f:
        return json.load(f)


def stats(ret):
    """Overall statistics."""
    total = len(ret)
    with_alignment = sum(1 for e in ret.values() if 'hebrew_candidates' in e)
    with_canonical = sum(1 for e in ret.values() if 'hebrew_canonical' in e)
    with_biblical = sum(
        1 for e in ret.values()
        if e.get('hebrew_canonical', {}).get('strongs_he') is not None
    )
    print(f'Total Greek lemmas: {total}')
    print(f'  With alignment candidates: {with_alignment} ({100*with_alignment/total:.0f}%)')
    print(f'  With canonical retroversion: {with_canonical} ({100*with_canonical/total:.0f}%)')
    print(f'  With biblical OSHB match: {with_biblical} ({100*with_biblical/total:.0f}%)')


def find_base_matches(ret):
    """Find Greek forms or Hebrew forms matching theological base values."""
    print('\n=== Matches with theological base values ===')
    hits = defaultdict(list)

    for lemma, entry in ret.items():
        ro = entry.get('ro', '')
        iso_lemma = entry.get('isopsephy_lemma')

        # Check lemma isopsephy
        if iso_lemma in BASE_VALUES:
            hits[iso_lemma].append(('Greek lemma', lemma, ro))

        # Check all Greek forms isopsephies
        for f in entry.get('greek_forms', []):
            if f['iso'] in BASE_VALUES:
                hits[f['iso']].append(('Greek form', f['form'], ro))

        # Check Hebrew stems and forms
        can = entry.get('hebrew_canonical', {})
        if can:
            if can.get('gematria') in BASE_VALUES:
                hits[can['gematria']].append(('Hebrew stem', can['stem'], f'< {lemma}'))
            if can.get('form_gematria') in BASE_VALUES:
                hits[can['form_gematria']].append(('Hebrew form', can['form_most_common'], f'< {lemma}'))

        for h in entry.get('hebrew_candidates', [])[:3]:
            if h['gematria_stem'] in BASE_VALUES:
                hits[h['gematria_stem']].append(('Hebrew stem', h['stem'], f'< {lemma}'))

    # Print by value
    for value in sorted(hits.keys()):
        desc = BASE_VALUES[value]
        items = hits[value]
        # Dedupe
        seen = set()
        uniq = []
        for item in items:
            key = (item[0], item[1])
            if key not in seen:
                seen.add(key)
                uniq.append(item)
        uniq = uniq[:10]  # limit per value
        print(f'\n  {value:>5} = {desc}')
        for src, word, note in uniq:
            print(f'    [{src:12}] {word:20} ({note})')


def find_factor_37(ret):
    """Find Greek lemmas whose isopsephy contains 37 as a factor."""
    print('\n=== Greek lemmas with factor 37 (Christ factor) ===')
    factor_37 = []
    for lemma, entry in ret.items():
        iso = entry.get('isopsephy_lemma', 0)
        if iso > 37 and iso % 37 == 0:
            factor_37.append((iso, lemma, entry.get('ro', ''), iso // 37))
    factor_37.sort()
    # Print only multiples up to 64x37 = 2368 (Ιησους + Χριστός)
    count_printed = 0
    for iso, lemma, ro, quot in factor_37:
        if quot <= 64 and count_printed < 30:
            print(f"  {iso:>5} = {quot:>3} × 37 : {lemma:20} ({ro})")
            count_printed += 1
    print(f"  ... ({len(factor_37)} total)")


def find_convergence(ret):
    """Find values where Greek isopsephy == Hebrew canonical gematria."""
    print('\n=== Cross-language convergence: iso(Greek) == gem(Hebrew) ===')
    conv = []
    for lemma, entry in ret.items():
        iso = entry.get('isopsephy_lemma')
        can = entry.get('hebrew_canonical', {})
        gem = can.get('gematria')
        if iso and gem and iso == gem:
            conv.append((iso, lemma, entry.get('ro', ''), can.get('stem', '')))
    conv.sort()
    for iso, lemma, ro, stem in conv[:20]:
        print(f"  {iso:>5}: {lemma:15} = {stem} ({ro})")
    if len(conv) > 20:
        print(f"  ... and {len(conv)-20} more")

    print('\n=== Lemma-form isopsephy == Hebrew gematria ===')
    conv2 = []
    for lemma, entry in ret.items():
        can = entry.get('hebrew_canonical', {})
        gem = can.get('gematria')
        if gem is None:
            continue
        for f in entry.get('greek_forms', [])[:5]:  # top 5 forms
            if f['iso'] == gem:
                conv2.append((f['iso'], f['form'], lemma, entry.get('ro', ''), can.get('stem', '')))
    conv2.sort()
    for iso, form, lemma, ro, stem in conv2[:30]:
        print(f"  {iso:>5}: {form:15} [{lemma:15}] = {stem} ({ro})")
    if len(conv2) > 30:
        print(f"  ... and {len(conv2)-30} more")


if __name__ == '__main__':
    print('Loading retroversion.json...')
    ret = load_retroversion()
    stats(ret)
    find_base_matches(ret)
    find_factor_37(ret)
    find_convergence(ret)
