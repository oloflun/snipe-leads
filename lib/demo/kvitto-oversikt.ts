import type { Kvitto } from "@/components/kvitton/KvittoYta";
import { MEJL } from "@/lib/demo/kvitton";

/**
 * Exempeldata för Kvitton › Översikt på /demo (Sebbes beställning 2026-10-07:
 * Leads-översiktens layout, anpassad för Kvittohanteraren).
 *
 * Samma regel som lib/demo/kvitton.ts: påhittat, ingen session, ingen databas.
 * September är demons inkorg (`MEJL`), så att översikten och skanningen
 * berättar samma historia; veckorna före är en deterministisk mall med samma
 * leverantörer, så att veckografen och förändringen mot föregående period har
 * något att visa. Inga slumptal: samma rader vid varje rendering, på servern
 * och i webbläsaren.
 */

/** Demons "i dag": dagen efter inkorgens sista kvitto. */
export const DEMO_IDAG = "2026-09-15";

const KATEGORINYCKEL: Record<string, string> = {
  Drivmedel: "drivmedel",
  Representation: "representation",
  Kontorsmateriel: "kontorsmateriel",
  Prenumerationer: "programvara",
  "Resor & transport": "biljett",
  Logi: "kost_och_logi",
  "Verktyg & förbrukning": "forbrukningsinventarier",
  "Övrigt": "ovrig_extern_kostnad"
};

function rad(del: Partial<Kvitto> & Pick<Kvitto, "id" | "datum" | "motpart">): Kvitto {
  return {
    filnamn: null,
    brutto: null,
    momssats: null,
    kategori: null,
    kategorietikett: "",
    riktning: "kostnad",
    status: "klar",
    betalstatus: "betald",
    kalla: "mejl",
    mejl_amne: null,
    mejl_avsandare: null,
    valuta: "SEK",
    belopp_original: null,
    anmarkning: "",
    granskningsstatus: "KLAR_FÖR_GRANSKNING", // inte-copy: backendens statuskod
    flaggor: [],
    forfallodatum: null,
    ...del
  };
}

/** Septembers kvitton ur demons inkorg, med granskningen backenden hade satt. */
function septembersKvitton(): Kvitto[] {
  const granskning: Record<string, Pick<Kvitto, "granskningsstatus" | "flaggor">> = {
    m4: { granskningsstatus: "BEHÖVER_GRANSKNING", flaggor: ["möjlig_dubblett"] }, // inte-copy: statuskod
    m5: { granskningsstatus: "BEHÖVER_GRANSKNING", flaggor: ["utländsk_valuta", "utländsk_leverantör"] }, // inte-copy: statuskod
    m11: { granskningsstatus: "KRÄVER_MANUELL_HÄMTNING", flaggor: ["saknar_obligatoriska_fält"] } // inte-copy: statuskod
  };
  return MEJL.filter((m) => m.utfall !== "ej_kvitto").map((m) => {
    const kategori = m.kategoriEtikett ? (KATEGORINYCKEL[m.kategoriEtikett] ?? null) : null;
    return rad({
      id: `demo-${m.id}`,
      datum: m.datum,
      motpart: m.avsandare,
      brutto: m.belopp,
      momssats: m.momssats ?? null,
      kategori,
      kategorietikett: m.kategoriEtikett ?? "",
      status: m.utfall === "kvitto" ? "klar" : "granska_manuellt",
      mejl_amne: m.amne,
      mejl_avsandare: m.avsandare,
      belopp_original: m.beloppOriginal ?? null,
      anmarkning: m.anmarkning ?? "",
      ...(granskning[m.id] ?? {})
    });
  });
}

type Mall = {
  motpart: string;
  kategori: string;
  etikett: string;
  sats: string;
  /** Grundbelopp i öre, plus en deterministisk variation upp till `variation`. */
  bas: number;
  variation: number;
  /** Var `varje`:e vecka, förskjutet `forskjut` veckor. */
  varje: number;
  forskjut: number;
  /** Dag i veckan, 0 = måndag. */
  dag: number;
  /** Uteblir under semesterveckorna. */
  semester?: boolean;
  kalla?: string;
};

