-- report_summaries table (used by services/database.py but missing from prior migrations)
create table if not exists report_summaries (
    id          bigserial primary key,
    telegram_id bigint      not null references users (telegram_id) on delete cascade,
    summary     text        not null,
    created_at  timestamptz not null default now()
);

create index if not exists report_summaries_telegram_id_created_at
    on report_summaries (telegram_id, created_at desc);

-- current_plan column (used by handlers/plan.py but missing from prior migrations)
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS current_plan text;
