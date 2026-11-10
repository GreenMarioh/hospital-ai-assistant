import type { Config } from "tailwindcss";

/*
 * Design tokens. Navy carries structure and action, white carries content,
 * marigold is a sparing signal (active place, brand mark, "today").
 */
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          50: "#EEF2F8",
          100: "#DCE4F0",
          200: "#B9C7DD",
          300: "#8FA3C4",
          400: "#6079A3",
          500: "#3F5A86",
          600: "#2D4670",
          700: "#213A63",
          800: "#16294F",
          900: "#0F1F3D",
          950: "#0A152B",
        },
        marigold: {
          100: "#FBEFD6",
          300: "#F0C774",
          400: "#E2A63B",
          600: "#A86F12",
        },
        paper: "#F4F6FA",
        line: "#DBE1EB",
      },
      borderColor: { DEFAULT: "#DBE1EB" },
      fontFamily: {
        sans: ['"Public Sans Variable"', "system-ui", "sans-serif"],
        serif: ['"Source Serif 4 Variable"', "Georgia", "serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
