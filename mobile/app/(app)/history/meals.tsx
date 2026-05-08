import { View, Text, SectionList, ActivityIndicator } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

interface MealEntry {
  id: number
  description: string
  calories: number
  logged_at: string
}

function groupByDate(entries: MealEntry[]): { title: string; data: MealEntry[] }[] {
  const map = new Map<string, MealEntry[]>()
  for (const e of entries) {
    const day = e.logged_at.slice(0, 10)
    if (!map.has(day)) map.set(day, [])
    map.get(day)!.push(e)
  }
  return Array.from(map.entries()).map(([title, data]) => ({ title, data }))
}

function formatDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', weekday: 'short' })
}

export default function MealHistoryScreen() {
  const { data = [], isLoading } = useQuery({
    queryKey: ['meal-history'],
    queryFn: () => api.get<MealEntry[]>('/api/history/meals?days=30'),
  })

  if (isLoading) return <ActivityIndicator color="#16a34a" className="mt-20" />

  const sections = groupByDate(data)

  return (
    <SectionList
      sections={sections}
      keyExtractor={(item) => item.id.toString()}
      className="flex-1 bg-gray-50"
      contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 16, paddingBottom: 32 }}
      renderSectionHeader={({ section: { title } }) => (
        <View className="flex-row items-center justify-between py-2">
          <Text className="text-sm font-bold text-gray-500 uppercase">{formatDate(title)}</Text>
        </View>
      )}
      renderItem={({ item }) => (
        <View className="bg-white rounded-xl px-4 py-3 mb-2 flex-row items-center justify-between shadow-sm">
          <View className="flex-1 mr-3">
            <Text className="text-sm font-medium text-gray-900" numberOfLines={2}>{item.description}</Text>
            <Text className="text-xs text-gray-400 mt-0.5">
              {new Date(item.logged_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
            </Text>
          </View>
          <View className="bg-nutrition-bg border border-nutrition-border rounded-full px-2.5 py-1">
            <Text className="text-xs font-bold text-green-700">{item.calories} kcal</Text>
          </View>
        </View>
      )}
      ListEmptyComponent={
        <View className="items-center pt-20">
          <Text className="text-4xl mb-3">🍽</Text>
          <Text className="text-gray-400">No meals logged yet</Text>
        </View>
      }
    />
  )
}
