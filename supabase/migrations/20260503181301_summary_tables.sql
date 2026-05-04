-- Summary tables for /brief charts (computed by pipelines/compute_summaries.py).

create table if not exists ticker_summaries (
    ticker          text primary key references tickers(ticker),
    car_total       numeric,
    car_mean        numeric,
    volume_lift_pct numeric,
    amihud_change   numeric,
    n_events        int,
    computed_at     timestamptz default now(),
    pipeline_run_id uuid references pipeline_runs(run_id)
);
create index if not exists ticker_summaries_car_total_idx
    on ticker_summaries(car_total desc nulls last);

create table if not exists cohort_timeseries (
    trade_date          date primary key,
    treatment_cum       numeric,
    control_cum         numeric,
    sti_cum             numeric,
    n_treatment         int,
    n_control           int,
    computed_at         timestamptz default now(),
    pipeline_run_id     uuid references pipeline_runs(run_id)
);
create index if not exists cohort_timeseries_date_idx
    on cohort_timeseries(trade_date desc);

alter table ticker_summaries enable row level security;
alter table cohort_timeseries enable row level security;

create policy "ticker_summaries_public_read"
  on ticker_summaries for select to anon, authenticated using (true);
create policy "cohort_timeseries_public_read"
  on cohort_timeseries for select to anon, authenticated using (true);
