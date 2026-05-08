import { View } from 'react-native'

interface ProgressBarProps {
  progress: number   // 0–1
  color?: string
  height?: number
  className?: string
}

export function ProgressBar({ progress, color = '#16a34a', height = 8, className = '' }: ProgressBarProps) {
  const clamped = Math.min(Math.max(progress, 0), 1)
  return (
    <View className={`bg-gray-200 rounded-full overflow-hidden ${className}`} style={{ height }}>
      <View
        style={{ width: `${clamped * 100}%`, height, backgroundColor: color, borderRadius: 999 }}
      />
    </View>
  )
}
