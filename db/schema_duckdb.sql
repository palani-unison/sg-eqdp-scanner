-- =====================================================================
-- sg-eqdp-scanner — DuckDB schema (Streamlit + DuckDB-in-repo edition)
--
-- Apply on first run via `python -m scripts.init_duckdb`. Idempotent —
-- every CREATE uses IF NOT EXISTS. Identical column names + types to the
-- old Supabase Postgres schema, with the following intentional drops:
--   - auth.users / user_profiles / engagement_events  (no auth in v2)
--   - row-level security and policies                  (irrelevant in DuckDB)
--   - GENERATED ALWAYS AS (...) STORED columns         (DuckDB doesn't support;
--                                                       compute in Python)
--   - PostgreSQL-only types (uuid_generate_v4, jsonb)  (use UUID, JSON)
-- =====================================================================

-- DuckDB has UUID as a built-in type; pipelines pass UUID strings produced
-- via Python's uuid.uuid4(), so no extension is required.

-- ---------------------------------------------------------------------
-- Operations
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id          UUID PRIMARY KEY DEFAULT uuid(),
    job_name        TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    status          TEXT NOT NULL CHECK (status IN ('running','succeeded','partial','failed')),
    metrics_json    JSON,
    error_message   TEXT
);
CREATE INDEX IF NOT EXISTS pipeline_runs_job_status_idx
    ON pipeline_runs(job_name, status, started_at DESC);

-- ---------------------------------------------------------------------
-- Universe
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tickers (
    ticker              TEXT PRIMARY KEY,
    sgx_code            TEXT,
    name                TEXT NOT NULL,
    sector              TEXT,
    market_cap_band     TEXT CHECK (market_cap_band IN ('large','mid','small','micro')),
    listing_board       TEXT CHECK (listing_board IN ('Mainboard','Catalist')),
    in_sti30            BOOLEAN DEFAULT false,
    in_next50           BOOLEAN DEFAULT false,
    restricted_sector   BOOLEAN DEFAULT false,
    t1_flag             BOOLEAN DEFAULT false,
    t2_flag             BOOLEAN DEFAULT false,
    t3_flag             BOOLEAN DEFAULT false,
    broker_named_count  INTEGER DEFAULT 0,
    first_seen          DATE,
    last_seen           DATE,
    created_at          TIMESTAMPTZ DEFAULT now(),
    pipeline_run_id     UUID
);

