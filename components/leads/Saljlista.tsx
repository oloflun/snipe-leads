"use client";

import { Download, Mail, Phone, Plus, Search, Trash2 } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useId, useMemo, useRef, useState } from "react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { hamtaSaljlista, laggTillSaljrad, sattSaljstatus, taBortSaljrad, uppdateraSaljrad } from "@/lib/actions/saljlista";
import { mejlaOss } from "@/components/marketing/copy";
import { SALJLISTA_EXEMPEL } from "@/lib/demo/saljlista-exempel";
import {
  SALJLISTA_FALT,
  byggSaljCsv,
  dagarSedan,
  dubblettnycklar,
  idagLokalt,
  normaliseraFalt,
  telefonlank,
  type Saljfalt,
  type Saljfel,
  type Saljrad,
  type Saljstatus,
  type Saljsvar
} from "@/lib/leads/saljlista";
import {
  Badge,
  btnLiten,
  btnPrimary,
  btnSecondary,
  Cell,
  chip,
  chipAktiv,
  chipInaktiv,
  chiplista,
  etikett,
  faltDiskret,
  faltTatt,
  meta,
  SkeletonRows,
  Tabell,
  tabellRad,
  Tomt
} from "@/components/ui";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Säljlistan (Sebbes beställning 2026-10-06): CRM:et över bolagen man ringt.
 * Kolumnerna är kalkylarkets — Företagsnamn, Organisationsnummer,
 * Kontaktperson, Kontaktnummer, Kontaktmail, Senast kontaktad,
 * Anteckningar/Info.
 *
 * Ingår i tillägget Leadslistor, som vi slår på när kunden hört av sig; en
 * lista per arbetsyta (tabellen `saljlista`, migration 100 + 103). Snajps egen
 * arbetsyta har tillägget och använder listan för vår egen utringning. Står
 * överst i Leads › Listor; läsrollen ser listan men kan inte ändra den.
 *
 * Varje cell sparas när fältet lämnas (eller på Enter); Esc ångrar. `api` går
 * att byta ut så att ytan kan provas utan databas.
 */

export type SaljlistaApi = {
  hamta: () => Promise<Saljsvar<Saljrad[]>>;
  laggTill: (falt: Partial<Record<Saljfalt, string | null>>) => Promise<Saljsvar<Saljrad>>;
  uppdatera: (id: string, namn: Saljfalt, varde: string | null) => Promise<Saljsvar<Saljrad>>;
  sattStatus: (id: string, status: Saljstatus) => Promise<Saljsvar<Saljrad>>;
  taBort: (id: string) => Promise<Saljsvar<{ id: string }>>;
};

const SERVERAPI: SaljlistaApi = {
  hamta: hamtaSaljlista,
  laggTill: laggTillSaljrad,
  uppdatera: uppdateraSaljrad,
  sattStatus: sattSaljstatus,
  taBort: taBortSaljrad
};

const T = {
  rubrik: { sv: "Säljlista", en: "Sales list" },
  ingarTillagg: { sv: "Ingår i Leadslistor", en: "Included in Lead lists" },
  lasbehorighet: { sv: "Läsbehörighet", en: "Read-only" },
  laggTill: { sv: "Lägg till företag", en: "Add company" },
  exportera: { sv: "Exportera CSV", en: "Export CSV" },
  sok: { sv: "Sök företag, person, nummer eller anteckning", en: "Search company, person, number or note" },
  sortera: { sv: "Sortera", en: "Sort" },
  sortNya: { sv: "Senast tillagda", en: "Recently added" },
  sortKontakt: { sv: "Senast kontaktad", en: "Last contacted" },
  sortLangst: { sv: "Längst sedan kontakt", en: "Longest since contact" },
  sortNamn: { sv: "Företagsnamn A–Ö", en: "Company name A–Z" },
  filtrera: { sv: "Filtrera på kontakt", en: "Filter by contact" },
  filterAlla: { sv: "Alla", en: "All" },
  filterAldrig: { sv: "Ej kontaktade", en: "Not contacted" },
  filterVecka: { sv: "Kontaktade senaste 7 dagarna", en: "Contacted in the last 7 days" },
  filterGammal: { sv: "Över 30 dagar sedan", en: "Over 30 days ago" },
  foretagsnamn: { sv: "Företagsnamn", en: "Company name" },
  orgnr: { sv: "Organisationsnummer", en: "Company reg. no." },
  orgnrKort: { sv: "Org.nr", en: "Reg. no." },
  kontaktperson: { sv: "Kontaktperson", en: "Contact person" },
  kontaktnummer: { sv: "Kontaktnummer", en: "Phone number" },
  kontaktmail: { sv: "Kontaktmail", en: "Contact email" },
  senastKontaktad: { sv: "Senast kontaktad", en: "Last contacted" },
  anteckningar: { sv: "Anteckningar/Info", en: "Notes/Info" },
  atgarder: { sv: "Åtgärder", en: "Actions" },
  status: { sv: "Status", en: "Status" },
  statusIngen: { sv: "Ingen status", en: "No status" },
  statusSalt: { sv: "Sålt", en: "Sold" },
  statusSignering: { sv: "Väntar på signering", en: "Awaiting signing" },
  statusNej: { sv: "Nej", en: "No" },
  statusEjSvar: { sv: "Ej svar", en: "No answer" },
  valjStatus: { sv: "Sätt status för", en: "Set status for" },
  demoMarke: { sv: "Demo", en: "Demo" },
  demoNotis: { sv: "Demon är ifylld med påhittade bolag. Ändringarna sparas inte.", en: "The demo is filled with fictional companies. Changes are not saved." },
  tillval: { sv: "Tillval", en: "Add-on" },
  utforska: { sv: "Utforska i demo", en: "Explore in demo" },
  stangDemo: { sv: "Stäng demon", en: "Close the demo" },
  horAvDig: { sv: "Hör av dig om leadslistor", en: "Ask us about lead lists" },
  utforskaText: {
    sv: "Håll ordning på bolagen ni ringt: kontaktuppgifter, senaste samtalet och statusfärger för sålt, väntar på signering, nej och ej svar. Säljlistan ingår i tillägget Leadslistor. Hör av dig så slår vi på det.",
    en: "Keep track of the companies you have called: contact details, the latest call and status colours for sold, awaiting signing, no and no answer. The sales list is included in the Lead lists add-on. Get in touch and we will turn it on."
  },
  idag: { sv: "Idag", en: "Today" },
  satIdag: { sv: "Sätt senast kontaktad till idag", en: "Set last contacted to today" },
  igar: { sv: "Igår", en: "Yesterday" },
  aldrig: { sv: "Ej kontaktad", en: "Not contacted" },
  ring: { sv: "Ring", en: "Call" },
  mejla: { sv: "Mejla", en: "Email" },
  taBort: { sv: "Ta bort", en: "Delete" },
  nyttForetag: { sv: "Nytt företag", en: "New company" },
  spara: { sv: "Spara företag", en: "Save company" },
  sparaAnda: { sv: "Lägg till ändå", en: "Add anyway" },
  sparar: { sv: "Sparar…", en: "Saving…" },
  sparat: { sv: "Alla ändringar sparade", en: "All changes saved" },
  avbryt: { sv: "Avbryt", en: "Cancel" },
  laddarFel: { sv: "Säljlistan kunde inte hämtas.", en: "The sales list could not be loaded." },
  forsokIgen: { sv: "Försök igen", en: "Try again" },
  tomt: {
    sv: "Inga företag i listan än. Lägg till det första bolaget du ringer.",
    en: "No companies in the list yet. Add the first company you call."
  },
  ingaTraffar: { sv: "Inga företag matchar sökningen eller filtret.", en: "No companies match the search or filter." },
  platsNamn: { sv: "t.ex. Nordform AB", en: "e.g. Nordform AB" },
  platsOrgnr: { sv: "556677-8899", en: "556677-8899" },
  platsPerson: { sv: "Förnamn Efternamn", en: "First Last" },
  platsNummer: { sv: "070-123 45 67", en: "070-123 45 67" },
  platsMail: { sv: "namn@bolag.se", en: "name@company.com" },
  platsAnteckning: { sv: "Vad sades, nästa steg, återkom när…", en: "What was said, next step, call back when…" }
} satisfies Record<string, Localized>;

