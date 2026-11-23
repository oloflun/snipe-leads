"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Cell, Rad, Radlista, Tabell, btnPrimary, btnSecondary, chip, chipAktiv, chipInaktiv, chiplista, etikett, faltTatt, meta, rubrikPanel, tabellRad } from "@/components/ui";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { ImportFel, lasImportfil, type ImportFelkod, type Importfil } from "@/lib/leads/importfil";
import { FLERVAL, bytKolumnval, gissaKolumner, tolkaTabell, type ImportFalt, type Kolumnval } from "@/lib/leads/importmallar";
import { sammanfatta, tolkaRader, type Radutfall } from "@/lib/leads/importrader";
import type { Anmarkningskod } from "@/lib/leads/importvarden";
import { leadsAnrop } from "@/lib/leads/suite";
import { cn } from "@/lib/utils";

/**
 * Import av kundens egen lista (hårdtest och ombyggnad 2026-11-23, Antons
 * beställning efter Buddy: "leads med vår egen data").
 *
 * Fyra steg på samma plats i sidan, efter Twentys import:
 *
 *   Fil       CSV, text eller Excel läses i webbläsaren (lib/leads/importfil.ts)
 *   Kolumner  varje kolumn i filen får ett fält; förslaget kommer ur rubriken
 *             och innehållet (lib/leads/importmallar.ts), kunden ändrar fritt
 *   Granska   vad som importeras och vad som hoppas över, och varför: värden
 *             som inte håller, dubbletter i filen, befintliga kunder, bolag som
 *             redan är leads och spärrade adresser (POST /leads/import/granska)
 *   Klart     kvittot. Det sparas på listan (`importinfo`, migration 152) och
 *             står kvar efter en omladdning.
 *
 * `kalla="crm"` (migration 098): kundens BEFINTLIGA kunder. Samma steg, men
 * listan blir en uteslutningsmängd: Iris och listorna hoppar över bolagen.
 */

/** Backendens tak för en lista, och hur många rader en begäran bär. */
const MAX_RADER = 5000;
const SATS = 500;
const VISA_STEG = 50;

type Steg = "fil" | "kolumner" | "granska" | "klart";
const STEGORDNING: Steg[] = ["fil", "kolumner", "granska", "klart"];

type Flagga = "kund" | "lead" | "sparrad";
type Radstatus = "ok" | "anmarkning" | "utan_bolag" | "dubblett" | Flagga;
type Radfilter = "alla" | "importeras" | "anmarkning" | "hoppas";
type Hoppade = { utan_bolag: number; dubbletter: number; redan_kund: number; redan_lead: number; sparrade: number };

export type ImporteradLista = { id: string; titel: string; [nyckel: string]: unknown };

/** Kvittot som sparas på listan (lead_lists.importinfo). */
export type Importinfo = {
  fil: string;
  format: string;
  rader_i_fil: number;
  importerade: number;
  hoppade: Hoppade;
  anmarkningar: number;
  /** Filens rubrik → fältet den blev. */
  kolumner: Record<string, string>;
  importerad_at: string;
};

type Importsvar = { list: ImporteradLista; antal: number; hoppade_over: number; hoppade?: Partial<Hoppade> };

