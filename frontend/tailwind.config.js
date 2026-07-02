/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: '#2C5F8A', light: '#3B82C4', dark: '#1e4060' },
        surface: { DEFAULT: '#1e293b', raised: '#273449' },
      },
    },
  },
  plugins: [],
}
