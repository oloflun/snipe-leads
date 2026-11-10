"use client";

import { useEffect } from "react";

import { AppShell } from "@/components/AppShell";
import { btnPrimary } from "@/components/ui";
import { useLocale } from "@/lib/i18n";

/**
 * Felgränsernas gemensamma innehåll — det `error.tsx` renderar.
 *
 * Före 2026-11-09 fanns EN felgräns, i roten (Fas 0-fyndet H8). Ett renderfel
 * i en enda vy i arbetsytan bytte därför ut hela sidan, menyn inräknad, och
 * den som fyllt i fyra steg av onboardingen förlorade dem. Med en gräns per
 * yta stannar felet i innehållet: menyn står kvar och användaren kan gå
 * vidare till en annan flik.
 *
 * Samma regel som i app/error.tsx: felmeddelandet återges INTE. Ett serverfel
 * kan bära interna detaljer, och den som har nytta av dem läser loggen.
 * `error.digest` är Nexts opaka referens och säker att visa.
 *
 * Texten och typografin är den felsida som redan fanns; det nya är var den
 * visas, och att den finns på engelska.
 */
type Felprops = Readonly<{
  error: Error & { digest?: string };
  reset: () => void;
}>;

function useLoggatFel(error: Error, var_: string) {
  useEffect(() => {
    console.error(`${var_} fångade:`, error);
  }, [error, var_]);
}

function Felruta({ error, reset }: Felprops) {
  const { text } = useLocale();
  return (
    <div className="max-w-lg text-center" role="alert">
      <h1 className="font-display text-[2.5rem] leading-tight tracking-[-0.02em]">
        {text({ sv: "Något gick fel", en: "Something went wrong" })}
      </h1>
      <p className="mt-4 text-[17px] leading-8 text-ink2">
        {text({
          sv: "Felet är loggat på vår sida. Prova igen. Hjälper inte det, mejla",
          en: "The error has been logged on our side. Try again. If that does not help, email"
        })}{" "}
        <a href="mailto:kontakt@snajp.se" className="text-warning">
          kontakt@snajp.se
        </a>
        .
      </p>
      {/* Felkoden på egen rad: en referens att citera för supporten. */}
      {error.digest ? (
        <p className="mt-3 text-[13px] tracking-[0.04em] text-mineral">
          {text({ sv: "FELKOD", en: "ERROR CODE" })} {error.digest}
        </p>
      ) : null}
      <div className="mt-8 flex justify-center">
        <button type="button" onClick={reset} className={btnPrimary}>
          {text({ sv: "Försök igen", en: "Try again" })}
        </button>
      </div>
    </div>
  );
}

/** Hela sidan: roten och ytor utan eget skal (onboarding). */
export function FelHelsida(props: Felprops) {
  useLoggatFel(props.error, "Felgränsen (helsida)");
  return (
    <main className="grid min-h-screen place-items-center bg-paper p-6">
      <Felruta {...props} />
    </main>
  );
}

/** Kundens yta och inställningarna: varje vy bär sitt eget AppShell, så
 * gränsen gör det också — annars försvinner menyn med felet. Faller skalet
 * självt tar rotgränsen över. */
export function FelArbetsyta(props: Felprops) {
  useLoggatFel(props.error, "Felgränsen (arbetsytan)");
  return (
    <AppShell>
      <section className="mx-auto grid w-full max-w-[1200px] place-items-center px-4 py-16 md:px-8">
        <Felruta {...props} />
      </section>
    </AppShell>
  );
}

/** Adminytan: skalet och containern bor redan i app/admin/layout.tsx. */
export function FelAdmin(props: Felprops) {
  useLoggatFel(props.error, "Felgränsen (admin)");
  return (
    <div className="grid place-items-center py-16">
      <Felruta {...props} />
    </div>
  );
}

/**
 * Den publika chatten och widgeten. Läsaren är kundens kund, på kundens sajt:
 * ingen hänvisning till Snajp, ingen felkod, bara vad som hände och vad man
 * kan göra.
 */
export function FelChatt({ error, reset }: Felprops) {
  useLoggatFel(error, "Felgränsen (chatten)");
  const { text } = useLocale();
  return (
    <main className="grid min-h-screen place-items-center bg-paper p-6">
      <div className="max-w-sm text-center" role="alert">
        <p className="text-[17px] leading-8 text-ink2">
          {text({
            sv: "Chatten kunde inte laddas just nu. Försök igen, eller ladda om sidan.",
            en: "The chat could not load right now. Try again, or reload the page."
          })}
        </p>
        <div className="mt-6 flex justify-center">
          <button type="button" onClick={reset} className={btnPrimary}>
            {text({ sv: "Försök igen", en: "Try again" })}
          </button>
        </div>
      </div>
    </main>
  );
}