const T = {
  stegFil: { sv: "Fil", en: "File" },
  stegKolumner: { sv: "Kolumner", en: "Columns" },
  stegGranska: { sv: "Granska", en: "Review" },
  stegKlart: { sv: "Klart", en: "Done" },
  steg: { sv: "Importens steg", en: "Import steps" },
  slapp: { sv: "Släpp filen här eller välj en fil", en: "Drop the file here or choose a file" },
  format: {
    sv: "CSV, text eller Excel (.xlsx). Exporten kan komma ur HubSpot, Pipedrive, Salesforce, Dynamics, Lime, Upsales, SuperOffice, Fortnox, Visma eller ett eget kalkylblad.",
    en: "CSV, text or Excel (.xlsx). The export can come from HubSpot, Pipedrive, Salesforce, Dynamics, Lime, Upsales, SuperOffice, Fortnox, Visma or your own spreadsheet."
  },
  laser: { sv: "Läser filen…", en: "Reading the file…" },
  ingaRader: { sv: "Filen har inga rader under rubrikraden.", en: "The file has no rows below the header row." },
  titel: { sv: "Listans namn", en: "List name" },
  blad: { sv: "Blad", en: "Sheet" },
  rubrikrad: { sv: "Rubrikrad", en: "Header row" },
  utanRubrik: { sv: "Filen saknar rubrikrad", en: "The file has no header row" },
  rad: { sv: "Rad", en: "Row" },
  kolumn: { sv: "Kolumn", en: "Column" },
  kolumnIFilen: { sv: "Kolumner i filen", en: "Columns in the file" },
  blir: { sv: "Blir", en: "Becomes" },
  ingetBolag: { sv: "Välj vilken kolumn som är bolagsnamnet.", en: "Choose which column holds the company name." },
  flera: {
    sv: "Flera kolumner har samma fält. Den första med ett giltigt värde används, rad för rad.",
    en: "Several columns share a field. The first one with a valid value is used, row by row."
  },
  extraHjalp: {
    sv: "Extra uppgifter följer med raden som de står i filen. Kolumner du inte väljer lämnas utanför.",
    en: "Extra details follow the row as they stand in the file. Columns you do not choose are left out."
  },
  tillbaka: { sv: "Tillbaka", en: "Back" },
  bytFil: { sv: "Välj en annan fil", en: "Choose another file" },
  granskar: { sv: "Jämför med dina kunder och leads…", en: "Comparing with your customers and leads…" },
  taMedLeads: {
    sv: "Ta med bolag som redan finns bland dina leads",
    en: "Include companies that are already among your leads"
  },
  filterAlla: { sv: "Alla", en: "All" },
  filterImporteras: { sv: "Importeras", en: "Imported" },
  filterAnmarkning: { sv: "Med anmärkning", en: "With remarks" },
  filterHoppas: { sv: "Hoppas över", en: "Skipped" },
  bolag: { sv: "Bolag", en: "Company" },
  kontakt: { sv: "Kontakt", en: "Contact" },
  utfall: { sv: "Utfall", en: "Outcome" },
  raderna: { sv: "Filens rader", en: "The file's rows" },
  visaFler: { sv: "Visa fler", en: "Show more" },
  importerar: { sv: "Importerar", en: "Importing" },
  forsokIgen: { sv: "Försök igen", en: "Try again" },
  demo: { sv: "Importen sparas inte i demon.", en: "The import is not saved in the demo." },
  crmTitel: { sv: "Befintliga kunder (CRM)", en: "Existing customers (CRM)" },
  oppna: { sv: "Öppna listan", en: "Open the list" },
  enTill: { sv: "Importera en fil till", en: "Import another file" },
  importeras: { sv: "Importeras", en: "Imported" },
  hoppasOver: { sv: "Hoppas över", en: "Skipped" }
} satisfies Record<string, Localized>;

const STEGNAMN: Record<Steg, Localized> = { fil: T.stegFil, kolumner: T.stegKolumner, granska: T.stegGranska, klart: T.stegKlart };

const VAL_ETIKETT: Record<Kolumnval, Localized> = {
  company_name: { sv: "Bolag", en: "Company" },
  orgnr: { sv: "Org.nr", en: "Org. no." },
  contact_name: { sv: "Kontaktperson", en: "Contact person" },
  fornamn: { sv: "Förnamn", en: "First name" },
  efternamn: { sv: "Efternamn", en: "Last name" },
  contact_role: { sv: "Roll", en: "Role" },
  contact_email: { sv: "E-post", en: "Email" },
  contact_phone: { sv: "Telefon", en: "Phone" },
  website: { sv: "Webbplats", en: "Website" },
  ort: { sv: "Ort", en: "City" },
  avtalsslut: { sv: "Avtalsslut", en: "Contract end" },
  extra: { sv: "Ta med som extra uppgift", en: "Keep as an extra detail" },
  hoppa: { sv: "Importera inte", en: "Do not import" }
};

const FALTVAL: Kolumnval[] = [
  "company_name", "orgnr", "contact_name", "fornamn", "efternamn", "contact_role", "contact_email", "contact_phone",
  "website", "ort", "avtalsslut"
];

const FELTEXT: Record<ImportFelkod, Localized> = {
  xls: {
    sv: "Det gamla Excel-formatet (.xls) går inte att läsa. Öppna filen i Excel och spara den som Excel-arbetsbok (.xlsx) eller CSV.",
    en: "The old Excel format (.xls) cannot be read. Open the file in Excel and save it as an Excel workbook (.xlsx) or CSV."
  },
  format: {
    sv: "Filen innehåller ingen tabell som går att läsa. Ladda upp en CSV-fil eller en Excel-arbetsbok (.xlsx).",
    en: "The file holds no table that can be read. Upload a CSV file or an Excel workbook (.xlsx)."
  },
  stor: {
    sv: "Filen är större än 15 MB. Dela upp den, eller spara bara de kolumner som behövs.",
    en: "The file is larger than 15 MB. Split it, or save only the columns that are needed."
  },
  trasig: {
    sv: "Filen gick inte att öppna. Spara den på nytt från programmet den kommer ifrån och försök igen.",
    en: "The file could not be opened. Save it again from the program it came from and try again."
  },
  tom: { sv: "Filen har inga rader.", en: "The file has no rows." }
};

/** Vad som är fel med värdet. Står efter värdet i citat: ”eva(at)x.se” är ingen giltig adress. */
const ANMARKNING: Record<Anmarkningskod, Localized> = {
  epost: { sv: "är ingen giltig adress", en: "is not a valid address" },
  telefon: { sv: "är inget telefonnummer", en: "is not a phone number" },
  orgnr: { sv: "är inget giltigt org.nr", en: "is not a valid org. no." },
  personnummer: { sv: "är ett personnummer och sparas inte", en: "is a personal identity number and is not stored" },
  webb: { sv: "är ingen webbadress", en: "is not a web address" },
  datum: { sv: "går inte att läsa som datum", en: "cannot be read as a date" },
  excel: { sv: "är ett tal som Excel gjort om, siffrorna saknas", en: "is a number Excel has converted, the digits are gone" }
};

