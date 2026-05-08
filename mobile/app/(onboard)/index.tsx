import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ActivityIndicator, ScrollView } from 'react-native'
import { router } from 'expo-router'
import { useForm, Controller } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

const schema = z.object({
  name: z.string().min(1, 'Required'),
  age: z.coerce.number().int().min(10).max(120),
  gender: z.enum(['male', 'female']),
  height_cm: z.coerce.number().min(50).max(300),
  weight_kg: z.coerce.number().min(20).max(500),
  target_weight_kg: z.coerce.number().min(20).max(500),
  activity_level: z.enum(['sedentary', 'light', 'moderate', 'active']),
  diet_preference: z.string().min(1, 'Required'),
  medical_conditions: z.string().optional(),
})

type FormData = z.infer<typeof schema>

const STEPS = [
  { field: 'name', label: "What's your name?", placeholder: 'e.g. Ravi', type: 'text' },
  { field: 'age', label: 'How old are you?', placeholder: 'e.g. 28', type: 'numeric', hint: '10–120 years' },
  { field: 'gender', label: "What's your gender?", options: ['male', 'female'] },
  { field: 'height_cm', label: 'How tall are you?', placeholder: 'e.g. 172', type: 'numeric', unit: 'cm', hint: '50–300 cm' },
  { field: 'weight_kg', label: "What's your current weight?", placeholder: 'e.g. 80.5', type: 'decimal', unit: 'kg', hint: '20–500 kg' },
  { field: 'target_weight_kg', label: "What's your target weight?", placeholder: 'e.g. 70', type: 'decimal', unit: 'kg', hint: '20–500 kg' },
  { field: 'activity_level', label: "What's your activity level?", options: ['sedentary', 'light', 'moderate', 'active'] },
  { field: 'diet_preference', label: 'Any dietary preference?', placeholder: 'e.g. vegetarian, vegan, none', type: 'text' },
  { field: 'medical_conditions', label: 'Any medical conditions?', placeholder: 'e.g. diabetes, none', type: 'text', optional: true },
]

export default function OnboardWizard() {
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const setInternalId = useAuthStore((s) => s.setInternalId)

  const { control, handleSubmit, trigger, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { gender: 'male', activity_level: 'moderate', medical_conditions: '' },
  })

  const current = STEPS[step]
  const progress = ((step + 1) / STEPS.length) * 100

  async function nextStep() {
    const valid = await trigger(current.field as keyof FormData)
    if (!valid) return
    if (step < STEPS.length - 1) { setStep(step + 1); return }
    handleSubmit(submit)()
  }

  async function submit(data: FormData) {
    setLoading(true)
    try {
      const result = await api.post<{ calorie_target: number }>('/api/onboard', data)
      // Reload internal_id after onboard
      const me = await api.get<{ internal_id: number }>('/api/auth/me')
      if (me.internal_id) setInternalId(me.internal_id)
      router.replace('/(app)')
    } catch {
      setLoading(false)
    }
  }

  return (
    <View className="flex-1 bg-brand-light">
      {/* Progress bar */}
      <View className="px-6 pt-14 pb-4">
        <Text className="text-sm text-gray-500 mb-2">Step {step + 1} of {STEPS.length}</Text>
        <View className="h-2 bg-gray-200 rounded-full">
          <View className="h-2 bg-brand rounded-full" style={{ width: `${progress}%` }} />
        </View>
      </View>

      <ScrollView className="flex-1 px-6" keyboardShouldPersistTaps="handled">
        <Text className="text-2xl font-bold text-gray-900 mt-6 mb-6">{current.label}</Text>

        <View className="bg-white rounded-2xl p-5 shadow-sm">
          {current.options ? (
            <View className="gap-3">
              {current.options.map((opt) => (
                <Controller
                  key={opt}
                  control={control}
                  name={current.field as keyof FormData}
                  render={({ field }) => (
                    <TouchableOpacity
                      onPress={() => field.onChange(opt)}
                      className={`border-2 rounded-xl px-4 py-3 ${field.value === opt ? 'border-brand bg-brand-light' : 'border-gray-200'}`}
                    >
                      <Text className={`font-semibold capitalize ${field.value === opt ? 'text-brand-dark' : 'text-gray-700'}`}>
                        {opt}
                      </Text>
                    </TouchableOpacity>
                  )}
                />
              ))}
            </View>
          ) : (
            <Controller
              control={control}
              name={current.field as keyof FormData}
              render={({ field }) => (
                <View>
                  <View className="flex-row items-center border border-gray-200 rounded-xl px-3 py-3">
                    <TextInput
                      className="flex-1 text-base text-gray-900"
                      placeholder={current.placeholder}
                      keyboardType={current.type === 'numeric' ? 'number-pad' : current.type === 'decimal' ? 'decimal-pad' : 'default'}
                      value={field.value?.toString() ?? ''}
                      onChangeText={field.onChange}
                      autoFocus
                    />
                    {current.unit && <Text className="text-gray-400 font-medium ml-1">{current.unit}</Text>}
                  </View>
                  {current.hint && <Text className="text-xs text-gray-400 mt-1">{current.hint}</Text>}
                </View>
              )}
            />
          )}

          {errors[current.field as keyof FormData] && (
            <Text className="text-red-500 text-sm mt-2">
              {errors[current.field as keyof FormData]?.message as string}
            </Text>
          )}
        </View>

        {current.optional && (
          <TouchableOpacity onPress={() => { setStep((s) => s + 1) }} className="mt-3 items-center">
            <Text className="text-gray-400 text-sm">Skip this step</Text>
          </TouchableOpacity>
        )}
      </ScrollView>

      {/* Navigation */}
      <View className="flex-row px-6 pb-8 pt-4 gap-3">
        {step > 0 && (
          <TouchableOpacity
            onPress={() => setStep(step - 1)}
            className="flex-1 border-2 border-brand rounded-xl py-3.5 items-center"
          >
            <Text className="text-brand font-semibold">← Back</Text>
          </TouchableOpacity>
        )}
        <TouchableOpacity
          onPress={nextStep}
          disabled={loading}
          className="flex-1 bg-brand rounded-xl py-3.5 items-center disabled:opacity-50"
        >
          {loading ? <ActivityIndicator color="#fff" /> : (
            <Text className="text-white font-semibold">{step === STEPS.length - 1 ? 'Finish' : 'Next →'}</Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  )
}
