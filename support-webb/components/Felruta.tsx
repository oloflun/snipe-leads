"use client";

import { useEffect } from "react";

import { btnPrimary } from "@/components/ui";

/**
 * Portalens felgräns. Före 2026-11-09 hade support-webb ingen alls (Fas
 * 0-fyndet H8): ett renderfel gav Nexts vita, engelska standardsida mitt i
 * supportmedarbetarens arbetsdag.
 *
 * Felmeddelandet återges inte, av samma skäl som i huvudappens felgräns: ett
 * serverfel kan bära interna detaljer. `digest` är Nexts opaka referens.
 *
 * Portalen har ingen språkväxlare, så båda språken står här: svenska först,
 * engelska under.
 */
export function Felruta({
  error,
  reset
}: Readonly<{ error: Error & { digest?: string }; reset: () => void }>) {
  useEffect(() => {
    console.error("support-webb fångade:", error);
  }, [error]);

  return (
    <div className="grid place-items-center py-16" role="alert">
      <div className="max-w-lg text-center">
        <h1 className="font-display text-[2rem] leading-tight tracking-[-0.02em]">Något gick fel</h1>
        <p className="mt-4 text-[16px] leading-7 text-ink2">
          Felet är loggat på vår sida. Prova igen. Hjälper inte det, mejla{" "}
          <a href="mailto:kontakt@snajp.se" className="underline">
            kontakt@snajp.se
          </a>
          .
        </p>
        <p className="mt-2 text-[13px] leading-6 text-ink2" lang="en">
          Something went wrong. The error has been logged. Try again, or email kontakt@snajp.se.
        </p>
        {error.digest ? (
          <p className="mt-3 text-[13px] tracking-[0.04em] text-ink2">FELKOD {error.digest}</p>
        ) : null}
        <div className="mt-8 flex justify-center">
          <button type="button" onClick={reset} className={btnPrimary}>
            Försök igen
          </button>
        </div>
      </div>
    </div>
  );
}
