import { Source_Serif_4 } from "next/font/google";

/**
 * Source Serif 4, förladdad. Importeras av marknadssidorna (ProductPage), som
 * är de enda som ritar med den. Se lib/fonts-rubrik.ts för varför den bor i en
 * egen modul. Samma inställningar som i lib/fonts.ts.
 */
export const sourceSerifLandning = Source_Serif_4({
  subsets: ["latin"],
  style: ["normal", "italic"],
  axes: ["opsz"],
  variable: "--font-source-serif",
  display: "swap"
});
