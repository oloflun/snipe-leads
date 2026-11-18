"use client";

import { ExternalLink, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Rad, Radlista, btnLiten, btnPrimary, btnSecondary, meta, rubrikPanel } from "@/components/ui";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Webbplatsskanningens förlopp och förslag (migration 121).
 *
 * Onboardingen startar skanningen åt kunden (lib/snajp/webbplatsskanning.ts).
 * Den läser kundens sajt och skriver UTKAST: de blir artiklar först när kunden
 * lägger till dem, och kundens egna texter ändras aldrig. Förloppet visas där
 * kunden landar (Översikt › Kom igång) och förslagen här, i Kunskapsbas, och
 * båda finns kvar efter en omladdning (Antons regel 2026-10-10).
 */

export type Skanning = {
  id: string;
  webbplats: string;
  status: "pagar" | "klar" | "fel";
  startad_av: "onboarding" | "kund";
  sidor: number | null;
  lasbara_sidor: number | null;
  forslag: number;
  redan_fanns: number;
  fel: string | null;
  startad_at: string;
  klar_at: string | null;
};

export type Forslag = {
  id: string;
  title: string;
  content: string;
  category: string;
  source_url: string | null;
  confidence: number | null;
  varningar: string[];
};

type Lage = { skanning: Skanning | null; forslag: Forslag[] };

/** Hur ofta läget hämtas medan skanningen pågår. Den tar en till tre minuter. */
const POLL_MS = 4000;

/** Server- och skanningstext kommer på svenska; samma text i båda halvorna. */
const ord = (s: string): Localized => ({ sv: s, en: s });

/**
 * Backendens skanningsfel (snajp-support/app/api/kb.py) kommer på svenska.
 * De kända får sitt engelska par här, så att ett engelskt gränssnitt inte
 * visar en svensk mening (uppmätt 2026-11-18). Ett okänt fel visas som det är.
 */
const SKANNINGSFEL: Localized[] = [
  { sv: "Webbplatsen hittades inte.", en: "The website could not be found." },
  { sv: "Adressen går inte att läsa.", en: "The address cannot be read." },
  {
    sv: "Ange er egen webbplats. Register, annonsplattformar och exempeldomäner skannas inte.",
    en: "Enter your own website. Registers, ad platforms and example domains are not scanned."
  },
  {
    sv: "Sidorna lästes, men utkasten gick inte att skriva. Försök igen om en stund.",
    en: "The pages were read, but the drafts could not be written. Try again in a while."
  },
  { sv: "Skanningen avbröts. Försök igen om en stund.", en: "The scan was interrupted. Try again in a while." },
  { sv: "Skanningen avbröts. Försök igen.", en: "The scan was interrupted. Try again." }
];

export function skanningsfel(fel: string | null): Localized {
  const sv = fel ?? "";
  return SKANNINGSFEL.find((par) => par.sv === sv) ?? { sv, en: sv };
}

/**
 * Förslagets text som löptext i förhandsvisningen. Artikeln sparas som
 * markdown (agenten läser den så), men raden visade fetstilsstjärnor och
 * listtecken rakt av: "**Vilka uppgifter behandlas:** * **Kontouppgifter:**"
 * (genomgången 2026-11-18).
 */
export function klartext(markdown: string): string {
  return markdown
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/(\*\*|__)(.+?)\1/g, "$2")
    .replace(/^[ \t]*[*-][ \t]+/gm, "· ")
    .replace(/(?<=\s)\*[ \t]+(?=\S)/g, "· ")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Skanningens varningar kommer på svenska från backenden
 * (snajp-support/app/kb_skanning.py). De tre kända får ett engelskt par,
 * med talen och kategorierna inflyttade. Båda formerna av siffervarningen
 * matchas, eftersom förslag från före 2026-11-18 bär den äldre.
 */
const VARNINGAR: { monster: RegExp; en: (m: RegExpMatchArray) => string }[] = [
  {
    monster: /^Siffrorna (.+) står inte i källsidan(?:\.| \u2014) [Kk]ontrollera eller stryk(?: dem)?\.$/,
    en: (m) => `The figures ${m[1]} do not appear on the source page. Check or remove them.`
  },
  {
    monster: /^Modellen föreslog kategorin (.+), som inte finns(?:\. Den ändrades| \u2014 ändrad) till (.+)\.$/,
    en: (m) => `The model suggested the category ${m[1]}, which does not exist. It was changed to ${m[2]}.`
  },
  {
    monster: /^Simulerat utkast: sidtexten rakt av, ingen sammanfattning\.$/,
    en: () => "Simulated draft: the page text as is, no summary."
  }
];

