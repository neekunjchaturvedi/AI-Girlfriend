/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        relationship: {
          acquaintance: '#3B82F6', // blue
          friend: '#22C55E',       // green
          girlfriend: '#EC4899'    // pink
        }
      }
    },
  },
  safelist: [
    {
      pattern: /(bg|text|hover:bg|border)-(blue|green|pink)-(100|200|500|700)/,
    }
  ],
  plugins: [],
}

