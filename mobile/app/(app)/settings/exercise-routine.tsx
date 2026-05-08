import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ActivityIndicator, Alert, ScrollView } from 'react-native'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

interface ExerciseRoutine {
  exercise_type: string
  frequency_per_week: number
  preferred_days: string
  notes: string
}

export default function ExerciseRoutineScreen() {
  const qc = useQueryClient()
  const { data: routine, isLoading } = useQuery({
    queryKey: ['exercise-routine'],
    queryFn: () => api.get<ExerciseRoutine | null>('/api/routines/exercise'),
  })

  const [type, setType] = useState(routine?.exercise_type ?? '')
  const [freq, setFreq] = useState(String(routine?.frequency_per_week ?? '3'))
  const [selectedDays, setSelectedDays] = useState<string[]>(
    routine?.preferred_days ? routine.preferred_days.split(',').map((d) => d.trim()) : []
  )
  const [notes, setNotes] = useState(routine?.notes ?? '')

  const saveMutation = useMutation({
    mutationFn: () => api.post('/api/routines/exercise', {
      exercise_type: type,
      frequency_per_week: parseInt(freq),
      preferred_days: selectedDays.join(', '),
      notes,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['exercise-routine'] })
      Alert.alert('Saved', 'Routine updated.')
    },
  })

  function toggleDay(day: string) {
    setSelectedDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    )
  }

  if (isLoading) return <ActivityIndicator color="#16a34a" className="mt-20" />

  return (
    <ScrollView className="flex-1 bg-gray-50 px-4 pt-4">
      <View className="bg-white rounded-2xl p-4 shadow-sm mb-4">
        <Text className="text-sm font-semibold text-gray-600 mb-1">Exercise Type</Text>
        <TextInput
          className="border border-gray-200 rounded-xl px-3 py-3 text-sm mb-4"
          placeholder="e.g. Running, Gym, Yoga"
          value={type}
          onChangeText={setType}
          defaultValue={routine?.exercise_type}
        />

        <Text className="text-sm font-semibold text-gray-600 mb-1">Days per week</Text>
        <TextInput
          className="border border-gray-200 rounded-xl px-3 py-3 text-sm mb-4"
          keyboardType="number-pad"
          value={freq}
          onChangeText={setFreq}
          maxLength={1}
        />

        <Text className="text-sm font-semibold text-gray-600 mb-2">Preferred Days</Text>
        <View className="flex-row flex-wrap gap-2 mb-4">
          {DAYS.map((d) => (
            <TouchableOpacity
              key={d}
              onPress={() => toggleDay(d)}
              className={`px-3 py-2 rounded-full border ${selectedDays.includes(d) ? 'bg-brand border-brand' : 'bg-white border-gray-200'}`}
            >
              <Text className={`text-xs font-semibold ${selectedDays.includes(d) ? 'text-white' : 'text-gray-600'}`}>{d}</Text>
            </TouchableOpacity>
          ))}
        </View>

        <Text className="text-sm font-semibold text-gray-600 mb-1">Notes</Text>
        <TextInput
          className="border border-gray-200 rounded-xl px-3 py-3 text-sm"
          placeholder="Optional notes"
          value={notes}
          onChangeText={setNotes}
          multiline
          numberOfLines={2}
        />
      </View>

      <TouchableOpacity
        onPress={() => saveMutation.mutate()}
        disabled={!type || saveMutation.isPending}
        className="bg-brand rounded-xl py-3.5 items-center mb-8 disabled:opacity-50"
      >
        {saveMutation.isPending ? <ActivityIndicator color="#fff" /> : (
          <Text className="text-white font-semibold">Save Routine</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  )
}