const FEL: Record<Saljfel, Localized> = {
  ej_inloggad: { sv: "Du är inte inloggad. Logga in igen och ladda om sidan.", en: "You are not signed in. Sign in again and reload the page." },
  fel_vy: { sv: "Säljlistan går bara att använda i din egen arbetsyta.", en: "The sales list can only be used in your own workspace." },
  saknar_tillagg: {
    sv: "Säljlistan ingår i tillägget Leadslistor. Hör av dig till oss så slår vi på det.",
    en: "The sales list is included in the Lead lists add-on. Get in touch and we will turn it on."
  },
  las_roll: { sv: "Ditt konto har läsbehörighet och kan inte ändra säljlistan.", en: "Your account is read-only and cannot change the sales list." },
  migration_saknas: {
    sv: "Säljlistans tabell finns inte i den här miljön än (migration 100). Kör migrationerna och ladda om sidan.",
    en: "The sales list table does not exist in this environment yet (migration 100). Run the migrations and reload the page."
  },
  databasfel: { sv: "Databasen svarade med ett fel. Försök igen.", en: "The database returned an error. Please try again." },
  namn_saknas: { sv: "Företagsnamn måste fyllas i.", en: "Company name is required." },
  okant_falt: { sv: "Okänt fält.", en: "Unknown field." },
  ogiltig_mejl: { sv: "Mejladressen ser inte giltig ut.", en: "The email address does not look valid." },
  ogiltigt_datum: { sv: "Datumet är ogiltigt. Använd ÅÅÅÅ-MM-DD.", en: "The date is invalid. Use YYYY-MM-DD." },
  for_lang: { sv: "Texten är för lång för fältet.", en: "The text is too long for the field." },
  finns_inte: { sv: "Företaget finns inte längre i listan. Ladda om sidan.", en: "The company is no longer in the list. Reload the page." }
};

type Filter = "alla" | "aldrig" | "vecka" | "gammal";
type Sortering = "nya" | "kontakt" | "langst" | "namn";

const FALTETIKETT: Record<Saljfalt, Localized> = {
  foretagsnamn: T.foretagsnamn,
  orgnr: T.orgnr,
  kontaktperson: T.kontaktperson,
  kontaktnummer: T.kontaktnummer,
  kontaktmail: T.kontaktmail,
  senast_kontaktad: T.senastKontaktad,
  anteckningar: T.anteckningar
};

/**
 * Statusfärgerna: hur samtalet gick. `prick` är bollen i förklaringsrutan och
 * menyn, `yta` radens ton, `kant` kortets vänsterkant. Tonerna är låga nog
 * att texten behåller sin kontrast i både ljust och mörkt läge.
 */
const STATUSVAL: {
  kod: Exclude<Saljstatus, "">;
  etikett: Localized;
  prick: string;
  yta: string;
  kant: string;
}[] = [
  { kod: "salt", etikett: T.statusSalt, prick: "bg-moss", yta: "bg-moss/[0.09]", kant: "border-l-moss" },
  { kod: "signering", etikett: T.statusSignering, prick: "bg-chart-blue", yta: "bg-chart-blue/[0.09]", kant: "border-l-chart-blue" },
  { kod: "nej", etikett: T.statusNej, prick: "bg-danger", yta: "bg-danger/[0.08]", kant: "border-l-danger" },
  { kod: "ej_svar", etikett: T.statusEjSvar, prick: "bg-ochre", yta: "bg-ochre/[0.16]", kant: "border-l-ochre" }
];

function statusInfo(status: Saljstatus) {
  return STATUSVAL.find((val) => val.kod === status) ?? null;
}

const PLATSHALLARE: Partial<Record<Saljfalt, Localized>> = {
  foretagsnamn: T.platsNamn,
  orgnr: T.platsOrgnr,
  kontaktperson: T.platsPerson,
  kontaktnummer: T.platsNummer,
  kontaktmail: T.platsMail,
  anteckningar: T.platsAnteckning
};

function tomtUtkast(): Record<Saljfalt, string> {
  return {
    foretagsnamn: "",
    orgnr: "",
    kontaktperson: "",
    kontaktnummer: "",
    kontaktmail: "",
    senast_kontaktad: "",
    anteckningar: ""
  };
}

function relativ(datum: string | null, idag: string, text: (v: Localized) => string): string | null {
  if (!datum) return null;
  const dagar = dagarSedan(datum, idag);
  if (dagar === null) return null;
  if (dagar === 0) return text(T.idag);
  if (dagar === 1) return text(T.igar);
  if (dagar < 0) return text({ sv: `om ${-dagar} dagar`, en: `in ${-dagar} days` });
  return text({ sv: `för ${dagar} dagar sedan`, en: `${dagar} days ago` });
}

/** Läsrollen ser listan men kan inte ändra den. */
const LasLage = createContext(false);

/**
 * Säljlistan med sin grind: arbetsytan har tillägget Leadslistor (som slås på
 * av oss när kunden hört av sig), och det är den egna vyn — aldrig demovyn
 * eller ett kundbesök, där skrivningarna hade hamnat i adminens egen
 * arbetsyta. Samma villkor står i server actions (lib/actions/saljlista.ts).
 */
