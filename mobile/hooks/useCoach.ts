import { useCallback, useState } from 'react'
import EventSource, { type CustomEvent as SSEEvent } from 'react-native-sse'
import { supabase } from '@/lib/supabase'
import { useTodayStore, MealEntry } from '@/stores/today'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
}

const API_BASE = process.env.EXPO_PUBLIC_API_BASE_URL!

function updateLastAssistant(messages: Message[], text: string): Message[] {
  const last = messages[messages.length - 1]
  if (last?.role === 'assistant') {
    return [...messages.slice(0, -1), { ...last, text }]
  }
  return [...messages, { id: Date.now().toString(), role: 'assistant', text }]
}

export function useCoach() {
  const [messages, setMessages] = useState<Message[]>([])
  const [streaming, setStreaming] = useState(false)

  const send = useCallback(async (text: string, imageUri?: string) => {
    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), role: 'user', text },
    ])
    setStreaming(true)

    const { data } = await supabase.auth.getSession()
    const token = data.session?.access_token ?? ''

    let path = '/api/chat'
    let body: string | FormData = JSON.stringify({ message: text })
    let headers: Record<string, string> = {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    }

    if (imageUri) {
      path = '/api/chat/photo'
      const form = new FormData()
      form.append('file', { uri: imageUri, name: 'photo.jpg', type: 'image/jpeg' } as never)
      body = form
      headers = { Authorization: `Bearer ${token}` }
    }

    let buffer = ''
    const es = new EventSource<'token' | 'meal_logged' | 'done'>(`${API_BASE}${path}`, {
      headers,
      method: 'POST',
      body: body as string,
    })

    es.addEventListener('token', (e: SSEEvent<'token'>) => {
      const data = JSON.parse(e.data ?? '{}')
      buffer += data.text
      setMessages((prev) => updateLastAssistant(prev, buffer))
    })

    es.addEventListener('meal_logged', (e: SSEEvent<'meal_logged'>) => {
      const meal: MealEntry = JSON.parse(e.data ?? '{}')
      useTodayStore.getState().appendMeal(meal)
    })

    es.addEventListener('done', () => {
      setStreaming(false)
      buffer = ''
      es.close()
    })

    es.addEventListener('error', () => {
      setStreaming(false)
      buffer = ''
      es.close()
      setMessages((prev) =>
        updateLastAssistant(prev, 'Coach is temporarily unavailable. Please try again.')
      )
    })
  }, [])

  const clear = useCallback(() => setMessages([]), [])

  return { messages, streaming, send, clear }
}
