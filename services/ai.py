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


def chat_response(user_message: str, user_profile: dict) -> str:
    system = (
        f"You are a concise weight-loss coach. "
        f"Client: {user_profile.get('name')}, "
        f"daily target {user_profile.get('calorie_target')} kcal, "
        f"goal {user_profile.get('target_weight_kg')} kg. "
        "Reply in 2-3 sentences max. Be specific — no generic advice."
    )
    model = _get_model(system)
    response = model.generate_content(
        contents=user_message,
        generation_config={"max_output_tokens": 200},
    )
    return response.text
