#!/usr/bin/env python3.11
"""
Convert fara_buton.html → carte.tex
All content preserved, styled like tutorial.tex, structure from TOC.
"""

from bs4 import BeautifulSoup, NavigableString, Tag
import re, html as htmlmod, hashlib, json

# ── TOC-defined chapters (by id) ──────────────────────────────────────────
CHAPTER_IDS = [
    'harisme','ce-este','de-ce-enoh','paradox','nazaret','steaua',
    'pestele','surse-patimi','foc-vesnic','crest-enoh','teologi',
    'dovada-matei','26-pasaje','monopol','cronologia','parinti',
    'geez','tabel-nt','vt','vt-enoh','concluzie',
    'semnatura','macdonald','halley','bloodmoon','halley3d'
]

# ── LaTeX preamble ────────────────────────────────────────────────────────
PREAMBLE = r"""\documentclass[12pt,a4paper,twoside,openany]{book}

% Fonts (XeLaTeX)
\usepackage{fontspec}
\setmainfont{Linux Libertine O}
\setsansfont{Linux Biolinum O}
\setmonofont[Scale=0.85]{DejaVu Sans Mono}
\newfontfamily\geezfont{Droid Sans Ethiopic}
\newfontfamily\hebrewfont{Linux Libertine O}
\newfontfamily\greekfont{Linux Libertine O}
\usepackage{polyglossia}
\setdefaultlanguage{romanian}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{microtype}

% Page layout
\usepackage[margin=2.5cm,inner=3cm,outer=2cm,headheight=24pt]{geometry}
\usepackage{fancyhdr}

% Graphics and colors
\usepackage{graphicx}
\usepackage[dvipsnames,svgnames,x11names]{xcolor}
\usepackage{tikz}
\usetikzlibrary{shadows}
% no landscape — all portrait

% Primary color palette (from tutorial.tex)
\definecolor{primaryblue}{HTML}{2563EB}
\definecolor{primarydark}{HTML}{1E40AF}
\definecolor{primarylight}{HTML}{DBEAFE}
\definecolor{secondarygreen}{HTML}{059669}
\definecolor{secondarylight}{HTML}{D1FAE5}
\definecolor{warningorange}{HTML}{D97706}
\definecolor{warninglight}{HTML}{FEF3C7}
\definecolor{accentpurple}{HTML}{7C3AED}
\definecolor{accentlight}{HTML}{EDE9FE}
\definecolor{codebg}{HTML}{F8FAFC}
\definecolor{codeframe}{HTML}{E2E8F0}
\definecolor{headingcolor}{HTML}{1E293B}
\definecolor{bodytext}{HTML}{334155}
\definecolor{linkblue}{HTML}{2563EB}
\definecolor{darkred}{HTML}{8B0000}
\definecolor{enochgreen}{HTML}{006600}
\definecolor{ivoryback}{HTML}{FFFFF0}
\definecolor{parallelstrong}{HTML}{D4EDDA}
\definecolor{parallelthematic}{HTML}{FFF3CD}
\definecolor{parallelbg}{HTML}{E2E3E5}
\definecolor{parallelloose}{HTML}{F8D7DA}

% Tables
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{ltablex}
\usepackage{multirow}
\usepackage{colortbl}
\usepackage{array}

% Code listings
\usepackage{listings}
\lstset{
    basicstyle=\small\ttfamily\color{bodytext},
    keywordstyle=\color{primaryblue}\bfseries,
    commentstyle=\color{gray}\itshape,
    stringstyle=\color{secondarygreen},
    numberstyle=\tiny\color{gray},
    numbers=left,
    numbersep=10pt,
    frame=single,
    framerule=0.8pt,
    rulecolor=\color{codeframe},
    backgroundcolor=\color{codebg},
    breaklines=true,
    breakatwhitespace=true,
    tabsize=4,
    showstringspaces=false,
    captionpos=b,
    xleftmargin=2em,
    framexleftmargin=2em,
    aboveskip=1.2em,
    belowskip=0.8em,
    literate={á}{{\'a}}1 {ă}{{\u{a}}}1 {â}{{\^a}}1 {î}{{\^i}}1
             {ș}{{\textcommabelow{s}}}1 {ț}{{\textcommabelow{t}}}1
             {Ă}{{\u{A}}}1 {Â}{{\^A}}1 {Î}{{\^I}}1
             {Ș}{{\textcommabelow{S}}}1 {Ț}{{\textcommabelow{T}}}1
             {é}{{\'e}}1 {ö}{{\"o}}1 {ü}{{\"u}}1,
}

% Boxes and callouts
\usepackage{tcolorbox}
\tcbuselibrary{skins,breakable,hooks}

\newtcolorbox{biblequote}{
    enhanced,
    colback=ivoryback,
    colframe=ivoryback,
    boxrule=0pt,
    borderline west={3pt}{0pt}{darkred},
    breakable,
    left=8pt, right=8pt, top=6pt, bottom=6pt,
    sharp corners,
}

\newtcolorbox{enochquote}{
    enhanced,
    colback=secondarylight,
    colframe=secondarylight,
    boxrule=0pt,
    borderline west={3pt}{0pt}{enochgreen},
    breakable,
    left=8pt, right=8pt, top=6pt, bottom=6pt,
    sharp corners,
}

\newtcolorbox{infobox}{
    enhanced,
    colback=codebg,
    colframe=codeframe,
    boxrule=0.5pt,
    breakable,
    left=8pt, right=8pt, top=6pt, bottom=6pt,
    rounded corners, arc=4pt,
}

\newtcolorbox{contextbox}{
    enhanced,
    colback=ivoryback,
    colframe=ivoryback,
    boxrule=0pt,
    borderline west={4pt}{0pt}{darkred},
    breakable,
    left=10pt, right=10pt, top=8pt, bottom=8pt,
    sharp corners,
}

% Hyperlinks
\usepackage[hyphens]{url}
\usepackage[bookmarks=true]{hyperref}
\hypersetup{
    colorlinks=true,
    linkcolor=primarydark,
    citecolor=accentpurple,
    urlcolor=linkblue,
    pdftitle={Fiul Omului: de la Enoh și Daniel la Iisus Hristos},
    pdfauthor={},
    pdfsubject={Studiu biblic},
    pdfpagemode=UseOutlines,
    bookmarksopen=true,
    bookmarksopenlevel=1,
    bookmarksdepth=3,
    pdfstartview=FitH,
    unicode=true,
}
\usepackage{bookmark}

% Bibliography
\usepackage[backend=biber,style=numeric,sorting=nyt,maxbibnames=99]{biblatex}
\addbibresource{carte.bib}

% Cross-references
\usepackage[section]{placeins}

% Table of contents styling
\usepackage{tocloft}
\renewcommand{\cftchapfont}{\bfseries\sffamily\color{primarydark}}
\renewcommand{\cftchappagefont}{\bfseries\color{primarydark}}
\renewcommand{\cftsecfont}{\sffamily\color{headingcolor}}
\renewcommand{\cftsecpagefont}{\color{headingcolor}}
\renewcommand{\cftsubsecfont}{\small\color{bodytext}}
\renewcommand{\cftsubsecpagefont}{\small\color{bodytext}}
\renewcommand{\cftchapleader}{\cftdotfill{\cftdotsep}}
\setlength{\cftbeforechapskip}{0.5em}

% Caption styling
\usepackage{caption}
\captionsetup{
    font={small,sf},
    labelfont={bf,color=primarydark},
    format=hang,
    margin=1cm
}

% Headers and footers
\pagestyle{fancy}
\fancyhf{}
\fancyhead[LE,RO]{\color{primarydark}\bfseries\thepage}
\fancyhead[LO]{\color{headingcolor}\small\nouppercase{\rightmark}}
\fancyhead[RE]{\color{headingcolor}\small\nouppercase{\leftmark}}
\renewcommand{\headrulewidth}{0.8pt}
\renewcommand{\headrule}{\hbox to\headwidth{\color{primaryblue}\leaders\hrule height \headrulewidth\hfill}}
\renewcommand{\footrulewidth}{0pt}

% Chapter formatting
\usepackage{titlesec}

\titleformat{\chapter}[display]
    {\Large\bfseries\sffamily\color{primarydark}}
    {\colorbox{primaryblue}{\parbox{1.5em}{\centering\color{white}\thechapter}}}
    {0.8em}
    {\LARGE}

\titleformat{\section}
    {\large\bfseries\sffamily\color{headingcolor}}
    {\color{primaryblue}\thesection}
    {0.6em}
    {}

\titleformat{\subsection}
    {\normalsize\bfseries\sffamily\color{headingcolor}}
    {\color{secondarygreen}\thesubsection}
    {0.5em}
    {}

\titlespacing*{\chapter}{0pt}{-20pt}{15pt}
\titlespacing*{\section}{0pt}{2.5ex plus 1ex minus .2ex}{1.5ex plus .2ex}
\titlespacing*{\subsection}{0pt}{1.5ex plus 1ex minus .2ex}{1ex plus .2ex}

% Paragraph spacing
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.6em}

% Allow line breaks in URLs and long words in tables
\makeatletter
\g@addto@macro\UrlBreaks{\UrlOrds}
\makeatother
\sloppy
\emergencystretch=3em
\setlength{\tabcolsep}{3pt}

% Allow more float space
\renewcommand{\topfraction}{0.9}
\renewcommand{\bottomfraction}{0.9}
\renewcommand{\textfraction}{0.1}

% Prevent overfull hboxes in tables
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}

"""

