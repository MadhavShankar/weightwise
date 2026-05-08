-- Add scheduler-related columns to users table
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS onboarding_complete BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS notifications_paused BOOLEAN NOT NULL DEFAULT FALSE;

-- Mark existing users with a full profile as onboarding complete
UPDATE users SET onboarding_complete = TRUE WHERE calorie_target IS NOT NULL;
