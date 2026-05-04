"""Tests for scrapers.sgxnet.manager_aliases."""

from __future__ import annotations

import pytest

from scrapers.sgxnet.manager_aliases import (
    CANONICAL_IDS,
    all_canonical_ids,
    resolve_manager,
)
from src.constants import EQDP_MANAGERS


def test_canonical_ids_cover_every_manager() -> None:
    assert set(CANONICAL_IDS.keys()) == set(EQDP_MANAGERS)
    for mid in CANONICAL_IDS.values():
        assert mid.replace("_", "").isalnum()


def test_all_canonical_ids_returns_a_copy() -> None:
    a = all_canonical_ids()
    b = all_canonical_ids()
    a["NEW"] = "x"
    assert "NEW" not in b


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("BlackRock Investment Management (Singapore) Pte. Ltd.", "BlackRock"),
        ("BlackRock Inc.", "BlackRock"),
        ("BLACKROCK ASSET MANAGEMENT NORTH ASIA LIMITED", "BlackRock"),
        ("J.P. Morgan Asset Management (Singapore) Limited", "JPMorgan Asset Management"),
        ("JPMorgan Chase Bank, N.A.", "JPMorgan Asset Management"),
        ("Avanda Investment Management Pte. Ltd.", "Avanda Investment Management"),
        ("Fullerton Fund Management Company Ltd.", "Fullerton Fund Management"),
        ("Lion Global Investors Limited", "Lion Global Investors"),
        ("Eastspring Investments (Singapore) Limited", "Eastspring Investments"),
        ("Manulife Investment Management (Singapore) Pte Ltd", "Manulife Investment Management"),
        ("Nikko Asset Management Asia Limited", "Amova Asset Management"),  # pre-rebrand
        ("Amova Asset Management Asia Limited", "Amova Asset Management"),
        ("AR Capital Pte. Ltd.", "AR Capital"),
    ],
)
def test_resolve_manager_known_aliases(raw: str, expected: str) -> None:
    m = resolve_manager(raw)
    assert m is not None, f"failed to resolve: {raw}"
    assert m.canonical_name == expected
    assert m.manager_id == CANONICAL_IDS[expected]


@pytest.mark.parametrize(
    "raw",
    [
        "DBS Asset Management",  # not on the EQDP list
        "Citibank Singapore",
        "Some Person Name",
        "",
        "   ",
    ],
)
def test_resolve_manager_rejects_non_eqdp(raw: str) -> None:
    assert resolve_manager(raw) is None


def test_whitespace_and_case_normalised() -> None:
    a = resolve_manager("BLACKROCK   ASSET   MANAGEMENT")
    b = resolve_manager("blackrock asset management")
    assert a is not None and b is not None
    assert a.canonical_name == b.canonical_name == "BlackRock"
