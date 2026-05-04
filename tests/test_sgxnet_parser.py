"""Tests for scrapers.sgxnet.parser using a fabricated SGX-shaped fixture."""

from __future__ import annotations

import pytest

from scrapers.sgxnet.parser import (
    ParseError,
    page_fingerprint,
    parse_filing,
)


def _golden_html() -> str:
    """A minimal but realistic SGX substantial-shareholder filing.

    Uses the same labels SGX's actual form does. The parser is keyword-anchored
    rather than DOM-path-anchored so this stays robust under small layout
    changes on the live site.
    """
    return """
    <html>
      <body>
        <h1>Notification of Substantial Shareholder</h1>
        <table class="form">
          <tr><td>Stock Code</td><td>E28</td></tr>
          <tr><td>Filing ID</td><td>SG-2025-001234</td></tr>
          <tr><td>Name of Substantial Shareholder</td>
              <td>BlackRock Investment Management (Singapore) Pte. Ltd.</td></tr>
          <tr><td>Date of Change</td><td>2025-09-12</td></tr>
          <tr><td>Date of Notice</td><td>2025-09-15</td></tr>
          <tr><td>Current Shareholding</td><td>5.42%</td></tr>
          <tr><td>Nature of Transaction</td><td>Acquisition</td></tr>
        </table>
      </body>
    </html>
    """


def test_parse_filing_extracts_required_fields() -> None:
    f = parse_filing(_golden_html(), source_url="https://sgx.example/filing/1234")
    assert f.ticker == "E28.SI"
    assert "BlackRock" in f.notifier_raw
    assert f.effective_date == "2025-09-12"
    assert f.filing_date == "2025-09-15"
    assert f.stake_pct == pytest.approx(5.42)
    assert f.direction == "acquired"
    assert f.source_url.startswith("https://sgx.example/")
    assert f.parser_version


def test_parse_filing_missing_required_fields_raises() -> None:
    bad = "<html><body>Notification</body></html>"
    with pytest.raises(ParseError, match="missing required fields"):
        parse_filing(bad, source_url="x")


def test_parse_filing_synthesises_filing_id_when_absent() -> None:
    html = _golden_html().replace(
        "<tr><td>Filing ID</td><td>SG-2025-001234</td></tr>", ""
    )
    f = parse_filing(html, source_url="https://sgx.example/no-id")
    assert f.filing_id.startswith("sgx_E28.SI_2025-09-15_")


def test_parse_filing_classifies_disposal() -> None:
    html = _golden_html().replace(
        "<tr><td>Nature of Transaction</td><td>Acquisition</td></tr>",
        "<tr><td>Nature of Transaction</td><td>Disposal of shares</td></tr>",
    )
    f = parse_filing(html, source_url="x")
    assert f.direction == "disposed"


def test_page_fingerprint_stable_across_text_changes() -> None:
    a = _golden_html()
    b = a.replace("BlackRock Investment Management", "BlackRock Asset Management")
    # Same skeleton, different text → same fingerprint
    assert page_fingerprint(a) == page_fingerprint(b)


def test_page_fingerprint_changes_on_structural_edit() -> None:
    a = _golden_html()
    b = a.replace("<table", "<div", 1).replace("</table>", "</div>", 1)
    # Tag changed → fingerprint shifts. This is what protects us when SGX
    # changes their layout.
    assert page_fingerprint(a) != page_fingerprint(b)
