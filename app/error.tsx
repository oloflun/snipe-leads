"use client";

import { useEffect } from "react";

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
          <a href="mailto:hej@snajp.se" className="text-ochre">
            hej@snajp.se
          </a>
          {error.digest ? ` och ange felkoden ${error.digest}` : ""}.
        </p>
        <button
          type="button"
          onClick={reset}
          className="mt-8 inline-flex min-h-11 items-center rounded-full bg-ink px-6 text-[15px] font-medium text-paper"
        >
          Försök igen
        </button>
      </div>
    </main>
  );
}
