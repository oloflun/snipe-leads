import type { TenantRow } from "@/lib/data/admin";

/**
 * Kundstatistiken för fliken Kunder & Data — ren beräkning, ingen rendering.
 *
 * ## Vad som räknas, och vad som uttryckligen inte gör det
 *
 * Demoytorna (nordlys-handel, public-demo) och testarbetsytorna (slug
 * `testkund` eller `testkund-…`) räknas ALDRIG som kunder här. En testyta som
 * ser ut som en riktig kund i en försäljningskurva är exakt den sortens
 * siffra som fattar beslut åt en — samma regel som `is_test` i körnings-
 * volymen. De göms inte: komponenten skriver ut hur många som filtrerats
 * bort.
 *
 * ## Definitionen av försäljningstakt
 *
 * Nya kunder respektive signerade avtal per vecka, med de senaste fyra
 * veckorna jämförda mot de fyra före dem. Det är en VALD definition — det
 * finns ingen orderdata att räkna på — och den står utskriven i vyn så att
 * den kan ifrågasättas.
 *
 * Alla datum är date-strängar (ÅÅÅÅ-MM-DD) från backenden; de jämförs som
 * hela dagar i UTC så att en kund som registrerades 23:30 inte hamnar i fel
 * vecka beroende på var servern står.
 */

const DEMO_SLUGS = new Set(["nordlys-handel", "public-demo"]);

/**
 * Är arbetsytan en av VÅRA demoytor?
 *
 * Smalare än `arRiktigKund()`, som avvisar både demoytor och testytor. De två
 * behöver skiljas åt sedan exempeldatan började räknas med: en testyta med
 * exempelmärke SKA synas i kurvan, en demoyta ska aldrig göra det — den är vår
 * egen skyltdocka, inte en kund vi kan sälja till en gång till.
 */
export function arDemoyta(slug: string | null): boolean {
  return slug !== null && DEMO_SLUGS.has(slug);
}

export function arRiktigKund(slug: string | null): boolean {
  if (!slug) return true;
  if (DEMO_SLUGS.has(slug)) return false;
  return slug !== "testkund" && !slug.startsWith("testkund-");
}

