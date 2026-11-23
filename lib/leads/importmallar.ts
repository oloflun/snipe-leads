import { tolkaDatum, tolkaEpost, tolkaOrgnr, tolkaTelefon, tolkaWebb } from "./importvarden.ts";

/**
 * Listimportens kolumnmatchning: vilken rad som är rubrikraden, vilka rader
 * som är data, och vilken kolumn som är vilket fält.
 *
 * Förut fanns fem mallar (HubSpot, Pipedrive, Salesforce, Upsales, egen fil)
 * som kunden valde mellan, och en rubrik matchade bara ordagrant. Hårdtestet
 * 2026-11-23 (lib/leads/fixtures/crm-export, 48 exporter) visade att det inte
 * räckte: "Mail", "Förnamn", "Main Phone" och "Kund" föll igenom. Nu finns en
 * enda aliaslista över leverantörer och språk, rubriken jämförs utan skiftläge,
 * diakriter och skiljetecken, och kolumnens innehåll får sista ordet: en kolumn
 * som heter E-post men inte innehåller adresser blir inte e-postfältet, och en
 * kolumn full av adresser hittas även om rubriken är "Kolumn 4".
 */

export type ImportFalt =
  | "company_name"
  | "orgnr"
  | "contact_name"
  | "contact_role"
  | "contact_email"
  | "contact_phone"
  | "website"
  | "ort"
  | "avtalsslut";

/**
 * Vad en kolumn i filen blir: ett fält, en namnhalva, en extra uppgift som
 * följer med raden som den står (`extra`), eller ingenting (`hoppa`).
 */
export type Kolumnval = ImportFalt | "fornamn" | "efternamn" | "extra" | "hoppa";
type Mal = Exclude<Kolumnval, "extra" | "hoppa">;

/** Fält som får läsas ur flera kolumner (Apollo har sex telefonkolumner): den
 *  första kolumnen med ett giltigt värde används, rad för rad. */
export const FLERVAL: ReadonlySet<Kolumnval> = new Set<Kolumnval>(["contact_email", "contact_phone"]);

/** Högst så här många extra kolumner följer med en rad (backendens tak). */
export const MAX_EXTRA = 40;

/** Rubriken jämförbar: "E-postadress", "e_postadress" och "EPostAdress" blir
 *  samma sak, och å, ä, ö viks till a, a, o. */
