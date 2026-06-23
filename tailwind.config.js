/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Anthropic-inspired warm dark palette
        ink: {
          900: "#16130f",
          800: "#1c1813",
          700: "#241f18",
          600: "#2e2820",
          500: "#3a332a",
        },
        clay: {
          300: "#e8c4a0",
          400: "#e0a872",
          500: "#d97757", // Claude coral accent
          600: "#c05f3f",
        },
        agent: {
          orchestrator: "#d97757",
          design: "#e0a872",
          content: "#8bb4a3",
          structure: "#7fa8d9",
          layout: "#9d8bd9",
          builder: "#d98bb4",
          reflection: "#d9c77f",
          evaluator: "#86d99b",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(217,119,87,0.4), 0 0 24px 2px rgba(217,119,87,0.35)",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 0 1px rgba(217,119,87,0.5), 0 0 18px 2px rgba(217,119,87,0.30)" },
          "50%": { boxShadow: "0 0 0 1px rgba(217,119,87,0.9), 0 0 34px 6px rgba(217,119,87,0.55)" },
        },
        dash: {
          to: { strokeDashoffset: "-16" },
        },
        fadeIn: {
          from: { opacity: "0", transform: "translateY(2px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        pulseGlow: "pulseGlow 1.6s ease-in-out infinite",
        dash: "dash 0.8s linear infinite",
        fadeIn: "fadeIn 0.15s ease-out",
      },
    },
  },
  plugins: [],
};
