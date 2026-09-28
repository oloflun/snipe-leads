"use client";

import Link from "next/link";

import {
  Badge,
  Rad,
  Radlista,
  Sidhuvud,
  Tomt,
  etikett,
  flik,
  flikAktiv,
  flikInaktiv,
  meta,
  rubrikPanel,
} from "@/components/ui";
import { NIVANAMN, kallnamn, tolkaHandelse } from "@/lib/admin/handelsetext";
import { a, tidpunkt } from "@/lib/admin/sprak";
import type { EventRow } from "@/lib/data/admin";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

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

/**
 * Nivån som bricka. Bara fel och varningar får ton: färgas allt är ingen färg
 * en signal längre.
 *
 * Radens högerkant var en spärrad mono-rad ("INFO · ADMIN.IMPERSONATION ·
 * 11 GGR"). Nu står nivån som bricka, antalet i klartext bredvid, och källan
 * först i metaraden: källans namn när vi känner den, annars koden i mono,
 * eftersom en okänd kod är en maskin-id och inte en rubrik.
 */
const NIVATON: Record<string, "neutral" | "warn" | "danger"> = {
  error: "danger",
  warning: "warn",
  info: "neutral",
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
      <div className="mt-6">
        <Tomt>{niva ? a("ingaHandelserFilter", locale) : a("ingaHandelser", locale)}</Tomt>
      </div>
    );
  }

  return (
    <Radlista className="mt-6">
      {rader.map(({ antal: forekomster, senaste, forsta }) => {
        const tolkning = tolkaHandelse(senaste.message);
        const kalla = kallnamn(senaste.source);
        const nivanamn = text(
          NIVANAMN[senaste.level] ?? { sv: senaste.level, en: senaste.level },
        );

        return (
          <Rad key={senaste.id} className="min-w-0">
            <div className="flex min-w-0 flex-wrap items-start justify-between gap-x-6 gap-y-2">
              {/* Rubriken är en mening, inte en nyttolast. Se filens docstring.
                  h2 och inte h3: sidan har inga sektioner, så raden är nivån
                  under sidrubriken. Utseendet är radrubrikens. */}
              <h2 className={cn(rubrikPanel, "min-w-0 break-words")}>
                {text(tolkning.rubrik)}
              </h2>
              <div className="flex shrink-0 items-center gap-3">
                {forekomster > 1 ? (
                  <span className={cn(meta, "num")}>
                    {forekomster} {text({ sv: "gånger", en: "times" })}
                  </span>
                ) : null}
                <Badge tone={NIVATON[senaste.level] ?? "neutral"}>{nivanamn}</Badge>
              </div>
            </div>

            {tolkning.forklaring ? (
              <p className="mt-1.5 max-w-[78ch] text-[0.9375rem] leading-[1.6] text-ink-muted">
                {text(tolkning.forklaring)}
              </p>
            ) : null}

            <p className={cn(meta, "num mt-2 break-words")}>
              {kalla.sv === senaste.source ? (
                <span className="font-mono">{senaste.source}</span>
              ) : (
                text(kalla)
              )}
              {" · "}
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
              <details className="mt-2 min-w-0">
                <summary
                  className={cn(
                    etikett,
                    "focus-ring inline-flex min-h-9 cursor-pointer items-center rounded-input hover:text-ink",
                  )}
                >
                  {a("tekniskaDetaljer", locale)}
                </summary>
                <pre className="thin-scrollbar mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-input bg-paper2 p-3 font-mono text-[0.8125rem] leading-[1.55] text-ink-muted">
                  {tolkning.teknisk}
                </pre>
              </details>
            ) : null}
          </Rad>
        );
      })}
    </Radlista>
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
    <div className="mt-8 flex min-w-0 flex-wrap gap-2">
      {val.map(({ varde, etikett: namn }) => {
        const pa = niva === varde;
        return (
          <Link
            key={varde || "alla"}
            href={
              varde ? `/admin/handelser?level=${varde}` : "/admin/handelser"
            }
            aria-current={pa ? "page" : undefined}
            className={cn(flik, pa ? flikAktiv : flikInaktiv)}
          >
            {namn}
          </Link>
        );
      })}
    </div>
  );
}

/**
 * Sidrubriken. Klientsida av samma skäl som resten. Ingressen under den är
 * borta (F-016); `handelserIngress` i lib/admin/sprak.ts läses inte längre.
 */
export function Handelserubrik() {
  const { locale } = useLocale();
  return <Sidhuvud title={a("handelser", locale)} />;
}
