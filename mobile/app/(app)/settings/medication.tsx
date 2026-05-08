import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, FlatList, ActivityIndicator, Alert } from 'react-native'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

interface MedSchedule {
  id: number
  medication_name: string
  frequency: string
  schedule_times: string
}

export default function MedicationScreen() {
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [frequency, setFrequency] = useState('')
  const [times, setTimes] = useState('')

  const { data: schedules = [], isLoading } = useQuery({
    queryKey: ['medication-schedules'],
    queryFn: () => api.get<MedSchedule[]>('/api/routines/medication'),
  })

  const addMutation = useMutation({
    mutationFn: () => api.post('/api/routines/medication', {
      medication_name: name,
      frequency,
      schedule_times: times,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['medication-schedules'] })
      setName(''); setFrequency(''); setTimes('')
    },
  })

  return (
    <View className="flex-1 bg-gray-50 px-4 pt-4">
      {/* Add form */}
      <View className="bg-white rounded-2xl p-4 shadow-sm mb-4">
        <Text className="text-base font-bold text-gray-800 mb-3">Add Medication</Text>
        {[
          { label: 'Medication name', value: name, set: setName, placeholder: 'e.g. Metformin' },
          { label: 'Frequency', value: frequency, set: setFrequency, placeholder: 'e.g. Twice daily' },
          { label: 'Times', value: times, set: setTimes, placeholder: 'e.g. 8:00 AM, 8:00 PM' },
        ].map((f) => (
          <View key={f.label} className="mb-3">
            <Text className="text-xs text-gray-500 mb-1">{f.label}</Text>
            <TextInput
              className="border border-gray-200 rounded-xl px-3 py-2.5 text-sm"
              placeholder={f.placeholder}
              value={f.value}
              onChangeText={f.set}
            />
          </View>
        ))}
        <TouchableOpacity
          onPress={() => addMutation.mutate()}
          disabled={!name || !frequency || !times || addMutation.isPending}
          className="bg-brand rounded-xl py-3 items-center disabled:opacity-50"
        >
          {addMutation.isPending ? <ActivityIndicator color="#fff" size="small" /> : (
            <Text className="text-white font-semibold">Add Schedule</Text>
          )}
        </TouchableOpacity>
      </View>

      {/* List */}
      {isLoading ? <ActivityIndicator color="#16a34a" /> : (
        <FlatList
          data={schedules}
          keyExtractor={(item) => item.id.toString()}
          contentContainerStyle={{ gap: 8 }}
          renderItem={({ item }) => (
            <View className="bg-white rounded-xl px-4 py-3 shadow-sm">
              <Text className="text-sm font-bold text-gray-900">💊 {item.medication_name}</Text>
              <Text className="text-xs text-gray-500 mt-1">{item.frequency} · {item.schedule_times}</Text>
            </View>
          )}
          ListEmptyComponent={<Text className="text-gray-400 text-center mt-4">No schedules yet</Text>}
        />
      )}
    </View>
  )
}
