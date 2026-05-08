import { View, Text, TouchableOpacity, Switch, ScrollView, Alert } from 'react-native'
import { router } from 'expo-router'
import { useQuery, useMutation } from '@tanstack/react-query'
import { supabase } from '@/lib/supabase'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/lib/api'

function SettingsRow({ label, onPress, value }: { label: string; onPress?: () => void; value?: string }) {
  return (
    <TouchableOpacity onPress={onPress} className="flex-row items-center justify-between py-4 border-b border-gray-100">
      <Text className="text-base text-gray-800">{label}</Text>
      {value ? <Text className="text-gray-400 text-sm">{value}</Text> : <Text className="text-gray-300 text-base">›</Text>}
    </TouchableOpacity>
  )
}

export default function SettingsScreen() {
  const { signOut } = useAuthStore()

  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: () => api.get<{ notifications_paused: boolean; phone_number: string }>('/api/profile'),
  })

  const notifMutation = useMutation({
    mutationFn: (paused: boolean) => api.patch('/api/settings/notifications', { paused }),
  })

  async function handleSignOut() {
    Alert.alert('Sign out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign out',
        style: 'destructive',
        onPress: async () => {
          await supabase.auth.signOut()
          signOut()
        },
      },
    ])
  }

  return (
    <ScrollView className="flex-1 bg-gray-50">
      {/* Profile */}
      <View className="bg-white mx-4 mt-5 rounded-2xl px-4 shadow-sm">
        <Text className="text-xs font-bold text-gray-400 uppercase pt-4 pb-2">Profile</Text>
        <SettingsRow label="Edit Profile" onPress={() => router.push('/(app)/settings/profile')} />
        <SettingsRow
          label="Phone Number"
          value={profile?.phone_number ?? 'Not set'}
          onPress={() => router.push('/(app)/settings/profile')}
        />
      </View>

      {/* Health Routines */}
      <View className="bg-white mx-4 mt-4 rounded-2xl px-4 shadow-sm">
        <Text className="text-xs font-bold text-gray-400 uppercase pt-4 pb-2">Health Routines</Text>
        <SettingsRow label="Exercise Routine" onPress={() => router.push('/(app)/settings/exercise-routine')} />
        <SettingsRow label="Medication Schedules" onPress={() => router.push('/(app)/settings/medication')} />
      </View>

      {/* Notifications */}
      <View className="bg-white mx-4 mt-4 rounded-2xl px-4 shadow-sm">
        <Text className="text-xs font-bold text-gray-400 uppercase pt-4 pb-2">Notifications</Text>
        <View className="flex-row items-center justify-between py-4 border-b border-gray-100">
          <Text className="text-base text-gray-800">
            {profile?.notifications_paused ? 'Paused' : 'Active'}
          </Text>
          <Switch
            value={!profile?.notifications_paused}
            onValueChange={(val) => notifMutation.mutate(!val)}
            trackColor={{ true: '#16a34a', false: '#d1d5db' }}
            thumbColor="#fff"
          />
        </View>
      </View>

      {/* Account */}
      <View className="bg-white mx-4 mt-4 mb-8 rounded-2xl px-4 shadow-sm">
        <Text className="text-xs font-bold text-gray-400 uppercase pt-4 pb-2">Account</Text>
        <TouchableOpacity onPress={handleSignOut} className="py-4">
          <Text className="text-red-500 text-base font-medium">Sign Out</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}
