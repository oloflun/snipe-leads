"use client";

import { useEffect } from "react";

import { btnPrimary } from "@/components/ui";

/**
 * Felgräns för hela den routade ytan. Fanns inte förrän 2026-08-27, och
 * följden var mätbar: ett okastat serverfel i en server-komponent gav Nexts
 * råa "Application error: a server-side exception has occurred" — engelsk,
 * omärkt, vit — på en produkt som lovar svenska hela vägen.
 *
 * Felmeddelandet återges MEDVETET INTE här. Ett serverfel kan bära interna
 * detaljer (tabellnamn, env-varnamn, en annan kunds slug i värsta fall), och
 * den enda som har nytta av dem är den som läser loggen — dit de redan går
 * via console.error nedan. `error.digest` är däremot säker att visa: den är
 * Nexts opaka referens som supporten kan slå upp i Vercel/Railway-loggen.
 */
export default function Error({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("app/error.tsx fångade:", error);
  }, [error]);

  return (
    <main className="grid min-h-screen place-items-center bg-paper p-6">
      <div className="max-w-lg text-center">
        <h1 className="font-display text-[2.5rem] leading-tight tracking-[-0.02em]">
          Något gick fel
        </h1>
        <p className="mt-4 text-[17px] leading-8 text-ink2">
          Felet är loggat på vår sida. Prova igen — hjälper inte det, mejla{" "}
          <a href="mailto:kontakt@snajp.se" className="text-ochre">
            kontakt@snajp.se
          </a>
          .
        </p>
        {/* Felkoden på egen rad. Inbakad i meningen läste den som brus mitt i
            en text man ändå skummar — sedd i skärmdump. Fristående blir den
            det den är: en referens att citera för supporten. */}
        {error.digest ? (
          <p className="mt-3 text-[13px] tracking-[0.04em] text-mineral">
            FELKOD {error.digest}
          </p>
        ) : null}
        <div className="mt-8 flex justify-center">
          <button type="button" onClick={reset} className={btnPrimary}>
            Försök igen
          </button>
        </div>
      </div>
    </main>
  );
}
