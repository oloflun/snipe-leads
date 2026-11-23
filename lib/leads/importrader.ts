import { MAX_EXTRA, flervalsordning, normRubrik, type ImportFalt, type Kolumnval, type Tabell } from "./importmallar.ts";
import {
  datumordning,
  tolkaDatum,
  tolkaEpost,
  tolkaOrgnr,
  tolkaTelefon,
  tolkaWebb,
  TOMT,
  type Anmarkningskod,
  type Tolkat
} from "./importvarden.ts";

/**
 * Listimportens radbyggare: filens rader blir importrader, med en anmärkning
 * för varje värde som inte höll och en dubblettkontroll inom filen. Det är
 * den här listan granskningssteget visar innan något skickas till servern.
 */

/** Raden som `POST /leads/import` tar emot. */
export type Importrad = { company_name: string } & Partial<Record<Exclude<ImportFalt, "company_name">, string>> & {
    extra?: Record<string, string>;
  };

export type Anmarkning = { falt: ImportFalt; kod: Anmarkningskod; varde: string };

export type Radutfall = {
  /** Radens plats i `tabell.data`. */
  index: number;
  /** `null` när bolagsnamnet saknas: raden kan inte importeras. */
  rad: Importrad | null;
  /** Värden som inte höll. Fältet är tomt på raden; resten importeras. */
  anmarkningar: Anmarkning[];
  /** Samma bolag som raden med det här indexet, som är den som importeras. */
  dubblettAv?: number;
};

/** Backendens fälttak (leads_suite.Importrad). */
const MAX_TECKEN = 200;
const MAX_EXTRATECKEN = 500;

function text(ra: string | undefined): string {
  const v = (ra ?? "").replace(/\s+/g, " ").trim();
  return TOMT.test(v) ? "" : v.slice(0, MAX_TECKEN);
}

const BOLAGSFORMER = new Set([
  "ab", "aktiebolag", "publ", "hb", "handelsbolag", "kb", "kommanditbolag", "ek", "för", "ekonomisk", "förening",
  "ef", "enskild", "firma", "i", "likvidation"
]);

/**
 * Bolagsnamnet jämförbart: "Byggarna Berggren AB" och "byggarna berggren" är
 * samma bolag. Spegel av `nyckel` i snajp-support/app/leads/upptagna.py, så
 * att dubbletterna granskningen visar är de servern sedan slår ihop.
 */
export function bolagsnyckel(namn: string): string {
  const rent = namn.normalize("NFKC").toLowerCase().replace(/&/g, " och ");
  const ord = rent
    .replace(/[^\p{L}\p{N}_]+/gu, " ")
    .trim()
    .split(" ")
    .filter(Boolean);
  while (ord.length && BOLAGSFORMER.has(ord[ord.length - 1])) ord.pop();
  while (ord.length && (ord[0] === "ab" || ord[0] === "aktiebolag")) ord.shift();
  return ord.join(" ") || rent.trim();
}

/** Hur mycket raden går att använda: en adress väger tyngst, sedan ett nummer. */
const vikt = (rad: Importrad) => (rad.contact_email ? 2 : 0) + (rad.contact_phone ? 1 : 0);

