"""Three-tier beneficiary universe — T1 / T2 / T3 / control.

Day-1 deliverable per docs/PLAN.md. Pure data + accessor functions; no DB
or network. The SGXNet scraper (Day 6) will populate T1 from real filings;
the eligibility filter (Day 2+) will expand T2 from full SGX listings.

Identifier convention: yfinance form, e.g. ``E28.SI``. The local SGX code
is everything before ``.SI``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from src.constants import SGX_SUFFIX, TIER_CONTROL, TIER_T1, TIER_T2, TIER_T3


@dataclass(frozen=True, slots=True)
class Ticker:
    """One row of the universe.

    Tiers represent inclusion in each tier; a stock can sit in several. The
    headline tier (highest by precedence T1 > T3 > T2 > control) is computed
    by ``headline_tier`` for display.
    """

    symbol: str
    name: str
    sector: str
    sources: tuple[str, ...] = ()
    in_t1: bool = False
    in_t2: bool = False
    in_t3: bool = False
    in_control: bool = False

    def __post_init__(self) -> None:
        if not self.symbol.endswith(SGX_SUFFIX):
            raise ValueError(
                f"Ticker symbol must end with {SGX_SUFFIX!r}: {self.symbol!r}"
            )

    @property
    def headline_tier(self) -> str:
        if self.in_t1:
            return TIER_T1
        if self.in_t3:
            return TIER_T3
        if self.in_t2:
            return TIER_T2
        if self.in_control:
            return TIER_CONTROL
        raise ValueError(f"Ticker {self.symbol} has no tier flags set")


# ---------------------------------------------------------------------------
# T3 — Named beneficiaries (broker lists)
# Source: docs/TICKERS.md. Sources column is the union of broker notes.
# ---------------------------------------------------------------------------

_T3_SEED: Final[tuple[Ticker, ...]] = (
    # Industrial / tech small-mid caps
    Ticker("E28.SI", "Frencken Group", "Industrial",
           sources=("RHB-30", "Edge-69"), in_t3=True),
    Ticker("558.SI", "UMS Integration", "Industrial",
           sources=("RHB-30", "Edge-69", "Maybank-18"), in_t3=True),
    Ticker("AWX.SI", "AEM Holdings", "Industrial",
           sources=("RHB-30",), in_t3=True),
    Ticker("544.SI", "CSE Global", "Industrial",
           sources=("RHB-30",), in_t3=True),
    Ticker("AP4.SI", "Riverstone", "Industrial",
           sources=("Edge-69",), in_t3=True),
    Ticker("H22.SI", "Hong Leong Asia", "Industrial",
           sources=("Edge-69",), in_t3=True),
    Ticker("F03.SI", "Food Empire", "Consumer",
           sources=("Edge-69",), in_t3=True),
    Ticker("EB5.SI", "First Resources", "Consumer",
           sources=("Edge-69",), in_t3=True),
    # Consumer / services mid-caps
    Ticker("OV8.SI", "Sheng Siong", "Consumer",
           sources=("Maybank-18",), in_t3=True),
    Ticker("C52.SI", "ComfortDelGro", "Industrial",
           sources=("RHB-30", "Maybank-18"), in_t3=True),
    Ticker("AIY.SI", "iFAST Corporation", "Financials",
           sources=("Maybank-18", "Edge-69"), in_t3=True),
    Ticker("OYY.SI", "PropNex", "Real Estate",
           sources=("Edge-69",), in_t3=True),
    Ticker("BSL.SI", "Raffles Medical", "Healthcare",
           sources=("RHB-30",), in_t3=True),
    # REITs
    Ticker("C2PU.SI", "Parkway Life REIT", "REIT",
           sources=("RHB-30",), in_t3=True),
    Ticker("K71U.SI", "Keppel REIT", "REIT",
           sources=("Edge-69",), in_t3=True),
    Ticker("T82U.SI", "Suntec REIT", "REIT",
           sources=("Edge-69",), in_t3=True),
    Ticker("HMN.SI", "CapitaLand Ascott Trust", "REIT",
           sources=("Edge-69",), in_t3=True),
    Ticker("O5RU.SI", "AIMS APAC REIT", "REIT",
           sources=("RHB-30",), in_t3=True),
    Ticker("P40U.SI", "Starhill Global REIT", "REIT",
           sources=("RHB-30",), in_t3=True),
    Ticker("BUOU.SI", "Frasers Logistics & Commercial Trust", "REIT",
           sources=("Edge-69",), in_t3=True),
    Ticker("J91U.SI", "ESR-LOGOS REIT", "REIT",
           sources=("Edge-69",), in_t3=True),
    Ticker("AJBU.SI", "Keppel DC REIT", "REIT",
           sources=("RHB-30",), in_t3=True),
    # Other
    Ticker("BS6.SI", "Yangzijiang Shipbuilding", "Industrial",
           sources=("Edge-69",), in_t3=True),
    Ticker("B61.SI", "Bukit Sembawang Estates", "Real Estate",
           sources=("RHB-30",), in_t3=True),
    Ticker("P34.SI", "Delfi Limited", "Consumer",
           sources=("RHB-30",), in_t3=True),
    Ticker("S08.SI", "Singapore Post", "Industrial",
           sources=("Edge-69",), in_t3=True),
    Ticker("CJLU.SI", "NetLink NBN Trust", "Telecom",
           sources=("Edge-69",), in_t3=True),
)


# ---------------------------------------------------------------------------
# Control — STI-30 large caps. Naturally de-emphasised by EQDP.
# Source: docs/TICKERS.md. Refresh on each STI rebalance.
# ---------------------------------------------------------------------------

_CONTROL_SEED: Final[tuple[Ticker, ...]] = (
    Ticker("D05.SI", "DBS Group", "Financials", in_control=True),
    Ticker("O39.SI", "OCBC", "Financials", in_control=True),
    Ticker("U11.SI", "UOB", "Financials", in_control=True),
    Ticker("Z74.SI", "Singtel", "Telecom", in_control=True),
    Ticker("C6L.SI", "Singapore Airlines", "Industrial", in_control=True),
    Ticker("C38U.SI", "CapitaLand Integrated Commercial Trust", "REIT",
           in_control=True),
    Ticker("BN4.SI", "Keppel", "Industrial", in_control=True),
    Ticker("F34.SI", "Wilmar International", "Consumer", in_control=True),
    Ticker("S63.SI", "ST Engineering", "Industrial", in_control=True),
    Ticker("Y92.SI", "Thai Beverage", "Consumer", in_control=True),
    Ticker("G13.SI", "Genting Singapore", "Consumer", in_control=True),
    Ticker("ME8U.SI", "Mapletree Industrial Trust", "REIT", in_control=True),
    Ticker("N2IU.SI", "Mapletree Pan Asia Commercial Trust", "REIT",
           in_control=True),
    Ticker("M44U.SI", "Mapletree Logistics Trust", "REIT", in_control=True),
    Ticker("J69U.SI", "Frasers Centrepoint Trust", "REIT", in_control=True),
    Ticker("A17U.SI", "Ascendas REIT", "REIT", in_control=True),
    Ticker("V03.SI", "Venture Corp", "Industrial", in_control=True),
    Ticker("S58.SI", "SATS", "Industrial", in_control=True),
    Ticker("S68.SI", "Singapore Exchange", "Financials", in_control=True),
    Ticker("U96.SI", "Sembcorp Industries", "Utilities", in_control=True),
)


# ---------------------------------------------------------------------------
# T2 — Eligible (starter seed).
# Day-1 hand-curated bootstrap. To be expanded by the programmatic SGX
# eligibility filter on Day 2+ once full listings are loaded. Each entry
# below is a Mainboard small/mid-cap not in STI-30; tickers are validated
# on first yfinance fetch and dropped if they fail.
# ---------------------------------------------------------------------------

_T2_EXTRA_SEED: Final[tuple[Ticker, ...]] = (
    Ticker("F99.SI", "Fraser & Neave", "Consumer", in_t2=True),
    Ticker("C07.SI", "Jardine Matheson Holdings", "Conglomerate", in_t2=True),
    Ticker("J36.SI", "Jardine Strategic Holdings", "Conglomerate", in_t2=True),
    Ticker("H78.SI", "Hongkong Land Holdings", "Real Estate", in_t2=True),
    Ticker("Q5T.SI", "DFI Retail Group", "Consumer", in_t2=True),
    Ticker("C61U.SI", "CapitaLand China Trust", "REIT", in_t2=True),
    Ticker("BTOU.SI", "Manulife US REIT", "REIT", in_t2=True),
    Ticker("M1GU.SI", "Sasseur REIT", "REIT", in_t2=True),
    Ticker("O08.SI", "Oxley Holdings", "Real Estate", in_t2=True),
    Ticker("S59.SI", "SIA Engineering", "Industrial", in_t2=True),
    Ticker("CC3.SI", "StarHub", "Telecom", in_t2=True),
    Ticker("F1E.SI", "OUE", "Real Estate", in_t2=True),
    Ticker("M03.SI", "Wing Tai Holdings", "Real Estate", in_t2=True),
    Ticker("504.SI", "Hi-P International", "Industrial", in_t2=True),
    Ticker("5DD.SI", "Innotek", "Industrial", in_t2=True),
    Ticker("BLR.SI", "Boustead Singapore", "Industrial", in_t2=True),
    Ticker("I07.SI", "ISDN Holdings", "Industrial", in_t2=True),
    Ticker("H02.SI", "Haw Par Corporation", "Healthcare", in_t2=True),
    Ticker("AYV.SI", "Stamford Land", "Real Estate", in_t2=True),
    Ticker("D03.SI", "Del Monte Pacific", "Consumer", in_t2=True),
    Ticker("U77.SI", "Sarine Technologies", "Industrial", in_t2=True),
    Ticker("P5P.SI", "Pan-United", "Industrial", in_t2=True),
    Ticker("M11.SI", "First Sponsor Group", "Real Estate", in_t2=True),
    Ticker("Q01.SI", "QAF Limited", "Consumer", in_t2=True),
    Ticker("5UA.SI", "Nera Telecommunications", "Telecom", in_t2=True),
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_t1() -> list[Ticker]:
    """Confirmed beneficiaries — populated from SGXNet substantial-shareholder
    filings by ``scrapers/sgxnet/`` on Day 6+. Empty until then."""
    return []


def get_t2() -> list[Ticker]:
    """Eligible universe — T3 names (which are by construction eligible) plus
    a hand-curated extras seed of Mainboard small/mid-caps not in STI-30.

    Returns merged Ticker rows: any stock that is also in T3 carries both
    ``in_t2=True`` and ``in_t3=True``."""
    by_symbol: dict[str, Ticker] = {}
    for t in _T3_SEED:
        # T3 names are eligible by construction; expose them as in_t2 too.
        by_symbol[t.symbol] = Ticker(
            symbol=t.symbol,
            name=t.name,
            sector=t.sector,
            sources=t.sources,
            in_t1=t.in_t1,
            in_t2=True,
            in_t3=True,
            in_control=t.in_control,
        )
    for t in _T2_EXTRA_SEED:
        if t.symbol in by_symbol:
            continue
        by_symbol[t.symbol] = t
    return list(by_symbol.values())


def get_t3() -> list[Ticker]:
    """Named beneficiaries from broker notes (RHB-30, Maybank-18, Edge-69)."""
    return list(_T3_SEED)


def get_control() -> list[Ticker]:
    """Control pool — STI-30 large caps."""
    return list(_CONTROL_SEED)


def all_tickers() -> list[Ticker]:
    """Union of T2 (which includes T3) and control. T1 will be added once
    the SGXNet scraper lands."""
    by_symbol: dict[str, Ticker] = {t.symbol: t for t in get_t2()}
    for t in get_control():
        if t.symbol in by_symbol:
            continue
        by_symbol[t.symbol] = t
    return list(by_symbol.values())


def find(symbol: str) -> Ticker | None:
    """Look up a single ticker across all tiers; ``None`` if not found."""
    for t in all_tickers():
        if t.symbol == symbol:
            return t
    return None