CREATE TABLE IF NOT EXISTS eqdp_managers (
    manager_id      TEXT PRIMARY KEY,
    canonical_name  TEXT NOT NULL,
    aliases         TEXT[] DEFAULT [],
    tranche         INTEGER CHECK (tranche IN (1,2)),
    appointed_date  DATE,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Prices and factors
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS prices_daily (
    ticker          TEXT NOT NULL,
    trade_date      DATE NOT NULL,
    open            DOUBLE,
    high            DOUBLE,
    low             DOUBLE,
    close           DOUBLE,
    adj_close       DOUBLE,
    volume          BIGINT,
    -- dollar_volume was a generated column in Postgres; pipelines compute it.
    dollar_volume   DOUBLE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    pipeline_run_id UUID,
    PRIMARY KEY (ticker, trade_date)
);
CREATE INDEX IF NOT EXISTS prices_daily_date_idx
    ON prices_daily(trade_date DESC);

CREATE TABLE IF NOT EXISTS factor_returns (
    trade_date      DATE PRIMARY KEY,
    market          DOUBLE NOT NULL,
    smb             DOUBLE,
    hml             DOUBLE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    pipeline_run_id UUID
);

CREATE TABLE IF NOT EXISTS betas (
    ticker          TEXT NOT NULL,
    window_end      DATE NOT NULL,
    window_days     INTEGER NOT NULL,
    alpha           DOUBLE NOT NULL,
    beta            DOUBLE NOT NULL,
    r_squared       DOUBLE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    pipeline_run_id UUID,
    PRIMARY KEY (ticker, window_end)
);

-- ---------------------------------------------------------------------
-- Impact estimation
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS abnormal_returns (
    ticker          TEXT NOT NULL,
    event_id        TEXT NOT NULL,
    t               INTEGER NOT NULL,
    benchmark       TEXT NOT NULL CHECK (benchmark IN ('capm','ff3','market_adjusted')),
    ar              DOUBLE,
    car             DOUBLE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    pipeline_run_id UUID,
    PRIMARY KEY (ticker, event_id, t, benchmark)
);
CREATE INDEX IF NOT EXISTS abnormal_returns_event_idx
    ON abnormal_returns(event_id, benchmark, t);

CREATE TABLE IF NOT EXISTS liquidity_metrics (
    ticker              TEXT NOT NULL,
    trade_date          DATE NOT NULL,
    amihud              DOUBLE,
    amihud_60d          DOUBLE,
    turnover_velocity   DOUBLE,
    created_at          TIMESTAMPTZ DEFAULT now(),
    pipeline_run_id     UUID,
    PRIMARY KEY (ticker, trade_date)
);
CREATE INDEX IF NOT EXISTS liquidity_metrics_date_idx
    ON liquidity_metrics(trade_date DESC);

CREATE TABLE IF NOT EXISTS synthetic_controls (
    ticker          TEXT NOT NULL,
    event_id        TEXT NOT NULL,
    t               INTEGER NOT NULL,
    observed        DOUBLE,
    counterfactual  DOUBLE,
    ci_lower        DOUBLE,
    ci_upper        DOUBLE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    pipeline_run_id UUID,
    PRIMARY KEY (ticker, event_id, t)
);

CREATE TABLE IF NOT EXISTS placebo_results (
    placebo_date    DATE NOT NULL,
    panel           TEXT NOT NULL,
    metric          TEXT NOT NULL,
    value           DOUBLE,
    p_value         DOUBLE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    pipeline_run_id UUID,
    PRIMARY KEY (placebo_date, panel, metric)
);

CREATE TABLE IF NOT EXISTS bootstrap_cis (
    metric          TEXT NOT NULL,
    scope           TEXT NOT NULL,
    point_estimate  DOUBLE,
    lower_5         DOUBLE,
    upper_95        DOUBLE,
    n_replications  INTEGER,
    computed_at     TIMESTAMPTZ DEFAULT now(),
    pipeline_run_id UUID,
    PRIMARY KEY (metric, scope)
);

-- ---------------------------------------------------------------------
-- Candidate score (no return inputs)
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS candidate_scores (
    ticker              TEXT NOT NULL,
    score_date          DATE NOT NULL,
    liquidity_rise      DOUBLE,
    institutional_proxy DOUBLE,
    index_inclusion     INTEGER CHECK (index_inclusion IN (0,1)),
    broker_named        DOUBLE,
    filing_present      INTEGER CHECK (filing_present IN (0,1)),
    total_score         DOUBLE,
    eqdp_tier           TEXT CHECK (eqdp_tier IN ('T1','T2','T3','control','none')),
    created_at          TIMESTAMPTZ DEFAULT now(),
    pipeline_run_id     UUID,
    PRIMARY KEY (ticker, score_date)
);
CREATE INDEX IF NOT EXISTS candidate_scores_latest_idx
    ON candidate_scores(score_date DESC, total_score DESC);

-- ---------------------------------------------------------------------
-- T1 ground truth — SGXNet substantial-shareholder filings
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS filings_t1 (
    filing_id       TEXT PRIMARY KEY,
    manager_id      TEXT NOT NULL,
    ticker          TEXT NOT NULL,
    effective_date  DATE NOT NULL,
    filing_date     DATE NOT NULL,
    stake_pct       DOUBLE,
    direction       TEXT CHECK (direction IN ('acquired','disposed','crossed_up','crossed_down')),
    source_url      TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now(),
    pipeline_run_id UUID
);
CREATE INDEX IF NOT EXISTS filings_t1_filing_date_idx
    ON filings_t1(filing_date DESC);
CREATE INDEX IF NOT EXISTS filings_t1_ticker_idx
    ON filings_t1(ticker, filing_date DESC);

-- =====================================================================
-- End of schema. user_profiles, engagement_events, and RLS policies are
-- intentionally absent — there is no auth in the DuckDB edition.
-- =====================================================================