const MALL: Mall[] = [
  { motpart: "Nordvik Drivmedel AB", kategori: "drivmedel", etikett: "Drivmedel", sats: "0.25", bas: 52_000, variation: 14_000, varje: 1, forskjut: 0, dag: 1 },
  { motpart: "Bistro Linnea", kategori: "representation", etikett: "Representation", sats: "0.12", bas: 32_000, variation: 26_000, varje: 2, forskjut: 0, dag: 3, semester: true },
  { motpart: "Molnlagring Norr AB", kategori: "programvara", etikett: "Prenumerationer & programvara", sats: "0.25", bas: 19_900, variation: 0, varje: 4, forskjut: 1, dag: 0 },
  { motpart: "Svenska Tåglinjer AB", kategori: "biljett", etikett: "Resor & transport", sats: "0.06", bas: 74_500, variation: 0, varje: 3, forskjut: 1, dag: 2, semester: true },
  { motpart: "Taxi Mälardalen", kategori: "biljett", etikett: "Resor & transport", sats: "0.06", bas: 24_000, variation: 9_000, varje: 3, forskjut: 2, dag: 4 },
  { motpart: "Skrivbo Kontorsvaror AB", kategori: "kontorsmateriel", etikett: "Kontorsmateriel", sats: "0.25", bas: 30_000, variation: 90_000, varje: 4, forskjut: 2, dag: 2, kalla: "uppladdning" },
  { motpart: "Verktygsboden Nord AB", kategori: "forbrukningsinventarier", etikett: "Verktyg & förbrukning", sats: "0.25", bas: 89_000, variation: 150_000, varje: 3, forskjut: 0, dag: 0, semester: true },
  { motpart: "Stadshotellet Örebro", kategori: "kost_och_logi", etikett: "Logi", sats: "0.12", bas: 169_000, variation: 0, varje: 9, forskjut: 4, dag: 2 },
  { motpart: "Mobilnät Syd AB", kategori: "mobiltelefon", etikett: "Telefoni", sats: "0.25", bas: 34_900, variation: 0, varje: 4, forskjut: 3, dag: 0 },
  { motpart: "Lokaltidningen Mälardalen", kategori: "annonsering", etikett: "Annonsering", sats: "0.25", bas: 250_000, variation: 0, varje: 9, forskjut: 2, dag: 3 }
];

/** Måndagarna före september: v27 till v35. Veckorna 1–3 är semester. */
const MANDAGAR = ["2026-06-29", "2026-07-06", "2026-07-13", "2026-07-20", "2026-07-27", "2026-08-03", "2026-08-10", "2026-08-17", "2026-08-24"];

function plusDagar(iso: string, dagar: number): string {
  const [a, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(a, m - 1, d + dagar)).toISOString().slice(0, 10);
}

function kr(ore: number): string {
  return `${Math.floor(ore / 100)}.${String(ore % 100).padStart(2, "0")}`;
}

function sommarensKvitton(): Kvitto[] {
  const rader: Kvitto[] = [];
  MANDAGAR.forEach((mandag, i) => {
    const semester = i >= 1 && i <= 3;
    MALL.forEach((m, j) => {
      if ((i + m.forskjut) % m.varje !== 0) return;
      if (semester && m.semester) return;
      // Deterministisk variation, avrundad till hela 50-öringar.
      const ore = m.bas + (m.variation ? Math.round((((i + 1) * 7919 + j * 104_729) % m.variation) / 50) * 50 : 0);
      rader.push(
        rad({
          id: `demo-s${i}-${j}`,
          datum: plusDagar(mandag, m.dag),
          motpart: m.motpart,
          brutto: kr(ore),
          momssats: m.sats,
          kategori: m.kategori,
          kategorietikett: m.etikett,
          kalla: m.kalla ?? "mejl",
          // Två avläsningar som granskaren ändå släppte igenom: adminrutans flaggor.
          flaggor: m.kategori === "biljett" && i % 2 === 0 ? ["tvetydigt_datum"] : m.kategori === "representation" && i === 6 ? ["osäker_klassning"] : []
        })
      );
    });
  });
  return rader;
}