# ── Helper functions ──────────────────────────────────────────────────────

def escape_latex(text):
    """Escape special LaTeX characters in plain text."""
    if not text:
        return ''
    # Order matters: & first, then others
    text = text.replace('\\', '\\textbackslash{}')
    text = text.replace('&', r'\&')
    text = text.replace('%', r'\%')
    text = text.replace('$', r'\$')
    text = text.replace('#', r'\#')
    text = text.replace('_', r'\_')
    text = text.replace('{', r'\{')
    text = text.replace('}', r'\}')
    text = text.replace('~', r'\textasciitilde{}')
    text = text.replace('^', r'\textasciicircum{}')
    # Fix double-escaped backslash
    text = text.replace('\\textbackslash\\{\\}', '\\textbackslash{}')
    return text


def decode_entities(text):
    """Decode HTML entities to Unicode."""
    if not text:
        return ''
    return htmlmod.unescape(text)


def get_element_id(tag):
    """Get id from tag or its first child heading."""
    if tag.get('id'):
        return tag.get('id')
    if tag.name == 'div':
        h = tag.find(['h1','h2','h3','h4'])
        if h and h.get('id'):
            return h.get('id')
    return ''


def is_chapter_element(tag):
    """Check if this tag starts a chapter (based on TOC ids)."""
    eid = get_element_id(tag)
    return eid in CHAPTER_IDS


def get_row_color(tag):
    """Extract background color from style attribute."""
    style = tag.get('style', '')
    m = re.search(r'background\s*:\s*#([0-9A-Fa-f]{6})', style)
    if m:
        return m.group(1)
    m = re.search(r'background-color\s*:\s*#([0-9A-Fa-f]{6})', style)
    if m:
        return m.group(1)
    return None


