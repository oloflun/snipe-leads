import Link from "next/link";

import type { EventRow, TenantRow } from "@/lib/data/admin";

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
  taketNaddes
}: Readonly<{ tenants: TenantRow[]; events: EventRow[]; taketNaddes: boolean }>) {
  const grans = Date.now() - FONSTER_DAGAR * 86_400_000;
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
    .sort((a, b) => b.senaste.created_at.localeCompare(a.senaste.created_at))
    .slice(0, 5);

  const eskalerade = tenants.reduce((summa, t) => summa + (t.escalated ?? 0), 0);
  const minst = taketNaddes ? "minst " : "";

  return (
    <section className="mt-10 border-t border-ink/15 pt-4">
      <h2 className="kicker text-mineral">Fel &amp; eskaleringar</h2>
      <p className="mt-1.5 max-w-[70ch] text-[0.875rem] leading-6 text-mineral">
        Sammanfattning av plattformens fellogg och eskalerade ärenden. Hela
        listan, med filter per nivå och kund, ligger under{" "}
        <Link href="/admin/handelser" className="focus-ring text-ochre underline underline-offset-4">
          Händelser
        </Link>
        . Felkolumnen i tabellen ovan visar samma fel per kund.
      </p>

      <div className="mt-4 grid gap-px overflow-hidden rounded-input border border-ink/15 bg-ink/15 sm:grid-cols-3">
        <Nyckeltal
          etikett={`Fel senaste ${FONSTER_DAGAR} dagarna`}
          varde={`${minst}${fel.length}`}
          varning={fel.length > 0}
        />
        <Nyckeltal
          etikett={`Varningar senaste ${FONSTER_DAGAR} dagarna`}
          varde={`${minst}${varningar.length}`}
        />
        <Nyckeltal etikett="Eskalerade ärenden" varde={String(eskalerade)} rad="alla kunder, totalt" />
      </div>

      {toppfel.length === 0 ? (
        <p className="mt-4 text-[0.875rem] text-mineral">
          Inga fel de senaste {FONSTER_DAGAR} dagarna. Det är det önskade tillståndet.
        </p>
      ) : (
        <ul className="mt-4">
          {toppfel.map(({ antal, senaste }) => (
            <li key={senaste.id} className="min-w-0 border-t border-ink/10 py-4">
              <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
                <span className="min-w-0 break-words text-[0.9375rem]">{senaste.message}</span>
                <span className="kicker shrink-0 text-warning">
                  {senaste.source}
                  {antal > 1 ? ` · ${antal} ggr` : ""}
                </span>
              </div>
              <p className="mt-1 text-[0.8125rem] tabular-nums text-mineral">
                {senaste.tenant_slug ?? "plattformsnivå"} ·{" "}
                {senaste.created_at.slice(0, 19).replace("T", " ")}
                {senaste.run_id ? (
                  <>
                    {" · "}
                    <Link
                      href={`/admin/korningar/${senaste.run_id}`}
                      className="focus-ring underline underline-offset-4 hover:text-ochre"
                    >
                      till körningen
                    </Link>
                  </>
                ) : null}
              </p>
            </li>
          ))}
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
