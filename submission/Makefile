MAIN = main
TEX  = pdflatex -interaction=nonstopmode -halt-on-error

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex iclr2027_conference.sty references.bib tables/study1_ledger.tex tables/claim_stats.tex tables/sta_pilot.tex
	$(TEX) $(MAIN).tex
	bibtex $(MAIN)
	$(TEX) $(MAIN).tex
	$(TEX) $(MAIN).tex

clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log $(MAIN).out $(MAIN).toc $(MAIN).fdb_latexmk $(MAIN).fls

distclean: clean
	rm -f $(MAIN).pdf

.PHONY: all clean distclean