export function normRubrik(s: string): string {
  return (s ?? "")
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/**
 * Alias per fält, redan normerade. `stark` står i preferensordning: finns
 * flera telefonkolumner går mobilen före växeln. `svag` gäller bara när hela
 * rubriken är aliaset ("Namn" är bolaget i ett kundregister och personen i en
 * kontaktexport: det avgörs av vilka andra kolumner som finns).
 */
const ALIAS: Record<Mal, { stark: string[]; svag?: string[] }> = {
  company_name: {
    stark: [
      "company name", "company", "foretagsnamn", "foretag", "bolagsnamn", "bolag", "account name", "account",
      "organization name", "organisation name", "organization", "organisation", "organisationsnamn",
      "kundnamn", "kund", "customer name", "customer", "client name", "client", "firmanamn", "firma",
      "company account", "associated company", "primary company", "person organization", "deal organization",
      "juridiskt namn", "legal name", "business name", "foretagets namn"
    ],
    svag: ["name", "namn"]
  },
  orgnr: {
    stark: [
      "organisationsnummer", "org nr", "orgnr", "org nummer", "orgnummer", "organisationsnr", "org no",
      "org number", "organization number", "organisation number", "company registration number",
      "company reg no", "registration number", "reg no", "business id", "corp id no", "corporate identity number",
      "corporate id", "cvr", "y tunnus"
    ],
    svag: ["vat number", "vat id", "vat no", "vat", "momsnummer", "momsregistreringsnummer", "momsreg nr"]
  },
  contact_name: {
    stark: [
      "contact name", "full name", "fullname", "kontaktperson", "contact person name", "contact person",
      "kontaktnamn", "person name", "primary contact", "main contact", "beslutsfattare", "decision maker",
      "kontakt", "contact", "person", "er referens", "your reference", "referens", "deal contact person",
      "associated contact", "lead name", "vd", "ceo", "verkstallande direktor"
    ],
    svag: ["name", "namn"]
  },
  fornamn: { stark: ["first name", "firstname", "fornamn", "given name", "tilltalsnamn"] },
  efternamn: { stark: ["last name", "lastname", "efternamn", "surname", "family name"] },
  contact_role: {
    stark: [
      "job title", "jobtitle", "jobbtitel", "befattning", "title", "titel", "roll", "role", "position",
      "designation", "yrkestitel", "funktion", "arbetstitel"
    ]
  },
  contact_email: {
    stark: [
      "contact email", "person email", "kontaktmail", "work email", "business email", "primary email",
      "email", "e mail", "email address", "e mail address", "epost", "e post", "e postadress", "epostadress",
      "mejl", "mejladress", "mail", "mailadress", "email 1", "emails", "email addresses", "e postadresser"
    ]
  },
  contact_phone: {
    stark: [
      "mobile phone", "mobile", "mobil", "mobiltelefon", "mobilnummer", "mobilnr", "mobile number", "cell phone",
      "cell", "direct phone number", "direct phone", "direct dial", "direktnummer", "direkttelefon",
      "work direct phone", "phone number", "phone", "telefon", "telefonnummer", "tel", "tel nr", "telefonnr",
      "tfn", "telephone", "telephone number", "business phone", "work phone", "work number", "arbetstelefon",
      "phone 1", "first phone", "phones",
      "phone numbers", "person phone", "contact phone", "kontaktnummer", "main phone", "company phone",
      "corporate phone", "office phone", "vaxel", "vaxelnummer", "switchboard", "other phone"
    ]
  },
  website: {
    stark: [
      "website", "web site", "website url", "webbplats", "webbadress", "webbsida", "hemsida", "hemsideadress",
      "company website", "organization website", "work website", "company domain name", "company domain",
      "domain name", "domain", "doman", "www address", "web address", "homepage", "home page", "company url",
      "webb", "web", "url", "www", "sajt"
    ]
  },
  ort: {
    stark: ["ort", "stad", "city", "postort", "besoksort", "town", "address 1 city", "billing city", "mailing city"]
  },
  avtalsslut: {
    stark: [
      "avtalsslut", "avtal slut", "avtalets slut", "avtalets slutdatum", "avtal slutdatum", "slutdatum avtal",
      "avtal loper ut", "avtalet loper ut", "avtal gar ut", "avtalet gar ut", "loper ut", "utgangsdatum",
      "avtalstid t o m", "avtal t o m", "avtal till", "bindningstid t o m", "bindningstid slut",
      "bindningstid till", "bindningstid tom", "bindningstidens slut", "bundet till", "bunden till",
      "fornyelsedatum", "contract end date", "contract end", "contract expiration date", "contract expiration",
      "contract expiry date", "contract expiry", "contract renewal date", "renewal date", "expiration date",
      "expiry date", "term end date", "agreement end date", "subscription end date", "end date", "slutdatum",
      "fornyelse", "renewal", "bindningstid"
    ]
  }
};

const MAL = Object.keys(ALIAS) as Mal[];

/** Ord som får stå bredvid ett alias var det än står: "Person - Email - Work". */
const NEUTRALA = new Set([
  "name", "namn", "number", "nummer", "nr", "no", "address", "adress", "primary", "primar", "work", "arbete",
  "business", "main", "huvud", "direct", "full", "person", "persons", "contact", "contacts", "kontakt",
  "organization", "organisation", "company", "foretag", "account", "lead", "the", "for", "of", "pa", "till",
  "1", "2", "3", "4"
]);

/**
 * Ord som gör rubriken till något annat än fältet: "Contact owner" är vår
 * säljare, "Email Opt Out" ingen adress, "Home Phone" ett privat nummer (inte
 * B2B), "Deal - Title" ingen befattning.
 */
const NEJ = new Set([
  "owner", "agare", "ansvarig", "saljare", "created", "skapad", "skapat", "modified", "andrad", "updated",
  "uppdaterad", "opt", "opted", "bounced", "bounce", "id", "ids", "count", "antal", "fax", "assistant",
  "assistent", "parent", "moder", "previous", "tidigare", "deal", "affar", "opportunity", "campaign", "kampanj",
  "status", "score", "poang", "confidence", "verified", "verification", "valid", "quality", "grade", "linkedin",
  "facebook", "twitter", "instagram", "skype", "profile", "profil", "home", "hem", "privat", "private",
  "personal", "extension", "anknytning", "ext", "country", "land", "code", "kod", "not", "ej", "inte", "billing",
  "faktura", "invoice", "shipping", "leverans", "delivery", "source", "kalla", "type", "typ", "date", "datum",
  "time", "tid", "last", "senaste", "senast", "next", "nasta", "email", "emails", "mail", "phone", "phones",
  "telefon", "mobil", "mobile"
]);

const FOR = new Set(["for", "till", "per"]);

/** Fältets egna ord är inga nej-ord: "Phones / Primary Phone Number". */
const EGNA: Partial<Record<Mal, Set<string>>> = {
  contact_email: new Set(["email", "emails", "mail"]),
  contact_phone: new Set(["phone", "phones", "telefon", "mobil", "mobile"])
};

/** Avdrag för ett alias som bara är en del av rubriken, eller `null` när
 *  resten av rubriken säger att det är något annat. */
function inneslutning(full: string, alias: string, mal: Mal): number | null {
  const hel = ` ${full} `;
  const pos = hel.indexOf(` ${alias} `);
  if (pos < 0) return null;
  const ovriga = `${hel.slice(0, pos)} ${hel.slice(pos + alias.length + 2)}`
    .trim()
    .split(/\s+/)
    .filter((o) => o && !EGNA[mal]?.has(o));
  // Sist i rubriken är aliaset huvudordet ("Kontaktperson e-post" är en
  // adress), utom efter en preposition ("Company Name for Emails" är ett
  // namn). Annars måste resten vara ofarliga ord.
  if (hel.endsWith(` ${alias} `)) return ovriga.some((o) => NEJ.has(o) || FOR.has(o)) ? null : 10 + ovriga.length * 2;
  return ovriga.every((o) => NEUTRALA.has(o)) ? 30 + ovriga.length * 2 : null;
}

/** `rang` är platsen i preferensordningen för det bästa alias som träffade. */
type Traff = { mal: Mal; poang: number; rang: number };

/** Fälten rubriken kan vara, med poäng: hel rubrik 100, alias sist 90, alias
 *  på annan plats 70, svagt alias 50 (minus aliasets plats i preferensordningen). */
function traffar(rubrik: string): Traff[] {
  const full = normRubrik(rubrik);
  if (!full) return [];
  const bas = normRubrik(rubrik.replace(/\([^)]*\)/g, " "));
  const ut: Traff[] = [];
  for (const mal of MAL) {
    const { stark, svag = [] } = ALIAS[mal];
    let poang = 0;
    let rang = Number.POSITIVE_INFINITY;
    stark.forEach((alias, i) => {
      const grund = 100 - i * 0.25;
      const avdrag = full === alias || bas === alias ? 0 : inneslutning(full, alias, mal);
      if (avdrag === null) return;
      poang = Math.max(poang, grund - avdrag);
      rang = Math.min(rang, i);
    });
    svag.forEach((alias, i) => {
      if (full === alias || bas === alias) poang = Math.max(poang, 50 - i * 0.25);
    });
    if (poang > 0) ut.push({ mal, poang, rang });
  }
  return ut;
}

