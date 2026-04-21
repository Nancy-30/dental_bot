/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          primary:  '#0EA5E9',   // sky-500 — dental blue
          dark:     '#0F172A',   // slate-900
          panel:    '#1E293B',   // slate-800
          accent:   '#38BDF8',   // sky-400
          light:    '#E0F2FE',   // sky-100
        },
      },
      animation: {
        pulse: 'pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