export function SaljlistaSektion({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { addons, vy, impersonation, isDemo, arLasare } = useDashboard();
  // Demoytorna (marknadsdemon och demovyn) visar utforskaren med exempelbolag,
  // öppen direkt — det är den som säljer tillvalet.
  if (demo || isDemo || vy === "demo") return <SaljlistaUtforska startOppen />;
  // Kundbesök: datan hade hämtats ur adminens EGEN arbetsyta medan skärmen
  // visar kundens — därför ingenting alls.
  if (impersonation || vy !== "admin") return null;
  if (!addons.includes("leadlists")) return <SaljlistaUtforska />;
  return <Saljlista las={arLasare} />;
}

export function Saljlista({
  api = SERVERAPI,
  las = false,
  demo = false
}: Readonly<{ api?: SaljlistaApi; las?: boolean; demo?: boolean }>) {
  return (
    <LasLage.Provider value={las}>
      <SaljlistaYta api={api} demo={demo} />
    </LasLage.Provider>
  );
}

function SaljlistaYta({ api, demo }: Readonly<{ api: SaljlistaApi; demo: boolean }>) {
  const { text } = useLocale();
  const las = useContext(LasLage);
  const [rader, setRader] = useState<Saljrad[] | null>(null);
  const [laddFel, setLaddFel] = useState<string | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [pagaende, setPagaende] = useState(0);
  const [harSparat, setHarSparat] = useState(false);
  const [sok, setSok] = useState("");
  const [filter, setFilter] = useState<Filter>("alla");
  const [sortering, setSortering] = useState<Sortering>("nya");
  const [formOppen, setFormOppen] = useState(false);
  const [idag, setIdag] = useState("");

  useEffect(() => setIdag(idagLokalt()), []);

  const felText = useCallback(
    (svar: { fel: Saljfel; detalj?: string }) => text(FEL[svar.fel]),
    [text]
  );

  const hamta = useCallback(async () => {
    setLaddFel(null);
    try {
      const svar = await api.hamta();
      if (svar.ok) setRader(svar.data);
      else setLaddFel(felText(svar));
    } catch {
      setLaddFel(text(T.laddarFel));
    }
  }, [api, felText, text]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  /** Kör en skrivning med sparstatus; returnerar svaret eller null vid nätverksfel. */
  const skriv = useCallback(
    async <D,>(gor: () => Promise<Saljsvar<D>>): Promise<Saljsvar<D> | null> => {
      setPagaende((n) => n + 1);
      setFel(null);
      try {
        const svar = await gor();
        if (!svar.ok) setFel(felText(svar));
        else setHarSparat(true);
        return svar;
      } catch {
        setFel(text(FEL.databasfel));
        return null;
      } finally {
        setPagaende((n) => n - 1);
      }
    },
    [felText, text]
  );

  const uppdatera = useCallback(
    async (id: string, namn: Saljfalt, varde: string): Promise<boolean> => {
      const svar = await skriv(() => api.uppdatera(id, namn, varde));
      if (svar?.ok) {
        setRader((nu) => nu?.map((r) => (r.id === id ? svar.data : r)) ?? nu);
        return true;
      }
      return false;
    },
    [api, skriv]
  );

  const sattStatus = useCallback(
    async (id: string, status: Saljstatus) => {
      const svar = await skriv(() => api.sattStatus(id, status));
      if (svar?.ok) setRader((nu) => nu?.map((r) => (r.id === id ? svar.data : r)) ?? nu);
    },
    [api, skriv]
  );

  const taBort = useCallback(
    async (rad: Saljrad) => {
      const fraga = text({
        sv: `Ta bort ${rad.foretagsnamn} ur säljlistan? Det går inte att ångra.`,
        en: `Remove ${rad.foretagsnamn} from the sales list? This cannot be undone.`
      });
      if (!window.confirm(fraga)) return;
      const svar = await skriv(() => api.taBort(rad.id));
      if (svar?.ok) setRader((nu) => nu?.filter((r) => r.id !== rad.id) ?? nu);
    },
    [api, skriv, text]
  );

  const laggTill = useCallback(
    async (utkast: Record<Saljfalt, string>): Promise<boolean> => {
      const svar = await skriv(() => api.laggTill(utkast));
      if (svar?.ok) {
        setRader((nu) => [svar.data, ...(nu ?? [])]);
        return true;
      }
      return false;
    },
    [api, skriv]
  );

  const antal = useMemo(() => {
    const alla = rader ?? [];
    const dagar = (r: Saljrad) => (r.senast_kontaktad && idag ? dagarSedan(r.senast_kontaktad, idag) : null);
    return {
      alla: alla.length,
      aldrig: alla.filter((r) => !r.senast_kontaktad).length,
      vecka: alla.filter((r) => {
        const d = dagar(r);
        return d !== null && d >= 0 && d <= 7;
      }).length,
      gammal: alla.filter((r) => {
        const d = dagar(r);
        return d !== null && d > 30;
      }).length
    } satisfies Record<Filter, number>;
  }, [rader, idag]);

  const synliga = useMemo(() => {
    const fraga = sok.trim().toLowerCase();
    const fragaSiffror = fraga.replace(/\D/g, "");
    const urval = (rader ?? []).filter((r) => {
      const d = r.senast_kontaktad && idag ? dagarSedan(r.senast_kontaktad, idag) : null;
      if (filter === "aldrig" && r.senast_kontaktad) return false;
      if (filter === "vecka" && !(d !== null && d >= 0 && d <= 7)) return false;
      if (filter === "gammal" && !(d !== null && d > 30)) return false;
      if (!fraga) return true;
      const hostack = [r.foretagsnamn, r.orgnr, r.kontaktperson, r.kontaktnummer, r.kontaktmail, r.anteckningar]
        .join(" ")
        .toLowerCase();
      if (hostack.includes(fraga)) return true;
      // "0701234567" ska hitta "070-123 45 67" och orgnr skrivna med bindestreck.
      return (
        fragaSiffror.length >= 4 &&
        [r.orgnr, r.kontaktnummer].some((v) => v.replace(/\D/g, "").includes(fragaSiffror))
      );
    });
    const kontakt = (r: Saljrad) => r.senast_kontaktad ?? "";
    return [...urval].sort((a, b) => {
      if (sortering === "namn") return a.foretagsnamn.localeCompare(b.foretagsnamn, "sv");
      if (sortering === "kontakt") return kontakt(b).localeCompare(kontakt(a)) || b.created_at.localeCompare(a.created_at);
      if (sortering === "langst") {
        // Aldrig kontaktade först — de är de som väntat längst.
        return kontakt(a).localeCompare(kontakt(b)) || a.created_at.localeCompare(b.created_at);
      }
      return b.created_at.localeCompare(a.created_at);
    });
  }, [rader, sok, filter, sortering, idag]);

  function exportera() {
    if (!rader?.length) return;
    const rubriker = [...SALJLISTA_FALT.map((namn) => text(FALTETIKETT[namn])), text(T.status)];
    const csv = byggSaljCsv(synliga, rubriker, (rad) => {
      const val = statusInfo(rad.status);
      return val ? text(val.etikett) : "";
    });
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `snajp-saljlista-${idagLokalt()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const filterval: { id: Filter; etikett: Localized }[] = [
    { id: "alla", etikett: T.filterAlla },
    { id: "aldrig", etikett: T.filterAldrig },
    { id: "vecka", etikett: T.filterVecka },
    { id: "gammal", etikett: T.filterGammal }
  ];

  const sparstatus = pagaende > 0 ? text(T.sparar) : harSparat && !fel ? text(T.sparat) : "";

  return (
    <section
      aria-labelledby="saljlista-rubrik"
      className="rounded-card border border-ink/12 bg-paper p-4 shadow-hairline sm:p-6"
    >
      {/* ------------------------------------------------ HUVUD */}
      <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-4">
        <div className="min-w-0 max-w-[68ch]">
          <div className="flex flex-wrap items-center gap-2.5">
            <h2 id="saljlista-rubrik" className="text-[1.25rem] font-semibold tracking-[-0.015em]">
              {text(T.rubrik)}
            </h2>
            <Badge tone={demo ? "warn" : "neutral"}>
              {demo ? text(T.demoMarke) : las ? text(T.lasbehorighet) : text(T.ingarTillagg)}
            </Badge>
          </div>
          {demo ? <p className="mt-1.5 text-[14px] leading-6 text-ink-subtle">{text(T.demoNotis)}</p> : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={exportera}
            disabled={!rader?.length}
            className={cn(btnSecondary, btnLiten)}
          >
            <Download aria-hidden className="h-4 w-4" />
            {text(T.exportera)}
          </button>
          {las ? null : (
            <button
              type="button"
              aria-expanded={formOppen}
              aria-controls="saljlista-ny"
              onClick={() => setFormOppen((v) => !v)}
              className={cn(btnPrimary, btnLiten)}
            >
              <Plus aria-hidden className="h-4 w-4" />
              {text(T.laggTill)}
            </button>
          )}
        </div>
      </div>

      {/* ----------------------------------- STATUSFÄRGERNA (104) */}
      <Statusforklaring />

      {/* --------------------------------------------- NYTT BOLAG */}
      {formOppen && !las ? (
        <NyttForetag
          rader={rader ?? []}
          onSpara={laggTill}
          onStang={() => setFormOppen(false)}
          idag={idag}
        />
      ) : null}

      {/* ---------------------------------------- VERKTYGSRADEN */}
      {rader && rader.length > 0 ? (
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <div className={chiplista} role="group" aria-label={text(T.filtrera)}>
            {filterval.map((val) => (
              <button
                key={val.id}
                type="button"
                aria-pressed={filter === val.id}
                onClick={() => setFilter(val.id)}
                className={cn(chip, filter === val.id ? chipAktiv : chipInaktiv)}
              >
                {text(val.etikett)}
                <span className={cn("num text-[0.75rem]", filter === val.id ? "text-paper/70" : "text-ink-subtle")}>
                  {antal[val.id]}
                </span>
              </button>
            ))}
          </div>
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
            <label className="relative w-full min-w-0 sm:w-[280px]">
              <span className="sr-only">{text(T.sok)}</span>
              <Search aria-hidden className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle" />
              <input
                type="search"
                value={sok}
                onChange={(e) => setSok(e.target.value)}
                placeholder={text(T.sok)}
                className={cn(faltTatt, "w-full pl-8")}
              />
            </label>
            <label className="w-full sm:w-auto">
              <span className="sr-only">{text(T.sortera)}</span>
              <select
                value={sortering}
                onChange={(e) => setSortering(e.target.value as Sortering)}
                className={cn(faltTatt, "w-full sm:w-auto")}
              >
                <option value="nya">{text(T.sortNya)}</option>
                <option value="kontakt">{text(T.sortKontakt)}</option>
                <option value="langst">{text(T.sortLangst)}</option>
                <option value="namn">{text(T.sortNamn)}</option>
              </select>
            </label>
          </div>
        </div>
      ) : null}

      {/* ------------------------------------------------ LISTAN */}
      <div className="mt-5">
        {laddFel ? (
          <Tomt
            action={
              <button type="button" onClick={() => void hamta()} className={cn(btnSecondary, btnLiten)}>
                {text(T.forsokIgen)}
              </button>
            }
          >
            <span role="alert">{laddFel}</span>
          </Tomt>
        ) : rader === null ? (
          <SkeletonRows />
        ) : rader.length === 0 ? (
          <Tomt
            action={
              formOppen || las ? null : (
                <button type="button" onClick={() => setFormOppen(true)} className={cn(btnPrimary, btnLiten)}>
                  <Plus aria-hidden className="h-4 w-4" />
                  {text(T.laggTill)}
                </button>
              )
            }
          >
            {text(T.tomt)}
          </Tomt>
        ) : synliga.length === 0 ? (
          <Tomt>{text(T.ingaTraffar)}</Tomt>
        ) : (
          <>
            {/* Bred skärm: tabellen, med kolumnerna i kalkylarkets ordning. */}
            <div className="hidden md:block">
              <Tabell
                minBredd={1080}
                ariaLabel={text(T.rubrik)}
                kolumner={[
                  { rubrik: text(T.foretagsnamn), bredd: "14%" },
                  { rubrik: text(T.orgnrKort), bredd: "11%" },
                  { rubrik: text(T.kontaktperson), bredd: "10%" },
                  { rubrik: text(T.kontaktnummer), bredd: "14.5%" },
                  { rubrik: text(T.kontaktmail), bredd: "17%" },
                  { rubrik: text(T.senastKontaktad), bredd: "13%" },
                  { rubrik: text(T.anteckningar) },
                  { rubrik: text(T.atgarder), bredd: "80px", srOnly: true }
                ]}
              >
                {synliga.map((rad) => (
                  <TabellRad key={rad.id} rad={rad} idag={idag} onSpara={uppdatera} onStatus={sattStatus} onTaBort={taBort} />
                ))}
              </Tabell>
            </div>
            {/* Telefon: ett kort per bolag, numret överst att ringa från. */}
            <ul className="grid gap-3 md:hidden" aria-label={text(T.rubrik)}>
              {synliga.map((rad) => (
                <Kort key={rad.id} rad={rad} idag={idag} onSpara={uppdatera} onStatus={sattStatus} onTaBort={taBort} />
              ))}
            </ul>
          </>
        )}
      </div>

      {/* ---------------------------------------------- STATUS */}
      <div className="mt-3 flex min-h-5 flex-wrap items-center justify-between gap-2">
        <p role="status" aria-live="polite" className={meta}>
          {sparstatus}
        </p>
        {rader && rader.length > 0 ? (
          <p className={cn(meta, "num")}>
            {text({ sv: `${synliga.length} av ${rader.length} företag`, en: `${synliga.length} of ${rader.length} companies` })}
          </p>
        ) : null}
      </div>
      {fel ? (
        <p role="alert" className="mt-2 text-[14px] text-danger">
          {fel}
        </p>
      ) : null}
    </section>
  );
}

/* ================================================================ FÄLT */

type SparaFn = (id: string, namn: Saljfalt, varde: string) => Promise<boolean>;

/**
 * Ett redigerbart värde som läses som text tills det fokuseras. Sparar på
 * blur och Enter (i anteckningar Ctrl/Cmd+Enter, där Enter är en
 * radbrytning), Esc återställer. Faller sparningen tillbaka fältet på det som
 * står i databasen.
 *
 * `radbryt` ritar ett enradsvärde som en textarea som växer med innehållet,
 * så att ett långt bolagsnamn eller en lång adress bryts i stället för att
 * klippas i den fasta tabellen. Enter skriver aldrig en radbrytning där.
 */
function Falt({
  rad,
  namn,
  onSpara,
  multiline = false,
  radbryt = false,
  typ = "text",
  className,
  etikettText
}: Readonly<{
  rad: Saljrad;
  namn: Saljfalt;
  onSpara: SaljlistaFn;
  multiline?: boolean;
  radbryt?: boolean;
  typ?: "text" | "tel" | "email" | "date";
  className?: string;
  etikettText: string;
}>) {
  const las = useContext(LasLage);
  const sparat = rad[namn] ?? "";
  const [varde, setVarde] = useState(sparat);
  const [fokus, setFokus] = useState(false);
  const [felaktigt, setFelaktigt] = useState(false);

  // Ett nytt värde från servern (normaliserat orgnr, "Idag"-knappen) ska synas
  // — men inte skriva över det någon håller på att skriva.
  useEffect(() => {
    if (!fokus) setVarde(sparat);
  }, [sparat, fokus]);

  async function spara() {
    if (varde === sparat) return;
    const ok = await onSpara(rad.id, namn, varde);
    setFelaktigt(!ok);
    if (!ok) setVarde(sparat);
  }

  function aterstall(el: HTMLInputElement | HTMLTextAreaElement) {
    setVarde(sparat);
    // Blur efter återställningen sparar inget: värdet är då det sparade.
    requestAnimationFrame(() => el.blur());
  }

  const gemensamt = {
    value: varde,
    "aria-label": `${etikettText}, ${rad.foretagsnamn}`,
    "aria-invalid": felaktigt || undefined,
    readOnly: las,
    // Ett tomt fält ska gå att se och träffa, men aldrig se ut som ett värde.
    placeholder: typ === "date" ? undefined : "–",
    onFocus: () => setFokus(true),
    onBlur: () => {
      setFokus(false);
      void spara();
    },
    className: cn(
      faltDiskret,
      "w-full min-w-0 placeholder:text-ink-subtle/50",
      felaktigt && "!border-danger/60",
      las && "hover:!border-transparent",
      className
    )
  };

  if (multiline || radbryt) {
    return (
      <textarea
        {...gemensamt}
        rows={1}
        onChange={(e) => setVarde(radbryt ? e.target.value.replace(/[\r\n]+/g, " ") : e.target.value)}
        onKeyDown={(e) => {
          const el = e.currentTarget;
          if (e.key === "Escape") aterstall(el);
          if (e.key === "Enter" && (radbryt || e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            el.blur();
          }
        }}
        className={cn(
          gemensamt.className,
          "!h-auto resize-none py-1 leading-5 [field-sizing:content]",
          multiline ? "max-h-48 min-h-8" : "min-h-8"
        )}
      />
    );
  }

  return (
    <input
      {...gemensamt}
      type={typ}
      onChange={(e) => setVarde(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === "Enter") e.currentTarget.blur();
        if (e.key === "Escape") aterstall(e.currentTarget);
      }}
    />
  );
}

type SaljlistaFn = SparaFn;

function Ringlank({ nummer, foretag }: Readonly<{ nummer: string; foretag: string }>) {
  const { text } = useLocale();
  const href = telefonlank(nummer);
  if (!href) return null;
  return (
    <a
      href={href}
      aria-label={`${text(T.ring)} ${foretag}`}
      title={text(T.ring)}
      className="focus-ring inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-input text-ink-muted transition-colors hover:bg-moss/10 hover:text-moss"
    >
      <Phone aria-hidden className="h-4 w-4" />
    </a>
  );
}

function Mejllank({ adress, foretag }: Readonly<{ adress: string; foretag: string }>) {
  const { text } = useLocale();
  if (!adress.includes("@")) return null;
  return (
    <a
      href={`mailto:${adress}`}
      aria-label={`${text(T.mejla)} ${foretag}`}
      title={text(T.mejla)}
      className="focus-ring inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-input text-ink-muted transition-colors hover:bg-paper2 hover:text-ink"
    >
      <Mail aria-hidden className="h-4 w-4" />
    </a>
  );
}

function Kontaktdatum({
  rad,
  idag,
  onSpara
}: Readonly<{ rad: Saljrad; idag: string; onSpara: SaljlistaFn }>) {
  const { text } = useLocale();
  const las = useContext(LasLage);
  const relativText = relativ(rad.senast_kontaktad, idag, text);
  const dagar = rad.senast_kontaktad && idag ? dagarSedan(rad.senast_kontaktad, idag) : null;
  return (
    <div className="grid gap-1">
      <Falt rad={rad} namn="senast_kontaktad" typ="date" onSpara={onSpara} etikettText={text(T.senastKontaktad)} />
      <div className="flex min-h-7 flex-wrap items-center gap-1.5 px-1">
        {relativText ? (
          <span className={cn(meta, "text-[0.75rem]", dagar !== null && dagar > 30 && "font-medium text-copper")}>
            {relativText}
          </span>
        ) : (
          <Badge tone="warn">{text(T.aldrig)}</Badge>
        )}
        {idag && rad.senast_kontaktad !== idag && !las ? (
          <button
            type="button"
            title={text(T.satIdag)}
            aria-label={`${text(T.satIdag)}, ${rad.foretagsnamn}`}
            onClick={() => void onSpara(rad.id, "senast_kontaktad", idag)}
            className="focus-ring inline-flex h-6 shrink-0 items-center rounded-full border border-ink/15 px-2 text-[0.75rem] font-medium text-ink-muted transition-colors hover:border-ink/30 hover:bg-paper2 hover:text-ink"
          >
            {text(T.idag)}
          </button>
        ) : null}
      </div>
    </div>
  );
}

/**
 * Förklaringsrutan: en boll per färg med betydelsen bredvid. Står alltid
 * framme — den är nyckeln till radernas färger och demons säljargument.
 */
function Statusforklaring() {
  const { text } = useLocale();
  return (
    <div className="mt-5 flex max-w-full flex-wrap items-center gap-x-5 gap-y-2 rounded-input border border-ink/12 bg-paper2/50 px-3.5 py-2.5">
      <span className={etikett}>{text(T.status)}</span>
      {STATUSVAL.map((val) => (
        <span key={val.kod} className="inline-flex items-center gap-1.5 text-[0.8125rem] text-ink-muted">
          <span aria-hidden className={cn("h-2.5 w-2.5 shrink-0 rounded-full", val.prick)} />
          {text(val.etikett)}
        </span>
      ))}
    </div>
  );
}

type StatusFn = (id: string, status: Saljstatus) => void;

/**
 * Radens statusboll. Klicket öppnar en liten meny med de fyra färgerna och
 * "Ingen status"; att välja den aktiva igen släcker den. Menyn ligger
 * position:fixed — tabellen scrollar i sidled och en absolut meny hade
 * klippts av scrollbehållaren. Läsrollen ser bollen men får ingen knapp.
 */
function StatusKnapp({ rad, onStatus }: Readonly<{ rad: Saljrad; onStatus: StatusFn }>) {
  const { text } = useLocale();
  const las = useContext(LasLage);
  const [meny, setMeny] = useState<{ x: number; y: number; uppat: boolean } | null>(null);
  const aktiv = statusInfo(rad.status);

  if (las) {
    return aktiv ? (
      <span
        role="img"
        aria-label={`${text(T.status)}: ${text(aktiv.etikett)}`}
        title={text(aktiv.etikett)}
        className="inline-flex h-8 w-8 items-center justify-center"
      >
        <span className={cn("h-3 w-3 rounded-full", aktiv.prick)} />
      </span>
    ) : null;
  }

  function oppna(e: React.MouseEvent<HTMLButtonElement>) {
    if (meny) {
      setMeny(null);
      return;
    }
    const r = e.currentTarget.getBoundingClientRect();
    // ~250 px meny: ryms den inte nedåt öppnas den uppåt.
    const uppat = r.bottom + 250 > window.innerHeight;
    setMeny({ x: r.right, y: uppat ? r.top - 4 : r.bottom + 4, uppat });
  }

  function valj(kod: Saljstatus) {
    setMeny(null);
    onStatus(rad.id, kod);
  }

  const alternativ: { kod: Saljstatus; etikett: Localized; prick: string | null }[] = [
    ...STATUSVAL.map((val) => ({ kod: val.kod as Saljstatus, etikett: val.etikett, prick: val.prick as string | null })),
    { kod: "", etikett: T.statusIngen, prick: null }
  ];

  return (
    <div
      onKeyDown={(e) => {
        if (e.key === "Escape") setMeny(null);
      }}
    >
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={meny !== null}
        aria-label={`${text(T.valjStatus)} ${rad.foretagsnamn}. ${aktiv ? text(aktiv.etikett) : text(T.statusIngen)}`}
        title={aktiv ? text(aktiv.etikett) : text(T.status)}
        onClick={oppna}
        className="focus-ring inline-flex h-8 w-8 items-center justify-center rounded-input transition-colors hover:bg-paper2"
      >
        {aktiv ? (
          <span aria-hidden className={cn("h-3 w-3 rounded-full", aktiv.prick)} />
        ) : (
          <span aria-hidden className="h-3 w-3 rounded-full border-[1.5px] border-ink/35" />
        )}
      </button>
      {meny ? (
        <>
          <button
            type="button"
            aria-hidden
            tabIndex={-1}
            onClick={() => setMeny(null)}
            className="fixed inset-0 z-20 cursor-default"
          />
          <div
            role="menu"
            aria-label={`${text(T.status)}, ${rad.foretagsnamn}`}
            style={{
              top: meny.y,
              left: meny.x,
              transform: meny.uppat ? "translate(-100%, -100%)" : "translateX(-100%)"
            }}
            className="fixed z-30 w-60 rounded-input border border-ink/15 bg-paper p-1 shadow-lift"
          >
            {alternativ.map((val) => (
              <button
                key={val.kod || "ingen"}
                type="button"
                role="menuitemradio"
                aria-checked={rad.status === val.kod}
                onClick={() => valj(rad.status === val.kod && val.kod !== "" ? "" : val.kod)}
                className={cn(
                  "focus-ring flex w-full items-center gap-2.5 rounded-[6px] px-2.5 py-2 text-left text-[0.875rem] transition-colors hover:bg-paper2",
                  val.prick === null && "text-ink-muted",
                  rad.status === val.kod && "bg-paper2 font-medium"
                )}
              >
                {val.prick ? (
                  <span aria-hidden className={cn("h-3 w-3 shrink-0 rounded-full", val.prick)} />
                ) : (
                  <span aria-hidden className="h-3 w-3 shrink-0 rounded-full border-[1.5px] border-ink/35" />
                )}
                {text(val.etikett)}
              </button>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}

function TaBortKnapp({ rad, onTaBort }: Readonly<{ rad: Saljrad; onTaBort: (rad: Saljrad) => void }>) {
  const { text } = useLocale();
  if (useContext(LasLage)) return null;
  return (
    <button
      type="button"
      onClick={() => onTaBort(rad)}
      aria-label={`${text(T.taBort)} ${rad.foretagsnamn}`}
      title={text(T.taBort)}
      className="focus-ring inline-flex h-8 w-8 items-center justify-center rounded-input text-ink-subtle transition-colors hover:bg-danger/10 hover:text-danger"
    >
      <Trash2 aria-hidden className="h-4 w-4" />
    </button>
  );
}

function TabellRad({
  rad,
  idag,
  onSpara,
  onStatus,
  onTaBort
}: Readonly<{ rad: Saljrad; idag: string; onSpara: SaljlistaFn; onStatus: StatusFn; onTaBort: (rad: Saljrad) => void }>) {
  const { text } = useLocale();
  const ton = statusInfo(rad.status);
  return (
    <tr className={cn("align-top transition-colors", ton ? ton.yta : "hover:bg-paper2/60")}>
      <Cell titel className="!align-top">
        <Falt rad={rad} namn="foretagsnamn" radbryt onSpara={onSpara} etikettText={text(T.foretagsnamn)} className="font-semibold" />
      </Cell>
      <Cell className="!align-top">
        <Falt rad={rad} namn="orgnr" onSpara={onSpara} etikettText={text(T.orgnr)} className="num" />
      </Cell>
      <Cell className="!align-top">
        <Falt rad={rad} namn="kontaktperson" radbryt onSpara={onSpara} etikettText={text(T.kontaktperson)} />
      </Cell>
      <Cell className="!align-top">
        <div className="flex items-center gap-0.5">
          <Falt rad={rad} namn="kontaktnummer" typ="tel" onSpara={onSpara} etikettText={text(T.kontaktnummer)} className="num" />
          <Ringlank nummer={rad.kontaktnummer} foretag={rad.foretagsnamn} />
        </div>
      </Cell>
      <Cell className="!align-top">
        <div className="flex items-center gap-0.5">
          <Falt rad={rad} namn="kontaktmail" radbryt onSpara={onSpara} etikettText={text(T.kontaktmail)} className="[overflow-wrap:anywhere]" />
          <Mejllank adress={rad.kontaktmail} foretag={rad.foretagsnamn} />
        </div>
      </Cell>
      <Cell className="!align-top">
        <Kontaktdatum rad={rad} idag={idag} onSpara={onSpara} />
      </Cell>
      <Cell className="!align-top">
        <Falt rad={rad} namn="anteckningar" multiline onSpara={onSpara} etikettText={text(T.anteckningar)} />
      </Cell>
      <Cell className="!align-top">
        <div className="flex items-center">
          <StatusKnapp rad={rad} onStatus={onStatus} />
          <TaBortKnapp rad={rad} onTaBort={onTaBort} />
        </div>
      </Cell>
    </tr>
  );
}

function Kort({
  rad,
  idag,
  onSpara,
  onStatus,
  onTaBort
}: Readonly<{ rad: Saljrad; idag: string; onSpara: SaljlistaFn; onStatus: StatusFn; onTaBort: (rad: Saljrad) => void }>) {
  const { text } = useLocale();
  const rubrikId = useId();
  const ton = statusInfo(rad.status);
  return (
    <li
      aria-labelledby={rubrikId}
      className={cn("rounded-input border border-ink/12 bg-paper p-3", ton && cn("border-l-4", ton.kant, ton.yta))}
    >
      <div className="flex items-start gap-1">
        <div className="min-w-0 flex-1" id={rubrikId}>
          <Falt rad={rad} namn="foretagsnamn" radbryt onSpara={onSpara} etikettText={text(T.foretagsnamn)} className="font-semibold" />
        </div>
        <StatusKnapp rad={rad} onStatus={onStatus} />
        <TaBortKnapp rad={rad} onTaBort={onTaBort} />
      </div>
      <dl className="mt-2 grid grid-cols-1 gap-x-4 gap-y-2 min-[440px]:grid-cols-2">
        <KortFalt etikettText={text(T.kontaktnummer)}>
          <div className="flex items-center gap-0.5">
            <Falt rad={rad} namn="kontaktnummer" typ="tel" onSpara={onSpara} etikettText={text(T.kontaktnummer)} className="num" />
            <Ringlank nummer={rad.kontaktnummer} foretag={rad.foretagsnamn} />
          </div>
        </KortFalt>
        <KortFalt etikettText={text(T.kontaktperson)}>
          <Falt rad={rad} namn="kontaktperson" radbryt onSpara={onSpara} etikettText={text(T.kontaktperson)} />
        </KortFalt>
        <KortFalt etikettText={text(T.kontaktmail)}>
          <div className="flex items-center gap-0.5">
            <Falt rad={rad} namn="kontaktmail" radbryt onSpara={onSpara} etikettText={text(T.kontaktmail)} className="[overflow-wrap:anywhere]" />
            <Mejllank adress={rad.kontaktmail} foretag={rad.foretagsnamn} />
          </div>
        </KortFalt>
        <KortFalt etikettText={text(T.orgnr)}>
          <Falt rad={rad} namn="orgnr" onSpara={onSpara} etikettText={text(T.orgnr)} className="num" />
        </KortFalt>
        <KortFalt etikettText={text(T.senastKontaktad)}>
          <Kontaktdatum rad={rad} idag={idag} onSpara={onSpara} />
        </KortFalt>
        <KortFalt etikettText={text(T.anteckningar)} bred>
          <Falt rad={rad} namn="anteckningar" multiline onSpara={onSpara} etikettText={text(T.anteckningar)} />
        </KortFalt>
      </dl>
    </li>
  );
}

function KortFalt({
  etikettText,
  bred = false,
  children
}: Readonly<{ etikettText: string; bred?: boolean; children: React.ReactNode }>) {
  return (
    <div className={cn("min-w-0", bred && "min-[440px]:col-span-2")}>
      <dt className={cn(etikett, "px-1 text-[0.75rem]")}>{etikettText}</dt>
      <dd>{children}</dd>
    </div>
  );
}

/* =========================================================== NYTT BOLAG */

function NyttForetag({
  rader,
  onSpara,
  onStang,
  idag
}: Readonly<{
  rader: Saljrad[];
  onSpara: (utkast: Record<Saljfalt, string>) => Promise<boolean>;
  onStang: () => void;
  idag: string;
}>) {
  const { text } = useLocale();
  const [utkast, setUtkast] = useState(tomtUtkast);
  const [sparar, setSparar] = useState(false);
  const [bekraftadDubblett, setBekraftadDubblett] = useState(false);
  const forsta = useRef<HTMLInputElement | null>(null);
  const basId = useId();

  useEffect(() => {
    forsta.current?.focus();
  }, []);

  // Samma bolag två gånger är två samtal till samma VD. Varna innan, men låt
  // den som vet bättre (ett nytt kontorsnummer, en ny kontakt) lägga till ändå.
  const dubblett = useMemo(() => {
    const nycklar = new Set(dubblettnycklar({ foretagsnamn: utkast.foretagsnamn, orgnr: utkast.orgnr }));
    if (!nycklar.size) return null;
    return rader.find((r) => dubblettnycklar(r).some((n) => nycklar.has(n))) ?? null;
  }, [rader, utkast.foretagsnamn, utkast.orgnr]);

  useEffect(() => setBekraftadDubblett(false), [dubblett?.id]);

  function satt(namn: Saljfalt, varde: string) {
    setUtkast((nu) => ({ ...nu, [namn]: varde }));
  }

  async function skicka(e: React.FormEvent) {
    e.preventDefault();
    if (!utkast.foretagsnamn.trim()) {
      forsta.current?.focus();
      return;
    }
    if (dubblett && !bekraftadDubblett) {
      setBekraftadDubblett(true);
      return;
    }
    setSparar(true);
    const ok = await onSpara(utkast);
    setSparar(false);
    if (ok) {
      setUtkast(tomtUtkast());
      setBekraftadDubblett(false);
      forsta.current?.focus();
    }
  }

  const falt = (namn: Saljfalt, props: React.ComponentProps<"input"> = {}) => (
    <label className="grid min-w-0 gap-1">
      <span className={etikett}>
        {text(FALTETIKETT[namn])}
        {namn === "foretagsnamn" ? <span aria-hidden className="text-copper"> *</span> : null}
      </span>
      <input
        value={utkast[namn]}
        onChange={(e) => satt(namn, e.target.value)}
        placeholder={PLATSHALLARE[namn] ? text(PLATSHALLARE[namn]) : undefined}
        className={cn(faltTatt, "w-full placeholder:text-ink-subtle/60")}
        {...props}
      />
    </label>
  );

  return (
    <form
      id="saljlista-ny"
      onSubmit={(e) => void skicka(e)}
      aria-labelledby={`${basId}-rubrik`}
      className="mt-5 rounded-input border border-ink/12 bg-paper2/50 p-4 sm:p-5"
      onKeyDown={(e) => {
        if (e.key === "Escape") onStang();
      }}
    >
      <h3 id={`${basId}-rubrik`} className="text-[0.9375rem] font-semibold">
        {text(T.nyttForetag)}
      </h3>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {falt("foretagsnamn", { ref: forsta, required: true, "aria-required": true })}
        {falt("orgnr", { inputMode: "numeric" })}
        {falt("kontaktperson")}
        {falt("kontaktnummer", { type: "tel" })}
        {falt("kontaktmail", { type: "email" })}
        <label className="grid min-w-0 gap-1">
          <span className={etikett}>{text(T.senastKontaktad)}</span>
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={utkast.senast_kontaktad}
              onChange={(e) => satt("senast_kontaktad", e.target.value)}
              className={cn(faltTatt, "min-w-0 flex-1")}
            />
            {idag ? (
              <button
                type="button"
                onClick={() => satt("senast_kontaktad", idag)}
                className={cn(btnSecondary, btnLiten)}
              >
                {text(T.idag)}
              </button>
            ) : null}
          </div>
        </label>
        <label className="grid min-w-0 gap-1 sm:col-span-2 lg:col-span-3">
          <span className={etikett}>{text(T.anteckningar)}</span>
          <textarea
            value={utkast.anteckningar}
            onChange={(e) => satt("anteckningar", e.target.value)}
            placeholder={text(T.platsAnteckning)}
            rows={2}
            className={cn(faltTatt, "!h-auto w-full resize-y py-2 leading-5 placeholder:text-ink-subtle/60")}
          />
        </label>
      </div>

      {dubblett ? (
        <p role="status" className="mt-3 rounded-input border border-copper/30 bg-copper/10 px-3 py-2 text-[14px] text-ink">
          {text({
            sv: `${dubblett.foretagsnamn} finns redan i listan${dubblett.senast_kontaktad ? `, senast kontaktad ${dubblett.senast_kontaktad}` : ""}.`,
            en: `${dubblett.foretagsnamn} is already in the list${dubblett.senast_kontaktad ? `, last contacted ${dubblett.senast_kontaktad}` : ""}.`
          })}
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button type="submit" disabled={sparar} className={cn(btnPrimary, btnLiten)}>
          {sparar ? text(T.sparar) : dubblett && bekraftadDubblett ? text(T.sparaAnda) : text(T.spara)}
        </button>
        <button type="button" onClick={onStang} className={cn(btnSecondary, btnLiten)}>
          {text(T.avbryt)}
        </button>
      </div>
    </form>
  );
}

/* ====================================================== UTFORSKA I DEMO */

/**
 * "Utforska säljlistan i demo" (Sebbes beställning 2026-10-06): kunder utan
 * tillägget — och demoytorna — får prova listan med påhittade exempelbolag.
 * Allt sker i minnet i webbläsaren; inget når databasen, och en omladdning
 * börjar om. Teaserrutan frontar tillvalet med mejlvägen in.
 */
export function SaljlistaUtforska({ startOppen = false }: Readonly<{ startOppen?: boolean }>) {
  const { text } = useLocale();
  const [oppen, setOppen] = useState(startOppen);
  const [api] = useState(() => demoApi());

  return (
    <section aria-labelledby="saljlista-utforska" className="grid gap-4">
      <div className="rounded-card border border-ink/12 bg-paper2/40 p-4 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
          <div className="min-w-0 max-w-[64ch]">
            <div className="flex flex-wrap items-center gap-2.5">
              <h2 id="saljlista-utforska" className="text-[1.125rem] font-semibold tracking-[-0.01em]">
                {text(T.rubrik)}
              </h2>
              <Badge tone="warn">{text(T.tillval)}</Badge>
            </div>
            <p className="mt-1 text-[14px] leading-6 text-ink-subtle">{text(T.utforskaText)}</p>
            <a
              href={mejlaOss(text({ sv: "Tillägg: Leadslistor", en: "Add-on: Lead lists" }))}
              className="mt-2 inline-block text-[13px] underline underline-offset-4 transition-colors hover:text-ochre"
            >
              {text(T.horAvDig)}
            </a>
          </div>
          <button type="button" aria-expanded={oppen} onClick={() => setOppen((v) => !v)} className={btnSecondary}>
            {oppen ? text(T.stangDemo) : text(T.utforska)}
          </button>
        </div>
      </div>
      {oppen ? <Saljlista api={api} demo /> : null}
    </section>
  );
}

/** Exempeldatan bakom demon: samma API-form som servern, fast i minnet. */
function demoApi(): SaljlistaApi {
  let rader: Saljrad[] = SALJLISTA_EXEMPEL.map((rad) => ({ ...rad }));
  let lopnummer = 0;

  function kopia(rad: Saljrad): Saljrad {
    return { ...rad };
  }

  return {
    hamta: async () => ({ ok: true, data: rader.map(kopia) }),

    laggTill: async (falt) => {
      const varden = {} as Record<Saljfalt, string | null>;
      for (const namn of SALJLISTA_FALT) {
        const n = normaliseraFalt(namn, falt[namn] ?? null);
        if (!n.ok) return { ok: false, fel: n.fel };
        varden[namn] = n.varde;
      }
      if (!varden.foretagsnamn) return { ok: false, fel: "namn_saknas" };
      lopnummer += 1;
      const rad: Saljrad = {
        id: `00000000-0000-4000-a000-${String(lopnummer).padStart(12, "0")}`,
        foretagsnamn: varden.foretagsnamn,
        orgnr: varden.orgnr ?? "",
        kontaktperson: varden.kontaktperson ?? "",
        kontaktnummer: varden.kontaktnummer ?? "",
        kontaktmail: varden.kontaktmail ?? "",
        senast_kontaktad: varden.senast_kontaktad,
        anteckningar: varden.anteckningar ?? "",
        status: "",
        created_at: new Date().toISOString(),
        updated_at: ""
      };
      rader = [rad, ...rader];
      return { ok: true, data: kopia(rad) };
    },

    uppdatera: async (id, namn, varde) => {
      const n = normaliseraFalt(namn, varde);
      if (!n.ok) return { ok: false, fel: n.fel };
      if (namn === "foretagsnamn" && !n.varde) return { ok: false, fel: "namn_saknas" };
      const plats = rader.findIndex((rad) => rad.id === id);
      if (plats < 0) return { ok: false, fel: "finns_inte" };
      rader[plats] = {
        ...rader[plats],
        [namn]: namn === "senast_kontaktad" ? n.varde : (n.varde ?? "")
      };
      return { ok: true, data: kopia(rader[plats]) };
    },

    sattStatus: async (id, status) => {
      const plats = rader.findIndex((rad) => rad.id === id);
      if (plats < 0) return { ok: false, fel: "finns_inte" };
      rader[plats] = { ...rader[plats], status };
      return { ok: true, data: kopia(rader[plats]) };
    },

    taBort: async (id) => {
      rader = rader.filter((rad) => rad.id !== id);
      return { ok: true, data: { id } };
    }
  };
}