// ----------------------------------------------------------------- tabellen

export type Tabell = {
  /** Rubrikradens index bland bladets rader; -1 när filen saknar rubrikrad. */
  rubrikrad: number;
  /** Rubrikerna som de står i filen, gjorda unika ("Namn", "Namn (2)"). Tom
   *  sträng för en kolumn utan rubrik. */
  rubriker: string[];
  /** Raderna under rubrikraden, utan fot, summarader och upprepade rubriker. */
  data: string[][];
  /** Rader under rubrikraden som inte är data och därför rensats bort. */
  bortrensade: number;
};

const ifyllda = (rad: string[]) => rad.filter((c) => c && c.trim() !== "").length;

/** Ser cellen ut som data (en adress, ett org.nr, ett nummer, ett datum)? */
function arData(c: string): boolean {
  return Boolean(
    tolkaEpost(c).varde || tolkaOrgnr(c).varde?.includes("-") || (/^[+0]/.test(c.trim()) && tolkaTelefon(c).varde) || tolkaDatum(c).varde
  );
}

const rubrikpoang = (rad: string[]) => new Set(rad.flatMap((c) => traffar(c).filter((t) => t.poang >= 60).map((t) => t.mal))).size;

/**
 * Rubrikraden: den av de femton första raderna där flest celler är kända
 * rubriker (Monday och handgjorda listor har titelrader överst). Känns ingen
 * rubrik igen och första raden ser ut som data saknar filen rubrikrad (-1).
 */
