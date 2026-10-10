import type { OversiktSvar } from "@/components/snajp/SupportOversikt";

/**
 * Kundtjänst › Översikt på /demo (Sebbes beställning 2026-10-07).
 *
 * Samma form som backendens `GET /api/support/oversikt`
 * (snajp-support/app/support_oversikt.py), så att demon och arbetsytan går
 * genom exakt samma rendering. Regeln från app/demo/[[...slug]]/page.tsx
 * gäller: ingenting här får sträcka sig efter en session eller databasen.
 *
 * Talen är handskrivna och hänger ihop: hanteringen summerar till periodens
 * inkomna, svarstidshinkarna till de besvarade.
 */
export function demoSupportOversikt(): OversiktSvar {
  const nu = Date.now();
  const inkomna = [38, 41, 36, 44, 47, 43, 52, 49, 55, 58, 54, 61];
  const besvarade = [33, 37, 33, 40, 44, 40, 49, 46, 52, 55, 52, 58];
  const eskalerade = [6, 5, 6, 5, 5, 4, 5, 4, 4, 4, 3, 3];
  const svarstid = [22, 19, 21, 17, 15, 16, 13, 12, 11, 10, 9, 9];
  const veckostart = (i: number) => new Date(nu - (11 - i) * 7 * 86_400_000).toISOString();
  return {
    period_dygn: 28,
    veckor: inkomna.map((n, i) => ({
      week: `v${30 + i}`,
      start: veckostart(i),
      inkomna: n,
      besvarade: besvarade[i],
      eskalerade: eskalerade[i],
      svarstid_median: svarstid[i]
    })),
    nu: { inkomna: 228, auto: 131, godkant: 70, manniska: 14, vantar: 13, svarstid_median: 9, inom_timme: 0.8, kb_traff: 0.86 },
    forra: { inkomna: 191, auto: 99, godkant: 63, manniska: 18, vantar: 11, svarstid_median: 13, inom_timme: 0.71, kb_traff: 0.79 },
    kategorier: [
      { id: "orderstatus", antal: 64, eskalerade: 1 },
      { id: "leverans", antal: 48, eskalerade: 2 },
      { id: "betalning", antal: 37, eskalerade: 3 },
      { id: "retur_reklamation", antal: 31, eskalerade: 3 },
      { id: "teknisk_support", antal: 26, eskalerade: 1 },
      { id: "garanti", antal: 12, eskalerade: 3 },
      { id: "ovrigt", antal: 10, eskalerade: 1 }
    ],
    svarstider: [
      { id: "15m", antal: 124 },
      { id: "1h", antal: 37 },
      { id: "4h", antal: 26 },
      { id: "24h", antal: 11 },
      { id: "mer", antal: 3 }
    ],
    vantande: { antal: 3, aldsta: new Date(nu - 94 * 60_000).toISOString() },
    kb_luckor: {
      antal: 3,
      rader: [
        { id: "kb-1", titel: "Byta leveransadress efter beställning", created_at: new Date(nu - 86_400_000).toISOString() },
        { id: "kb-2", titel: "Leverans till Åland", created_at: new Date(nu - 3 * 86_400_000).toISOString() },
        { id: "kb-3", titel: "Presentkortets giltighetstid", created_at: new Date(nu - 5 * 86_400_000).toISOString() }
      ]
    },
    drift: { korningar: 702, tokens_in: 3_850_000, tokens_out: 410_000, cache: 64, modell: "vertex:gemini-2.5-flash", kb_artiklar: 48 }
  };
}
