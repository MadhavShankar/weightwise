import { View, Text, ScrollView, ActivityIndicator, Platform } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

const CartesianChart = Platform.OS !== 'web' ? require('victory-native').CartesianChart : null
const Bar = Platform.OS !== 'web' ? require('victory-native').Bar : null

interface WaterDayStat {
  date: string
  amount_ml: number
  goal_ml: number
}

export default function WaterHistoryScreen() {
  const { data = [], isLoading } = useQuery({
    queryKey: ['water-history'],
    queryFn: () => api.get<WaterDayStat[]>('/api/history/water?days=7'),
  })

  if (isLoading) return <ActivityIndicator color="#16a34a" className="mt-20" />

  const today = new Date().toISOString().slice(0, 10)
  const chartData = data.map((d, i) => ({
    idx: i,
    label: new Date(d.date).toLocaleDateString('en-IN', { weekday: 'short' }),
    amount: d.amount_ml,
  }))

  return (
    <ScrollView className="flex-1 bg-gray-50 px-4 pt-4">
      {chartData.length > 0 && Platform.OS !== 'web' ? (
        <View className="bg-white rounded-2xl shadow-sm overflow-hidden mb-4" style={{ height: 220 }}>
          <CartesianChart
            data={chartData}
            xKey="idx"
            yKeys={['amount']}
            domainPadding={{ left: 20, right: 20, top: 20 }}
            axisOptions={{
              formatXLabel: (v) => chartData[v]?.label ?? '',
              formatYLabel: (v) => `${v}`,
              labelColor: '#9ca3af',
              lineColor: '#e5e7eb',
            }}
          >
            {({ points, chartBounds }) => (
              <Bar
                points={points.amount}
                chartBounds={chartBounds}
                color="#93c5fd"
                roundedCorners={{ topLeft: 4, topRight: 4 }}
              />
            )}
          </CartesianChart>
          <Text className="text-xs text-center text-gray-400 pb-3">7-day water intake (ml)</Text>
        </View>
      ) : chartData.length === 0 ? (
        <View className="bg-white rounded-2xl p-8 items-center mb-4">
          <Text className="text-gray-400">No water logs yet</Text>
        </View>
      ) : null}

      {/* Daily list */}
      {data.map((d) => {
        const pct = Math.min(d.amount_ml / d.goal_ml, 1)
        const met = d.amount_ml >= d.goal_ml
        return (
          <View key={d.date} className="bg-white rounded-xl px-4 py-3 mb-2 shadow-sm">
            <View className="flex-row items-center justify-between mb-2">
              <Text className="text-sm font-semibold text-gray-700">
                {new Date(d.date).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })}
              </Text>
              <Text className={`text-xs font-bold ${met ? 'text-green-600' : 'text-blue-500'}`}>
                {d.amount_ml} / {d.goal_ml} ml {met ? '✓' : ''}
              </Text>
            </View>
            <View className="h-2 bg-blue-100 rounded-full">
              <View className="h-2 bg-blue-400 rounded-full" style={{ width: `${pct * 100}%` }} />
            </View>
          </View>
        )
      })}
    </ScrollView>
  )
}
