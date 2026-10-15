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
        // StockLens Natural Editorial & Terminal Palette
        base: '#081919', // Black Stallion
        surface: {
          DEFAULT: '#223330', // Concealed Green
          base: '#081919',    // Black Stallion
          card: '#223330',    // Concealed Green
          raised: '#2F403C',  // Elevated Concealed Green
          elevated: '#4D524B',// Iron River
          subtle: '#1C2A28',  // Deep tint
          hover: 'rgba(131, 127, 120, 0.12)',
        },
        editorial: {
          primary: '#F4F5F1',   // Warm off-white (17.5:1 on Black Stallion)
          secondary: '#B4B0A7', // Warm secondary (7.2:1)
          muted: '#837F78',     // Chain Link (4.9:1 - passes WCAG AA)
          hairline: 'rgba(131, 127, 120, 0.22)',
          subtle: 'rgba(131, 127, 120, 0.38)',
          strong: '#4D524B',    // Iron River
        },
        // Palette Specific Colors
        palette: {
          blackStallion: '#081919',
          concealedGreen: '#223330',
          ironRiver: '#4D524B',
          chainLink: '#837F78',
          bloodGod: '#65060E',
          thunderPepper: '#CE1A1E',
        },
        stallion: '#081919',
        concealed: '#223330',
        iron: '#4D524B',
        chain: '#837F78',
        blood: {
          DEFAULT: '#65060E',
          muted: 'rgba(101, 6, 14, 0.18)',
          border: 'rgba(101, 6, 14, 0.45)',
        },
        pepper: {
          DEFAULT: '#CE1A1E',
          muted: 'rgba(206, 26, 30, 0.14)',
          border: 'rgba(206, 26, 30, 0.35)',
          deep: '#65060E',
          light: '#E8383D',
        },
        // Semantic Financial Colors
        gain: {
          DEFAULT: '#2FD08A',   // Refined emerald
          muted: 'rgba(47, 208, 138, 0.12)',
          border: 'rgba(47, 208, 138, 0.3)',
          light: '#61E4A9',
        },
        loss: {
          DEFAULT: '#CE1A1E',   // Thunder Mountain Longhorn Pepper
          muted: 'rgba(206, 26, 30, 0.14)',
          border: 'rgba(206, 26, 30, 0.35)',
          deep: '#65060E',      // Blood God
          light: '#E8383D',
        },
        gold: {
          DEFAULT: '#C9A96A',   // Champagne gold (Neutral / Info / Company 1 fallback)
          muted: 'rgba(201, 169, 106, 0.12)',
          border: 'rgba(201, 169, 106, 0.3)',
          light: '#DCBF85',
        },
        cyan: {
          DEFAULT: '#6FB7D6',   // Cool steel-cyan (Company 2 fallback)
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
          850: '#1C2A28',
          950: '#081919',
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
        hairline: 'inset 0 1px 0 0 rgba(131, 127, 120, 0.18), 0 12px 32px -8px rgba(8, 25, 25, 0.85)',
        'hairline-sm': 'inset 0 1px 0 0 rgba(131, 127, 120, 0.18)',
        'glow-pepper': '0 0 35px -8px rgba(206, 26, 30, 0.35)',
        'glow-blood': '0 0 35px -8px rgba(101, 6, 14, 0.45)',
        'glow-gold': '0 0 35px -8px rgba(206, 26, 30, 0.25)',
        'glow-cyan': '0 0 35px -8px rgba(131, 127, 120, 0.25)',
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
