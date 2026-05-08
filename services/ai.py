import logging
import os
from pathlib import Path

import google.generativeai as genai

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_configured = False


def _configure() -> None:
    global _configured
    if not _configured:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        _configured = True


def _get_model(system_prompt: str | None = None) -> genai.GenerativeModel:
    _configure()
    return genai.GenerativeModel(MODEL, system_instruction=system_prompt)


def _load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _detect_mime_type(image_bytes: bytes) -> str:
    if image_bytes[:4] == b"\x89PNG":
        return "image/png"
    return "image/jpeg"


def analyze_meal_photo(image_bytes: bytes, user_profile: dict) -> str:
    system = _load_prompt("meal_analysis.txt").format(
        name=user_profile.get("name", "User"),
        calorie_target=user_profile.get("calorie_target", 2000),
        today_calories=user_profile.get("today_calories", 0),
        weight_kg=user_profile.get("weight_kg", 0),
        target_weight_kg=user_profile.get("target_weight_kg", 0),
        diet_preference=user_profile.get("diet_preference", "none"),
        current_streak=user_profile.get("current_streak", 0),
        eating_pattern_summary=user_profile.get("eating_pattern_summary") or "No patterns recorded yet.",
    )
    model = _get_model(system)
    response = model.generate_content(
        contents=[
            {"mime_type": _detect_mime_type(image_bytes), "data": image_bytes},
            "Analyze this meal.",
        ],
        generation_config={"max_output_tokens": 400},
    )
    return response.text


def analyze_meal_text(description: str, user_profile: dict) -> str:
    system = _load_prompt("meal_analysis.txt").format(
        name=user_profile.get("name", "User"),
        calorie_target=user_profile.get("calorie_target", 2000),
        today_calories=user_profile.get("today_calories", 0),
        weight_kg=user_profile.get("weight_kg", 0),
        target_weight_kg=user_profile.get("target_weight_kg", 0),
        diet_preference=user_profile.get("diet_preference", "none"),
        current_streak=user_profile.get("current_streak", 0),
        eating_pattern_summary=user_profile.get("eating_pattern_summary") or "No patterns recorded yet.",
    )
    model = _get_model(system)
    response = model.generate_content(
        contents=f"Analyze this meal (text description): {description}",
        generation_config={"max_output_tokens": 400},
    )
    return response.text


def analyze_lab_report(image_bytes: bytes) -> str:
    system = _load_prompt("report_analysis.txt")
    model = _get_model(system)
    response = model.generate_content(
        contents=[
            {"mime_type": _detect_mime_type(image_bytes), "data": image_bytes},
            "Analyze this lab report.",
        ],
        generation_config={"max_output_tokens": 600},
    )
    return response.text


def generate_weight_plan(user_profile: dict) -> str:
    system = _load_prompt("weight_plan.txt").format(
        name=user_profile.get("name", "User"),
        age=user_profile.get("age", 0),
        gender=user_profile.get("gender", ""),
        height_cm=user_profile.get("height_cm", 0),
        weight_kg=user_profile.get("weight_kg", 0),
        target_weight_kg=user_profile.get("target_weight_kg", 0),
        activity_level=user_profile.get("activity_level", ""),
        diet_preference=user_profile.get("diet_preference", "none"),
        medical_conditions=user_profile.get("medical_conditions", "none"),
        calorie_target=user_profile.get("calorie_target", 0),
        current_streak=user_profile.get("current_streak", 0),
        eating_pattern_summary=user_profile.get("eating_pattern_summary") or "No patterns recorded yet.",
    )
    model = _get_model(system)
    response = model.generate_content(
        contents="Generate my personalised weight-loss plan.",
        generation_config={"max_output_tokens": 800},
    )
    return response.text


def generate_meal_plan(user_profile: dict) -> str:
    calorie_target = user_profile.get("calorie_target", 2000)
    diet_preference = user_profile.get("diet_preference", "none")
    medical_conditions = user_profile.get("medical_conditions", "none")
    name = user_profile.get("name", "User")
    system = (
        f"You are a precise nutrition coach creating a 7-day meal plan for {name}. "
        f"Daily calorie target: {calorie_target} kcal. "
        f"Diet: {diet_preference}. Medical conditions: {medical_conditions}. "
        "Reply ONLY with a table in this exact format — no preamble, no closing remarks:\n\n"
        "DAY | MEAL | DESCRIPTION | APPROX KCAL\n\n"
        "Include Breakfast, Lunch, and Dinner for each of the 7 days. "
        f"Keep each day's total within 100 kcal of the {calorie_target} kcal target."
    )
    model = _get_model(system)
    response = model.generate_content(
        contents="Generate my 7-day meal plan.",
        generation_config={"max_output_tokens": 1200},
    )
    return response.text


def recommend_lab_tests(user_profile: dict) -> str:
    system = _load_prompt("lab_tests.txt").format(
        name=user_profile.get("name", "User"),
        medical_conditions=user_profile.get("medical_conditions", "none"),
        weight_loss_rate=user_profile.get("weight_loss_rate", 0.0),
        plateau_flag=user_profile.get("plateau_flag", False),
        last_report_markers=user_profile.get("last_report_markers", "none"),
    )
    model = _get_model(system)
    response = model.generate_content(
        contents="Recommend blood tests for me.",
        generation_config={"max_output_tokens": 600},
    )
    return response.text


