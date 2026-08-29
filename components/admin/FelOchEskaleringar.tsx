"use client";

import Link from "next/link";

import { kallnamn, tolkaHandelse } from "@/lib/admin/handelsetext";
import { a, tidpunkt } from "@/lib/admin/sprak";
import type { EventRow, TenantRow } from "@/lib/data/admin";
import { useLocale } from "@/lib/i18n";

/**
 * Fel & eskaleringar i Kunder & Data — en SAMMANFATTNING av det som redan
 * loggas, inte ett eget felsystem.
 *
 * Källorna är de två som finns: platform_events (fel och varningar, samma
 * data som fliken Händelser) och ss_tickets med status 'escalated' (samma
 * villkor som veckoanalysen). Ingenting räknas fram ur något annat — den
 * fullständiga listan bor kvar under Händelser, och den här sektionen
 * länkar dit i stället för att bli en andra kopia av den.
 *
 * Att den länkar dit är också varför den använder SAMMA tolkning av
 * felmeddelandena (`lib/admin/handelsetext.ts`). Två vyer som visar samma fel
 * med olika formulering läser som två olika fel, och den som klickar vidare
 * ska känna igen raden hen kom ifrån.
 *
 * ## "minst"-prefixet
 *
 * Händelserna hämtas med ett tak. Är svaret fullt kan det finnas fler i
 * fönstret än vi såg, och då säger talet "minst N" i stället för att
 * presentera en trunkerad räkning som en fullständig.
 */

const FONSTER_DAGAR = 7;

export function FelOchEskaleringar({
  tenants,
  events,
  taketNaddes,
  nu
}: Readonly<{
  tenants: TenantRow[];
  events: EventRow[];
  taketNaddes: boolean;
  nu: number;
}>) {
  const { locale, text } = useLocale();

  // `nu` från servern och inte `Date.now()`: sektionen är en klientkomponent
  // och renderas två gånger. En händelse som ligger precis på sjudagarsgränsen
  // hade räknats med i den ena renderingen och inte i den andra — alltså ett
  // annat tal i rutan efter hydreringen än före.
  const grans = nu - FONSTER_DAGAR * 86_400_000;
  const nyliga = events.filter((e) => new Date(e.created_at).getTime() >= grans);
  const fel = nyliga.filter((e) => e.level === "error");
  const varningar = nyliga.filter((e) => e.level === "warning");

  // Samma gruppering som Händelser: källa + meddelande. Hundra rader av
  // samma trasiga källa är ETT problem.
  const grupper = new Map<string, { antal: number; senaste: EventRow }>();
  for (const event of fel) {
    const nyckel = `${event.source}::${event.message}`;
    const befintlig = grupper.get(nyckel);
    if (befintlig) befintlig.antal += 1;
    else grupper.set(nyckel, { antal: 1, senaste: event });
  }
  const toppfel = [...grupper.values()]
    .sort((x, y) => y.senaste.created_at.localeCompare(x.senaste.created_at))
    .slice(0, 5);

  const eskalerade = tenants.reduce((summa, t) => summa + (t.escalated ?? 0), 0);
  const minst = taketNaddes ? a("minst", locale) : "";

  return (
    <section className="mt-10 border-t border-ink/15 pt-4">
      <h2 className="kicker text-mineral">{a("felOchEskaleringar", locale)}</h2>
      <p className="mt-1.5 max-w-[70ch] text-[0.875rem] leading-6 text-mineral">
        {text({
          sv: "Sammanfattning av plattformens fellogg och eskalerade ärenden. Hela listan, med filter per nivå och kund, ligger under ",
          en: "A summary of the platform error log and escalated tickets. The full list, filterable by level and customer, lives under "
        })}
        <Link
          href="/admin/handelser"
          className="focus-ring text-ochre underline underline-offset-4"
        >
          {a("handelser", locale)}
        </Link>
        {text({
          sv: ". Felkolumnen i tabellen ovan visar samma fel per kund.",
          en: ". The error column in the table above shows the same errors per customer."
        })}
      </p>

      <div className="mt-4 grid gap-px overflow-hidden rounded-input border border-ink/15 bg-ink/15 sm:grid-cols-3">
        <Nyckeltal
          etikett={text({
            sv: `Fel senaste ${FONSTER_DAGAR} dagarna`,
            en: `Errors in the last ${FONSTER_DAGAR} days`
          })}
          varde={`${minst}${fel.length}`}
          varning={fel.length > 0}
        />
        <Nyckeltal
          etikett={text({
            sv: `Varningar senaste ${FONSTER_DAGAR} dagarna`,
            en: `Warnings in the last ${FONSTER_DAGAR} days`
          })}
          varde={`${minst}${varningar.length}`}
        />
        <Nyckeltal
          etikett={a("eskaleradeArenden", locale)}
          varde={String(eskalerade)}
          rad={a("allaKunderTotalt", locale)}
        />
      </div>

      {toppfel.length === 0 ? (
        <p className="mt-4 text-[0.875rem] text-mineral">
          {text({
            sv: `Inga fel de senaste ${FONSTER_DAGAR} dagarna. Det är det önskade tillståndet.`,
            en: `No errors in the last ${FONSTER_DAGAR} days. That is the desired state.`
          })}
        </p>
      ) : (
        <ul className="mt-4">
          {toppfel.map(({ antal: forekomster, senaste }) => {
            const tolkning = tolkaHandelse(senaste.message);
            return (
              <li key={senaste.id} className="min-w-0 border-t border-ink/10 py-4">
                <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
                  {/* Rubriken, inte råtexten — se filens docstring. */}
                  <span className="min-w-0 break-words text-[0.9375rem]">
                    {text(tolkning.rubrik)}
                  </span>
                  <span className="kicker shrink-0 text-warning">
                    {text(kallnamn(senaste.source))}
                    {forekomster > 1 ? ` · ${forekomster} ${a("ggr", locale)}` : ""}
                  </span>
                </div>
                <p className="mt-1 text-[0.8125rem] tabular-nums text-mineral">
                  {senaste.tenant_slug ?? a("plattformsniva", locale)} ·{" "}
                  {tidpunkt(senaste.created_at, locale)}
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
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function Nyckeltal({
  etikett,
  varde,
  rad,
  varning
}: Readonly<{ etikett: string; varde: string; rad?: string; varning?: boolean }>) {
  return (
    <div className="bg-paper px-4 py-3">
      <p className="kicker text-mineral">{etikett}</p>
      <p
        className={`mt-1 font-display text-[1.375rem] tabular-nums tracking-[-0.02em] ${
          varning ? "text-warning" : ""
        }`}
      >
        {varde}
      </p>
      {rad ? <p className="mt-0.5 text-[0.8125rem] leading-[1.45] text-ink/60">{rad}</p> : null}
    </div>
  );
}
