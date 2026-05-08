# WeightWise Bot — CLAUDE.md

## Stack
- Python 3.11, python-telegram-bot v20 (async)
- Google Gemini API (gemini-2.0-flash) for all AI calls
- Supabase (PostgreSQL) for persistence
- python-dotenv for env vars
- Hosted on Hostinger VPS via systemd

## Project structure
handlers/ → one file per feature
services/ → ai.py, database.py, calculator.py
prompts/ → .txt system prompts (never inline in code)
main.py → entry point, registers handlers only

## Rules
- Never inline AI prompts in code — always load from prompts/*.txt
- Every handler must pull user profile from DB before calling AI
- No print() — use logging.info() only
- All AI calls go through services/ai.py — never call Gemini directly from handlers
- Env vars via os.getenv() only, never hardcoded
- Async throughout — no sync functions in handlers

## Do not read
node_modules/, .git/, __pycache__/, *.pyc, venv/

## Test command
python -m pytest tests/ -v