def correct_meal_analysis(original_analysis: str, correction: str, user_profile: dict) -> str:
    system = _load_prompt("meal_correction.txt").format(
        calorie_target=user_profile.get("calorie_target", 2000),
        today_calories=user_profile.get("today_calories", 0),
    )
    model = _get_model(system)
    response = model.generate_content(
        contents=f"Original analysis:\n{original_analysis}\n\nUser correction: {correction}",
        generation_config={"max_output_tokens": 400},
    )
    return response.text


def coach_chat(user_message: str, user_profile: dict) -> str:
    system = _load_prompt("coach_chat.txt").format(
        name=user_profile.get("name", "User"),
        weight_kg=user_profile.get("weight_kg", 0),
        target_weight_kg=user_profile.get("target_weight_kg", 0),
        calorie_target=user_profile.get("calorie_target", 2000),
        today_calories=user_profile.get("today_calories", 0),
        exercise_calories=user_profile.get("exercise_calories", 0),
        water_ml=user_profile.get("water_ml", 0),
        current_streak=user_profile.get("current_streak", 0),
        medical_conditions=user_profile.get("medical_conditions", "none"),
        eating_pattern_summary=user_profile.get("eating_pattern_summary") or "No patterns recorded yet.",
    )
    model = _get_model(system)
    response = model.generate_content(
        contents=user_message,
        generation_config={"max_output_tokens": 400},
    )
    return response.text


def analyze_exercise(description: str, user_profile: dict) -> str:
    system = _load_prompt("exercise_log.txt").format(
        name=user_profile.get("name", "User"),
        weight_kg=user_profile.get("weight_kg", 70),
    )
    model = _get_model(system)
    response = model.generate_content(
        contents=f"Log this exercise: {description}",
        generation_config={"max_output_tokens": 200},
    )
    return response.text


def analyze_water(description: str) -> int:
    system = _load_prompt("water_log.txt")
    model = _get_model(system)
    response = model.generate_content(
        contents=description,
        generation_config={"max_output_tokens": 20},
    )
    try:
        return int(response.text.strip())
    except ValueError:
        return 250


def generate_morning_motivation(user_profile: dict, yesterday_stats: dict) -> str:
    system = _load_prompt("coach_morning.txt").format(
        name=user_profile.get("name", "User"),
        weight_kg=user_profile.get("weight_kg", 0),
        target_weight_kg=user_profile.get("target_weight_kg", 0),
        calorie_target=user_profile.get("calorie_target", 2000),
        current_streak=user_profile.get("current_streak", 0),
        longest_streak=user_profile.get("longest_streak", 0),
        eating_pattern_summary=user_profile.get("eating_pattern_summary") or "No patterns recorded yet.",
        yesterday_calories=yesterday_stats.get("calories", 0),
        yesterday_water_ml=yesterday_stats.get("water_ml", 0),
        yesterday_exercise_calories=yesterday_stats.get("exercise_calories", 0),
    )
    model = _get_model(system)
    response = model.generate_content(
        contents="Give me my morning motivation.",
        generation_config={"max_output_tokens": 300},
    )
    return response.text


def generate_evening_summary(user_profile: dict, daily_stats: dict) -> str:
    system = _load_prompt("coach_evening.txt").format(
        name=user_profile.get("name", "User"),
        weight_kg=user_profile.get("weight_kg", 0),
        target_weight_kg=user_profile.get("target_weight_kg", 0),
        calorie_target=user_profile.get("calorie_target", 2000),
        current_streak=daily_stats.get("current_streak", 0),
        longest_streak=user_profile.get("longest_streak", 0),
        milestone=daily_stats.get("milestone") or "",
        eating_pattern_summary=user_profile.get("eating_pattern_summary") or "No patterns recorded yet.",
        calories_in=daily_stats.get("calories_in", 0),
        exercise_calories=daily_stats.get("exercise_calories", 0),
        net_calories=daily_stats.get("net_calories", 0),
        water_ml=daily_stats.get("water_ml", 0),
        meal_count=daily_stats.get("meal_count", 0),
    )
    model = _get_model(system)
    response = model.generate_content(
        contents="Give me my evening summary.",
        generation_config={"max_output_tokens": 400},
    )
    return response.text


def extract_medication_name(text: str) -> str:
    system = _load_prompt("medication_extract.txt")
    model = _get_model(system)
    response = model.generate_content(
        contents=text,
        generation_config={"max_output_tokens": 15},
    )
    return response.text.strip().lower()


def analyze_eating_patterns(meal_history: list, user_profile: dict) -> str:
    meal_text = "\n".join(
        f"{row.get('logged_at', '')[:16]} — {row.get('description', '')} ({row.get('calories', 0)} kcal)"
        for row in meal_history
    )
    system = _load_prompt("pattern_analysis.txt").format(
        name=user_profile.get("name", "User"),
        weight_kg=user_profile.get("weight_kg", 0),
        target_weight_kg=user_profile.get("target_weight_kg", 0),
        calorie_target=user_profile.get("calorie_target", 2000),
        diet_preference=user_profile.get("diet_preference", "none"),
        meal_history=meal_text or "No meals logged in the past 7 days.",
    )
    model = _get_model(system)
    response = model.generate_content(
        contents="Analyze my eating patterns.",
        generation_config={"max_output_tokens": 300},
    )
    return response.text
