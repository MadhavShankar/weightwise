import { Tabs } from 'expo-router'

export default function HistoryLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: true,
        headerTitle: 'History',
        tabBarStyle: { height: 44 },
        tabBarLabelStyle: { fontSize: 12, fontWeight: '600' },
        tabBarActiveTintColor: '#16a34a',
        tabBarInactiveTintColor: '#9ca3af',
      }}
    >
      <Tabs.Screen name="weight" options={{ title: 'Weight' }} />
      <Tabs.Screen name="meals" options={{ title: 'Meals' }} />
      <Tabs.Screen name="exercise" options={{ title: 'Exercise' }} />
      <Tabs.Screen name="water" options={{ title: 'Water' }} />
    </Tabs>
  )
}
