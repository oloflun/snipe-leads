"use client";

import { FelHelsida } from "@/components/Felgrans";

/**
 * Felgräns för hela den routade ytan. Fanns inte förrän 2026-08-27, och
 * följden var mätbar: ett okastat serverfel i en server-komponent gav Nexts
 * råa "Application error: a server-side exception has occurred" — engelsk,
 * omärkt, vit — på en produkt som lovar svenska hela vägen.
 *
 * Felmeddelandet återges MEDVETET INTE här. Ett serverfel kan bära interna
 * detaljer (tabellnamn, env-varnamn, en annan kunds slug i värsta fall), och
 * den enda som har nytta av dem är den som läser loggen — dit de redan går
 * via console.error. `error.digest` är däremot säker att visa: den är Nexts
 * opaka referens som supporten kan slå upp i Railway-loggen.
 *
 * Sedan 2026-11-09 är det här den YTTERSTA gränsen: arbetsytan, adminytan,
 * inställningarna, onboardingen och chatten har var sin (components/
 * Felgrans.tsx), så att ett fel i en vy inte tar menyn med sig.
 */
export default function Error(
  props: Readonly<{
    error: Error & { digest?: string };
    reset: () => void;
  }>
) {
  return <FelHelsida {...props} />;
}
