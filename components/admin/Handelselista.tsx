"use client";

import Link from "next/link";

import { NIVANAMN, kallnamn, tolkaHandelse } from "@/lib/admin/handelsetext";
import { a, tidpunkt } from "@/lib/admin/sprak";
import type { EventRow } from "@/lib/data/admin";
import { useLocale } from "@/lib/i18n";

/**
 * Notiscentret.
 *
 * ## Vad som var fel med den tidigare vyn
 *
 * Den skrev ut `latest.message` rakt av, och backendens `log_exception` sätter
 * meddelandet till `f"{type(error).__name__}: {error}"`. För ett LLM-fel är
 * `{error}` leverantörens hela JSON-svar — så listan bestod av rader som
 * började med `RateLimitError: Error code: 429 - [{'error': {'code': 429,` och
 * fortsatte i femton rader av `quotaDimensions` och `@type`. Tre av de fyra
 * synliga raderna sade samma sak: Gemini-kvoten är slut.
 *
 * Nu tolkar `lib/admin/handelsetext.ts` meddelandet till en rubrik och en
 * förklaring. Råtexten finns kvar bakom "Tekniska detaljer" — den som felsöker
 * behöver `retryDelay` i sekunder, och en vy som slänger den hade tvingat fram
 * ett databasanrop för att få tillbaka den.
 *
 * ## Grupperingen
 *
 * Grupperat på källa + meddelande, sorterat på senaste förekomst. Hundra rader
 * av samma trasiga skrapkälla är ETT problem, och en oplatt lista hade begravt
 * de nittionio andra felen under det. Sortering på senaste och inte på antal:
 * det som händer nu är mer intressant än det som hänt mest.
 */

/** Nivåns färg. Bara felen får varningsfärg — annars är ingen färg en signal. */
const NIVAFARG: Record<string, string> = {
  error: "text-warning",
  warning: "text-ochre",
  info: "text-mineral",
};

type Grupp = { antal: number; senaste: EventRow; forsta: EventRow };

