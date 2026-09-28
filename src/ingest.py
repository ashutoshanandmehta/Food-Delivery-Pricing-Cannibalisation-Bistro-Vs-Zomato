"""Acquisition and PDF extraction.

How the committed panel was actually built
==========================================

**Finding first: Eternal's Annexure A tables do not have a text layer.** They
are vector graphics. `pdftotext -layout` returns the surrounding notes and
nothing from the tables, and `pdfplumber.extract_tables()` finds no rulings
because there are none to find. Any parser written against those pages returns
empty, or worse, returns the notes and looks like it worked.

So the panel was transcribed from rendered page images, not parsed. That is
slower and it is the honest option. The controls on transcription risk are:

1. **Overlap.** Each letter carries five trailing quarters, so consecutive
   letters overlap. Q1FY25 to Q4FY25 appear in both the Q4FY25 and Q1FY26
   letters, and Q1FY26 appears in both the Q1FY26 and Q1FY27 letters. Every
   overlapping figure matched exactly, which also confirms no restatements.
2. **An arithmetic identity.** Quick commerce discloses NOV, Orders and net AOV
   independently, so `NOV / Orders` must reproduce NAOV. It does, within 2%, in
   every quarter. Asserted in tests and in notebook 00.
3. **The validation gate** in `panel.validate`.

Acquisition
===========

The letters are not on Eternal's IR site under stable URLs. The site renders
them client side from an internal API. BSE is the reliable source:

    https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w
        ?pageno=1&strCat=-1&strPrevDate=YYYYMMDD&strScrip=543320
        &strSearch=P&strToDate=YYYYMMDD&strType=C&subcategory=-1

Send a browser User-Agent and a `Referer: https://www.bseindia.com/` header.
Filter for NEWSSUB containing "Shareholders Letter", then fetch each
ATTACHMENTNAME from

    https://www.bseindia.com/xml-data/corpfiling/AttachHis/<uuid>.pdf

Older filings live under `AttachHis`, recent ones under `AttachLive`. Try both.
Eternal is scrip 543320, Swiggy is 544285. Swiggy's tables do carry a text
layer, so `pdftotext -layout` works there.

Extraction strategy, in order of preference
===========================================

1. `pdftotext -layout file.pdf -` for a fast readable dump. Best for locating
   which page holds which table, and it is all that is needed for the Q&A prose
   where the Bistro kitchen counts and price points live.
2. `pdfplumber.extract_tables()` for ruled tables. Works on Swiggy, not on
   Eternal's Annexure A.
3. Rasterise and read visually when the table is vector art. `pdfimages` will
   not extract vector graphics: use
   `pdftoppm -png -r 150 -f N -l N file.pdf out` and read the image.

Run `pdffonts file.pdf` first. An empty font table means the PDF is raster only
and text extraction will return nothing at all.

Scraping hygiene: descriptive User-Agent, about one request per second, cache
every response to disk on first fetch, respect robots.txt, keep the raw file
alongside the parsed output so results stay reproducible.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd

from . import config

USER_AGENT = "eternal-research/0.1 (student placement project; contact: YOUR_EMAIL)"


def pdf_to_text(path: Path, layout: bool = True) -> str:
    """Dump a PDF to text via poppler. Layout mode preserves column
    positioning, which matters for the segment tables."""
    cmd = ["pdftotext"]
    if layout:
        cmd.append("-layout")
    cmd += [str(path), "-"]
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def has_text_layer(path: Path) -> bool:
    """False means the PDF is scanned or raster-only: text extraction will
    return nothing and you need to rasterise instead."""
    out = subprocess.run(
        ["pdffonts", str(path)], capture_output=True, text=True, check=True
    ).stdout
    return len(out.strip().splitlines()) > 2


def download_letters(scrip: str = "543320", dest: Path = None) -> list[Path]:
    """TODO: automate the BSE announcement query documented in the module
    docstring, filter for shareholders' letters, and fetch each attachment.

    Skip files already on disk. Do not re-download during development.
    """
    raise NotImplementedError("Implement against the BSE announcement API.")


def parse_letter(path: Path) -> dict:
    """Not implemented, and deliberately so.

    Eternal's Annexure A tables are vector graphics with no text layer, so
    there is nothing here for a parser to read. See the module docstring. The
    committed panel was transcribed from rendered page images and verified
    three ways.

    If a future letter switches to real tables, implement this and return a
    dict matching the panel schema including source_url. Every field you cannot
    find must be None, never zero or a guess. A None shows up honestly in the
    coverage report. A zero corrupts a growth rate.
    """
    raise NotImplementedError(
        "Eternal's Annexure A has no text layer. Render the page with pdftoppm "
        "and read it. See the module docstring."
    )


def annexure_pages(path: Path, dpi: int = 150, out_dir: Path = None) -> list[Path]:
    """Render every page of a letter to PNG so the tables can be read.

    This is the working method for Eternal's letters, not a fallback.
    """
    out_dir = out_dir or path.parent / f"{path.stem}_pages"
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), str(path), str(out_dir / path.stem)],
        check=True,
    )
    return sorted(out_dir.glob("*.png"))


def transcript_keyword_counts(
    transcripts_dir: Path = None,
    keywords: tuple[str, ...] = (
        "cannibal", "incremental", "bistro", "overlap",
        "10-minute", "frequency", "aov",
    ),
) -> pd.DataFrame:
    """Keyword frequency per transcript, for tracking how management framing
    shifts quarter to quarter.

    Confident denial giving way to hedging, or the topic vanishing from Q&A
    entirely, is a finding in its own right. Read the surrounding paragraphs
    before drawing conclusions: raw counts are a pointer, not evidence.
    """
    transcripts_dir = transcripts_dir or config.TRANSCRIPTS
    rows = []
    for p in sorted(transcripts_dir.glob("*.pdf")):
        text = pdf_to_text(p).lower()
        row = {"file": p.stem, "total_words": len(text.split())}
        row.update({k: text.count(k) for k in keywords})
        rows.append(row)
    return pd.DataFrame(rows)
