# sg-eqdp-scanner

> **Personal research by Palaniappan Chidambaram. Not investment advice. Not affiliated with Unison Group or any other entity.**
> See [DISCLAIMER.md](docs/DISCLAIMER.md) before reading or using anything in this repository.

A reproducible, public-data forensic study of the **Singapore MAS Equity Market Development Programme (EQDP)** — a S$6.5 billion programme deploying capital through nine appointed asset managers into SGX-listed equities. This repository identifies which Singapore-listed companies plausibly benefited from the programme (and which did not), and powers the **EQDP Brief** web application.

🔗 **Live site:** _to be added once deployed_

📄 **License:** MIT — fork, run, verify, disagree, publish your own conclusions.

---

## What this is

MAS does not disclose which specific stocks the EQDP-appointed managers buy. This repository:

1. Constructs a **three-tier beneficiary universe** — Confirmed (SGXNet 5%+ filings), Eligible (programmatic screen), Named (broker beneficiary lists).
2. Computes **abnormal returns** (CAPM- and Fama-French-adjusted), **liquidity changes** (Amihud), and **synthetic-control counterfactuals** around the four EQDP event dates.
3. Produces a **decoupled candidate score** that does not use returns as an input — so we never measure the outcome with the outcome.
4. Stores results in a **DuckDB file committed to the repo** (`data/eqdp.duckdb`) and renders them in a **Streamlit** data-science dashboard with a forensic, technical-analyst aesthetic.

## Architecture

| Layer | Tech | Role |
|---|---|---|
| Analytical core | Python 3.11, pandas, numpy, scipy, statsmodels, linearmodels, CausalImpact, yfinance | All analysis, signals, backtests |
| Data store | DuckDB file (`data/eqdp.duckdb`, in repo) | Gold-tier tables (prices, abnormal returns, candidate scores, T1 filings) |
| Web app | Streamlit + Plotly | Public site (`streamlit_app/`) — Tracker, Event Studies, Universe, Ticker Analyzer, Filings |
| Pipeline runner | GitHub Actions | Daily / weekly / monthly Python jobs that update the DuckDB file and push it back |
| Hosting | Streamlit Community Cloud (free tier) | The web app |

> No managed database, no auth, no external service. The dashboard reads from the same DuckDB file the pipeline wrote — a clone of the repo is a complete reproduction of the analysis.

> The legacy Next.js prototype lives in `web/` and is no longer the active surface. It will be removed once the Streamlit app reaches feature parity.

See [`CLAUDE.md`](CLAUDE.md) for the project guide, [`docs/STRATEGY.md`](docs/STRATEGY.md) for the strategic plan, and [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) for the math.

## Quick start

### Prerequisites
- Python 3.11+
- A free Streamlit Community Cloud account ([streamlit.io/cloud](https://streamlit.io/cloud))

### Reproduce the analysis (Phase 0 backfill on your laptop)
```bash
git clone https://github.com/<your-handle>/sg-eqdp-scanner.git
cd sg-eqdp-scanner
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt   # dashboard + pipelines
python -m scripts.init_duckdb              # creates data/eqdp.duckdb
python -m pipelines.backfill --start 2020-01-01 --end yesterday
```

### Run the Streamlit app locally
```bash
streamlit run streamlit_app/EQDP_Brief.py
```
The app reads `data/eqdp.duckdb`. If it's missing, run `python -m scripts.init_duckdb` first.

### Deploy to Streamlit Community Cloud (free)
1. Push this repo to GitHub.
2. New app → repo + branch + main file path = `streamlit_app/EQDP_Brief.py`.
3. **Advanced Settings → Python version → 3.12.** The pinned wheels do not have 3.13 / 3.14 builds, so the default Python will source-build and likely fail.
4. No secrets required — the DuckDB file ships with the repo.
5. Streamlit installs only from `requirements.txt` (slim — ~5 packages). `requirements-dev.txt` is for local pipeline runs and is *not* read by Streamlit Cloud.

### Continue the live increments
GitHub Actions takes over after the backfill — daily, weekly, and monthly cron jobs upsert fresh data into Supabase. See `.github/workflows/`.

## Methodology, in one paragraph

For each stock and each EQDP event date, we estimate **abnormal return** = realised return − CAPM expected return, where β is fit on a 252-day pre-event window. We measure **abnormal volume** and **Amihud illiquidity change** the same way. For each named beneficiary we build a **Bayesian synthetic control** (CausalImpact) from non-EQDP stocks and report the post-event divergence with full posterior intervals. We then run **placebo tests** on non-event dates to verify that the method finds null where it should, and report **block-bootstrap 5–95 % confidence intervals** for every headline number. Full math in [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## What this repository does **not** claim

- That this is investment advice. It is not.
- That MAS disclosed any of the holdings used in T1. It did not — those are inferred from public SGXNet substantial-shareholder filings.
- That sub-5 % positions are detectable. They are not — meaningful EQDP capital may sit in stocks that never appear in T1.
- That the named beneficiaries are guaranteed to outperform going forward. Past performance does not predict future results.

## Contributing

This is a personal-research project, but PRs that improve methodology, fix bugs, or extend the universe are welcome. Open an issue first to discuss large changes. All contributions accepted under the repository's MIT licence.

## License

[MIT](LICENSE) — © 2026 Palaniappan Chidambaram.
