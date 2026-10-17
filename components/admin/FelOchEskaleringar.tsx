"use client";

import Link from "next/link";

import { Panelrubrik } from "@/components/dashboard/OversiktPaneler";
import { Rad, Radlista, Tomt, etikett, meta, rubrikPanel, panelKort } from "@/components/ui";
import { kallnamn, tolkaHandelse } from "@/lib/admin/handelsetext";
import { a, tidpunkt } from "@/lib/admin/sprak";
import type { EventRow, TenantRow } from "@/lib/data/admin";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

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

  // Ingressen som stod här är borta (F-016). Att hela listan bor under
  // Händelser är nu sektionens åtgärd; att felkolumnen i kundtabellen visar
  // samma fel syns i tabellen själv. Raderna har samma anatomi som i
  // Händelselista.tsx: rubrik, antal i klartext till höger, källa först i
  // metaraden (namnet när vi känner källan, annars koden i mono).
  // Kortform sedan 2026-10-07 (Kunder i översikternas layout): samma tre tal
  // och samma topplista, i en panel bredvid provperioderna.
  const tal: { id: string; etikett: string; varde: string; notis?: string; varning?: boolean }[] = [
    {
      id: "fel",
      etikett: text({ sv: `Fel, ${FONSTER_DAGAR} dagar`, en: `Errors, ${FONSTER_DAGAR} days` }),
      varde: `${minst}${fel.length}`,
      varning: fel.length > 0
    },
    {
      id: "varningar",
      etikett: text({ sv: `Varningar, ${FONSTER_DAGAR} dagar`, en: `Warnings, ${FONSTER_DAGAR} days` }),
      varde: `${minst}${varningar.length}`
    },
    {
      id: "eskalerade",
      etikett: a("eskaleradeArenden", locale),
      varde: String(eskalerade),
      notis: a("allaKunderTotalt", locale)
    }
  ];

  return (
    <section aria-labelledby="kunder-fel" className={cn(panelKort, "min-w-0")}>
      <Panelrubrik
        id="kunder-fel"
        titel={{ sv: a("felOchEskaleringar", "sv"), en: a("felOchEskaleringar", "en") }}
        action={
          <Link
            href="/admin/handelser"
            className="focus-ring text-[0.8125rem] font-medium text-ink-muted underline underline-offset-4 hover:text-ochre"
          >
            {text({ sv: "Alla händelser", en: "All events" })}
          </Link>
        }
      />
      <dl className="grid grid-cols-3 gap-3 border-b border-ink/10 pb-4">
        {tal.map((t) => (
          <div key={t.id} className="min-w-0">
            <dt className={cn(etikett, "line-clamp-2")}>{t.etikett}</dt>
            <dd className={cn("num mt-1 text-[1.5rem] font-semibold leading-none tabular-nums", t.varning ? "text-warning" : "text-ink")}>
              {t.varde}
            </dd>
            {t.notis ? <dd className={cn(meta, "mt-1")}>{t.notis}</dd> : null}
          </div>
        ))}
      </dl>

      {toppfel.length === 0 ? (
        <div className="mt-4">
          <Tomt>
            {text({
              sv: `Inga fel de senaste ${FONSTER_DAGAR} dagarna.`,
              en: `No errors in the last ${FONSTER_DAGAR} days.`
            })}
          </Tomt>
        </div>
      ) : (
        <Radlista className="mt-2">
          {toppfel.map(({ antal: forekomster, senaste }) => {
            const tolkning = tolkaHandelse(senaste.message);
            const kalla = kallnamn(senaste.source);
            return (
              <Rad key={senaste.id} className="min-w-0">
                <div className="flex min-w-0 flex-wrap items-start justify-between gap-x-6 gap-y-1">
                  {/* Rubriken, inte råtexten. Se filens docstring. */}
                  <h3 className={cn(rubrikPanel, "min-w-0 break-words")}>
                    {text(tolkning.rubrik)}
                  </h3>
                  {forekomster > 1 ? (
                    <span className={cn(meta, "num shrink-0")}>
                      {forekomster} {text({ sv: "gånger", en: "times" })}
                    </span>
                  ) : null}
                </div>
                <p className={cn(meta, "num mt-1 break-words")}>
                  {kalla.sv === senaste.source ? (
                    <span className="font-mono">{senaste.source}</span>
                  ) : (
                    text(kalla)
                  )}
                  {" · "}
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
              </Rad>
            );
          })}
        </Radlista>
      )}
    </section>
  );
}
