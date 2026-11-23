import { Fraunces } from "next/font/google";

/**
 * Fraunces, förladdad. Importeras av de sidor och layouter som faktiskt ritar
 * med den (arbetsytan, inställningarna, admin, inloggning, onboarding och
 * innehållssidorna). next/font förladdar per sida efter vilka typsnittsmoduler
 * sidan importerar, så en egen modul är sättet att förladda på vissa sidor och
 * inte på andra. Inställningarna ska vara desamma som i lib/fonts.ts: då är
 * det samma fil som hämtas, och variabeln `--font-fraunces` från rotlayouten
 * pekar på den.
 */
export const frauncesRubrik = Fraunces({
  subsets: ["latin"],
  style: ["normal", "italic"],
  axes: ["SOFT", "opsz"],
  variable: "--font-fraunces",
  display: "swap"
});
