# TICKERS.md — starter universe

The seed lists used to bootstrap the analytical universe on Day 1. These are populated into `tickers` via `src/universe.py` and then enriched by the SGXNet scraper (T1) and the programmatic eligibility filter (T2).

Ticker convention: yfinance form, e.g. `E28.SI`. Local SGX code = the part before `.SI`.

---

## EQDP timeline (canonical event dates)

| Event ID | Date | Description |
|---|---|---|
| `announcement` | 2025-02-21 | MAS launches S$5B EQDP |
| `tranche_1` | 2025-07-21 | S$1.1B → 3 managers |
| `tranche_2` | 2025-11-19 | S$2.85B → 6 managers |
| `expansion` | 2026-02-12 | Expanded to S$6.5B |

---

## EQDP-appointed managers (the nine)

| Manager | Tranche | Notes |
|---|---|---|
| Avanda Investment Management | 1 | |
| Fullerton Fund Management | 1 | |
| JPMorgan Asset Management | 1 | |
| Amova Asset Management | 2 | formerly Nikko AM |
| AR Capital | 2 | |
| BlackRock | 2 | files under multiple legal entities — alias resolution required |
| Eastspring Investments | 2 | |
| Lion Global Investors | 2 | |
| Manulife Investment Management | 2 | |

---

## T3 — Named beneficiaries (broker lists)

Stocks named in published broker beneficiary notes. This is the easiest tier to populate (no scraping yet) and gives Day 1 something to score.

### Industrial / tech small-mid caps
| Ticker | Name | Source |
|---|---|---|
| E28.SI | Frencken Group | RHB-30, Edge-69 |
| 558.SI | UMS Integration | RHB-30, Edge-69, Maybank-18 |
| AWX.SI | AEM Holdings | RHB-30 |
| 544.SI | CSE Global | RHB-30 |
| AP4.SI | Riverstone | Edge-69 |
| H22.SI | Hong Leong Asia | Edge-69 |
| F03.SI | Food Empire | Edge-69 |
| EB5.SI | First Resources | Edge-69 |

### Consumer / services mid-caps
| Ticker | Name | Source |
|---|---|---|
| OV8.SI | Sheng Siong | Maybank-18 |
| C52.SI | ComfortDelGro | RHB-30, Maybank-18 |
| AIY.SI | iFAST Corporation | Maybank-18, Edge-69 |
| OYY.SI | PropNex | Edge-69 |
| BSL.SI | Raffles Medical | RHB-30 |

### REITs
| Ticker | Name | Source |
|---|---|---|
| C2PU.SI | Parkway Life REIT | RHB-30 |
| K71U.SI | Keppel REIT | Edge-69 |
| T82U.SI | Suntec REIT | Edge-69 |
| HMN.SI | CapitaLand Ascott Trust | Edge-69 |
| O5RU.SI | AIMS APAC REIT | RHB-30 |
| P40U.SI | Starhill Global REIT | RHB-30 |
| BUOU.SI | Frasers Logistics & Commercial Trust | Edge-69 |
| J91U.SI | ESR-LOGOS REIT | Edge-69 |
| AJBU.SI | Keppel DC REIT | RHB-30 |

### Other
| Ticker | Name | Source |
|---|---|---|
| BS6.SI | Yangzijiang Shipbuilding | Edge-69 |
| B61.SI | Bukit Sembawang | RHB-30 |
| P34.SI | Delfi Limited | RHB-30 |
| S08.SI | Singapore Post | Edge-69 |
| CJLU.SI | NetLink NBN Trust | Edge-69 |

These are the seeds; the SGXNet scraper enriches T1 and the eligibility filter expands T2 programmatically.

---

## Control universe — STI-30

Used as the matched-control pool for the event studies.

| Ticker | Name |
|---|---|
| D05.SI | DBS Group |
| O39.SI | OCBC |
| U11.SI | UOB |
| Z74.SI | Singtel |
| C6L.SI | Singapore Airlines |
| C38U.SI | CapitaLand Integrated Commercial Trust |
| BN4.SI | Keppel |
| F34.SI | Wilmar International |
| S63.SI | ST Engineering |
| Y92.SI | Thai Beverage |
| G13.SI | Genting Singapore |
| ME8U.SI | Mapletree Industrial Trust |
| N2IU.SI | Mapletree Pan Asia Commercial Trust |
| M44U.SI | Mapletree Logistics Trust |
| J69U.SI | Frasers Centrepoint Trust |
| A17U.SI | Ascendas REIT |
| V03.SI | Venture Corp |
| S58.SI | SATS |
| S68.SI | Singapore Exchange |
| U96.SI | Sembcorp Industries |

(Refresh from index sheet as STI-30 rebalances.)

---

## Excluded sectors (T2 eligibility filter)

EQDP eligibility criteria, applied programmatically:

- **Excluded**: STI-30 constituents, REITs already in STI-30, business trusts heavily concentrated in offshore exposure, Catalist micro-caps with median dollar-volume < S$1m/day.
- **Included**: Mainboard small/mid-caps, Catalist mid-caps with adequate liquidity, REITs not in STI-30 with daily turnover > S$500k.

These are heuristics derived from public programme design language, not a verbatim quote of MAS criteria. Expect to refine.
