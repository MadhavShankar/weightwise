from typing import Optional
from pydantic import BaseModel, Field


class OnboardPayload(BaseModel):
    name: str
    age: int = Field(ge=10, le=120)
    gender: str = Field(pattern="^(male|female)$")
    height_cm: float = Field(ge=50, le=300)
    weight_kg: float = Field(ge=20, le=500)
    target_weight_kg: float = Field(ge=20, le=500)
    activity_level: str = Field(pattern="^(sedentary|light|moderate|active)$")
    diet_preference: str
    medical_conditions: Optional[str] = ""


class ProfilePatch(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = Field(None, ge=10, le=120)
    gender: Optional[str] = Field(None, pattern="^(male|female)$")
    height_cm: Optional[float] = Field(None, ge=50, le=300)
    weight_kg: Optional[float] = Field(None, ge=20, le=500)
    target_weight_kg: Optional[float] = Field(None, ge=20, le=500)
    activity_level: Optional[str] = Field(None, pattern="^(sedentary|light|moderate|active)$")
    diet_preference: Optional[str] = None
    medical_conditions: Optional[str] = None


class LinkByPhoneRequest(BaseModel):
    phone_number: str = Field(pattern=r"^\+\d{7,15}$")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class MealCorrectRequest(BaseModel):
    meal_id: int
    correction: str


class RestaurantRequest(BaseModel):
    place_name: str


class MealLogRequest(BaseModel):
    description: str


class WeightLogRequest(BaseModel):
    weight_kg: float = Field(ge=20, le=500)


class WaterLogRequest(BaseModel):
    amount_ml: Optional[int] = Field(None, ge=1)
    amount_text: Optional[str] = None


class ExerciseLogRequest(BaseModel):
    description: str


class MedicationLogRequest(BaseModel):
    text: str


class ExerciseRoutinePayload(BaseModel):
    exercise_type: str
    frequency_per_week: int = Field(ge=1, le=7)
    preferred_days: str
    notes: Optional[str] = ""


class MedicationSchedulePayload(BaseModel):
    medication_name: str
    frequency: str
    schedule_times: str


class NotificationsSettingRequest(BaseModel):
    paused: bool


class DeviceTokenRequest(BaseModel):
    expo_push_token: str
    platform: str = Field(pattern="^(ios|android)$")


class NotificationsReadRequest(BaseModel):
    ids: list[int]