function tillDag(varde: string | null | undefined): Date | null {
  if (!varde) return null;
  // Bara datumdelen — kund_sedan kan komma som "2026-08-15" och en
  // timestamp som "2026-08-15T09:12:00Z" ska räknas som samma dag.
  const d = new Date(`${varde.slice(0, 10)}T00:00:00Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Måndagen i dagens vecka, som UTC-midnatt. */
function veckostart(dag: Date): Date {
  const d = new Date(Date.UTC(dag.getUTCFullYear(), dag.getUTCMonth(), dag.getUTCDate()));
  const veckodag = (d.getUTCDay() + 6) % 7; // 0 = måndag
  d.setUTCDate(d.getUTCDate() - veckodag);
  return d;
}

/** ISO-veckonummer. Etiketten formateras i vyn — se `VeckoPunkt.vecka`. */
export function isoVecka(dag: Date): number {
  const d = new Date(Date.UTC(dag.getUTCFullYear(), dag.getUTCMonth(), dag.getUTCDate()));
  d.setUTCDate(d.getUTCDate() + 4 - ((d.getUTCDay() + 6) % 7) - 1 + 1);
  const arsstart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(((d.getTime() - arsstart.getTime()) / 86_400_000 + 1) / 7);
}

export type Perioder = {
  idag: number;
  veckan: number;
  manaden: number;
  aret: number;
  totalt: number;
};

export function raknaPerioder(datumlista: (string | null)[], nu: Date): Perioder {
  const idagUtc = new Date(Date.UTC(nu.getFullYear(), nu.getMonth(), nu.getDate()));
  const veckan = veckostart(idagUtc);
  const resultat: Perioder = { idag: 0, veckan: 0, manaden: 0, aret: 0, totalt: 0 };

  for (const varde of datumlista) {
    const dag = tillDag(varde);
    if (!dag) continue;
    resultat.totalt += 1;
    if (dag.getUTCFullYear() === idagUtc.getUTCFullYear()) {
      resultat.aret += 1;
      if (dag.getUTCMonth() === idagUtc.getUTCMonth()) resultat.manaden += 1;
    }
    if (dag.getTime() >= veckan.getTime()) resultat.veckan += 1;
    if (dag.getTime() === idagUtc.getTime()) resultat.idag += 1;
  }
  return resultat;
}

export type VeckoPunkt = {
  /**
   * ISO-veckonumret som TAL, inte en färdig etikett.
   *
   * Det stod `"v.35"` här, byggt på servern. Prefixet är svenskt, och i
   * engelskt läge blev axeln därför en rad "v.24 v.25 …" under en i övrigt
   * engelsk graf. Vyn vet vilket språk som gäller; beräkningen gör det inte.
   */
  vecka: number;
  nyaKunder: number;
  avtal: number;
};

export type Kundstatistik = {
  avtal: Perioder;
  nyaKunder: Perioder;
  veckor: VeckoPunkt[];
  /** Senaste 4 veckorna mot de 4 före dem. */
  takt: {
    senaste: { kunder: number; avtal: number };
    foregaende: { kunder: number; avtal: number };
  };
  /** Demo- och testytor som INTE ingår i något av talen ovan. */
  bortfiltrerade: number;
  /** Hur många av de MEDRÄKNADE raderna som bär exempeldata. */
  exempel: number;
};

/** Raden som statistiken räknar på: tenanten plus exempelmärket, om det finns. */
export type Statistikrad = TenantRow & { ar_exempel?: boolean };

/**
 * Räknas raden som kund i statistiken?
 *
 * `arRiktigKund()` ensam var villkoret förut, och den regeln står kvar orörd:
 * en test- eller demoyta ska inte smyga in i en försäljningskurva. Det som
 * tillkommit är att en rad som bär EXEMPELMÄRKET räknas ändå.
 *
 * Skillnaden mellan de två fallen är att exempelraden är MÄRKT. Vyn skriver ut
 * hur många av talen som kommer därifrån, så den som läser kurvan vet vad hen
 * ser. En omärkt testyta hade sett ut som en kund, och det är det
 * `arRiktigKund()` finns för att förhindra.
 *
 * DEMOYTORNA ar undantagna oavsett marke, och det ar inte en detalj: forsta
 * versionen slapp in `public-demo` men inte `nordlys-handel`, av det godtyckliga
 * skalet att den forra saknade aktivitet och darfor blev berikad medan den
 * senare hade riktig trafik och inte blev det. Tva demoytor, olika behandling,
 * avgjort av nagot som inte har med saken att gora. `arDemoyta()` avgor det nu
 * i stallet.
 */
export function raknasSomKund(rad: Statistikrad): boolean {
  if (arDemoyta(rad.slug)) return false;
  return arRiktigKund(rad.slug) || rad.ar_exempel === true;
}

export function beraknaKundstatistik(
  tenants: readonly Statistikrad[],
  nu: Date,
  antalVeckor = 12
): Kundstatistik {
  const riktiga = tenants.filter(raknasSomKund);
  const idagUtc = new Date(Date.UTC(nu.getFullYear(), nu.getMonth(), nu.getDate()));
  const dennaVecka = veckostart(idagUtc);

  const veckor: VeckoPunkt[] = [];
  const index = new Map<number, VeckoPunkt>();
  for (let i = antalVeckor - 1; i >= 0; i -= 1) {
    const start = new Date(dennaVecka.getTime() - i * 7 * 86_400_000);
    const punkt = { vecka: isoVecka(start), nyaKunder: 0, avtal: 0 };
    veckor.push(punkt);
    index.set(start.getTime(), punkt);
  }

  const taktFonster = (dagar: number) =>
    new Date(dennaVecka.getTime() - dagar * 86_400_000).getTime();
  // "Senaste 4" = innevarande vecka + 3 bakåt; "föregående 4" = de 4 före dem.
  const senasteStart = taktFonster(21);
  const foregaendeStart = taktFonster(49);
  const takt = {
    senaste: { kunder: 0, avtal: 0 },
    foregaende: { kunder: 0, avtal: 0 }
  };

  for (const tenant of riktiga) {
    for (const [falt, serie] of [
      ["kund_sedan", "nyaKunder"],
      ["avtal_signerat", "avtal"]
    ] as const) {
      const dag = tillDag(tenant[falt]);
      if (!dag) continue;
      const punkt = index.get(veckostart(dag).getTime());
      if (punkt) punkt[serie] += 1;

      const t = dag.getTime();
      const taktNyckel = serie === "nyaKunder" ? "kunder" : "avtal";
      if (t >= senasteStart) takt.senaste[taktNyckel] += 1;
      else if (t >= foregaendeStart) takt.foregaende[taktNyckel] += 1;
    }
  }

  return {
    avtal: raknaPerioder(riktiga.map((t) => t.avtal_signerat ?? null), nu),
    nyaKunder: raknaPerioder(riktiga.map((t) => t.kund_sedan ?? null), nu),
    veckor,
    takt,
    bortfiltrerade: tenants.length - riktiga.length,
    exempel: riktiga.filter((t) => t.ar_exempel === true).length
  };
}
