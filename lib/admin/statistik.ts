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

/** ISO-veckonummer, för etiketterna ("v.35"). */
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
  /** "v.35" */
  etikett: string;
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
};

export function beraknaKundstatistik(
  tenants: TenantRow[],
  nu: Date,
  antalVeckor = 12
): Kundstatistik {
  const riktiga = tenants.filter((t) => arRiktigKund(t.slug));
  const idagUtc = new Date(Date.UTC(nu.getFullYear(), nu.getMonth(), nu.getDate()));
  const dennaVecka = veckostart(idagUtc);

  const veckor: VeckoPunkt[] = [];
  const index = new Map<number, VeckoPunkt>();
  for (let i = antalVeckor - 1; i >= 0; i -= 1) {
    const start = new Date(dennaVecka.getTime() - i * 7 * 86_400_000);
    const punkt = { etikett: `v.${isoVecka(start)}`, nyaKunder: 0, avtal: 0 };
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
    bortfiltrerade: tenants.length - riktiga.length
  };
}
