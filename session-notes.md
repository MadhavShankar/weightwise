# Session Notes

## Session 7 — 2026-05-07

### What was built
- `services/scheduler.py`: APScheduler `AsyncIOScheduler`; `daily_summary` job at 15:30 UTC (9 pm IST) — fetches all onboarded non-paused users, sends calories in/target, deficit/surplus, meal count, rule-based coaching line; `re_engagement` job at 13:30 UTC (7 pm IST) — fetches users with no meal logged in 48 h, sends nudge message; `setup_scheduler(bot)` / `shutdown_scheduler()` API
- `services/database.py`: added `get_all_onboarded_users()`, `get_today_meal_count()`, `get_last_meal_logged_at()`, `get_users_inactive_48h()` (Python-side 48 h filter)
- `handlers/start.py`: `_ask_medical` now sets `onboarding_complete: True` in the final `update_user` call
- `main.py`: added `_post_init` / `_post_shutdown` async hooks wired into `Application.builder()`; imports scheduler
- `requirements.txt`: added `APScheduler==3.10.4`
- `migrations/002_scheduler_columns.sql`: adds `onboarding_complete` and `notifications_paused` boolean columns; backfills existing complete profiles

### Pending for next session (Deployment)
1. Run `migrations/002_scheduler_columns.sql` in Supabase SQL editor
2. `pip install APScheduler==3.10.4` on VPS (or `pip install -r requirements.txt`)
3. Restart systemd service — verify scheduler log lines appear in `journalctl`
4. End-to-end test: confirm daily_summary fires at 9 pm IST; test `/pause` command (not yet built) to set `notifications_paused = true`
5. Write pytest suite

## Session 1 — 2026-05-07

### What was done
- Read CLAUDE.md and established project rules (no inline prompts, all AI via services/ai.py, async throughout, logging not print)
- Scaffolded full project structure: main.py, handlers/, services/, prompts/
- Implemented services/database.py in full (Supabase client, lazy singleton)

### Key decisions
- Supabase client uses lazy singleton via module-level `_client` to avoid repeated initialisation
- `telegram_id` used directly as the FK in meal_logs and weight_logs (no JOIN needed in handlers)
- `logged_at` stored as UTC ISO-8601 string; `get_today_calories` and `get_weight_history` filter server-side
- `maybe_single()` used in `get_user` so it returns `None` instead of raising when user doesn't exist

### Database tables expected
| Table        | Key columns                                                        |
|--------------|--------------------------------------------------------------------|
| users        | telegram_id (unique), name, created_at                             |
| meal_logs    | telegram_id, description, calories (int), meal_data (jsonb), logged_at |
| weight_logs  | telegram_id, weight_kg (float), logged_at                          |

### Next steps
1. Write `.env.example` and `requirements.txt`
2. Create Supabase tables (SQL migration)
3. Implement `handlers/start.py` — `/start` registers new user or greets returning user
4. Implement `services/ai.py` — prompt loader + `analyse_meal()` and `generate_report()` wrappers
5. Implement `handlers/meal_log.py` — free-text meal entry → AI analysis → log_meal → reply with calories
6. Fill in `prompts/meal_analysis.txt`, `report_analysis.txt`, `weight_plan.txt`
7. Implement remaining handlers: report, plan, meal_plan, restaurant
8. Write pytest suite in `tests/`

---

## Session 3 — 2026-05-07

### What was built
- `prompts/meal_analysis.txt`, `report_analysis.txt`, `weight_plan.txt` — all filled with structured, format-locked system prompts using `{placeholder}` injection
- `services/ai.py` — full implementation: `analyze_meal_photo` (vision), `analyze_lab_report` (vision), `generate_weight_plan` (text), `chat_response` (inline system prompt); lazy Anthropic client singleton, `_detect_media_type` for JPEG/PNG
- `handlers/meal_log.py` — `photo_meal_handler` (photo → AI → regex-parse calories → `log_meal` → reply) and `log_command_handler` (`/log <text>` → `chat_response` → reply)
- `main.py` updated — registered `filters.PHOTO → photo_meal_handler`, `CommandHandler("log") → log_command_handler`

### Key decisions
- `today_calories` fetched in handler and injected into user_profile dict before AI call (so prompt shows running daily total)
- Calories parsed from AI response via `re.compile(r"Calories:\s*(\d+)")` — prompt format enforces this line
- `meal_data` jsonb stores full `ai_response` string + parsed `calories` int
- `/log` command uses inline system prompt (too short to warrant a .txt file)

