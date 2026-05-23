import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "oklch(var(--ink) / <alpha-value>)",
        ink2: "oklch(var(--ink2) / <alpha-value>)",
        paper: "oklch(var(--paper) / <alpha-value>)",
        paper2: "oklch(var(--paper2) / <alpha-value>)",
        linen: "oklch(var(--paper2) / <alpha-value>)",
        mineral: "oklch(var(--mineral) / <alpha-value>)",
        seal: "oklch(var(--seal) / <alpha-value>)",
        ochre: "oklch(var(--ochre) / <alpha-value>)",
        steel: "oklch(var(--mineral) / <alpha-value>)",
        moss: "oklch(var(--moss) / <alpha-value>)",
        copper: "oklch(var(--ochre) / <alpha-value>)",
        frost: "oklch(var(--paper2) / <alpha-value>)",
        danger: "oklch(var(--danger) / <alpha-value>)"
      },
      fontFamily: {
        display: ["Fraunces", "ui-serif", "Georgia", "serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"]
      },
      boxShadow: {
        hairline: "0 0 0 1px oklch(var(--ink) / 0.09)",
        lift: "0 24px 70px oklch(var(--ink) / 0.12)"
      }
    }
  },
  plugins: []
};

export default config;
