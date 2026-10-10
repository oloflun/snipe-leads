import type { ChattRad, UsageSvar } from "@/components/dashboard/Aktivitet";
import type { KorningsRad } from "@/components/leads/IrisKorningar";

/**
 * Aktivitet på /demo (Sebbes beställning 2026-10-07): samma former som
 * `GET /leads/korningar`, `GET /usage` och `GET /chattar`, så att demon och
 * arbetsytan går genom exakt samma rendering.
 *
 * Regeln från app/demo/[[...slug]]/page.tsx gäller: ingenting här får sträcka
 * sig efter en session eller databasen. Tiderna räknas från Date.now() och
 * anropas därför först efter monteringen (relativa tider får inte skilja
 * mellan server och klient).
 *
 * Talen hänger ihop: varje körnings levererade och undersökta ryms i dess
 * beställning och tak, och en pågående körning står i 'processing'.
 */

const DYGN = 86_400_000;

function sedan(dygn: number, timmar = 0): string {
  return new Date(Date.now() - dygn * DYGN - timmar * 3_600_000).toISOString();
}

type Underlag = {
  dygn: number;
  scope: "batch" | "lista";
  irisScope?: "research" | "research_and_draft";
  mal: number;
  levererade: number;
  undersokta: number;
  slut?: string;
  status?: KorningsRad["status"];
  pagaende?: number;
  test?: boolean;
};

const KORNINGAR: Underlag[] = [
  { dygn: 0.05, scope: "batch", irisScope: "research_and_draft", mal: 10, levererade: 4, undersokta: 11, status: "processing", pagaende: 2 },
  { dygn: 1, scope: "batch", irisScope: "research_and_draft", mal: 10, levererade: 10, undersokta: 23, slut: "klar" },
  { dygn: 3, scope: "lista", mal: 50, levererade: 0, undersokta: 0 },
  { dygn: 5, scope: "batch", irisScope: "research_and_draft", mal: 10, levererade: 7, undersokta: 40, slut: "tak" },
  { dygn: 8, scope: "batch", irisScope: "research", mal: 5, levererade: 5, undersokta: 9, slut: "klar" },
  { dygn: 11, scope: "batch", irisScope: "research_and_draft", mal: 10, levererade: 10, undersokta: 19, slut: "klar" },
  { dygn: 13, scope: "batch", irisScope: "research", mal: 5, levererade: 0, undersokta: 6, slut: "slut_pa_kandidater" },
  { dygn: 16, scope: "batch", irisScope: "research_and_draft", mal: 10, levererade: 9, undersokta: 40, slut: "tak" },
  { dygn: 19, scope: "lista", mal: 50, levererade: 0, undersokta: 0 },
  { dygn: 22, scope: "batch", irisScope: "research_and_draft", mal: 10, levererade: 10, undersokta: 26, slut: "klar" },
  { dygn: 26, scope: "batch", irisScope: "research_and_draft", mal: 5, levererade: 5, undersokta: 12, slut: "klar", test: true },
  { dygn: 31, scope: "batch", irisScope: "research_and_draft", mal: 10, levererade: 6, undersokta: 40, slut: "tak" },
  { dygn: 36, scope: "batch", irisScope: "research", mal: 10, levererade: 10, undersokta: 21, slut: "klar" },
  { dygn: 40, scope: "batch", irisScope: "research_and_draft", mal: 10, levererade: 0, undersokta: 0, status: "failed" },
  { dygn: 45, scope: "batch", irisScope: "research_and_draft", mal: 10, levererade: 8, undersokta: 40, slut: "tak" },
  { dygn: 52, scope: "batch", irisScope: "research", mal: 5, levererade: 5, undersokta: 10, slut: "klar" },
  { dygn: 60, scope: "batch", irisScope: "research_and_draft", mal: 10, levererade: 10, undersokta: 24, slut: "klar" },
  { dygn: 68, scope: "batch", irisScope: "research_and_draft", mal: 10, levererade: 3, undersokta: 40, slut: "tak" },
  { dygn: 75, scope: "batch", irisScope: "research", mal: 5, levererade: 5, undersokta: 8, slut: "klar" }
];