export function hittaRubrikrad(rader: string[][]): number {
  let bast = 0;
  let bastPoang = 0;
  rader.slice(0, 15).forEach((rad, i) => {
    const poang = rubrikpoang(rad);
    if (poang > bastPoang) {
      bast = i;
      bastPoang = poang;
    }
  });
  if (bastPoang === 0 && (rader[0] ?? []).some(arData)) return -1;
  return bast;
}

/** Rapportfoten i en Salesforce-export, utskriftsrader och liknande. */
const FOT = /copyright|©|confidential|konfidentiell|all rights reserved|generated by|genererad|exporterad|exported|utskriven|printed|filtered by|sida \d|page \d/i;
/** "Summa", "Totalt: 5", "Antal rader = 12". Inte "Total Bygg AB". */
const SUMMA = /^(summa|delsumma|totalt?|grand total|sum|antal)(\s+(rader|poster|antal|kunder|bolag|rows))?\s*([:=].*)?$/i;

export function tolkaTabell(rader: string[][], valdRubrikrad?: number): Tabell {
  const rubrikrad = valdRubrikrad ?? hittaRubrikrad(rader);
  const ra = rubrikrad < 0 ? [] : (rader[rubrikrad] ?? []);
  const kropp = rader.slice(rubrikrad + 1);
  const bredd = kropp.reduce((storst, rad) => Math.max(storst, rad.length), ra.length);

  const sedda = new Map<string, number>();
  const rubriker = Array.from({ length: bredd }, (_, i) => {
    const namn = (ra[i] ?? "").replace(/\s+/g, " ").trim();
    if (!namn) return "";
    const n = (sedda.get(namn.toLowerCase()) ?? 0) + 1;
    sedda.set(namn.toLowerCase(), n);
    return n > 1 ? `${namn} (${n})` : namn;
  });

  // Foten: ett avslutande block rader med en enda ifylld cell, där någon rad
  // ser ut som en fot. Utan fotord är blocket glesa datarader och står kvar.
  let slut = kropp.length;
  if (bredd >= 3) {
    let i = kropp.length;
    while (i > 0 && ifyllda(kropp[i - 1]) <= 1) i--;
    if (i < kropp.length && kropp.slice(i).some((rad) => FOT.test(rad.join(" ")))) slut = i;
  }

  const nyckel = (rad: string[]) => rad.map((c) => (c ?? "").trim().toLowerCase()).join("\u0001");
  const rubriknyckel = nyckel(ra);
  const arRubrik = (rad: string[] | undefined) => rubrikrad >= 0 && rad !== undefined && nyckel(rad) === rubriknyckel;
  const data: string[][] = [];
  for (let i = 0; i < slut; i++) {
    const rad = kropp[i];
    // Monday upprepar rubrikraden under varje grupptitel.
    const grupptitel = bredd >= 3 && ifyllda(rad) === 1 && arRubrik(kropp[i + 1]);
    const summa = SUMMA.test((rad.find((c) => c && c.trim()) ?? "").trim());
    if (!arRubrik(rad) && !grupptitel && !summa) data.push(rad);
  }
  return { rubrikrad, rubriker, data, bortrensade: kropp.length - data.length };
}

