import { useState } from 'react'
import { View, Text, ScrollView, TouchableOpacity, ActivityIndicator, Platform } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

const CartesianChart = Platform.OS !== 'web' ? require('victory-native').CartesianChart : null
const Line = Platform.OS !== 'web' ? require('victory-native').Line : null
const Scatter = Platform.OS !== 'web' ? require('victory-native').Scatter : null

const RANGES = [30, 90, 365] as const

interface WeightHistory {
  entries: { weight_kg: number; logged_at: string }[]
  start_weight: number | null
  current_weight: number | null
  target_weight: number | null
}

export default function WeightHistoryScreen() {
  const [days, setDays] = useState<typeof RANGES[number]>(30)

  const { data, isLoading } = useQuery({
    queryKey: ['weight-history', days],
    queryFn: () => api.get<WeightHistory>(`/api/history/weight?days=${days}`),
  })

  const chartData = (data?.entries ?? []).map((e, i) => ({
    x: i + 1,
    weight: e.weight_kg,
  }))

  const lost = data?.start_weight && data?.current_weight
    ? +(data.start_weight - data.current_weight).toFixed(1)
    : 0
  const remaining = data?.current_weight && data?.target_weight
    ? +(data.current_weight - data.target_weight).toFixed(1)
    : 0

  return (
    <ScrollView className="flex-1 bg-gray-50 px-4 pt-4">
      {/* Range toggle */}
      <View className="flex-row gap-2 mb-4">
        {RANGES.map((r) => (
          <TouchableOpacity
            key={r}
            onPress={() => setDays(r)}
            className={`px-4 py-2 rounded-full border ${days === r ? 'bg-brand border-brand' : 'bg-white border-gray-200'}`}
          >
            <Text className={`text-sm font-semibold ${days === r ? 'text-white' : 'text-gray-600'}`}>
              {r === 365 ? 'All' : `${r}d`}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {isLoading ? (
        <ActivityIndicator color="#16a34a" className="mt-10" />
      ) : chartData.length > 1 && Platform.OS !== 'web' ? (
        <View className="bg-white rounded-2xl shadow-sm overflow-hidden mb-4" style={{ height: 220 }}>
          <CartesianChart
            data={chartData}
            xKey="x"
            yKeys={['weight']}
            domainPadding={{ left: 10, right: 10, top: 20 }}
            axisOptions={{
              formatXLabel: () => '',
              formatYLabel: (v) => `${v}`,
              labelColor: '#9ca3af',
              lineColor: '#e5e7eb',
            }}
          >
            {({ points }) => (
              <>
                <Line
                  points={points.weight}
                  color="#16a34a"
                  strokeWidth={2.5}
                  curveType="monotoneX"
                />
                <Scatter points={points.weight} radius={3} color="#16a34a" />
              </>
            )}
          </CartesianChart>
        </View>
      ) : !isLoading && chartData.length <= 1 ? (
        <View className="bg-white rounded-2xl p-8 items-center mb-4">
          <Text className="text-gray-400">No weight logs yet</Text>
        </View>
      ) : null}

      {/* Stats row */}
      <View className="flex-row gap-3 mb-6">
        {[
          { label: 'Start', value: data?.start_weight ? `${data.start_weight} kg` : '—' },
          { label: 'Now', value: data?.current_weight ? `${data.current_weight} kg` : '—' },
          { label: 'Goal', value: data?.target_weight ? `${data.target_weight} kg` : '—' },
        ].map((s) => (
          <View key={s.label} className="flex-1 bg-white rounded-xl p-3 items-center shadow-sm">
            <Text className="text-xs text-gray-500">{s.label}</Text>
            <Text className="text-base font-bold text-gray-900 mt-0.5">{s.value}</Text>
          </View>
        ))}
      </View>

      {lost > 0 && (
        <View className="bg-nutrition-bg border border-nutrition-border rounded-xl p-4 mb-6">
          <Text className="text-green-800 font-semibold text-center">
            Lost {lost} kg · {remaining > 0 ? `${remaining} kg remaining` : 'Goal reached!'}
          </Text>
        </View>
      )}
    </ScrollView>
  )
}
