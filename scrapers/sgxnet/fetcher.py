"""SGXNet fetch layer.

Status (2026-05-03): SGX's user-facing announcement portal is a JavaScript
SPA (``www.sgx.com/securities/company-announcements``); a plain GET returns
a ~6 KB shell with no listings. Live filings require a headless-browser
render (Playwright) — that integration is **deferred**.

Until then, this module supports two practical paths:

1. **Fixture mode** — ``fetch_from_fixture_dir(path)`` walks a directory of
   pre-saved filing HTML files. Useful for backfill of historical filings
   you've manually saved, and for the unit-test golden files.

2. **Live mode** — ``fetch_live()`` raises ``NotImplementedError`` with the
   exact next steps. Implementing it requires Playwright wired up against
   the SGX SPA. Out of scope for the current turn.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from scrapers.sgxnet.parser import Filing, parse_filing


@dataclass(frozen=True, slots=True)
class FetchedHTML:
    """One unit of fetched HTML plus its provenance."""

    source_url: str
    html: str


def fetch_from_fixture_dir(path: Path | str) -> Iterator[FetchedHTML]:
    """Yield each ``*.html`` file in ``path`` as a ``FetchedHTML`` whose
    ``source_url`` is the file's path.

    This is how you ingest historical filings you've already saved: drop
    the saved HTML into ``data/sgxnet/<ticker>/<filing>.html`` and run
    ``pipelines.weekly_filings --fixtures-dir data/sgxnet``.
    """
    p = Path(path)
    if not p.exists():
        return
    for f in sorted(p.rglob("*.html")):
        yield FetchedHTML(source_url=str(f), html=f.read_text(encoding="utf-8"))


def parse_fetched(items: Iterator[FetchedHTML]) -> Iterator[Filing]:
    """Compose: fetch (or replay) → parse. Errors are surfaced; caller
    decides whether to skip or fail."""
    for item in items:
        yield parse_filing(item.html, source_url=item.source_url)


def fetch_live() -> Iterator[FetchedHTML]:
    """Live fetch from SGX's company-announcements SPA — NOT YET WIRED.

    Implementing this requires:

    1. Add ``playwright`` to requirements.txt.
    2. Run ``playwright install chromium`` once on the runner.
    3. In this function:
       - launch chromium, navigate to
         ``https://www.sgx.com/securities/company-announcements``,
         set filters: announcement_category = Disclosure of Interest,
         period_start = 2025-07-21, period_end = today.
       - Iterate through paginated results, capture each filing's URL.
       - For each filing URL, navigate, extract ``page.content()``.
       - Yield ``FetchedHTML`` with that URL + html.
    4. Wrap network calls with ``ratelimit.gate()`` and ``ratelimit.transient``.
    5. Compute ``parser.page_fingerprint`` on the first filing and compare
       to the stored known-good hash; short-circuit + alert if mismatched.
    """
    raise NotImplementedError(
        "Live SGX fetch needs Playwright. See docstring for the wiring plan."
    )
