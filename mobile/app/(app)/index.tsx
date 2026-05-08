import { useState } from 'react'
import { View, Text, ScrollView, TouchableOpacity, SafeAreaView } from 'react-native'
import { useToday } from '@/hooks/useToday'
import { useTodayStore } from '@/stores/today'
import { ProgressBar } from '@/components/ProgressBar'
import { MealCard } from '@/components/MealCard'
import { QuickLogSheet } from '@/components/QuickLogSheet'

type LogType = 'meal' | 'weight' | 'water' | 'exercise' | 'medication' | null

const QUICK_ACTIONS = [
  { type: 'meal',       emoji: '🍽',  label: 'Meal' },
  { type: 'weight',     emoji: '⚖️',  label: 'Weight' },
  { type: 'water',      emoji: '💧',  label: 'Water' },
  { type: 'exercise',   emoji: '🏃',  label: 'Exercise' },
  { type: 'medication', emoji: '💊',  label: 'Medication' },
] as const

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

export default function DashboardScreen() {
  const { refresh } = useToday()
  const { name, calories_consumed, calorie_target, water_ml, water_goal_ml, exercise_calories_burned, streak, meals } = useTodayStore()
  const [activeLog, setActiveLog] = useState<LogType>(null)

  const caloriePercent = calorie_target ? calories_consumed / calorie_target : 0
  const waterPercent = water_goal_ml ? water_ml / water_goal_ml : 0
  const remaining = Math.max(0, calorie_target - calories_consumed)

  return (
    <SafeAreaView className="flex-1 bg-gray-50">
      <ScrollView className="flex-1" showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View className="px-5 pt-4 pb-3 flex-row items-center justify-between">
          <View>
            <Text className="text-xl font-bold text-gray-900">{greeting()}, {name || 'there'}</Text>
          </View>
          {streak > 0 && (
            <View className="flex-row items-center bg-orange-100 px-3 py-1.5 rounded-full">
              <Text className="text-lg">🔥</Text>
              <Text className="text-orange-600 font-bold ml-1">{streak}-day</Text>
            </View>
          )}
        </View>

        {/* Calories + Water cards */}
        <View className="flex-row px-5 gap-3 mb-3">
          <View className="flex-1 bg-nutrition-bg border border-nutrition-border rounded-2xl p-4">
            <Text className="text-xs font-semibold text-gray-500 uppercase mb-1">Calories</Text>
            <Text className="text-xl font-bold text-gray-900">{calories_consumed}</Text>
            <Text className="text-xs text-gray-500">/ {calorie_target} kcal</Text>
            <ProgressBar progress={caloriePercent} color="#16a34a" className="mt-2" />
            <Text className="text-xs text-gray-500 mt-1">{remaining} remaining</Text>
          </View>

          <View className="flex-1 bg-water-bg border border-water-border rounded-2xl p-4">
            <Text className="text-xs font-semibold text-gray-500 uppercase mb-1">Water</Text>
            <Text className="text-xl font-bold text-gray-900">{water_ml}</Text>
            <Text className="text-xs text-gray-500">/ {water_goal_ml} ml</Text>
            <ProgressBar progress={waterPercent} color="#3b82f6" className="mt-2" />
          </View>
        </View>

        {/* Exercise */}
        {exercise_calories_burned > 0 && (
          <View className="mx-5 mb-3 bg-fasting-bg border border-fasting-border rounded-2xl px-4 py-3 flex-row items-center">
            <Text className="text-lg mr-2">🏃</Text>
            <Text className="text-gray-700 font-medium">Exercise burned: <Text className="font-bold text-gray-900">{exercise_calories_burned} kcal</Text></Text>
          </View>
        )}

        {/* Today's meals */}
        {meals.length > 0 && (
          <View className="mx-5 mb-3">
            <Text className="text-base font-bold text-gray-900 mb-2">Today's Meals</Text>
            {meals.map((meal) => (
              <MealCard key={meal.id} meal={meal} />
            ))}
          </View>
        )}

        {/* Quick log */}
        <View className="mx-5 mb-6">
          <Text className="text-base font-bold text-gray-900 mb-3">Quick Log</Text>
          <View className="flex-row flex-wrap gap-2">
            {QUICK_ACTIONS.map((action) => (
              <TouchableOpacity
                key={action.type}
                onPress={() => setActiveLog(action.type)}
                className="bg-white border border-gray-200 rounded-xl px-4 py-2.5 flex-row items-center shadow-sm active:bg-gray-50"
              >
                <Text className="text-base mr-1.5">{action.emoji}</Text>
                <Text className="text-gray-700 font-medium text-sm">{action.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </ScrollView>

      <QuickLogSheet
        type={activeLog}
        onClose={() => setActiveLog(null)}
        onSuccess={refresh}
      />
    </SafeAreaView>
  )
}