export function tolkaRader(tabell: Tabell, val: Kolumnval[]): Radutfall[] {
  const kolumner = (mal: Kolumnval) => val.flatMap((v, i) => (v === mal ? [i] : []));
  const kol = Object.fromEntries(
    (["company_name", "orgnr", "contact_name", "fornamn", "efternamn", "contact_role", "contact_email", "contact_phone", "website", "ort", "avtalsslut", "extra"] as Kolumnval[]).map(
      (mal) => [mal, kolumner(mal)]
    )
  ) as Record<Kolumnval, number[]>;
  kol.contact_email = flervalsordning(tabell.rubriker, kol.contact_email, "contact_email");
  kol.contact_phone = flervalsordning(tabell.rubriker, kol.contact_phone, "contact_phone");
  const ordning = datumordning(kol.avtalsslut.flatMap((i) => tabell.data.map((rad) => rad[i] ?? "")));
  // En kolumn som heter VD innehåller namnet på VD: rollen följer av rubriken.
  const vdKolumn = kol.contact_name.some((i) => /^(vd|ceo|verkstallande direktor)$/.test(normRubrik(tabell.rubriker[i] ?? "")));

  const utfall: Radutfall[] = tabell.data.map((ra, index) => {
    const cell = (i: number | undefined) => (i === undefined ? "" : (ra[i] ?? ""));
    const company = text(cell(kol.company_name[0]));
    if (!company) return { index, rad: null, anmarkningar: [] };

    const rad: Importrad = { company_name: company };
    const anmarkningar: Anmarkning[] = [];
    /** Första kolumnen med ett giltigt värde; annars en anmärkning om någon
     *  kolumn hade ett värde som inte höll. */
    const tolkat = (falt: Exclude<ImportFalt, "company_name">, tolka: (v: string) => Tolkat) => {
      let fel: Anmarkning | undefined;
      for (const i of kol[falt]) {
        const varde = cell(i).trim();
        if (!varde) continue;
        const t = tolka(varde);
        if (t.varde) {
          rad[falt] = t.varde.slice(0, MAX_TECKEN);
          return;
        }
        if (t.fel && !fel) fel = { falt, kod: t.fel, varde: varde.slice(0, 80) };
      }
      if (fel) anmarkningar.push(fel);
    };

    tolkat("orgnr", tolkaOrgnr);
    const namn = text(cell(kol.contact_name[0])) || text([cell(kol.fornamn[0]), cell(kol.efternamn[0])].join(" "));
    if (namn) rad.contact_name = namn;
    const roll = text(cell(kol.contact_role[0])) || (vdKolumn && namn ? "VD" : "");
    if (roll) rad.contact_role = roll;
    tolkat("contact_email", tolkaEpost);
    tolkat("contact_phone", tolkaTelefon);
    tolkat("website", tolkaWebb);
    const ort = text(cell(kol.ort[0]));
    if (ort) rad.ort = ort;
    tolkat("avtalsslut", (v) => tolkaDatum(v, ordning));

    const extra: Record<string, string> = {};
    for (const i of kol.extra.slice(0, MAX_EXTRA)) {
      const varde = cell(i).replace(/\s+/g, " ").trim().slice(0, MAX_EXTRATECKEN);
      if (varde) extra[(tabell.rubriker[i] || String(i + 1)).slice(0, 100)] = varde;
    }
    if (Object.keys(extra).length) rad.extra = extra;
    return { index, rad, anmarkningar };
  });

  // Ett bolag, en rad: samma org.nr eller samma namn utan bolagsform. Den rad
  // som har en adress (annars ett nummer) är den som importeras.
  const behallen = new Map<string, number>();
  for (const u of utfall) {
    if (!u.rad) continue;
    const nycklar = [bolagsnyckel(u.rad.company_name)];
    if (u.rad.orgnr?.includes("-")) nycklar.push(`orgnr:${u.rad.orgnr.replace(/\D/g, "")}`);
    const traff = nycklar.map((n) => behallen.get(n)).find((i) => i !== undefined);
    if (traff === undefined) {
      nycklar.forEach((n) => behallen.set(n, u.index));
      continue;
    }
    const forra = utfall[traff];
    if (vikt(u.rad) > vikt(forra.rad!)) {
      forra.dubblettAv = u.index;
      for (const [n, i] of behallen) if (i === traff) behallen.set(n, u.index);
      for (const annan of utfall) if (annan.dubblettAv === traff) annan.dubblettAv = u.index;
      nycklar.forEach((n) => behallen.set(n, u.index));
    } else {
      u.dubblettAv = traff;
      nycklar.forEach((n) => behallen.set(n, traff));
    }
  }
  return utfall;
}

export type Sammanfattning = {
  /** Rader i filen under rubrikraden. */
  rader: number;
  /** Rader som går vidare till servern. */
  importeras: number;
  utanBolag: number;
  dubbletter: number;
  /** Importeras, men med minst ett värde som inte höll. */
  medAnmarkning: number;
  perKod: Partial<Record<Anmarkningskod, number>>;
  medEpost: number;
  medTelefon: number;
  medAvtalsslut: number;
};

export function sammanfatta(utfall: Radutfall[]): Sammanfattning {
  const s: Sammanfattning = {
    rader: utfall.length, importeras: 0, utanBolag: 0, dubbletter: 0, medAnmarkning: 0, perKod: {},
    medEpost: 0, medTelefon: 0, medAvtalsslut: 0
  };
  for (const u of utfall) {
    if (!u.rad) s.utanBolag++;
    else if (u.dubblettAv !== undefined) s.dubbletter++;
    else {
      s.importeras++;
      if (u.anmarkningar.length) s.medAnmarkning++;
      for (const a of u.anmarkningar) s.perKod[a.kod] = (s.perKod[a.kod] ?? 0) + 1;
      if (u.rad.contact_email) s.medEpost++;
      if (u.rad.contact_phone) s.medTelefon++;
      if (u.rad.avtalsslut) s.medAvtalsslut++;
    }
  }
  return s;
}

/** Raderna som skickas till servern, i filens ordning. */
export function importrader(utfall: Radutfall[]): Importrad[] {
  return utfall.flatMap((u) => (u.rad && u.dubblettAv === undefined ? [u.rad] : []));
}