def get_parallel_class(tag):
    """Get parallel classification from span class."""
    classes = tag.get('class', [])
    if isinstance(classes, str):
        classes = classes.split()
    for c in classes:
        if c == 'parallel-strong':
            return r'\textcolor{secondarygreen}{\textbf{Puternică}}'
        elif c == 'parallel-thematic':
            return r'\textcolor{warningorange}{Tematică}'
        elif c == 'parallel-background':
            return r'\textcolor{gray}{Context}'
        elif c == 'parallel-loose':
            return r'\textcolor{darkred}{Vagă}'
        elif c == 'parallel-none':
            return r'{\color{gray}Niciuna}'
    return None


def convert_inline(tag, inside_listing=False, in_table_cell=False):
    """Convert an inline element (or NavigableString) to LaTeX."""
    if isinstance(tag, NavigableString):
        text = str(tag)
        if inside_listing:
            return text
        return escape_latex(decode_entities(text))

    if not isinstance(tag, Tag):
        return ''

    name = tag.name

    # Skip script, style
    if name in ('script', 'style'):
        return ''

    # SVG images → include as vector PDF
    if name == 'svg':
        title_el = tag.find('text')
        title_text = title_el.get_text(strip=True)[:80] if title_el else ''
        if 'hexagonal' in title_text.lower() or 'steaua' in title_text.lower():
            return '\n\\begin{center}\n\\includegraphics[width=0.75\\textwidth]{img_svg_1.pdf}\n\\end{center}\n'
        elif 'vesica' in title_text.lower() or '153' in title_text:
            return '\n\\begin{center}\n\\includegraphics[width=0.75\\textwidth]{img_svg_2.pdf}\n\\end{center}\n'
        elif 'halley' in title_text.lower() or 'traiectoria' in title_text.lower():
            return '\n\\begin{center}\n\\includegraphics[width=\\textwidth]{img_svg_3.pdf}\n\\end{center}\n'
        return '\n\\begin{center}\n\\textit{[Diagramă SVG --- vezi versiunea HTML]}\n\\end{center}\n'

    # br — may have children in malformed HTML (BeautifulSoup quirk)
    if name == 'br':
        result = ' \\\\\n'
        for child in tag.children:
            result += convert_inline(child, inside_listing, in_table_cell)
        return result

    # hr
    if name == 'hr':
        return '\n\\bigskip\\noindent\\textcolor{darkred}{\\rule{\\textwidth}{2pt}}\\bigskip\n'

    # Images
    if name == 'img':
        alt = tag.get('alt', '')
        src = tag.get('src', '')
        if 'Tuenger' in alt or 'peștelui' in alt:
            return '\n\\begin{center}\n\\includegraphics[width=0.6\\textwidth]{img_1.jpeg}\n\\end{center}\n'
        elif 'Halley' in alt or 'halley' in alt.lower():
            return '\n\\begin{center}\n\\includegraphics[width=0.85\\textwidth]{img_2.png}\n\\end{center}\n'
        elif 'Luna de Sânge' in alt or 'blood' in alt.lower() or 'Eclips' in alt:
            return '\n\\begin{center}\n\\includegraphics[width=0.85\\textwidth]{img_3.png}\n\\end{center}\n'
        return ''

    # Get children content
    children_latex = ''
    for child in tag.children:
        children_latex += convert_inline(child, inside_listing, in_table_cell)

    # Formatting tags
    if name in ('strong', 'b'):
        style = tag.get('style', '')
        if 'color:#8B0000' in style or 'color: #8B0000' in style:
            return '\\textcolor{darkred}{\\textbf{' + children_latex + '}}'
        return '\\textbf{' + children_latex + '}'
    if name in ('em', 'i'):
        return '\\textit{' + children_latex + '}'
    if name == 'u':
        return '\\underline{' + children_latex + '}'
    if name == 'sup':
        return '\\textsuperscript{' + children_latex + '}'
    if name == 'sub':
        return '\\textsubscript{' + children_latex + '}'
    if name == 'code':
        return '\\texttt{' + children_latex + '}'
    if name == 'span':
        # Check for special classes
        classes = tag.get('class', [])
        if isinstance(classes, str):
            classes = classes.split()

        par = get_parallel_class(tag)
        if par is not None:
            return par

        if 'enoch' in classes:
            return '\\textcolor{enochgreen}{\\textbf{' + children_latex + '}}'
        if 'enoch-text' in classes:
            return '\\textcolor{enochgreen}{' + children_latex + '}'
        if 'geez' in classes:
            return '{\\small ' + children_latex + '}'
        if 'ref' in classes:
            return '\\textbf{' + children_latex + '}'
        if 'verse-ro' in classes:
            return '\\textit{' + children_latex + '}'

        # Check inline style for color
        style = tag.get('style', '')
        if 'color:#8B0000' in style or 'color: #8B0000' in style:
            return '\\textcolor{darkred}{' + children_latex + '}'
        if 'color:#006600' in style or 'color: #006600' in style:
            return '\\textcolor{enochgreen}{' + children_latex + '}'
        if 'color:#666' in style:
            return '{\\small\\color{gray}' + children_latex + '}'
        if 'color:#d4a84b' in style:
            return '\\textcolor{warningorange}{' + children_latex + '}'

        return children_latex

    if name == 'a':
        href = tag.get('href', '')
        if href:
            # Escape special chars in URL
            href = href.replace('%', '\\%').replace('#', '\\#').replace('&', '\\&')
            return '\\href{' + href + '}{' + children_latex + '}'
        return children_latex

    # Block-level elements encountered in inline context → delegate to convert_block
    # Note: blockquote is excluded — it's handled by convert_blockquote which calls convert_inline
    if name in ('pre', 'hr', 'ul', 'ol') and not inside_listing:
        return '\n' + convert_block(tag) + '\n'
    # Tables: only delegate if NOT inside another table cell (nested tabular breaks LaTeX)
    if name == 'table' and not inside_listing and not in_table_cell:
        return '\n' + convert_block(tag) + '\n'

    # div with special classes
    if name == 'div':
        classes = tag.get('class', [])
        if isinstance(classes, str):
            classes = classes.split()
        style = tag.get('style', '')
        # 3D model placeholder → use 3dNucleu.jpg
        if 'background:#050510' in style or 'background: #050510' in style:
            return '\n\\begin{center}\n\\includegraphics[width=0.8\\textwidth]{3dNucleu.jpg}\n\\end{center}\n'
        # Context box (ivory background + red left border) — like epilog
        if ('border-left:4px solid #8B0000' in style or 'border-left: 4px solid #8B0000' in style or
            'border-left:3px solid #8B0000' in style) and 'background:#fffff0' in style:
            return '\n\\begin{contextbox}\n' + children_latex + '\n\\end{contextbox}\n'
        # Info box (gray background)
        if 'background:#f8f9fa' in style or 'background: #f8f9fa' in style:
            return '\n\\begin{infobox}\n' + children_latex + '\n\\end{infobox}\n'
        if 'background:#f0f8f0' in style or 'background: #f0f8f0' in style:
            return '\n\\begin{infobox}\n' + children_latex + '\n\\end{infobox}\n'
        if 'verse-ro' in classes:
            return '\\textit{' + children_latex + '}'
        if 'enoch-text' in classes:
            return '\\textcolor{enochgreen}{' + children_latex + '}'
        # Check if div contains block elements
        block_tags = ['table','blockquote','ul','ol','pre','h1','h2','h3','h4']
        if tag.find(block_tags, recursive=True):
            result = ''
            for child in tag.children:
                if isinstance(child, Tag) and (child.name in block_tags or child.find(block_tags, recursive=True)):
                    result += '\n' + convert_block(child) + '\n'
                else:
                    result += convert_inline(child)
            return result
        # Generic div - just return content
        return children_latex

    # Default: return children
    return children_latex


