-- =====================================================================
-- sg-eqdp-scanner — Postgres schema (Supabase)
-- Apply once on Day 1: paste this into the Supabase SQL editor.
-- After this, use db/migrations/ for incremental changes.
-- =====================================================================

-- Required extension for uuid_generate_v4(); installed by default on Supabase.
create extension if not exists "uuid-ossp";

-- =====================================================================
-- Operations
-- =====================================================================

create table if not exists pipeline_runs (
    run_id          uuid primary key default uuid_generate_v4(),
    job_name        text not null,
    started_at      timestamptz not null default now(),
    completed_at    timestamptz,
    status          text not null check (status in ('running','succeeded','partial','failed')),
    metrics_json    jsonb,
    error_message   text
);
create index if not exists pipeline_runs_job_status_idx
    on pipeline_runs(job_name, status, started_at desc);

-- =====================================================================
-- Universe
-- =====================================================================

create table if not exists tickers (
    ticker              text primary key,
    sgx_code            text,
    name                text not null,
    sector              text,
    market_cap_band     text check (market_cap_band in ('large','mid','small','micro')),
    listing_board       text check (listing_board in ('Mainboard','Catalist')),
    in_sti30            boolean default false,
    in_next50           boolean default false,
    restricted_sector   boolean default false,
    t1_flag             boolean default false,
    t2_flag             boolean default false,
    t3_flag             boolean default false,
    broker_named_count  int default 0,
    first_seen          date,
    last_seen           date,
    created_at          timestamptz default now(),
    pipeline_run_id     uuid references pipeline_runs(run_id)
);

create table if not exists eqdp_managers (
    manager_id      text primary key,
    canonical_name  text not null,
    aliases         text[] default '{}',
    tranche         int check (tranche in (1,2)),
    appointed_date  date,
    created_at      timestamptz default now()
);

-- =====================================================================
-- Prices and factors
-- =====================================================================

create table if not exists prices_daily (
    ticker          text not null references tickers(ticker),
    trade_date      date not null,
    open            numeric,
    high            numeric,
    low             numeric,
    close           numeric,
    adj_close       numeric,
    volume          bigint,
    dollar_volume   numeric generated always as (adj_close * volume) stored,
    created_at      timestamptz default now(),
    pipeline_run_id uuid references pipeline_runs(run_id),
    primary key (ticker, trade_date)
);
create index if not exists prices_daily_date_idx
    on prices_daily(trade_date desc);

create table if not exists factor_returns (
    trade_date      date primary key,
    market          numeric not null,
    smb             numeric,
    hml             numeric,
    created_at      timestamptz default now(),
    pipeline_run_id uuid references pipeline_runs(run_id)
);

create table if not exists betas (
    ticker          text not null references tickers(ticker),
    window_end      date not null,
    window_days     int not null,
    alpha           numeric not null,
    beta            numeric not null,
    r_squared       numeric,
    created_at      timestamptz default now(),
    pipeline_run_id uuid references pipeline_runs(run_id),
    primary key (ticker, window_end)
);

-- =====================================================================
-- Impact estimation
-- =====================================================================

create table if not exists abnormal_returns (
    ticker          text not null references tickers(ticker),
    event_id        text not null,
    t               int not null,
    benchmark       text not null check (benchmark in ('capm','ff3','market_adjusted')),
    ar              numeric,
    car             numeric,
    created_at      timestamptz default now(),
    pipeline_run_id uuid references pipeline_runs(run_id),
    primary key (ticker, event_id, t, benchmark)
);
create index if not exists abnormal_returns_event_idx
    on abnormal_returns(event_id, benchmark, t);

create table if not exists liquidity_metrics (
    ticker              text not null references tickers(ticker),
    trade_date          date not null,
    amihud              numeric,
    amihud_60d          numeric,
    turnover_velocity   numeric,
    created_at          timestamptz default now(),
    pipeline_run_id     uuid references pipeline_runs(run_id),
    primary key (ticker, trade_date)
);
create index if not exists liquidity_metrics_date_idx
    on liquidity_metrics(trade_date desc);

create table if not exists synthetic_controls (
    ticker          text not null references tickers(ticker),
    event_id        text not null,
    t               int not null,
    observed        numeric,
    counterfactual  numeric,
    ci_lower        numeric,
    ci_upper        numeric,
    created_at      timestamptz default now(),
    pipeline_run_id uuid references pipeline_runs(run_id),
    primary key (ticker, event_id, t)
);

create table if not exists placebo_results (
    placebo_date    date not null,
    panel           text not null,
    metric          text not null,
    value           numeric,
    p_value         numeric,
    created_at      timestamptz default now(),
    pipeline_run_id uuid references pipeline_runs(run_id),
    primary key (placebo_date, panel, metric)
);

