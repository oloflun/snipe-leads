/**
 * Beloppsformatering på STRÄNGEN, aldrig via Number() — samma regel som i
 * huvudappens BokforingPanel: API:t skickar belopp som strängar för att en
 * JavaScript-float inte ska kunna ändra sista decimalen, och den garantin
 * ska inte kastas bort i visningen.
 */
export function kronor(varde: string | null | undefined): string {
  if (varde === null || varde === undefined) return "—";
  const negativt = varde.startsWith("-");
  const [heltal, decimaler = "00"] = varde.replace("-", "").split(".");
  const grupperat = heltal.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${negativt ? "−" : ""}${grupperat},${decimaler.padEnd(2, "0")} kr`;
}

/** Momssatsen som etikett. UPPSLAG, inte räkning — se huvudappens historik:
 *  strängaritmetik gav en gång "0.0600" → 60 %. */
const MOMSETIKETT: Record<string, string> = {
  "0.25": "25 %",
  "0.12": "12 %",
  "0.06": "6 %",
  "0": "0 %"
};

export function procent(varde: string | null | undefined): string {
  if (varde === null || varde === undefined) return "—";
  const normaliserad = varde.includes(".")
    ? varde.replace(/0+$/, "").replace(/\.$/, "")
    : varde;
  return MOMSETIKETT[normaliserad] ?? "—";
}

/**
 * Skattesatsen för svensk bolagsskatt sedan 2021. Räknas i ÖREN (heltal) så
 * att float aldrig rör beloppet; avrundas till hela kronor nedåt eftersom
 * uppskattningen är just en uppskattning.
 *
 * Returnerar null när resultatet inte är ett tolkbart positivt belopp —
 * ingen skatt att uppskatta är ett svar, inte en nolla.
 */
export function preliminarBolagsskatt(resultatForeSkatt: string | null | undefined): string | null {
  if (!resultatForeSkatt) return null;
  const match = /^(-?)(\d+)(?:\.(\d{1,2}))?$/.exec(resultatForeSkatt.trim());
  if (!match) return null;
  const [, minus, heltal, dec = "0"] = match;
  if (minus) return null;
  const oren = BigInt(heltal) * 100n + BigInt(dec.padEnd(2, "0"));
  const skattOren = (oren * 206n) / 1000n;
  const kronorHela = skattOren / 100n;
  const rest = skattOren % 100n;
  return `${kronorHela}.${rest.toString().padStart(2, "0")}`;
}

/** "1250.00" → 1250 (för stapeldiagram och proportioner, ALDRIG för belopp
 *  som visas — visningen går genom `kronor`). */
export function somTal(varde: string | null | undefined): number {
  if (!varde) return 0;
  const tal = Number(varde);
  return Number.isFinite(tal) ? tal : 0;
}
