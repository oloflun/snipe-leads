"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FileDown, Mail, Newspaper, Search, Upload } from "lucide-react";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import type { EmailStudioData } from "@/lib/data/emails";
import { btnLiten, btnPrimary, btnSecondary } from "@/components/ui";
import { cn } from "@/lib/utils";

/**
 * CRM-demon: kundens egen kundlista in, en Email studio per kund ut.
 *
 * Det här är den omgjorda leadsagenten i demoform. I stället för att agenten
 * letar prospekt laddar företaget upp sin CRM-lista (CSV, varje CRM kan
 * exportera en). Agenten bevakar kunderna i listan, och varje kund har en
 * EGEN, isolerad Email studio som skriver utifrån kundens signaler och det
 * uthyrande företagets produkt och affärsidé.
 *
 * ## Reglerna som gör den ofarlig
 *
 * Sidan lyder under demoroutens hårda regel (se app/demo/[[...slug]]/page.tsx):
 * INGENTING här får sträcka sig efter en session eller databasen. Listan
 * parsas i webbläsaren (`fil.text()`, samma mönster som Kunskapsbas) och
 * sparas bara i localStorage, så en uppladdad riktig kundlista lämnar aldrig
 * besökarens dator. Knapparna postar till /api/email-studio, som för anonyma
 * alltid svarar deterministiskt utan modellanrop (INV-SEC-010-resonemanget i
 * den routen). Signalerna är av samma skäl SIMULERADE och märkta som det;
 * i drift kommer de från källfederationen (sources/jobtech.py, nyheter.py).
 *
 * ## Layouten: master och detalj, inte dragspel
 *
 * Studion öppnades först som en expanderad rad mitt i tabellen. Då trycktes
 * resten av listan en hel skärmhöjd nedåt varje gång en kund öppnades, och
 * listan gick inte att överblicka medan man skrev. Nu står listan till
 * vänster och kundens detaljpanel (signaler + studio) till höger; ett klick
 * byter innehåll i panelen utan att listan flyttar sig.
 *
 * ## Isoleringen
 *
 * Varje öppnad kunds EmailStudioEditor HÅLLS monterad och döljs bara när en
 * annan kund är vald. Utkasten ligger i editorns eget state och kan därför
 * aldrig blandas mellan kunder. Affärsprofilen och den valda signalen skickas
 * däremot LEVANDE: editorns refineContext räknas om från props varje render,
 * så ett signalbyte eller en ändrad affärsidé slår igenom i nästa knapptryck
 * utan att kundens utkast nollställs.
 */

type Kund = {
  id: string;
  foretag: string;
  kontakt: string | null;
  epost: string | null;
  orgnr: string | null;
  ort: string | null;
  webbplats: string | null;
  telefon: string | null;
  /** Fritext ur CRM:et: senaste aktivitet, status, anteckning. Blir en signal. */
  notering: string | null;
};

type Affarsprofil = {
  /** Vad företaget säljer och varför, det Email studio lutar sig mot. */
  affarside: string;
  /**
   * Erbjudandet som KORT NOMINALFRAS ("larm- och brandskydd med fast pris"),
   * inte en hel mening. Simuleringen väver in det mitt i meningar och
   * gemenar första bokstaven; en hel mening med punkt blir styltig text
   * mitt i mejlet (uppmätt i demon 2026-09-11). Speglar business_contexts
   * där product och offer också är skilda fält.
   */
  erbjudande: string;
  /** Önskat nästa steg i mejlen. */
  cta: string;
  /** Företagets webbplats. I drift läser agenten den själv; i demon visas
   *  den som kontext så flödet är komplett. */
  webbplats: string;
};

/** En bevakad händelse hos en kund i listan, med varför den är ett säljläge. */
type Signal = {
  id: string;
  kalla: "CRM-notering" | "Nyhetsbevakning" | "Platsannonser";
  text: string;
  mojlighet: string;
};

type ImportResultat = {
  importerade: number;
  hoppade: number;
  dubbletter: number;
  /** Rader utöver demons tak som aldrig lästes in. */
  kapade: number;
  /** Vilken kolumn som blev vilket fält, så att mappningen går att granska. */
  mappning: Array<[string, string]>;
  ignorerade: string[];
};

/**
 * Demons volymtak. En CSV på 50 000 rader ska inte rendera 50 000 listrader
 * i en yta vars poäng är att visa flödet; taket sägs ärligt i resultatraden.
 */
const MAX_KUNDER = 500;