create table if not exists bootstrap_cis (
    metric          text not null,
    scope           text not null,
    point_estimate  numeric,
    lower_5         numeric,
    upper_95        numeric,
    n_replications  int,
    computed_at     timestamptz default now(),
    pipeline_run_id uuid references pipeline_runs(run_id),
    primary key (metric, scope)
);

-- =====================================================================
-- Candidate score (the screen — no return inputs)
-- =====================================================================

create table if not exists candidate_scores (
    ticker              text not null references tickers(ticker),
    score_date          date not null,
    liquidity_rise      numeric,
    institutional_proxy numeric,
    index_inclusion     int check (index_inclusion in (0,1)),
    broker_named        numeric,
    filing_present      int check (filing_present in (0,1)),
    total_score         numeric,
    eqdp_tier           text check (eqdp_tier in ('T1','T2','T3','control','none')),
    created_at          timestamptz default now(),
    pipeline_run_id     uuid references pipeline_runs(run_id),
    primary key (ticker, score_date)
);
create index if not exists candidate_scores_latest_idx
    on candidate_scores(score_date desc, total_score desc);

-- =====================================================================
-- Ground truth — SGXNet substantial-shareholder filings
-- =====================================================================

create table if not exists filings_t1 (
    filing_id       text primary key,
    manager_id      text not null references eqdp_managers(manager_id),
    ticker          text not null references tickers(ticker),
    effective_date  date not null,
    filing_date     date not null,
    stake_pct       numeric,
    direction       text check (direction in ('acquired','disposed','crossed_up','crossed_down')),
    source_url      text not null,
    created_at      timestamptz default now(),
    pipeline_run_id uuid references pipeline_runs(run_id)
);
create index if not exists filings_t1_filing_date_idx
    on filings_t1(filing_date desc);
create index if not exists filings_t1_ticker_idx
    on filings_t1(ticker, filing_date desc);

-- =====================================================================
-- Users + engagement
-- (auth.users is managed by Supabase Auth)
-- =====================================================================

create table if not exists user_profiles (
    user_id                 uuid primary key references auth.users(id) on delete cascade,
    name                    text,
    firm                    text,
    country                 text,
    disclaimer_accepted_at  timestamptz not null,
    email_optin             boolean default true,
    registered_at           timestamptz default now(),
    unsubscribed_at         timestamptz
);

create table if not exists engagement_events (
    event_id            uuid primary key default uuid_generate_v4(),
    user_id             uuid references auth.users(id) on delete set null,
    session_id          text,
    route               text not null,
    section_anchor      text,
    time_on_section_ms  int,
    event_at            timestamptz default now()
);
create index if not exists engagement_events_user_idx
    on engagement_events(user_id, event_at desc);
create index if not exists engagement_events_route_idx
    on engagement_events(route, event_at desc);

-- =====================================================================
-- Row-level security
-- =====================================================================
-- Anon (public) reads of analytical tables are allowed; writes are service-role only.
-- User-profile reads are restricted to the owning user. Engagement writes are
-- only allowed for the owning user (or anon for unauthenticated public pages).

alter table tickers              enable row level security;
alter table prices_daily         enable row level security;
alter table factor_returns       enable row level security;
alter table betas                enable row level security;
alter table abnormal_returns     enable row level security;
alter table liquidity_metrics    enable row level security;
alter table synthetic_controls   enable row level security;
alter table placebo_results      enable row level security;
alter table bootstrap_cis        enable row level security;
alter table candidate_scores     enable row level security;
alter table filings_t1           enable row level security;
alter table eqdp_managers        enable row level security;
alter table pipeline_runs        enable row level security;
alter table user_profiles        enable row level security;
alter table engagement_events    enable row level security;

-- Public read on the analytical tables.
do $$
declare t text;
begin
  for t in select unnest(array[
    'tickers','prices_daily','factor_returns','betas','abnormal_returns',
    'liquidity_metrics','synthetic_controls','placebo_results','bootstrap_cis',
    'candidate_scores','filings_t1','eqdp_managers','pipeline_runs'
  ])
  loop
    execute format(
      'create policy "%I_public_read" on %I for select to anon, authenticated using (true);',
      t, t
    );
  end loop;
end $$;

-- User profile: a user may read and update only their own row.
create policy "user_profiles_self_read"
  on user_profiles for select
  to authenticated using (user_id = auth.uid());
create policy "user_profiles_self_upsert"
  on user_profiles for insert
  to authenticated with check (user_id = auth.uid());
create policy "user_profiles_self_update"
  on user_profiles for update
  to authenticated using (user_id = auth.uid());

-- Engagement: any session may write its own events; reads are admin-only
-- (admin queries use the service-role key, which bypasses RLS).
create policy "engagement_events_insert_anyone"
  on engagement_events for insert
  to anon, authenticated with check (true);

-- =====================================================================
-- Done. All writes from the Python pipeline must use SUPABASE_SERVICE_KEY,
-- which bypasses RLS. The web app uses the anon key for public reads and
-- the user's session for authenticated reads.
-- =====================================================================
