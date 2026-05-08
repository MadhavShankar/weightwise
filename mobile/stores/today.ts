import { create } from 'zustand'

export interface MealEntry {
  id: number
  description: string
  calories: number
  logged_at: string
}

interface TodaySummary {
  name: string
  calories_consumed: number
  calorie_target: number
  water_ml: number
  water_goal_ml: number
  exercise_calories_burned: number
  streak: number
  meals: MealEntry[]
}

interface TodayStore extends TodaySummary {
  setToday: (summary: TodaySummary) => void
  appendMeal: (meal: MealEntry) => void
  addWater: (ml: number) => void
}

export const useTodayStore = create<TodayStore>((set) => ({
  name: '',
  calories_consumed: 0,
  calorie_target: 0,
  water_ml: 0,
  water_goal_ml: 2700,
  exercise_calories_burned: 0,
  streak: 0,
  meals: [],
  setToday: (summary) => set(summary),
  appendMeal: (meal) =>
    set((s) => ({
      meals: [...s.meals, meal],
      calories_consumed: s.calories_consumed + meal.calories,
    })),
  addWater: (ml) => set((s) => ({ water_ml: s.water_ml + ml })),
}))
