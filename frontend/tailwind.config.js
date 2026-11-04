/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ayur: {
          50: '#f2f9f6',
          100: '#e1f2eb',
          200: '#c5e5d8',
          300: '#99d2be',
          400: '#64b69d',
          500: '#3e9b81',
          600: '#2c7c66',
          700: '#246353',
          800: '#1e4f43',
          900: '#1b4238',
          950: '#0c241f',
        },
        gold: {
          50: '#fefce8',
          100: '#fef9c3',
          200: '#fef08a',
          300: '#fde047',
          400: '#facc15',
          500: '#eab308',
          600: '#ca8a04',
          700: '#a16207',
          800: '#854d0e',
          900: '#713f12',
          950: '#422006',
        },
        parchment: {
          50: '#fdfbf7',
          100: '#f8f4eb',
          200: '#f2ebd9',
          300: '#e9dfc2',
          400: '#ddcca4',
          500: '#ceb685',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        sanskrit: ['"Noto Serif Devanagari"', 'Georgia', 'serif'],
        display: ['"Playfair Display"', 'Georgia', 'serif'],
      }
    },
  },
  plugins: [],
}
