-- WeightWise — initial schema
-- Run this in the Supabase SQL editor (or via CLI: supabase db push)

-- ── users ────────────────────────────────────────────────────────────────────
create table if not exists users (
    id                  bigserial primary key,
    telegram_id         bigint      not null unique,
    name                text        not null,

    -- onboarding profile
    age                 int,
    gender              text        check (gender in ('male', 'female')),
    height_cm           float,
    weight_kg           float,
    target_weight_kg    float,
    activity_level      text        check (activity_level in ('sedentary', 'light', 'moderate', 'active')),
    diet_preference     text,
    medical_conditions  text,

    -- computed at onboarding, re-computed on profile update
    calorie_target      int,

    created_at          timestamptz not null default now()
);

-- ── meal_logs ────────────────────────────────────────────────────────────────
create table if not exists meal_logs (
    id          bigserial primary key,
    telegram_id bigint      not null references users (telegram_id) on delete cascade,
    description text        not null,
    calories    int         not null,
    meal_data   jsonb       not null default '{}',   -- {protein_g, carbs_g, fat_g, …}
    logged_at   timestamptz not null default now()
);

create index if not exists meal_logs_telegram_id_logged_at
    on meal_logs (telegram_id, logged_at desc);

-- ── weight_logs ───────────────────────────────────────────────────────────────
create table if not exists weight_logs (
    id          bigserial primary key,
    telegram_id bigint      not null references users (telegram_id) on delete cascade,
    weight_kg   float       not null,
    logged_at   timestamptz not null default now()
);

create index if not exists weight_logs_telegram_id_logged_at
    on weight_logs (telegram_id, logged_at desc);
