"use client";

import { ExternalLink, ImagePlus, Loader2, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useId, useRef, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { HJALP_AV_TEXT, SupportChat, downscaleImage } from "@/components/snajp/SupportChat";
import { Badge, btnLiten, btnPrimary, btnSecondary, chip, chipInaktiv, etikett, flik, flikAktiv, flikInaktiv, fliklista, meta, rubrikPanel } from "@/components/ui";
import { readJsonBody } from "@/lib/http/json";
import { useLocale, type Locale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Hjälprutan (docs/PLAN-HJALPRUTAN-2026-11-25.md, del 1 och 5).
 *
 * Öppnas från "Hjälp och fel" i Meny (components/snajp/AgentMenu.tsx). Ett ark
 * förankrat intill sidomenyn på desktop och i full höjd på mobil; ingen
 * flytande bubbla och ingen panel ovanpå sidans innehåll i övrigt.
 *
 * Två flikar i samma huvud:
 *  - Samtal: SupportChat i hjalpMode mot Snajps egen supportagent, med två
 *    kort i flödet: "Lär agenten om oss" (en artikel i KUNDENS egen
 *    kunskapsbas, genom kundens egen väg och efter kundens klick) och "Något
 *    är fel" (en felrapport som blir ett ärende). Ärenden som väntar på kunden
 *    står fast överst.
 *  - Mina ärenden: kundens egna felrapporter och var de står.
 *
 * Ärendet skapas alltid av kundens klick, aldrig av modellens klassning.
 */

// ---------------------------------------------------------------------------
// Ärendena: typer, kundens ord för lägena, och en delad hämtning.
// ---------------------------------------------------------------------------

export type ArendeStatus =
  | "mottagen"
  | "undersoks"
  | "rattning_pagar"
  | "redo_att_testa"
  | "kund_godkand"
  | "i_development"
  | "i_main"
  | "behover_mer"
  | "stangd";

export type ArendeHandelse = { tid: string; typ: string; status: string | null; meddelande: string | null };

export type Arende = {
  id: string;
  nummer: string;
  status: ArendeStatus;
  sida: string;
  gjorde: string;
  created_at: string;
  updated_at: string;
  vantar_pa_kund: boolean;
  testversion_url: string | null;
  handelser: ArendeHandelse[];
};

/** Kundens ord för lägena. De interna stegen syns bara för plattformsadmin. */
export const STATUSORD: Record<ArendeStatus, Localized> = {
  mottagen: { sv: "Mottaget", en: "Received" },
  undersoks: { sv: "Vi undersöker", en: "We are looking into it" },
  rattning_pagar: { sv: "Rättning på gång", en: "Fix in progress" },
  redo_att_testa: { sv: "Redo att testa", en: "Ready to test" },
  kund_godkand: { sv: "Godkänd, granskas av oss", en: "Approved, under our review" },
  i_development: { sv: "Godkänd, granskas av oss", en: "Approved, under our review" },
  i_main: { sv: "Ute i Snajp", en: "Live in Snajp" },
  behover_mer: { sv: "Behöver mer från dig", en: "We need more from you" },
  stangd: { sv: "Stängd", en: "Closed" }
};

function statusord(status: string | null | undefined): Localized | null {
  return status && status in STATUSORD ? STATUSORD[status as ArendeStatus] : null;
}

export function vantarPaKund(arende: Arende): boolean {
  return arende.vantar_pa_kund || arende.status === "behover_mer" || arende.status === "redo_att_testa";
}

function statuston(status: ArendeStatus): "neutral" | "good" | "warn" {
  if (status === "behover_mer" || status === "redo_att_testa") return "warn";
  if (status === "i_main") return "good";
  return "neutral";
}

/** Bara en https-adress öppnas i en ny flik; allt annat visas inte. */
function sakerTestadress(url: string | null): string | null {
  if (!url) return null;
  try {
    return new URL(url).protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}

type Butik = { arenden: Arende[] | null; fel: "hjalp_av" | "fel" | null; hamtad: number };

const TOM_BUTIK: Butik = { arenden: null, fel: null, hamtad: 0 };
let butik: Butik = TOM_BUTIK;
const lyssnare = new Set<() => void>();
let pagaende: Promise<void> | null = null;
/** Hur gammal listan får vara innan en ny visning eller flikbyte hämtar om den. */
const FARSK_MS = 30_000;
/** Lugn pollning medan rutan är öppen. Pausad när webbläsarfliken är dold. */
const POLL_MS = 20_000;

function sattButik(nytt: Partial<Butik>) {
  butik = { ...butik, ...nytt };
  lyssnare.forEach((lyssnare) => lyssnare());
}

/**
 * En hämtning åt alla: Meny sitter två gånger i skalet (sidomenyn på desktop,
 * mobilraden), och båda behöver veta om något väntar.
 */
export function hamtaArenden(): Promise<void> {
  if (pagaende) return pagaende;
  pagaende = (async () => {
    try {
      const svar = await fetch("/api/snajp-support/hjalp/arenden", { cache: "no-store" });
      const kropp = await readJsonBody<{ arenden?: Arende[]; kod?: string }>(svar).catch(() => null);
      if (kropp?.kod === "hjalp_av") {
        sattButik({ fel: "hjalp_av", hamtad: Date.now() });
      } else if (!svar.ok || !Array.isArray(kropp?.arenden)) {
        sattButik({ fel: "fel", hamtad: Date.now() });
      } else {
        sattButik({ arenden: kropp.arenden, fel: null, hamtad: Date.now() });
      }
    } catch {
      sattButik({ fel: "fel", hamtad: Date.now() });
    } finally {
      pagaende = null;
    }
  })();
  return pagaende;
}

function sattArende(arende: Arende) {
  const lista = butik.arenden ?? [];
  const finns = lista.some((a) => a.id === arende.id);
  sattButik({ arenden: finns ? lista.map((a) => (a.id === arende.id ? arende : a)) : [arende, ...lista] });
}

/** Förhandsvisningen byter läge utan omladdning; listan ska då hämtas på nytt. */
export function glomHjalpArenden() {
  butik = TOM_BUTIK;
  pagaende = null;
  lyssnare.forEach((lyssnare) => lyssnare());
}

function prenumerera(lyssna: () => void) {
  lyssnare.add(lyssna);
  return () => {
    lyssnare.delete(lyssna);
  };
}

/**
 * Kundens ärenden. `aktiv` hämtar alls (bara inloggat, bara där hjälpen
 * finns); `oppen` pollar lugnt medan rutan är öppen och fliken syns.
 */
export function useHjalpArenden(aktiv: boolean, oppen: boolean) {
  const lage = useSyncExternalStore(prenumerera, () => butik, () => TOM_BUTIK);

  useEffect(() => {
    if (!aktiv) return;
    if (Date.now() - butik.hamtad > FARSK_MS) void hamtaArenden();
    const vidSynlig = () => {
      if (document.visibilityState === "visible" && Date.now() - butik.hamtad > FARSK_MS) void hamtaArenden();
    };
    document.addEventListener("visibilitychange", vidSynlig);
    return () => document.removeEventListener("visibilitychange", vidSynlig);
  }, [aktiv]);

  useEffect(() => {
    if (!aktiv || !oppen) return;
    void hamtaArenden();
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") void hamtaArenden();
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [aktiv, oppen]);

  const vantar = aktiv ? (lage.arenden ?? []).filter(vantarPaKund).length : 0;
  return { arenden: lage.arenden, fel: lage.fel, vantar };
}

// ---------------------------------------------------------------------------
// Korten i samtalet
// ---------------------------------------------------------------------------

export type KunskapKortLage = {
  typ: "kunskap";
  steg: "skriv" | "granska" | "sparar" | "tillagd" | "forslag";
  utkast: string;
  titel: string;
  innehall: string;
  fel: Localized | null;
};

export type FelKortLage = {
  typ: "fel";
  steg: "fyll" | "skickar" | "kvitterad" | "avbruten";
  gjorde: string;
  hande: string;
  vantade: string;
  bild: string | null;
  nummer: string | null;
  fel: Localized | null;
};

export type HjalpKortLage = KunskapKortLage | FelKortLage;

function nyttKunskapskort(): KunskapKortLage {
  return { typ: "kunskap", steg: "skriv", utkast: "", titel: "", innehall: "", fel: null };
}

function nyttFelkort(): FelKortLage {
  return { typ: "fel", steg: "fyll", gjorde: "", hande: "", vantade: "", bild: null, nummer: null, fel: null };
}

/**
 * Korten bor utanför rutan. AgentMenu avmonterar rutan när den stängs, och en
 * kund som stänger den för att titta på sidan ska hitta sin halvskrivna
 * rapport (med bild) när hen öppnar igen. Samma modulbutik-mönster som
 * ärendena ovan; den lever så länge sidan inte laddas om.
 */
type KortButik = { ids: string[]; kort: Record<string, HjalpKortLage> };

const TOM_KORT: KortButik = { ids: [], kort: {} };
let kortButik: KortButik = TOM_KORT;
const kortLyssnare = new Set<() => void>();

function prenumereraKort(lyssna: () => void) {
  kortLyssnare.add(lyssna);
  return () => {
    kortLyssnare.delete(lyssna);
  };
}

function sattKortButik(andring: (nu: KortButik) => KortButik) {
  kortButik = andring(kortButik);
  kortLyssnare.forEach((lyssna) => lyssna());
}

/** Ett kort ut ur flödet: både dess innehåll och dess plats. */
function utanKort(nu: KortButik, kortId: string): KortButik {
  const kvar = { ...nu.kort };
  delete kvar[kortId];
  return { ids: nu.ids.filter((id) => id !== kortId), kort: kvar };
}

/**
 * Rutans kort. Utan `start` den delade butiken; med `start` (förhandsvisningen)
 * ett eget tillstånd per läge, så att lägena inte läcker in i varandra.
 */
function useHjalpKort(start: HjalpRutaStart | undefined) {
  const lokalt = start !== undefined;
  const delad = useSyncExternalStore(prenumereraKort, () => kortButik, () => TOM_KORT);
  const [egen, setEgen] = useState<KortButik>(() => ({
    ids: (start?.kort ?? []).map((_, i) => `start-${i}`),
    kort: Object.fromEntries((start?.kort ?? []).map((k, i) => [`start-${i}`, k]))
  }));
  const andra = useCallback(
    (andring: (nu: KortButik) => KortButik) => (lokalt ? setEgen(andring) : sattKortButik(andring)),
    [lokalt]
  );
  return [lokalt ? egen : delad, andra] as const;
}

/** Rubriken ur texten: första raden, högst 80 tecken, avkortad vid ett ord. */
export function rubrikUr(text: string): string {
  const rad = text.trim().split(/\r?\n/).find((r) => r.trim()) ?? "";
  const ren = rad.trim().replace(/^#+\s*/, "");
  if (ren.length <= 80) return ren;
  const kort = ren.slice(0, 80);
  const ord = kort.lastIndexOf(" ");
  return `${(ord > 40 ? kort.slice(0, ord) : kort).trim()}…`;
}

const TITEL_MIN = 3;
const TITEL_MAX = 200;
const INNEHALL_MIN = 10;
const INNEHALL_MAX = 8000;
const FALT_MAX = 4000;

const T = {
  rubrik: { sv: "Snajp Support", en: "Snajp Support" },
  ai: { sv: "AI-assistent", en: "AI assistant" },
  stang: { sv: "Stäng hjälpen", en: "Close help" },
  flikar: { sv: "Hjälpens flikar", en: "Help tabs" },
  samtal: { sv: "Samtal", en: "Conversation" },
  minaArenden: { sv: "Mina ärenden", en: "My cases" },
  tomtRad: {
    sv: "Fråga om Snajp, lär agenten om er eller säg till när något är fel. Svaren kommer från Snajps supportagent, en AI.",
    en: "Ask about Snajp, teach the agent about you, or tell us when something is wrong. Answers come from Snajp's support agent, an AI."
  },
  fraga: { sv: "Fråga om Snajp", en: "Ask about Snajp" },
  lar: { sv: "Lär agenten om oss", en: "Teach the agent about us" },
  fel: { sv: "Något är fel", en: "Something is wrong" },
  // Kunskapskortet
  larEtikett: { sv: "Lär agenten om oss", en: "Teach the agent about us" },
  larFalt: {
    sv: "Skriv eller klistra in det agenten ska veta om er",
    en: "Write or paste what the agent should know about you"
  },
  visaKortet: { sv: "Visa kortet", en: "Show the card" },
  avbryt: { sv: "Avbryt", en: "Cancel" },
  sparasSa: { sv: "Så här sparas det i er kunskapsbas", en: "This is how it is saved in your knowledge base" },
  titel: { sv: "Rubrik", en: "Title" },
  text: { sv: "Text", en: "Text" },
  laggTill: { sv: "Lägg till i er kunskapsbas", en: "Add to your knowledge base" },
  sparaForslag: { sv: "Spara som förslag", en: "Save as suggestion" },
  sparar: { sv: "Sparar…", en: "Saving…" },
  tillagd: { sv: "Tillagd", en: "Added" },
  forslagSparat: { sv: "Sparad som förslag", en: "Saved as a suggestion" },
  visaIKb: { sv: "Visa i Kunskapsbas", en: "Show in Knowledge base" },
  lasroll: {
    sv: "Ditt konto har läsbehörighet. Be en ägare i arbetsytan att lägga till texten.",
    en: "Your account has read access. Ask an owner of the workspace to add the text."
  },
  forKort: {
    sv: `Rubriken behöver minst ${TITEL_MIN} tecken och texten minst ${INNEHALL_MIN}.`,
    en: `The title needs at least ${TITEL_MIN} characters and the text at least ${INNEHALL_MIN}.`
  },
  kbFel: {
    sv: "Texten gick inte att spara. Försök igen om en stund.",
    en: "The text could not be saved. Try again in a moment."
  },
  // Felkortet
  gjorde: { sv: "Vad gjorde du?", en: "What did you do?" },
  hande: { sv: "Vad hände?", en: "What happened?" },
  vantade: { sv: "Vad väntade du dig?", en: "What did you expect?" },
  bifogaBild: { sv: "Bifoga bild", en: "Attach image" },
  taBortBild: { sv: "Ta bort bild", en: "Remove image" },
  bildBifogad: { sv: "Bild bifogad", en: "Image attached" },
  bildFel: { sv: "Bilden gick inte att läsa.", en: "The image could not be read." },
  skickasMed: { sv: "Det här skickas med", en: "This is sent along" },
  sidan: { sv: "Sidan", en: "The page" },
  tiden: { sv: "Tiden", en: "The time" },
  rollen: { sv: "Din roll i arbetsytan", en: "Your role in the workspace" },
  rollLasare: { sv: "Läsbehörighet", en: "Read access" },
  rollMedlem: { sv: "Ägare eller medlem", en: "Owner or member" },
  skicka: { sv: "Skicka", en: "Send" },
  skickar: { sv: "Skickar…", en: "Sending…" },
  fyllNagot: { sv: "Fyll i minst ett av fälten.", en: "Fill in at least one of the fields." },
  rapportFel: {
    sv: "Rapporten gick inte att skicka. Försök igen om en stund.",
    en: "The report could not be sent. Try again in a moment."
  },
  tack: { sv: "Tack. Ärendet är mottaget.", en: "Thank you. The case has been received." },
  visaArenden: { sv: "Visa i Mina ärenden", en: "Show in My cases" },
  // Mina ärenden
  laddar: { sv: "Hämtar dina ärenden…", en: "Fetching your cases…" },
  inga: {
    sv: "Du har inga ärenden. När du säger till om ett fel i Samtal hamnar det här.",
    en: "You have no cases. When you report an issue in Conversation it ends up here."
  },
  listFel: {
    sv: "Ärendena gick inte att hämta just nu. Rutan försöker igen av sig själv.",
    en: "The cases could not be fetched right now. The panel tries again by itself."
  },
  vantarPaDig: { sv: "Väntar på dig", en: "Waiting for you" },
  ditSvar: { sv: "Ditt svar", en: "Your answer" },
  skickaSvar: { sv: "Skicka svar", en: "Send answer" },
  oppnaTest: { sv: "Öppna testversionen", en: "Open the test version" },
  nyFlik: { sv: "öppnas i en ny flik", en: "opens in a new tab" },
  fungerade: { sv: "Fungerade det?", en: "Did it work?" },
  ja: { sv: "Ja", en: "Yes" },
  nej: { sv: "Nej", en: "No" },
  vadFelade: { sv: "Vad fungerar fortfarande inte?", en: "What still does not work?" },
  skickaNej: { sv: "Skicka", en: "Send" },
  atgardFel: { sv: "Det gick inte att skicka. Försök igen.", en: "It could not be sent. Try again." },
  andradesTill: { sv: "Läget blev", en: "Status changed to" },
  handelser: { sv: "Förlopp", en: "Progress" }
} satisfies Record<string, Localized>;

function tidText(iso: string, locale: Locale): string {
  const tid = new Date(iso);
  if (Number.isNaN(tid.getTime())) return "";
  return new Intl.DateTimeFormat(locale === "sv" ? "sv-SE" : "en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit"
  }).format(tid);
}

const kortYta = "rounded-card border border-ink/12 bg-paper2/60 px-4 py-3 text-[0.875rem] leading-6";
const faltYta =
  "focus-ring mt-1 w-full resize-y rounded-input border border-ink/15 bg-paper px-3 py-2 text-[1rem] leading-6 text-ink outline-none [@media(pointer:fine)]:text-[0.9375rem]";

function KunskapKort({
  kort,
  arLasare,
  onAndra
}: Readonly<{ kort: KunskapKortLage; arLasare: boolean; onAndra: (nytt: KunskapKortLage | null) => void }>) {
  const { text, locale } = useLocale();
  const id = useId();

  const spara = async (som: "artikel" | "forslag") => {
    const titel = kort.titel.trim();
    const innehall = kort.innehall.trim();
    if (titel.length < TITEL_MIN || innehall.length < INNEHALL_MIN) {
      onAndra({ ...kort, fel: T.forKort });
      return;
    }
    onAndra({ ...kort, steg: "sparar", fel: null });
    try {
      // Kundens EGEN kunskapsbas, genom kundens egen väg (catch-all-proxyn,
      // proxyAsTenant). Kundens klick här är godkännandet (INV-LEARN-001).
      const svar =
        som === "artikel"
          ? await fetch("/api/snajp-support/kb", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ articles: [{ title: titel, content: innehall }] })
            })
          : await fetch("/api/snajp-support/kb/forslag", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ title: titel, content: innehall, category: null, kalla: "chatt" })
            });
      if (!svar.ok) {
        onAndra({ ...kort, steg: "granska", fel: svar.status === 403 ? T.lasroll : T.kbFel });
        return;
      }
      onAndra({ ...kort, titel, innehall, steg: som === "artikel" ? "tillagd" : "forslag", fel: null });
    } catch {
      onAndra({ ...kort, steg: "granska", fel: T.kbFel });
    }
  };

  if (kort.steg === "skriv") {
    return (
      <div className={kortYta}>
        <p className={etikett}>{text(T.larEtikett)}</p>
        <label htmlFor={`${id}-utkast`} className="mt-2 block text-ink">
          {text(T.larFalt)}
        </label>
        <textarea
          id={`${id}-utkast`}
          value={kort.utkast}
          onChange={(e) => onAndra({ ...kort, utkast: e.target.value })}
          rows={5}
          maxLength={INNEHALL_MAX}
          className={faltYta}
        />
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={kort.utkast.trim().length < INNEHALL_MIN}
            onClick={() =>
              onAndra({
                ...kort,
                steg: "granska",
                titel: rubrikUr(kort.utkast).slice(0, TITEL_MAX),
                innehall: kort.utkast.trim(),
                fel: null
              })
            }
            className={cn(btnPrimary, btnLiten)}
          >
            {text(T.visaKortet)}
          </button>
          <button type="button" onClick={() => onAndra(null)} className={cn(btnSecondary, btnLiten)}>
            {text(T.avbryt)}
          </button>
        </div>
      </div>
    );
  }

  const klar = kort.steg === "tillagd" || kort.steg === "forslag";
  const sparar = kort.steg === "sparar";
  return (
    <div className={kortYta}>
      <p className={etikett}>{text(T.sparasSa)}</p>
      {klar ? (
        <>
          <p className="mt-2 font-semibold text-ink">{kort.titel}</p>
          <div className="mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap rounded-input bg-paper px-3 py-2 text-ink-muted">
            {kort.innehall}
          </div>
          <p className="mt-3 text-moss">
            {text(kort.steg === "tillagd" ? T.tillagd : T.forslagSparat)}
            {" · "}
            <Link href="/settings/kunskapsbas" className="focus-ring rounded-input font-medium text-ink underline underline-offset-4">
              {text(T.visaIKb)}
            </Link>
          </p>
        </>
      ) : (
        <>
          <label htmlFor={`${id}-titel`} className={cn(etikett, "mt-2 block")}>
            {text(T.titel)}
          </label>
          <input
            id={`${id}-titel`}
            value={kort.titel}
            onChange={(e) => onAndra({ ...kort, titel: e.target.value })}
            maxLength={TITEL_MAX}
            disabled={sparar}
            className={cn(faltYta, "resize-none font-semibold")}
          />
          <label htmlFor={`${id}-text`} className={cn(etikett, "mt-2 block")}>
            {text(T.text)}
          </label>
          <textarea
            id={`${id}-text`}
            value={kort.innehall}
            onChange={(e) => onAndra({ ...kort, innehall: e.target.value })}
            rows={6}
            maxLength={INNEHALL_MAX}
            disabled={sparar}
            className={faltYta}
          />
          {arLasare ? <p className="mt-2 text-ink-muted">{text(T.lasroll)}</p> : null}
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={arLasare || sparar}
              onClick={() => void spara("artikel")}
              className={cn(btnPrimary, btnLiten)}
            >
              {sparar ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
              {text(sparar ? T.sparar : T.laggTill)}
            </button>
            <button
              type="button"
              disabled={arLasare || sparar}
              onClick={() => void spara("forslag")}
              className={cn(btnSecondary, btnLiten)}
            >
              {text(T.sparaForslag)}
            </button>
            <button type="button" disabled={sparar} onClick={() => onAndra(null)} className={cn(btnSecondary, btnLiten)}>
              {text(T.avbryt)}
            </button>
          </div>
          {kort.fel ? (
            <p role="alert" className="mt-2 text-danger">
              {kort.fel[locale]}
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}

function FelKort({
  kort,
  arLasare,
  onAndra,
  onVisaArenden
}: Readonly<{
  kort: FelKortLage;
  arLasare: boolean;
  onAndra: (nytt: FelKortLage) => void;
  onVisaArenden: () => void;
}>) {
  const { text, locale } = useLocale();
  const id = useId();
  const filRef = useRef<HTMLInputElement>(null);
  // Sidan och tiden som skickas med, så som kunden ser dem. Bara sökvägen:
  // söksträngen kan bära ett id eller en token och lämnar aldrig webbläsaren.
  const [sida] = useState(() => (typeof window === "undefined" ? "/" : window.location.pathname.slice(0, 300)));
  const [nu, setNu] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setNu(new Date()), 30_000);
    return () => clearInterval(timer);
  }, []);

  if (kort.steg === "avbruten") return null;

  if (kort.steg === "kvitterad") {
    return (
      <div className={kortYta}>
        <p className={etikett}>{text(T.fel)}</p>
        <p className="mt-2 text-ink">{text(T.tack)}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="num font-semibold text-ink">{kort.nummer}</span>
          <Badge>{text(STATUSORD.mottagen)}</Badge>
        </div>
        <button type="button" onClick={onVisaArenden} className={cn(btnSecondary, btnLiten, "mt-3")}>
          {text(T.visaArenden)}
        </button>
      </div>
    );
  }

  const skickar = kort.steg === "skickar";
  const skicka = async () => {
    if (!kort.gjorde.trim() && !kort.hande.trim() && !kort.vantade.trim()) {
      onAndra({ ...kort, fel: T.fyllNagot });
      return;
    }
    onAndra({ ...kort, steg: "skickar", fel: null });
    try {
      const svar = await fetch("/api/snajp-support/hjalp/arenden", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sida,
          gjorde: kort.gjorde,
          hande: kort.hande,
          vantade: kort.vantade,
          bild: kort.bild
        })
      });
      const kropp = await readJsonBody<{ nummer?: string; kod?: string }>(svar).catch(() => null);
      if (!svar.ok || !kropp?.nummer) {
        onAndra({ ...kort, steg: "fyll", fel: kropp?.kod === "hjalp_av" ? HJALP_AV_TEXT : T.rapportFel });
        return;
      }
      onAndra({ ...kort, steg: "kvitterad", nummer: kropp.nummer, fel: null });
      void hamtaArenden();
    } catch {
      onAndra({ ...kort, steg: "fyll", fel: T.rapportFel });
    }
  };

  const falt = (namn: "gjorde" | "hande" | "vantade", etikettText: Localized) => (
    <div className="mt-2">
      <label htmlFor={`${id}-${namn}`} className="block text-ink">
        {text(etikettText)}
      </label>
      <textarea
        id={`${id}-${namn}`}
        value={kort[namn]}
        onChange={(e) => onAndra({ ...kort, [namn]: e.target.value })}
        rows={2}
        maxLength={FALT_MAX}
        disabled={skickar}
        className={faltYta}
      />
    </div>
  );

  return (
    <div className={kortYta}>
      <p className={etikett}>{text(T.fel)}</p>
      {falt("gjorde", T.gjorde)}
      {falt("hande", T.hande)}
      {falt("vantade", T.vantade)}

      <div className="mt-3">
        <input
          ref={filRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => {
            const fil = e.target.files?.[0];
            e.target.value = "";
            if (!fil || !fil.type.startsWith("image/")) return;
            downscaleImage(fil)
              .then((bild) => onAndra({ ...kort, bild, fel: null }))
              .catch(() => onAndra({ ...kort, fel: T.bildFel }));
          }}
        />
        {kort.bild ? (
          <div className="inline-flex items-center gap-2 rounded-input bg-paper p-1.5 pr-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={kort.bild} alt={text(T.bildBifogad)} className="h-10 w-10 rounded-[6px] object-cover" />
            <span className={meta}>{text(T.bildBifogad)}</span>
            <button
              type="button"
              onClick={() => onAndra({ ...kort, bild: null })}
              className="focus-ring rounded-full p-1 text-ink-subtle hover:text-danger"
              aria-label={text(T.taBortBild)}
            >
              <X className="h-3.5 w-3.5" aria-hidden />
            </button>
          </div>
        ) : (
          <button type="button" disabled={skickar} onClick={() => filRef.current?.click()} className={cn(btnSecondary, btnLiten)}>
            <ImagePlus className="h-3.5 w-3.5" aria-hidden />
            {text(T.bifogaBild)}
          </button>
        )}
      </div>

      {/* Öppet om vad som följer med, före knappen och inte efter. */}
      <div className="mt-3 border-t border-ink/10 pt-2">
        <p className={etikett}>{text(T.skickasMed)}</p>
        <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[0.8125rem] text-ink-muted">
          <dt>{text(T.sidan)}</dt>
          <dd className="min-w-0 break-all font-mono text-[0.75rem] leading-5">{sida}</dd>
          <dt>{text(T.tiden)}</dt>
          <dd>{tidText(nu.toISOString(), locale)}</dd>
          <dt>{text(T.rollen)}</dt>
          <dd>{arLasare ? text(T.rollLasare) : text(T.rollMedlem)}</dd>
        </dl>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" disabled={skickar} onClick={() => void skicka()} className={cn(btnPrimary, btnLiten)}>
          {skickar ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
          {text(skickar ? T.skickar : T.skicka)}
        </button>
        <button
          type="button"
          disabled={skickar}
          onClick={() => onAndra({ ...kort, steg: "avbruten" })}
          className={cn(btnSecondary, btnLiten)}
        >
          {text(T.avbryt)}
        </button>
      </div>
      {kort.fel ? (
        <p role="alert" className="mt-2 text-danger">
          {kort.fel[locale]}
        </p>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Ett ärende
// ---------------------------------------------------------------------------

function ArendeKort({ arende }: Readonly<{ arende: Arende }>) {
  const { text, locale } = useLocale();
  const id = useId();
  const [svarText, setSvarText] = useState("");
  const [nejOppen, setNejOppen] = useState(false);
  const [kommentar, setKommentar] = useState("");
  const [skickar, setSkickar] = useState(false);
  const [fel, setFel] = useState(false);

  const posta = async (slut: "svar" | "utslag", kropp: unknown) => {
    setSkickar(true);
    setFel(false);
    try {
      const svar = await fetch(`/api/snajp-support/hjalp/arenden/${encodeURIComponent(arende.id)}/${slut}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(kropp)
      });
      const nytt = await readJsonBody<Arende>(svar).catch(() => null);
      if (!svar.ok || !nytt?.id) {
        setFel(true);
        return;
      }
      sattArende(nytt);
      setSvarText("");
      setKommentar("");
      setNejOppen(false);
    } catch {
      setFel(true);
    } finally {
      setSkickar(false);
    }
  };

  const testadress = sakerTestadress(arende.testversion_url);
  const handelser = arende.handelser
    .map((h) => {
      const ord = statusord(h.status);
      const rad = h.meddelande?.trim() || (ord ? `${text(T.andradesTill)}: ${text(ord)}` : "");
      return rad ? { tid: h.tid, rad } : null;
    })
    .filter((h): h is { tid: string; rad: string } => h !== null);

  return (
    <article
      aria-labelledby={`${id}-nummer`}
      className={cn("rounded-card border bg-paper px-4 py-3", vantarPaKund(arende) ? "border-ochre/50" : "border-ink/12")}
    >
      <div className="flex flex-wrap items-center gap-2">
        <h3 id={`${id}-nummer`} className={cn(rubrikPanel, "num")}>
          {arende.nummer}
        </h3>
        <Badge tone={statuston(arende.status)}>{text(STATUSORD[arende.status] ?? STATUSORD.mottagen)}</Badge>
      </div>
      <p className={cn(meta, "mt-0.5")}>
        <span className="font-mono text-[0.75rem]">{arende.sida}</span> · {tidText(arende.created_at, locale)}
      </p>
      {arende.gjorde ? <p className="mt-2 line-clamp-2 text-[0.9375rem] text-ink-muted">{arende.gjorde}</p> : null}

      {handelser.length ? (
        <div className="mt-3">
          <p className={etikett}>{text(T.handelser)}</p>
          <ol className="mt-1 flex flex-col gap-1.5">
            {handelser.map((h, i) => (
              <li key={`${h.tid}-${i}`} className="grid grid-cols-[5.5rem_1fr] gap-2 text-[0.875rem] leading-5">
                <span className={cn(meta, "num")}>{tidText(h.tid, locale)}</span>
                <span className="whitespace-pre-wrap text-ink">{h.rad}</span>
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      {arende.status === "behover_mer" ? (
        <div className="mt-3 border-t border-ink/10 pt-3">
          <label htmlFor={`${id}-svar`} className={etikett}>
            {text(T.ditSvar)}
          </label>
          <textarea
            id={`${id}-svar`}
            value={svarText}
            onChange={(e) => setSvarText(e.target.value)}
            rows={3}
            maxLength={FALT_MAX}
            disabled={skickar}
            className={faltYta}
          />
          <button
            type="button"
            disabled={skickar || !svarText.trim()}
            onClick={() => void posta("svar", { text: svarText })}
            className={cn(btnPrimary, btnLiten, "mt-2")}
          >
            {skickar ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
            {text(T.skickaSvar)}
          </button>
        </div>
      ) : null}

      {arende.status === "redo_att_testa" ? (
        <div className="mt-3 border-t border-ink/10 pt-3">
          {testadress ? (
            <a
              href={testadress}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(btnSecondary, btnLiten)}
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden />
              {text(T.oppnaTest)}
              <span className="sr-only"> ({text(T.nyFlik)})</span>
            </a>
          ) : null}
          <p className={cn(etikett, "mt-3")}>{text(T.fungerade)}</p>
          <div className="mt-1.5 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={skickar}
              onClick={() => void posta("utslag", { fungerar: true, kommentar: null })}
              className={cn(btnPrimary, btnLiten)}
            >
              {text(T.ja)}
            </button>
            <button
              type="button"
              disabled={skickar}
              aria-expanded={nejOppen}
              onClick={() => setNejOppen(true)}
              className={cn(btnSecondary, btnLiten)}
            >
              {text(T.nej)}
            </button>
          </div>
          {nejOppen ? (
            <div className="mt-2">
              <label htmlFor={`${id}-kommentar`} className={etikett}>
                {text(T.vadFelade)}
              </label>
              <textarea
                id={`${id}-kommentar`}
                value={kommentar}
                onChange={(e) => setKommentar(e.target.value)}
                rows={3}
                maxLength={FALT_MAX}
                disabled={skickar}
                className={faltYta}
              />
              <button
                type="button"
                disabled={skickar}
                onClick={() => void posta("utslag", { fungerar: false, kommentar })}
                className={cn(btnPrimary, btnLiten, "mt-2")}
              >
                {skickar ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : null}
                {text(T.skickaNej)}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      {fel ? (
        <p role="alert" className="mt-2 text-[0.875rem] text-danger">
          {text(T.atgardFel)}
        </p>
      ) : null}
    </article>
  );
}

// ---------------------------------------------------------------------------
// Rutan
// ---------------------------------------------------------------------------

type Flik = "samtal" | "arenden";

export type HjalpRutaStart = {
  flik?: Flik;
  /** Kort som redan står i samtalet när rutan öppnas (förhandsvisningen). */
  kort?: HjalpKortLage[];
  /** En fråga som skickas direkt (förhandsvisningen). */
  fraga?: string;
  /** Läsrollen utan inloggning (förhandsvisningen). Annars avgör sessionen. */
  lasare?: boolean;
};

export function HjalpRuta({ onStang, start }: Readonly<{ onStang: () => void; start?: HjalpRutaStart }>) {
  const { text } = useLocale();
  const dashboard = useDashboard();
  const arLasare = start?.lasare ?? dashboard.arLasare;
  const rubrikId = useId();
  const rubrikRef = useRef<HTMLHeadingElement>(null);
  const [flikVal, setFlikVal] = useState<Flik>(start?.flik ?? "samtal");
  const [{ ids: kortIds, kort }, andraKortButik] = useHjalpKort(start);
  const { arenden, fel, vantar } = useHjalpArenden(true, true);
  const [monterad, setMonterad] = useState(false);

  useEffect(() => {
    setMonterad(true);
  }, []);

  useEffect(() => {
    if (monterad) rubrikRef.current?.focus();
  }, [monterad]);

  useEffect(() => {
    const vidTangent = (e: KeyboardEvent) => {
      if (e.key === "Escape") onStang();
    };
    document.addEventListener("keydown", vidTangent);
    return () => document.removeEventListener("keydown", vidTangent);
  }, [onStang]);

  const oppnaKort = useCallback(
    (lage: HjalpKortLage) => {
      const nyttId = crypto.randomUUID();
      andraKortButik((nu) => ({ ids: [...nu.ids, nyttId], kort: { ...nu.kort, [nyttId]: lage } }));
      setFlikVal("samtal");
    },
    [andraKortButik]
  );

  const andraKort = useCallback(
    (kortId: string, nytt: HjalpKortLage | null) => {
      // Ett avbrutet kort försvinner helt ur flödet, plats och allt, så att
      // tomt läge med startvalen kommer tillbaka när inget annat står där.
      if (!nytt || (nytt.typ === "fel" && nytt.steg === "avbruten")) {
        andraKortButik((nu) => utanKort(nu, kortId));
        return;
      }
      andraKortButik((nu) => ({ ...nu, kort: { ...nu.kort, [kortId]: nytt } }));
    },
    [andraKortButik]
  );

  const renderKort = useCallback(
    (kortId: string) => {
      const lage = kort[kortId];
      if (!lage) return null;
      if (lage.typ === "kunskap") {
        return <KunskapKort kort={lage} arLasare={arLasare} onAndra={(nytt) => andraKort(kortId, nytt)} />;
      }
      return (
        <FelKort
          kort={lage}
          arLasare={arLasare}
          onAndra={(nytt) => andraKort(kortId, nytt)}
          onVisaArenden={() => setFlikVal("arenden")}
        />
      );
    },
    [kort, arLasare, andraKort]
  );

  const vantande = (arenden ?? []).filter(vantarPaKund);
  const hjalpAv = fel === "hjalp_av";

  if (!monterad) return null;

  const ruta = (
    <div
      role="dialog"
      aria-modal="false"
      aria-labelledby={rubrikId}
      className="safe-top fixed inset-0 z-50 flex flex-col bg-paper text-ink lg:inset-auto lg:bottom-3 lg:left-[268px] lg:h-[min(46rem,calc(100dvh-1.5rem))] lg:w-[26rem] lg:overflow-hidden lg:rounded-card lg:border lg:border-ink/15 lg:shadow-lift"
    >
      <div className="flex items-start justify-between gap-3 px-4 pt-3">
        <div className="min-w-0">
          <h2 id={rubrikId} ref={rubrikRef} tabIndex={-1} className={cn(rubrikPanel, "outline-none")}>
            {text(T.rubrik)}
          </h2>
          {/* AI-upplysningen (AI-förordningen art. 50.1) syns under hela samtalet. */}
          <p className={meta}>{text(T.ai)}</p>
        </div>
        <button
          type="button"
          onClick={onStang}
          aria-label={text(T.stang)}
          className="focus-ring -mr-2 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-input text-ink-muted transition-colors hover:bg-paper2 hover:text-ink"
        >
          <X className="h-5 w-5" aria-hidden />
        </button>
      </div>

      <div role="tablist" aria-label={text(T.flikar)} className={cn(fliklista, "mt-1 px-4")}>
        {(["samtal", "arenden"] as const).map((namn) => (
          <button
            key={namn}
            type="button"
            role="tab"
            aria-selected={flikVal === namn}
            onClick={() => setFlikVal(namn)}
            className={cn(flik, flikVal === namn ? flikAktiv : flikInaktiv)}
          >
            {text(namn === "samtal" ? T.samtal : T.minaArenden)}
            {namn === "arenden" && vantar > 0 ? (
              <span className="num inline-flex min-w-[1.25rem] items-center justify-center rounded-full bg-ochre px-1.5 text-[0.75rem] font-semibold leading-5 text-ink">
                {vantar}
                <span className="sr-only"> {text(T.vantarPaDig)}</span>
              </span>
            ) : null}
          </button>
        ))}
      </div>

      <div role="tabpanel" className="flex min-h-0 flex-1 flex-col">
        {hjalpAv ? (
          <div className="px-4 py-4">
            <p className="rounded-input border border-ink/10 bg-paper2 px-4 py-3 text-[0.9375rem] text-ink-muted">
              {text(HJALP_AV_TEXT)}
            </p>
          </div>
        ) : (
          <>
          {/* Samtalet står kvar monterat under Mina ärenden, så att en fråga
              som pågår inte tappas när kunden byter flik. */}
          <div className={cn("min-h-0 flex-1 flex-col", flikVal === "samtal" ? "flex" : "hidden")}>
          <SupportChat
            hjalpMode
            layout="fyll"
            hjalpStartFraga={start?.fraga}
            hjalpKort={kortIds}
            renderHjalpKort={renderKort}
            hjalpFast={
              vantande.length ? (
                <div className="flex flex-col gap-3">
                  {vantande.map((a) => (
                    <ArendeKort key={a.id} arende={a} />
                  ))}
                </div>
              ) : null
            }
            hjalpVerktyg={
              <div className="mb-2 flex flex-wrap gap-1.5">
                <button type="button" onClick={() => oppnaKort(nyttKunskapskort())} className={cn(chip, chipInaktiv, "border border-ink/12")}>
                  {text(T.lar)}
                </button>
                <button type="button" onClick={() => oppnaKort(nyttFelkort())} className={cn(chip, chipInaktiv, "border border-ink/12")}>
                  {text(T.fel)}
                </button>
              </div>
            }
            hjalpTomt={({ fokusera }) => (
              <div className="flex min-h-full flex-col">
                <div className="m-auto flex max-w-sm flex-col items-center gap-4 py-2 text-center">
                  <p className="text-[0.9375rem] leading-6 text-ink-muted">{text(T.tomtRad)}</p>
                  <div className="flex w-full flex-col gap-2">
                    <button type="button" onClick={fokusera} className={btnSecondary}>
                      {text(T.fraga)}
                    </button>
                    <button type="button" onClick={() => oppnaKort(nyttKunskapskort())} className={btnSecondary}>
                      {text(T.lar)}
                    </button>
                    <button type="button" onClick={() => oppnaKort(nyttFelkort())} className={btnSecondary}>
                      {text(T.fel)}
                    </button>
                  </div>
                </div>
              </div>
            )}
          />
          </div>
          {flikVal === "arenden" ? (
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
            {arenden === null && fel === null ? (
              <p className={cn(meta, "flex items-center gap-2")}>
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                {text(T.laddar)}
              </p>
            ) : arenden === null ? (
              <p className="rounded-input border border-ink/10 bg-paper2 px-4 py-3 text-[0.9375rem] text-ink-muted">
                {text(T.listFel)}
              </p>
            ) : arenden.length === 0 ? (
              <p className="rounded-input border border-ink/10 bg-paper2 px-4 py-3 text-[0.9375rem] text-ink-muted">
                {text(T.inga)}
              </p>
            ) : (
              <div className="flex flex-col gap-3">
                {fel === "fel" ? <p className={meta}>{text(T.listFel)}</p> : null}
                {arenden.map((a) => (
                  <ArendeKort key={a.id} arende={a} />
                ))}
              </div>
            )}
          </div>
          ) : null}
          </>
        )}
      </div>
    </div>
  );

  return createPortal(ruta, document.body);
}
