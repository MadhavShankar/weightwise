import { View } from 'react-native'

interface CardProps {
  children: React.ReactNode
  className?: string
  tint?: 'white' | 'nutrition' | 'water' | 'fasting'
}

const tintClasses = {
  white: 'bg-white',
  nutrition: 'bg-nutrition-bg border border-nutrition-border',
  water: 'bg-water-bg border border-water-border',
  fasting: 'bg-fasting-bg border border-fasting-border',
}

export function Card({ children, className = '', tint = 'white' }: CardProps) {
  return (
    <View className={`rounded-2xl p-4 shadow-sm ${tintClasses[tint]} ${className}`}>
      {children}
    </View>
  )
}
