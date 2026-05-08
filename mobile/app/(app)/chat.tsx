import { useState, useRef } from 'react'
import { View, Text, TextInput, TouchableOpacity, FlatList, KeyboardAvoidingView, Platform, SafeAreaView, ActivityIndicator } from 'react-native'
import * as ImagePicker from 'expo-image-picker'
import { useCoach } from '@/hooks/useCoach'
import { MessageBubble } from '@/components/MessageBubble'
import { useTodayStore } from '@/stores/today'

export default function ChatScreen() {
  const { messages, streaming, send, clear } = useCoach()
  const [input, setInput] = useState('')
  const listRef = useRef<FlatList>(null)
  const { calories_consumed, calorie_target } = useTodayStore()

  async function handleSend() {
    if (!input.trim() || streaming) return
    const text = input.trim()
    setInput('')
    await send(text)
    listRef.current?.scrollToEnd({ animated: true })
  }

  async function pickImage() {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.7,
    })
    if (!result.canceled && result.assets[0]) {
      await send('Analyse this meal photo', result.assets[0].uri)
    }
  }

  async function openCamera() {
    const result = await ImagePicker.launchCameraAsync({ quality: 0.7 })
    if (!result.canceled && result.assets[0]) {
      await send('Analyse this meal photo', result.assets[0].uri)
    }
  }

  const calorieProgress = calorie_target ? calories_consumed / calorie_target : 0

  return (
    <SafeAreaView className="flex-1 bg-white">
      {/* Header */}
      <View className="flex-row items-center justify-between px-5 py-3 border-b border-gray-100">
        <Text className="text-lg font-bold text-gray-900">Coach</Text>
        <TouchableOpacity onPress={clear}>
          <Text className="text-brand text-sm font-medium">clear</Text>
        </TouchableOpacity>
      </View>

      {/* Messages */}
      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(m) => m.id}
        className="flex-1 px-4"
        contentContainerStyle={{ paddingVertical: 12, gap: 8 }}
        renderItem={({ item }) => <MessageBubble message={item} />}
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
        ListEmptyComponent={
          <View className="flex-1 items-center justify-center pt-20">
            <Text className="text-4xl mb-3">🏋️</Text>
            <Text className="text-gray-500 text-center">
              Hi! I'm your AI coach.{'\n'}Tell me what you ate, drank, or how you feel.
            </Text>
          </View>
        }
      />

      {/* Calorie progress strip */}
      {calorie_target > 0 && (
        <View className="mx-4 mb-1">
          <View className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <View className="h-full bg-brand rounded-full" style={{ width: `${Math.min(calorieProgress, 1) * 100}%` }} />
          </View>
          <Text className="text-xs text-gray-400 text-center mt-0.5">
            {calories_consumed} / {calorie_target} kcal today
          </Text>
        </View>
      )}

      {/* Input bar */}
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View className="flex-row items-end px-4 py-2 border-t border-gray-100 gap-2">
          <TouchableOpacity onPress={pickImage} className="p-2">
            <Text className="text-xl">📎</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={openCamera} className="p-2">
            <Text className="text-xl">📷</Text>
          </TouchableOpacity>
          <TextInput
            className="flex-1 bg-gray-100 rounded-2xl px-4 py-2.5 text-base max-h-28"
            placeholder="Type a message…"
            value={input}
            onChangeText={setInput}
            multiline
            onSubmitEditing={handleSend}
            blurOnSubmit={false}
          />
          <TouchableOpacity
            onPress={handleSend}
            disabled={!input.trim() || streaming}
            className="bg-brand rounded-2xl px-4 py-2.5 disabled:opacity-40"
          >
            {streaming ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Text className="text-white font-semibold">→</Text>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}
