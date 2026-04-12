#!/usr/bin/env python3
"""
Merge BLB + openBible citation lists into a unified set, then
re-run the isopsephy-match scan on the larger dataset.
"""
import re
import sys
from pathlib import Path

WORK = Path(__file__).parent

# openBible uses "Matt.1.23", BLB uses "Mat 1:23"
OB_TO_BLB = {
    'Matt': 'Mat', 'Mark': 'Mar', 'Luke': 'Luk', 'John': 'Jhn',
    'Acts': 'Act', 'Rom': 'Rom', '1Cor': '1Co', '2Cor': '2Co',
    'Gal': 'Gal', 'Eph': 'Eph', 'Phil': 'Phl', 'Col': 'Col',
    '1Thess': '1Th', '2Thess': '2Th', '1Tim': '1Ti', '2Tim': '2Ti',
    'Titus': 'Tit', 'Phlm': 'Phm', 'Heb': 'Heb', 'Jas': 'Jas',
    '1Pet': '1Pe', '2Pet': '2Pe', '1John': '1Jo', '2John': '2Jo',
    '3John': '3Jo', 'Jude': 'Jde', 'Rev': 'Rev',
    # OT
    'Gen': 'Gen', 'Exod': 'Exo', 'Lev': 'Lev', 'Num': 'Num',
    'Deut': 'Deu', 'Josh': 'Jos', 'Judg': 'Jdg', 'Ruth': 'Rut',
    '1Sam': '1Sa', '2Sam': '2Sa', '1Kgs': '1Ki', '2Kgs': '2Ki',
    '1Chr': '1Ch', '2Chr': '2Ch', 'Ezra': 'Ezr', 'Neh': 'Neh',
    'Esth': 'Est', 'Job': 'Job', 'Ps': 'Psa', 'Prov': 'Pro',
    'Eccl': 'Ecc', 'Song': 'Sng', 'Isa': 'Isa', 'Jer': 'Jer',
    'Lam': 'Lam', 'Ezek': 'Eze', 'Dan': 'Dan', 'Hos': 'Hos',
    'Joel': 'Joe', 'Amos': 'Amo', 'Obad': 'Oba', 'Jonah': 'Jon',
    'Mic': 'Mic', 'Nah': 'Nah', 'Hab': 'Hab', 'Zeph': 'Zep',
    'Hag': 'Hag', 'Zech': 'Zec', 'Mal': 'Mal',
}


def ob_to_blb(ref):
    """Convert 'Matt.1.23' to 'Mat 1:23'."""
    parts = ref.split('.')
    if len(parts) < 3:
        return None
    book = OB_TO_BLB.get(parts[0])
    if not book:
        return None
    return f"{book} {parts[1]}:{parts[2]}"


def main():
    # Load BLB
    blb_pairs = set()
    with open(WORK / 'blb_parallels.tsv') as f:
        next(f)
        for line in f:
            line = line.strip()
            if not line:
                continue
            nt, ot = line.split('\t', 1)
            blb_pairs.add((nt.strip(), ot.strip()))

    # Load openBible high-confidence
    ob_pairs = set()
    with open(WORK / 'openbible_high.tsv') as f:
        next(f)
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 2:
                continue
            nt_blb = ob_to_blb(parts[0])
            ot_blb = ob_to_blb(parts[1])
            if nt_blb and ot_blb:
                ob_pairs.add((nt_blb, ot_blb))

    # Merge
    all_pairs = blb_pairs | ob_pairs
    blb_only = blb_pairs - ob_pairs
    ob_only = ob_pairs - blb_pairs
    both = blb_pairs & ob_pairs

    print(f'BLB: {len(blb_pairs)}, openBible: {len(ob_pairs)}', file=sys.stderr)
    print(f'Merged: {len(all_pairs)} (BLB-only {len(blb_only)}, OB-only {len(ob_only)}, both {len(both)})', file=sys.stderr)

    # Save merged
    with open(WORK / 'merged_citations.tsv', 'w') as f:
        f.write('NT\tOT\n')
        for nt, ot in sorted(all_pairs):
            f.write(f'{nt}\t{ot}\n')

    print(f'Wrote merged_citations.tsv ({len(all_pairs)} pairs)', file=sys.stderr)


if __name__ == '__main__':
    main()
