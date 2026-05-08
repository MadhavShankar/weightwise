import { View, Text } from 'react-native'
import type { Message } from '@/hooks/useCoach'

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  return (
    <View className={`flex-row ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <View className="w-8 h-8 rounded-full bg-brand items-center justify-center mr-2 mt-1 shrink-0">
          <Text className="text-white text-sm font-bold">W</Text>
        </View>
      )}
      <View
        className={`max-w-[78%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-brand rounded-tr-sm'
            : 'bg-gray-100 rounded-tl-sm'
        }`}
      >
        <Text className={`text-sm leading-relaxed ${isUser ? 'text-white' : 'text-gray-800'}`}>
          {message.text}
        </Text>
      </View>
    </View>
  )
}
