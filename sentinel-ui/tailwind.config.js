/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // SENTINEL Theme: "If it looks calm, it's lying."
        sentinel: {
          primary: '#4a7c9b',      // steel_blue - cold twilight blue
          secondary: '#b3b3b3',    // grey70 - pale surgical white
          warning: '#b8860b',      // dark_goldenrod - muted radioactive yellow
          danger: '#8b0000',       // dark_red - rusted red
          accent: '#00d7ff',       // cyan - interface highlights
          dim: '#666666',          // muted text
          bg: '#0a0a0a',           // near-black background
          surface: '#141414',      // elevated surfaces
          border: '#2a2a2a',       // subtle borders
        },
        // Faction colors
        faction: {
          nexus: '#00bfff',        // Deep sky blue
          ember: '#ff6b35',        // Warm orange
          lattice: '#32cd32',      // Electric green
          convergence: '#da70d6',  // Orchid purple
          covenant: '#ffd700',     // Gold
          wanderers: '#cd853f',    // Peru brown
          cultivators: '#228b22',  // Forest green
          steel: '#708090',        // Slate gray
          witnesses: '#e6e6fa',    // Lavender
          architects: '#4169e1',   // Royal blue
          ghost: '#2f4f4f',        // Dark slate gray
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      animation: {
        'glitch': 'glitch 0.3s steps(2) infinite',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'scan': 'scan 4s linear infinite',
      },
      keyframes: {
        glitch: {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '50%': { transform: 'translate(2px, -1px)' },
        },
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
      },
    },
  },
  plugins: [],
}
