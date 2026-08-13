MAIN = main
TEX  = pdflatex -interaction=nonstopmode -halt-on-error

# Pin the timestamp pdfTeX embeds in /CreationDate and /ModDate. Without this the PDF is
# not byte-reproducible, so the sha256 recorded in FREEZE_HASHES.md could not be re-verified
# by anyone rebuilding from source. 1790294400 = 2026-09-25T00:00:00Z (the ICLR 2027 full-paper
# deadline; an arbitrary fixed instant, only its constancy matters). Reveals no author, host
# or working-hours signal.
export SOURCE_DATE_EPOCH = 1790294400
export FORCE_SOURCE_DATE = 1

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex iclr2027_conference.sty references.bib tables/study1_ledger.tex tables/claim_stats.tex tables/sta_pilot.tex
	$(TEX) $(MAIN).tex
	bibtex $(MAIN)
	$(TEX) $(MAIN).tex
	$(TEX) $(MAIN).tex

clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log $(MAIN).out $(MAIN).toc $(MAIN).fdb_latexmk $(MAIN).fls

# NOTE: `clean` deliberately keeps main.pdf. Use `distclean` before any build whose log you
# intend to measure -- otherwise make is a no-op and the log describes a build that never ran.
distclean: clean
	rm -f $(MAIN).pdf

.PHONY: all clean distclean