### Next steps
1. ~~Implement `handlers/report.py`~~ — done (Session 4)
2. ~~Implement `handlers/plan.py`~~ — done (Session 4)
3. Implement `handlers/meal_plan.py` — `/mealplan` → AI-generated day's meal suggestions within calorie target
4. Implement `handlers/restaurant.py` — restaurant menu help
5. Write `requirements.txt` and `.env.example`
6. Write pytest suite in `tests/`
7. Add Supabase column migration SQL for session 2's new `users` columns

---

## Session 5 — 2026-05-07

### What was built
- `services/ai.py`: added `generate_meal_plan(user_profile)` — builds system prompt dynamically from calorie_target, diet_preference, medical_conditions; forces table output format `DAY | MEAL | DESCRIPTION | APPROX KCAL`; max_tokens 1200
- `handlers/meal_plan.py`: `/mealplan` command; checks calorie_target + diet_preference are set; calls `ai.generate_meal_plan()`; replies with 7-day table
- `handlers/restaurant.py`: `/restaurant [name]` command + regex trigger on "eating out at" / "going to" in free text; extracts venue via `_extract_restaurant()`; fetches `get_today_calories` to compute remaining; builds context string; calls `ai.chat_response()`; reply includes 3 safe choices, 2 to avoid, 1 hack in <100 words
- `main.py`: added `CommandHandler("restaurant")` + `MessageHandler(TEXT & Regex("eating out at|going to"))` for restaurant trigger

### Key decisions
- `generate_meal_plan` prompt is built inline in ai.py (not a .txt file) because it's short and fully dynamic — consistent with the existing inline system prompt in `chat_response`
- Restaurant handler uses existing `chat_response()` with a structured user_message string rather than a new AI function — sufficient for the short, one-shot response needed
- `_extract_restaurant` regex returns "this restaurant" as fallback so the AI call always has some venue context

### Next steps
1. Wire up `CallbackQueryHandler` for `adjust_plan_yes` / `adjust_plan_no` inline keyboard callbacks (from report handler)
2. Write `requirements.txt` and `.env.example`
3. Write pytest suite in `tests/`
4. SQL migrations for `report_summaries` table and `users.current_plan` column

---

## Session 4 — 2026-05-07

### What was built
- `handlers/report.py`: handles PHOTO (with `/report` caption) and Document.PDF; extracts PDF first page via Pillow `Image.open().seek(0)`; calls `ai.analyze_lab_report()`; saves to `report_summaries` table; replies with inline Yes/No keyboard ("Want me to adjust your meal plan?")
- `handlers/plan.py`: `/plan` command; checks `_REQUIRED_FIELDS` for profile completeness; calls `ai.generate_weight_plan()`; stores plan text in `users.current_plan` via `update_user`
- `services/database.py`: added `save_report_summary(telegram_id, summary)` → inserts into `report_summaries` table
- `main.py`: added `MessageHandler(filters.Document.PDF, report_handler)` and `MessageHandler(filters.PHOTO & filters.CaptionRegex(r"^/report"), report_handler)` before the general PHOTO handler

### DB tables needed
- `report_summaries`: `telegram_id`, `summary` (text), `created_at` (timestamptz)
- `users`: add `current_plan` (text) column

### Next steps
1. Implement `handlers/meal_plan.py` — `/mealplan` → AI meal suggestions within calorie target
2. Implement `handlers/restaurant.py` — restaurant menu help
3. Wire up `CallbackQueryHandler` for `adjust_plan_yes` / `adjust_plan_no` inline keyboard callbacks
4. Write `requirements.txt` and `.env.example`
5. Write pytest suite in `tests/`
6. SQL migrations for `report_summaries` table and `users.current_plan` column

---

## Session 2 — 2026-05-07

### What was built
- `services/calculator.py`: Mifflin-St Jeor BMR, TDEE with 4 activity multipliers, calorie target (TDEE − 400), macros (1.8g/kg protein, 0.8g/kg fat, carbs from remainder)
- `handlers/start.py`: 9-state ConversationHandler for onboarding (name → age → gender → height → weight → target weight → activity → diet → medical); ReplyKeyboardMarkup for gender and activity; inline validation with re-prompt on bad input; calls calculator to set calorie_target on DB save; returning users get a calorie-status greeting
- `main.py`: updated to register `start_conversation` (ConversationHandler) instead of bare CommandHandler