def convert_table(table_tag):
    """Convert an HTML table to LaTeX."""
    rows = table_tag.find_all('tr')
    if not rows:
        return ''

    # Determine number of columns from header row (most reliable)
    # Using max across all rows can be wrong when cells contain nested tables
    thead = table_tag.find('thead')
    header_row = None
    if thead:
        header_row = thead.find('tr')
    else:
        first_row = rows[0] if rows else None
        if first_row and first_row.find('th'):
            header_row = first_row

    if header_row:
        max_cols = len(header_row.find_all(['th', 'td'], recursive=False))
    else:
        # Fallback: use median column count (robust against nested tables)
        col_counts = [len(r.find_all(['th', 'td'], recursive=False)) for r in rows]
        if col_counts:
            col_counts.sort()
            max_cols = col_counts[len(col_counts) // 2]  # median
        else:
            max_cols = 0

    if max_cols == 0:
        return ''

    # Check if table has thead
    thead = table_tag.find('thead')

    # ── Estimate content width per column ──────────────────────────────
    col_max_chars = [0] * max_cols
    for row in rows:
        cells = row.find_all(['th', 'td'], recursive=False)
        for j, cell in enumerate(cells):
            if j < max_cols:
                text = cell.get_text(strip=True)
                col_max_chars[j] = max(col_max_chars[j], len(text))
    total_chars = sum(col_max_chars)

    # ── All tables portrait, multi-page if needed ────────────────────
    PORTRAIT_WIDTH = 15.5   # cm (text width with margins)

    use_landscape = False
    # Estimate if table fits on one page: ~45 lines at \small, ~55 at \footnotesize
    # Use longtable for any table that might not fit
    estimated_height = sum(
        max(len(cell.get_text(strip=True)) // 40 + 1, 1)
        for row in rows
        for cell in row.find_all(['th','td'])[:1]  # estimate by first cell
    )
    use_longtable = len(rows) > 8 or estimated_height > 40 or max_cols >= 6

    # Font size: readable, never tiny
    if max_cols >= 8:
        font_size = '\\scriptsize'  # 9 columns need smaller font to fit portrait
        use_longtable = True
    elif max_cols >= 5:
        font_size = '\\footnotesize'
    elif total_chars > 120:
        font_size = '\\small'
    else:
        font_size = '\\small'

    avail_width = PORTRAIT_WIDTH

    # ── Build column spec with proportional paragraph widths ──────────
    if max_cols == 9:
        # Big NT table: 9 cols in portrait, footnotesize, longtable multi-page
        # Available: 15.5cm - 9*0.21cm = 13.6cm
        # #(0.3) Ref(1.1) Cat(1.0) TextBiblie(3.0) ParEnoh(1.1) Tip(1.2) TextEnoh(2.4) Geez(1.1) Note(2.0) = 13.2
        col_spec = (r'C{0.3cm}'
                    r'>{\raggedright\arraybackslash}p{1.1cm}'
                    r'>{\raggedright\arraybackslash}p{1.0cm}'
                    r'>{\raggedright\arraybackslash}p{3.0cm}'
                    r'>{\raggedright\arraybackslash}p{1.1cm}'
                    r'>{\raggedright\arraybackslash}p{1.2cm}'
                    r'>{\raggedright\arraybackslash}p{2.4cm}'
                    r'>{\raggedright\arraybackslash}p{1.1cm}'
                    r'>{\raggedright\arraybackslash}p{2.0cm}')
    elif max_cols == 1:
        col_spec = f'L{{{avail_width}cm}}'
    else:
        # Proportional widths based on max content length
        # Target: total column widths = avail_width (columns fill the page)
        total_w = sum(max(c, 3) for c in col_max_chars)  # min 3 chars per col
        padding = 0.21 * max_cols  # tabcolsep=3pt per side = 6pt = 0.21cm per col
        usable = avail_width - padding
        col_widths = []
        for j in range(max_cols):
            char_w = max(col_max_chars[j], 3)
            w = (char_w / total_w) * usable
            w = max(w, 0.8)  # minimum 0.8cm
            col_widths.append(w)
        # Normalize: ensure sum == usable width exactly
        total_generated = sum(col_widths)
        if total_generated != usable:
            scale = usable / total_generated
            col_widths = [w * scale for w in col_widths]
        col_specs = [f'L{{{round(w, 1)}cm}}' for w in col_widths]
        col_spec = ''.join(col_specs)

    # ── Generate LaTeX ────────────────────────────────────────────────
    lines = []

    if use_longtable:
        lines.append(f'{font_size}')
        lines.append(f'\\begin{{longtable}}{{{col_spec}}}')
        lines.append('\\toprule')
    else:
        lines.append(f'\\begin{{center}}\n{font_size}')
        lines.append(f'\\begin{{tabular}}{{{col_spec}}}')
        lines.append('\\toprule')

    first_row = True
    for row in rows:
        cells = row.find_all(['th', 'td'], recursive=False)
        is_header = cells and cells[0].name == 'th'

        # Row color
        row_color = get_row_color(row)
        row_bold = 'font-weight:bold' in row.get('style', '')

        cell_texts = []
        for cell in cells:
            ct = convert_inline(cell, in_table_cell=True).strip()
            # In table cells, \\ means end-of-row; use \newline for line breaks
            ct = ct.replace('\\\\', '\\newline ')
            # Replace blank lines (paragraph breaks) with \newline - they break tables
            ct = re.sub(r'\n\s*\n', ' \\\\newline ', ct)
            # Replace remaining newlines with spaces
            ct = ct.replace('\n', ' ')
            # Remove excessive newlines
            ct = re.sub(r'(\\newline\s*){3,}', '\\newline ', ct)
            # Remove trailing \newline (causes issues before &)
            ct = re.sub(r'\s*\\newline\s*$', '', ct)
            if is_header:
                ct = '\\textbf{' + ct + '}'
            elif row_bold:
                ct = '\\textbf{' + ct + '}'
            cell_texts.append(ct)

        # Pad to max_cols
        while len(cell_texts) < max_cols:
            cell_texts.append('')

        row_line = ' & '.join(cell_texts) + ' \\\\'

        if row_color:
            lines.append(f'\\rowcolor[HTML]{{{row_color}}}')
        elif is_header:
            lines.append('\\rowcolor{primarylight}')

        lines.append(row_line)

        if is_header or (first_row and thead is None and is_header):
            lines.append('\\midrule')
            if use_longtable:
                lines.append('\\endhead')

        first_row = False

    lines.append('\\bottomrule')
    if use_longtable:
        lines.append('\\end{longtable}')
        lines.append('\\normalsize')
    else:
        lines.append('\\end{tabular}')
        lines.append(f'\\end{{center}}\n\\normalsize')

    # all portrait, no landscape

    return '\n'.join(lines) + '\n'


def convert_list(list_tag):
    """Convert ul/ol to LaTeX."""
    block_tags = ['table','blockquote','ul','ol','pre','h1','h2','h3','h4']
    env = 'enumerate' if list_tag.name == 'ol' else 'itemize'
    lines = [f'\\begin{{{env}}}']
    for li in list_tag.find_all('li', recursive=False):
        # Check if li contains block elements (like tables)
        if li.find(block_tags, recursive=True):
            item_lines = '\\item '
            for child in li.children:
                if isinstance(child, Tag) and (child.name in block_tags or child.find(block_tags, recursive=True)):
                    item_lines += '\n' + convert_block(child)
                else:
                    item_lines += convert_inline(child)
            lines.append(item_lines.strip())
        else:
            content = convert_inline(li).strip()
            lines.append(f'  \\item {content}')
    lines.append(f'\\end{{{env}}}')
    return '\n'.join(lines) + '\n'


def convert_blockquote(bq_tag):
    """Convert blockquote to biblequote tcolorbox."""
    # Check if it's an Enoch quote (green border)
    style = bq_tag.get('style', '')
    env = 'enochquote' if '#006600' in style else 'biblequote'
    content = convert_inline(bq_tag).strip()
    return f'\n\\begin{{{env}}}\n{content}\n\\end{{{env}}}\n'


def convert_pre(pre_tag):
    """Convert pre/code block to lstlisting."""
    code = pre_tag.get_text()
    # Decode entities
    code = decode_entities(code)
    return f'\n\\begin{{lstlisting}}[language=Python,basicstyle=\\tiny\\ttfamily]\n{code}\n\\end{{lstlisting}}\n'


def is_info_div(tag):
    """Check if a div should be rendered as an info box."""
    style = tag.get('style', '')
    if 'background:#f8f9fa' in style or 'background: #f8f9fa' in style:
        return True
    if 'background:#f0f8f0' in style or 'background: #f0f8f0' in style:
        return True
    return False


def is_context_div(tag):
    """Check if a div should be rendered as a context box (ivory + border)."""
    style = tag.get('style', '')
    if 'border-left:4px solid #8B0000' in style or 'border-left: 4px solid #8B0000' in style:
        return True
    if 'border-left:3px solid #8B0000' in style:
        return True
    return False


def convert_block(tag, depth=0):
    """Convert a block-level element to LaTeX."""
    if isinstance(tag, NavigableString):
        text = str(tag).strip()
        if text:
            return escape_latex(decode_entities(text)) + '\n'
        return ''

    if not isinstance(tag, Tag):
        return ''

    name = tag.name

    if name in ('script', 'style', 'head', 'meta', 'link'):
        return ''

    if name == 'svg':
        return convert_inline(tag)

    # Headings (mapped by structure analysis)
    if name in ('h1', 'h2', 'h3', 'h4'):
        eid = tag.get('id', '')
        title = convert_inline(tag).strip()
        # Remove \textbf from chapter/section titles (titlesec handles it)
        title_clean = re.sub(r'\\textbf\{([^}]*)\}', r'\1', title)
        # Remove \href from titles (causes issues in TOC)
        title_clean = re.sub(r'\\href\{[^}]*\}\{([^}]*)\}', r'\1', title_clean)

        # Check if this heading is a chapter (by own id OR parent div id)
        is_chap = eid in CHAPTER_IDS
        if not is_chap:
            # Check if parent div has a chapter id and this is its first heading
            parent = tag.parent
            if parent and parent.name == 'div':
                parent_id = parent.get('id', '')
                if parent_id in CHAPTER_IDS:
                    first_h = parent.find(['h1','h2','h3','h4'])
                    if first_h is tag:
                        is_chap = True
                        eid = parent_id

        if is_chap:
            label = f'\\label{{{eid}}}' if eid else ''
            return f'\n\\chapter{{{title_clean}}}{label}\n'
        elif name in ('h1',):
            return ''  # h1 is the main title, handled in title page
        elif name == 'h2':
            label = f'\\label{{{eid}}}' if eid else ''
            return f'\n\\section{{{title_clean}}}{label}\n'
        elif name == 'h3':
            label = f'\\label{{{eid}}}' if eid else ''
            return f'\n\\section{{{title_clean}}}{label}\n'
        elif name == 'h4':
            label = f'\\label{{{eid}}}' if eid else ''
            return f'\n\\subsection{{{title_clean}}}{label}\n'
        return ''

    if name == 'p':
        # Check if this <p> has info-box styling (background color)
        p_style = tag.get('style', '')
        if 'background:#f8f9fa' in p_style or 'background: #f8f9fa' in p_style:
            content = convert_inline(tag).strip()
            return f'\n\\begin{{infobox}}\n{content}\n\\end{{infobox}}\n'
        if ('border-left' in p_style and '#8B0000' in p_style) or 'background:#fffff0' in p_style:
            content = convert_inline(tag).strip()
            return f'\n\\begin{{contextbox}}\n{content}\n\\end{{contextbox}}\n'

        # Check if this <p> contains block-level elements (invalid HTML but common)
        # Browser moves h2/h3/h4/table/blockquote/ul/ol/pre/div out of <p>
        # Use recursive=True since block elements may be nested several levels deep
        block_tags = ['h1','h2','h3','h4','table','blockquote','ul','ol','pre','hr']
        block_children = tag.find_all(block_tags, recursive=True)
        if block_children:
            # Process each direct child, recursing into sub-elements
            result = ''
            for child in tag.children:
                if isinstance(child, Tag):
                    if child.name in block_tags:
                        result += convert_block(child, depth+1)
                    elif child.find(block_tags, recursive=True):
                        # This child contains nested block elements
                        result += convert_block(child, depth+1)
                    else:
                        text = convert_inline(child).strip()
                        if text:
                            result += text + '\n\n'
                else:
                    text = convert_inline(child).strip()
                    if text:
                        result += text + '\n\n'
            return result
        content = convert_inline(tag).strip()
        if not content:
            return ''
        return content + '\n\n'

    if name == 'blockquote':
        return convert_blockquote(tag)

    if name in ('ul', 'ol'):
        return convert_list(tag)

    if name == 'table':
        return convert_table(tag)

    if name == 'pre':
        return convert_pre(tag)

    if name == 'hr':
        return '\n\\bigskip\\noindent\\textcolor{darkred}{\\rule{\\textwidth}{2pt}}\\bigskip\n'

    if name == 'br':
        return ' \\\\\n'

    if name == 'div':
        eid = get_element_id(tag)
        classes = tag.get('class', [])
        if isinstance(classes, str):
            classes = classes.split()

        # Skip TOC div (id from the h2 "Cuprins" parent div)
        # The TOC is inside a div that contains h2 "Cuprins" and an ol
        h2_child = tag.find('h2', recursive=False)
        if h2_child and 'Cuprins' in h2_child.get_text():
            return ''  # Skip HTML TOC, LaTeX generates its own

        # Legend bar
        if 'legend-bar' in classes:
            content = convert_inline(tag).strip()
            return f'\n\\begin{{infobox}}\n{content}\n\\end{{infobox}}\n'

        # Stats div
        if 'stats' in classes:
            result = ''
            for child in tag.children:
                result += convert_block(child, depth+1)
            return result

        # Footer
        if 'footer' in classes:
            content = convert_inline(tag).strip()
            return f'\n\\bigskip\n\\begin{{center}}\n\\textcolor{{gray}}{{{content}}}\n\\end{{center}}\n'

        # Sky map container - process children (includes SVG)
        if tag.get('id') == 'skyMapContainer':
            result = ''
            for child in tag.children:
                result += convert_block(child, depth+1)
            return result

        # 3D model → use 3dNucleu.jpg
        style = tag.get('style', '')
        if 'background:#050510' in style or 'background: #050510' in style:
            return '\n\\begin{center}\n\\includegraphics[width=0.8\\textwidth]{3dNucleu.jpg}\n\\end{center}\n'

        # Context box (ivory + red left border)
        if is_context_div(tag):
            result = ''
            for child in tag.children:
                result += convert_block(child, depth+1)
            return f'\n\\begin{{contextbox}}\n{result}\\end{{contextbox}}\n'

        # Info box (gray background)
        if is_info_div(tag):
            result = ''
            for child in tag.children:
                result += convert_block(child, depth+1)
            return f'\n\\begin{{infobox}}\n{result}\\end{{infobox}}\n'

        # Chapter div (contains a chapter heading)
        if eid in CHAPTER_IDS:
            result = ''
            for child in tag.children:
                result += convert_block(child, depth+1)
            return result

        # Generic div - process children
        result = ''
        for child in tag.children:
            result += convert_block(child, depth+1)
        return result

    # Fallback: process children
    result = ''
    for child in tag.children:
        result += convert_block(child, depth+1)
    return result


def make_title_page():
    """Generate the title page in tikz style."""
    return r"""
\begin{titlepage}
\begin{tikzpicture}[remember picture,overlay]
    % Top colored band - taller to fit two-line title
    \fill[primaryblue] (current page.north west) rectangle ([yshift=-8cm]current page.north east);
    % Decorative diagonal element
    \fill[primarydark] ([yshift=-7.5cm]current page.north west) -- ([yshift=-8.5cm]current page.north west) -- ([yshift=-8cm]current page.north east) -- ([yshift=-7.5cm]current page.north east) -- cycle;
    % Bottom accent bar
    \fill[secondarygreen] (current page.south west) rectangle ([yshift=0.8cm]current page.south east);
\end{tikzpicture}

\centering
\vspace*{1.5cm}

% Title on blue background
{\color{white}\fontsize{28}{34}\selectfont\bfseries\sffamily „Fiul Omului"\par}
\vspace{0.4cm}
{\color{white}\fontsize{24}{30}\selectfont\bfseries\sffamily de la Enoh și Daniel la Iisus Hristos\par}

\vspace{2.5cm}

% Subtitle
{\color{bodytext}\large\itshape Biblia, Parabolele lui Enoh și tradiția biblică a titlului mesianic\par}

\vspace{0.6cm}

\begin{center}
\includegraphics[width=0.95\textwidth]{coperta2.jpg}

\vspace{0.2cm}
{\scriptsize\color{gray}\textit{Giotto di Bondone, Judecata de Apoi (c.~1306), Capela Scrovegni, Padova. Domeniu public.}}
\end{center}

\vspace{0.3cm}

% Badge
\begin{tikzpicture}
    \node[fill=primarylight, rounded corners=4pt, inner sep=8pt, font=\normalsize\sffamily] {
        \color{primarydark}\textbf{Descifrare și Demonstrație de Teologie Narativă}
    };
\end{tikzpicture}

\vfill
\vspace{1cm}
\end{titlepage}

% Abstract on page 2
\thispagestyle{empty}
\vspace*{\fill}
\begin{center}
\begin{tikzpicture}
    \node[fill=codebg, rounded corners=6pt, inner sep=15pt, drop shadow=black!10] {
        \begin{minipage}{12cm}
            \small\color{bodytext}
            {\centering\Large\bfseries Abstract\par}
            \vspace{0.6em}
            Lucrarea de față demonstrează că Evangheliile sunt \textit{teologie narativă}
            și că autorii lor au folosit expresii, concepte și referințe enoice --- din Cartea lui Enoh,
            eliminată ulterior din canonul bisericesc. Se demonstrează totodată că autorii s-au folosit de
            \textit{gematrie} și de \textit{isopsefie} pentru a lega între ele cuvinte, pasaje și imagini,
            asemenea unui zugrav care țese un goblen --- există stratul imediat vizibil,
            dar și cel din spatele goblenului unde intrările și ieșirile sunt legate matematic.\par
            \vspace{0.8em}
            {\footnotesize\color{gray}\textbf{Cuvinte cheie:}
            Fiul Omului $\cdot$ teologie narativă $\cdot$ 1~Enoh $\cdot$ Parabolele lui Enoh $\cdot$
            gematrie $\cdot$ isopsefie $\cdot$ Daniel~7:13 $\cdot$
            Noul Testament $\cdot$ Biblia Ortodoxă $\cdot$ Qumran $\cdot$
            Cometa Halley $\cdot$ Luna Roșie $\cdot$ cutremur\par
            \vspace{0.4em}
            \href{https://creativecommons.org/publicdomain/zero/1.0/deed.ro}{CC0 1.0 Universal --- Dedicare Domeniului Public}\par}
        \end{minipage}
    };
\end{tikzpicture}
\end{center}

\vspace*{\fill}

\begin{center}
\begin{minipage}{0.8\textwidth}
\centering
\rule{\textwidth}{0.4pt}

\vspace{1em}
{\Large\sffamily\bfseries\color{primarydark} Licență}
\vspace{0.8em}

Persoana care a asociat o operă cu acest act

\vspace{0.5em}
{\LARGE\sffamily\bfseries CC0 1.0 Universal}
\vspace{0.3em}

{\large\sffamily Dedicare Domeniului Public}
\vspace{0.6em}

a \textbf{dedicat opera domeniului public} prin renunțarea pe plan mondial la toate drepturile sale asupra operei conform legii dreptului de autor, incluzând toate drepturile conexe și vecine, în măsura permisă de lege.

\vspace{0.4em}
Puteți \textbf{copia, modifica, distribui și efectua opera}, chiar și în scopuri comerciale, fără a mai cere permisiunea.

\vspace{0.4em}
{\small\color{gray}
Drepturile de brevet și marcă nu sunt afectate de CC0, iar drepturile de publicitate și viață privată rămân în vigoare. Nu se oferă garanții asupra operei.
}

\vspace{0.8em}
\href{https://creativecommons.org/publicdomain/zero/1.0/deed.ro}{\texttt{creativecommons.org/publicdomain/zero/1.0/deed.ro}}

\vspace{1em}
\rule{\textwidth}{0.4pt}
\end{minipage}
\end{center}
\newpage
"""


# ── Main conversion ──────────────────────────────────────────────────────

def main():
    print("Reading fara_buton.html...")
    with open('fara_buton.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    body = soup.find('body')

    print("Converting to LaTeX...")

    # Build the document
    doc = PREAMBLE
    doc += '\\begin{document}\n\n'
    doc += make_title_page()
    doc += '\n\\tableofcontents\n\\newpage\n\n'

    # Process all children of body
    for child in body.children:
        # Skip the h1 (title), subtitle paragraphs, and the TOC div
        if isinstance(child, Tag):
            if child.name == 'h1':
                continue  # Title is on title page
            if child.name == 'p':
                classes = child.get('class', [])
                if isinstance(classes, str):
                    classes = classes.split()
                if 'subtitle' in classes:
                    continue  # Subtitles are on title page
            if child.name == 'div':
                h2_in = child.find('h2', recursive=False)
                if h2_in and 'Cuprins' in h2_in.get_text():
                    continue  # Skip HTML TOC
        doc += convert_block(child)

    # Bibliography (appears in table of contents)
    doc += '\n\\nocite{*}\n'
    doc += '\\printbibliography[heading=bibintoc,title={Bibliografie}]\n'

    # License is on the abstract page (page 2), no separate page needed

    doc += '\n\\end{document}\n'

    # Post-processing fixes

    # Wrap Ge'ez (Ethiopic) text runs in \geezfont
    # Ethiopic Unicode range: U+1200-U+137F, U+1380-U+139F, U+2D80-U+2DDF
    def wrap_geez(m):
        # Add \allowbreak after Ethiopic word separator ፡ for line breaking
        text = m.group(0).replace('፡', '፡\\allowbreak ')
        return '{\\geezfont ' + text + '}'
    doc = re.sub(r'[\u1200-\u139F\u2D80-\u2DDF][\u1200-\u139F\u2D80-\u2DDF\s፡:]+', wrap_geez, doc)

    # Fix double backslashes in problematic positions
    doc = re.sub(r'\\\\\s*\\\\(\s*\\\\)+', r'\\\\', doc)
    # Fix empty textbf
    doc = re.sub(r'\\textbf\{\s*\}', '', doc)
    # Fix empty textit
    doc = re.sub(r'\\textit\{\s*\}', '', doc)
    # Fix \textit and \textbf spanning paragraph breaks (LaTeX error)
    # Split them: \textit{A\n\nB} → \textit{A}\n\n\textit{B}
    for cmd in ['textit', 'textbf']:
        def fix_para_in_cmd(m):
            content = m.group(1)
            parts = re.split(r'\n\s*\n', content)
            if len(parts) <= 1:
                return m.group(0)
            return ('\n\n').join(f'\\{cmd}{{{p.strip()}}}' for p in parts if p.strip())
        doc = re.sub(r'\\' + cmd + r'\{((?:[^{}]|\{[^{}]*\})*)\}', fix_para_in_cmd, doc)

    # Fix consecutive blank lines (max 2)
    doc = re.sub(r'\n{4,}', '\n\n\n', doc)

    print(f"Writing carte.tex ({len(doc)} chars)...")
    with open('carte.tex', 'w', encoding='utf-8') as f:
        f.write(doc)

    # ── Verification ──────────────────────────────────────────────────
    print("\n=== Verification ===")

    # Count structural elements in generated LaTeX
    chapters = len(re.findall(r'\\chapter\{', doc))
    sections = len(re.findall(r'\\section\{', doc))
    subsections = len(re.findall(r'\\subsection\{', doc))
    tables_lt = len(re.findall(r'\\begin\{longtable\}', doc))
    tables_tab = len(re.findall(r'\\begin\{tabular\}', doc))
    bq = len(re.findall(r'\\begin\{biblequote\}', doc))
    eq = len(re.findall(r'\\begin\{enochquote\}', doc))
    itemize = len(re.findall(r'\\begin\{itemize\}', doc))
    enumerate_ = len(re.findall(r'\\begin\{enumerate\}', doc))
    listings = len(re.findall(r'\\begin\{lstlisting\}', doc))

    print(f"Chapters:     {chapters}  (expected: 26)")
    print(f"Sections:     {sections}")
    print(f"Subsections:  {subsections}")
    print(f"Tables:       {tables_lt + tables_tab}  (longtable: {tables_lt}, tabular: {tables_tab})  (expected: 53)")
    print(f"Blockquotes:  {bq + eq}  (bible: {bq}, enoch: {eq})  (expected: 25)")
    print(f"Lists:        {itemize + enumerate_}  (itemize: {itemize}, enum: {enumerate_})  (expected: 30)")
    print(f"Code blocks:  {listings}  (expected: 3)")

    # Extract text from LaTeX for word count comparison
    tex_text = doc
    # Remove LaTeX commands roughly
    tex_text = re.sub(r'\\begin\{lstlisting\}.*?\\end\{lstlisting\}', ' CODE ', tex_text, flags=re.DOTALL)
    tex_text = re.sub(r'\\[a-zA-Z]+\{', ' ', tex_text)
    tex_text = re.sub(r'\\[a-zA-Z]+\[.*?\]', ' ', tex_text)
    tex_text = re.sub(r'\\[a-zA-Z]+', ' ', tex_text)
    tex_text = re.sub(r'[{}\\]', ' ', tex_text)
    tex_text = re.sub(r'\s+', ' ', tex_text).strip()
    tex_words = len(tex_text.split())
    print(f"Word count:   ~{tex_words}  (HTML had: 81701)")

    print("\nDone! Run: pdflatex carte.tex")


if __name__ == '__main__':
    main()