const HOPPSKAL: Record<Exclude<Radstatus, "ok" | "anmarkning">, Localized> = {
  utan_bolag: { sv: "bolagsnamn saknas", en: "no company name" },
  dubblett: { sv: "samma bolag står redan i filen", en: "the same company is already in the file" },
  kund: { sv: "redan din kund", en: "already your customer" },
  lead: { sv: "finns redan bland dina leads", en: "already among your leads" },
  sparrad: { sv: "adressen har avböjt kontakt", en: "the address has declined contact" }
};

const ACCEPT = ".csv,.tsv,.tab,.txt,.xlsx,.xls,.xml,.html,.htm,text/csv,text/plain,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

/** Radens läge i granskningen. En rad med en serverflagga hoppas över, utom
 *  ett befintligt lead som kunden valt att ta med. */
function radstatus(u: Radutfall, flagga: Flagga | null, taMedLeads: boolean): Radstatus {
  if (!u.rad) return "utan_bolag";
  if (u.dubblettAv !== undefined) return "dubblett";
  if (flagga && !(flagga === "lead" && taMedLeads)) return flagga;
  return u.anmarkningar.length ? "anmarkning" : "ok";
}

const importeras = (s: Radstatus) => s === "ok" || s === "anmarkning";

export function ImportLista({
  onKlar,
  onOppna,
  demo = false,
  kalla = "import"
}: Readonly<{
  onKlar: (lista: ImporteradLista) => void;
  /** Öppnar den importerade listan. Utan den visas ingen sådan knapp. */
  onOppna?: (lista: ImporteradLista) => void;
  demo?: boolean;
  kalla?: "import" | "crm";
}>) {
  const crm = kalla === "crm";
  const { text, locale } = useLocale();
  const [steg, setSteg] = useState<Steg>("fil");
  const [fil, setFil] = useState<{ namn: string; innehall: Importfil } | null>(null);
  const [bladIndex, setBladIndex] = useState(0);
  const [rubrikrad, setRubrikrad] = useState<number | undefined>(undefined);
  const [val, setVal] = useState<Kolumnval[]>([]);
  const [titel, setTitel] = useState("");
  const [laser, setLaser] = useState(false);
  const [drar, setDrar] = useState(false);
  const [fel, setFel] = useState<string | null>(null);

  const [flaggor, setFlaggor] = useState<(Flagga | null)[] | null>(null);
  const [taMedLeads, setTaMedLeads] = useState(false);
  const [filter, setFilter] = useState<Radfilter>("alla");
  const [visade, setVisade] = useState(VISA_STEG);

  const [forlopp, setForlopp] = useState<{ klara: number; totalt: number } | null>(null);
  const [importerar, setImporterar] = useState(false);
  const [kvitto, setKvitto] = useState<{ lista: ImporteradLista; importerade: number; hoppade: Hoppade; anmarkningar: number } | null>(null);
  /** En import som stannat halvvägs fortsätter härifrån i stället för att börja om. */
  const pagaende = useRef<{ listId: string; klara: number; importerade: number; server: Hoppade } | null>(null);

  const rubrik = useRef<HTMLHeadingElement>(null);
  const forstaSteg = useRef(true);
  // Ett nytt steg flyttar fokus till stegets rubrik: annars står en
  // skärmläsare kvar på en knapp som inte längre finns.
  useEffect(() => {
    if (forstaSteg.current) {
      forstaSteg.current = false;
      return;
    }
    rubrik.current?.focus();
  }, [steg]);

  const blad = fil?.innehall.blad[bladIndex];
  const tabell = useMemo(() => (blad ? tolkaTabell(blad.rader, rubrikrad) : null), [blad, rubrikrad]);
  const utfall = useMemo(() => (tabell ? tolkaRader(tabell, val) : []), [tabell, val]);
  const summering = useMemo(() => sammanfatta(utfall), [utfall]);
  /** Raderna som jämförs med servern: de med bolagsnamn som inte är dubbletter. */
  const kandidater = useMemo(() => utfall.filter((u) => u.rad && u.dubblettAv === undefined), [utfall]);

  const statusar = useMemo(() => {
    const flaggaFor = new Map(kandidater.map((u, i) => [u.index, flaggor?.[i] ?? null]));
    return utfall.map((u) => radstatus(u, flaggaFor.get(u.index) ?? null, taMedLeads));
  }, [utfall, kandidater, flaggor, taMedLeads]);
  const antal = useMemo(() => {
    const n: Record<Radstatus, number> = { ok: 0, anmarkning: 0, utan_bolag: 0, dubblett: 0, kund: 0, lead: 0, sparrad: 0 };
    for (const s of statusar) n[s]++;
    return n;
  }, [statusar]);
  const attImportera = useMemo(() => utfall.filter((_, i) => importeras(statusar[i])), [utfall, statusar]);
  const antalLeads = flaggor?.filter((f) => f === "lead").length ?? 0;

  function nollstallGranskning() {
    setFlaggor(null);
    setFilter("alla");
    setVisade(VISA_STEG);
  }

  /** Ny fil, nytt blad eller ny rubrikrad: kolumnförslaget görs om. */
  function valjTabell(innehall: Importfil, nyttBlad: number, nyRubrikrad: number | undefined) {
    setBladIndex(nyttBlad);
    setRubrikrad(nyRubrikrad);
    setVal(gissaKolumner(tolkaTabell(innehall.blad[nyttBlad].rader, nyRubrikrad)));
    nollstallGranskning();
  }

  async function lasFil(f: File | undefined) {
    if (!f || laser) return;
    setFel(null);
    setLaser(true);
    try {
      const innehall = await lasImportfil(new Uint8Array(await f.arrayBuffer()));
      setFil({ namn: f.name, innehall });
      valjTabell(innehall, 0, undefined);
      setTitel(crm ? text(T.crmTitel) : f.name.replace(/\.[a-z0-9]+$/i, ""));
      pagaende.current = null;
      setKvitto(null);
      setSteg("kolumner");
    } catch (orsak) {
      setFel(orsak instanceof ImportFel ? text(FELTEXT[orsak.kod]) : text(FELTEXT.trasig));
    } finally {
      setLaser(false);
    }
  }

  function bytVal(kol: number, nytt: Kolumnval) {
    setVal((v) => bytKolumnval(v, kol, nytt));
    nollstallGranskning();
  }

  async function granska() {
    setFel(null);
    setSteg("granska");
    if (demo || crm || kandidater.length === 0) {
      setFlaggor(kandidater.map(() => null));
      return;
    }
    try {
      const svar = await leadsAnrop<{ flaggor: (Flagga | null)[] }>("/leads/import/granska", {
        method: "POST",
        body: JSON.stringify({
          kalla,
          rader: kandidater.map((u) => ({ company_name: u.rad!.company_name, orgnr: u.rad!.orgnr, contact_email: u.rad!.contact_email }))
        })
      });
      setFlaggor(svar.flaggor);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
      setSteg("kolumner");
    }
  }

  async function importera() {
    if (!fil || !tabell || importerar || attImportera.length === 0 || attImportera.length > MAX_RADER) return;
    const rader = attImportera.map((u) => u.rad!);
    const hallna: Hoppade = {
      utan_bolag: antal.utan_bolag,
      dubbletter: antal.dubblett,
      redan_kund: antal.kund,
      redan_lead: antal.lead,
      sparrade: antal.sparrad
    };
    const info: Importinfo = {
      fil: fil.namn,
      format: fil.innehall.format,
      rader_i_fil: tabell.data.length,
      importerade: rader.length,
      hoppade: hallna,
      anmarkningar: antal.anmarkning,
      kolumner: Object.fromEntries(tabell.rubriker.flatMap((r, i) => (val[i] === "hoppa" ? [] : [[r || `${i + 1}`, val[i]]]))),
      importerad_at: new Date().toISOString()
    };
    setImporterar(true);
    setFel(null);
    const lage = pagaende.current ?? { listId: "", klara: 0, importerade: 0, server: { utan_bolag: 0, dubbletter: 0, redan_kund: 0, redan_lead: 0, sparrade: 0 } };
    setForlopp({ klara: lage.klara, totalt: rader.length });
    try {
      let lista: ImporteradLista | null = null;
      while (lage.klara < rader.length) {
        const svar = await leadsAnrop<Importsvar>("/leads/import", {
          method: "POST",
          body: JSON.stringify({
            kalla,
            rader: rader.slice(lage.klara, lage.klara + SATS),
            ta_med_leads: taMedLeads,
            ...(lage.listId ? { list_id: lage.listId } : { titel: titel.trim() || fil.namn, importinfo: info })
          })
        });
        lista = svar.list;
        lage.listId = svar.list.id;
        lage.klara = Math.min(lage.klara + SATS, rader.length);
        lage.importerade += svar.antal;
        for (const k of Object.keys(lage.server) as (keyof Hoppade)[]) lage.server[k] += svar.hoppade?.[k] ?? 0;
        pagaende.current = lage;
        setForlopp({ klara: lage.klara, totalt: rader.length });
      }
      if (!lista) return;
      const hoppade = { ...hallna };
      for (const k of Object.keys(hoppade) as (keyof Hoppade)[]) hoppade[k] += lage.server[k];
      setKvitto({ lista, importerade: lage.importerade, hoppade, anmarkningar: antal.anmarkning });
      pagaende.current = null;
      setSteg("klart");
      onKlar(lista);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setImporterar(false);
    }
  }

  function borjaOm() {
    setFil(null);
    setKvitto(null);
    setForlopp(null);
    setFel(null);
    pagaende.current = null;
    nollstallGranskning();
    setSteg("fil");
  }

  const nu = STEGORDNING.indexOf(steg);
  const harData = useMemo(() => (tabell ? tabell.rubriker.map((_, i) => tabell.data.some((rad) => (rad[i] ?? "").trim() !== "")) : []), [tabell]);
  const exempel = (kol: number) => {
    const sedda: string[] = [];
    for (const rad of tabell?.data ?? []) {
      const v = (rad[kol] ?? "").replace(/\s+/g, " ").trim();
      if (v && !sedda.includes(v)) sedda.push(v.length > 40 ? `${v.slice(0, 40)}…` : v);
      if (sedda.length === 3) break;
    }
    return sedda.join(" · ");
  };
  const harFlerval = [...FLERVAL].some((f) => val.filter((v) => v === f).length > 1);
  const tomma = harData.filter((d) => !d).length;
  const kanda = val.filter((v, i) => harData[i] && v !== "hoppa").length;
  const utanBolagskolumn = !val.includes("company_name");
  const visarAvtalsslut = val.includes("avtalsslut");
  const tal = (n: number) => n.toLocaleString(locale === "en" ? "en-GB" : "sv-SE");

  const filtrerade = useMemo(
    () =>
      utfall
        .map((u, i) => ({ u, s: statusar[i] }))
        .filter(({ s }) => filter === "alla" || (filter === "importeras" ? importeras(s) : filter === "anmarkning" ? s === "anmarkning" : !importeras(s))),
    [utfall, statusar, filter]
  );

  function utfallstext(u: Radutfall, s: Radstatus): string {
    if (s === "ok") return text(T.importeras);
    if (s === "anmarkning") {
      return u.anmarkningar.map((a) => `${text(VAL_ETIKETT[a.falt as ImportFalt])}: ”${a.varde}” ${text(ANMARKNING[a.kod])}`).join(". ");
    }
    return `${text(T.hoppasOver)}: ${text(HOPPSKAL[s])}`;
  }

  const hoppadeRader = (h: Hoppade): string[] =>
    (
      [
        [h.utan_bolag, { sv: "utan bolagsnamn", en: "without a company name" }],
        [h.dubbletter, h.dubbletter === 1 ? { sv: "dubblett", en: "duplicate" } : { sv: "dubbletter", en: "duplicates" }],
        [h.redan_kund, { sv: "som redan är kunder", en: "that are already customers" }],
        [h.redan_lead, { sv: "som redan är leads", en: "that are already leads" }],
        [h.sparrade, { sv: "som avböjt kontakt", en: "that have declined contact" }]
      ] as [number, Localized][]
    )
      .filter(([n]) => n > 0)
      .map(([n, l]) => `${tal(n)} ${text(l)}`);
  const hoppasNu = hoppadeRader({ utan_bolag: antal.utan_bolag, dubbletter: antal.dubblett, redan_kund: antal.kund, redan_lead: antal.lead, sparrade: antal.sparrad });

  return (
    <div className="space-y-5">
      <ol aria-label={text(T.steg)} className="flex flex-wrap items-center gap-x-5 gap-y-1 border-b border-ink/12 pb-3 text-[0.8125rem]">
        {STEGORDNING.map((s, i) => (
          <li
            key={s}
            aria-current={i === nu ? "step" : undefined}
            className={cn("flex items-center gap-1.5", i === nu ? "font-semibold text-ink" : i < nu ? "text-ink-muted" : "text-ink-subtle")}
          >
            <span aria-hidden className="num tabular-nums">
              {i < nu ? "✓" : i + 1}
            </span>
            {text(STEGNAMN[s])}
          </li>
        ))}
      </ol>

      {/* ------------------------------------------------------------- FIL */}
      {steg === "fil" ? (
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDrar(true);
          }}
          onDragLeave={() => setDrar(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrar(false);
            void lasFil(e.dataTransfer.files?.[0]);
          }}
          className={cn(
            "flex min-h-36 flex-col items-center justify-center gap-2 rounded-card border border-dashed px-4 py-6 text-center transition-colors",
            // Fältet är dolt, så ringen ritas på ytan: samma ring som .focus-ring
            // (accenten mörkad 18 %, 3:1 mot paper).
            "has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:[outline:2px_solid_color-mix(in_oklch,oklch(var(--focus)),black_18%)]",
            laser ? "cursor-progress border-ink/15 bg-paper2/60" : "cursor-pointer",
            !laser && (drar ? "border-ink/50 bg-paper2" : "border-ink/25 bg-paper hover:border-ink/45 hover:bg-paper2/60 active:bg-paper2")
          )}
        >
          <input
            type="file"
            accept={ACCEPT}
            disabled={laser}
            onChange={(e) => {
              void lasFil(e.target.files?.[0]);
              e.target.value = "";
            }}
            className="sr-only"
          />
          <span className="text-[0.9375rem] font-medium text-ink">{laser ? text(T.laser) : text(T.slapp)}</span>
          <span className={cn(meta, "max-w-[62ch]")}>{text(T.format)}</span>
        </label>
      ) : null}

      {/* -------------------------------------------------------- KOLUMNER */}
      {steg === "kolumner" && fil && tabell ? (
        <div className="space-y-5">
          <div>
            <h3 ref={rubrik} tabIndex={-1} className={cn(rubrikPanel, "outline-none")}>
              {fil.namn}
            </h3>
            <p className={cn(meta, "mt-1")}>
              {text({
                sv: `${tal(tabell.data.length)} rader. ${kanda} av ${harData.length - tomma} kolumner kändes igen. Kontrollera valen och ändra där det behövs.`,
                en: `${tal(tabell.data.length)} rows. ${kanda} of ${harData.length - tomma} columns were recognised. Check the choices and change them where needed.`
              })}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <label className={cn(etikett, "flex flex-col gap-1")}>
              {text(T.titel)}
              <input value={titel} onChange={(e) => setTitel(e.target.value)} maxLength={200} className={cn(faltTatt, "w-full")} />
            </label>
            {fil.innehall.blad.length > 1 ? (
              <label className={cn(etikett, "flex flex-col gap-1")}>
                {text(T.blad)}
                <select value={bladIndex} onChange={(e) => valjTabell(fil.innehall, Number(e.target.value), undefined)} className={cn(faltTatt, "w-full")}>
                  {fil.innehall.blad.map((b, i) => (
                    <option key={i} value={i}>
                      {b.namn || `${text(T.blad)} ${i + 1}`} ({tal(b.rader.length)})
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            <label className={cn(etikett, "flex flex-col gap-1")}>
              {text(T.rubrikrad)}
              <select
                value={tabell.rubrikrad}
                onChange={(e) => valjTabell(fil.innehall, bladIndex, Number(e.target.value))}
                className={cn(faltTatt, "w-full")}
              >
                {(blad?.rader ?? []).slice(0, 10).map((rad, i) => (
                  <option key={i} value={i}>
                    {`${text(T.rad)} ${i + 1}: ${rad.filter(Boolean).slice(0, 3).join(", ").slice(0, 60)}`}
                  </option>
                ))}
                <option value={-1}>{text(T.utanRubrik)}</option>
              </select>
            </label>
          </div>

          {tabell.data.length === 0 ? (
            <p role="alert" className="text-[0.9375rem] text-danger">
              {text(T.ingaRader)}
            </p>
          ) : (
            <div>
              <div className="hidden grid-cols-[minmax(0,5fr)_minmax(0,6fr)_minmax(0,5fr)] gap-x-4 border-b border-ink/15 pb-2 sm:grid">
                <span className={etikett}>{text(T.kolumnIFilen)}</span>
                <span className={etikett}>{text({ sv: "Exempel", en: "Examples" })}</span>
                <span className={etikett}>{text(T.blir)}</span>
              </div>
              <Radlista ariaLabel={text(T.kolumnIFilen)} className="border-t-0 sm:border-t-0">
                {tabell.rubriker.map((r, i) =>
                  harData[i] ? (
                    <Rad key={i} className="grid items-center gap-x-4 gap-y-1.5 py-2 sm:grid-cols-[minmax(0,5fr)_minmax(0,6fr)_minmax(0,5fr)]">
                      <span className="min-w-0 break-words text-[0.875rem] font-medium text-ink">{r || `${text(T.kolumn)} ${i + 1}`}</span>
                      <span className={cn(meta, "min-w-0 break-words")}>{exempel(i)}</span>
                      <select
                        aria-label={text({ sv: `${r || `${text(T.kolumn)} ${i + 1}`} blir`, en: `${r || `${text(T.kolumn)} ${i + 1}`} becomes` })}
                        value={val[i] ?? "hoppa"}
                        onChange={(e) => bytVal(i, e.target.value as Kolumnval)}
                        className={cn(faltTatt, "w-full", val[i] === "hoppa" && "text-ink-muted")}
                      >
                        {FALTVAL.map((v) => (
                          <option key={v} value={v}>
                            {text(VAL_ETIKETT[v])}
                          </option>
                        ))}
                        <option value="extra">{text(VAL_ETIKETT.extra)}</option>
                        <option value="hoppa">{text(VAL_ETIKETT.hoppa)}</option>
                      </select>
                    </Rad>
                  ) : null
                )}
              </Radlista>
              <p className={cn(meta, "mt-2 max-w-[75ch]")}>
                {[
                  text(T.extraHjalp),
                  harFlerval ? text(T.flera) : null,
                  tomma > 0 ? text({ sv: `${tomma} tomma kolumner visas inte.`, en: `${tomma} empty columns are not shown.` }) : null,
                  tabell.bortrensade > 0
                    ? text({
                        sv: `${tabell.bortrensade} rader är rapportfot, summor eller upprepade rubriker och räknas inte.`,
                        en: `${tabell.bortrensade} rows are report footers, totals or repeated headers and are not counted.`
                      })
                    : null
                ]
                  .filter(Boolean)
                  .join(" ")}
              </p>
            </div>
          )}

          {utanBolagskolumn && tabell.data.length > 0 ? (
            <p role="alert" className="text-[0.9375rem] text-danger">
              {text(T.ingetBolag)}
            </p>
          ) : null}

          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={() => void granska()} disabled={utanBolagskolumn || summering.importeras === 0} className={btnPrimary}>
              {text({ sv: `Granska ${tal(summering.rader)} rader`, en: `Review ${tal(summering.rader)} rows` })}
            </button>
            <button type="button" onClick={borjaOm} className={btnSecondary}>
              {text(T.bytFil)}
            </button>
          </div>
        </div>
      ) : null}

      {/* --------------------------------------------------------- GRANSKA */}
      {steg === "granska" && fil && tabell ? (
        <div className="space-y-5">
          <div>
            <h3 ref={rubrik} tabIndex={-1} className={cn(rubrikPanel, "outline-none")}>
              {flaggor === null
                ? text(T.granskar)
                : crm
                  ? text({ sv: `${tal(attImportera.length)} kunder sparas`, en: `${tal(attImportera.length)} customers will be saved` })
                  : text({ sv: `${tal(attImportera.length)} av ${tal(summering.rader)} rader importeras`, en: `${tal(attImportera.length)} of ${tal(summering.rader)} rows will be imported` })}
            </h3>
            {flaggor !== null ? (
              <p className={cn(meta, "mt-1 max-w-[75ch]")}>
                {[
                  crm ? null : text({ sv: `${tal(attImportera.filter((u) => u.rad?.contact_email).length)} med e-post`, en: `${tal(attImportera.filter((u) => u.rad?.contact_email).length)} with email` }),
                  crm ? null : text({ sv: `${tal(attImportera.filter((u) => u.rad?.contact_phone).length)} med telefon`, en: `${tal(attImportera.filter((u) => u.rad?.contact_phone).length)} with phone` }),
                  visarAvtalsslut ? text({ sv: `${tal(attImportera.filter((u) => u.rad?.avtalsslut).length)} med avtalsslut`, en: `${tal(attImportera.filter((u) => u.rad?.avtalsslut).length)} with contract end` }) : null,
                  antal.anmarkning > 0
                    ? text({ sv: `${tal(antal.anmarkning)} med värden som lämnas tomma`, en: `${tal(antal.anmarkning)} with values that are left empty` })
                    : null,
                  hoppasNu.length ? text({ sv: `Hoppas över: ${hoppasNu.join(", ")}`, en: `Skipped: ${hoppasNu.join(", ")}` }) : null
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            ) : null}
          </div>

          {flaggor !== null ? (
            <>
              {antalLeads > 0 ? (
                <label className="flex min-h-9 items-center gap-2 text-[0.9375rem] text-ink">
                  <input type="checkbox" checked={taMedLeads} onChange={(e) => setTaMedLeads(e.target.checked)} className="h-4 w-4 accent-ink" />
                  {text(T.taMedLeads)} <span className={cn(meta, "num tabular-nums")}>({tal(antalLeads)})</span>
                </label>
              ) : null}

              <div className={chiplista} role="group" aria-label={text(T.utfall)}>
                {(
                  [
                    ["alla", T.filterAlla, statusar.length],
                    ["importeras", T.filterImporteras, antal.ok + antal.anmarkning],
                    ["anmarkning", T.filterAnmarkning, antal.anmarkning],
                    ["hoppas", T.filterHoppas, statusar.length - antal.ok - antal.anmarkning]
                  ] as [Radfilter, Localized, number][]
                ).map(([id, namn, n]) => (
                  <button
                    key={id}
                    type="button"
                    aria-pressed={filter === id}
                    onClick={() => {
                      setFilter(id);
                      setVisade(VISA_STEG);
                    }}
                    className={cn(chip, filter === id ? chipAktiv : chipInaktiv)}
                  >
                    {text(namn)} <span className="num tabular-nums">{tal(n)}</span>
                  </button>
                ))}
              </div>

              <Tabell
                ariaLabel={text(T.raderna)}
                minBredd={visarAvtalsslut ? 860 : 760}
                kolumner={[
                  { rubrik: text(T.bolag), bredd: "22%" },
                  { rubrik: text(T.kontakt), bredd: "16%" },
                  { rubrik: text(VAL_ETIKETT.contact_email), bredd: "20%" },
                  { rubrik: text(VAL_ETIKETT.contact_phone), bredd: "13%" },
                  ...(visarAvtalsslut ? [{ rubrik: text(VAL_ETIKETT.avtalsslut), bredd: "12%" }] : []),
                  { rubrik: text(T.utfall) }
                ]}
              >
                {filtrerade.slice(0, visade).map(({ u, s }) => (
                  <tr key={u.index} className={cn(tabellRad, !importeras(s) && "text-ink-muted")}>
                    <Cell titel className="break-words align-top">
                      {u.rad?.company_name ?? text({ sv: "(inget bolagsnamn)", en: "(no company name)" })}
                    </Cell>
                    <Cell className="break-words align-top">{[u.rad?.contact_name, u.rad?.contact_role].filter(Boolean).join(", ")}</Cell>
                    <Cell className="break-all align-top">{u.rad?.contact_email ?? ""}</Cell>
                    <Cell className="num break-words align-top">{u.rad?.contact_phone ?? ""}</Cell>
                    {visarAvtalsslut ? <Cell className="num whitespace-nowrap align-top">{u.rad?.avtalsslut ?? ""}</Cell> : null}
                    <Cell className={cn("break-words align-top", s === "anmarkning" && "text-warning")}>{utfallstext(u, s)}</Cell>
                  </tr>
                ))}
              </Tabell>
              {filtrerade.length > visade ? (
                <button type="button" onClick={() => setVisade((n) => n + VISA_STEG * 4)} className={btnSecondary}>
                  {text(T.visaFler)} ({tal(filtrerade.length - visade)})
                </button>
              ) : null}

              {attImportera.length > MAX_RADER ? (
                <p role="alert" className="max-w-[70ch] text-[0.9375rem] text-danger">
                  {text({
                    sv: `En lista rymmer högst ${tal(MAX_RADER)} rader och filen ger ${tal(attImportera.length)}. Dela upp filen, till exempel efter avtalsslut eller ort.`,
                    en: `A list holds at most ${tal(MAX_RADER)} rows and the file gives ${tal(attImportera.length)}. Split the file, for example by contract end or city.`
                  })}
                </p>
              ) : null}

              {forlopp ? (
                <div aria-live={importerar ? "off" : "polite"}>
                  <p className="num text-[0.9375rem] tabular-nums text-ink">
                    {text(T.importerar)} {tal(forlopp.klara)} / {tal(forlopp.totalt)}
                  </p>
                  <div
                    role="progressbar"
                    aria-label={text(T.importerar)}
                    aria-valuemin={0}
                    aria-valuemax={forlopp.totalt}
                    aria-valuenow={forlopp.klara}
                    className="mt-2 h-1.5 overflow-hidden rounded-full bg-ink/10"
                  >
                    <div
                      className="h-full rounded-full bg-ochre transition-[width] duration-200"
                      style={{ width: `${forlopp.totalt ? Math.round((forlopp.klara / forlopp.totalt) * 100) : 0}%` }}
                    />
                  </div>
                </div>
              ) : null}

              {demo ? <p className={meta}>{text(T.demo)}</p> : null}
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => void importera()}
                  disabled={demo || importerar || attImportera.length === 0 || attImportera.length > MAX_RADER}
                  className={btnPrimary}
                >
                  {importerar
                    ? `${text(T.importerar)}…`
                    : pagaende.current
                      ? text(T.forsokIgen)
                      : crm
                        ? text({ sv: `Spara ${tal(attImportera.length)} kunder`, en: `Save ${tal(attImportera.length)} customers` })
                        : text({ sv: `Importera ${tal(attImportera.length)} rader`, en: `Import ${tal(attImportera.length)} rows` })}
                </button>
                {/* En import som börjat går inte att backa ur: raderna som redan
                    ligger i listan kom ur den här kolumnmappningen. */}
                <button type="button" onClick={() => setSteg("kolumner")} disabled={importerar || pagaende.current !== null} className={btnSecondary}>
                  {text(T.tillbaka)}
                </button>
              </div>
            </>
          ) : null}
        </div>
      ) : null}

      {/* ----------------------------------------------------------- KLART */}
      {steg === "klart" && kvitto ? (
        <div className="space-y-4">
          <div role="status">
            <h3 ref={rubrik} tabIndex={-1} className={cn(rubrikPanel, "outline-none")}>
              {crm
                ? text({ sv: `${tal(kvitto.importerade)} kunder sparade i ${kvitto.lista.titel}`, en: `${tal(kvitto.importerade)} customers saved to ${kvitto.lista.titel}` })
                : text({ sv: `${tal(kvitto.importerade)} bolag importerade till ${kvitto.lista.titel}`, en: `${tal(kvitto.importerade)} companies imported to ${kvitto.lista.titel}` })}
            </h3>
            <p className={cn(meta, "mt-1 max-w-[75ch]")}>
              {[
                crm ? text({ sv: "Iris och listorna hoppar över dem från och med nu.", en: "Iris and the lists skip them from now on." }) : null,
                hoppadeRader(kvitto.hoppade).length
                  ? text({ sv: `Hoppades över: ${hoppadeRader(kvitto.hoppade).join(", ")}.`, en: `Skipped: ${hoppadeRader(kvitto.hoppade).join(", ")}.` })
                  : null,
                kvitto.anmarkningar
                  ? text({ sv: `${tal(kvitto.anmarkningar)} rader har värden som lämnats tomma.`, en: `${tal(kvitto.anmarkningar)} rows have values that were left empty.` })
                  : null
              ]
                .filter(Boolean)
                .join(" ")}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            {onOppna && !crm ? (
              <button type="button" onClick={() => onOppna(kvitto.lista)} className={btnPrimary}>
                {text(T.oppna)}
              </button>
            ) : null}
            <button type="button" onClick={borjaOm} className={btnSecondary}>
              {text(T.enTill)}
            </button>
          </div>
        </div>
      ) : null}

      {fel ? (
        <p role="alert" className="max-w-[70ch] break-words text-[0.9375rem] text-danger">
          {fel}
        </p>
      ) : null}
    </div>
  );
}