/** De två rader som inte kommer ur inkorgen: en obetald faktura och en prioriterad. */
const EXTRA: Kvitto[] = [
  rad({
    id: "demo-x1",
    datum: "2026-09-14",
    motpart: "Kontorshuset Mälardalen AB",
    brutto: "4800.00",
    momssats: "0.25",
    kategori: "lokalhyra",
    kategorietikett: "Lokalhyra",
    status: "granska_manuellt",
    betalstatus: "obetald",
    granskningsstatus: "PRIORITERAD_GRANSKNING", // inte-copy: backendens statuskod
    flaggor: ["misstänkt_bedrägeri"],
    forfallodatum: "2026-09-25",
    anmarkning: "Bankgirot skiljer sig från tidigare fakturor från samma leverantör."
  }),
  rad({
    id: "demo-x2",
    datum: "2026-09-01",
    motpart: "Mobilnät Syd AB",
    brutto: "349.00",
    momssats: "0.25",
    kategori: "mobiltelefon",
    kategorietikett: "Telefoni",
    betalstatus: "obetald",
    forfallodatum: "2026-09-30"
  })
];

/**
 * Exempelbolagets egna fakturor till kunder: intäkterna (sedan 2026-10-07).
 * Sommaren är en mall som kvittona; september står utskriven, med en faktura
 * som väntar på bekräftelse (bara namnet pekade ut den som kundfaktura).
 */
const KUNDER: Mall[] = [
  { motpart: "Mälardalens Bygg AB", kategori: "", etikett: "", sats: "0.25", bas: 1_800_000, variation: 1_200_000, varje: 2, forskjut: 0, dag: 4, semester: true },
  { motpart: "Fastighetsbolaget Norr AB", kategori: "", etikett: "", sats: "0.25", bas: 1_250_000, variation: 0, varje: 4, forskjut: 1, dag: 0 },
  { motpart: "Café Linnégatan", kategori: "", etikett: "", sats: "0.25", bas: 420_000, variation: 360_000, varje: 3, forskjut: 2, dag: 2 }
];

function sommarensFakturor(): Kvitto[] {
  const rader: Kvitto[] = [];
  MANDAGAR.forEach((mandag, i) => {
    const semester = i >= 1 && i <= 3;
    KUNDER.forEach((m, j) => {
      if ((i + m.forskjut) % m.varje !== 0) return;
      if (semester && m.semester) return;
      const ore = m.bas + (m.variation ? Math.round((((i + 3) * 7919 + j * 104_729) % m.variation) / 5000) * 5000 : 0);
      rader.push(
        rad({
          id: `demo-f${i}-${j}`,
          datum: plusDagar(mandag, m.dag),
          motpart: m.motpart,
          brutto: kr(ore),
          momssats: m.sats,
          riktning: "intakt",
          kategorietikett: "Kundfaktura",
          kalla: "uppladdning"
        })
      );
    });
  });
  return rader;
}

const SEPTEMBERS_FAKTUROR: Kvitto[] = [
  rad({ id: "demo-fs1", datum: "2026-09-03", motpart: "Mälardalens Bygg AB", brutto: "28750.00", momssats: "0.25", riktning: "intakt", kategorietikett: "Kundfaktura", betalstatus: "obetald", forfallodatum: "2026-10-03", kalla: "uppladdning" }),
  rad({ id: "demo-fs2", datum: "2026-09-10", motpart: "Café Linnégatan", brutto: "6250.00", momssats: "0.25", riktning: "intakt", kategorietikett: "Kundfaktura" }),
  rad({ id: "demo-fs3", datum: "2026-09-11", motpart: "Fastighetsbolaget Norr AB", brutto: "12500.00", momssats: "0.25", riktning: "intakt", kategorietikett: "Kundfaktura", betalstatus: "obetald", forfallodatum: "2026-10-11" }),
  rad({
    id: "demo-fs4",
    datum: "2026-09-15",
    motpart: "Stenhuggeriet i Kumla AB",
    brutto: "9375.00",
    momssats: "0.25",
    riktning: "intakt",
    kategorietikett: "Kundfaktura",
    status: "granska_manuellt",
    betalstatus: null,
    granskningsstatus: "BEHÖVER_GRANSKNING", // inte-copy: backendens statuskod
    flaggor: ["osäker_klassning"],
    anmarkning: "Säljaren på fakturan har företagets namn men inget organisationsnummer att jämföra; bekräfta att det är en kundfaktura innan intäkten räknas."
  })
];

export function demoKvitton(): Kvitto[] {
  return [...sommarensKvitton(), ...septembersKvitton(), ...EXTRA, ...sommarensFakturor(), ...SEPTEMBERS_FAKTUROR];
}

export const DEMO_MEJLKONTO = { kopplad: true, leverantor: "demo", adress: "kvitton@exempelbolaget.se" } as const;
