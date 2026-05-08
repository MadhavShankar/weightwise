import { View, Text } from 'react-native'

export function NotificationBadge({ count }: { count: number }) {
  if (count <= 0) return null
  return (
    <View className="absolute -top-1 -right-1 bg-red-500 rounded-full min-w-[18px] h-[18px] items-center justify-center px-1">
      <Text className="text-white text-xs font-bold">{count > 99 ? '99+' : count}</Text>
    </View>
  )
}