const BOLAG = ["Lundsund Mekaniska AB", "Viksund Plåt AB", "Hammarnäs Bygg AB", "Granstrand Logistik AB", "Sjöhaga Snickeri AB"];

export function demoKorningar(): KorningsRad[] {
  return KORNINGAR.map((u, i) => {
    const skapad = sedan(u.dygn);
    const klar = u.status !== "processing" && u.status !== "failed";
    const fardig = u.status === "processing" ? null : sedan(u.dygn, -2);
    return {
      job_id: `demo-korning-${i + 1}`,
      status: u.status ?? "completed",
      scope: u.scope,
      is_test: Boolean(u.test),
      created_at: skapad,
      updated_at: fardig ?? sedan(0, 0.02),
      completed_at: fardig,
      error: u.status === "failed" ? "Sökningen svarade inte. Försök igen om en stund." : null,
      korning:
        u.scope === "lista" || u.status === "failed"
          ? null
          : {
              mal: u.mal,
              levererade: u.levererade,
              undersokta: u.undersokta,
              pagaende: u.pagaende ?? 0,
              tak: u.mal * 4,
              klar,
              slut_orsak: klar ? (u.slut ?? "klar") : null,
              scope: u.irisScope,
              jobs: BOLAG.slice(0, Math.min(BOLAG.length, u.levererade)).map((namn, j) => ({
                job_id: `demo-jobb-${i}-${j}`,
                prospect_id: `demo-prospekt-${i}-${j}`,
                company_name: namn
              })),
              tratt:
                u.undersokta > u.levererade
                  ? [{ namn: "Norrby Måleri AB", steg: "Webbkriterier", skal: "Sajten saknar kontaktuppgifter till någon på bolaget." }]
                  : []
            }
    };
  });
}

/** Sextio dygn, nyast först, som backendens `daily_support_usage`. */
export function demoUsage(): UsageSvar {
  const dagar = Array.from({ length: 60 }, (_, i) => {
    const datum = new Date(Date.now() - i * DYGN);
    const helg = [0, 6].includes(datum.getDay());
    // Trafiken växer mot i dag, helgerna är lugnare.
    const bas = Math.round((helg ? 9 : 26) * (1 + (60 - i) / 120));
    const korningar = bas + ((i * 7) % 5);
    return {
      datum: datum.toISOString().slice(0, 10),
      korningar,
      korningar_test: i % 9 === 0 ? 3 : 0,
      tokens_in: korningar * 5_400,
      tokens_out: korningar * 610
    };
  });
  return { dagar, budget: { tak: 400_000, forbrukat_24h: dagar[0].tokens_in + dagar[0].tokens_out } };
}

export function demoChattar(): ChattRad[] {
  const rader: [string, string, string, number, boolean][] = [
    ["Maja Ek", "Faktura dragen två gånger", "Kunden ber om en människa", 0.2, true],
    ["Johan Berg", "Reklamation, trasig leverans", "Agenten saknade svar i kunskapsbasen", 1.1, true],
    ["Sara Nilsson", "Ändra leveransadress", "Kunden ber om en människa", 4, false],
    ["Okänd besökare", "Avtalsfråga", "Juridisk fråga", 9, false],
    ["Per Holm", "Garanti på pump", "Agenten saknade svar i kunskapsbasen", 15, false],
    ["Lina Ström", "Retur efter 40 dagar", "Utanför returpolicyn", 23, false],
    ["Erik Lund", "Kreditupplysning", "Kunden ber om en människa", 34, false]
  ];
  return rader.map(([namn, amne, orsak, dygn, aktiv], i) => ({
    customer_id: `demo-kund-${i + 1}`,
    customer_name: namn,
    subject: amne,
    channel: "chatt",
    overlamnad_at: sedan(dygn),
    orsak_text: orsak,
    aktiv
  }));
}
