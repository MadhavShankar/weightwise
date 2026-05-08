import { View, Text } from 'react-native'
import type { MealEntry } from '@/stores/today'

export function MealCard({ meal }: { meal: MealEntry }) {
  const time = new Date(meal.logged_at).toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <View className="flex-row items-center bg-white rounded-xl px-4 py-3 mb-2 shadow-sm">
      <View className="w-2 h-2 rounded-full bg-brand mr-3 shrink-0" />
      <View className="flex-1 mr-2">
        <Text className="text-sm text-gray-800 font-medium" numberOfLines={1}>
          {meal.description}
        </Text>
        <Text className="text-xs text-gray-400 mt-0.5">{time}</Text>
      </View>
      <View className="bg-nutrition-bg border border-nutrition-border rounded-full px-2.5 py-1">
        <Text className="text-xs font-bold text-green-700">{meal.calories} kcal</Text>
      </View>
    </View>
  )
}
