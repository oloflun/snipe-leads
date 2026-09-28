import { Cell, Nyckeltal, Tabell, Tomt, meta } from "@/components/ui";
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
    const kund = run.tenant_name || run.tenant_slug || "okänd";
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

/**
 * Prisunderlaget, på EN plats: som `title` på kostnadsnyckeltalet. Att talet är
 * en uppskattning står synligt i etiketten; listpriset och avläsningsdatumet
 * behövs bara av den som vill kontrollera det, och var tidigare en ingress
 * under sidrubriken (F-016).
 */
const PRISUNDERLAG = `Räknad på Vertex listpris för Gemini 2.5 Flash ($${USD_PER_MILJON.in} per miljon tokens in, $${USD_PER_MILJON.ut} per miljon ut, avläst 2026-09-15), inte på Googles faktura.`;

/**
 * Fyra nyckeltal i varje sektion, alltid samma fyra: sex poster i ett
 * fyrkolumnsrutnät gav en trasig andra rad. Slagdelningen (Underlag/Frågor)
 * står därför som notis under Körningar (och per kund i tabellen), och tokens
 * in/ut som notis under Tokens.
 */
export function AgentAnvandning({
  runs,
  delning = null,
  tomtext,
  vidTaket = null
}: Readonly<{
  runs: RunRow[];
  delning?: Slagdelning | null;
  tomtext: string;
  /** Satt när hämtningen nådde backendens tak: talen är då en undre gräns. */
  vidTaket?: number | null;
}>) {
  const { rader, a, b, tokensIn, tokensUt } = summera(runs, delning);

  if (runs.length === 0) {
    return <Tomt>{tomtext}</Tomt>;
  }

  return (
    <div>
      <Nyckeltal
        poster={[
          {
            etikett: "Körningar",
            varde: vidTaket ? `${a + b}+` : a + b,
            notis: vidTaket
              ? `De senaste ${vidTaket} per agenttyp. Äldre körningar räknas inte.`
              : delning
                ? `${a} ${delning.etikettA.toLowerCase()}, ${b} ${delning.etikettB.toLowerCase()}`
                : undefined
          },
          { etikett: "Kunder", varde: rader.length },
          {
            etikett: "Tokens",
            varde: (tokensIn + tokensUt).toLocaleString("sv-SE"),
            notis: `${tokensIn.toLocaleString("sv-SE")} in, ${tokensUt.toLocaleString("sv-SE")} ut`
          },
          {
            etikett: "AI-kostnad, uppskattad",
            varde: <span title={PRISUNDERLAG}>{usd(kostnadUsd(tokensIn, tokensUt))}</span>
          }
        ]}
      />

      <div className="mt-8">
        <Tabell
          minBredd={560}
          kolumner={[
            { rubrik: "Kund" },
            { rubrik: delning?.etikettA ?? "Körningar", bredd: "13%", hoger: true },
            ...(delning ? [{ rubrik: delning.etikettB, bredd: "13%", hoger: true }] : []),
            { rubrik: "Tokens", bredd: "16%", hoger: true },
            { rubrik: "Kostnad", bredd: "13%", hoger: true },
            { rubrik: "Senast", bredd: "20%", hoger: true }
          ]}
        >
          {rader.map((rad) => (
            <tr key={rad.kund}>
              <Cell titel className="break-words">
                {rad.kund}
              </Cell>
              <Cell hoger>{rad.a}</Cell>
              {delning ? <Cell hoger>{rad.b}</Cell> : null}
              <Cell hoger>{(rad.tokensIn + rad.tokensUt).toLocaleString("sv-SE")}</Cell>
              <Cell hoger>{usd(kostnadUsd(rad.tokensIn, rad.tokensUt))}</Cell>
              <Cell hoger className={meta}>
                {rad.senast ? rad.senast.slice(0, 16).replace("T", " ") : "–"}
              </Cell>
            </tr>
          ))}
        </Tabell>
      </div>
    </div>
  );
}