const STANDARDPROFIL: Affarsprofil = {
  affarside:
    "Demo AB levererar larm- och brandskyddslösningar till små och medelstora " +
    "företag i Västsverige. Affärsidén: när ett bolag flyttar, växer eller " +
    "rekryterar är säkerheten det som skjuts upp, så vi tar hela ansvaret från " +
    "riskgenomgång till installation och service, med fast pris och en " +
    "kontaktperson.",
  erbjudande: "larm- och brandskydd med fast pris och en enda kontaktperson",
  cta: "Vill ni att vi hör av oss med ett konkret förslag?",
  webbplats: "https://demoab.example"
};

/** Fälten en CSV-kolumn kan mappas till, med de rubriker vi känner igen. */
const FALTSYNONYMER: Array<[keyof Omit<Kund, "id">, string[]]> = [
  ["foretag", ["företag", "företagsnamn", "bolag", "bolagsnamn", "kund", "company", "company name", "account", "organisation"]],
  ["kontakt", ["kontakt", "kontaktperson", "namn", "name", "contact", "contact name", "full name"]],
  ["epost", ["e-post", "epost", "email", "e-mail", "mejl", "mail", "e-postadress"]],
  ["orgnr", ["orgnr", "org.nr", "organisationsnummer", "org nr", "orgnummer"]],
  ["ort", ["ort", "stad", "city", "kommun"]],
  ["webbplats", ["webbplats", "hemsida", "website", "webb", "url", "domän"]],
  ["telefon", ["telefon", "tel", "phone", "mobil", "telefonnummer"]],
  ["notering", ["notering", "anteckning", "anteckningar", "notes", "senaste aktivitet", "aktivitet", "signal", "status", "kommentar"]]
];

const LAGRINGSNYCKEL = "snajp-demo-crm";

/**
 * Minimal CSV-parser med citattecken ("" som escape) och radbrytningar inne i
 * fält. Avgränsaren gissas ur rubrikraden: svensk Excel exporterar semikolon,
 * de flesta CRM komma, några tab.
 */
function parseCsv(ratext: string): string[][] {
  const text = ratext.replace(/^﻿/, "");
  const forstaRad = text.slice(0, text.indexOf("\n") === -1 ? text.length : text.indexOf("\n"));
  const kandidater: Array<[string, number]> = [";", ",", "\t"].map((d) => [d, forstaRad.split(d).length - 1]);
  kandidater.sort((a, b) => b[1] - a[1]);
  const avgransare = kandidater[0][1] > 0 ? kandidater[0][0] : ";";

  const rader: string[][] = [];
  let rad: string[] = [];
  let falt = "";
  let iCitat = false;
  for (let i = 0; i < text.length; i++) {
    const tecken = text[i];
    if (iCitat) {
      if (tecken === '"') {
        if (text[i + 1] === '"') {
          falt += '"';
          i++;
        } else {
          iCitat = false;
        }
      } else {
        falt += tecken;
      }
    } else if (tecken === '"') {
      iCitat = true;
    } else if (tecken === avgransare) {
      rad.push(falt);
      falt = "";
    } else if (tecken === "\n" || tecken === "\r") {
      if (tecken === "\r" && text[i + 1] === "\n") i++;
      rad.push(falt);
      falt = "";
      if (rad.some((f) => f.trim() !== "")) rader.push(rad);
      rad = [];
    } else {
      falt += tecken;
    }
  }
  rad.push(falt);
  if (rad.some((f) => f.trim() !== "")) rader.push(rad);
  return rader;
}

