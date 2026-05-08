import { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity,
  ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView,
} from 'react-native'
import { router } from 'expo-router'
import { supabase } from '@/lib/supabase'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

const EMAIL_DOMAIN = '@ww.weightwise.in'

type Mode = 'signin' | 'signup'

function phoneToEmail(phone: string): string {
  const e164 = phone.startsWith('+') ? phone : `+91${phone}`
  return `${e164}${EMAIL_DOMAIN}`
}

export default function AuthScreen() {
  const [mode, setMode] = useState<Mode>('signin')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const setSession = useAuthStore((s) => s.setSession)
  const setInternalId = useAuthStore((s) => s.setInternalId)

  async function submit() {
    setError('')
    if (phone.length < 10) { setError('Enter a valid phone number.'); return }
    if (password.length < 6) { setError('Password must be at least 6 characters.'); return }

    const email = phoneToEmail(phone)
    setLoading(true)
    try {
      if (mode === 'signin') {
        const { data, error: err } = await supabase.auth.signInWithPassword({ email, password })
        if (err) { setError(err.message); return }
        setSession(data.session)
      } else {
        const { data, error: err } = await supabase.auth.signUp({ email, password })
        if (err) { setError(err.message); return }
        if (!data.session) {
          setError('Sign-up requires email confirmation. Ask your admin to disable it in Supabase Auth settings.')
          return
        }
        setSession(data.session)
      }

      // Resolve internal_id and onboarding state
      const me = await api.get<{ internal_id: number | null; onboarding_complete: boolean }>('/api/auth/me')
      if (me.internal_id) setInternalId(me.internal_id)
      router.replace(me.internal_id && me.onboarding_complete ? '/(app)' : '/(onboard)')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      className="flex-1 bg-brand-light"
    >
      <ScrollView contentContainerStyle={{ flexGrow: 1 }} keyboardShouldPersistTaps="handled">
        <View className="flex-1 justify-center px-6 py-12">
          {/* Header */}
          <View className="items-center mb-10">
            <Text className="text-4xl font-bold text-brand-dark">WeightWise</Text>
            <Text className="text-base text-gray-500 mt-1">Your AI Weight Coach</Text>
          </View>

          {/* Card */}
          <View className="bg-white rounded-2xl p-5 shadow-sm">
            {/* Mode toggle */}
            <View className="flex-row bg-gray-100 rounded-xl p-1 mb-5">
              {(['signin', 'signup'] as const).map((m) => (
                <TouchableOpacity
                  key={m}
                  onPress={() => { setMode(m); setError('') }}
                  className={`flex-1 py-2 rounded-lg items-center ${mode === m ? 'bg-white shadow-sm' : ''}`}
                >
                  <Text className={`text-sm font-semibold ${mode === m ? 'text-brand' : 'text-gray-400'}`}>
                    {m === 'signin' ? 'Sign In' : 'Create Account'}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Phone */}
            <Text className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              Phone Number
            </Text>
            <View className="flex-row items-center border border-gray-200 rounded-xl px-3 py-3 mb-4">
              <Text className="text-gray-500 font-medium mr-2">+91</Text>
              <View className="w-px h-5 bg-gray-200 mr-2" />
              <TextInput
                className="flex-1 text-base text-gray-900"
                placeholder="10-digit number"
                keyboardType="phone-pad"
                value={phone}
                onChangeText={setPhone}
                maxLength={10}
                autoComplete="tel"
                textContentType="telephoneNumber"
              />
            </View>

            {/* Password */}
            <Text className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
              Password
            </Text>
            <View className="border border-gray-200 rounded-xl px-3 py-3 mb-5">
              <TextInput
                className="text-base text-gray-900"
                placeholder={mode === 'signup' ? 'Create a password (min 6 chars)' : 'Your password'}
                secureTextEntry
                value={password}
                onChangeText={setPassword}
                autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                textContentType={mode === 'signup' ? 'newPassword' : 'password'}
                onSubmitEditing={submit}
              />
            </View>

            {error ? (
              <Text className="text-red-500 text-sm mb-3 text-center">{error}</Text>
            ) : null}

            <TouchableOpacity
              onPress={submit}
              disabled={loading}
              className="bg-brand rounded-xl py-3.5 items-center disabled:opacity-50"
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text className="text-white font-semibold text-base">
                  {mode === 'signin' ? 'Sign In' : 'Create Account'}
                </Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}
