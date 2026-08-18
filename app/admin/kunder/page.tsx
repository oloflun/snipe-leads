import { listTenants, unwrap } from "@/lib/data/admin";

export const dynamic = "force-dynamic";

/**
 * Backenden ligger på Renders gratisnivå och tar upp till ~35 s att vakna.
 * Utan detta dödar Vercel renderingen mitt i uppvakningen. Se app/admin/page.tsx.
 */
export const maxDuration = 60;

/**
 * Kundlistan — avsiktligt magrare än Översikten.
 *
 * Översikten (/admin) svarar på "hur går det": intäkt, kostnad, marginal och
 * vilka kunder som kräver en åtgärd. Den här sidan svarar på "vilka är de":
 * namn, slug, volym och när vi senast såg liv. Två frågor som ställs vid olika
 * tillfällen, och en tabell som försöker svara på båda blir svår att skumma.
 *
 * Inga uppskattningar här — bara räknade tal ur agent_runs och ss_tickets.
 * Marginalen bor i Översikten, med sitt förbehåll.
 */

function datum(värde: string | null): string {
  if (!värde) return "—";
  const d = new Date(värde);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString("sv-SE");
}

export default async function Page() {
  const { data, error } = unwrap(await listTenants());

  if (error) {
    return (
      <div>
        <h1 className="font-display text-4xl tracking-[-0.03em]">Kunder</h1>
        <p role="alert" className="mt-6 max-w-[70ch] break-words text-[15px] text-danger">
          {error}
        </p>
      </div>
    );
  }

  const kunder = [...(data ?? [])].sort((a, b) => a.name.localeCompare(b.name, "sv"));

  return (
    <div>
      <h1 className="font-display text-4xl tracking-[-0.03em]">Kunder</h1>
      <p className="mt-3 max-w-[70ch] text-[15px] leading-7 text-mineral">
        Alla registrerade kunder med volym och senaste aktivitet. Ekonomin och
        hälsobedömningen ligger under Översikt.
      </p>

      {kunder.length === 0 ? (
        <p className="mt-10 text-[15px] text-mineral">Inga kunder registrerade ännu.</p>
      ) : (
        <div className="mt-10 overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-[15px]">
            <thead>
              <tr className="border-b border-ink/15 text-left">
                <th className="py-3 pr-6 font-medium text-mineral">Kund</th>
                <th className="py-3 pr-6 font-medium text-mineral">Slug</th>
                <th className="py-3 pr-6 text-right font-medium text-mineral">Ärenden</th>
                <th className="py-3 pr-6 text-right font-medium text-mineral">Körningar</th>
                <th className="py-3 pr-6 text-right font-medium text-mineral">Fel</th>
                <th className="py-3 text-right font-medium text-mineral">Senast aktiv</th>
              </tr>
            </thead>
            <tbody>
              {kunder.map((kund) => (
                <tr key={kund.id} className="border-b border-ink/8">
                  <td className="py-3 pr-6">{kund.name}</td>
                  <td className="py-3 pr-6 font-mono text-[13px] text-ink/55">
                    {kund.slug ?? <span className="text-danger">saknas</span>}
                  </td>
                  <td className="py-3 pr-6 text-right tabular-nums">{kund.tickets}</td>
                  <td className="py-3 pr-6 text-right tabular-nums">{kund.runs}</td>
                  <td className="py-3 pr-6 text-right tabular-nums">
                    {kund.errors > 0 ? <span className="text-danger">{kund.errors}</span> : "0"}
                  </td>
                  <td className="py-3 text-right tabular-nums text-ink/70">
                    {datum(kund.last_activity)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
