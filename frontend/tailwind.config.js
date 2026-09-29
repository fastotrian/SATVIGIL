/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          950: '#060E1C',
          900: '#0A1628',
          850: '#0D1B32',
          800: '#0F1F3D',
          700: '#112244',
          600: '#1A3560',
          500: '#1E3A5F',
          400: '#1B6CA8',
        },
      },
    },
  },
  plugins: [],
}
