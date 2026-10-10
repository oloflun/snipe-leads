"use client";

import { Cell, Tabell, Talrad, Tomt, meta } from "@/components/ui";
import { a as at } from "@/lib/admin/sprak";
import type { RunRow } from "@/lib/data/admin";
import { useLocale, type Localized } from "@/lib/i18n";

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
  etikettA: Localized;
  etikettB: Localized;
  /** true = körningen räknas till B-kolumnen. */
  arB: (run: RunRow) => boolean;
};

function arBokforingschatt(run: RunRow): boolean {
  // Sammandraget (agentanvändningssidan) bär svaret färdigräknat och ingen logg.
  if (typeof run.bokforingschatt === "boolean") return run.bokforingschatt;
  try {
    return JSON.stringify(run.step_log ?? "").includes("bokforing-chatt");
  } catch {
    return false;
  }
}

/**
 * Delningarna bor här och inte i sidan: komponenten är en klientkomponent (den
 * byter språk), och en funktion kan inte skickas från en server-komponent som
 * prop. Sidan väljer delning med namn.
 */
const DELNINGAR: Record<"bokforing", Slagdelning> = {
  bokforing: {
    etikettA: { sv: "Underlag", en: "Receipts" },
    etikettB: { sv: "Frågor", en: "Questions" },
    arB: arBokforingschatt
  }
};

type Rad = {
  kund: string;
  a: number;
  b: number;
  tokensIn: number;
  tokensUt: number;
  senast: string | null;
};

function summera(runs: RunRow[], delning: Slagdelning | null, okand: string) {
  const perKund = new Map<string, Rad>();
  for (const run of runs) {
    const kund = run.tenant_name || run.tenant_slug || okand;
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
const PRISUNDERLAG: Localized = {
  sv: `Räknad på Vertex listpris för Gemini 2.5 Flash ($${USD_PER_MILJON.in} per miljon tokens in, $${USD_PER_MILJON.ut} per miljon ut, avläst 2026-09-15), inte på Googles faktura.`,
  en: `Based on the Vertex list price for Gemini 2.5 Flash ($${USD_PER_MILJON.in} per million tokens in, $${USD_PER_MILJON.ut} per million out, read 2026-09-15), not on Google's invoice.`
};

/**
 * Fyra nyckeltal i varje sektion, alltid samma fyra: sex poster i ett
 * fyrkolumnsrutnät gav en trasig andra rad. Slagdelningen (Underlag/Frågor)
 * står därför som notis under Körningar (och per kund i tabellen), och tokens
 * in/ut som notis under Tokens.
 */
export function AgentAnvandning({
  runs,
  delning: delningsnamn = null,
  tomtext,
  vidTaket = null
}: Readonly<{
  runs: RunRow[];
  delning?: keyof typeof DELNINGAR | null;
  tomtext: Localized;
  /** Satt när hämtningen nådde backendens tak: talen är då en undre gräns. */
  vidTaket?: number | null;
}>) {
  const { locale, text } = useLocale();
  const delning = delningsnamn ? DELNINGAR[delningsnamn] : null;
  const { rader, a, b, tokensIn, tokensUt } = summera(runs, delning, at("okand", locale));

  if (runs.length === 0) {
    return <Tomt>{text(tomtext)}</Tomt>;
  }

  return (
    <div>
      <Talrad
        poster={[
          {
            etikett: at("kolKorningar", locale),
            varde: vidTaket ? `${a + b}+` : a + b,
            notis: vidTaket
              ? text({
                  sv: `De senaste ${vidTaket} per agenttyp. Äldre körningar räknas inte.`,
                  en: `The latest ${vidTaket} per agent type. Older runs are not counted.`
                })
              : delning
                ? `${a} ${text(delning.etikettA).toLowerCase()}, ${b} ${text(delning.etikettB).toLowerCase()}`
                : undefined
          },
          { etikett: at("kunderLank", locale), varde: rader.length },
          {
            etikett: at("kolTokens", locale),
            varde: (tokensIn + tokensUt).toLocaleString("sv-SE"),
            notis: `${tokensIn.toLocaleString("sv-SE")} in, ${tokensUt.toLocaleString("sv-SE")} ${at("ut", locale)}`
          },
          {
            etikett: at("aiKostnadUppskattad", locale),
            varde: <span title={text(PRISUNDERLAG)}>{usd(kostnadUsd(tokensIn, tokensUt))}</span>
          }
        ]}
      />

      <div className="mt-4">
        <Tabell
          minBredd={560}
          kolumner={[
            { rubrik: at("kolKund", locale) },
            {
              rubrik: delning ? text(delning.etikettA) : at("kolKorningar", locale),
              bredd: "13%",
              hoger: true
            },
            ...(delning ? [{ rubrik: text(delning.etikettB), bredd: "13%", hoger: true }] : []),
            { rubrik: at("kolTokens", locale), bredd: "16%", hoger: true },
            { rubrik: at("kolKostnad", locale), bredd: "13%", hoger: true },
            { rubrik: at("senast", locale), bredd: "20%", hoger: true }
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