### Key decisions
- All state handlers prefixed with `_` (module-private); only `start_conversation` is exported
- `create_user` called first with name only, then `update_user` for all profile fields — avoids a wide INSERT and reuses existing DB API
- `calorie_target` computed at onboarding completion and persisted; no runtime recalculation needed per-request
- `/cancel` fallback clears `user_data` and removes keyboard

### Users table — additional columns needed in Supabase
The following columns must be added to the `users` table (session 1 schema only had telegram_id, name, created_at):
`age` int, `gender` text, `height_cm` float, `weight_kg` float, `target_weight_kg` float, `activity_level` text, `diet_preference` text, `medical_conditions` text, `calorie_target` int

### Next steps
1. Add missing columns to Supabase `users` table (SQL migration)
2. Implement `services/ai.py` — prompt loader + `analyse_meal()` and `generate_report()` wrappers
3. Write `prompts/meal_analysis.txt` and `prompts/report_analysis.txt`
4. Implement `handlers/meal_log.py` — free-text → AI → log_meal → calorie reply
5. Implement `handlers/report.py` — daily/weekly summary via AI
6. Implement remaining handlers: plan, meal_plan, restaurant
7. Write `requirements.txt`, `.env.example`, pytest suite

---

## Session 6 — 2026-05-07 (Final)

### What was built
- `handlers/tests.py`: `/tests` command; fetches weight history (28 days) and computes kg/week loss rate; flags plateau if < 0.3 kg/week; fetches last report summary from DB; calls `ai.recommend_lab_tests()`; returns Priority 1 / Priority 2 tests with INR cost estimate
- `services/database.py`: added `get_last_report_summary(telegram_id)` — latest row from `report_summaries`
- `services/ai.py`: added `recommend_lab_tests(user_profile)` — loads `prompts/lab_tests.txt`, injects medical_conditions, weight_loss_rate, plateau_flag, last_report_markers
- `prompts/lab_tests.txt`: format-locked prompt; outputs Priority 1 / Priority 2 sections + INR cost table + notes
- `handlers/meal_log.py`: added `log_handler(update, context)` for free-text routing (uses `update.message.text`, calls `ai.chat_response()`)
- `main.py`: full rewrite — single `MessageHandler(PHOTO, photo_router)` where `photo_router` checks caption for "report"; single `MessageHandler(TEXT & ~COMMAND, smart_router)` where `smart_router` checks restaurant keywords then falls back to `log_handler`; `CallbackQueryHandler` for `adjust_plan_yes/no` wired up; `CommandHandler("tests")` added
- `requirements.txt`: pinned — anthropic==0.34.2, python-telegram-bot==20.7, supabase==2.5.3, python-dotenv==1.0.1, Pillow==10.4.0
- `systemd/weightwise.service`: systemd unit file; WorkingDirectory=/root/weightwise, EnvironmentFile=.env, Restart=on-failure

### Key decisions
- Plateau detection uses `datetime.fromisoformat()` (Python 3.11 stdlib) — no extra dependency
- `photo_router` and `smart_router` are defined in main.py as thin routing functions, not in handlers — keeps handlers single-responsibility
- `adjust_plan_callback` wired directly in main.py — routes Yes to `/mealplan` reminder, No to acknowledgement
- Restaurant detection regex in smart_router: `eating out|eating at|restaurant|cafe|going to`

### Pending for next session (Deployment)
1. **Supabase migrations** — run SQL to add missing `users` columns (age, gender, height_cm, weight_kg, target_weight_kg, activity_level, diet_preference, medical_conditions, calorie_target, current_plan) and create `report_summaries` table
2. **Deploy to VPS** — `scp` or `git clone` to `/root/weightwise`, create `venv`, `pip install -r requirements.txt`, copy `.env`
3. **Enable service** — `systemctl enable --now weightwise`, verify with `journalctl -u weightwise -f`
4. **End-to-end test** — run `/start` onboarding, log a meal photo, upload a PDF report, run `/tests`
5. **Write pytest suite** — unit tests for `_compute_plateau`, `_parse_calories`, `_extract_restaurant`
