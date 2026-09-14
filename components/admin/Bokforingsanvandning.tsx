import type { RunRow } from "@/lib/data/admin";

/**
 * Bokföringsagentens användning, per kund.
 *
 * ## Varför den räknar ur `agent_runs` och inte ur en egen tabell
 *
 * Varje avläst underlag och varje chattsvar loggas redan till `agent_runs`
 * med `agent_type="bookkeeping"` — det är samma revisionslogg som leads och
 * support skriver till, och den fanns innan den här vyn. En egen räknartabell
 * hade varit en andra sanning som glider isär med den första, och den som
 * glider är alltid räknaren.
 *
 * ## Hur en uppladdning skiljs från en chattfråga
 *
 * De två skriver olika `step_log`. Uppladdningen skriver avläsningsstegets
 * spår (`snajp:bokforing-avlasning`), chatten skriver en rad märkt
 * `snajp:bokforing-chatt`.
 *
 * Fältet läses som TEXT och inte som en struktur, med flit: `step_log` är
 * jsonb och har nått frontenden som en sträng förr — det är precis den buggen
 * som tog ner leads-vyn (`score_breakdown`, commit 7acd94b) och adminytans
 * spårvy innan dess. En `JSON.stringify` som redan tål båda formerna är
 * billigare än en tredje upptäckt av samma sak.
 */

function arChatt(run: RunRow): boolean {
  try {
    return JSON.stringify(run.step_log ?? "").includes("bokforing-chatt");
  } catch {
    return false;
  }
}

type Rad = {
  kund: string;
  uppladdningar: number;
  fragor: number;
  senast: string | null;
};

function summera(runs: RunRow[]): { rader: Rad[]; uppladdningar: number; fragor: number } {
  const perKund = new Map<string, Rad>();

  for (const run of runs) {
    const kund = run.tenant_slug || "okänd";
    const rad = perKund.get(kund) ?? { kund, uppladdningar: 0, fragor: 0, senast: null };
    if (arChatt(run)) rad.fragor += 1;
    else rad.uppladdningar += 1;
    // Körningarna kommer nyast först från backenden, men den ordningen är
    // backendens och inte ett kontrakt. Vi jämför i stället.
    if (!rad.senast || run.created_at > rad.senast) rad.senast = run.created_at;
    perKund.set(kund, rad);
  }

  const rader = [...perKund.values()].sort(
    (a, b) => b.uppladdningar + b.fragor - (a.uppladdningar + a.fragor)
  );
  return {
    rader,
    uppladdningar: rader.reduce((s, r) => s + r.uppladdningar, 0),
    fragor: rader.reduce((s, r) => s + r.fragor, 0)
  };
}

function Matt({ etikett, varde }: Readonly<{ etikett: string; varde: number | string }>) {
  return (
    <div className="border-y border-ink/15 py-4">
      <p className="kicker text-mineral">{etikett}</p>
      <p className="num mt-2 font-display text-[2rem] leading-none tracking-[-0.02em]">{varde}</p>
    </div>
  );
}

export function Bokforingsanvandning({ runs }: Readonly<{ runs: RunRow[] }>) {
  const { rader, uppladdningar, fragor } = summera(runs);

  if (runs.length === 0) {
    return (
      <p className="mt-8 max-w-[70ch] text-[15px] leading-7 text-ink/65">
        Ingen bokföringskörning är loggad ännu. Så fort en kund laddar upp sitt
        första underlag eller ställer en fråga till assistenten dyker den upp här.
      </p>
    );
  }

  return (
    <div className="mt-8">
      <div className="grid gap-x-10 sm:grid-cols-3">
        <Matt etikett="Uppladdade underlag" varde={uppladdningar} />
        <Matt etikett="Frågor till assistenten" varde={fragor} />
        <Matt etikett="Kunder som använt den" varde={rader.length} />
      </div>

      <table className="mt-10 w-full text-[15px]">
        <thead>
          <tr className="border-b border-ink/15 text-left">
            <th className="kicker py-2 font-normal text-mineral">Kund</th>
            <th className="kicker py-2 text-right font-normal text-mineral">Underlag</th>
            <th className="kicker py-2 text-right font-normal text-mineral">Frågor</th>
            <th className="kicker py-2 text-right font-normal text-mineral">Senast</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ink/10">
          {rader.map((rad) => (
            <tr key={rad.kund}>
              <td className="py-3 font-mono text-[13px]">{rad.kund}</td>
              <td className="num py-3 text-right">{rad.uppladdningar}</td>
              <td className="num py-3 text-right">{rad.fragor}</td>
              <td className="py-3 text-right text-[13px] text-mineral">
                {rad.senast ? rad.senast.slice(0, 16).replace("T", " ") : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="mt-6 max-w-[70ch] text-[13px] leading-6 text-mineral">
        Räknat ur `agent_runs` med agent_type=bookkeeping. En rad per körning:
        ett uppladdat underlag eller en fråga till assistenten. Siffrorna är
        alltså aktivitet, inte fakturerbar volym.
      </p>
    </div>
  );
}
