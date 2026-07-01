/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        github: '#24292f',
        accent: '#0969da',
      },
    },
  },
  plugins: [],
}
