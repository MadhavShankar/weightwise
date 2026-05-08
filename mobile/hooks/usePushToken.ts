import { useEffect } from 'react'
import * as Notifications from 'expo-notifications'
import * as Device from 'expo-device'
import { Platform } from 'react-native'
import { api } from '@/lib/api'

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
})

export function usePushToken(internalId: number | null) {
  useEffect(() => {
    if (!internalId || !Device.isDevice) return

    async function register() {
      const { status: existing } = await Notifications.getPermissionsAsync()
      const { status } = existing === 'granted'
        ? { status: existing }
        : await Notifications.requestPermissionsAsync()

      if (status !== 'granted') return

      const { data: token } = await Notifications.getExpoPushTokenAsync()
      await api.post('/api/devices', {
        expo_push_token: token,
        platform: Platform.OS as 'ios' | 'android',
      })
    }

    register().catch(() => {})
  }, [internalId])
}
