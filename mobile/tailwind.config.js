/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './features/**/*.{ts,tsx}',
  ],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#16a34a',
          light: '#dcfce7',
          dark: '#15803d',
        },
        // Domain colors from design system
        nutrition: { bg: '#f0fdf4', border: '#86efac' },  // green-50 / green-300
        water:     { bg: '#eff6ff', border: '#93c5fd' },  // blue-50 / blue-300
        fasting:   { bg: '#fefce8', border: '#fde047' },  // yellow-50 / yellow-300
      },
    },
  },
  plugins: [],
}
