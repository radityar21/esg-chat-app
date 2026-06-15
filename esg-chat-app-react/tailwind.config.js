/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  safelist: [
    // Dynamic color classes used in components
    'bg-accent-blue/10', 'bg-accent-blue/20', 'bg-accent-teal/10', 'bg-accent-teal/20',
    'bg-accent-purple/10', 'bg-accent-purple/20', 'bg-esg-green/10', 'bg-esg-green/20',
    'bg-esg-amber/10', 'bg-esg-amber/20', 'bg-esg-red/10', 'bg-esg-red/20',
    'text-accent-blue', 'text-accent-teal', 'text-accent-purple', 'text-accent-cyan',
    'text-esg-green', 'text-esg-amber', 'text-esg-red',
    'border-accent-blue/20', 'border-accent-teal/20', 'border-accent-purple/20',
    'border-esg-green/20', 'border-esg-amber/20', 'border-esg-red/20',
    'from-accent-blue/20', 'from-accent-blue/5', 'to-accent-blue/5',
    'from-esg-green/20', 'from-esg-green/5', 'to-esg-green/5',
    'from-esg-red/20', 'from-esg-red/5', 'to-esg-red/5',
    'from-esg-amber/20', 'from-esg-amber/5', 'to-esg-amber/5',
    'border-white/50/20',
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0a0e1a',
          800: '#0d1225',
          700: '#111830',
          600: '#1a2240',
          500: '#243055',
          400: '#2d3a66',
        },
        accent: {
          blue: '#4f8cf7',
          teal: '#06d6a0',
          purple: '#7c5cfc',
          cyan: '#22d3ee',
        },
        esg: {
          green: '#06d6a0',
          amber: '#fbbf24',
          red: '#ef4444',
          teal: '#14b8a6',
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'glass-gradient': 'linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)',
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'glass-sm': '0 4px 16px 0 rgba(0, 0, 0, 0.25)',
        'neon-blue': '0 0 20px rgba(79, 140, 247, 0.3)',
        'neon-green': '0 0 20px rgba(6, 214, 160, 0.3)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
