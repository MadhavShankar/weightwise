-- Migration 004 — Phone number + web identity bridge
-- Additive only; no existing tables, columns, or policies are modified.

ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number text UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS water_goal_ml int;

CREATE TABLE IF NOT EXISTS web_users (
  id           bigserial PRIMARY KEY,
  auth_uuid    uuid UNIQUE NOT NULL,
  internal_id  bigint UNIQUE NOT NULL,
  email        text,
  phone_number text,
  created_at   timestamptz DEFAULT now()
);

-- Mobile-only user IDs start above any realistic Telegram ID
CREATE SEQUENCE IF NOT EXISTS web_user_id_seq START 9000000000;

ALTER TABLE web_users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own row only" ON web_users
  USING (auth_uuid = auth.uid());
