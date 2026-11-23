import { excelDatum } from "./importfil.ts";

/**
 * Listimportens värdetolkning: en cell ur kundens fil blir ett värde som går
 * att använda, eller en anmärkning som säger varför det inte gick. Ett värde
 * som inte håller sparas aldrig halvt: fältet lämnas tomt och raden visas i
 * granskningen, så att en felskriven adress inte blir ett utskick som studsar.
 */

export type Anmarkningskod =
  /** Ingen giltig e-postadress i cellen. */
  | "epost"
  /** Inget telefonnummer (7–15 siffror) i cellen. */
  | "telefon"
  /** Tio siffror vars kontrollsiffra inte stämmer, eller inget org.nr alls. */
  | "orgnr"
  /** Ett personnummer (enskild firma). Sparas inte. */
  | "personnummer"
  /** Ingen webbadress (en e-postadress, en profil i sociala medier). */
  | "webb"
  /** Gick inte att läsa som datum. */
  | "datum"
  /** Excel har gjort om talet till 5,56E+09; siffrorna är borta. */
  | "excel";

export type Tolkat = { varde?: string; fel?: Anmarkningskod };

/** Det folk skriver när uppgiften saknas. Räknas som tomt, inte som fel. */
export const TOMT = /^(-+|–|—|\?+|n\/?a|null|none|nil|saknas|ingen|inget|okänd|okant|unknown|ej angivet|ej angiven|x)$/i;
const VETENSKAPLIG = /^\d[.,]\d+e\+?\d+$/i;

function ren(ra: string): string {
  const v = (ra ?? "").trim();
  return TOMT.test(v) ? "" : v;
}

/** Kontrollsiffran i org.nr och personnummer (modulus 10 över tio siffror). */
function luhn(siffror: string): boolean {
  let summa = 0;
  for (let i = 0; i < siffror.length; i++) {
    let n = Number(siffror[i]);
    if (i % 2 === 0) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    summa += n;
  }
  return summa % 10 === 0;
}

/**
 * Svenskt org.nr som NNNNNN-NNNN. Sekelprefix (16…) och momsnummer (SE…01)
 * skalas av. Ett personnummer (tredje siffran 0 eller 1: enskild firma)
 * sparas inte, och inte heller tio siffror med fel kontrollsiffra: org.nr
 * avgör vilka bolag som är samma, så ett felskrivet nummer pekar ut fel bolag.
 * Åtta och nio siffror är utländska nummer (CVR, Y-tunnus, norskt org.nr)
 * och står kvar som de skrevs.
 */
export function tolkaOrgnr(ra: string): Tolkat {
  const v = ren(ra);
  if (!v) return {};
  if (VETENSKAPLIG.test(v)) return { fel: "excel" };
  let s = v.replace(/\D/g, "");
  if (/^se/i.test(v) && s.length === 12 && s.endsWith("01")) s = s.slice(0, 10);
  else if (s.length === 12 && /^(16|18|19|20)/.test(s)) s = s.slice(2);
  if (s.length === 8 || s.length === 9) return { varde: v.slice(0, 20) };
  if (s.length !== 10) return { fel: "orgnr" };
  if (s[2] < "2") return { fel: "personnummer" };
  if (!luhn(s)) return { fel: "orgnr" };
  return { varde: `${s.slice(0, 6)}-${s.slice(6)}` };
}

