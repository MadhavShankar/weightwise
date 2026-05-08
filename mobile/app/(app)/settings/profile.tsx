import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, ActivityIndicator, Alert } from 'react-native'
import { router } from 'expo-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

const FIELDS = [
  { key: 'name', label: 'Name', type: 'default' },
  { key: 'age', label: 'Age', type: 'number-pad', unit: 'years' },
  { key: 'height_cm', label: 'Height', type: 'decimal-pad', unit: 'cm' },
  { key: 'weight_kg', label: 'Current Weight', type: 'decimal-pad', unit: 'kg' },
  { key: 'target_weight_kg', label: 'Target Weight', type: 'decimal-pad', unit: 'kg' },
  { key: 'diet_preference', label: 'Diet Preference', type: 'default' },
  { key: 'medical_conditions', label: 'Medical Conditions', type: 'default' },
] as const

export default function ProfileEditScreen() {
  const qc = useQueryClient()
  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: () => api.get<Record<string, unknown>>('/api/profile'),
  })

  const [values, setValues] = useState<Record<string, string>>({})
  const mutation = useMutation({
    mutationFn: (updates: Record<string, unknown>) => api.patch('/api/profile', updates),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profile'] })
      Alert.alert('Saved', 'Profile updated.')
      router.back()
    },
  })

  if (isLoading) return <ActivityIndicator color="#16a34a" className="mt-20" />

  function val(key: string) {
    return key in values ? values[key] : String(profile?.[key] ?? '')
  }

  function save() {
    const updates: Record<string, unknown> = {}
    for (const f of FIELDS) {
      if (f.key in values && values[f.key] !== String(profile?.[f.key] ?? '')) {
        updates[f.key] = ['age', 'height_cm', 'weight_kg', 'target_weight_kg'].includes(f.key)
          ? parseFloat(values[f.key]) : values[f.key]
      }
    }
    if (Object.keys(updates).length === 0) { router.back(); return }
    mutation.mutate(updates)
  }

  return (
    <ScrollView className="flex-1 bg-gray-50 px-4 pt-4">
      {FIELDS.map((f) => (
        <View key={f.key} className="mb-4">
          <Text className="text-sm font-semibold text-gray-600 mb-1">{f.label}</Text>
          <View className="flex-row items-center bg-white border border-gray-200 rounded-xl px-3 py-3">
            <TextInput
              className="flex-1 text-base text-gray-900"
              keyboardType={f.type as never}
              value={val(f.key)}
              onChangeText={(v) => setValues((p) => ({ ...p, [f.key]: v }))}
            />
            {'unit' in f && <Text className="text-gray-400 ml-1">{f.unit}</Text>}
          </View>
        </View>
      ))}

      <TouchableOpacity
        onPress={save}
        disabled={mutation.isPending}
        className="bg-brand rounded-xl py-3.5 items-center mb-8 disabled:opacity-50"
      >
        {mutation.isPending ? <ActivityIndicator color="#fff" /> : (
          <Text className="text-white font-semibold text-base">Save Changes</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  )
}
