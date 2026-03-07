/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  corePlugins: {
    preflight: false, // Do NOT reset existing CSS
  },
  theme: {
    extend: {
      colors: {
        'ws-bg':      '#0f1923',
        'ws-surface': '#12161e',
        'ws-surface2':'#1a1f2b',
        'ws-border':  '#2a3040',
        'ws-gold':    '#c9a84c',
        'ws-blue':    '#4a90d9',
        'ws-text':    '#dde3ef',
        'ws-muted':   '#7a8499',
      },
    },
  },
  plugins: [],
}
