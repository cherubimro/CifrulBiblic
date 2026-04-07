#!/usr/bin/env python3
"""Index of explicit numbers in biblical texts (NT, LXX, Masoretic).

Usage:
    python numbers_cli.py                    # show all significant numbers
    python numbers_cli.py --query 153        # where does 153 appear?
    python numbers_cli.py --query 666        # where does 666 appear?
    python numbers_cli.py --min 100          # only numbers ≥ 100
    python numbers_cli.py --corpus nt        # only NT
    python numbers_cli.py --corpus lxx       # only LXX
    python numbers_cli.py --corpus mas       # only Masoretic
    python numbers_cli.py --all-three        # numbers in all 3 texts
    python numbers_cli.py -o numbers.tsv     # save to file
"""

import argparse
import sys

from biblegematria.numbers import (
    build_number_index, extract_nt_numbers, extract_lxx_numbers, extract_masoretic_numbers
)


_SIGNIFICANT = {7, 12, 14, 37, 40, 42, 70, 72, 84, 120, 144, 153, 276, 318, 490, 666, 1000, 1260, 1290, 1335, 144000}


def main():
    parser = argparse.ArgumentParser(
        description='Index of explicit numbers in biblical texts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Exemple:
  python numbers_cli.py --query 153
  python numbers_cli.py --query 666
  python numbers_cli.py --all-three
  python numbers_cli.py --corpus nt --min 100""")
    parser.add_argument('--query', type=int, help='Query a specific number')
    parser.add_argument('--min', type=int, default=12, help='Minimum value (default: 12)')
    parser.add_argument('--corpus', choices=['nt', 'lxx', 'mas', 'all'], default='all',
                        help='Which corpus (default: all)')
    parser.add_argument('--all-three', action='store_true',
                        help='Show only numbers that appear in all 3 texts')
    parser.add_argument('--significant', action='store_true',
                        help='Show only theologically significant numbers')
    parser.add_argument('-o', '--output', help='Save to file')
    args = parser.parse_args()

    print("Building number index...", file=sys.stderr)

    if args.query:
        # Query a specific number
        idx = build_number_index(min_value=1)
        val = args.query
        if val not in idx:
            print(f"Numărul {val} nu apare explicit în niciun text.", file=sys.stderr)
            sys.exit(1)

        d = idx[val]
        lines = [f"Numărul {val}:"]
        lines.append(f"{'═'*60}")
        if d['nt']:
            lines.append(f"\n  NT ({len(d['nt'])} apariții):")
            for ref, desc in d['nt']:
                lines.append(f"    {ref:<25} {desc}")
        if d['lxx']:
            lines.append(f"\n  LXX ({len(d['lxx'])} apariții):")
            for ref, desc in d['lxx'][:20]:
                lines.append(f"    {ref:<25} {desc}")
            if len(d['lxx']) > 20:
                lines.append(f"    ... și încă {len(d['lxx'])-20}")
        if d['mas']:
            lines.append(f"\n  Masoretic ({len(d['mas'])} apariții):")
            for ref, desc in d['mas'][:20]:
                lines.append(f"    {ref:<25} {desc}")
            if len(d['mas']) > 20:
                lines.append(f"    ... și încă {len(d['mas'])-20}")

        sig = "★ SEMNIFICATIV TEOLOGIC" if val in _SIGNIFICANT else ""
        if sig:
            lines.append(f"\n  {sig}")

    elif args.corpus != 'all':
        # Single corpus
        if args.corpus == 'nt':
            data = extract_nt_numbers(args.min)
            name = "NT (SBLGNT)"
        elif args.corpus == 'lxx':
            data = extract_lxx_numbers(args.min)
            name = "LXX (Rahlfs 1935)"
        else:
            data = extract_masoretic_numbers(args.min)
            name = "Masoretic"

        lines = [f"Numere explicite în {name} (≥{args.min}):", f"{'═'*70}"]
        lines.append(f"{'VAL':>6} {'REFERINȚĂ':<25} {'COMPONENTE'}")
        lines.append(f"{'─'*70}")
        seen = set()
        for val, ref, desc in data:
            key = f"{val}:{ref}"
            if key in seen: continue
            seen.add(key)
            sig = " ★" if val in _SIGNIFICANT else ""
            lines.append(f"{val:>6} {ref:<25} {desc}{sig}")
        lines.append(f"\nTotal: {len(seen)} apariții")

    elif args.all_three:
        # Numbers in all 3 texts
        idx = build_number_index(args.min)
        all3 = {v: d for v, d in idx.items() if d['nt'] and d['lxx'] and d['mas']}

        lines = [f"Numere care apar în toate cele 3 texte (NT + LXX + Masoretic):", f"{'═'*70}"]
        lines.append(f"{'VAL':>6} {'NT':>5} {'LXX':>5} {'MAS':>5} {'SEMNIFICAȚIE'}")
        lines.append(f"{'─'*70}")
        for v in sorted(all3.keys()):
            d = all3[v]
            sig = " ★" if v in _SIGNIFICANT else ""
            lines.append(f"{v:>6} {len(d['nt']):>5} {len(d['lxx']):>5} {len(d['mas']):>5}{sig}")
        lines.append(f"\nTotal: {len(all3)} numere comune")

    elif args.significant:
        # Only significant numbers
        idx = build_number_index(min_value=1)
        lines = [f"Numere semnificative teologic:", f"{'═'*70}"]
        lines.append(f"{'VAL':>6} {'NT':>5} {'LXX':>5} {'MAS':>5}")
        lines.append(f"{'─'*70}")
        for v in sorted(_SIGNIFICANT):
            if v in idx:
                d = idx[v]
                lines.append(f"{v:>6} {len(d['nt']):>5} {len(d['lxx']):>5} {len(d['mas']):>5}")
                # Show first NT example
                if d['nt']:
                    lines.append(f"       NT:  {d['nt'][0][0]}: {d['nt'][0][1]}")
                if d['lxx']:
                    lines.append(f"       LXX: {d['lxx'][0][0]}: {d['lxx'][0][1]}")
            else:
                lines.append(f"{v:>6}     —     —     —")

    else:
        # Default: show all numbers with references and Romanian context
        from biblegematria.romanian import get_verse, parse_ref

        idx = build_number_index(args.min)
        lines = [f"Index numere biblice (≥{args.min}):", f"{'═'*80}"]

        total_nt = sum(len(d['nt']) for d in idx.values())
        total_lxx = sum(len(d['lxx']) for d in idx.values())
        total_mas = sum(len(d['mas']) for d in idx.values())
        lines.append(f"Valori distincte: {len(idx)}, Apariții: NT={total_nt}, LXX={total_lxx}, Masoretic={total_mas}")
        lines.append("")

        # NT book short→full for Romanian lookup
        nt_short_to_full = {
            'Matei':'Matei','Marcu':'Marcu','Luca':'Luca','Ioan':'Ioan','Fapte':'Fapte',
            'Romani':'Romani','1Cor':'1Cor','2Cor':'2Cor','Galateni':'Galateni',
            'Efeseni':'Efeseni','Filipeni':'Filipeni','Coloseni':'Coloseni',
            'Evrei':'Evrei','Iacov':'Iacov','1Petru':'1Petru','2Petru':'2Petru',
            '1Ioan':'1Ioan','Iuda':'Iuda','Apocalipsa':'Apocalipsa',
        }

        for v in sorted(idx.keys()):
            d = idx[v]
            if not (v in _SIGNIFICANT or (len(d['nt']) + len(d['lxx']) + len(d['mas'])) >= 5):
                continue

            sig = " ★" if v in _SIGNIFICANT else ""
            lines.append(f"\033[1;33m{v}{sig}\033[0m")

            if d['nt']:
                for ref, desc in d['nt'][:3]:
                    # Get Romanian verse
                    ro = ''
                    parts = ref.split()
                    if len(parts) >= 2:
                        bk = parts[0]
                        ch_vs = parts[1].split(':')
                        if len(ch_vs) == 2 and bk in nt_short_to_full:
                            ro = get_verse(nt_short_to_full[bk], int(ch_vs[0]), int(ch_vs[1]), max_len=60)
                    lines.append(f"  NT:  {ref:<22} {desc}")
                    if ro:
                        lines.append(f"       \033[2m{ro}\033[0m")
                if len(d['nt']) > 3:
                    lines.append(f"       ... și încă {len(d['nt'])-3} apariții NT")

            if d['lxx']:
                for ref, desc in d['lxx'][:2]:
                    lines.append(f"  LXX: {ref:<22} {desc}")
                if len(d['lxx']) > 2:
                    lines.append(f"       ... și încă {len(d['lxx'])-2} apariții LXX")

            if d['mas']:
                for ref, desc in d['mas'][:2]:
                    lines.append(f"  Mas: {ref:<22} {desc}")
                if len(d['mas']) > 2:
                    lines.append(f"       ... și încă {len(d['mas'])-2} apariții Masoretic")

            lines.append("")

    # Output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        for line in lines:
            print(line)


if __name__ == '__main__':
    main()