export function varning(sv: string): Localized {
  for (const { monster, en } of VARNINGAR) {
    const traff = sv.match(monster);
    if (traff) {
      // Äldre förslag bär tankstreck; samma mening skrivs om till dagens form.
      const ny = sv.replace(/ \u2014 ([a-zåäö])/, (_, forsta: string) => `. ${forsta.toUpperCase()}`);
      return { sv: ny, en: en(traff) };
    }
  }
  return { sv, en: sv };
}

/** Värdnamnet, utan protokoll och www, för en läsbar rad. */
export function vard(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/**
 * Skanningens läge och de väntande förslagen. Hämtas igen var fjärde sekund
 * medan skanningen pågår, och stannar när den är klar.
 */
export function useWebbplatsskanning(aktiv = true) {
  const [lage, setLage] = useState<Lage | null>(null);
  const [fel, setFel] = useState<string | null>(null);

  const ladda = useCallback(async () => {
    try {
      const svar = await fetch("/api/snajp-support/kb/forslag", { cache: "no-store" });
      const kropp = await readJsonBody<Lage & { error?: string; detail?: string }>(svar);
      if (!svar.ok) throw new Error(kropp?.detail ?? kropp?.error ?? `${svar.status}`);
      setLage({ skanning: kropp?.skanning ?? null, forslag: kropp?.forslag ?? [] });
      setFel(null);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    }
  }, []);

  useEffect(() => {
    if (aktiv) void ladda();
  }, [aktiv, ladda]);

  const pagar = lage?.skanning?.status === "pagar";
  useEffect(() => {
    if (!aktiv || !pagar) return;
    const tid = window.setInterval(() => void ladda(), POLL_MS);
    return () => window.clearInterval(tid);
  }, [aktiv, pagar, ladda]);

  return { lage, fel, ladda };
}

const T = {
  rubrik: { sv: "Förslag från er webbplats", en: "Suggestions from your website" },
  pagar: {
    sv: "Vi läser {sajt} och skriver förslag till kunskapsbasen. Det brukar ta en till tre minuter, och ni kan lämna sidan under tiden.",
    en: "We are reading {sajt} and writing suggestions for the knowledge base. It usually takes one to three minutes, and you can leave this page meanwhile."
  },
  ingress: {
    sv: "Skrivna ur {sajt}. De blir artiklar först när ni lägger till dem, och era egna texter ändras inte.",
    en: "Written from {sajt}. They become articles only when you add them, and your own texts are never changed."
  },
  klarInget: {
    sv: "Skanningen av {sajt} är klar. Den läste {sidor} sidor men hittade inget som inte redan finns i kunskapsbasen.",
    en: "The scan of {sajt} is done. It read {sidor} pages but found nothing that is not already in the knowledge base."
  },
  klarAllt: {
    sv: "Alla förslag från {sajt} är hanterade.",
    en: "All suggestions from {sajt} have been handled."
  },
  felRubrik: { sv: "Webbplatsen gick inte att läsa", en: "The website could not be read" },
  forsokIgen: { sv: "Försök igen", en: "Try again" },
  laggTill: { sv: "Lägg till", en: "Add" },
  laggTillAlla: { sv: "Lägg till alla", en: "Add all" },
  avvisa: { sv: "Avvisa", en: "Dismiss" },
  kalla: { sv: "Källa", en: "Source" },
  kontrollera: { sv: "Kontrollera", en: "Check" },
  tillagdEtt: { sv: "Förslaget lades till i kunskapsbasen.", en: "The suggestion was added to the knowledge base." },
  tillagda: { sv: "{n} förslag lades till i kunskapsbasen.", en: "{n} suggestions were added to the knowledge base." },
  fannsRedanEtt: {
    sv: "Ett förslag fanns redan med samma rubrik och lades inte till.",
    en: "One suggestion already existed with the same title and was not added."
  },
  fannsRedan: {
    sv: "{n} förslag fanns redan med samma rubrik och lades inte till.",
    en: "{n} suggestions already existed with the same title and were not added."
  },
  hamtaFel: { sv: "Kunde inte hämta förslagen: {fel}", en: "Could not load the suggestions: {fel}" }
} satisfies Record<string, Localized>;

function fyll(mall: string, varden: Record<string, string | number>): string {
  return mall.replace(/\{(\w+)\}/g, (_, nyckel: string) => String(varden[nyckel] ?? ""));
}

/** Panelen i Kunskapsbas. `onAndrat` laddar om artikellistan efter ett tillägg. */
export function WebbplatsForslag({ onAndrat }: Readonly<{ onAndrat: () => void }>) {
  const { text } = useLocale();
  const { lage, fel, ladda } = useWebbplatsskanning();
  const [upptagen, setUpptagen] = useState<string | null>(null);
  const [besked, setBesked] = useState<Localized | null>(null);
  const [atgardsfel, setAtgardsfel] = useState<Localized | null>(null);

  const skanning = lage?.skanning ?? null;
  const forslag = lage?.forslag ?? [];
  const sajt = skanning ? vard(skanning.webbplats) : "";

  async function besluta(ids: string[], beslut: "lagg_till" | "avvisa", nyckel: string) {
    setUpptagen(nyckel);
    setBesked(null);
    setAtgardsfel(null);
    try {
      const svar = await fetch("/api/snajp-support/kb/forslag/beslut", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids, beslut })
      });
      const kropp = await readJsonBody<{ tillagda?: string[]; fanns_redan?: string[]; detail?: string; error?: string }>(svar);
      if (!svar.ok) throw new Error(kropp?.detail ?? kropp?.error ?? `${svar.status}`);
      const tillagda = kropp?.tillagda?.length ?? 0;
      const redan = kropp?.fanns_redan?.length ?? 0;
      if (beslut === "lagg_till") {
        const delar = [
          tillagda === 1 ? text(T.tillagdEtt) : tillagda ? fyll(text(T.tillagda), { n: tillagda }) : "",
          redan === 1 ? text(T.fannsRedanEtt) : redan ? fyll(text(T.fannsRedan), { n: redan }) : ""
        ].filter(Boolean);
        if (delar.length) setBesked(ord(delar.join(" ")));
        if (tillagda) onAndrat();
      }
      await ladda();
    } catch (orsak) {
      setAtgardsfel(ord(felmeddelande(orsak)));
    } finally {
      setUpptagen(null);
    }
  }

  async function skannaIgen() {
    if (!skanning) return;
    setUpptagen("skanna");
    setAtgardsfel(null);
    try {
      const svar = await fetch("/api/snajp-support/kb/skanna", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ webbplats: skanning.webbplats, spara: true, startad_av: "kund" })
      });
      if (!svar.ok && svar.status !== 422) {
        const kropp = await readJsonBody<{ detail?: string; error?: string }>(svar);
        throw new Error(kropp?.detail ?? kropp?.error ?? `${svar.status}`);
      }
      await ladda();
    } catch (orsak) {
      setAtgardsfel(ord(felmeddelande(orsak)));
    } finally {
      setUpptagen(null);
    }
  }

  // Ingen skanning har körts: inget att visa. Kunskapsbasen fungerar som förut.
  if (!skanning && !fel) return null;

  return (
    <section aria-labelledby="webbplatsforslag" className="rounded-card border border-ink/15 bg-paper p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h3 id="webbplatsforslag" className={rubrikPanel}>
          {text(T.rubrik)}
          {forslag.length ? ` (${forslag.length})` : ""}
        </h3>
        {forslag.length > 1 ? (
          <button
            type="button"
            disabled={upptagen !== null}
            onClick={() => void besluta(forslag.map((f) => f.id), "lagg_till", "alla")}
            className={btnPrimary}
          >
            {upptagen === "alla" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
            {text(T.laggTillAlla)}
          </button>
        ) : null}
      </div>

      {fel ? (
        <p role="alert" className="mt-2 text-[0.9375rem] text-danger">
          {fyll(text(T.hamtaFel), { fel })}
        </p>
      ) : null}

      {/* Överst, under rubriken: listan kan vara lång, och ett besked längst
          ner syntes inte på mobilen (uppmätt i development 2026-11-18). */}
      {besked ? (
        <p role="status" className="mt-2 text-[0.9375rem] font-medium text-moss">
          {text(besked)}
        </p>
      ) : null}
      {atgardsfel ? (
        <p role="alert" className="mt-2 break-words text-[0.9375rem] text-danger">
          {text(atgardsfel)}
        </p>
      ) : null}

      {skanning?.status === "pagar" ? (
        <p role="status" className="mt-2 flex max-w-[70ch] items-start gap-2 text-[0.9375rem] leading-6 text-ink-muted">
          <Loader2 className="mt-1 h-4 w-4 shrink-0 animate-spin text-warning" aria-hidden />
          {fyll(text(T.pagar), { sajt })}
        </p>
      ) : null}

      {skanning?.status === "fel" ? (
        <div className="mt-2">
          <p className="text-[0.9375rem] font-medium text-danger">
            {text(T.felRubrik)}: {sajt}
          </p>
          {skanning.fel ? (
            <p className="mt-1 text-[0.9375rem] text-ink-muted">{text(skanningsfel(skanning.fel))}</p>
          ) : null}
          <button
            type="button"
            disabled={upptagen !== null}
            onClick={() => void skannaIgen()}
            className={cn(btnSecondary, "mt-3")}
          >
            {upptagen === "skanna" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
            {text(T.forsokIgen)}
          </button>
        </div>
      ) : null}

      {skanning?.status === "klar" && forslag.length === 0 ? (
        <p className="mt-2 max-w-[70ch] text-[0.9375rem] leading-6 text-ink-muted">
          {skanning.forslag === 0
            ? fyll(text(T.klarInget), { sajt, sidor: skanning.lasbara_sidor ?? skanning.sidor ?? 0 })
            : fyll(text(T.klarAllt), { sajt })}
        </p>
      ) : null}

      {forslag.length ? (
        <>
          <p className="mt-2 max-w-[70ch] text-[0.9375rem] leading-6 text-ink-muted">{fyll(text(T.ingress), { sajt })}</p>
          <Radlista ariaLabel={text(T.rubrik)} className="mt-4">
            {forslag.map((f) => (
              <Rad key={f.id}>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <p className="text-[0.9375rem] font-medium">{f.title}</p>
                    <p className="mt-1 line-clamp-3 max-w-[80ch] text-[0.875rem] leading-6 text-ink-muted">
                      {klartext(f.content)}
                    </p>
                    {f.varningar.length ? (
                      <p className="mt-1 max-w-[80ch] text-[0.8125rem] leading-5 text-warning">
                        {text(T.kontrollera)}: {f.varningar.map((v) => text(varning(v))).join(" ")}
                      </p>
                    ) : null}
                    {f.source_url ? (
                      <a
                        href={f.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={cn(meta, "focus-ring mt-1 inline-flex items-center gap-1 rounded-input underline underline-offset-4 hover:text-ink")}
                      >
                        {text(T.kalla)}: {vard(f.source_url)}
                        {(() => {
                          try {
                            const sokvag = new URL(f.source_url).pathname;
                            return sokvag !== "/" ? sokvag : "";
                          } catch {
                            return "";
                          }
                        })()}
                        <ExternalLink className="h-3 w-3" aria-hidden />
                      </a>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <button
                      type="button"
                      disabled={upptagen !== null}
                      onClick={() => void besluta([f.id], "lagg_till", f.id)}
                      className={cn(btnSecondary, btnLiten)}
                    >
                      {upptagen === f.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
                      {text(T.laggTill)}
                    </button>
                    <button
                      type="button"
                      disabled={upptagen !== null}
                      onClick={() => void besluta([f.id], "avvisa", `${f.id}-avvisa`)}
                      className="focus-ring inline-flex h-9 items-center rounded-input px-3 text-[0.875rem] font-medium text-ink-muted hover:text-ink disabled:opacity-40"
                    >
                      {text(T.avvisa)}
                    </button>
                  </div>
                </div>
              </Rad>
            ))}
          </Radlista>
        </>
      ) : null}

    </section>
  );
}
