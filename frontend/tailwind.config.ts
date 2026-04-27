import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'terminal-dark': '#0d1117',
        'terminal-bg': '#1a1a2e',
        'terminal-border': '#30363d',
        'terminal-text': '#c9d1d9',
        'terminal-muted': '#8b949e',
        'accent-yellow': '#ecad0a',
        'accent-blue': '#209dd7',
        'accent-purple': '#753991',
        'price-up': '#238636',
        'price-down': '#da3633',
      },
      fontFamily: {
        'mono': ['IBM Plex Mono', 'Menlo', 'monospace'],
        'sans': ['IBM Plex Sans', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      animation: {
        'price-flash': 'priceFlash 0.5s ease-out',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
      },
      keyframes: {
        priceFlash: {
          '0%': { backgroundColor: 'rgba(34, 134, 54, 0.3)' },
          '100%': { backgroundColor: 'rgba(34, 134, 54, 0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
      },
      boxShadow: {
        'terminal': '0 4px 12px rgba(0, 0, 0, 0.5)',
        'glow': '0 0 20px rgba(236, 173, 10, 0.2)',
      },
    },
  },
  plugins: [],
}
export default config