function nyttId(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return `kund-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
  }
}

/** Rubrikrad -> per kolumn: vilket kundfält den fyller, eller null. */
function mappaRubriker(rubriker: string[]): Array<keyof Omit<Kund, "id"> | null> {
  const tagna = new Set<string>();
  return rubriker.map((rubrik) => {
    const normal = rubrik.trim().toLowerCase();
    for (const [falt, synonymer] of FALTSYNONYMER) {
      if (tagna.has(falt)) continue;
      if (synonymer.includes(normal)) {
        tagna.add(falt);
        return falt;
      }
    }
    return null;
  });
}

function importeraCsv(
  ratext: string,
  befintliga: Kund[]
): { kunder: Kund[]; resultat: ImportResultat } {
  const rader = parseCsv(ratext);
  if (rader.length < 2) {
    return {
      kunder: [],
      resultat: { importerade: 0, hoppade: 0, dubbletter: 0, kapade: 0, mappning: [], ignorerade: [] }
    };
  }

  const rubriker = rader[0];
  const mappning = mappaRubriker(rubriker);
  const kandaNamn = new Set(befintliga.map((k) => k.foretag.trim().toLowerCase()));

  const kunder: Kund[] = [];
  let hoppade = 0;
  let dubbletter = 0;
  let kapade = 0;

  for (const rad of rader.slice(1)) {
    if (befintliga.length + kunder.length >= MAX_KUNDER) {
      kapade++;
      continue;
    }
    const kund: Kund = {
      id: nyttId(),
      foretag: "",
      kontakt: null,
      epost: null,
      orgnr: null,
      ort: null,
      webbplats: null,
      telefon: null,
      notering: null
    };
    mappning.forEach((falt, index) => {
      if (!falt) return;
      const varde = (rad[index] ?? "").trim();
      if (!varde) return;
      if (falt === "foretag") kund.foretag = varde;
      else kund[falt] = varde;
    });

    if (!kund.foretag) {
      hoppade++;
      continue;
    }
    const nyckel = kund.foretag.trim().toLowerCase();
    if (kandaNamn.has(nyckel)) {
      dubbletter++;
      continue;
    }
    kandaNamn.add(nyckel);
    kunder.push(kund);
  }

  const mappadeKolumner: Array<[string, string]> = [];
  const ignorerade: string[] = [];
  const faltEtiketter: Record<string, string> = {
    foretag: "Företag",
    kontakt: "Kontaktperson",
    epost: "E-post",
    orgnr: "Orgnr",
    ort: "Ort",
    webbplats: "Webbplats",
    telefon: "Telefon",
    notering: "Notering/signal"
  };
  mappning.forEach((falt, index) => {
    const rubrik = rubriker[index]?.trim() || `kolumn ${index + 1}`;
    if (falt) mappadeKolumner.push([faltEtiketter[falt], rubrik]);
    else ignorerade.push(rubrik);
  });

  return {
    kunder,
    resultat: {
      importerade: kunder.length,
      hoppade,
      dubbletter,
      kapade,
      mappning: mappadeKolumner,
      ignorerade
    }
  };
}

/** Förnamnet ur "Elin Nordin": mejl inleds med förnamn, inte fullständigt namn. */
function fornamn(namn: string | null): string | null {
  if (!namn) return null;
  const del = namn.trim().split(/\s+/)[0];
  return del || null;
}

/** Deterministisk siffra ur ett namn, så demon ser likadan ut varje gång. */
function namnhash(text: string): number {
  let summa = 0;
  for (let i = 0; i < text.length; i++) summa += text.charCodeAt(i);
  return summa;
}

/**
 * Kundens bevakade signaler. CRM-noteringen är kundens egen data; den andra
 * signalen är en SIMULERAD nyhets-/annonsbevakning, deterministisk per bolag
 * så att demon är stabil. I drift kommer den raden från källfederationen
 * (Platsbanken via sources/jobtech.py, nyhets-RSS via sources/nyheter.py),
 * och det sägs rakt ut i panelen. Inga påhittade signaler presenteras som
 * verkliga (DESIGN.md, Honest-proof rule).
 */
function signalerFor(kund: Kund): Signal[] {
  const ut: Signal[] = [];
  if (kund.notering) {
    ut.push({
      id: `${kund.id}-crm`,
      kalla: "CRM-notering",
      text: kund.notering,
      mojlighet: "Det ni själva noterat om kunden är den säkraste ingången: utgå från den."
    });
  }

  const hash = namnhash(kund.foretag);
  const iOrt = kund.ort ? ` i ${kund.ort}` : "";
  const mallar: Array<Omit<Signal, "id">> = [
    {
      kalla: "Platsannonser",
      text: `${kund.foretag} söker ${2 + (hash % 3)} nya medarbetare${iOrt}`,
      mojlighet: "Fler anställda betyder nya behov och nya beslut. Hör av er innan behovet är upphandlat."
    },
    {
      kalla: "Nyhetsbevakning",
      text: `${kund.foretag} utökar verksamheten${iOrt}`,
      mojlighet: "Expansion är ett köpfönster: besluten fattas nu, inte i höst."
    },
    {
      kalla: "Nyhetsbevakning",
      text: `${kund.foretag} har tagit ett nytt större uppdrag`,
      mojlighet: "Ett nytt uppdrag ger budget och tidspress. Bra tajming för ett konkret förslag."
    }
  ];
  ut.push({ id: `${kund.id}-nyhet`, ...mallar[hash % mallar.length] });
  return ut;
}

/**
 * Startutkastet när en kunds studio öppnas första gången: kort, signalburen
 * text att arbeta vidare med i stället för ett tomt fält. En mening om
 * avsändaren hämtas ur affärsidén (första meningen); resten av mejlet handlar
 * om kunden, samma regel som Email studios systemprompt ställer.
 */
function startutkast(kund: Kund, profil: Affarsprofil, signal: Signal | null): { subject: string; body: string } {
  const halsning = fornamn(kund.kontakt) ? `Hej ${fornamn(kund.kontakt)},` : "Hej,";
  const forstaMening = profil.affarside.split(/(?<=\.)\s+/)[0]?.trim() || profil.affarside.trim();
  const signalrad = signal
    ? `Jag såg att det händer saker hos er: ${signal.text.charAt(0).toLowerCase()}${signal.text.slice(1)}. `
    : `Vi har följt ${kund.foretag} ett tag. `;

  return {
    // Inte samma formulering som simuleringens ämnesförslag ("X: rätt läge
    // nu?"), annars visas förslagslistan med en dublett av det som redan står.
    subject: signal ? `${kund.foretag} och nästa steg` : `En fråga till ${kund.foretag}`,
    body:
      `${halsning}\n\n` +
      `${signalrad}Det brukar vara läget då nästa steg är värt att titta på.\n\n` +
      `Kort om oss: ${forstaMening}\n\n` +
      `${profil.cta}`
  };
}

/**
 * Kundens fält + vald signal + affärsprofilen som Email studio-kontext.
 * source: "mock" och compact-läget hör ihop: banderollen "Ni har inga utkast
 * ännu" gäller arbetsytan, inte demon (samma val som MejlRuta i
 * LeadslistorView).
 *
 * Erbjudandet skickas som den korta erbjudandefrasen, inte hela affärsidén:
 * demons anonyma väg svarar med simulateAction, som klistrar in `offer`
 * ordagrant mitt i meningar; 800 tecken affärsidé mitt i ett kallmejl
 * (uppmätt i demon 2026-09-11). Frasen bär vinkeln och håller mejlet
 * läsbart; den inloggade LLM-vägen har egna regler för bakgrunden.
 */
function byggStudioData(
  kund: Kund,
  profil: Affarsprofil,
  signal: Signal | null,
  utkast: { subject: string; body: string }
): EmailStudioData {
  const erbjudande = profil.erbjudande.trim().replace(/\.+$/, "") || null;
  return {
    source: "mock",
    businessContext: null,
    email: {
      id: kund.id,
      subject: utkast.subject,
      body: utkast.body,
      variantLength: "kort",
      variantType: "cold",
      status: "draft",
      companyId: null,
      contactId: null,
      companyName: kund.foretag,
      signal: signal?.text ?? kund.notering,
      offer: erbjudande,
      cta: profil.cta,
      contactName: fornamn(kund.kontakt)
    }
  };
}

export function CrmDemo() {
  const [profil, setProfil] = useState<Affarsprofil>(STANDARDPROFIL);
  const [kunder, setKunder] = useState<Kund[]>([]);
  const [sok, setSok] = useState("");
  const [resultat, setResultat] = useState<ImportResultat | null>(null);
  const [importFel, setImportFel] = useState<string | null>(null);
  const [hamtarExempel, setHamtarExempel] = useState(false);
  /** Töm-knappen kräver ett andra klick: den raderar lista OCH alla utkast. */
  const [bekraftaTom, setBekraftaTom] = useState(false);
  /** Kunder vars studio någon gång öppnats: de hålls monterade (isoleringen). */
  const [oppnade, setOppnade] = useState<string[]>([]);
  const [valdKund, setValdKund] = useState<string | null>(null);
  /** Vald signal per kund; osatt = kundens första signal. */
  const [valdaSignaler, setValdaSignaler] = useState<Record<string, string>>({});
  const [laddat, setLaddat] = useState(false);
  const filRef = useRef<HTMLInputElement>(null);
  const detaljRef = useRef<HTMLDivElement>(null);

  // localStorage läses EFTER första renderingen: serverns HTML och klientens
  // första målning måste vara identiska, annars hydreringskrock (känt mönster
  // i den här kodbasen). try/catch för lägen där lagringen inte finns alls.
  useEffect(() => {
    try {
      const sparat = window.localStorage.getItem(LAGRINGSNYCKEL);
      if (sparat) {
        const data = JSON.parse(sparat) as { profil?: Partial<Affarsprofil>; kunder?: Kund[] };
        if (data.profil?.affarside) {
          // En profil sparad innan ett fält fanns fylls på med standardvärdet
          // i stället för att rendera ett tomt fält.
          setProfil({ ...STANDARDPROFIL, ...data.profil });
        }
        if (Array.isArray(data.kunder)) setKunder(data.kunder);
      }
    } catch {
      // En trasig eller blockerad lagring lämnar demon på standardläget.
    }
    setLaddat(true);
  }, []);

  useEffect(() => {
    if (!laddat) return;
    try {
      window.localStorage.setItem(LAGRINGSNYCKEL, JSON.stringify({ profil, kunder }));
    } catch {
      // Full eller blockerad lagring: demon fungerar ändå, bara utan minne.
    }
  }, [laddat, profil, kunder]);

  // Startutkasten låses per kund NÄR studion öppnas, så en senare profil-
  // eller signaländring inte skriver över text kunden redan arbetat med.
  // Kontexten (signal/offer/cta) är däremot levande: den räknas från props i
  // varje render av editorn.
  const utkastRef = useRef(new Map<string, { subject: string; body: string }>());

  const taEmotCsv = useCallback(
    (ratext: string) => {
      setImportFel(null);
      setBekraftaTom(false);
      const { kunder: nya, resultat: res } = importeraCsv(ratext, kunder);
      setResultat(res);
      if (res.importerade === 0 && res.hoppade === 0 && res.dubbletter === 0 && res.kapade === 0) {
        setImportFel("Filen gick inte att läsa som en kundlista. Den behöver en rubrikrad och minst en rad med ett företagsnamn.");
        return;
      }
      if (nya.length > 0) setKunder((forr) => [...forr, ...nya]);
    },
    [kunder]
  );

  const valjFil = useCallback(
    async (fil: File | undefined) => {
      if (!fil) return;
      try {
        taEmotCsv(await fil.text());
      } catch {
        setImportFel("Filen gick inte att läsa. Prova att exportera om den som CSV.");
      } finally {
        if (filRef.current) filRef.current.value = "";
      }
    },
    [taEmotCsv]
  );

  const laddaExempel = useCallback(async () => {
    if (hamtarExempel) return;
    setImportFel(null);
    setHamtarExempel(true);
    try {
      const svar = await fetch("/demo/crm-exempel.csv");
      if (!svar.ok) throw new Error();
      taEmotCsv(await svar.text());
    } catch {
      setImportFel("Exempellistan gick inte att hämta just nu. Prova igen om en stund.");
    } finally {
      setHamtarExempel(false);
    }
  }, [hamtarExempel, taEmotCsv]);

  const valjKund = useCallback((id: string) => {
    setOppnade((forr) => (forr.includes(id) ? forr : [...forr, id]));
    setValdKund(id);
    // På en skärm utan plats för två kolumner ligger panelen under listan;
    // utan scrollen ser ett klick i listans slut ut att inte göra någonting.
    if (typeof window !== "undefined" && window.matchMedia("(max-width: 1023px)").matches) {
      requestAnimationFrame(() => detaljRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
    }
  }, []);

  const tomLista = useCallback(() => {
    if (!bekraftaTom) {
      setBekraftaTom(true);
      return;
    }
    setKunder([]);
    setOppnade([]);
    setValdKund(null);
    setValdaSignaler({});
    setResultat(null);
    setBekraftaTom(false);
    utkastRef.current.clear();
  }, [bekraftaTom]);

  const filtrerade = useMemo(() => {
    const term = sok.trim().toLowerCase();
    if (!term) return kunder;
    return kunder.filter((k) =>
      [k.foretag, k.kontakt, k.epost, k.ort, k.notering]
        .filter(Boolean)
        .some((falt) => (falt as string).toLowerCase().includes(term))
    );
  }, [kunder, sok]);

  const aktivKund = useMemo(() => kunder.find((k) => k.id === valdKund) ?? null, [kunder, valdKund]);

  const signalFor = useCallback(
    (kund: Kund): Signal | null => {
      const signaler = signalerFor(kund);
      if (signaler.length === 0) return null;
      const valt = valdaSignaler[kund.id];
      return signaler.find((s) => s.id === valt) ?? signaler[0];
    },
    [valdaSignaler]
  );

  const utkastFor = useCallback(
    (kund: Kund) => {
      const fanns = utkastRef.current.get(kund.id);
      if (fanns) return fanns;
      const nytt = startutkast(kund, profil, signalFor(kund));
      utkastRef.current.set(kund.id, nytt);
      return nytt;
    },
    [profil, signalFor]
  );

  return (
    <div className="space-y-8">
      {/* ————— Affärsprofilen: det agenten läser om ER ————— */}
      <section className="rounded-card border border-ink/12 bg-paper p-5 md:p-6">
        <p className="kicker text-mineral">Er produkt och affärsidé</p>
        <p className="mt-2 max-w-[70ch] text-[0.9375rem] leading-[1.6] text-ink/65">
          Det här läser Email studio inför varje omskrivning, som bakgrund för ton och vinkel,
          aldrig som text att klistra in i mejlet. I drift läser agenten även er webbplats själv;
          i demon står texten här för den. Ändra och se hur förslagen följer med.
        </p>
        <label htmlFor="crm-affarside" className="mt-5 block text-[0.8125rem] font-medium text-ink/45">
          Vad ni säljer och varför
        </label>
        <textarea
          id="crm-affarside"
          maxLength={800}
          value={profil.affarside}
          onChange={(e) => setProfil((forr) => ({ ...forr, affarside: e.target.value }))}
          className="focus-ring mt-2 min-h-[110px] w-full resize-y rounded-input border border-ink/12 bg-paper px-4 py-3 text-[0.9375rem] leading-6 outline-none transition-colors focus:border-ink/30"
        />
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div>
            <label htmlFor="crm-erbjudande" className="block text-[0.8125rem] font-medium text-ink/45">
              Erbjudandet, i en kort fras
            </label>
            <input
              id="crm-erbjudande"
              maxLength={160}
              value={profil.erbjudande}
              onChange={(e) => setProfil((forr) => ({ ...forr, erbjudande: e.target.value }))}
              className="focus-ring mt-2 w-full rounded-input border border-ink/12 bg-paper px-4 py-3 text-[0.9375rem] outline-none transition-colors focus:border-ink/30"
            />
          </div>
          <div>
            <label htmlFor="crm-webbplats" className="block text-[0.8125rem] font-medium text-ink/45">
              Er webbplats
            </label>
            <input
              id="crm-webbplats"
              maxLength={200}
              inputMode="url"
              value={profil.webbplats}
              onChange={(e) => setProfil((forr) => ({ ...forr, webbplats: e.target.value }))}
              className="focus-ring mt-2 w-full rounded-input border border-ink/12 bg-paper px-4 py-3 text-[0.9375rem] outline-none transition-colors focus:border-ink/30"
            />
          </div>
        </div>
        <label htmlFor="crm-cta" className="mt-4 block text-[0.8125rem] font-medium text-ink/45">
          Önskat nästa steg (CTA)
        </label>
        <input
          id="crm-cta"
          maxLength={200}
          value={profil.cta}
          onChange={(e) => setProfil((forr) => ({ ...forr, cta: e.target.value }))}
          className="focus-ring mt-2 w-full rounded-input border border-ink/12 bg-paper px-4 py-3 text-[0.9375rem] outline-none transition-colors focus:border-ink/30"
        />
      </section>

      {/* ————— Importen: CRM-listan in ————— */}
      <section className="rounded-card border border-ink/12 bg-paper p-5 md:p-6">
        <p className="kicker text-mineral">Ladda upp er CRM-lista</p>
        <p className="mt-2 max-w-[70ch] text-[0.9375rem] leading-[1.6] text-ink/65">
          Exportera kundlistan som CSV ur ert CRM (HubSpot, Pipedrive, Lime och Excel kan alla) och
          släpp den här. Kolumnerna känns igen automatiskt. Listan stannar i din webbläsare och
          laddas aldrig upp till någon server i demon.
        </p>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <input
            ref={filRef}
            type="file"
            accept=".csv,text/csv,.txt"
            className="hidden"
            onChange={(e) => void valjFil(e.target.files?.[0])}
          />
          <button type="button" onClick={() => filRef.current?.click()} className={btnPrimary}>
            <Upload className="h-4 w-4" aria-hidden />
            Välj CSV-fil
          </button>
          <button
            type="button"
            disabled={hamtarExempel}
            onClick={() => void laddaExempel()}
            className={cn(btnSecondary, "disabled:cursor-wait")}
          >
            <FileDown className="h-4 w-4" aria-hidden />
            {hamtarExempel ? "Hämtar…" : "Ladda in exempellistan"}
          </button>
          {kunder.length > 0 ? (
            <button
              type="button"
              onClick={tomLista}
              onBlur={() => setBekraftaTom(false)}
              className={cn(btnSecondary, btnLiten, bekraftaTom && "!bg-danger/10 !text-danger")}
            >
              {bekraftaTom ? "Klicka igen: listan och alla utkast raderas" : "Töm listan"}
            </button>
          ) : null}
        </div>

        {importFel ? (
          <p role="alert" className="mt-4 rounded-input bg-danger/10 px-4 py-3 text-[0.875rem] text-danger">
            {importFel}
          </p>
        ) : null}

        {resultat && !importFel ? (
          <div className="mt-4 rounded-input bg-paper2/70 px-4 py-3 text-[0.875rem] leading-6 text-ink/70">
            <p role="status">
              {resultat.importerade === 1 ? "1 kund importerad" : `${resultat.importerade} kunder importerade`}
              {resultat.dubbletter > 0
                ? `, ${resultat.dubbletter === 1 ? "1 dubblett" : `${resultat.dubbletter} dubbletter`} hoppades över`
                : ""}
              {resultat.hoppade > 0
                ? `, ${resultat.hoppade === 1 ? "1 rad" : `${resultat.hoppade} rader`} utan företagsnamn hoppades över`
                : ""}
              {resultat.kapade > 0
                ? `, ${resultat.kapade} rader över demons tak på ${MAX_KUNDER} kunder lästes inte in`
                : ""}
              .
            </p>
            {resultat.mappning.length > 0 ? (
              <p className="mt-1 text-ink/55">
                Kolumner: {resultat.mappning.map(([falt, rubrik]) => `${falt} ← ”${rubrik}”`).join(" · ")}
                {resultat.ignorerade.length > 0 ? ` · Ignorerade: ${resultat.ignorerade.join(", ")}` : ""}
              </p>
            ) : null}
          </div>
        ) : null}
      </section>

      {/* ————— Kundlistan + detaljpanelen: master och detalj ————— */}
      <section className="rounded-card border border-ink/12 bg-paper p-5 md:p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="kicker text-mineral">Kundlistan</p>
            <p className="mt-1 max-w-[60ch] text-[0.9375rem] text-ink/65">
              {kunder.length === 0
                ? "Ingen lista inläst ännu. Välj en CSV-fil ovan, eller börja med exempellistan."
                : `${kunder.length === 1 ? "1 kund" : `${kunder.length} kunder`}. Klicka på en kund: signalerna och en egen Email studio öppnas bredvid listan.`}
            </p>
          </div>
          {kunder.length > 0 ? (
            <label className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink/35" aria-hidden />
              <span className="sr-only">Sök i kundlistan</span>
              <input
                value={sok}
                onChange={(e) => setSok(e.target.value)}
                placeholder="Sök företag, kontakt, ort …"
                className="focus-ring w-64 rounded-input border border-ink/12 bg-paper py-2 pl-9 pr-3 text-[0.875rem] outline-none transition-colors focus:border-ink/30"
              />
            </label>
          ) : null}
        </div>

        {kunder.length > 0 ? (
          <div className="mt-5 grid gap-6 lg:grid-cols-12">
            {/* Listan: ett klick byter innehåll i panelen, listan flyttar sig inte. */}
            <ul className="lg:col-span-5 divide-y divide-ink/8 border-y border-ink/8" aria-label="Kunder">
              {filtrerade.map((kund) => {
                const vald = kund.id === valdKund;
                return (
                  <li key={kund.id}>
                    <button
                      type="button"
                      onClick={() => valjKund(kund.id)}
                      aria-current={vald ? "true" : undefined}
                      className={cn(
                        "focus-ring block w-full px-3 py-3 text-left transition-colors",
                        vald ? "bg-ochre/10" : "hover:bg-paper2/60"
                      )}
                    >
                      <span className="flex items-baseline justify-between gap-3">
                        <span className="truncate text-[0.9375rem] font-medium text-ink">{kund.foretag}</span>
                        {kund.ort ? <span className="shrink-0 text-[0.8125rem] text-ink/45">{kund.ort}</span> : null}
                      </span>
                      {kund.kontakt || kund.epost ? (
                        <span className="mt-0.5 block truncate text-[0.8125rem] text-ink/55">
                          {[kund.kontakt, kund.epost].filter(Boolean).join(" · ")}
                        </span>
                      ) : null}
                      {kund.notering ? (
                        <span className="mt-0.5 block truncate text-[0.8125rem] text-ink/45">{kund.notering}</span>
                      ) : null}
                    </button>
                  </li>
                );
              })}
              {filtrerade.length === 0 ? (
                <li className="px-3 py-6 text-[0.9375rem] text-ink/55">Inga kunder matchar sökningen.</li>
              ) : null}
            </ul>

            {/* Detaljpanelen: signaler + kundens egen studio. */}
            <div ref={detaljRef} className="lg:col-span-7 min-w-0 scroll-mt-6">
              {aktivKund ? (
                <KundDetalj
                  kund={aktivKund}
                  profil={profil}
                  signal={signalFor(aktivKund)}
                  onValjSignal={(signalId) =>
                    setValdaSignaler((forr) => ({ ...forr, [aktivKund.id]: signalId }))
                  }
                />
              ) : (
                <div className="rounded-card border border-ink/12 bg-paper2/40 p-6">
                  <p className="text-[0.9375rem] leading-[1.6] text-ink/60">
                    Välj en kund i listan. Här visas kundens signaler och en Email studio som är
                    isolerad till just den kunden.
                  </p>
                </div>
              )}

              {/* Varje öppnad kunds studio hålls monterad och döljs bara:
                  utkastet lever i editorns eget state och överlever kundbyten.
                  [hidden] i stället för display-toggling i stil. */}
              {kunder
                .filter((kund) => oppnade.includes(kund.id))
                .map((kund) => (
                  <div key={kund.id} hidden={kund.id !== valdKund} className="mt-4">
                    <div className="rounded-card border border-ink/15 bg-paper2/50 p-4 md:p-5">
                      <p className="kicker text-mineral">
                        Email studio · {kund.foretag}
                        {kund.epost ? ` · ${kund.epost}` : ""}
                      </p>
                      <div className="mt-4">
                        <EmailStudioEditor
                          data={byggStudioData(kund, profil, signalFor(kund), utkastFor(kund))}
                          compact
                        />
                      </div>
                      <p className="mt-4 max-w-[70ch] text-[0.8125rem] leading-6 text-ink/50">
                        Studion är isolerad till {kund.foretag}: text och förslag här påverkar aldrig
                        någon annan kund i listan. Inget skickas från demon.
                      </p>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}

/** Kundhuvudet och signalvalet ovanför studion i detaljpanelen. */
function KundDetalj({
  kund,
  profil,
  signal,
  onValjSignal
}: Readonly<{
  kund: Kund;
  profil: Affarsprofil;
  signal: Signal | null;
  onValjSignal: (signalId: string) => void;
}>) {
  const signaler = signalerFor(kund);
  const fakta = [
    kund.kontakt,
    kund.epost,
    kund.telefon,
    kund.ort,
    kund.webbplats,
    kund.orgnr ? `Orgnr ${kund.orgnr}` : null
  ].filter(Boolean) as string[];

  return (
    <div className="rounded-card border border-ink/12 bg-paper p-4 md:p-5">
      <h2 className="text-[1.125rem] font-semibold tracking-[-0.01em] text-ink">{kund.foretag}</h2>
      {fakta.length > 0 ? (
        <p className="mt-1 text-[0.875rem] leading-6 text-ink/55">{fakta.join(" · ")}</p>
      ) : null}

      <div className="hrule mt-4 pt-4">
        <p className="flex items-center gap-2 text-[0.8125rem] font-medium text-ink/45">
          <Newspaper className="h-4 w-4 text-ink/40" aria-hidden />
          Signaler och affärsmöjligheter
        </p>
        <ul className="mt-3 space-y-2">
          {signaler.map((s) => {
            const anvands = signal?.id === s.id;
            return (
              <li key={s.id} className={cn("rounded-input border p-3", anvands ? "border-ochre/60 bg-ochre/10" : "border-ink/10 bg-paper2/40")}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-[0.75rem] font-medium uppercase tracking-wide text-ink/40">{s.kalla}</p>
                    <p className="mt-0.5 text-[0.9375rem] leading-6 text-ink">{s.text}</p>
                    <p className="mt-1 text-[0.8125rem] leading-6 text-ink/55">{s.mojlighet}</p>
                  </div>
                  {anvands ? (
                    <span className="shrink-0 text-[0.8125rem] font-medium text-ochre">Används i mejlet</span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => onValjSignal(s.id)}
                      className={cn(btnSecondary, btnLiten, "shrink-0 whitespace-nowrap")}
                    >
                      <Mail className="h-4 w-4" aria-hidden />
                      Skriv på signalen
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
        <p className="mt-3 max-w-[70ch] text-[0.8125rem] leading-6 text-ink/45">
          Nyhets- och annonsraden är simulerad i demon. I drift bevakar agenten Platsbanken och
          nyhetskällor per kund i listan, och läser er webbplats ({profil.webbplats || "ingen angiven"})
          för att veta vad mejlen ska utgå från. Signalbytet används av studions knappar vid nästa
          körning; texten du redan skrivit rörs inte.
        </p>
      </div>
    </div>
  );
}