const EPOST = /^[^\s@<>()[\],;:"']+@[^\s@<>()[\],;:"']+\.[a-z0-9-]{2,}$/i;
/** Adresser ingen läser. Samma tanke som discovery._EJ_SALJADRESS. */
const ROBOT = /^(no-?reply|do-?not-?reply|mailer-daemon|postmaster|bounce[s]?)@/i;

/** Första giltiga adressen i cellen: "Eva Ek <eva@x.se>", "a@x.se; b@x.se". */
export function tolkaEpost(ra: string): Tolkat {
  const v = ren(ra);
  if (!v) return {};
  const traff = v
    .replace(/mailto:/gi, "")
    .split(/[\s,;<>()"'[\]|]+/)
    .map((d) => d.replace(/\.+$/, ""))
    .find((d) => EPOST.test(d) && !ROBOT.test(d));
  return traff ? { varde: traff } : { fel: "epost" };
}

/**
 * Första telefonnumret i cellen, utan etiketter ("mobil:", "(växel)").
 * Excel tappar nollan i ett mobilnummer (701740605): den läggs tillbaka.
 * 0046 och 46 framför ett svenskt nummer blir +46.
 */
export function tolkaTelefon(ra: string): Tolkat {
  let v = ren(ra).replace(/^'+/, "");
  if (!v) return {};
  if (VETENSKAPLIG.test(v)) return { fel: "excel" };
  v = v.split(/\s*(?:[;,|\n]|\s\/\s|\/(?=\s*[+0])|\boch\b|\beller\b|\bor\b)\s*/)[0];
  v = v
    .replace(/\(0\)/, "")
    .replace(/[^\d+()\s-]/g, "")
    .replace(/\(\s*\)/g, "")
    .replace(/\s+/g, " ")
    .replace(/^[\s()-]+|[\s(-]+$/g, "");
  const plus = v.startsWith("+");
  const d = v.replace(/\D/g, "");
  if (d.length < 7 || d.length > 15) return { fel: "telefon" };
  if (!plus && d.startsWith("00")) return { varde: `+${d.slice(2)}` };
  if (!plus && d.startsWith("46") && d.length >= 10 && d[2] !== "0") return { varde: `+${d}` };
  if (!plus && d.length === 9 && d[0] === "7") return { varde: `0${d}` };
  return { varde: plus ? `+${v.slice(1).trim()}` : v };
}

const SOCIALA = /(^|\.)(linkedin|facebook|instagram|twitter|x|youtube|tiktok)\.com$/;

/** Värdnamnet utan schema, www och sökväg: "https://www.Bygg.se/om" → "bygg.se". */
export function tolkaWebb(ra: string): Tolkat {
  const v = ren(ra).split(/[\s,;|]+/)[0];
  if (!v) return {};
  if (v.includes("@")) return { fel: "webb" };
  const vard = v
    .replace(/^[a-z][a-z0-9+.-]*:\/\//i, "")
    .replace(/^www\./i, "")
    .split(/[/?#]/)[0]
    .replace(/:\d+$/, "")
    .replace(/\.$/, "")
    .toLowerCase();
  if (!/^[\p{L}\d-]+(\.[\p{L}\d-]+)+$/u.test(vard) || SOCIALA.test(vard)) return { fel: "webb" };
  return { varde: vard };
}

// --------------------------------------------------------------------- datum

/** Dag före månad (svenskt, europeiskt) eller månad före dag (amerikanskt). */
export type Datumordning = "dm" | "md";

const MANADER: Record<string, number> = {};
[
  ["jan", "januari", "january"],
  ["feb", "februari", "february"],
  ["mar", "mars", "march"],
  ["apr", "april"],
  ["maj", "may"],
  ["jun", "juni", "june"],
  ["jul", "juli", "july"],
  ["aug", "augusti", "august"],
  ["sep", "sept", "september"],
  ["okt", "oct", "oktober", "october"],
  ["nov", "november"],
  ["dec", "december"]
].forEach((namn, i) => namn.forEach((n) => (MANADER[n] = i + 1)));

const tva = (n: number) => String(n).padStart(2, "0");
const sistaDag = (y: number, m: number) => new Date(Date.UTC(y, m, 0)).getUTCDate();

function iso(y: number, m: number, d: number): string | null {
  const ar = y < 100 ? y + 2000 : y;
  if (ar < 1990 || ar > 2100 || m < 1 || m > 12 || d < 1 || d > sistaDag(ar, m)) return null;
  return `${ar}-${tva(m)}-${tva(d)}`;
}

/** En månad utan dag ("2027-03", "mars 2027") är månadens sista dag: ett avtal
 *  som löper ut i mars gäller månaden ut. */
const manadsslut = (y: number, m: number) => (m >= 1 && m <= 12 ? iso(y, m, sistaDag(y, m)) : null);

/**
 * Datumet som ÅÅÅÅ-MM-DD. Läser ISO, 31/3/2027, 31.03.2027, 3/31/2027 (se
 * `ordning`), "31 mars 2027", "March 31, 2027", "31-Mar-27", månad utan dag
 * och Excels löpnummer. Klockslag efter datumet ignoreras.
 */
export function tolkaDatum(ra: string, ordning: Datumordning = "dm"): Tolkat {
  const v = ren(ra).toLowerCase();
  if (!v) return {};
  const ok = (d: string | null): Tolkat => (d ? { varde: d } : { fel: "datum" });
  let m: RegExpExecArray | null;

  if ((m = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[t\s].*)?$/.exec(v))) return ok(iso(+m[1], +m[2], +m[3]));
  if ((m = /^(\d{4})(\d{2})(\d{2})$/.exec(v))) return ok(iso(+m[1], +m[2], +m[3]));
  if ((m = /^(\d{4})[-/](\d{1,2})$/.exec(v))) return ok(manadsslut(+m[1], +m[2]));
  if ((m = /^(\d{1,2})[-/](\d{4})$/.exec(v))) return ok(manadsslut(+m[2], +m[1]));
  if ((m = /^(\d{1,2})[-/.\s](\d{1,2})[-/.\s](\d{4}|\d{2})(?:\s.*)?$/.exec(v))) {
    const [a, b, y] = [+m[1], +m[2], +m[3]];
    // Går datumet inte i den valda ordningen (månad 31) gäller den andra.
    return ok(ordning === "dm" ? (iso(y, b, a) ?? iso(y, a, b)) : (iso(y, a, b) ?? iso(y, b, a)));
  }
  if ((m = /^(\d{1,2})[.\s-]+([a-zåäö]+)[.,\s-]+(\d{4}|\d{2})$/.exec(v))) return ok(iso(+m[3], MANADER[m[2]] ?? 0, +m[1]));
  if ((m = /^([a-zåäö]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})$/.exec(v))) return ok(iso(+m[3], MANADER[m[1]] ?? 0, +m[2]));
  if ((m = /^([a-zåäö]+)\.?[\s-]+(\d{4})$/.exec(v))) return ok(manadsslut(+m[2], MANADER[m[1]] ?? 0));
  if (/^\d{5}$/.test(v) && +v >= 20000 && +v <= 80000) return { varde: excelDatum(+v) };
  return { fel: "datum" };
}

/**
 * Kolumnens datumordning: ett första tal över 12 betyder dag först, ett andra
 * tal över 12 månad först. Säger inget värde något gäller dag först, som i
 * svenska filer.
 */
export function datumordning(varden: string[]): Datumordning {
  for (const v of varden) {
    const m = /^\s*(\d{1,2})[-/.\s](\d{1,2})[-/.\s]\d{2,4}/.exec(v ?? "");
    if (!m) continue;
    if (+m[1] > 12) return "dm";
    if (+m[2] > 12) return "md";
  }
  return "dm";
}
