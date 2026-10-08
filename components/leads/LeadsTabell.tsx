"use client";

import { X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { EjAktiverad } from "@/components/EjAktiverad";
import { Badge, Cell, SkeletonRows, Tabell, Tomt, btnPrimary, btnSecondary, etikett, btnLiten, faltDiskret, faltTatt, chip, chipAktiv, chipInaktiv, chiplista, meta, rubrikPanel, tabellRad } from "@/components/ui";
import { useSmal } from "@/components/leads/smal";
import { SkickatLista, type SkickatRad } from "@/components/leads/SkickatLista";
import { useRadrorelse } from "@/components/leads/useRadrorelse";
import { BekraftaUtskick } from "@/components/leads/BekraftaUtskick";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import {
  LeadsFel,
  datumFormat,
  kontaktvagAv,
  leadsAnrop,
  poangAv,
  relativTid,
  type Kontaktvag,
  type SuiteProspekt,
  type Uppgift,
  type Vy,
  type VyFilter
} from "@/lib/leads/suite";
import { LEADS_UPPDATERADE, UTAN_UTKAST, UTKAST_TON, meddelaLeadsUppdaterade, utkastText } from "@/lib/leads/utkast";
import { LEAD_TYP_ETIKETT, STATUS_ETIKETT, STATUS_ORDNING, leadTyp, nivaEtikett, type LeadTyp } from "@/lib/prospekt";
import { cn } from "@/lib/utils";

/**
 * Leads › Leads (plan 2026-10-05, fas 4): EN vy i full bredd i stället för
 * tre (Alla leads, Tabell, Pipeline). Antons beställning: alla datapunkter på
 * ett ställe, en enkel statusmarkering i stället för pipelinen, och leadsen
 * över hela ytan i stället för en halv sida "Välj ett lead i listan".
 *
 * - Statusremsan överst är pipelinen i kompakt form: varje steg är en räknare
 *   som filtrerar listan.
 * - Varje rad bär bolaget, motiveringens första mening, status (byts direkt,
 *   PATCH, återställs om sparningen faller), poäng och nivå, webbbetyget ur
 *   webbrevisionen, kontaktväg, senaste händelse, nästa uppgift och typ.
 * - Klick på bolaget öppnar detaljen (Bedömning, Mejlutkast, Tidslinje) i en
 *   låda från höger — det ägs av IrisBolag via `onValj`.
 * - Bortvalda (nivå C) ligger bakom en växel: de är Iris arbete, inte leverans.
 */

const T = {
  tabell: { sv: "Leads", en: "Leads" },
  hamtaFel: { sv: "Leads kunde inte hämtas.", en: "The leads could not be loaded." },
  forsokIgen: { sv: "Försök igen", en: "Try again" },
  tomt: { sv: "Inga leads ännu. Kör Iris eller importera en lista.", en: "No leads yet. Run Iris or import a list." },
  ingaTraffar: { sv: "Inga leads matchar filtret.", en: "No leads match the filter." },
  allaKontaktade: {
    sv: "Inga leads väntar på utskick. De kontaktade finns under Inkorg › Skickat.",
    en: "No leads are waiting to be emailed. The contacted ones are under Inbox › Sent."
  },
  kolBolag: { sv: "Bolag", en: "Company" },
  kolStatus: { sv: "Status", en: "Status" },
  kolPoang: { sv: "Poäng", en: "Score" },
  kolWebb: { sv: "Webbplats", en: "Website" },
  kolKontakt: { sv: "Kontaktväg", en: "Contact" },
  kolSenaste: { sv: "Senaste händelse", en: "Last event" },
  kolUppgift: { sv: "Nästa uppgift", en: "Next task" },
  kolTyp: { sv: "Typ", en: "Type" },
  filterNiva: { sv: "Nivå", en: "Tier" },
  filterTyp: { sv: "Typ", en: "Type" },
  filterSok: { sv: "Sök", en: "Search" },
  sokPlaceholder: { sv: "Bolag eller kontakt", en: "Company or contact" },
  alla: { sv: "Alla", en: "All" },
  pipeline: { sv: "Status", en: "Status" },
  vyer: { sv: "Sparade vyer", en: "Saved views" },
  vyNamn: { sv: "Namn på vyn", en: "View name" },
  vyPlaceholder: { sv: "Heta leads i Göteborg", en: "Hot leads in Gothenburg" },
  sparaVy: { sv: "Spara vy", en: "Save view" },
  sparar: { sv: "Sparar…", en: "Saving…" },
  statusSparadesInte: { sv: "Statusen sparades inte", en: "The status was not saved" },
  bortvalda: { sv: "Bortvalda", en: "Dropped" },
  bortvaldaRubrik: { sv: "Bortvalda bolag", en: "Dropped companies" },
  bortvaldaText: {
    sv: "Bolag Iris valde bort för att de inte uppfyller kraven. Inget raderas av sig självt: de står kvar här och nästa sökning hoppar över dem. Markera och välj Ta bort för att radera dem för gott.",
    en: "Companies Iris dropped because they do not meet the requirements. Nothing is deleted on its own: they stay here and the next search skips them. Select them and choose Delete to remove them for good."
  },
  bortvaldaTomt: { sv: "Inga bortvalda bolag.", en: "No dropped companies." },
  bortvaldaFel: { sv: "De bortvalda bolagen kunde inte hämtas.", en: "The dropped companies could not be loaded." },
  bortvald: { sv: "Bortvald", en: "Dropped" },
  arkiverade: { sv: "Arkiverade", en: "Archived" },
  arkiveradeRubrik: { sv: "Arkiverade leads", en: "Archived leads" },
  arkiveradeText: {
    sv: "Leads du arkiverat. De får inga mejl, behåller sin historik och nästa sökning hoppar över dem. Återställ tar tillbaka dem till listan.",
    en: "Leads you have archived. They get no emails, keep their history and the next search skips them. Restore brings them back to the list."
  },
  arkiveradeTomt: { sv: "Inga arkiverade leads.", en: "No archived leads." },
  arkiveradeFel: { sv: "De arkiverade leadsen kunde inte hämtas.", en: "The archived leads could not be loaded." },
  arkiverad: { sv: "Arkiverad", en: "Archived" },
  kolUtkast: { sv: "Utkast", en: "Draft" },
  skickatLank: { sv: "Skickade mejl finns under Inkorg › Skickat", en: "Sent emails are under Inbox › Sent" },
  sidodata: {
    sv: "Uppgifter eller sparade vyer kunde inte hämtas",
    en: "Tasks or saved views could not be loaded"
  },
  ingenUppgift: { sv: "Ingen", en: "None" },
  statusFor: { sv: "Status för", en: "Status for" },
  statusAndrad: { sv: "Status ändrad till", en: "Status changed to" },
  exempel: { sv: "Exempel", en: "Example" },
  ingenPoang: { sv: "Ingen poäng än", en: "No score yet" },
  vyer2: { sv: "Andra vyer", en: "Other views" },
  live: { sv: "Uppdateras live", en: "Updating live" },
  oppna: { sv: "Öppna", en: "Open" },
  modernitet: { sv: "Modernitet", en: "Modernity" }
} satisfies Record<string, Localized>;

const KONTAKT_ETIKETT: Record<Kontaktvag, Localized> = {
  bada: { sv: "Tel och mejl", en: "Phone and email" },
  telefon: { sv: "Tel", en: "Phone" },
  mejl: { sv: "Mejl", en: "Email" },
  saknas: { sv: "Saknas", en: "Missing" }
};

const TYPER: LeadTyp[] = ["iris", "lista", "import", "inkorg"];

/**
 * Iris-listan visar bara leads FÖRE utskick (Antons beställning 2026-10-07):
 * research pågår, Ny och Redo. Ett kontaktat lead tar inte plats bland de
 * genererade — det bor under Inkorg › Skickat, där svaren flyttar det mellan
 * filtren. Remsan är därför bara de tre stegen.
 */
const FORE_UTSKICK = new Set(["researching", "new", "ready"]);
const REMSA = ["researching", "new", "ready"] as const;

/** Skickade mejl de senaste fyra veckorna: samma fönster som nyckeltalen. */
const FYRA_VECKOR_MS = 28 * 24 * 3600 * 1000;

/** Skapa utkast-anropets tak (ProcessaOmRequest): större urval delas upp. */
const PROCESSA_TAK = 200;

/** Lägen som systemet sätter, aldrig kunden: research pågår medan ett jobb
 *  lever (härlett i API:t) och spärrad via avregistreringen. I statusvalet
 *  visas de bara när raden redan står i dem. */
const SYSTEMSTATUS = new Set(["researching", "suppressed"]);

/** Statusar där ett mejl gått ut, och där leadet svarat. Demons Skickat-lista
 *  och nyckeltal räknas ur dem, så att demon säger samma sak på båda ställena. */
const SKICKADE = new Set(["contacted", "replied", "meeting", "won", "lost"]);
const SVARADE = new Set(["replied", "meeting", "won"]);

/**
 * Pipelinestatus i säljlistans färgsystem (Sebbe 2026-10-06): grönt = i hamn,
 * blått = på väg mot affär, rött = nej, gult = kontaktad utan svar. Samma
 * tokens som components/leads/Saljlista.tsx (moss/chart-blue/danger/ochre).
 */
const STATUSPRICK: Record<string, string> = {
  won: "bg-moss",
  replied: "bg-chart-blue",
  meeting: "bg-chart-blue",
  contacted: "bg-ochre",
  lost: "bg-danger"
};

/** Antalet i ett chip. En muted token, aldrig opacity (DESIGN.md: genomskinlig
 *  text har ingen kontrastgaranti): paper-muted på det aktiva ink-chipet,
 *  ink-subtle annars. */
function Antal({ aktiv, children }: Readonly<{ aktiv: boolean; children: React.ReactNode }>) {
  return <span className={cn("num tabular-nums", aktiv ? "text-paper-muted" : "text-ink-subtle")}>{children}</span>;
}

function matchar(p: SuiteProspekt, f: VyFilter): boolean {
  if (f.status && p.status !== f.status) return false;
  if (f.niva && p.niva !== f.niva) return false;
  if (f.typ && leadTyp(p.origin) !== f.typ) return false;
  const sok = f.sok?.trim().toLowerCase();
  if (sok && ![p.company_name, p.contact_name, p.contact_email].some((v) => v?.toLowerCase().includes(sok))) return false;
  return true;
}

/** Bara de nycklar som är satta, så att en sparad vy är jämförbar. */
function rensat(f: VyFilter): VyFilter {
  return Object.fromEntries(Object.entries(f).filter(([, v]) => typeof v === "string" && v.trim() !== "")) as VyFilter;
}

function domanAv(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    return new URL(url.startsWith("http") ? url : `https://${url}`).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** Motiveringens första mening: raden ska gå att skumma, detaljen bär resten. */
function forstaMening(p: SuiteProspekt): string | null {
  const text = p.motivering ?? p.disqualifiers?.[0] ?? null;
  if (!text) return null;
  const slut = text.search(/[.!?](\s|$)/);
  return slut > 0 ? text.slice(0, slut + 1) : text;
}

/** Researchen är köad eller pågår: backenden säger det (status härledd ur
 *  jobbliggaren), eller raden finns men är inte bedömd än. */
function researchPagar(p: SuiteProspekt): boolean {
  if (p.origin === "example") return false;
  return p.status === "researching" || (!p.niva && p.score_total == null && p.icp_fit == null);
}

/** Backendens härledda status: ett researchjobb är köat eller körs nu. Bara
 *  den styr livetakten — en importerad rad utan poäng ser ut som research
 *  men väntar inte på något. */
function iResearch(p: SuiteProspekt): boolean {
  return p.origin !== "example" && p.status === "researching";
}

const NIVA_RANG: Record<string, number> = { A: 0, B: 1 };

function kvalitet(p: SuiteProspekt): number {
  if (typeof p.score_total === "number") return p.score_total;
  if (typeof p.icp_fit === "number") return p.icp_fit * 100;
  return -1;
}

function nyast(a: SuiteProspekt, b: SuiteProspekt): number {
  return (b.created_at ?? "").localeCompare(a.created_at ?? "");
}

/**
 * De bästa leadsen överst (Sebbe 2026-10-07): poäng, sedan nivå (Stark före
 * Möjlig) vid lika poäng, sedan nyast. Poängen är rangpoängen
 * (snajp-support/app/leads/rangpoang.py) och mäter just hur bra leadet är;
 * med nivån först stod "Stark 58" över "Möjlig 78". Bolag under research har
 * inget betyg än och står överst, så att man ser dem bli klara och glida ner
 * till sin plats. Exemplen sorteras som allt annat (kritiken 2026-10-07: med
 * exemplen först läste demon 91, 79, research, 88).
 *
 * Ersätter Antons "nyaste överst" (2026-10-06), vars skäl var att nya leads
 * hamnade mitt i listan: de nya har nu en egen flik, Ny.
 */
function sortera(rader: SuiteProspekt[]): SuiteProspekt[] {
  const grupp = (p: SuiteProspekt) => (iResearch(p) ? 0 : 1);
  return [...rader].sort(
    (a, b) =>
      grupp(a) - grupp(b) ||
      kvalitet(b) - kvalitet(a) ||
      (NIVA_RANG[a.niva ?? ""] ?? 2) - (NIVA_RANG[b.niva ?? ""] ?? 2) ||
      nyast(a, b)
  );
}

/** Tidtakten medan något pågår: tätt nog att se ett bolag byta flik. */
const LIVE_MS = 4000;

/**
 * Demons uppspelade körning (kritiken 2026-10-07: det som Sebbe beställt,
 * leads som flyttar live från Research pågår till Ny, syntes aldrig i demon,
 * som är säljytan). Två påhittade bolag dyker upp under research och blir
 * klara ett i taget. Exempeldata, märkt som allt annat i demon.
 */
const DEMO_KORNING: { id: string; namn: string; ort: Localized; webb: string; niva: "A" | "B"; poang: number; varfor: Localized }[] = [
  {
    id: "demo-live-1",
    namn: "Norrsken Snickeri AB",
    ort: { sv: "Umeå", en: "Umeå" },
    webb: "norrskensnickeri.se",
    niva: "B",
    poang: 71,
    varfor: { sv: "Snickeri med sju anställda som just öppnat en andra verkstad.", en: "Joinery with seven employees that just opened a second workshop." }
  },
  {
    id: "demo-live-2",
    namn: "Kustvik Elteknik AB",
    ort: { sv: "Luleå", en: "Luleå" },
    webb: "kustvikel.se",
    niva: "A",
    poang: 86,
    varfor: { sv: "Elfirma som söker fler företagskunder och rekryterar en säljare.", en: "Electrical firm looking for more business customers and hiring a salesperson." }
  }
];
/** När i demons körning: bolagen dyker upp, och när vart och ett blir klart. */
const DEMO_TIDER = { start: 1200, klara: [5000, 8500] };

export function LeadsTabell({
  onValj,
  valdId = null,
  exempel = [],
  demo = false,
  flyttbar = false,
  korningPagar = false,
  onAntal
}: Readonly<{
  onValj?: (id: string) => void;
  /** Leadet vars låda är öppen: raden markeras. */
  valdId?: string | null;
  /** Demons exempelbolag, överst i listan. */
  exempel?: SuiteProspekt[];
  demo?: boolean;
  /** Plattformsadmin i development: markera leads och flytta dem till main. */
  flyttbar?: boolean;
  /** En Iris-körning pågår (översiktens körningsruta): listan hämtas tätt
   *  även innan första bolaget hunnit köas. */
  korningPagar?: boolean;
  /** Översiktens nyckeltal: listans egna tal, så att de aldrig säger
   *  något annat än listan. `skickat`/`svarat` (de senaste fyra veckorna, ur
   *  samma källa som Inkorg › Skickat) är null tills de hämtats; `godkanda`
   *  är godkända utkast som väntar på sändfönstret. */
  onAntal?: (tal: {
    alla: number;
    nya: number;
    skickat: number | null;
    svarat: number | null;
    godkanda: number;
  }) => void;
}>) {
  const { locale, text } = useLocale();
  const smal = useSmal();
  const pathname = usePathname();
  const [prospekt, setProspekt] = useState<SuiteProspekt[] | null>(null);
  const [uppgifter, setUppgifter] = useState<Uppgift[]>([]);
  const [vyer, setVyer] = useState<Vy[]>([]);
  const [fel, setFel] = useState<string | null>(null);
  const [ejAktiverad, setEjAktiverad] = useState(false);
  const [notis, setNotis] = useState<string | null>(null);
  const [meddelande, setMeddelande] = useState<string | null>(null);
  const [fokusId, setFokusId] = useState<string | null>(null);
  const [sparaOppen, setSparaOppen] = useState(false);

  // Raden kan lämna filtret efter statusbytet: fokus till samma select om den
  // finns kvar efter commit, annars till remsans Alla (2.4.3).
  useEffect(() => {
    if (fokusId) (document.getElementById(`leads-status-${fokusId}`) ?? document.getElementById("leads-remsa-alla"))?.focus();
  }, [fokusId, prospekt]);
  const [filter, setFilter] = useState<VyFilter>({});
  // Flytta till main (admin, development): markerade leads skickas genom
  // samma signerade flyttväg som Byt kund-panelen (lib/actions/flytt.ts).
  const [valda, setValda] = useState<Set<string>>(new Set());
  const [flyttar, setFlyttar] = useState(false);
  const [flyttNotis, setFlyttNotis] = useState<string | null>(null);
  // Massåtgärderna (Sebbe 2026-10-07, Anton 2026-10-07): skapa, skapa om,
  // skicka, arkivera, återställ och ta bort de markerade. En åtgärd i taget.
  const [atgard, setAtgard] = useState<string | null>(null);
  const [atgardNotis, setAtgardNotis] = useState<{ text: string; fel: boolean } | null>(null);
  // Bortvalda (nivå C): dolda som standard (Antons krav), nåbara på begäran
  // (Sebbes krav: inget får se ut som raderat). Hämtas först vid klick.
  const [visaBortvalda, setVisaBortvalda] = useState(false);
  const [bortvalda, setBortvalda] = useState<SuiteProspekt[] | null>(null);
  // Arkiverade (107): samma mönster som bortvalda, med Återställ.
  const [visaArkiverade, setVisaArkiverade] = useState(false);
  const [arkiverade, setArkiverade] = useState<SuiteProspekt[] | null>(null);
  const [arkiveradeFel, setArkiveradeFel] = useState<string | null>(null);
  // Skickat (Sebbe 2026-10-07): varje leadsmejl som gått ut. Hämtas direkt:
  // nyckeltalen räknas ur samma lista som Inkorg › Skickat visar. Listan
  // själv bor i Inkorgen; bara demon (som saknar Inkorg) visar den här.
  const [visaSkickat, setVisaSkickat] = useState(false);
  const [skickat, setSkickat] = useState<SkickatRad[] | null>(null);
  const [skickatFel, setSkickatFel] = useState<string | null>(null);
  const hamtaSkickat = useCallback(async () => {
    if (demo) {
      setSkickat([]);
      return;
    }
    try {
      const svar = await leadsAnrop<{ skickat?: SkickatRad[] }>("/leads/skickat?limit=500");
      setSkickat(svar.skickat ?? []);
      setSkickatFel(null);
    } catch (orsak) {
      setSkickatFel(felmeddelande(orsak));
      setSkickat((nu) => nu ?? []);
    }
  }, [demo]);
  useEffect(() => {
    void hamtaSkickat();
  }, [hamtaSkickat]);
  const [bortvaldaFel, setBortvaldaFel] = useState<string | null>(null);
  const [vyNamn, setVyNamn] = useState("");
  const [sparar, setSparar] = useState(false);

  const hamta = useCallback(async () => {
    setFel(null);
    if (demo) {
      const svar = demoOversiktSvar("/leads/prospects") as { prospects?: SuiteProspekt[] } | undefined;
      setProspekt(svar?.prospects ?? []);
      return;
    }
    try {
      const [p, u, v] = await Promise.allSettled([
        leadsAnrop<{ prospects?: SuiteProspekt[] }>("/leads/prospects"),
        leadsAnrop<{ uppgifter?: Uppgift[] }>("/leads/uppgifter?oppna=1"),
        leadsAnrop<{ vyer?: Vy[] }>("/leads/vyer")
      ]);
      if (p.status === "rejected") throw p.reason;
      setProspekt(p.value.prospects ?? []);
      setUppgifter(u.status === "fulfilled" ? (u.value.uppgifter ?? []) : []);
      setVyer(v.status === "fulfilled" ? (v.value.vyer ?? []) : []);
      const sidofel = [u, v].find((r) => r.status === "rejected") as PromiseRejectedResult | undefined;
      setNotis(sidofel ? `${text(T.sidodata)}: ${felmeddelande(sidofel.reason)}` : null);
    } catch (orsak) {
      if (orsak instanceof LeadsFel && orsak.ejAktiverad) {
        setEjAktiverad(true);
        return;
      }
      setFel(felmeddelande(orsak));
    }
  }, [demo, text]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  // Demons körning spelas upp en gång per besök, i stället för att polla.
  const [demoKorning, setDemoKorning] = useState(false);
  useEffect(() => {
    if (!demo) return;
    const nu = new Date().toISOString();
    const rad = (k: (typeof DEMO_KORNING)[number], klar: boolean): SuiteProspekt => ({
      id: k.id,
      company_name: k.namn,
      ort: text(k.ort),
      website: k.webb,
      origin: "manual",
      created_at: nu,
      status: klar ? "new" : "researching",
      niva: klar ? k.niva : null,
      score_total: klar ? k.poang : null,
      motivering: klar ? text(k.varfor) : null,
      contact_email: klar ? `info@${k.webb}` : null
    });
    const timers: number[] = [];
    const spela = () => {
      timers.push(
        window.setTimeout(() => {
          setDemoKorning(true);
          setProspekt((forra) => [...(forra ?? []), ...DEMO_KORNING.map((k) => rad(k, false))]);
        }, DEMO_TIDER.start),
        ...DEMO_KORNING.map((k, i) =>
          window.setTimeout(() => {
            setProspekt((forra) => (forra ?? []).map((p) => (p.id === k.id ? rad(k, true) : p)));
            if (i === DEMO_KORNING.length - 1) setDemoKorning(false);
          }, DEMO_TIDER.klara[i])
        )
      );
    };
    // Kritik 3: körningen spelades upp innan besökaren nått listan och
    // missades. Den startar nu när listan syns; utan IntersectionObserver
    // (eller utan lista) som förut, från sidladdningen.
    let observer: IntersectionObserver | null = null;
    const vantare = window.setTimeout(() => {
      const el = listref.current;
      if (!el || typeof IntersectionObserver === "undefined") {
        spela();
        return;
      }
      observer = new IntersectionObserver(
        (poster) => {
          if (poster.some((x) => x.isIntersecting)) {
            observer?.disconnect();
            spela();
          }
        },
        { threshold: 0.2 }
      );
      observer.observe(el);
    }, 300);
    return () => {
      window.clearTimeout(vantare);
      observer?.disconnect();
      timers.forEach((t) => window.clearTimeout(t));
    };
    // Språket läses när raden blir klar; ett språkbyte mitt i spelar inte om körningen.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demo]);

  // Bara leadsen, tyst: livetakten ska inte blinka fram fel eller skelett.
  const hamtaLeads = useCallback(async () => {
    if (demo) return;
    try {
      const svar = await leadsAnrop<{ prospects?: SuiteProspekt[] }>("/leads/prospects");
      setProspekt(svar.prospects ?? []);
    } catch {
      // Nästa varv försöker igen; ett tillfälligt fel är ingen nyhet.
    }
  }, [demo]);

  // Live (Sebbe 2026-10-07): medan en körning pågår eller något bolag
  // researchas hämtas listan var fjärde sekund, så att bolagen syns flytta
  // från Research pågår till Ny. När det tystnar hämtas allt en sista gång.
  // Demon: bara den uppspelade körningen. Dess exempelrad som står i
  // research för alltid får inte hålla indikatorn tänd.
  const live = demo ? demoKorning : korningPagar || (prospekt ?? []).some(iResearch);
  const varLive = useRef(false);
  useEffect(() => {
    if (demo) return;
    if (!live) {
      if (varLive.current) void hamta();
      varLive.current = false;
      return;
    }
    varLive.current = true;
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") void hamtaLeads();
    }, LIVE_MS);
    return () => window.clearInterval(id);
  }, [demo, live, hamta, hamtaLeads]);

  // En pågående körning (Kör Iris) lägger till rader medan man tittar.
  useEffect(() => {
    const uppdatera = () => void hamta();
    window.addEventListener("snipra:leads-korning-steg", uppdatera);
    window.addEventListener("snipra:leads-korning-klar", uppdatera);
    return () => {
      window.removeEventListener("snipra:leads-korning-steg", uppdatera);
      window.removeEventListener("snipra:leads-korning-klar", uppdatera);
    };
  }, [hamta]);

  // Bortvalda och arkiverade hämtas först när vyn öppnas, och sedan om efter
  // varje åtgärd som kan ha flyttat ett lead dit eller därifrån.
  const hamtaUndan = useCallback(
    async (vilka: "bortvalda" | "arkiverade") => {
      const [satt, sattFel] = vilka === "bortvalda" ? [setBortvalda, setBortvaldaFel] : [setArkiverade, setArkiveradeFel];
      // Demon har inga bortvalda eller arkiverade bolag; utan det här stod chippen och laddade.
      if (demo) {
        satt([]);
        return;
      }
      sattFel(null);
      try {
        const svar = await leadsAnrop<{ prospects?: SuiteProspekt[] }>(`/leads/prospects?${vilka}=1`);
        satt([...(svar.prospects ?? [])].sort(nyast));
      } catch (orsak) {
        sattFel(felmeddelande(orsak));
        satt((nu) => nu ?? []);
      }
    },
    [demo]
  );

  // Efter en massåtgärd, ett godkännande eller en avvisning (här eller i
  // utkastrutan) hämtas listan, de skickade och de öppnade undanvyerna om —
  // nyckeltalen läser samma tal, så allt på sidan säger samma sak.
  const harBortvalda = bortvalda !== null;
  const harArkiverade = arkiverade !== null;
  useEffect(() => {
    const uppdatera = () => {
      void hamta();
      void hamtaSkickat();
      if (harBortvalda) void hamtaUndan("bortvalda");
      if (harArkiverade) void hamtaUndan("arkiverade");
    };
    window.addEventListener(LEADS_UPPDATERADE, uppdatera);
    return () => window.removeEventListener(LEADS_UPPDATERADE, uppdatera);
  }, [hamta, hamtaSkickat, hamtaUndan, harBortvalda, harArkiverade]);

  const nastaUppgift = useMemo(() => {
    // Backenden sorterar förfallodatum stigande med null sist: första öppna per prospekt vinner.
    const karta = new Map<string, Uppgift>();
    for (const u of uppgifter) if (!u.klar && !karta.has(u.prospect_id)) karta.set(u.prospect_id, u);
    return karta;
  }, [uppgifter]);

  const allaRader = useMemo(() => sortera([...exempel, ...(prospekt ?? [])]), [exempel, prospekt]);
  // Bara leads före utskick (FORE_UTSKICK). Bortvalda och arkiverade når
  // aldrig listan: API:t lämnar dem bara på begäran.
  const urval = useMemo(() => allaRader.filter((p) => FORE_UTSKICK.has(p.status)), [allaRader]);
  const listref = useRef<HTMLDivElement>(null);
  useRadrorelse(listref, prospekt === null ? null : urval);
  // Demon har ingen utskickslogg: dess Skickat byggs av samma exempelleads
  // som listan (kritiken 2: "Skickade 1 122" bredvid "Skickat 0").
  const skickatVisat = useMemo<SkickatRad[] | null>(() => {
    if (!demo) return skickat;
    return allaRader
      .filter((p) => SKICKADE.has(p.status))
      .map((p) => ({
        id: `demo-skickat-${p.id}`,
        subject: text({ sv: `Hej ${p.company_name}`, en: `Hello ${p.company_name}` }),
        body: text({
          sv: "Exempelmejl i demon. I din arbetsyta står mejlet som det skickades.",
          en: "Example email in the demo. In your workspace the email appears as it was sent."
        }),
        sent_at: p.senaste_handelse_at ?? p.created_at ?? new Date().toISOString(),
        prospect_id: p.id,
        company_name: p.company_name,
        contact_name: p.contact_name ?? null,
        prospect_email: p.contact_email ?? null,
        svarat: SVARADE.has(p.status)
      }));
  }, [demo, skickat, allaRader, text]);

  useEffect(() => {
    if (prospekt === null) return;
    // Skickade och svar de senaste fyra veckorna, ur samma lista som Inkorg ›
    // Skickat — nyckeltalet och listan kan inte säga olika saker. Demon har
    // ingen utskickslogg och räknar alla sina exempel.
    const grans = Date.now() - FYRA_VECKOR_MS;
    const fonster = skickatVisat
      ? demo
        ? skickatVisat
        : skickatVisat.filter((r) => new Date(r.sent_at).getTime() >= grans)
      : null;
    onAntal?.({
      alla: urval.length,
      nya: urval.filter((p) => p.status === "new").length,
      skickat: fonster ? fonster.length : null,
      svarat: fonster ? fonster.filter((r) => r.svarat).length : null,
      godkanda: allaRader.filter((p) => p.utkast_status === "godkant").length
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prospekt, allaRader, urval, skickatVisat]);
  const synliga = useMemo(() => urval.filter((p) => matchar(p, filter)), [urval, filter]);
  const harWebb = synliga.some((p) => typeof p.webbrevision?.modernitet === "number");
  const perStatus = useMemo(() => {
    const karta = new Map<string, number>();
    for (const p of urval) if (matchar(p, { ...filter, status: undefined })) karta.set(p.status, (karta.get(p.status) ?? 0) + 1);
    return karta;
  }, [urval, filter]);

  /** Byter vy: listan, en undanvy (bortvalda, arkiverade) eller demons
   *  Skickat. Ett andra klick på samma vy går tillbaka till listan. Valet
   *  töms: en markering gäller raderna man ser. */
  function valjVy(vy: "aktiva" | "bortvalda" | "arkiverade" | "skickat") {
    const nasta = (vy === "bortvalda" && visaBortvalda) || (vy === "arkiverade" && visaArkiverade) || (vy === "skickat" && visaSkickat) ? "aktiva" : vy;
    setVisaBortvalda(nasta === "bortvalda");
    setVisaArkiverade(nasta === "arkiverade");
    setVisaSkickat(nasta === "skickat");
    setValda(new Set());
    setAtgardNotis(null);
    if (nasta === "bortvalda" && bortvalda === null) void hamtaUndan("bortvalda");
    if (nasta === "arkiverade" && arkiverade === null) void hamtaUndan("arkiverade");
  }

  async function bytStatus(id: string, status: string) {
    const forra = prospekt?.find((p) => p.id === id)?.status;
    if (!forra || forra === status) return;
    setProspekt((rader) => rader?.map((p) => (p.id === id ? { ...p, status } : p)) ?? null);
    const namn = prospekt?.find((p) => p.id === id)?.company_name ?? "";
    setMeddelande(`${namn}: ${text(T.statusAndrad)} ${text(STATUS_ETIKETT[status] ?? { sv: status, en: status })}`);
    setFokusId(id);
    if (demo) return;
    setNotis(null);
    try {
      await leadsAnrop(`/leads/prospects/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      setProspekt((rader) =>
        rader?.map((p) => (p.id === id ? { ...p, senaste_handelse_at: new Date().toISOString() } : p)) ?? null
      );
    } catch (orsak) {
      setProspekt((rader) => rader?.map((p) => (p.id === id ? { ...p, status: forra } : p)) ?? null);
      setNotis(`${text(T.statusSparadesInte)}: ${felmeddelande(orsak)}`);
    }
  }

  function vaxlaVald(id: string) {
    setValda((nu) => {
      const nasta = new Set(nu);
      if (nasta.has(id)) nasta.delete(id);
      else nasta.add(id);
      return nasta;
    });
  }

  /** En massåtgärd i taget: knapparna låses, beskedet ersätter det förra.
   *  `gor` returnerar beskedet, eller null när användaren ångrade sig. */
  async function utfor(namn: string, gor: () => Promise<{ text: string; fel: boolean } | null>) {
    if (atgard) return;
    setAtgard(namn);
    setAtgardNotis(null);
    try {
      const notis = await gor();
      if (notis) setAtgardNotis(notis);
    } catch (orsak) {
      setAtgardNotis({ text: felmeddelande(orsak), fel: true });
    } finally {
      setAtgard(null);
    }
  }

  /** Demon gör inga anrop: den säger vad som hade hänt. */
  function demoNotis(vad: Localized) {
    setValda(new Set());
    return {
      text: text({ sv: `Demo: ${vad.sv} Inget ändras i demon.`, en: `Demo: ${vad.en} Nothing changes in the demo.` }),
      fel: false
    };
  }

  /**
   * Skapa utkast (bara markerade utan utkast) och Skapa om utkast (alla
   * markerade; väntande och godkända utkast ersätts). Båda går genom
   * processa-om, samma kedja som en körning: faktagrinden, underlagsgolvet och
   * mottagarregeln gäller. Leadsen står under Research pågår tills utkastet
   * är skrivet, och listan går i livetakt under tiden.
   */
  async function skapaUtkast(rader: SuiteProspekt[], ersatt: boolean) {
    const valt = ersatt ? rader : rader.filter((p) => UTAN_UTKAST.has(p.utkast_status ?? "saknas"));
    if (valt.length === 0) return;
    await utfor(ersatt ? "skapa-om" : "skapa", async () => {
      if (demo) {
        return demoNotis({
          sv: `utkast skulle skrivas till ${valt.length} bolag.`,
          en: `drafts would be written to ${valt.length} companies.`
        });
      }
      if (
        ersatt &&
        !window.confirm(
          text({
            sv: `Skapa om utkasten för ${valt.length} leads? Väntande och godkända utkast ersätts och skickas aldrig.`,
            en: `Recreate the drafts for ${valt.length} leads? Waiting and approved drafts are replaced and never sent.`
          })
        )
      ) {
        return null;
      }
      let koade = 0;
      const hoppade: string[] = [];
      for (let i = 0; i < valt.length; i += PROCESSA_TAK) {
        const svar = await leadsAnrop<{ count?: number; hoppade_over?: string[] }>("/leads/prospects/processa-om", {
          method: "POST",
          body: JSON.stringify({
            prospect_ids: valt.slice(i, i + PROCESSA_TAK).map((p) => p.id),
            scope: "research_and_draft",
            ersatt
          })
        });
        koade += svar.count ?? 0;
        hoppade.push(...(svar.hoppade_over ?? []));
      }
      setValda(new Set());
      meddelaLeadsUppdaterade("tabell");
      return {
        text: text({
          sv: `Utkast skrivs för ${koade} leads. De står under Research pågår tills de är klara.${hoppade.length ? ` ${hoppade.length} har redan fått mejl och hoppades över.` : ""}`,
          en: `Drafts are being written for ${koade} leads. They show as Researching until they are done.${hoppade.length ? ` ${hoppade.length} have already been emailed and were skipped.` : ""}`
        }),
        fel: false
      };
    });
  }

  /**
   * Godkänn och skicka de markerades väntande utkast, ett i taget, genom
   * samma väg som granskningen (POST /leads/queue/{id}/approve: tidsgrinden,
   * språkgrinden och de sex sändspärrarna). Köposten står på raden
   * (utkast_status), så ingen extra hämtning av kön behövs. Redan godkända
   * utkast väntar på sändfönstret och räknas för sig.
   */
  // Bekräftelsen med mottagarlistan (impeccable-kritik 3, Sebbes val:
  // massutskick ja, men aldrig utan att se vem som får mejlet). Ersätter
  // webbläsarens confirm-ruta, som bara sa ett antal.
  const [bekraftaSkick, setBekraftaSkick] = useState<SuiteProspekt[] | null>(null);
  useEffect(() => {
    setBekraftaSkick(null);
  }, [valda]);

  async function skickaValda(rader: SuiteProspekt[], bekraftat = false) {
    await utfor("skicka", async () => {
      if (demo) {
        return demoNotis({
          sv: `utkasten till de ${rader.length} markerade bolagen skulle godkännas och skickas.`,
          en: `the drafts to the ${rader.length} selected companies would be approved and sent.`
        });
      }
      const poster = rader.filter((p) => (p.utkast_status === "vantar" || p.utkast_status === "koad") && p.queue_item_id);
      const godkanda = rader.filter((p) => p.utkast_status === "godkant").length;
      const utan = rader.length - poster.length - godkanda;
      if (poster.length === 0) {
        return godkanda
          ? {
              text: text({
                sv: `De ${godkanda} markerade utkasten är redan godkända och skickas när sändfönstret öppnar (vardagar 08–16).`,
                en: `The ${godkanda} selected drafts are already approved and go out when the sending window opens (weekdays 08–16).`
              }),
              fel: false
            }
          : {
              text: text({
                sv: "Inget av de markerade bolagen har ett utkast som väntar. Välj Skapa utkast först.",
                en: "None of the selected companies has a draft waiting. Choose Create drafts first."
              }),
              fel: true
            };
      }
      if (!bekraftat) {
        setBekraftaSkick(rader);
        return null;
      }
      setBekraftaSkick(null);
      let skickade = 0;
      let vantar = 0;
      const stoppade: string[] = [];
      for (const p of poster) {
        try {
          const svar = await leadsAnrop<{ utfall?: string; besked?: string }>(
            `/leads/queue/${encodeURIComponent(p.queue_item_id ?? "")}/approve`,
            { method: "POST" }
          );
          if (svar.utfall === "sent") skickade += 1;
          else if (svar.utfall === "requeued") vantar += 1;
          else stoppade.push(`${p.company_name}: ${svar.besked ?? svar.utfall ?? ""}`);
        } catch (orsak) {
          stoppade.push(`${p.company_name}: ${felmeddelande(orsak)}`);
        }
      }
      setValda(new Set());
      meddelaLeadsUppdaterade("tabell");
      return {
        text: text({
          sv: [
            `${skickade} skickade`,
            vantar + godkanda ? `${vantar + godkanda} skickas när sändfönstret öppnar (vardagar 08–16)` : null,
            stoppade.length ? `${stoppade.length} stoppades: ${stoppade.join("; ")}` : null,
            utan ? `${utan} saknade utkast` : null
          ].filter(Boolean).join(", ") + ".",
          en: [
            `${skickade} sent`,
            vantar + godkanda ? `${vantar + godkanda} go out when the sending window opens (weekdays 08–16)` : null,
            stoppade.length ? `${stoppade.length} were stopped: ${stoppade.join("; ")}` : null,
            utan ? `${utan} had no draft` : null
          ].filter(Boolean).join(", ") + "."
        }),
        fel: stoppade.length > 0
      };
    });
  }

  /** Arkivera (väntande utskick ställs in) eller Återställ till listan. */
  async function arkivera(rader: SuiteProspekt[], arkivera: boolean) {
    await utfor(arkivera ? "arkivera" : "aterstall", async () => {
      if (demo) {
        return demoNotis(
          arkivera
            ? { sv: `${rader.length} leads skulle arkiveras.`, en: `${rader.length} leads would be archived.` }
            : { sv: `${rader.length} leads skulle återställas.`, en: `${rader.length} leads would be restored.` }
        );
      }
      const svar = await leadsAnrop<{ ids?: string[]; installda_utskick?: number }>("/leads/prospects/arkivera", {
        method: "POST",
        body: JSON.stringify({ ids: rader.map((p) => p.id), arkivera })
      });
      setValda(new Set());
      meddelaLeadsUppdaterade("tabell");
      const antal = svar.ids?.length ?? 0;
      const stoppade = svar.installda_utskick ?? 0;
      return {
        text: arkivera
          ? text({
              sv: `${antal} arkiverade.${stoppade ? ` ${stoppade} väntande utkast ställdes in och skickas inte.` : ""}`,
              en: `${antal} archived.${stoppade ? ` ${stoppade} pending drafts were cancelled and will not be sent.` : ""}`
            })
          : text({ sv: `${antal} återställda till listan.`, en: `${antal} restored to the list.` }),
        fel: false
      };
    });
  }

  /** Ta bort för gott — bara leads som aldrig fått mejl (backenden vägrar
   *  resten: utskicksloggen bär 90-dagarsspärren och avregistreringarna). */
  async function taBort(rader: SuiteProspekt[]) {
    await utfor("ta-bort", async () => {
      if (demo) {
        return demoNotis({ sv: `${rader.length} leads skulle tas bort.`, en: `${rader.length} leads would be deleted.` });
      }
      const fraga = text({
        sv: `Ta bort ${rader.length} leads för gott? Det går inte att ångra. Leads som redan fått mejl tas inte bort; arkivera dem i stället.`,
        en: `Delete ${rader.length} leads for good? This cannot be undone. Leads that have already been emailed are not deleted; archive them instead.`
      });
      if (!window.confirm(fraga)) return null;
      const svar = await leadsAnrop<{ raderade?: string[]; vagrade?: { id: string; skal: string }[] }>(
        "/leads/prospects/radera",
        { method: "POST", body: JSON.stringify({ ids: rader.map((p) => p.id) }) }
      );
      const kontaktade = (svar.vagrade ?? []).filter((v) => v.skal === "kontaktad").length;
      setValda(new Set());
      meddelaLeadsUppdaterade("tabell");
      return {
        text: text({
          sv: `${svar.raderade?.length ?? 0} borttagna.${kontaktade ? ` ${kontaktade} har fått mejl och kan bara arkiveras.` : ""}`,
          en: `${svar.raderade?.length ?? 0} deleted.${kontaktade ? ` ${kontaktade} have been emailed and can only be archived.` : ""}`
        }),
        fel: kontaktade > 0
      };
    });
  }

  async function flyttaValda() {
    if (valda.size === 0 || flyttar) return;
    setFlyttar(true);
    setFlyttNotis(null);
    try {
      const { flyttaProspektTillMain } = await import("@/lib/actions/flytt");
      const svar = await flyttaProspektTillMain([...valda]);
      if (svar.error) {
        const kand: Record<string, Localized> = {
          miljo: { sv: "Flytt till main går bara från development.", en: "Moving to main only works from development." },
          arbetsyta: { sv: "Arbetsytan gick inte att läsa.", en: "The workspace could not be read." },
          antal: { sv: "Markera 1–50 leads.", en: "Select 1–50 leads." }
        };
        setFlyttNotis(svar.felkod ? text(kand[svar.felkod]) : svar.error);
        return;
      }
      const ok = (svar.rader ?? []).filter((r) => r.resultat === "importerad").length;
      const redan = (svar.rader ?? []).filter((r) => r.resultat === "redan_flyttad").length;
      const fel = (svar.rader ?? []).filter((r) => r.resultat === "fel").length;
      setFlyttNotis(
        text({
          sv: `Flytt till main: ${ok} flyttade${redan ? `, ${redan} fanns redan` : ""}${fel ? `, ${fel} föll` : ""}.`,
          en: `Move to main: ${ok} moved${redan ? `, ${redan} already there` : ""}${fel ? `, ${fel} failed` : ""}.`
        })
      );
      if (fel === 0) setValda(new Set());
    } catch (orsak) {
      setFlyttNotis(felmeddelande(orsak));
    } finally {
      setFlyttar(false);
    }
  }

  async function sparaVy() {
    const namn = vyNamn.trim();
    if (!namn || demo) return;
    setSparar(true);
    setNotis(null);
    try {
      const svar = await leadsAnrop<{ vy: Vy }>("/leads/vyer", {
        method: "POST",
        body: JSON.stringify({ namn, filter: rensat(filter) })
      });
      setVyer((forra) => [...forra, svar.vy]);
      setVyNamn("");
      setSparaOppen(false);
    } catch (orsak) {
      setNotis(felmeddelande(orsak));
    } finally {
      setSparar(false);
    }
  }

  async function raderaVy(id: string) {
    const forra = vyer;
    setVyer((v) => v.filter((x) => x.id !== id));
    try {
      await leadsAnrop(`/leads/vyer/${id}`, { method: "DELETE" });
    } catch (orsak) {
      setVyer(forra);
      setNotis(felmeddelande(orsak));
    }
  }

  if (ejAktiverad) return <EjAktiverad yta={text(T.tabell)} />;
  if (fel) {
    return (
      <div>
        <p role="alert" className="text-[0.9375rem] text-danger">
          {text(T.hamtaFel)} {fel}
        </p>
        <button type="button" onClick={() => void hamta()} className={cn(btnSecondary, "mt-4")}>
          {text(T.forsokIgen)}
        </button>
      </div>
    );
  }
  if (prospekt === null && exempel.length === 0) return <SkeletonRows />;
  if (allaRader.length === 0) return <Tomt>{text(T.tomt)}</Tomt>;

  const aktivtFilter = JSON.stringify(rensat(filter));

  const statusVal = (p: SuiteProspekt) =>
    p.origin === "example" ? (
      <span className="inline-flex items-center gap-1.5 text-ink-muted">
        {STATUSPRICK[p.status] ? <span aria-hidden className={cn("h-2 w-2 shrink-0 rounded-full", STATUSPRICK[p.status])} /> : null}
        {text(STATUS_ETIKETT[p.status] ?? { sv: p.status, en: p.status })}
      </span>
    ) : (
      <span className="flex items-center gap-1.5">
        {STATUSPRICK[p.status] ? <span aria-hidden className={cn("h-2 w-2 shrink-0 rounded-full", STATUSPRICK[p.status])} /> : null}
      <select
        id={`leads-status-${p.id}`}
        value={p.status}
        onChange={(e) => void bytStatus(p.id, e.target.value)}
        aria-label={`${text(T.statusFor)} ${p.company_name}`}
        className={cn(faltDiskret, "w-full")}
      >
        {STATUS_ORDNING.filter((s) => !SYSTEMSTATUS.has(s) || s === p.status).map((s) => (
          <option key={s} value={s} disabled={SYSTEMSTATUS.has(s)}>
            {text(STATUS_ETIKETT[s])}
          </option>
        ))}
        {STATUS_ORDNING.includes(p.status as (typeof STATUS_ORDNING)[number]) ? null : (
          <option value={p.status}>{p.status}</option>
        )}
      </select>
      </span>
    );

  const bolag = (p: SuiteProspekt) => {
    const doman = domanAv(p.website);
    const motivering = forstaMening(p);
    return (
      <div className="min-w-0">
        <div className="flex flex-wrap items-baseline gap-x-2">
          {onValj ? (
            <button
              type="button"
              id={`iris-rad-${p.id}`}
              onClick={() => onValj(p.id)}
              aria-label={`${text(T.oppna)} ${p.company_name}`}
              className="focus-ring -mx-1 rounded-input px-1 text-left font-semibold decoration-ink/40 underline-offset-4 hover:underline"
            >
              {p.company_name}
            </button>
          ) : (
            <span className="font-semibold">{p.company_name}</span>
          )}
          {p.origin === "example" ? <Badge>{text(T.exempel)}</Badge> : null}
        </div>
        {p.ort || doman ? <p className={cn(meta, "mt-0.5 truncate")}>{[p.ort, doman].filter(Boolean).join(" · ")}</p> : null}
        {motivering ? (
          <p className="mt-1 line-clamp-2 max-w-[70ch] text-[0.875rem] leading-6 text-ink-muted">{motivering}</p>
        ) : null}
      </div>
    );
  };

  // Under research är poängen ett streck (kritiken 2026-10-07: "Researchar"
  // här och "Research pågår" i statusvalet var två uppgifter om samma sak).
  // Statusen bär läget; skärmläsaren får veta varför fältet är tomt.
  const poangCell = (p: SuiteProspekt) =>
    researchPagar(p) ? (
      <span className="text-ink-subtle">
        <span aria-hidden>–</span>
        <span className="sr-only">{text(T.ingenPoang)}</span>
      </span>
    ) : (
      <span className="inline-flex flex-col items-end leading-tight">
        <span className="num font-semibold tabular-nums">{poangAv(p)}</span>
        {p.niva ? (
          <span className={cn("text-[0.8125rem]", p.niva === "C" ? "text-danger" : "text-ink-subtle")}>
            {nivaEtikett(p.niva, locale)}
          </span>
        ) : null}
      </span>
    );

  const webbCell = (p: SuiteProspekt) => {
    const m = p.webbrevision?.modernitet;
    if (typeof m !== "number") return null;
    const brist = p.webbrevision?.brister?.[0];
    return (
      <span className="inline-flex flex-col gap-1" title={brist ?? undefined}>
        <Badge tone={m <= 4 ? "good" : m >= 7 ? "neutral" : "warn"}>
          <span className="sr-only">{text(T.modernitet)} </span>
          {m}/10
        </Badge>
        {brist ? <span className={cn(meta, "line-clamp-1 max-w-[18ch]")}>{brist}</span> : null}
      </span>
    );
  };

  const uppgiftText = (p: SuiteProspekt) => {
    const u = nastaUppgift.get(p.id);
    if (!u) return <span className={meta}>{text(T.ingenUppgift)}</span>;
    return (
      <>
        <span className="block break-words">{u.titel}</span>
        {u.forfaller ? (
          <span className={meta}>
            {new Date(`${u.forfaller}T00:00:00`).toLocaleDateString(datumFormat(locale), { day: "numeric", month: "short" })}
          </span>
        ) : null}
      </>
    );
  };

  const kontaktChip = (p: SuiteProspekt) => {
    const vag = kontaktvagAv(p);
    return <Badge tone={vag === "saknas" ? "warn" : vag === "bada" ? "good" : "neutral"}>{text(KONTAKT_ETIKETT[vag])}</Badge>;
  };

  /** Utkastets status (backendens härledning, app/leads/utkaststatus.py):
   *  "Väntar på ditt ja", "Godkänt – skickas 08:00" … Ett stopp bär skälet
   *  som hjälptext. Demons rader saknar fältet och visar ett streck. */
  const utkastCell = (p: SuiteProspekt) => {
    const etikett = utkastText(p, locale, text);
    if (!etikett || !p.utkast_status) return <span aria-hidden className="text-ink-subtle">–</span>;
    return (
      <span className={cn("inline-flex flex-col gap-0.5 text-[0.875rem] leading-5", UTKAST_TON[p.utkast_status])}>
        <span>{etikett}</span>
        {p.utkast_status === "stoppat" && p.utkast_skal ? (
          <span className={cn(meta, "line-clamp-2 max-w-[24ch]")} title={p.utkast_skal}>
            {p.utkast_skal}
          </span>
        ) : null}
      </span>
    );
  };

  const kryss = (p: SuiteProspekt, extra?: string) => (
    <label className={cn("-m-2 inline-flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center", extra)}>
      <input
        type="checkbox"
        checked={valda.has(p.id)}
        onChange={() => vaxlaVald(p.id)}
        aria-label={text({ sv: `Markera ${p.company_name}`, en: `Select ${p.company_name}` })}
        className="h-4 w-4 accent-ink"
      />
    </label>
  );

  /** Listan (inte en undanvy eller demons Skickat) visas. */
  const iListan = !visaSkickat && !visaBortvalda && !visaArkiverade;
  function tillListan() {
    if (!iListan) setValda(new Set());
    setVisaSkickat(false);
    setVisaBortvalda(false);
    setVisaArkiverade(false);
  }

  /**
   * Verktygsraden (Antons beställning 2026-10-07): Markera alla, och för de
   * markerade Skicka utkast, Skapa utkast (bara de utan), Skapa om utkast,
   * Arkivera (Återställ i arkivet), Ta bort och — för plattformsadmin i
   * development — Flytta till main. Ett primärt val: Skicka.
   */
  const verktygsrad = (rader: SuiteProspekt[], lage: "aktiva" | "bortvalda" | "arkiverade") => {
    const markerbara = rader.filter((p) => p.origin !== "example" || demo);
    if (markerbara.length === 0) return null;
    const allaValda = markerbara.every((p) => valda.has(p.id));
    const valt = markerbara.filter((p) => valda.has(p.id));
    const utan = valt.filter((p) => UTAN_UTKAST.has(p.utkast_status ?? "saknas")).length;
    const knapp = (namn: string, etikett: Localized, pagar: Localized, gor: () => void, primar = false, av = false) => (
      <button
        type="button"
        disabled={atgard !== null || av}
        onClick={gor}
        className={cn(primar ? btnPrimary : btnSecondary, btnLiten, "disabled:opacity-60")}
      >
        {atgard === namn ? text(pagar) : text(etikett)}
      </button>
    );
    return (
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <button
          type="button"
          onClick={() => setValda(allaValda ? new Set() : new Set(markerbara.map((p) => p.id)))}
          className={cn(btnSecondary, btnLiten)}
        >
          {allaValda
            ? text({ sv: "Avmarkera alla", en: "Clear all" })
            : text({ sv: `Markera alla (${markerbara.length})`, en: `Select all (${markerbara.length})` })}
        </button>
        {valt.length > 0 ? (
          <>
            <span className="num text-[0.875rem] font-medium">
              {text({ sv: `${valt.length} markerade`, en: `${valt.length} selected` })}
            </span>
            {lage === "aktiva" ? (
              <>
                {knapp("skicka", { sv: "Skicka utkast", en: "Send drafts" }, { sv: "Skickar…", en: "Sending…" }, () => void skickaValda(valt), true)}
                {knapp(
                  "skapa",
                  { sv: `Skapa utkast (${utan})`, en: `Create drafts (${utan})` },
                  { sv: "Skapar…", en: "Creating…" },
                  () => void skapaUtkast(valt, false),
                  false,
                  utan === 0
                )}
                {knapp("skapa-om", { sv: "Skapa om utkast", en: "Recreate drafts" }, { sv: "Skapar…", en: "Creating…" }, () => void skapaUtkast(valt, true))}
              </>
            ) : null}
            {lage === "arkiverade"
              ? knapp("aterstall", { sv: "Återställ", en: "Restore" }, { sv: "Återställer…", en: "Restoring…" }, () => void arkivera(valt, false))
              : knapp("arkivera", { sv: "Arkivera", en: "Archive" }, { sv: "Arkiverar…", en: "Archiving…" }, () => void arkivera(valt, true))}
            {knapp("ta-bort", { sv: "Ta bort", en: "Delete" }, { sv: "Tar bort…", en: "Deleting…" }, () => void taBort(valt))}
            {flyttbar && lage === "aktiva" ? (
              <button type="button" disabled={flyttar} onClick={() => void flyttaValda()} className={cn(btnSecondary, btnLiten)}>
                {flyttar
                  ? text({ sv: "Flyttar…", en: "Moving…" })
                  : text({ sv: "Flytta till main", en: "Move to main" })}
              </button>
            ) : null}
            {/* När allt är markerat gör knappen först i raden samma sak. */}
            {allaValda ? null : (
              <button
                type="button"
                onClick={() => setValda(new Set())}
                className="focus-ring text-[0.8125rem] text-ink-muted underline underline-offset-4 hover:text-ink"
              >
                {text({ sv: "Avmarkera", en: "Clear selection" })}
              </button>
            )}
          </>
        ) : null}
      </div>
    );
  };

  /** Bortvalda och arkiverade: samma ruta, var sin förklaring och markör.
   *  Raderna går att markera, så att verktygsraden når dem. */
  const undanPanel = (v: {
    id: string;
    lage: "bortvalda" | "arkiverade";
    rubrik: Localized;
    forklaring: Localized;
    rader: SuiteProspekt[] | null;
    fel: string | null;
    tomt: Localized;
    markor: Localized;
  }) => (
    <section aria-labelledby={v.id} className="rounded-card border border-ink/12 bg-paper2/40 p-4 sm:p-5">
      <h3 id={v.id} className={rubrikPanel}>
        {text(v.rubrik)}
      </h3>
      <p className="mt-1 max-w-[72ch] text-[0.875rem] leading-6 text-ink-subtle">{text(v.forklaring)}</p>
      {v.fel ? (
        <p role="alert" className="mt-3 text-[0.875rem] text-danger">
          {v.fel}
        </p>
      ) : v.rader === null ? (
        <div className="mt-4">
          <SkeletonRows />
        </div>
      ) : v.rader.length === 0 ? (
        <p className={cn(meta, "mt-3")}>{text(v.tomt)}</p>
      ) : (
        <>
          <div className="mt-4">{verktygsrad(v.rader, v.lage)}</div>
          <ul className="mt-3 divide-y divide-ink/10">
            {v.rader.map((p) => (
              <li key={p.id} className="flex items-start gap-3 py-2.5">
                {kryss(p, "mt-1 shrink-0")}
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                    <button
                      type="button"
                      onClick={() => onValj?.(p.id)}
                      className="focus-ring min-w-0 truncate text-left text-[0.9375rem] font-medium text-ink-muted underline-offset-4 hover:text-ink hover:underline"
                    >
                      {p.company_name}
                    </button>
                    <span className="flex shrink-0 items-center gap-2">
                      <Badge tone="warn">{text(v.markor)}</Badge>
                      <span className={meta}>{relativTid(p.arkiverad_at ?? p.senaste_handelse_at ?? p.created_at, locale)}</span>
                    </span>
                  </div>
                  {v.lage === "bortvalda" && (p.disqualifiers?.[0] || p.motivering) ? (
                    <p className={cn(meta, "mt-0.5 max-w-[80ch]")}>{p.disqualifiers?.[0] ?? p.motivering}</p>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );

  return (
    <div ref={listref} className="space-y-5">
      {live ? (
        <p className={cn(meta, "inline-flex items-center gap-2")}>
          <span aria-hidden className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ochre opacity-60 motion-reduce:hidden" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-ochre" />
          </span>
          {text(T.live)}
        </p>
      ) : null}
      {/* Statusremsan: pipelinen som räknare. Ett klick filtrerar, ett till släpper.
          Kritiken 2026-10-07: elva chips i tre rader, fem av dem med 0, och två
          som inte var statusar alls. Nu visas bara stegen före utskick som har
          leads (och det valda). Bortvalda och Arkiverade står för sig till
          höger: de byter vy, de filtrerar inte listan. Skickat är en länk till
          Inkorg › Skickat (Fas 4: kontaktade leads bor där). Antalen bär ett
          mellanslag så att skärmläsaren läser "Skickat 4", inte "Skickat4". */}
      <nav aria-label={text(T.pipeline)} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <ul className={chiplista}>
          <li>
            <button
              type="button"
              id="leads-remsa-alla"
              aria-pressed={!filter.status && iListan}
              onClick={() => {
                tillListan();
                setFilter((f) => ({ ...f, status: undefined }));
              }}
              className={cn(chip, !filter.status && iListan ? chipAktiv : chipInaktiv)}
            >
              {text(T.alla)}{" "}
              <Antal aktiv={!filter.status && iListan}>
                {urval.filter((p) => matchar(p, { ...filter, status: undefined })).length}
              </Antal>
            </button>
          </li>
          {REMSA.map((s) => {
            const antal = perStatus.get(s) ?? 0;
            const aktiv = filter.status === s && iListan;
            const halls = live && (s === "researching" || s === "new");
            if (antal === 0 && !aktiv && !halls) return null;
            return (
              <li key={s}>
                <button
                  type="button"
                  aria-pressed={aktiv}
                  onClick={() => {
                    tillListan();
                    setFilter((f) => ({ ...f, status: aktiv ? undefined : s }));
                  }}
                  className={cn(chip, aktiv ? chipAktiv : chipInaktiv)}
                >
                  {text(STATUS_ETIKETT[s])} <Antal aktiv={aktiv}>{antal}</Antal>
                </button>
              </li>
            );
          })}
        </ul>
        <ul className={chiplista} aria-label={text(T.vyer2)}>
          <li>
            <button
              type="button"
              aria-pressed={visaBortvalda}
              onClick={() => valjVy("bortvalda")}
              className={cn(chip, visaBortvalda ? chipAktiv : chipInaktiv)}
            >
              {text(T.bortvalda)}
              {bortvalda !== null ? (
                <>
                  {" "}
                  <Antal aktiv={visaBortvalda}>{bortvalda.length}</Antal>
                </>
              ) : null}
            </button>
          </li>
          <li>
            <button
              type="button"
              aria-pressed={visaArkiverade}
              onClick={() => valjVy("arkiverade")}
              className={cn(chip, visaArkiverade ? chipAktiv : chipInaktiv)}
            >
              {text(T.arkiverade)}
              {arkiverade !== null ? (
                <>
                  {" "}
                  <Antal aktiv={visaArkiverade}>{arkiverade.length}</Antal>
                </>
              ) : null}
            </button>
          </li>
          <li>
            {demo ? (
              // Demon har ingen Inkorg: dess Skickat visas här, som förut.
              <button
                type="button"
                aria-pressed={visaSkickat}
                onClick={() => valjVy("skickat")}
                className={cn(chip, visaSkickat ? chipAktiv : chipInaktiv)}
              >
                {text({ sv: "Skickat", en: "Sent" })}
                {skickatVisat !== null ? (
                  <>
                    {" "}
                    <Antal aktiv={visaSkickat}>{skickatVisat.length}</Antal>
                  </>
                ) : null}
              </button>
            ) : (
              <Link
                href={`${pathname}?vy=inkorg&flik=skickat`}
                title={text(T.skickatLank)}
                className={cn(chip, chipInaktiv, "underline decoration-ink/25 underline-offset-4")}
              >
                {text({ sv: "Skickat", en: "Sent" })}
                {skickatVisat !== null ? (
                  <>
                    {" "}
                    <Antal aktiv={false}>{skickatVisat.length}</Antal>
                  </>
                ) : null}
              </Link>
            )}
          </li>
        </ul>
      </nav>

      {atgardNotis ? (
        <p role={atgardNotis.fel ? "alert" : "status"} className={cn("text-[0.875rem]", atgardNotis.fel ? "text-danger" : "text-moss")}>
          {atgardNotis.text}
        </p>
      ) : null}
      {flyttNotis ? (
        <p role="status" className="text-[0.875rem] text-ink-muted">
          {flyttNotis}
        </p>
      ) : null}

      {visaSkickat ? (
        <SkickatLista rader={skickatVisat} fel={skickatFel} onValj={onValj} />
      ) : !iListan ? null : (
      <>
      <div className="flex flex-wrap items-end gap-2">
        <label className={cn(etikett, "flex flex-col gap-1")}>
          {text(T.filterNiva)}
          <select
            value={filter.niva ?? ""}
            onChange={(e) => setFilter((f) => ({ ...f, niva: e.target.value }))}
            className={faltTatt}
          >
            <option value="">{text(T.alla)}</option>
            {(["A", "B"] as const).map((n) => (
              <option key={n} value={n}>
                {nivaEtikett(n, locale)}
              </option>
            ))}
          </select>
        </label>
        <label className={cn(etikett, "flex flex-col gap-1")}>
          {text(T.filterTyp)}
          <select
            value={filter.typ ?? ""}
            onChange={(e) => setFilter((f) => ({ ...f, typ: e.target.value }))}
            className={faltTatt}
          >
            <option value="">{text(T.alla)}</option>
            {TYPER.map((t) => (
              <option key={t} value={t}>
                {text(LEAD_TYP_ETIKETT[t])}
              </option>
            ))}
          </select>
        </label>
        <label className={cn(etikett, "flex min-w-[200px] flex-1 flex-col gap-1")}>
          {text(T.filterSok)}
          <input
            type="search"
            value={filter.sok ?? ""}
            onChange={(e) => setFilter((f) => ({ ...f, sok: e.target.value }))}
            placeholder={text(T.sokPlaceholder)}
            className={faltTatt}
          />
        </label>
      </div>

      {vyer.length || !demo ? (
        <div className="flex flex-wrap items-center gap-2">
          <span className={etikett}>{text(T.vyer)}</span>
          <ul className={chiplista}>
            {vyer.map((vy) => {
              const aktiv = aktivtFilter === JSON.stringify(rensat(vy.filter ?? {}));
              return (
                <li key={vy.id} className="inline-flex items-center gap-1">
                  <button
                    type="button"
                    aria-pressed={aktiv}
                    onClick={() => setFilter(aktiv ? {} : rensat(vy.filter ?? {}))}
                    className={cn(chip, aktiv ? chipAktiv : chipInaktiv)}
                  >
                    {vy.namn}
                  </button>
                  {demo ? null : (
                    <button
                      type="button"
                      onClick={() => void raderaVy(vy.id)}
                      aria-label={text({ sv: `Radera vyn ${vy.namn}`, en: `Delete the view ${vy.namn}` })}
                      className="focus-ring inline-flex h-8 w-8 items-center justify-center rounded-full text-ink-muted hover:bg-paper2 hover:text-ink"
                    >
                      <X className="h-4 w-4" aria-hidden />
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
          {demo ? null : sparaOppen ? (
            <form
              className="flex flex-wrap items-center gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                void sparaVy();
              }}
            >
              <label className="sr-only" htmlFor="leads-vy-namn">
                {text(T.vyNamn)}
              </label>
              <input
                id="leads-vy-namn"
                value={vyNamn}
                onChange={(e) => setVyNamn(e.target.value)}
                placeholder={text(T.vyPlaceholder)}
                maxLength={80}
                autoFocus
                className={cn(faltTatt, "w-56")}
              />
              <button type="submit" disabled={sparar || !vyNamn.trim()} className={cn(btnSecondary, btnLiten)}>
                {sparar ? text(T.sparar) : text(T.sparaVy)}
              </button>
            </form>
          ) : (
            <button
              type="button"
              onClick={() => setSparaOppen(true)}
              className="focus-ring text-[0.8125rem] text-ink-muted underline decoration-ink/25 underline-offset-4 hover:text-ink"
            >
              {text(T.sparaVy)}
            </button>
          )}
        </div>
      ) : null}

      {verktygsrad(synliga, "aktiva")}
      {bekraftaSkick ? (
        (() => {
          const poster = bekraftaSkick.filter(
            (p) => (p.utkast_status === "vantar" || p.utkast_status === "koad") && p.queue_item_id
          );
          const godkanda = bekraftaSkick.filter((p) => p.utkast_status === "godkant").length;
          return (
            <BekraftaUtskick
              poster={poster.map((p) => ({
                id: p.id,
                bolag: p.company_name,
                mottagare: p.contact_email ?? null,
                amne: null
              }))}
              overhoppade={bekraftaSkick.length - poster.length - godkanda}
              upptagen={atgard === "skicka"}
              onBekrafta={() => void skickaValda(bekraftaSkick, true)}
              onAvbryt={() => setBekraftaSkick(null)}
            />
          );
        })()
      ) : null}

      {notis ? (
        <p role="alert" className="text-[0.9375rem] text-danger">
          {notis}
        </p>
      ) : null}
      <p role="status" className="sr-only">
        {meddelande}
      </p>

      {synliga.length === 0 ? (
        <Tomt>{urval.length === 0 ? text(T.allaKontaktade) : text(T.ingaTraffar)}</Tomt>
      ) : (
        <>
          <div className={smal ? "hidden" : "hidden lg:block"}>
            <Tabell
              ariaLabel={text(T.tabell)}
              // Typ står inte som kolumn sedan Utkast kom in (2026-10-08): med den
              // rullade tabellen i sidled vid 1440. Typfiltret ovanför och lådan
              // visar typen.
              minBredd={1040}
              kolumner={[
                { rubrik: text({ sv: "Markera", en: "Select" }), bredd: "36px", srOnly: true },
                { rubrik: text(T.kolBolag), bredd: harWebb ? "27%" : "33%" },
                { rubrik: text(T.kolStatus), bredd: "12%" },
                { rubrik: text(T.kolPoang), bredd: "7%", hoger: true },
                // Webbkolumnen bara när någon rad har ett betyg (webbrevisionen):
                // en tom kolumn är bredd utan information.
                ...(harWebb ? [{ rubrik: text(T.kolWebb), bredd: "10%" }] : []),
                { rubrik: text(T.kolUtkast), bredd: "14%" },
                { rubrik: text(T.kolKontakt), bredd: "9%" },
                { rubrik: text(T.kolSenaste), bredd: "11%" },
                { rubrik: text(T.kolUppgift) }
              ]}
            >
              {synliga.map((p) => (
                <tr key={p.id} data-rad-id={p.id} className={cn(tabellRad, "align-top", p.id === valdId && "bg-ochre/10")}>
                  {p.origin !== "example" || demo ? (
                    <Cell>{kryss(p)}</Cell>
                  ) : (
                    <Cell>{null}</Cell>
                  )}
                  <Cell titel>{bolag(p)}</Cell>
                  <Cell>{statusVal(p)}</Cell>
                  <Cell hoger>{poangCell(p)}</Cell>
                  {harWebb ? <Cell>{webbCell(p)}</Cell> : null}
                  <Cell>{utkastCell(p)}</Cell>
                  <Cell>{kontaktChip(p)}</Cell>
                  <Cell className="text-ink-muted">{relativTid(p.senaste_handelse_at ?? p.created_at, locale)}</Cell>
                  <Cell>{uppgiftText(p)}</Cell>
                </tr>
              ))}
            </Tabell>
          </div>

          <ul className={cn("space-y-3", !smal && "lg:hidden")} aria-label={text(T.tabell)}>
            {synliga.map((p) => (
              <li
                key={p.id}
                data-rad-id={p.id}
                className={cn("rounded-card border border-ink/12 bg-paper2/40 p-4", p.id === valdId && "border-ochre/50")}
              >
                <div className="flex items-start justify-between gap-3">
                  {p.origin !== "example" || demo ? kryss(p, "mt-1.5 shrink-0") : null}
                  {bolag(p)}
                  <div className="shrink-0 text-right">{poangCell(p)}</div>
                </div>
                <div className="mt-3 grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
                  <div>{statusVal(p)}</div>
                  <div className="flex flex-wrap items-start justify-end gap-2">
                    {webbCell(p)}
                    {kontaktChip(p)}
                  </div>
                </div>
                {utkastText(p, locale, text) ? <div className="mt-2">{utkastCell(p)}</div> : null}
                <p className={cn(meta, "mt-3")}>
                  {[text(LEAD_TYP_ETIKETT[leadTyp(p.origin)]), relativTid(p.senaste_handelse_at ?? p.created_at, locale)]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </li>
            ))}
          </ul>
        </>
      )}

      </>
      )}

      {/* ------------------------------------ BORTVALDA (nivå C) OCH ARKIVERADE */}
      {visaBortvalda
        ? undanPanel({
            id: "leads-bortvalda",
            lage: "bortvalda",
            rubrik: T.bortvaldaRubrik,
            forklaring: T.bortvaldaText,
            rader: bortvalda,
            fel: bortvaldaFel,
            tomt: T.bortvaldaTomt,
            markor: T.bortvald
          })
        : null}
      {visaArkiverade
        ? undanPanel({
            id: "leads-arkiverade",
            lage: "arkiverade",
            rubrik: T.arkiveradeRubrik,
            forklaring: T.arkiveradeText,
            rader: arkiverade,
            fel: arkiveradeFel,
            tomt: T.arkiveradeTomt,
            markor: T.arkiverad
          })
        : null}
    </div>
  );
}
