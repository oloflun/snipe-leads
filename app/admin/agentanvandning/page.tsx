import { AgentAnvandning } from "@/components/admin/AgentAnvandning";
import { Sektion, Sidhuvud } from "@/components/ui";
import { listRuns, unwrap, type RunRow } from "@/lib/data/admin";

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

function arBokforingschatt(run: RunRow): boolean {
  try {
    return JSON.stringify(run.step_log ?? "").includes("bokforing-chatt");
  } catch {
    return false;
  }
}

/**
 * Backendens tak per anrop (snajp-support/app/api/admin.py, `min(limit, 200)`).
 * Utan `limit` gällde standardvärdet 50, och nyckeltalen räknade då bara de 50
 * senaste körningarna per agenttyp men stod där som totaler.
 * ponytail: tak 200, ett aggregat-endpoint i backenden om volymen växer förbi det.
 */
const TAK = 200;

export default async function Page() {
  const [bokforing, support, ...leadsDelar] = await Promise.all([
    listRuns(`?agent_type=bookkeeping&limit=${TAK}`),
    listRuns(`?agent_type=support&limit=${TAK}`),
    ...LEADS_TYPER.map((typ) => listRuns(`?agent_type=${typ}&limit=${TAK}`))
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
      rubrik: "Iris",
      fel: leadsFel,
      innehall: (
        <AgentAnvandning
          runs={leadsRuns}
          vidTaket={leadsVidTaket ? TAK : null}
          tomtext="Ingen leadskörning loggad ännu."
        />
      )
    },
    {
      rubrik: "Kundtjänst",
      fel: sup.error,
      innehall: (
        <AgentAnvandning
          runs={sup.data ?? []}
          vidTaket={(sup.data?.length ?? 0) >= TAK ? TAK : null}
          tomtext="Ingen supportkörning loggad ännu."
        />
      )
    },
    {
      rubrik: "Kvitton",
      fel: bok.error,
      innehall: (
        <AgentAnvandning
          runs={bok.data ?? []}
          vidTaket={(bok.data?.length ?? 0) >= TAK ? TAK : null}
          delning={{
            etikettA: "Underlag",
            etikettB: "Frågor",
            arB: arBokforingschatt
          }}
          tomtext="Ingen bokföringskörning loggad ännu."
        />
      )
    }
  ];

  // Ingen ingress: att kostnaden är uppskattad står i nyckeltalets etikett, och
  // prisunderlaget bor i AgentAnvandning.tsx (PRISUNDERLAG).
  return (
    <div>
      <Sidhuvud title="Agentanvändning" />

      <div className="mt-8">
        {sektioner.map((sektion) => (
          <Sektion key={sektion.rubrik} title={sektion.rubrik}>
            {sektion.fel ? (
              <p role="alert" className="max-w-[70ch] break-words text-[15px] text-danger">
                {sektion.fel}
              </p>
            ) : (
              sektion.innehall
            )}
          </Sektion>
        ))}
      </div>
    </div>
  );
}
