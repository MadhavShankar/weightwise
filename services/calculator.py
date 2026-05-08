import logging

logger = logging.getLogger(__name__)

_ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
}


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if gender == "male" else base - 161


def calculate_tdee(bmr: float, activity_level: str) -> float:
    multiplier = _ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    return bmr * multiplier


def calculate_calorie_target(tdee: float, deficit: int = 400) -> int:
    return int(tdee - deficit)


def calculate_macros(calorie_target: int, weight_kg: float) -> dict:
    protein_g = round(1.8 * weight_kg)
    fat_g = round(0.8 * weight_kg)
    protein_kcal = protein_g * 4
    fat_kcal = fat_g * 9
    carbs_g = max(0, round((calorie_target - protein_kcal - fat_kcal) / 4))
    return {"protein_g": protein_g, "carbs_g": carbs_g, "fat_g": fat_g}