// --------------------------------------------------------------- kolumnerna

type Profil = { ifyllda: number; epost: number; telefon: number; orgnr: number; webb: number; datum: number; tal: number };

/** Andelen av kolumnens ifyllda celler (de 200 första raderna) som är adresser,
 *  nummer, org.nr, webbadresser, datum och rena tal. */
function profil(data: string[][], kol: number): Profil {
  const varden = data
    .slice(0, 200)
    .map((rad) => (rad[kol] ?? "").trim())
    .filter(Boolean);
  const andel = (ok: (v: string) => unknown) => (varden.length ? varden.filter((v) => Boolean(ok(v))).length / varden.length : 0);
  return {
    ifyllda: varden.length,
    epost: andel((v) => tolkaEpost(v).varde),
    // Ett telefonnummer börjar med 0 eller +; tio siffror som börjar med 5 är ett org.nr.
    telefon: andel((v) => /^[+0(']/.test(v) && tolkaTelefon(v).varde),
    orgnr: andel((v) => tolkaOrgnr(v).varde?.includes("-")),
    webb: andel((v) => !v.includes("@") && tolkaWebb(v).varde),
    datum: andel((v) => tolkaDatum(v).varde),
    tal: andel((v) => /^[\d\s.,+-]+$/.test(v))
  };
}

/** Håller kolumnens innehåll för fältet rubriken pekar ut? */
function haller(mal: Mal, p: Profil): boolean {
  if (mal === "avtalsslut") return p.datum >= 0.5;
  if (p.ifyllda < 3) return true;
  if (mal === "contact_email") return p.epost >= 0.2;
  if (mal === "contact_phone") return p.telefon >= 0.2 || p.tal >= 0.5;
  if (mal === "website") return p.webb >= 0.2;
  if (mal === "company_name" || mal === "contact_name" || mal === "fornamn" || mal === "efternamn") {
    return p.epost < 0.5 && p.tal < 0.8 && p.datum < 0.8;
  }
  return true;
}

/** Dynamics dolda kolumner: "(Do Not Modify) Account" är ett id, inte bolaget. */
const DOLD = /^\(do not modify\)/i;
/** Kolumner som aldrig är en extra uppgift: interna id:n och kontrollsummor. */
const SKRAP = /(^| )(id|ids|guid|uuid|checksum|hash)$/;
/**
 * Affärsuppgifter som följer med raden utan att kunden behöver be om det:
 * status, fas, förlustorsak, bransch, storlek, nuvarande leverantör, avtalets
 * övriga uppgifter. Allt annat lämnas utanför tills kunden väljer det
 * (dataminimering: en CRM-export bär mer än utskicket behöver).
 */
const EXTRA_STAM = [
  "status", "stage", "steg", "etikett", "label", "kategori", "category", "relation", "lifecycle", "journey",
  "bransch", "industry", "anstallda", "employees", "omsattning", "revenue", "leverantor", "operator", "supplier",
  "provider", "abonnemang", "produkt", "product", "forlora", "lost", "orsak", "reason", "avtal", "contract",
  "bindningstid", "kundnummer", "kundnr", "customer number", "type", "typ"
];
const EJ_EXTRA = /(^| )(email|emails|mail|phone|telefon|linkedin|owner|agare|opt|verification|verified|confidence)( |$)/;
const MAX_AUTOEXTRA = 12;

/**
 * Första förslaget på vad varje kolumn är. Rubrikerna poängsätts mot
 * aliaslistan och fördelas bäst först; innehållet fäller en kolumn som inte
 * håller, och hittar adresser, org.nr, webbplatser och telefonnummer i
 * kolumner vars rubrik inte sade något.
 */
export function gissaKolumner(tabell: Tabell): Kolumnval[] {
  const { rubriker, data } = tabell;
  const profiler = rubriker.map((_, kol) => profil(data, kol));
  const val: Kolumnval[] = rubriker.map(() => "hoppa");
  const antal = new Map<Mal, number>();

  const kandidater = rubriker
    .flatMap((rubrik, kol) =>
      profiler[kol].ifyllda === 0 || DOLD.test(rubrik.trim()) ? [] : traffar(rubrik).map((t) => ({ kol, ...t }))
    )
    .filter((k) => k.poang >= 45)
    .sort((a, b) => b.poang - a.poang || a.kol - b.kol);
  for (const k of kandidater) {
    if (val[k.kol] !== "hoppa") continue;
    const redan = antal.get(k.mal) ?? 0;
    if (redan > 0 && (!FLERVAL.has(k.mal) || k.poang < 60 || redan >= 4)) continue;
    if (!haller(k.mal, profiler[k.kol])) continue;
    val[k.kol] = k.mal;
    antal.set(k.mal, redan + 1);
  }

  // Innehållet hittar det rubriken inte sade. En rubrik med ett nej-ord
  // ("Home Phone", "Owner Email") har redan sagt nej.
  const avvisad = rubriker.map((rubrik) => DOLD.test(rubrik.trim()) || normRubrik(rubrik).split(" ").some((o) => NEJ.has(o)));
  const basta = (andel: (p: Profil) => number, krav = 0.6) => {
    let kol = -1;
    profiler.forEach((p, i) => {
      if (val[i] !== "hoppa" || avvisad[i] || p.ifyllda < 2 || andel(p) < krav) return;
      if (kol < 0 || andel(p) > andel(profiler[kol])) kol = i;
    });
    return kol;
  };
  const fyll = (mal: Mal, andel: (p: Profil) => number) => {
    if (antal.has(mal)) return;
    const kol = basta(andel);
    if (kol >= 0) {
      val[kol] = mal;
      antal.set(mal, 1);
    }
  };
  fyll("contact_email", (p) => p.epost);
  fyll("orgnr", (p) => p.orgnr);
  fyll("website", (p) => (p.epost < 0.2 ? p.webb : 0));
  fyll("contact_phone", (p) => p.telefon);

  let autoextra = 0;
  rubriker.forEach((rubrik, kol) => {
    if (val[kol] !== "hoppa" || profiler[kol].ifyllda === 0) return;
    const norm = normRubrik(rubrik);
    if (!norm || DOLD.test(rubrik.trim()) || SKRAP.test(norm) || EJ_EXTRA.test(norm)) return;
    if (autoextra < MAX_AUTOEXTRA && EXTRA_STAM.some((stam) => norm.includes(stam))) {
      val[kol] = "extra";
      autoextra++;
    }
  });
  return val;
}

/**
 * Kolumnerna för ett flervalsfält i den ordning de prövas: personens egna
 * uppgifter före bolagets ("ContactPersonEmail" före "EmailAddress"), mobilen
 * före växeln. En kolumn kunden själv pekat ut utan känd rubrik prövas sist.
 */
export function flervalsordning(rubriker: string[], kolumner: number[], falt: "contact_email" | "contact_phone"): number[] {
  const rang = (kol: number) => traffar(rubriker[kol] ?? "").find((t) => t.mal === falt)?.rang ?? Number.POSITIVE_INFINITY;
  return [...kolumner].sort((a, b) => rang(a) - rang(b) || a - b);
}

/**
 * Ett nytt val för en kolumn. Ett fält som bara får en kolumn flyttas dit:
 * kolumnen som hade det hoppas över. E-post och telefon får ha flera.
 */
export function bytKolumnval(val: Kolumnval[], kol: number, nytt: Kolumnval): Kolumnval[] {
  return val.map((v, i) => {
    if (i === kol) return nytt;
    if (v === nytt && nytt !== "extra" && nytt !== "hoppa" && !FLERVAL.has(nytt)) return "hoppa";
    return v;
  });
}
