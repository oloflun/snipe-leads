"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";
import { btnLiten, btnSecondary, meta } from "@/components/ui";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Sidindelning för leadslistorna (Sebbe 2026-11-15: "det får inte lagga,
 * hacka eller gå långsamt oavsett").
 *
 * Med 2 600 leads i listan ritade Iris-listan 5 200 rader (tabellen OCH
 * korten, den ena dold med CSS), varje rad med ett statusval på tio
 * alternativ, och varje klick i en kryssruta ritade om alla. Listorna håller
 * nu hela urvalet i minnet — filtren, Markera alla och massåtgärderna gäller
 * fortfarande alla leads — men bara en sida åt gången står i sidan.
 */

/** Rader per sida. Lagom för att skumma, och för att varje klick ska vara omedelbart. */
export const SIDSTORLEK = 100;

/**
 * Den sida som visas, nollställd när `nyckel` byts (ett nytt filter, en
 * annan vy) och aldrig bortom sista sidan när listan krymper.
 */
export function useSida(antal: number, nyckel: string) {
  const [sida, setSida] = useState(0);
  const [forraNyckel, setForraNyckel] = useState(nyckel);
  // Nollställningen under renderingen (React-mönstret för state som följer
  // en prop), inte i en effekt: annars ritas först fel sida en gång.
  if (forraNyckel !== nyckel) {
    setForraNyckel(nyckel);
    setSida(0);
  }
  const antalSidor = Math.max(1, Math.ceil(antal / SIDSTORLEK));
  const aktuell = Math.min(sida, antalSidor - 1);
  return {
    sida: aktuell,
    antalSidor,
    fran: aktuell * SIDSTORLEK,
    till: Math.min(antal, (aktuell + 1) * SIDSTORLEK),
    setSida
  };
}

function prenumerera(mediafraga: string) {
  return (andrad: () => void) => {
    const mq = window.matchMedia(mediafraga);
    mq.addEventListener("change", andrad);
    return () => mq.removeEventListener("change", andrad);
  };
}

const BRED = "(min-width: 1024px)";
const prenumereraBred = prenumerera(BRED);

/**
 * Sant från Tailwinds `lg` (1024 px). Listorna ritar då tabellen och annars
 * korten — EN av dem, i stället för båda med den ena dold. Servern och första
 * renderingen säger falskt; listorna har ändå inga rader förrän de hämtats.
 */
export function useBredSkarm(): boolean {
  return useSyncExternalStore(
    prenumereraBred,
    () => window.matchMedia(BRED).matches,
    () => false
  );
}

/** "Visar 1–100 av 2 597" med Föregående och Nästa. Ingenting när allt får plats. */
export function Sidvaljare({
  antal,
  sida,
  antalSidor,
  fran,
  till,
  onSida,
  className
}: Readonly<{
  antal: number;
  sida: number;
  antalSidor: number;
  fran: number;
  till: number;
  onSida: (sida: number) => void;
  className?: string;
}>) {
  const { text, locale } = useLocale();
  if (antalSidor <= 1) return null;
  const tal = (n: number) => n.toLocaleString(locale === "en" ? "en-GB" : "sv-SE");
  return (
    <nav
      aria-label={text({ sv: "Sidor", en: "Pages" })}
      className={cn("flex flex-wrap items-center justify-between gap-x-4 gap-y-2", className)}
    >
      <p className={cn(meta, "num tabular-nums")} aria-live="polite">
        {text({
          sv: `Visar ${tal(fran + 1)}–${tal(till)} av ${tal(antal)}`,
          en: `Showing ${tal(fran + 1)}–${tal(till)} of ${tal(antal)}`
        })}
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={sida === 0}
          onClick={() => onSida(sida - 1)}
          className={cn(btnSecondary, btnLiten, "disabled:opacity-50")}
        >
          <ChevronLeft className="h-4 w-4" aria-hidden />
          {text({ sv: "Föregående", en: "Previous" })}
        </button>
        <span className={cn(meta, "num tabular-nums")}>
          {text({ sv: `Sida ${sida + 1} av ${antalSidor}`, en: `Page ${sida + 1} of ${antalSidor}` })}
        </span>
        <button
          type="button"
          disabled={sida >= antalSidor - 1}
          onClick={() => onSida(sida + 1)}
          className={cn(btnSecondary, btnLiten, "disabled:opacity-50")}
        >
          {text({ sv: "Nästa", en: "Next" })}
          <ChevronRight className="h-4 w-4" aria-hidden />
        </button>
      </div>
    </nav>
  );
}

/** Till listans överkant efter ett sidbyte, så att nästa sida börjar uppifrån. */
export function tillListansTopp(el: HTMLElement | null) {
  if (!el) return;
  const topp = el.getBoundingClientRect().top;
  if (topp < 0) el.scrollIntoView({ block: "start" });
}

/** Sidan som bär ett visst id, så att en länk till ett lead (?lead=) visar dess rad. */
export function useSidaFor(id: string | null, ids: readonly string[], setSida: (sida: number) => void) {
  const laddad = ids.length > 0;
  useEffect(() => {
    if (!id) return;
    const i = ids.indexOf(id);
    if (i >= 0) setSida(Math.floor(i / SIDSTORLEK));
    // Bara när id:t byts eller listan först kommit: en ny hämtning ska inte
    // flytta den som bläddrar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, laddad]);
}
