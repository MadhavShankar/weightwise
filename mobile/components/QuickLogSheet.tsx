import { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, Modal,
  KeyboardAvoidingView, Platform, ActivityIndicator, TouchableWithoutFeedback,
} from 'react-native'
import { api } from '@/lib/api'
import { useTodayStore } from '@/stores/today'

type LogType = 'meal' | 'weight' | 'water' | 'exercise' | 'medication' | null

interface Props {
  type: LogType
  onClose: () => void
  onSuccess: () => void
}

const CONFIG = {
  meal:       { emoji: '🍽',  title: 'Log Meal',       placeholder: 'e.g. 2 idlis and sambar',    endpoint: '/api/log/meal',       field: 'description', keyboard: 'default' },
  weight:     { emoji: '⚖️', title: 'Log Weight',      placeholder: '80.5',                        endpoint: '/api/log/weight',     field: 'weight_kg',   keyboard: 'decimal-pad' },
  water:      { emoji: '💧',  title: 'Log Water',       placeholder: '500',                         endpoint: '/api/log/water',      field: 'amount_ml',   keyboard: 'number-pad' },
  exercise:   { emoji: '🏃',  title: 'Log Exercise',    placeholder: 'e.g. 30 min run',             endpoint: '/api/log/exercise',   field: 'description', keyboard: 'default' },
  medication: { emoji: '💊',  title: 'Log Medication',  placeholder: 'e.g. took my metformin',      endpoint: '/api/log/medication', field: 'text',        keyboard: 'default' },
} as const

const WATER_SHORTCUTS = [
  { label: '1 glass', ml: 250 },
  { label: '2 glasses', ml: 500 },
  { label: '500 ml', ml: 500 },
  { label: '1 L', ml: 1000 },
]

export function QuickLogSheet({ type, onClose, onSuccess }: Props) {
  const [value, setValue] = useState('')
  const [loading, setLoading] = useState(false)
  const addWater = useTodayStore((s) => s.addWater)

  if (!type) return null
  const config = CONFIG[type]

  async function submit(override?: string) {
    const v = override ?? value.trim()
    if (!v) return
    setLoading(true)
    try {
      const body: Record<string, unknown> = { [config.field]: config.field === 'weight_kg' || config.field === 'amount_ml' ? parseFloat(v) : v }
      const result = await api.post<{ amount_ml?: number }>(config.endpoint, body)
      if (type === 'water' && result.amount_ml) addWater(result.amount_ml)
      onSuccess()
      onClose()
    } catch (err) {
      // error shown inline if needed
    } finally {
      setLoading(false)
      setValue('')
    }
  }

  return (
    <Modal visible transparent animationType="slide" onRequestClose={onClose}>
      <TouchableWithoutFeedback onPress={onClose}>
        <View className="flex-1 bg-black/40 justify-end">
          <TouchableWithoutFeedback>
            <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
              <View className="bg-white rounded-t-3xl px-5 pt-5 pb-8">
                {/* Handle */}
                <View className="w-10 h-1 bg-gray-200 rounded-full self-center mb-4" />

                <Text className="text-lg font-bold text-gray-900 mb-4">
                  {config.emoji} {config.title}
                </Text>

                {/* Water shortcuts */}
                {type === 'water' && (
                  <View className="flex-row flex-wrap gap-2 mb-3">
                    {WATER_SHORTCUTS.map((s) => (
                      <TouchableOpacity
                        key={s.label}
                        onPress={() => submit(String(s.ml))}
                        className="bg-water-bg border border-water-border rounded-full px-3 py-1.5"
                      >
                        <Text className="text-blue-600 text-sm font-medium">{s.label}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                )}

                {/* Input */}
                <View className="flex-row items-center border border-gray-200 rounded-xl px-3 py-3 mb-4">
                  <TextInput
                    className="flex-1 text-base text-gray-900"
                    placeholder={config.placeholder}
                    keyboardType={config.keyboard as never}
                    value={value}
                    onChangeText={setValue}
                    autoFocus
                    onSubmitEditing={() => submit()}
                  />
                  {type === 'weight' && <Text className="text-gray-400 ml-2">kg</Text>}
                  {type === 'water' && <Text className="text-gray-400 ml-2">ml</Text>}
                </View>

                <TouchableOpacity
                  onPress={() => submit()}
                  disabled={!value.trim() || loading}
                  className="bg-brand rounded-xl py-3.5 items-center disabled:opacity-50"
                >
                  {loading ? <ActivityIndicator color="#fff" /> : (
                    <Text className="text-white font-semibold text-base">Log It</Text>
                  )}
                </TouchableOpacity>
              </View>
            </KeyboardAvoidingView>
          </TouchableWithoutFeedback>
        </View>
      </TouchableWithoutFeedback>
    </Modal>
  )
}
