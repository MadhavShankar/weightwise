-- Migration 005 — Notifications and device tokens

CREATE TABLE IF NOT EXISTS notifications (
  id           bigserial PRIMARY KEY,
  internal_id  bigint REFERENCES users(telegram_id) ON DELETE CASCADE,
  title        text NOT NULL,
  body         text NOT NULL,
  is_read      boolean DEFAULT false,
  created_at   timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS notifications_internal_id_created
  ON notifications (internal_id, is_read, created_at DESC);

CREATE TABLE IF NOT EXISTS device_tokens (
  id           bigserial PRIMARY KEY,
  internal_id  bigint REFERENCES users(telegram_id) ON DELETE CASCADE,
  expo_token   text NOT NULL,
  platform     text CHECK (platform IN ('ios', 'android')),
  created_at   timestamptz DEFAULT now(),
  UNIQUE (internal_id, expo_token)
);

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own notifications" ON notifications
  USING (internal_id = (
    SELECT internal_id FROM web_users WHERE auth_uuid = auth.uid()
  ));

ALTER TABLE device_tokens ENABLE ROW LEVEL SECURITY;
-- No client-side access; FastAPI service role key manages this table
