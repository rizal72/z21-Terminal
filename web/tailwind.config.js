/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'control-black': '#0a0a0a',
        'control-dark': '#1a1a1a',
        'control-grey': '#2a2a2a',
        'signal-amber': '#ff9500',
        'signal-amber-light': '#ffb340',
        'signal-red': '#e63946',
        'signal-green': '#06d6a0',
        'track-steel': '#64748b',
        'highlight-gold': '#fbbf24',
      },
      fontFamily: {
        'display': ['"Outfit"', 'system-ui', 'sans-serif'],
        'body': ['"Manrope"', 'system-ui', 'sans-serif'],
        'mono': ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite',
        'fade-in': 'fadeIn 0.6s ease-out forwards',
      },
      keyframes: {
        glow: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.6 },
        },
        fadeIn: {
          '0%': { opacity: 0, transform: 'translateY(20px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        }
      }
    },
  },
  plugins: [],
}
