import { AgentAnvandning, USD_PER_MILJON } from "@/components/admin/AgentAnvandning";
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

export default async function Page() {
  const [bokforing, support, ...leadsDelar] = await Promise.all([
    listRuns("?agent_type=bookkeeping"),
    listRuns("?agent_type=support"),
    ...LEADS_TYPER.map((typ) => listRuns(`?agent_type=${typ}`))
  ]);

  const bok = unwrap(bokforing);
  const sup = unwrap(support);
  const leadsRuns: RunRow[] = [];
  let leadsFel: string | null = null;
  for (const del of leadsDelar) {
    const { data, error } = unwrap(del);
    if (error) leadsFel = error;
    leadsRuns.push(...(data ?? []));
  }

  const sektioner = [
    {
      rubrik: "Leads",
      fel: leadsFel,
      innehall: (
        <AgentAnvandning
          runs={leadsRuns}
          tomtext="Ingen leadskörning loggad ännu."
        />
      )
    },
    {
      rubrik: "Support",
      fel: sup.error,
      innehall: (
        <AgentAnvandning
          runs={sup.data ?? []}
          tomtext="Ingen supportkörning loggad ännu."
        />
      )
    },
    {
      rubrik: "Bokföring",
      fel: bok.error,
      innehall: (
        <AgentAnvandning
          runs={bok.data ?? []}
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

  return (
    <div>
      <h1 className="font-display text-4xl italic-disp tighten">Agentanvändning</h1>
      <p className="mt-4 max-w-[70ch] text-[15px] leading-7 text-ink/65">
        Hur mycket varje agent används och vad AI-anropen uppskattningsvis
        kostar, per kund. Kostnaden räknas på Vertex listpris för Gemini 2.5
        Flash (${USD_PER_MILJON.in}/M in, ${USD_PER_MILJON.ut}/M ut, avläst
        2026-09-15) — riktmärke, inte Googles faktura.
      </p>

      {sektioner.map((sektion) => (
        <section key={sektion.rubrik} className="mt-12">
          <h2 className="font-display text-2xl tighten">{sektion.rubrik}</h2>
          {sektion.fel ? (
            <p role="alert" className="mt-4 max-w-[70ch] break-words text-[15px] text-danger">
              {sektion.fel}
            </p>
          ) : (
            sektion.innehall
          )}
        </section>
      ))}
    </div>
  );
}
