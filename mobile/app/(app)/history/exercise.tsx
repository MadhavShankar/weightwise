import { View, Text, FlatList, ActivityIndicator } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

interface ExerciseEntry {
  id: number
  description: string
  exercise_type: string
  duration_min: number
  calories_burned: number
  logged_at: string
}

export default function ExerciseHistoryScreen() {
  const { data = [], isLoading } = useQuery({
    queryKey: ['exercise-history'],
    queryFn: () => api.get<ExerciseEntry[]>('/api/history/exercise?days=30'),
  })

  if (isLoading) return <ActivityIndicator color="#16a34a" className="mt-20" />

  return (
    <FlatList
      data={data}
      keyExtractor={(item) => item.id.toString()}
      className="flex-1 bg-gray-50"
      contentContainerStyle={{ padding: 16, gap: 8 }}
      renderItem={({ item }) => (
        <View className="bg-white rounded-xl px-4 py-3 shadow-sm">
          <View className="flex-row items-center justify-between mb-1">
            <Text className="text-sm font-semibold text-gray-900 capitalize">{item.exercise_type}</Text>
            <View className="bg-fasting-bg border border-fasting-border rounded-full px-2.5 py-1">
              <Text className="text-xs font-bold text-yellow-700">{item.calories_burned} kcal</Text>
            </View>
          </View>
          <Text className="text-xs text-gray-500" numberOfLines={1}>{item.description}</Text>
          <Text className="text-xs text-gray-400 mt-1">
            {item.duration_min} min · {new Date(item.logged_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
          </Text>
        </View>
      )}
      ListEmptyComponent={
        <View className="items-center pt-20">
          <Text className="text-4xl mb-3">🏃</Text>
          <Text className="text-gray-400">No exercise logged yet</Text>
        </View>
      }
    />
  )
}