export function Handelselista({
  events,
  niva,
}: Readonly<{ events: EventRow[]; niva: string }>) {
  const { locale, text } = useLocale();

  const grupper = new Map<string, Grupp>();
  for (const event of events) {
    const nyckel = `${event.source}::${event.message}`;
    const befintlig = grupper.get(nyckel);
    if (befintlig) {
      befintlig.antal += 1;
      // Listan kommer nyast först, så varje ny träff på samma nyckel är ÄLDRE
      // än den vi redan har. Att spara den ger "första förekomst" gratis, och
      // spannet är det som skiljer ett engångsfel från ett som pågått i en
      // vecka — samma antal, helt olika åtgärd.
      befintlig.forsta = event;
    } else {
      grupper.set(nyckel, { antal: 1, senaste: event, forsta: event });
    }
  }

  const rader = [...grupper.values()].sort((x, y) =>
    y.senaste.created_at.localeCompare(x.senaste.created_at),
  );

  if (rader.length === 0) {
    return (
      <p className="mt-8 border-t border-ink/15 pt-5 text-[15px] text-mineral">
        {niva ? a("ingaHandelserFilter", locale) : a("ingaHandelser", locale)}
      </p>
    );
  }

  return (
    <ul className="mt-8">
      {rader.map(({ antal: forekomster, senaste, forsta }) => {
        const tolkning = tolkaHandelse(senaste.message);
        const kalla = text(kallnamn(senaste.source));
        const nivanamn = text(
          NIVANAMN[senaste.level] ?? { sv: senaste.level, en: senaste.level },
        );

        return (
          <li key={senaste.id} className="min-w-0 border-t border-ink/15 py-5">
            <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
              {/* Rubriken är en mening, inte en nyttolast. Se filens docstring. */}
              <h2 className="min-w-0 break-words text-[16px] font-medium leading-[1.45]">
                {text(tolkning.rubrik)}
              </h2>
              <span
                className={`kicker shrink-0 ${NIVAFARG[senaste.level] ?? "text-mineral"}`}
              >
                {nivanamn} · {kalla}
                {forekomster > 1 ? ` · ${forekomster} ${a("ggr", locale)}` : ""}
              </span>
            </div>

            {tolkning.forklaring ? (
              <p className="mt-1.5 max-w-[78ch] text-[14px] leading-[1.6] text-ink/70">
                {text(tolkning.forklaring)}
              </p>
            ) : null}

            <p className="mt-2 text-[13px] tabular-nums text-mineral">
              {senaste.tenant_slug ?? a("plattformsniva", locale)} ·{" "}
              {a("senast", locale)} {tidpunkt(senaste.created_at, locale)}
              {/* Spannet visas bara när gruppen faktiskt sträcker sig över tid.
                  "första: samma tidpunkt som senast" är brus. */}
              {forekomster > 1 && forsta.created_at !== senaste.created_at ? (
                <>
                  {" · "}
                  {a("forsta", locale)} {tidpunkt(forsta.created_at, locale)}
                </>
              ) : null}
              {senaste.run_id ? (
                <>
                  {" · "}
                  <Link
                    href={`/admin/korningar/${senaste.run_id}`}
                    className="focus-ring underline underline-offset-4 hover:text-ochre"
                  >
                    {a("tillKorningen", locale)}
                  </Link>
                </>
              ) : null}
            </p>

            {/* Råtexten göms, kastas inte. Stängd som default: den som skummar
                listan letar efter VAD som händer, den som felsöker öppnar.

                Vippan visas BARA när råtexten säger något rubriken inte redan
                gör. En otolkad info-rad ("Kunduppgifter ändrade: orgnr,
                adress.") är sin egen råtext, och en vippa som fäller ut exakt
                den mening som står ovanför den är en vippa man slutar öppna —
                också på de rader där den hade haft något att visa. */}
            {tolkning.teknisk.trim() &&
            tolkning.teknisk.trim() !== text(tolkning.rubrik).trim() ? (
              <details className="mt-2 min-w-0 text-[13px]">
                <summary className="focus-ring inline-flex min-h-9 cursor-pointer items-center rounded-input text-mineral hover:text-ink">
                  {a("tekniskaDetaljer", locale)}
                </summary>
                <pre className="thin-scrollbar mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-input bg-paper2 p-3 font-mono text-[12px] leading-[1.55] text-ink/70">
                  {tolkning.teknisk}
                </pre>
              </details>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

/**
 * Nivåfiltret. Egen komponent bara för att den behöver `useLocale` — länkarna
 * är fortfarande vanliga href:ar, så filtret fungerar utan JS och delas som URL.
 */
export function Handelsefilter({ niva }: Readonly<{ niva: string }>) {
  const { locale } = useLocale();

  const val = [
    { varde: "", etikett: a("filterAlla", locale) },
    { varde: "error", etikett: a("filterFel", locale) },
    { varde: "warning", etikett: a("filterVarningar", locale) },
    { varde: "info", etikett: a("filterInfo", locale) },
  ];

  return (
    <div className="mt-6 flex min-w-0 flex-wrap gap-3">
      {val.map(({ varde, etikett }) => {
        const pa = niva === varde;
        return (
          <Link
            key={varde || "alla"}
            href={
              varde ? `/admin/handelser?level=${varde}` : "/admin/handelser"
            }
            aria-current={pa ? "page" : undefined}
            className={
              pa
                ? "focus-ring rounded-input border border-ochre bg-ochre/10 px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em]"
                : "focus-ring rounded-input border border-ink/15 px-4 py-2 font-mono text-[12px] uppercase tracking-[0.18em] text-mineral transition hover:border-ochre hover:text-ochre"
            }
          >
            {etikett}
          </Link>
        );
      })}
    </div>
  );
}

/** Sidrubriken och ingressen. Klientsida av samma skäl som resten. */
export function Handelserubrik() {
  const { locale } = useLocale();
  return (
    <>
      <h1 className="font-display text-4xl italic-disp tighten">
        {a("handelser", locale)}
      </h1>
      <p className="mt-3 max-w-[70ch] text-[15px] leading-7 text-mineral">
        {a("handelserIngress", locale)}
      </p>
    </>
  );
}
