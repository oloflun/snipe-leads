import { panelKort } from "@/components/ui";
import { AdminText } from "@/components/admin/AdminText";
import { AgentAnvandning } from "@/components/admin/AgentAnvandning";
import { KostnadOversikt } from "@/components/admin/KostnadOversikt";

import { cn } from "@/lib/utils";
import { listRuns, unwrap, type RunRow } from "@/lib/data/admin";
import { AdminVyhuvud } from "@/components/admin/AdminVyhuvud";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

/**
 * Alla tre agenternas användning och AI-kostnad, per kund — EN flik i
 * stället för tre: Sebbe och Anton läser läget uppifrån och ner utan att
 * hoppa mellan sidor, och tre likadana flikar hade varit precis det rör
 * den här ytan inte ska vara.
 *
 * Leads är en FAMILJ av agent_types (research, outreach, svar, uppföljning
 * — storage.base.LEADS_BUDGET_AGENT_TYPES plus söksteget) och hämtas per
 * typ; support och bokföring är en typ var.
 */

const LEADS_TYPER = ["leads", "leads_research", "leads_outreach", "leads_svar", "leads_followup"];

/**
 * Backendens tak per anrop (snajp-support/app/api/admin.py, `min(limit, 200)`).
 * Utan `limit` gällde standardvärdet 50, och nyckeltalen räknade då bara de 50
 * senaste körningarna per agenttyp men stod där som totaler.
 * ponytail: tak 200, ett aggregat-endpoint i backenden om volymen växer förbi det.
 */
const TAK = 200;

// `sammandrag=true`: utan input/output/step_log. Hela raderna var 17,7 MB som
// serialiserades in i sidan (uppmätt 2026-10-09) för tabeller som bara läser
// tokens, kund och tid.

export default async function Page() {
  const [bokforing, support, ...leadsDelar] = await Promise.all([
    listRuns(`?agent_type=bookkeeping&limit=${TAK}&sammandrag=true`),
    listRuns(`?agent_type=support&limit=${TAK}&sammandrag=true`),
    ...LEADS_TYPER.map((typ) => listRuns(`?agent_type=${typ}&limit=${TAK}&sammandrag=true`))
  ]);

  const bok = unwrap(bokforing);
  const sup = unwrap(support);
  const leadsRuns: RunRow[] = [];
  let leadsFel: string | null = null;
  let leadsVidTaket = false;
  for (const del of leadsDelar) {
    const { data, error } = unwrap(del);
    if (error) leadsFel = error;
    leadsVidTaket ||= (data?.length ?? 0) >= TAK;
    leadsRuns.push(...(data ?? []));
  }

  // Sektionerna heter som i railen (Iris, Kundtjänst, Kvitton), inte som
  // agent_type-familjerna: samma agent ska inte ha två namn i samma app.
  const sektioner = [
    {
      rubrik: "railIris",
      fel: leadsFel,
      innehall: (
        <AgentAnvandning
          runs={leadsRuns}
          vidTaket={leadsVidTaket ? TAK : null}
          tomtext={{ sv: "Ingen leadskörning loggad ännu.", en: "No leads run logged yet." }}
        />
      )
    },
    {
      rubrik: "railKundtjanst",
      fel: sup.error,
      innehall: (
        <AgentAnvandning
          runs={sup.data ?? []}
          vidTaket={(sup.data?.length ?? 0) >= TAK ? TAK : null}
          tomtext={{ sv: "Ingen supportkörning loggad ännu.", en: "No support run logged yet." }}
        />
      )
    },
    {
      rubrik: "railKvitton",
      fel: bok.error,
      innehall: (
        <AgentAnvandning
          runs={bok.data ?? []}
          vidTaket={(bok.data?.length ?? 0) >= TAK ? TAK : null}
          delning="bokforing"
          tomtext={{ sv: "Ingen bokföringskörning loggad ännu.", en: "No bookkeeping run logged yet." }}
        />
      )
    }
  ];

  // Ingen ingress: att kostnaden är uppskattad står i nyckeltalets etikett, och
  // prisunderlaget bor i AgentAnvandning.tsx (PRISUNDERLAG).
  return (
    <div>
      <AdminVyhuvud grupp="logg" />

      {/* Översikternas layout (Sebbe 2026-10-07): de tre agenterna bredvid
          varandra överst, sedan en panel per agent med kunderna. */}
      <KostnadOversikt
        iris={{ runs: leadsFel ? [] : leadsRuns, vidTaket: leadsVidTaket }}
        kundtjanst={{ runs: sup.data ?? [], vidTaket: (sup.data?.length ?? 0) >= TAK }}
        kvitton={{ runs: bok.data ?? [], vidTaket: (bok.data?.length ?? 0) >= TAK }}
        tak={TAK}
      />

      <div className="mt-4 grid min-w-0 gap-4">
        {sektioner.map((sektion) => (
          <section key={sektion.rubrik} aria-labelledby={`agent-${sektion.rubrik}`} className={cn(panelKort, "min-w-0")}>
            <h2 id={`agent-${sektion.rubrik}`} className="mb-4 text-[1rem] font-semibold">
              <AdminText n={sektion.rubrik} />
            </h2>
            {sektion.fel ? (
              <p role="alert" className="max-w-[70ch] break-words text-[15px] text-danger">
                {sektion.fel}
              </p>
            ) : (
              sektion.innehall
            )}
          </section>
        ))}
      </div>
    </div>
  );
}
