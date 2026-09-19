import type { RunRow } from "@/lib/data/admin";

/**
 * En agents användning och AI-kostnad, per kund — samma vy för bokföring,
 * leads och support (sidan /admin/agentanvandning staplar tre av den här).
 *
 * Räknar ur `agent_runs`, aldrig ur en egen räknartabell — samma skäl som
 * alltid: en andra sanning glider, och den som glider är räknaren.
 *
 * Kostnaden är en UPPSKATTNING enligt Vertex listpris för Gemini 2.5 Flash
 * (avläst 2026-09-15) — riktmärke för er egen marginal, inte Googles faktura.
 * Byts modellen i driften ska talen bytas här.
 */

export const USD_PER_MILJON = { in: 0.3, ut: 2.5 };

export function kostnadUsd(tokensIn: number, tokensUt: number): number {
  return (tokensIn * USD_PER_MILJON.in + tokensUt * USD_PER_MILJON.ut) / 1_000_000;
}

function usd(varde: number): string {
  return `$${varde.toFixed(2)}`;
}

export type Slagdelning = {
  etikettA: string;
  etikettB: string;
  /** true = körningen räknas till B-kolumnen. */
  arB: (run: RunRow) => boolean;
};

type Rad = {
  kund: string;
  a: number;
  b: number;
  tokensIn: number;
  tokensUt: number;
  senast: string | null;
};

function summera(runs: RunRow[], delning: Slagdelning | null) {
  const perKund = new Map<string, Rad>();
  for (const run of runs) {
    const kund = run.tenant_slug || "okänd";
    const rad =
      perKund.get(kund) ?? { kund, a: 0, b: 0, tokensIn: 0, tokensUt: 0, senast: null };
    if (delning?.arB(run)) rad.b += 1;
    else rad.a += 1;
    rad.tokensIn += run.tokens_in ?? 0;
    rad.tokensUt += run.tokens_out ?? 0;
    if (!rad.senast || run.created_at > rad.senast) rad.senast = run.created_at;
    perKund.set(kund, rad);
  }
  const rader = [...perKund.values()].sort(
    (x, y) =>
      kostnadUsd(y.tokensIn, y.tokensUt) - kostnadUsd(x.tokensIn, x.tokensUt) ||
      y.a + y.b - (x.a + x.b)
  );
  const sum = (valj: (r: Rad) => number) => rader.reduce((s, r) => s + valj(r), 0);
  return {
    rader,
    a: sum((r) => r.a),
    b: sum((r) => r.b),
    tokensIn: sum((r) => r.tokensIn),
    tokensUt: sum((r) => r.tokensUt)
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

export function AgentAnvandning({
  runs,
  delning = null,
  tomtext
}: Readonly<{ runs: RunRow[]; delning?: Slagdelning | null; tomtext: string }>) {
  const { rader, a, b, tokensIn, tokensUt } = summera(runs, delning);

  if (runs.length === 0) {
    return <p className="mt-4 max-w-[70ch] text-[15px] leading-7 text-ink-muted">{tomtext}</p>;
  }

  return (
    <div className="mt-4">
      <div className="grid gap-x-10 sm:grid-cols-3">
        <Matt etikett={delning?.etikettA ?? "Körningar"} varde={a} />
        {delning ? <Matt etikett={delning.etikettB} varde={b} /> : null}
        <Matt etikett="Kunder" varde={rader.length} />
        <Matt etikett="Tokens in" varde={tokensIn.toLocaleString("sv-SE")} />
        <Matt etikett="Tokens ut" varde={tokensUt.toLocaleString("sv-SE")} />
        <Matt etikett="AI-kostnad, uppskattad" varde={usd(kostnadUsd(tokensIn, tokensUt))} />
      </div>

      <table className="mt-8 w-full text-[15px]">
        <thead>
          <tr className="border-b border-ink/15 text-left">
            <th className="kicker py-2 font-normal text-mineral">Kund</th>
            <th className="kicker py-2 text-right font-normal text-mineral">
              {delning?.etikettA ?? "Körningar"}
            </th>
            {delning ? (
              <th className="kicker py-2 text-right font-normal text-mineral">
                {delning.etikettB}
              </th>
            ) : null}
            <th className="kicker py-2 text-right font-normal text-mineral">Tokens</th>
            <th className="kicker py-2 text-right font-normal text-mineral">Kostnad</th>
            <th className="kicker py-2 text-right font-normal text-mineral">Senast</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ink/10">
          {rader.map((rad) => (
            <tr key={rad.kund}>
              <td className="py-3 font-mono text-[13px]">{rad.kund}</td>
              <td className="num py-3 text-right">{rad.a}</td>
              {delning ? <td className="num py-3 text-right">{rad.b}</td> : null}
              <td className="num py-3 text-right">
                {(rad.tokensIn + rad.tokensUt).toLocaleString("sv-SE")}
              </td>
              <td className="num py-3 text-right">{usd(kostnadUsd(rad.tokensIn, rad.tokensUt))}</td>
              <td className="py-3 text-right text-[13px] text-mineral">
                {rad.senast ? rad.senast.slice(0, 16).replace("T", " ") : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
