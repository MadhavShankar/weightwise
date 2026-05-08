# WeightWise Mobile App — Requirements Specification

**Version:** 1.0  
**Date:** 2026-05-08  
**Status:** Ready for implementation

---

## Table of Contents

1. [Overview and Objectives](#1-overview-and-objectives)
2. [Confirmed Technical Foundation](#2-confirmed-technical-foundation)
3. [User Roles and Flows](#3-user-roles-and-flows)
4. [Authentication Architecture](#4-authentication-architecture)
5. [Identity Linking — Telegram ↔ Mobile](#5-identity-linking--telegram--mobile)
6. [UI/UX Screens and Flows](#6-uiux-screens-and-flows)
7. [Frontend Architecture](#7-frontend-architecture)
8. [Backend API Blueprint](#8-backend-api-blueprint)
9. [Database Changes](#9-database-changes)
10. [Push Notifications](#10-push-notifications)
11. [Error Handling and Logging](#11-error-handling-and-logging)
12. [Security Considerations](#12-security-considerations)
13. [Deployment Plan](#13-deployment-plan)
14. [Milestones and Acceptance Criteria](#14-milestones-and-acceptance-criteria)

---

## 1. Overview and Objectives

**Goal.** Build a React Native + Expo mobile application that delivers all WeightWise bot features — meal logging, weight tracking, exercise logging, water tracking, medication reminders, lab report analysis, meal planning, and AI coaching — accessible from a native mobile interface on iOS and Android.

**Relationship to the Telegram bot.** The bot continues running unchanged. Both clients share the same Supabase database and the same FastAPI backend. A user's data is identical whether they interact via Telegram or the mobile app.

**Non-goals.**
- No new health domain features beyond what the bot already supports.
- No modifications to existing AI prompts, calorie formulas, or bot behaviour.
- No admin panel or multi-tenancy.

---

## 2. Confirmed Technical Foundation

The following values are confirmed from the live Supabase project and must be used verbatim in all configuration files.

| Item | Value |
|------|-------|
| Supabase Project URL | `https://uopoejlphsqbzluhxmlp.supabase.co` |
| Supabase Publishable Key | `sb_publishable_0RmgkVJ5saIif_n_3zdZOA_jMVUZa01` |
| Supabase Legacy Anon Key | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (use publishable key for new code) |
| RLS status | Enabled on all 9 tables |
| Primary user identifier | `telegram_id` (bigint, unique) in `users` table |

**Existing confirmed tables (all with RLS):**
`users`, `meal_logs`, `weight_logs`, `exercise_logs`, `water_logs`, `medication_logs`, `medication_schedules`, `exercise_routines`, `report_summaries`

**New tables required** (specified in §9): `web_users`, `notifications`, `device_tokens`

**New column required:** `phone_number text UNIQUE` on `users`

---

## 3. User Roles and Flows

### 3.1 Roles

| Role | Condition |
|------|-----------|
| `new_user` | Authenticated, `onboarding_complete = false`, no linked Telegram profile |
| `linked_user` | Authenticated, linked to existing Telegram profile, `onboarding_complete = true` |
| `active_user` | Authenticated, completed mobile onboarding, `onboarding_complete = true` |

### 3.2 Top-Level Flow After Authentication

```
App Launch
    ↓
Is session valid? (expo-secure-store)
    ├── NO  → Auth Screen (Phone OTP or Google Sign-In)
    └── YES ↓
         Does web_users row exist for this auth UUID?
             ├── NO  → create web_users row → Phone Collection Screen
             └── YES ↓
                  Is internal_id linked to a telegram_id?
                      ├── YES → load profile → Dashboard
                      └── NO  → Phone Collection Screen
                                    ↓
                               phone matches users.phone_number?
                                   ├── YES → auto-link → Dashboard
                                   └── NO  → onboarding_complete?
                                                ├── YES → Dashboard
                                                └── NO  → Onboarding Wizard
```

### 3.3 Primary User Journeys

**Journey 1 — Existing Telegram user installs the app**
1. Opens app → signs in with phone OTP or Google.
2. Enters phone number → matches `users.phone_number` → auto-linked.
3. Lands on Dashboard with full history already populated. No re-onboarding.

**Journey 2 — New user (no Telegram history)**
1. Opens app → signs in with phone OTP or Google.
2. Enters phone number → no match found.
3. Completes 9-step onboarding wizard.
4. Lands on Dashboard with fresh profile.

**Journey 3 — Daily usage**
- Logs meals via free text, photo, or quick-log buttons.
- Views today's calorie / water / exercise progress.
- Receives push notifications for water nudges, medication reminders, morning motivation, evening summary.
- Browses history charts.
- Generates or views weight-loss plan and meal plan.

---

## 4. Authentication Architecture

### 4.1 Methods

Two sign-in methods are supported, both via native Supabase Auth. No passwords.

| Method | Mechanism | Primary use case |
|--------|-----------|-----------------|
| **Phone OTP** | User enters phone number → receives SMS code → Supabase verifies | Users already on the Telegram bot (phone is the linking key) |
| **Google Sign-In** | Expo AuthSession → Google OAuth → Supabase `signInWithIdToken` | Users who prefer Google; phone collected on next screen |

Both methods produce a standard Supabase JWT. The FastAPI backend validates the same JWT for all `/api/*` routes — no auth code changes needed on the backend.

### 4.2 Phone OTP Flow

```
User enters +91XXXXXXXXXX
    ↓
supabase.auth.signInWithOtp({ phone: '+91XXXXXXXXXX' })
    ↓ Supabase sends SMS via Twilio
User enters 6-digit code
    ↓
supabase.auth.verifyOtp({ phone, token, type: 'sms' })
    ↓
Session created → JWT stored in expo-secure-store
    ↓
Phone number already known → proceed to linking check
```

**Supabase configuration required (one-time):**
- Dashboard → Authentication → Providers → Phone → Enable
- Add Twilio account SID, auth token, and messaging service SID
- Set OTP expiry to 600 seconds

### 4.3 Google Sign-In Flow

```
User taps "Continue with Google"
    ↓
expo-auth-session opens in-app browser
    ↓
Google consent screen
    ↓
Redirect back to app with id_token
    ↓
supabase.auth.signInWithIdToken({ provider: 'google', token: id_token })
    ↓
Session created → JWT stored in expo-secure-store
    ↓
No phone number yet → Phone Collection Screen shown
```

**Required packages:**
```bash
npx expo install expo-auth-session expo-web-browser expo-crypto
```

**Required configuration:**
- Google Cloud Console → OAuth 2.0 credentials: Web client ID + iOS client ID + Android client ID
- Supabase Dashboard → Authentication → Providers → Google → paste Web client ID + secret
- Add `https://uopoejlphsqbzluhxmlp.supabase.co/auth/v1/callback` to Google's authorised redirect URIs

**Implementation:**
```typescript
// features/auth/useGoogleSignIn.ts
import * as WebBrowser from 'expo-web-browser'
import * as Google from 'expo-auth-session/providers/google'
import { supabase } from '@/lib/supabase'

WebBrowser.maybeCompleteAuthSession()

export function useGoogleSignIn() {
  const [_, response, promptAsync] = Google.useAuthRequest({
    webClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID,
    iosClientId: process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID,
    androidClientId: process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID,
  })

  useEffect(() => {
    if (response?.type === 'success') {
      supabase.auth.signInWithIdToken({
        provider: 'google',
        token: response.params.id_token,
      })
    }
  }, [response])

  return { promptAsync }
}
```

### 4.4 Supabase Client Setup (Mobile)

```typescript
// lib/supabase.ts
import { createClient } from '@supabase/supabase-js'
import * as SecureStore from 'expo-secure-store'
import { AppState } from 'react-native'

const ExpoSecureStoreAdapter = {
  getItem: (key: string) => SecureStore.getItemAsync(key),
  setItem: (key: string, value: string) => SecureStore.setItemAsync(key, value),
  removeItem: (key: string) => SecureStore.deleteItemAsync(key),
}

export const supabase = createClient(
  'https://uopoejlphsqbzluhxmlp.supabase.co',
  'sb_publishable_0RmgkVJ5saIif_n_3zdZOA_jMVUZa01',
  {
    auth: {
      storage: ExpoSecureStoreAdapter,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,
    },
  }
)

// Refresh session when app comes back to foreground
AppState.addEventListener('change', (state) => {
  if (state === 'active') supabase.auth.startAutoRefresh()
  else supabase.auth.stopAutoRefresh()
})
```

---

## 5. Identity Linking — Telegram ↔ Mobile

### 5.1 The Problem

Telegram identifies users by an integer `telegram_id` (tied to their phone number internally). The mobile app authenticates via Supabase Auth (UUID). These are different identity systems with no automatic bridge.

**The bridge: phone number.** Telegram bots can request a user's phone number once via a native contact-sharing button. The mobile app collects the same phone number at sign-in. Matching on phone number enables automatic, zero-friction linking.

### 5.2 Telegram Bot Change — Collect Phone Number

Add a new final step to the existing onboarding `ConversationHandler` in `handlers/start.py` that requests the user's phone number via Telegram's native contact button:

```python
# handlers/start.py — new state: ASK_PHONE (after ASK_MEDICAL)
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

async def ask_phone(update, context):
    keyboard = [[KeyboardButton("📱 Share My Phone Number", request_contact=True)]]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Last step! Share your phone number to enable mobile app access "
        "and keep your data in sync across devices.",
        reply_markup=markup,
    )
    return ASK_PHONE

async def save_phone(update, context):
    contact = update.message.contact
    if contact and contact.user_id == update.effective_user.id:
        phone = contact.phone_number
        if not phone.startswith('+'):
            phone = '+' + phone
        await db.update_user(update.effective_user.id, {'phone_number': phone})
    await update.message.reply_text(
        "You're all set! ...",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
```

For existing Telegram users (already onboarded), add a separate `/sharephone` command that runs the same contact-request flow.

### 5.3 Mobile App — Phone Collection Screen

Shown after every fresh sign-in until a phone number is on file:

```
┌─────────────────────────────────────────┐
│                                         │
│  What's your phone number?              │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │ +91  │  98765 43210              │   │
│  └──────────────────────────────────┘   │
│                                         │
│  Already use WeightWise on Telegram?    │
│  We'll import your profile and history  │
│  automatically.                         │
│                                         │
│              [ Continue ]               │
│                                         │
└─────────────────────────────────────────┘
```

If sign-in was via Phone OTP, the phone number is already known — this screen is skipped entirely and the lookup runs automatically.

### 5.4 Auto-Linking Logic

Called from `POST /api/auth/link-by-phone` immediately after the phone number is confirmed:

```
Input: { phone_number: '+91XXXXXXXXXX', auth_uuid: '<supabase UUID>' }

1. SELECT telegram_id FROM users WHERE phone_number = $phone_number
   
   ├── FOUND (existing Telegram user):
   │     UPDATE web_users SET internal_id = telegram_id
   │       WHERE auth_uuid = $auth_uuid
   │     DELETE FROM users WHERE telegram_id = temp_internal_id  -- remove empty temp row
   │     Return: { linked: true, profile: <full user profile> }
   │
   └── NOT FOUND (new user):
         The web_users.internal_id stays as the generated temp ID
         A users row was already created on web_users insert
         Return: { linked: false }  → proceed to onboarding wizard
```

After a successful link, the mobile app loads the full profile from the existing `users` row (all meals, weight logs, streaks, plans) and navigates directly to the Dashboard.

### 5.5 What Happens to the `telegram_id` Column

Nothing changes. The column is renamed conceptually to "internal user ID" — it stores a Telegram-sourced integer for Telegram users, and a generated integer (starting at `9_000_000_000` to avoid collision with Telegram IDs) for mobile-only users. All existing queries in `services/database.py` continue to work without modification.

---

## 6. UI/UX Screens and Flows

### 6.1 Navigation Structure

```
App
├── Auth Stack (unauthenticated)
│   ├── AuthScreen         — Phone OTP or Google Sign-In choice
│   ├── OtpVerifyScreen    — 6-digit SMS code entry
│   └── PhoneCollectScreen — Phone number entry (Google users only)
│
├── Onboard Stack (authenticated, not onboarded)
│   └── OnboardScreen      — 9-step wizard (one screen, step state managed internally)
│
└── App Stack (authenticated + onboarded) — Bottom Tab Navigator
    ├── Tab: Today         — DashboardScreen
    ├── Tab: Chat          — ChatScreen
    ├── Tab: History       — HistoryNavigator (Weight / Meals / Exercise / Water)
    └── Tab: Settings      — SettingsNavigator (Profile / Medication / Exercise / Notifications)
        + Modal: PlanScreen
        + Modal: MealPlanScreen
        + Modal: ReportsScreen
        + Modal: BloodTestsScreen
        + Modal: RestaurantScreen
```

### 6.2 Auth Screen

```
┌─────────────────────────────────────────┐
│                                         │
│           WeightWise                    │
│      Your AI Weight Coach               │
│                                         │
│   ┌───────────────────────────────┐     │
│   │  +91  │  Enter phone number   │     │
│   └───────────────────────────────┘     │
│             [ Send OTP ]                │
│                                         │
│           ── or ──                      │
│                                         │
│   ┌───────────────────────────────┐     │
│   │  G  Continue with Google      │     │
│   └───────────────────────────────┘     │
│                                         │
└─────────────────────────────────────────┘
```

### 6.3 Onboarding Wizard

Single screen with animated step transitions. Progress bar at top shows step N of 9.

```
Step 4 of 9  ████████████░░░░░░░░░░ (44%)

  How tall are you?

  ┌─────────────────────┐
  │  172                │  cm
  └─────────────────────┘

  Validate: 50–300 cm

         [← Back]    [Next →]
```

Steps:
1. Name (text)
2. Age (number, 10–120)
3. Gender (radio: Male / Female)
4. Height in cm (number, 50–300)
5. Current weight in kg (number, 20–500)
6. Target weight in kg (number, 20–500)
7. Activity level (radio: Sedentary / Light / Moderate / Active)
8. Diet preference (text, free-form)
9. Medical conditions (text, free-form, skippable)

On final step submit: `POST /api/onboard` → response includes calorie target → navigate to Dashboard.

### 6.4 Dashboard Screen

```
┌─────────────────────────────────────────┐
│  Good morning, Ravi        🔥 7-day     │
├─────────────────────────────────────────┤
│                                         │
│  Calories          Water                │
│  1340 / 1800 kcal  1200 / 2700 ml      │
│  ▓▓▓▓▓▓▓░░░░       ▓▓▓▓░░░░░░░        │
│                                         │
│  Exercise burned: 280 kcal              │
│                                         │
├─────────────────────────────────────────┤
│  Today's Meals                          │
│  ● Breakfast  Idli × 2      180 kcal   │
│  ● Lunch      Dal rice      450 kcal   │
│  ● Snack      Banana        90 kcal    │
├─────────────────────────────────────────┤
│  Quick Log                              │
│  [🍽 Meal] [⚖ Weight] [💧 Water]       │
│  [🏃 Exercise] [💊 Medication]          │
│  [🍽 Restaurant] [📋 Plan] [🩺 Tests]  │
└─────────────────────────────────────────┘
```

Quick-log buttons open bottom sheets with appropriate inputs.

### 6.5 Chat Screen

```
┌─────────────────────────────────────────┐
│  Coach                          [clear] │
├─────────────────────────────────────────┤
│                                         │
│  [Coach]  Good morning! Yesterday       │
│  you hit 1750 kcal. Great work.         │
│                                         │
│           [User] I had 2 idlis  07:45   │
│                                         │
│  [Coach]  Logged: 2 Idlis — 180 kcal   │
│  Remaining today: 1620 kcal 💪          │
│                                         │
│  ───── Today: 1340 / 1800 kcal ─────   │
│                                         │
├───────────────────────────────┬─────────┤
│  📎  📷                       │   →    │
│  Type a message…              │  Send  │
└───────────────────────────────┴─────────┘
```

- Attachment button (📎): opens picker for PDF (lab report)
- Camera button (📷): opens `expo-image-picker` for meal photo
- Coach replies stream character-by-character via SSE
- A thin calorie progress bar persists at the bottom of the message list

### 6.6 History Screens

**Weight History**
```
┌─────────────────────────────────────────┐
│  Weight History        [30d] [90d] [All]│
├─────────────────────────────────────────┤
│  kg                                     │
│  84 •                                   │
│  83   •──•                              │
│  82       •──•──•                       │
│  81              •──•                   │
│     Week 1   Week 2   Week 3            │
├─────────────────────────────────────────┤
│  Start 84 kg │ Now 81 kg │ Goal 75 kg  │
│  Lost 3 kg   │ 6 kg remaining          │
└─────────────────────────────────────────┘
```

**Meal Log**
Reverse-chronological list grouped by date. Each entry shows food name, calories badge, and time. Tap to expand AI breakdown.

**Water Chart**
7-day bar chart. Each bar shows daily intake vs goal. Today's bar highlighted.

**Exercise Log**
List view: exercise type, duration, calories burned, time.

### 6.7 Quick-Log Bottom Sheets

Each quick-log button opens a modal bottom sheet:

**Weight log:**
```
  Log Weight
  ┌────────────────┐
  │  81.4          │  kg
  └────────────────┘
       [ Log It ]
```

**Water log:**
```
  Log Water
  ○ Glasses   ● ml
  ┌────────────────┐
  │  500           │  ml
  └────────────────┘
  Shortcuts: [1 glass] [2 glasses] [500ml] [1L]
       [ Log It ]
```

**Meal log / exercise / medication:** text input field with keyboard auto-shown.

### 6.8 Settings Screen

```
Profile
  › Edit Profile (all 9 onboarding fields)
  › Phone Number (shows current, allows update)

Health Routines
  › Exercise Routine
  › Medication Schedules

Notifications
  › Pause / Resume  [toggle]

Account
  › Telegram Link Status  (Linked as @username / Not linked)
  › Sign Out
```

---

## 7. Frontend Architecture

### 7.1 Technology Stack

| Concern | Choice |
|---------|--------|
| Framework | React Native 0.74 + Expo SDK 51 |
| Language | TypeScript (strict mode) |
| Routing | Expo Router v3 (file-based) |
| State | Zustand 4 |
| Data fetching | TanStack Query v5 |
| Forms | React Hook Form + Zod |
| Styling | NativeWind v4 (Tailwind CSS syntax on React Native) |
| Charts | `victory-native` |
| File / image | `expo-image-picker`, `expo-document-picker` |
| SSE streaming | `react-native-sse` (drop-in `EventSource` polyfill) |
| Push notifications | `expo-notifications` |
| Auth token storage | `expo-secure-store` |
| Supabase SDK | `@supabase/supabase-js` with SecureStore adapter |
| Build / distribution | Expo EAS Build |

### 7.2 Project Structure

```
mobile/
├── app/
│   ├── (auth)/
│   │   ├── _layout.tsx
│   │   ├── index.tsx          ← AuthScreen (phone + Google)
│   │   ├── verify.tsx         ← OtpVerifyScreen
│   │   └── phone.tsx          ← PhoneCollectScreen (Google users)
│   ├── (onboard)/
│   │   ├── _layout.tsx
│   │   └── index.tsx          ← OnboardWizard
│   ├── (app)/
│   │   ├── _layout.tsx        ← Bottom tab navigator + AuthGuard
│   │   ├── index.tsx          ← DashboardScreen
│   │   ├── chat.tsx           ← ChatScreen
│   │   ├── history/
│   │   │   ├── _layout.tsx    ← Top tab navigator
│   │   │   ├── weight.tsx
│   │   │   ├── meals.tsx
│   │   │   ├── exercise.tsx
│   │   │   └── water.tsx
│   │   └── settings/
│   │       ├── _layout.tsx
│   │       ├── index.tsx
│   │       ├── profile.tsx
│   │       ├── medication.tsx
│   │       └── exercise-routine.tsx
│   └── _layout.tsx            ← Root layout, session listener
├── components/
│   ├── Button.tsx
│   ├── Card.tsx
│   ├── ProgressBar.tsx
│   ├── MessageBubble.tsx
│   ├── MealCard.tsx
│   ├── QuickLogSheet.tsx
│   └── NotificationBadge.tsx
├── features/
│   ├── auth/
│   ├── onboard/
│   ├── dashboard/
│   ├── chat/
│   ├── history/
│   ├── plans/
│   ├── reports/
│   └── settings/
├── stores/
│   ├── auth.ts                ← { user, session, internalId }
│   └── today.ts               ← { calories, water, meals, streak } — reset at midnight
├── hooks/
│   ├── useCoach.ts            ← SSE streaming via react-native-sse
│   ├── useToday.ts            ← Fetches TodaySummary on mount + focus
│   └── usePushToken.ts        ← Registers Expo push token on mount
├── lib/
│   ├── supabase.ts            ← Client (see §4.4)
│   └── api.ts                 ← Base fetch with Bearer token injection
├── app.json
├── eas.json
├── tailwind.config.js
└── babel.config.js
```

### 7.3 NativeWind Setup

```bash
npm install nativewind
npm install -D tailwindcss@3.3.2
npx tailwindcss init
```

`tailwind.config.js`:
```js
module.exports = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './features/**/*.{ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: '#16a34a', light: '#dcfce7', dark: '#15803d' },
      },
    },
  },
}
```

`babel.config.js`:
```js
module.exports = { presets: ['babel-preset-expo'], plugins: ['nativewind/babel'] }
```

### 7.4 State Management

```typescript
// stores/auth.ts
interface AuthStore {
  session: Session | null
  internalId: number | null   // mapped from web_users after JWT verification
  setSession: (s: Session | null) => void
  setInternalId: (id: number) => void
  signOut: () => void
}

// stores/today.ts  — reset at local midnight via useToday hook
interface TodayStore {
  caloriesConsumed: number
  calorieTarget: number
  waterMl: number
  waterGoalMl: number
  exerciseCaloriesBurned: number
  streak: number
  meals: MealEntry[]
  setToday: (summary: TodaySummary) => void
  appendMeal: (meal: MealEntry) => void
  addWater: (ml: number) => void
}
```

TanStack Query handles all server state (history, plans, reports, routines). Zustand stores only the auth identity and the today snapshot.

### 7.5 SSE Streaming Hook

```typescript
// hooks/useCoach.ts
import EventSource from 'react-native-sse'
import { useAuthStore } from '@/stores/auth'

export function useCoach() {
  const [messages, setMessages] = useState<Message[]>([])
  const [streaming, setStreaming] = useState(false)
  const session = useAuthStore(s => s.session)

  const send = useCallback((text: string, attachment?: { uri: string; type: 'image' | 'pdf' }) => {
    setStreaming(true)
    const es = new EventSource(`${API_BASE}/api/chat`, {
      headers: { Authorization: `Bearer ${session?.access_token}` },
      method: 'POST',
      body: JSON.stringify({ message: text }),
    })

    let buffer = ''
    es.addEventListener('token', (e) => {
      buffer += JSON.parse(e.data).text
      setMessages(prev => updateLastAssistantMessage(prev, buffer))
    })
    es.addEventListener('meal_logged', (e) => {
      const meal = JSON.parse(e.data)
      useTodayStore.getState().appendMeal(meal)
    })
    es.addEventListener('done', () => {
      setStreaming(false)
      es.close()
    })
    es.addEventListener('error', () => {
      setStreaming(false)
      es.close()
    })
  }, [session])

  return { messages, streaming, send }
}
```

### 7.6 Environment Variables

All `EXPO_PUBLIC_*` variables are safe to bundle in the client. Never expose `GEMINI_API_KEY` or `SUPABASE_SERVICE_KEY` to the mobile app.

```env
# mobile/.env
EXPO_PUBLIC_SUPABASE_URL=https://uopoejlphsqbzluhxmlp.supabase.co
EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_0RmgkVJ5saIif_n_3zdZOA_jMVUZa01
EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=<from Google Cloud Console>
EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID=<from Google Cloud Console>
EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID=<from Google Cloud Console>
EXPO_PUBLIC_API_BASE_URL=https://api.weightwise.in
```

---

## 8. Backend API Blueprint

### 8.1 Technology Stack

| Concern | Choice |
|---------|--------|
| Framework | FastAPI 0.111 |
| Language | Python 3.11 (same as bot) |
| Server | Uvicorn + Gunicorn (2 workers) |
| Auth | Supabase JWT verification via `python-jose` |
| AI / DB | `services/ai.py` and `services/database.py` imported directly |
| File handling | `python-multipart`, `PyMuPDF` (reused from bot) |
| Streaming | FastAPI `StreamingResponse` (Server-Sent Events) |

The FastAPI app lives in `web_api/` at the repo root. It imports from `services/` via a symlink — no code duplication.

### 8.2 Auth Middleware

Every `/api/*` route passes through `verify_token()`:

```python
# web_api/middleware/auth.py
from jose import jwt
import httpx

SUPABASE_URL = 'https://uopoejlphsqbzluhxmlp.supabase.co'

async def verify_token(authorization: str = Header(...)) -> dict:
    token = authorization.removeprefix('Bearer ')
    jwks = await fetch_supabase_jwks()           # cached, refreshed hourly
    payload = jwt.decode(token, jwks, algorithms=['RS256'],
                         audience='authenticated')
    return payload  # payload['sub'] = Supabase UUID
```

The `sub` claim (Supabase UUID) is resolved to `internal_id` via `web_users` table on every request. This is the only ID used in all downstream DB calls.

### 8.3 Endpoint Catalog

#### Auth / Linking

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/api/auth/link-by-phone` | `{ phone_number }` | `{ linked: bool, profile?: UserProfile }` |
| GET | `/api/auth/me` | — | `{ internal_id, linked_telegram_id?, onboarding_complete }` |

#### Onboarding & Profile

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/api/onboard` | `OnboardPayload` | `{ calorie_target, macros }` |
| GET | `/api/profile` | — | `UserProfile` |
| PATCH | `/api/profile` | Partial `OnboardPayload` | `UserProfile` |

`OnboardPayload`:
```json
{
  "name": "Ravi",
  "age": 32,
  "gender": "male",
  "height_cm": 172.0,
  "weight_kg": 84.0,
  "target_weight_kg": 75.0,
  "activity_level": "moderate",
  "diet_preference": "vegetarian",
  "medical_conditions": "type 2 diabetes"
}
```

#### Today & Dashboard

| Method | Path | Response |
|--------|------|----------|
| GET | `/api/today/summary` | `TodaySummary` |

```json
{
  "calories_consumed": 1340,
  "calorie_target": 1800,
  "water_ml": 1200,
  "water_goal_ml": 2700,
  "exercise_calories_burned": 280,
  "streak": 7,
  "meals": [...]
}
```

#### Chat / Coach

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/api/chat` | `{ message: string }` | SSE stream |
| POST | `/api/chat/photo` | `multipart: file (image)` | SSE stream |
| POST | `/api/chat/report` | `multipart: file (image/PDF)` | `ReportResult` |
| POST | `/api/meal/correct` | `{ meal_id, correction }` | `MealEntry` |
| POST | `/api/restaurant` | `{ place_name }` | SSE stream |

SSE event types:
```
event: token        data: { "text": "Logged: 2 Idlis" }
event: meal_logged  data: { "meal_id": 42, "calories": 180, "description": "2 Idlis" }
event: done         data: {}
event: error        data: { "code": "AI_PARSE_FAILED", "message": "..." }
```

#### Quick Logs

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/api/log/meal` | `{ description }` | `MealEntry` |
| POST | `/api/log/weight` | `{ weight_kg }` | `WeightEntry` |
| POST | `/api/log/water` | `{ amount_ml }` or `{ amount_text }` | `WaterStatus` |
| POST | `/api/log/exercise` | `{ description }` | `ExerciseEntry` |
| POST | `/api/log/medication` | `{ text }` | `MedicationEntry` |

#### History

| Method | Path | Query | Response |
|--------|------|-------|----------|
| GET | `/api/history/meals` | `days=7` | `MealEntry[]` |
| GET | `/api/history/weight` | `days=30` | `WeightEntry[]` |
| GET | `/api/history/exercise` | `days=7` | `ExerciseEntry[]` |
| GET | `/api/history/water` | `days=7` | `WaterDayStat[]` |

#### Plans & Reports

| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | `/api/plan` | — | `{ plan: string }` |
| POST | `/api/plan/generate` | — | `{ plan: string }` |
| GET | `/api/mealplan` | — | `{ meal_plan: string }` |
| POST | `/api/mealplan/generate` | — | `{ meal_plan: string }` |
| POST | `/api/report/analyze` | `multipart: file` | `ReportResult` |
| GET | `/api/report/latest` | — | `ReportResult` |
| GET | `/api/tests/recommend` | — | `{ recommendations: string }` |

#### Routines & Settings

| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | `/api/routines/exercise` | — | `ExerciseRoutine \| null` |
| POST | `/api/routines/exercise` | `ExerciseRoutinePayload` | `ExerciseRoutine` |
| GET | `/api/routines/medication` | — | `MedicationSchedule[]` |
| POST | `/api/routines/medication` | `MedicationSchedulePayload` | `MedicationSchedule` |
| PATCH | `/api/settings/notifications` | `{ paused: bool }` | `{ paused: bool }` |

#### Notifications & Devices

| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | `/api/notifications` | `unread_only=true` | `Notification[]` |
| POST | `/api/notifications/read` | `{ ids: int[] }` | `{ ok: true }` |
| POST | `/api/devices` | `{ expo_push_token, platform }` | `{ ok: true }` |

### 8.4 Rate Limiting (Nginx)

| Tier | Limit |
|------|-------|
| `/api/chat`, `/api/restaurant` | 20 req/min per user |
| `/api/log/*` | 60 req/min per user |
| All other `/api/*` | 60 req/min per user |
| File uploads | 10 req/min per user, 10 MB max |

---

## 9. Database Changes

All changes are additive. No existing tables, columns, or RLS policies are modified.

### 9.1 Migration 004 — Phone Number and Web Identity

```sql
-- Add phone_number to users table
ALTER TABLE users ADD COLUMN phone_number text UNIQUE;

-- Map Supabase Auth UUID to internal integer user ID
CREATE TABLE web_users (
  id           bigserial PRIMARY KEY,
  auth_uuid    uuid UNIQUE NOT NULL,
  internal_id  bigint UNIQUE NOT NULL,
  email        text,
  phone_number text,
  created_at   timestamptz DEFAULT now()
);

-- Sequence for mobile-only user IDs (above any realistic Telegram ID)
CREATE SEQUENCE web_user_id_seq START 9000000000;
```

**Identity rules:**
- Telegram users: `internal_id = telegram_id` (Telegram's integer)
- Mobile-only users: `internal_id = nextval('web_user_id_seq')`
- After phone linking: `web_users.internal_id` is updated to the Telegram user's ID

### 9.2 Migration 005 — Notifications and Device Tokens

```sql
CREATE TABLE notifications (
  id           bigserial PRIMARY KEY,
  internal_id  bigint REFERENCES users(telegram_id) ON DELETE CASCADE,
  title        text NOT NULL,
  body         text NOT NULL,
  is_read      boolean DEFAULT false,
  created_at   timestamptz DEFAULT now()
);
CREATE INDEX ON notifications (internal_id, is_read, created_at DESC);

CREATE TABLE device_tokens (
  id           bigserial PRIMARY KEY,
  internal_id  bigint REFERENCES users(telegram_id) ON DELETE CASCADE,
  expo_token   text NOT NULL,
  platform     text CHECK (platform IN ('ios', 'android')),
  created_at   timestamptz DEFAULT now(),
  UNIQUE (internal_id, expo_token)
);
```

### 9.3 RLS Policies for New Tables

```sql
-- web_users: users can only read their own row
ALTER TABLE web_users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own row only" ON web_users
  USING (auth_uuid = auth.uid());

-- notifications: readable by the owning internal_id
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own notifications" ON notifications
  USING (internal_id = (
    SELECT internal_id FROM web_users WHERE auth_uuid = auth.uid()
  ));

-- device_tokens: managed by backend service role only
ALTER TABLE device_tokens ENABLE ROW LEVEL SECURITY;
-- No client-side access; only the FastAPI service role key writes here
```

### 9.4 Confirmed Existing Schema (for reference)

All columns confirmed live via Supabase MCP:

**`users`** — key columns: `telegram_id` (bigint, unique), `name`, `age`, `gender` (male/female), `height_cm`, `weight_kg`, `target_weight_kg`, `activity_level` (sedentary/light/moderate/active), `diet_preference`, `medical_conditions`, `calorie_target`, `onboarding_complete`, `notifications_paused`, `current_plan`, `current_streak`, `longest_streak`, `streak_last_updated`, `eating_pattern_summary`

**Missing columns not yet in live DB** (also added in migration 004):
- `water_goal_ml int` — referenced in bot code but not yet in schema

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS water_goal_ml int;
```

---

## 10. Push Notifications

### 10.1 Architecture

```
FastAPI Scheduler Job
      ↓
Generates notification text (same logic as Telegram scheduler)
      ↓
Writes row to notifications table (in-app history)
      ↓
Fetches device_tokens for user
      ↓
POST https://exp.host/--/api/v2/push/send
      ↓
Expo Push Service
      ↓
APNs (iOS) / FCM (Android)
      ↓
Device
```

No VAPID keys, no separate push server. Expo Push Service is the relay.

### 10.2 Notification Types and Schedule

| Notification | Time (IST) | Condition |
|--------------|-----------|-----------|
| Morning motivation | 8:30 AM | Daily, always |
| Water nudge | 8 AM, 12 PM, 4 PM, 8 PM | Skip if daily goal already met |
| Medication reminder | 7:30 AM, 1:30 PM, 8:30 PM | Only if schedule set; within ±1 hour of dose |
| Exercise reminder | 6:30 PM | Only if today is a scheduled day and not yet logged |
| Evening summary | 9:00 PM | Daily, always |
| Weekly recap | Sunday 8:00 PM | Weekly |
| Re-engagement | 7:00 PM | Only if inactive 48+ hours |

### 10.3 Mobile App Push Registration

```typescript
// hooks/usePushToken.ts
import * as Notifications from 'expo-notifications'
import * as Device from 'expo-device'

export async function registerPushToken(internalId: number) {
  if (!Device.isDevice) return  // simulators can't receive push

  const { status } = await Notifications.requestPermissionsAsync()
  if (status !== 'granted') return

  const token = (await Notifications.getExpoPushTokenAsync()).data
  await api.post('/api/devices', { expo_push_token: token, platform: Platform.OS })
}
```

Called once after successful auth and `internal_id` resolution.

### 10.4 In-App Notification Center

Notifications are also stored in the `notifications` table. The bell icon in the app header shows an unread badge count. The notification centre screen (`/notifications`) lists all notifications with read/unread state, pulled via `GET /api/notifications`.

---

## 11. Error Handling and Logging

### 11.1 API Error Schema

All errors return a consistent JSON envelope:
```json
{
  "error": "MEAL_PARSE_FAILED",
  "message": "Could not identify food items. Try describing the meal more specifically.",
  "status": 422
}
```

| HTTP Status | Error Code | Trigger |
|-------------|------------|---------|
| 400 | `VALIDATION_ERROR` | Pydantic schema failure |
| 401 | `UNAUTHORIZED` | Missing or expired JWT |
| 403 | `ONBOARDING_INCOMPLETE` | Required profile fields missing |
| 413 | `FILE_TOO_LARGE` | Upload exceeds 10 MB |
| 415 | `UNSUPPORTED_FILE_TYPE` | Non-image / non-PDF file |
| 422 | `AI_PARSE_FAILED` | AI returned unparseable output |
| 429 | `RATE_LIMITED` | Over request limit |
| 500 | `INTERNAL_ERROR` | Unhandled exception |
| 503 | `AI_UNAVAILABLE` | Gemini API timeout |

### 11.2 Backend Logging

Follows bot convention: `logging.info()` only, no `print()`. Structured JSON via `python-json-logger`:

```json
{
  "timestamp": "2026-05-08T07:45:00Z",
  "level": "INFO",
  "internal_id": 9000000001,
  "endpoint": "POST /api/chat",
  "intent": "meal",
  "calories_parsed": 180,
  "latency_ms": 1240
}
```

No PII (name, phone number) in logs. `internal_id` only.

### 11.3 Mobile Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Network offline | Toast: "No connection. Changes will sync when you're back online." |
| `401` response | Clear session → redirect to Auth screen |
| `503` AI unavailable | Inline message in chat: "Coach is temporarily unavailable. Please try again." |
| File upload rejected | Inline error below the picker |
| SSE stream cut short | Show partial reply + "Response was cut short. Tap to retry." |
| OTP expired | "Code expired. Tap to resend." with 60-second cooldown |

TanStack Query is configured with `retry: 2` for all non-streaming queries, with exponential backoff.

---

## 12. Security Considerations

### 12.1 Authentication

- All `/api/*` routes verify Supabase JWT on every request using the Supabase JWKS endpoint.
- `internal_id` is always derived from the verified JWT — never accepted from the request body.
- No endpoint can access data belonging to a different user. All DB queries in `services/database.py` are filtered by the verified `internal_id`.

### 12.2 Phone Number Handling

- Phone numbers are stored in E.164 format (`+91XXXXXXXXXX`).
- Phone numbers in `users.phone_number` are unique-constrained, preventing two accounts from linking to the same Telegram profile.
- The phone number is never returned in log output or error messages.

### 12.3 Input Validation

- Backend: Pydantic v2 models on all request bodies. Numeric fields have explicit min/max matching bot validation.
- Mobile: React Hook Form + Zod schemas mirror Pydantic models exactly.
- File uploads: MIME type and magic bytes verified server-side (not trusting `Content-Type` header). Only JPEG, PNG, PDF accepted.
- AI inputs: user text is passed as a user-role message to Gemini, never interpolated into system prompt strings (prevents prompt injection).
- All AI output is rendered as plain text in React Native — never evaluated as code or HTML.

### 12.4 Secrets

| Secret | Location |
|--------|----------|
| `GEMINI_API_KEY` | VPS `.env` only |
| `SUPABASE_SERVICE_KEY` | VPS `.env` only |
| Supabase publishable key | Mobile app bundle (safe — RLS enforces access) |
| Google client IDs | Mobile app bundle (safe — redirect URI validated by Google) |
| Twilio credentials | Supabase dashboard (not in codebase) |

### 12.5 CORS (FastAPI)

```python
origins = [
  'https://api.weightwise.in',
]
# Mobile app uses direct HTTP calls, not a browser — CORS not applicable for native
# Only needed if a web client is also built later
```

---

## 13. Deployment Plan

### 13.1 Directory Layout on VPS

```
/var/www/weightwise/
├── bot/                  ← existing Telegram bot (untouched)
│   └── services/         ← ai.py, database.py, calculator.py
├── web_api/              ← new FastAPI app
│   ├── main.py
│   ├── routers/
│   ├── middleware/
│   └── services          ← symlink to ../bot/services
└── (mobile app builds distributed via EAS — not hosted on VPS)
```

### 13.2 Systemd Service for FastAPI

`/etc/systemd/system/weightwise-api.service`:
```ini
[Unit]
Description=WeightWise FastAPI
After=network.target

[Service]
WorkingDirectory=/var/www/weightwise/web_api
ExecStart=/var/www/weightwise/venv/bin/gunicorn main:app \
  -k uvicorn.workers.UvicornWorker -w 2 --bind 127.0.0.1:8001
Restart=always
EnvironmentFile=/var/www/weightwise/.env

[Install]
WantedBy=multi-user.target
```

### 13.3 Nginx

```nginx
server {
    listen 443 ssl;
    server_name api.weightwise.in;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Disable buffering for SSE endpoints
    location ~ ^/api/(chat|restaurant) {
        proxy_pass http://127.0.0.1:8001;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 120s;
        add_header X-Accel-Buffering no;
    }
}
```

### 13.4 Mobile Distribution (No App Store Account Yet)

| Phase | Tool | Command |
|-------|------|---------|
| Development | Expo Go | `npx expo start` → scan QR |
| Internal testing | EAS Internal Distribution | `eas build --profile preview --platform all` |
| Production | EAS Submit | `eas submit --platform ios` / `android` |

`eas.json`:
```json
{
  "build": {
    "development": { "developmentClient": true, "distribution": "internal" },
    "preview":     { "distribution": "internal" },
    "production":  { "autoIncrement": true }
  }
}
```

EAS Internal Distribution generates a shareable install link — no App Store account required for sharing with testers.

### 13.5 One-Time Setup Checklist

- [ ] Enable Phone auth in Supabase dashboard (Auth → Providers → Phone → Twilio credentials)
- [ ] Enable Google auth in Supabase dashboard (Auth → Providers → Google → client ID + secret)
- [ ] Create Google Cloud project, generate Web / iOS / Android OAuth 2.0 client IDs
- [ ] Add `https://uopoejlphsqbzluhxmlp.supabase.co/auth/v1/callback` to Google's authorised redirect URIs
- [ ] Run migrations 004 and 005 against the Supabase project
- [ ] Deploy FastAPI (`weightwise-api` systemd service) on VPS
- [ ] Configure Nginx for `api.weightwise.in`
- [ ] Install `eas-cli` and run `eas login`
- [ ] Add `/sharephone` command to Telegram bot for existing users

---

## 14. Milestones and Acceptance Criteria

### Milestone 1 — Foundation (Week 1–2)

**Deliverables:**
- Expo project scaffolded with Expo Router, NativeWind, `expo-secure-store`
- Phone OTP sign-in working end-to-end (enter number → SMS → verify → session)
- Google Sign-In working end-to-end (tap → Google consent → Supabase session)
- FastAPI skeleton deployed on VPS with `GET /health → 200`
- `GET /api/auth/me` returns correct identity for a valid JWT
- Migrations 004 and 005 applied to Supabase

**Acceptance criteria:**
- Sign in via phone OTP on a physical device, receive SMS, verify, session persists after app close and reopen.
- Sign in via Google on the same device, session persists.
- Both auth methods produce a valid JWT that `GET /api/auth/me` accepts.

### Milestone 2 — Identity Linking (Week 3)

**Deliverables:**
- Phone Collection Screen shown to Google users post-auth
- `POST /api/auth/link-by-phone` implemented; auto-links when phone matches `users.phone_number`
- `ask_phone` / `save_phone` handlers added to Telegram bot (`/sharephone` command + onboarding step)
- `phone_number` stored in `users` table for at least one test Telegram user

**Acceptance criteria:**
- Telegram bot user shares phone number via `/sharephone`.
- Same user signs into mobile app with Google Sign-In.
- Enters same phone number on Phone Collection Screen.
- App navigates directly to Dashboard with full Telegram history loaded — no onboarding wizard shown.

### Milestone 3 — Onboarding and Dashboard (Week 4)

**Deliverables:**
- 9-step onboarding wizard with all validations
- `POST /api/onboard` returns calorie target
- Dashboard shows calorie progress bar, water progress, streak badge, today's meal list
- `GET /api/today/summary` returns correct values
- Quick-log bottom sheets for all 5 log types

**Acceptance criteria:**
- New user (no Telegram history) completes all 9 onboarding steps, sees their calculated calorie target on the Dashboard.
- Logging weight via bottom sheet updates the Dashboard without page reload.

### Milestone 4 — Chat and Logging (Week 5–6)

**Deliverables:**
- Chat screen with SSE streaming (character-by-character coach replies)
- Free-text meal logging triggers `meal_logged` SSE event → meal card appended in real time
- Photo meal logging via `expo-image-picker` → Gemini vision → streamed response
- Meal correction flow
- All 5 quick-log endpoints working

**Acceptance criteria:**
- Type "I had 2 idlis for breakfast" in chat → coach replies, meal appears in today's log with correct calories.
- Take photo of a meal → meal analysed and logged.
- Correct a logged meal → calorie count updates.

### Milestone 5 — History, Plans, Reports (Week 7)

**Deliverables:**
- Weight history chart (30-day, VictoryNative line chart)
- Meal log screen (reverse-chronological)
- Exercise and water history screens
- Plan and meal plan generation and display
- Lab report upload (PDF + image) with structured analysis display
- Blood test recommendations screen

**Acceptance criteria:**
- 30-day weight history renders correctly with start/current/goal annotations.
- Upload a PDF lab report → Key Results, Weight-Loss Relevance, Action Items displayed.
- Generate 7-day meal plan → table displayed within calorie target.

### Milestone 6 — Notifications and Polish (Week 8)

**Deliverables:**
- `usePushToken` hook registers Expo push token on login
- Scheduler jobs send push notifications via Expo Push Service
- In-app notification centre with unread badge count
- Settings screen (profile edit, medication schedules, exercise routines, pause toggle)
- EAS preview build shared for internal testing

**Acceptance criteria:**
- Install app on physical device, grant notification permission.
- At 8:30 AM IST, receive morning motivation push notification.
- Notification centre shows the same message with unread badge.
- Mark as read → badge clears.
- EAS preview build installs successfully on both iOS and Android via shared link.

---

## Appendix A — Open Items

| # | Item | Decision |
|---|------|----------|
| 1 | **Existing Telegram users with no phone shared** | `/sharephone` command added to bot. Not mandatory — users without phone in DB who sign in via mobile will go through onboarding and create a parallel profile. Can be merged later. |
| 2 | **Offline logging** | Out of scope for MVP. App requires connectivity for all AI calls. |
| 3 | **App Store / Play Store accounts** | Not required for MVP. EAS Internal Distribution used for testing. Create accounts before public launch. |
| 4 | **meal plan / restaurant mode restaurant search** | Bot uses AI knowledge of restaurant names. No live menu API. Behaviour preserved as-is. |
| 5 | **IST timezone assumption** | All scheduler jobs assume IST. Mobile app inherits this. Internationalisation is post-MVP. |
| 6 | **PDF lab report multi-page** | Only first page analysed (PyMuPDF behaviour inherited from bot). Documented in UI: "Only the first page is analysed." |

---

## Appendix B — Package Installation Reference

```bash
# Core
npx create-expo-app mobile --template blank-typescript
cd mobile

# Navigation
npx expo install expo-router react-native-safe-area-context react-native-screens
npx expo install expo-linking expo-constants expo-status-bar

# Auth
npx expo install expo-auth-session expo-web-browser expo-crypto
npx expo install expo-secure-store

# Supabase
npm install @supabase/supabase-js

# Styling
npm install nativewind
npm install -D tailwindcss@3.3.2

# State
npm install zustand @tanstack/react-query

# Forms
npm install react-hook-form zod @hookform/resolvers

# Media
npx expo install expo-image-picker expo-document-picker

# Charts
npm install victory-native

# Push
npx expo install expo-notifications expo-device

# SSE
npm install react-native-sse

# Build
npm install -g eas-cli
```
