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
        // StockLens Luxury Terminal & Editorial Palette
        base: '#0A0B0D',
        surface: {
          DEFAULT: '#101215',
          base: '#0A0B0D',
          card: '#101215',
          raised: '#171A1F',
          subtle: '#1C2027',
          hover: 'rgba(255, 255, 255, 0.04)',
        },
        editorial: {
          primary: '#F2F0EB',   // Warm off-white (17.4:1 on base)
          secondary: '#9A9A94', // Editorial secondary (6.8:1)
          muted: '#7E7F78',     // Captions (4.8:1 - passes WCAG AA)
          hairline: 'rgba(255, 255, 255, 0.07)',
          subtle: 'rgba(255, 255, 255, 0.12)',
          strong: 'rgba(255, 255, 255, 0.22)',
        },
        // Semantic Financial Colors
        gain: {
          DEFAULT: '#2FD08A',   // Refined emerald
          muted: 'rgba(47, 208, 138, 0.12)',
          border: 'rgba(47, 208, 138, 0.3)',
          light: '#61E4A9',
        },
        loss: {
          DEFAULT: '#FF5A4D',   // Muted vermilion
          muted: 'rgba(255, 90, 77, 0.12)',
          border: 'rgba(255, 90, 77, 0.3)',
          light: '#FF8178',
        },
        gold: {
          DEFAULT: '#C9A96A',   // Champagne gold (Neutral / Info / Company 1)
          muted: 'rgba(201, 169, 106, 0.12)',
          border: 'rgba(201, 169, 106, 0.3)',
          light: '#DCBF85',
        },
        cyan: {
          DEFAULT: '#6FB7D6',   // Cool steel-cyan (Company 2)
          muted: 'rgba(111, 183, 214, 0.12)',
          border: 'rgba(111, 183, 214, 0.3)',
          light: '#91CBE3',
        },
        // Semantic aliases
        champagne: '#C9A96A',
        steel: '#6FB7D6',

        // Legacy compatibility
        brand: {
          50: '#f0fdf4',
          100: '#dcfce7',
          500: '#2FD08A',
          600: '#24A86F',
          700: '#15803d',
          900: '#14532d',
        },
        slate: {
          850: '#151f32',
          950: '#0A0B0D',
        },
      },
      fontFamily: {
        serif: ['Fraunces', 'Playfair Display', 'Georgia', 'serif'],
        display: ['Fraunces', 'Playfair Display', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      fontSize: {
        'hero': ['4.5rem', { lineHeight: '1.02', letterSpacing: '-0.035em' }], // 72px
        'hero-lg': ['6rem', { lineHeight: '1.0', letterSpacing: '-0.04em' }], // 96px
        'section': ['2.25rem', { lineHeight: '1.15', letterSpacing: '-0.025em' }], // 36px
        'section-lg': ['3rem', { lineHeight: '1.1', letterSpacing: '-0.03em' }], // 48px
      },
      borderRadius: {
        card: '12px',
      },
      boxShadow: {
        hairline: 'inset 0 1px 0 0 rgba(255, 255, 255, 0.08), 0 12px 32px -8px rgba(0, 0, 0, 0.65)',
        'hairline-sm': 'inset 0 1px 0 0 rgba(255, 255, 255, 0.07)',
        'glow-gold': '0 0 35px -8px rgba(201, 169, 106, 0.25)',
        'glow-cyan': '0 0 35px -8px rgba(111, 183, 214, 0.25)',
      },
      animation: {
        'fadeIn': 'fadeIn 300ms cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'shimmer': 'shimmer 2s infinite linear',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
    },
  },
  plugins: [],
}
