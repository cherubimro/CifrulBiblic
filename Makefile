# Makefile for Expresia Fiul Omului
# Usage: make, make pdf, make html, make clean

TEX = carte
HTML_MAIN = Expresia_Fiul_Omului_Biblia_Ortodoxa
PDF_OUT = $(HTML_MAIN).pdf

.PHONY: all pdf html clean push

all: pdf html

# LaTeX → PDF (carte.pdf)
pdf: $(TEX).pdf

$(TEX).pdf: $(TEX).tex $(TEX).bib
	xelatex -interaction=nonstopmode $(TEX).tex
	biber $(TEX)
	xelatex -interaction=nonstopmode $(TEX).tex
	xelatex -interaction=nonstopmode $(TEX).tex

# HTML → PDF (WeasyPrint landscape cu numere de pagină)
html: $(PDF_OUT)

$(PDF_OUT): fara_buton.html
	weasyprint fara_buton.html /tmp/fiul_raw.pdf -s <(echo '@page { size: landscape; margin: 1cm 1cm 1.5cm 1cm; @bottom-center { content: counter(page) " / " counter(pages); font-size: 9pt; color: #888; font-family: Georgia, serif; } }')
	python3 fix_pdf_links.py /tmp/fiul_raw.pdf $(PDF_OUT)

clean:
	rm -f $(TEX).aux $(TEX).bbl $(TEX).bcf $(TEX).blg $(TEX).log $(TEX).out $(TEX).run.xml $(TEX).toc $(TEX).lof $(TEX).lot
	rm -f /tmp/fiul_raw.pdf

push:
	git add $(HTML_MAIN).html fara_buton.html $(PDF_OUT) $(TEX).tex $(TEX).pdf
	git push
