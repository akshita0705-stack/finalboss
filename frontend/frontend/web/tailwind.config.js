/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        void: '#07060B',
        night: '#0D1117',
        surface: '#14121C',
        'surface-2': '#1C1828',
        ghost: '#2A2538',
        pumpkin: { DEFAULT: '#FF7A1A', glow: '#FFB347' },
        blood: '#E5133A',
        witch: '#7B3FE4',
        toxic: '#39FF88',
        moon: '#F3E9C6',
        fog: '#9AA3B2',
        'sky-teal': '#1E4D4F',
      },
      fontFamily: {
        creep: ['Creepster', 'Nosifer', 'cursive'],
        tech: ['"Chakra Petch"', 'Rajdhani', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        pumpkin: '0 0 24px -4px rgba(255,122,26,.55)',
        blood: '0 0 28px -4px rgba(229,19,58,.6)',
        witch: '0 0 24px -4px rgba(123,63,228,.55)',
      },
      keyframes: {
        twinkle: { '0%,100%': { opacity: '.25' }, '50%': { opacity: '1' } },
        'moon-pulse': { '0%,100%': { opacity: '.85', transform: 'scale(1)' }, '50%': { opacity: '1', transform: 'scale(1.04)' } },
        'fog-drift': { from: { transform: 'translate3d(0,0,0)' }, to: { transform: 'translate3d(-50%,0,0)' } },
        flicker: { '0%,18%,22%,25%,53%,57%,100%': { opacity: '1' }, '20%,24%,55%': { opacity: '.55' } },
        flap: { '0%,100%': { transform: 'scaleY(1)' }, '50%': { transform: 'scaleY(.35)' } },
        ember: { '0%': { transform: 'translate3d(0,0,0)', opacity: '0' }, '10%': { opacity: '.9' }, '100%': { transform: 'translate3d(var(--dx,20px),-110vh,0)', opacity: '0' } },
        lightning: { '0%,100%': { opacity: '0' }, '8%': { opacity: '.9' }, '14%': { opacity: '.1' }, '20%': { opacity: '.6' }, '40%': { opacity: '0' } },
      },
      animation: {
        twinkle: 'twinkle 3s ease-in-out infinite',
        'moon-pulse': 'moon-pulse 7s ease-in-out infinite',
        'fog-drift': 'fog-drift 60s linear infinite',
        flicker: 'flicker 6s linear infinite',
        flap: 'flap .35s ease-in-out infinite',
        ember: 'ember 12s linear infinite',
        lightning: 'lightning 1.1s ease-out 1',
      },
    },
  },
  plugins: [],
}
