import { Stack } from 'expo-router'

export default function SettingsLayout() {
  return (
    <Stack screenOptions={{ headerTintColor: '#16a34a', headerTitleStyle: { fontWeight: '700' } }}>
      <Stack.Screen name="index" options={{ title: 'Settings' }} />
      <Stack.Screen name="profile" options={{ title: 'Edit Profile' }} />
      <Stack.Screen name="medication" options={{ title: 'Medication Schedules' }} />
      <Stack.Screen name="exercise-routine" options={{ title: 'Exercise Routine' }} />
    </Stack>
  )
}
