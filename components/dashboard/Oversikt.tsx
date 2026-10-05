"use client";

import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { Badge, Rad, Radlista, SkeletonRows, btnLiten, btnSecondary, etikett as etikettKlass, meta } from "@/components/ui";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { createDemoSupportApi } from "@/lib/demo/support-inbox";
import { readJsonBody } from "@/lib/http/json";
import { type KorningsRad } from "@/components/leads/IrisKorningar";
import { Aktivitetsgraf, Andelsring, KpiKort, PipelineStapel, forandring, type Kpi, type Steg, type Vecka } from "@/components/dashboard/OversiktPaneler";
import { STATUS_ETIKETT } from "@/lib/prospekt";
import { useLocale, type Locale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Översikten — arbetsytans startsida för båda produkterna.
 *
 * ## Varför den finns
 *
 * `/dashboard` renderade tidigare agentens RÅA arbetsvy: discovery-formuläret
 * och bolagsregistret för leads, inkorgen för support. Sammanfattningen låg
 * som inställning på `/settings/arbetsyta`. Utfallet var mätbart i skärmdump:
 * inloggningen landade i "Inget här ännu", medan den enda vy som faktiskt
 * sammanfattade arbetsytan gick att nå först efter tre klick.
 *
 * Nu gäller det omvända. Startsidan svarar på "vad har hänt och vad väntar på
 * mig", arbetsvyerna ligger kvar på `/dashboard/leads` och `/dashboard/support`
 * och gör jobbet. Det är också därför `duoOnly` försvann ur lib/routes.ts: utan
 * de flikarna hade en enproduktskund inte kommit åt sin arbetsvy alls.
 *
 * ## Talen är riktiga
 *
 * Varje siffra här räknas ur kundens EGEN tenant, genom endpoints som redan
 * fanns och redan är tenant-skopade ur sessionen. Den gamla panelen visade
 * `297 skickade` och `842 000 kr` ur `lib/mock-data.ts` för varje kund, med
 * "exempeldata" i småtext under. En siffra man ändå inte får tro på är en
 * siffra som inte behöver stå där.
 *
 * Två följder av att datan är riktig, och båda är avsiktliga:
 *
 *  * **Tak skrivs ut.** Backenden svarar med de 100 senaste prospekten och de
 *    200 senaste ärendena. När listan ligger på taket säger raden det, i
 *    stället för att presentera ett sidantal som ett totalantal.
 *  * **Ett trasigt anrop tömmer inte vyn.** Varje hämtning är sin egen, och en
 *    ruta utan svar visar `—`. Alternativet — en tom sida när en av fem
 *    endpoints somnat — ser ut som att arbetsytan är tom.
 *
 * ## Register
 *
 * Operate mode, DESIGN.md App-familjen: fast rem-skala, täta rader, ingen
 * hero, inga reveals, ingen bild. Talen sätts i Geist med `tnum` — DESIGN.md
 * reserverar Fraunces för list- och stegnummer, inte för data i tiles. Ochre
 * bär bara tillstånd: det som väntar på dig, och det största värdet i en
 * fördelning.
 */

// -- Text ------------------------------------------------------------------

/** Platshållaren för en ruta utan svar. Tankstreck, inte em-streck (DESIGN.md § Copy). */
const TOM = "–";

const T = {
  attGora: { sv: "Att göra", en: "To do" },
  komigang: { sv: "Innan agenterna kan börja", en: "Before the agents can start" },
  ofullstandig: { sv: "Vissa siffror kunde inte hämtas.", en: "Some figures could not be loaded." },
  forsokIgen: { sv: "Försök igen", en: "Try again" },
  iDrift: { sv: "i drift", en: "running" },
  arbetsyta: { sv: "Arbetsyta", en: "Workspace" },
  agenten: { sv: "Agenten", en: "The agent" },
  jobbar: { sv: "Jobbar", en: "Working" },
  kunskapsbas: { sv: "Kunskapsbas", en: "Knowledge base" },
  senasteKorning: { sv: "Senaste körning", en: "Latest run" },
  saknarKontext: { sv: "Agenterna vet inte vad ni säljer.", en: "The agents don't know what you sell." },
  fyllKontext: { sv: "Fyll i affärskontexten", en: "Fill in the business context" },
  utkast: { sv: "Utkast", en: "Draft" },
  utanAmnesrad: { sv: "Utan ämnesrad", en: "No subject line" },
  oppnaGranskning: { sv: "Öppna Att göra", en: "Open To do" },
  prospekt: { sv: "Prospekt", en: "Prospects" },
  kundeInteHamtas: { sv: "kunde inte hämtas", en: "could not be loaded" },
  ingaExempel: { sv: "inga exempelbolag", en: "no example companies" },
  kvalificerade: { sv: "Kvalificerade", en: "Qualified" },
  ingenBedomning: { sv: "ingen bedömning ännu", en: "not assessed yet" },
  vantarPaDig: { sv: "Väntar på dig", en: "Waiting for you" },
  utkastIKon: { sv: "utkast i granskningskön", en: "drafts in the review queue" },
  konTom: { sv: "granskningskön är tom", en: "the review queue is empty" },
  korningar7: { sv: "Körningar 7 dgr", en: "Runs, 7 days" },
  ingaEskalerade: { sv: "inga steg eskalerade", en: "no steps escalated" },
  regler: { sv: "Regler", en: "Rules" },
  senasteArendet: { sv: "Senaste ärendet", en: "Latest ticket" },
  kbTom: { sv: "Kunskapsbasen är tom.", en: "The knowledge base is empty." },
  fyllKb: { sv: "Fyll kunskapsbasen", en: "Fill the knowledge base" },
  utanAmne: { sv: "(utan ämne)", en: "(no subject)" },
  granskaUtkasten: { sv: "Granska utkasten", en: "Review the drafts" },
  arenden: { sv: "Ärenden", en: "Tickets" },
  iInkorgen: { sv: "i inkorgen", en: "in the inbox" },
  klaradeSjalv: { sv: "Klarade själv", en: "Handled by the agents" },
  ingaArenden: { sv: "inga ärenden ännu", en: "no tickets yet" },
  utkastAttGodkanna: { sv: "utkast att godkänna", en: "drafts to approve" },
  ingetUtkast: { sv: "inget utkast att granska", en: "no drafts to review" },
  eskalerade: { sv: "Eskalerade", en: "Escalated" },
  vadArendena: { sv: "Vad ärendena handlar om", en: "What the tickets are about" },
  ingaKlassificerade: { sv: "Inga klassificerade ärenden ännu.", en: "No classified tickets yet." },
  senasteArendena: { sv: "Senaste ärendena", en: "Latest tickets" },
  oppnaInkorgen: { sv: "Öppna inkorgen", en: "Open the inbox" },
  inkorgenTom: { sv: "Inkorgen är tom.", en: "The inbox is empty." }
} satisfies Record<string, Localized>;

// -- Hämtning --------------------------------------------------------------

type Hamtare = <T>(path: string) => Promise<T | null>;

/**
 * En hämtare per vy. `demo` byter ut backend-anropen mot exempeldata i
 * webbläsaren, precis som components/snajp/Dashboard.tsx redan gör: den
 * inloggade vägen går genom requireSnajpTenant(), som härleder tenanten ur
 * sessionen och saknar demo-väg med flit.
 *
 * Fel sväljs och blir `null`. Anroparen visar `—` för den rutan; se
 * modulens docstring om varför en död endpoint inte får tömma sidan.
 */
function useHamtare(demo: boolean): Hamtare {
  const [demoApi] = useState(() => (demo ? createDemoSupportApi() : null));

  return useCallback(
    async <T,>(path: string): Promise<T | null> => {
      try {
        if (demoApi) {
          // Översiktens egna vägar först; kundtjänstens demo-API tar resten.
          const eget = demoOversiktSvar(path);
          if (eget !== undefined) return eget as T;
          return (await demoApi<T>(path)) ?? null;
        }
        const response = await fetch(`/api/snajp-support${path}`, { cache: "no-store" });
        if (!response.ok) return null;
        const kropp = await readJsonBody<T & { offline?: boolean }>(response);
        if (!kropp || kropp.offline) return null;
        return kropp;
      } catch {
        return null;
      }
    },
    [demoApi]
  );
}

/** "3 dagar sedan". Tom sträng in ger tankstreck ut. */
function sedan(iso: string | null | undefined, locale: Locale): string {
  if (!iso) return TOM;
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms)) return TOM;
  const minuter = Math.floor(ms / 60000);
  if (minuter < 1) return { sv: "nyss", en: "just now" }[locale];
  if (minuter < 60) return { sv: `${minuter} min sedan`, en: `${minuter} min ago` }[locale];
  const timmar = Math.floor(minuter / 60);
  if (timmar < 24) return { sv: `${timmar} h sedan`, en: `${timmar} h ago` }[locale];
  const dagar = Math.floor(timmar / 24);
  if (dagar === 1) return { sv: "i går", en: "yesterday" }[locale];
  return { sv: `${dagar} dagar sedan`, en: `${dagar} days ago` }[locale];
}

function andel(del: number, av: number, locale: Locale): string {
  if (!av) return TOM;
  return new Intl.NumberFormat(locale === "en" ? "en-GB" : "sv-SE", {
    style: "percent",
    maximumFractionDigits: 0
  }).format(del / av);
}

// -- Delade byggstenar -----------------------------------------------------

type Tillstand = { etikett: string; varde: string; larm?: boolean; drift?: boolean };

/**
 * Raden överst: vad agenten vet och vad den får göra, på en rad.
 *
 * Den finns för att båda talen under är meningslösa utan den. Noll ärenden
 * besvarade betyder en sak när kunskapsbasen har 40 dokument och en helt annan
 * när den är tom, och den skillnaden syntes ingenstans tidigare.
 */
function Tillstandsrad({ poster }: Readonly<{ poster: Tillstand[] }>) {
  const { text } = useLocale();
  return (
    <dl className="grid gap-x-8 gap-y-4 border-y border-ink/15 py-4 sm:grid-cols-2 lg:grid-cols-4">
      {poster.map((post) => (
        <div key={post.etikett} className="min-w-0">
          <dt className={etikettKlass}>{post.etikett}</dt>
          <dd
            className={cn(
              "mt-1.5 flex items-center gap-2 truncate text-[0.9375rem]",
              post.larm ? "font-semibold text-ink" : "text-ink-muted"
            )}
            title={post.varde}
          >
            {/* Prickens jobb, inte textfärgens. Ochre som TEXT på papper mäter
                1,96:1 — under golvet oavsett grad, eftersom accenten ligger på
                0.74 i ljushet och pappret på 0.965. En form bär ingen text och
                har därför inget kontrastkrav; se DESIGN.md om att mäta med
                texten dold. */}
            {post.larm ? (
              <span className="h-2 w-2 shrink-0 rounded-full bg-ochre" aria-hidden />
            ) : null}
            {post.varde}
            {/* Grön prick EFTER värdet, inte före: den säger "det här är i
                drift" om raden den står på, och en markör som föregår sitt
                värde läses som en punktlista. Färgen bär ingen text, så den
                har inget kontrastkrav — men den behöver ett tillgängligt namn,
                annars är "Jobbar" med en osynlig prick allt en skärmläsare
                får. */}
            {post.drift ? (
              <span className="ml-1.5 inline-flex shrink-0 items-center">
                <span className="h-2 w-2 rounded-full bg-moss" aria-hidden />
                <span className="sr-only">{text(T.iDrift)}</span>
              </span>
            ) : null}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function Sektion({
  rubrik,
  bredvid,
  children
}: Readonly<{ rubrik: string; bredvid?: React.ReactNode; children: React.ReactNode }>) {
  return (
    <section>
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <h2 className="text-[1.0625rem] font-semibold tracking-[-0.01em]">{rubrik}</h2>
        {bredvid}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

/**
 * Fördelning som ruled lista med stapel.
 *
 * Den STÖRSTA stapeln är ochre, resten ink. Det är inte dekoration: färgen
 * pekar ut vilket värde som leder, vilket är hela frågan man ställer till en
 * fördelning. Alla staplar i accent hade varit en tapet.
 */
function Stapellista({
  rader,
  tomtext
}: Readonly<{ rader: [string, number][]; tomtext: string }>) {
  if (rader.length === 0) {
    return <p className="max-w-[60ch] text-[0.875rem] leading-6 text-ink-subtle">{tomtext}</p>;
  }
  const varden = rader.map(([, tal]) => tal);
  const storst = Math.max(...varden);
  // Ochre pekar ut vilket tal som LEDER. Är alla lika finns ingen ledare, och
  // att färga varje stapel hade gjort accenten till en tapet i stället för till
  // information — uppmätt i skärmdump: fem lika stora ochre staplar i rad.
  const harLedare = storst > Math.min(...varden);
  // Radlista bär hårlinjerna; varje rad har SAMMA deklarerade spann
  // (etikett 6, stapel 4, tal 2), så kolumnerna står stilla oavsett
  // hur lång en etikett är.
  return (
    <Radlista>
      {rader.map(([etikett, tal]) => (
        <Rad key={etikett} className="grid grid-cols-12 items-center gap-x-4">
          <span className="col-span-6 truncate text-[0.875rem]" title={etikett}>
            {etikett}
          </span>
          <span className="col-span-4">
            <span className="block h-1.5 overflow-hidden rounded-full bg-ink/8">
              <span
                className={cn(
                  "block h-full rounded-full",
                  harLedare && tal === storst ? "bg-ochre" : "bg-ink/30"
                )}
                style={{ width: `${Math.max(4, Math.round((tal / storst) * 100))}%` }}
              />
            </span>
          </span>
          <span className="num col-span-2 text-right text-[0.875rem] tabular-nums text-ink-muted">
            {tal}
          </span>
        </Rad>
      ))}
    </Radlista>
  );
}

type AttGoraRad = { id: string; rubrik: string; under: string; meta?: string; href?: string };

/**
 * Det enda blocket på sidan som är HANDLING och inte information — och sedan
 * 2026-09-20 sidans bärande yta: det står FÖRE nyckeltalen och bär sin egen
 * rubrik, med antalet i klartext ("2 utkast väntar på dig") i stället för ett
 * generiskt "Att göra" utanför kortet.
 *
 * Ligger i tonal inversion när kön inte är tom — sidans enda, och den betyder
 * "du måste göra något". Är kön tom renderas INGENTING (2026-09-21, på
 * begäran): rutan "Inga utkast väntar." var ett tomt kort mitt på sidan, och
 * en kö utan poster behöver inte meddela att den är tom — nyckeltalen under
 * säger redan läget.
 *
 * Varje rad är en länk till samma kö som knappen — kortet ska gå att agera på
 * var man än träffar det, inte bara i nedre vänstra hörnet.
 */
function AttGora({
  rader,
  href,
  knapp
}: Readonly<{ rader: AttGoraRad[]; href: string; knapp: string }>) {
  const { text } = useLocale();
  if (rader.length === 0) return null;
  const fler = rader.length - 5;
  // Papper med hårlinjer, inte en mörk platta (2026-10-03): railen är appens
  // enda tonala inversion (DESIGN.md § Macrostructure, App). Kön markeras i
  // stället av ochre-linjen överst och antalet i rubriken.
  return (
    <section aria-label={text(T.attGora)} className="border-t-2 border-ochre">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 py-4">
        <h2 className="text-[1.125rem] font-semibold tracking-[-0.01em]">
          {rader.length === 1
            ? text({ sv: "1 sak väntar på dig", en: "1 item waiting for you" })
            : text({
                sv: `${rader.length} saker väntar på dig`,
                en: `${rader.length} items waiting for you`
              })}
        </h2>
        <Link href={href} className={cn(btnSecondary, btnLiten)}>
          {knapp}
        </Link>
      </div>
      <ul className="divide-y divide-ink/12 border-y border-ink/12">
        {rader.slice(0, 5).map((rad) => (
          <li key={rad.id}>
            <Link
              href={rad.href ?? href}
              className="focus-ring grid grid-cols-12 gap-x-4 rounded-input px-1 py-2.5 text-ink transition-colors hover:bg-paper2/60"
            >
              <span className="col-span-12 min-w-0 sm:col-span-8">
                <span className="block truncate text-[0.9375rem] font-medium">{rad.rubrik}</span>
                <span className="mt-0.5 block truncate text-[0.8125rem] text-ink-subtle">{rad.under}</span>
              </span>
              <span className="col-span-12 mt-1 truncate text-[0.8125rem] text-ink-muted sm:col-span-4 sm:mt-0 sm:self-center sm:text-right">
                {rad.meta ?? ""}
              </span>
            </Link>
          </li>
        ))}
      </ul>
      {fler > 0 ? (
        <p className="mt-3 text-[0.8125rem] text-ink-subtle">
          {fler === 1
            ? text({ sv: "1 till i kön.", en: "1 more in the queue." })
            : text({ sv: `${fler} till i kön.`, en: `${fler} more in the queue.` })}
        </p>
      ) : null}
    </section>
  );
}

/**
 * Vad som saknas innan agenten kan göra sitt jobb.
 *
 * Den här ersätter det gamla tomläget, som var en HEL SIDA i stället för en
 * rad: `variant === "fresh"` kortslöt startsidan till "Inget här ännu" och
 * dolde varenda siffra bakom en knapp. Att sonden dessutom frågade en tabell
 * ingen skriver till gjorde att den grenen visades för varje kund, för alltid
 * (se lib/data/dashboard.ts).
 *
 * Nu: siffrorna står kvar, och det som fattas står ovanför dem. Blocket
 * försvinner av sig självt när underlaget finns — till skillnad från en tom
 * sida, som inte kan visa att den blivit mindre tom.
 *
 * Papper och inte bläck: den tonala inversionen är reserverad för ATT GÖRA,
 * alltså arbete som väntar. Det här är uppstart, inte en kö.
 */
function Komigang({ rader }: Readonly<{ rader: { text: string; href: string; knapp: string }[] }>) {
  const { text } = useLocale();
  if (rader.length === 0) return null;
  // Ingen färgad kantlist på ena sidan. Den läser som ett AI-manér, och
  // detektorn namnger den ("side-tab accent border"). Ochre bär larmet med
  // samma prick som tillståndsraden — ett tecken på ytan, inte två.
  return (
    <section aria-labelledby="komigang" className="rounded-card bg-paper2/60 p-5 md:p-6">
      <h2
        id="komigang"
        className="flex items-center gap-2.5 text-[1.0625rem] font-semibold tracking-[-0.01em]"
      >
        <span className="h-2 w-2 shrink-0 rounded-full bg-ochre" aria-hidden />
        {text(T.komigang)}
      </h2>
      <ul className="mt-4 grid gap-4">
        {rader.map((rad) => (
          <li key={rad.href} className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
            <p className="max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">{rad.text}</p>
            <Link href={rad.href} className={cn(btnSecondary, "shrink-0")}>
              {rad.knapp}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * Skalet: skelett medan det laddar, en ärlig rad när något inte gick, och en
 * uppdateringsknapp.
 *
 * Skelett och inte spinner — Operate-läget säger det, och skälet är att en
 * spinner mitt i innehållet inte visar VAD som kommer. Felraden fäller inte
 * sidan: rutorna som fick svar står kvar, och den som inte fick visar `—`.
 */
function OversiktShell({
  laddar,
  ofullstandig,
  uppdatera,
  children
}: Readonly<{
  laddar: boolean;
  ofullstandig: boolean;
  uppdatera: () => void;
  children: React.ReactNode;
}>) {
  const [uppdaterar, setUppdaterar] = useState(false);
  const { text } = useLocale();

  if (laddar) {
    return (
      <div className="space-y-10" aria-busy="true">
        <div className="h-16 animate-pulse rounded-card bg-ink/[0.055]" />
        <div className="grid grid-cols-2 gap-6 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-28 animate-pulse rounded-card bg-ink/[0.055]" />
          ))}
        </div>
        <SkeletonRows />
      </div>
    );
  }

  return (
    <div className="space-y-12">
      {ofullstandig ? (
        <p
          role="status"
          className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-card bg-paper2/60 px-4 py-3 text-[0.875rem] text-ink-muted"
        >
          <AlertTriangle className="h-4 w-4 shrink-0 text-warning" aria-hidden />
          {text(T.ofullstandig)}
          <button
            type="button"
            disabled={uppdaterar}
            onClick={() => {
              setUppdaterar(true);
              uppdatera();
              // Knappen släpps när nästa rendering kommer med nya siffror.
              window.setTimeout(() => setUppdaterar(false), 1200);
            }}
            className={cn(btnSecondary, "ml-auto min-h-10 px-4 text-[0.875rem]")}
          >
            {uppdaterar ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <RefreshCw className="h-4 w-4" aria-hidden />
            )}
            {text(T.forsokIgen)}
          </button>
        </p>
      ) : null}
      {children}
    </div>
  );
}

// -- Översikten (Snajp Suite 2026-10-03) -----------------------------------
//
// EN översikt för alla agenter arbetsytan har, i stället för en leadsdel och
// en kundtjänstdel staplade på varandra. Ordningen är Antons beställning:
// nyckeltalen överst, sedan det som väntar på dig och pipelinen, sist läget.
// Före 2026-10-03 började sidan med två datalösa länkkort ("Gemensam
// översikt") och kundtjänstens tal stod under hela leadsdelen.
//
// Varje tal är räknat ur kundens egen tenant, och en agent arbetsytan inte har
// syns inte alls (ett tal som alltid är noll är brus, inte information).

type Prospekt = {
  id: string;
  company_name?: string | null;
  ort?: string | null;
  status?: string | null;
  origin?: string | null;
  created_at?: string | null;
  niva?: "A" | "B" | "C" | null;
  score_total?: number | null;
  webbrevision?: { modernitet?: number | null } | null;
};
type Koartikel = {
  id: string;
  company_name?: string | null;
  prospect_email?: string | null;
  subject?: string | null;
  scheduled_at?: string | null;
};
/** `missing` är kontextdokument agenten saknar — se leads/onboarding_state.py. */
type Onboarding = { complete?: boolean; missing?: string[] };
type Arende = {
  id: string;
  from_email: string;
  from_name?: string | null;
  subject: string;
  received_at: string;
  status: string;
};
type Regel = { category: string; label: string; mode: "auto" | "draft" | "escalate" };

/** Backendens tak för inkorgslistan. Skrivs ut när listan ligger på det. */
const ARENDETAK = 200;
type Data = {
  prospekt: Prospekt[] | null;
  ko: Koartikel[] | null;
  korningar: KorningsRad[] | null;
  onboarding: Onboarding | null;
  arenden: Arende[] | null;
  fack: Record<string, number> | null;
  regler: Regel[] | null;
  kbAntal: number | null;
  veckor: Vecka[] | null;
};

/** Perioden som nyckeltalen räknar över, i veckor. Jämförs med lika lång period före. */
const PERIODER = [4, 12] as const;
type Period = (typeof PERIODER)[number];

/** Pipelinens steg i arbetsflödets ordning (Spärrad och Förlorad står utanför). */
const PIPELINE: string[] = ["new", "researching", "ready", "contacted", "replied", "meeting", "won"];

function summa(veckor: Vecka[], nyckel: keyof Vecka, fran: number, till: number): number {
  return veckor.slice(fran, till).reduce((s, v) => s + Number(v[nyckel] ?? 0), 0);
}

function halsning(locale: Locale): string {
  const h = new Date().getHours();
  const del = h < 10 ? { sv: "God morgon", en: "Good morning" } : h < 17 ? { sv: "Hej", en: "Hello" } : { sv: "God kväll", en: "Good evening" };
  return del[locale];
}

export function Oversikten({ demo = false }: Readonly<{ demo?: boolean }>) {
  const hamta = useHamtare(demo);
  const vag = useArbetsvag();
  const { products } = useDashboard();
  const { locale, text } = useLocale();
  const leads = products.includes("leads");
  const support = products.includes("support");
  const [laddar, setLaddar] = useState(true);
  const [nyckel, setNyckel] = useState(0);
  const [d, setD] = useState<Data | null>(null);
  const [period, setPeriod] = useState<Period>(4);

  useEffect(() => {
    let avbruten = false;
    setLaddar(true);
    const ingen = Promise.resolve(null);
    // Oberoende hämtningar. En som faller tar inte med sig de andra. Talen
    // över tid räknas på servern (/analytics/weekly), så inget listtak ljuger.
    void Promise.all([
      leads ? hamta<{ prospects?: Prospekt[] }>("/leads/prospects?limit=500") : ingen,
      leads ? hamta<{ items?: Koartikel[] }>("/leads/queue") : ingen,
      leads ? hamta<{ korningar?: KorningsRad[] }>("/leads/korningar?limit=5") : ingen,
      leads ? hamta<Onboarding>("/leads/onboarding/status") : ingen,
      support
        ? hamta<{ emails?: Arende[]; category_counts?: Record<string, number> }>(`/inbox?limit=${ARENDETAK}`)
        : ingen,
      support ? hamta<{ rules?: Regel[] }>("/rules") : ingen,
      hamta<{ articles?: unknown[] }>("/kb"),
      hamta<{ weeks?: Vecka[] }>("/analytics/weekly?weeks=24")
    ]).then(([p, q, k, o, i, r, kb, w]) => {
      if (avbruten) return;
      setD({
        prospekt: p ? (p.prospects ?? []) : null,
        ko: q ? (q.items ?? []) : null,
        // Demon har ingen jobbliggare: tom lista, inte "kunde inte hämtas".
        korningar: k ? (k.korningar ?? []) : demo ? [] : null,
        onboarding: o,
        arenden: i ? (i.emails ?? []) : null,
        fack: i ? (i.category_counts ?? {}) : null,
        regler: r ? (r.rules ?? []) : null,
        kbAntal: kb ? (kb.articles?.length ?? 0) : null,
        veckor: w ? (w.weeks ?? []) : null
      });
      setLaddar(false);
    });
    return () => {
      avbruten = true;
    };
  }, [hamta, nyckel, leads, support, demo]);

  // En pågående körning uppdateras medan man tittar, utan att sidan laddar om.
  const pagaendeKorning = d?.korningar?.find((k) => k.status === "queued" || k.status === "processing" || (k.korning && !k.korning.klar && k.status !== "failed"));
  useEffect(() => {
    if (!pagaendeKorning || demo) return;
    const id = window.setInterval(async () => {
      const k = await hamta<{ korningar?: KorningsRad[] }>("/leads/korningar?limit=5");
      if (k?.korningar) setD((forra) => (forra ? { ...forra, korningar: k.korningar ?? [] } : forra));
    }, 5000);
    return () => window.clearInterval(id);
  }, [pagaendeKorning, hamta, demo]);

  if (!d) {
    return <OversiktShell laddar ofullstandig={false} uppdatera={() => undefined}>{null}</OversiktShell>;
  }

  const prospekt = (d.prospekt ?? []).filter((p) => p.origin !== "example");
  const veckor = d.veckor ?? [];
  const n = veckor.length;
  const nu = (k: keyof Vecka) => summa(veckor, k, Math.max(0, n - period), n);
  const forra = (k: keyof Vecka) => summa(veckor, k, Math.max(0, n - 2 * period), Math.max(0, n - period));
  const serie = (k: keyof Vecka) => veckor.slice(-Math.max(period, 8)).map((v) => Number(v[k] ?? 0));
  const perioden: Localized = {
    sv: `de ${period} veckorna före`,
    en: `the ${period} weeks before`
  };
  const detalj: Localized = { sv: `senaste ${period} veckorna`, en: `last ${period} weeks` };

  const arenden = d.arenden ?? [];
  const vantarSupport = arenden.filter((a) => a.status === "awaiting_approval");
  const eskalerade = arenden.filter((a) => a.status === "escalated");
  const fackNamn = new Map((d.regler ?? []).map((r) => [r.category, r.label]));
  const losta = nu("resolved");
  const arendenNu = nu("tickets");

  const ofullstandig =
    (leads && (d.prospekt === null || d.ko === null || d.korningar === null)) ||
    (support && (d.arenden === null || d.regler === null)) ||
    d.kbAntal === null ||
    d.veckor === null;

  // Allt som väntar på ett beslut, från alla agenter, nyast först.
  const vantar: (AttGoraRad & { nar: string })[] = [
    ...(d.ko ?? []).map((post) => ({
      id: `iris-${post.id}`,
      rubrik: post.company_name ?? post.prospect_email ?? text(T.utkast),
      under: post.subject ?? text(T.utanAmnesrad),
      meta: text({ sv: "Iris · utkast", en: "Iris · draft" }),
      href: vag("/dashboard/leads?vy=utkast"),
      nar: post.scheduled_at ?? ""
    })),
    ...[...eskalerade, ...vantarSupport].map((a) => ({
      id: `support-${a.id}`,
      rubrik: a.subject || text(T.utanAmne),
      under: a.from_name ? `${a.from_name} · ${a.from_email}` : a.from_email,
      meta:
        a.status === "escalated"
          ? text({ sv: "Kundtjänst · eskalerat", en: "Customer service · escalated" })
          : text({ sv: "Kundtjänst · utkast", en: "Customer service · draft" }),
      href: vag("/dashboard/att-gora"),
      nar: a.received_at
    }))
  ].sort((a, b) => b.nar.localeCompare(a.nar));

  // Fyra nyckeltal, valda efter vilka agenter arbetsytan har.
  const kpier: Kpi[] = [];
  if (leads) {
    kpier.push(
      { id: "nya", etikett: { sv: "Nya leads", en: "New leads" }, varde: nu("new_leads"), forandring: forandring(nu("new_leads"), forra("new_leads")), serie: serie("new_leads"), detalj, href: vag("/dashboard/leads") },
      { id: "svar", etikett: { sv: "Svar från leads", en: "Replies from leads" }, varde: nu("replies"), forandring: forandring(nu("replies"), forra("replies")), serie: serie("replies"), detalj, href: vag("/dashboard/leads?vy=inkorg") }
    );
  }
  if (support) {
    kpier.push(
      { id: "arenden", etikett: { sv: "Ärenden", en: "Cases" }, varde: arendenNu, forandring: forandring(arendenNu, forra("tickets")), serie: serie("tickets"), detalj, href: vag("/dashboard/support") },
      {
        id: "losta",
        etikett: { sv: "Lösta av Snajp", en: "Resolved by Snajp" },
        varde: losta,
        visning: arendenNu ? andel(losta, arendenNu, locale) : TOM,
        forandring: forandring(losta, forra("resolved")),
        serie: serie("resolved"),
        detalj: { sv: `${losta} av ${arendenNu} ärenden`, en: `${losta} of ${arendenNu} cases` }
      }
    );
  }
  if (leads && !support) {
    kpier.push(
      { id: "skickat", etikett: { sv: "Skickade mejl", en: "Emails sent" }, varde: nu("sent"), forandring: forandring(nu("sent"), forra("sent")), serie: serie("sent"), detalj },
      {
        id: "moten",
        etikett: { sv: "Möten", en: "Meetings" },
        varde: prospekt.filter((p) => p.status === "meeting").length,
        detalj: { sv: `${prospekt.filter((p) => p.status === "won").length} vunna`, en: `${prospekt.filter((p) => p.status === "won").length} won` }
      }
    );
  }
  if (support && !leads) {
    kpier.push(
      { id: "eskalerade", etikett: { sv: "Eskalerade", en: "Escalated" }, varde: nu("escalated"), forandring: forandring(nu("escalated"), forra("escalated")), battre: "ner", serie: serie("escalated"), detalj },
      { id: "vantar", etikett: { sv: "Väntar på dig", en: "Waiting for you" }, varde: vantar.length, larm: vantar.length > 0, detalj: { sv: "utkast och eskaleringar", en: "drafts and escalations" }, href: vag("/dashboard/att-gora") }
    );
  }

  // Sammanfattningen: vad Snajp gjorde, i en mening med riktiga tal.
  const delar: string[] = [];
  if (leads) delar.push(text({ sv: `Iris hittade ${nu("new_leads")} leads`, en: `Iris found ${nu("new_leads")} leads` }));
  if (support && arendenNu) delar.push(text({ sv: `kundtjänsten löste ${losta} av ${arendenNu} ärenden själv`, en: `customer service resolved ${losta} of ${arendenNu} cases on its own` }));
  const sammanfattning = delar.length
    ? `${halsning(locale)}. ${text({ sv: `De senaste ${period} veckorna`, en: `In the last ${period} weeks` })} ${delar.join(text({ sv: " och ", en: " and " }))}.`
    : `${halsning(locale)}.`;

  const steg: Steg[] = PIPELINE.map((s) => ({
    status: s,
    etikett: STATUS_ETIKETT[s],
    antal: prospekt.filter((p) => (p.status ?? "new") === s).length
  }));

  const heta = prospekt
    .filter((p) => (p.niva === "A" || p.niva === "B") && typeof p.score_total === "number" && !["won", "lost", "suppressed"].includes(p.status ?? ""))
    .sort((a, b) => (b.score_total ?? 0) - (a.score_total ?? 0))
    .slice(0, 5);

  const aktivitet: Parameters<typeof Aktivitetsgraf>[0]["serier"] = leads
    ? [
        { nyckel: "new_leads", etikett: { sv: "Nya leads", en: "New leads" }, ton: "chart-ochre" },
        { nyckel: "replies", etikett: { sv: "Svar från leads", en: "Replies from leads" }, ton: "chart-blue" }
      ]
    : [
        { nyckel: "tickets", etikett: { sv: "Ärenden", en: "Cases" }, ton: "chart-blue" },
        { nyckel: "resolved", etikett: { sv: "Lösta av Snajp", en: "Resolved by Snajp" }, ton: "chart-ochre" }
      ];

  return (
    <OversiktShell laddar={laddar} ofullstandig={ofullstandig} uppdatera={() => setNyckel((x) => x + 1)}>
      {/* Huvudet: vad som hänt, i en mening, och perioden talen räknar över. */}
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <p className="max-w-[60ch] text-[1.0625rem] leading-7 text-ink">{sammanfattning}</p>
        <div role="group" aria-label={text({ sv: "Period", en: "Period" })} className="inline-flex rounded-input border border-ink/12 p-0.5">
          {PERIODER.map((p) => (
            <button
              key={p}
              type="button"
              aria-pressed={period === p}
              onClick={() => setPeriod(p)}
              className={cn(
                "focus-ring min-h-9 rounded-[6px] px-3 text-[0.8125rem] font-medium transition-colors",
                period === p ? "bg-ink text-paper" : "text-ink-muted hover:text-ink"
              )}
            >
              {text({ sv: `${p} veckor`, en: `${p} weeks` })}
            </button>
          ))}
        </div>
      </div>

      {/* Nyckeltalen: fyra kort, Upsales-mönstret (tal, förändring, sparkline). */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpier.slice(0, 4).map((k) => (
          <KpiKort key={k.id} kpi={k} perioden={perioden} />
        ))}
      </div>

      <Komigang
        rader={[
          ...(d.onboarding?.missing?.includes("product_marketing")
            ? [{ text: text(T.saknarKontext), href: vag("/settings/affarskontext"), knapp: text(T.fyllKontext) }]
            : []),
          ...(support && d.kbAntal === 0
            ? [{ text: text(T.kbTom), href: vag("/settings/kunskapsbas"), knapp: text(T.fyllKb) }]
            : [])
        ]}
      />

      <AttGora rader={vantar} href={vag("/dashboard/att-gora")} knapp={text(T.oppnaGranskning)} />

      <div className="grid gap-10 lg:grid-cols-12">
        <div className="lg:col-span-8">
          <Sektion rubrik={text({ sv: "Aktivitet per vecka", en: "Activity per week" })}>
            {veckor.length ? (
              <Aktivitetsgraf veckor={veckor.slice(-12)} serier={aktivitet} />
            ) : (
              <p className="text-[0.875rem] text-ink-subtle">{text({ sv: "Ingen aktivitet att visa än.", en: "No activity to show yet." })}</p>
            )}
          </Sektion>
        </div>
        <div className="lg:col-span-4">
          {leads ? (
            <IrisLive rad={pagaendeKorning ?? d.korningar?.[0] ?? null} pagar={Boolean(pagaendeKorning)} href={vag("/dashboard/leads?vy=korningar")} korHref={vag("/dashboard/leads")} />
          ) : (
            <Sektion rubrik={text(T.vadArendena)}>
              <Stapellista
                rader={Object.entries(d.fack ?? {})
                  .filter(([, antal]) => antal > 0)
                  .map(([kod, antal]) => [fackNamn.get(kod) ?? kod, antal] as [string, number])
                  .sort((a, b) => b[1] - a[1])}
                tomtext={text(T.ingaKlassificerade)}
              />
            </Sektion>
          )}
        </div>
      </div>

      {leads ? (
        <Sektion
          rubrik={text({ sv: "Pipeline", en: "Pipeline" })}
          bredvid={
            <div className="flex flex-wrap items-baseline gap-x-5 gap-y-1">
              {/* CRM-kundlistan (migration 098): befintliga kunder som Iris och
                  listorna hoppar över. Landar öppen i Leads › Listor. */}
              <Lank href={vag("/dashboard/leads?vy=listor&crm=1")}>
                {text({ sv: "Ladda upp befintlig CRM-kundlista", en: "Upload existing CRM customer list" })}
              </Lank>
              <Lank href={vag("/dashboard/leads")}>{text({ sv: "Öppna Leads", en: "Open Leads" })}</Lank>
            </div>
          }
        >
          <PipelineStapel steg={steg} href={vag("/dashboard/leads")} />
        </Sektion>
      ) : null}

      <div className="grid gap-10 lg:grid-cols-2">
        {leads ? (
          <Sektion
            rubrik={text({ sv: "Hetaste leads", en: "Hottest leads" })}
            bredvid={<Lank href={vag("/dashboard/leads")}>{text({ sv: "Alla leads", en: "All leads" })}</Lank>}
          >
            {heta.length ? (
              <ul className="divide-y divide-ink/10 border-y border-ink/15">
                {heta.map((p) => (
                  <li key={p.id}>
                    <Link
                      href={vag(`/dashboard/leads?lead=${encodeURIComponent(p.id)}`)}
                      className="focus-ring grid grid-cols-12 items-center gap-x-4 rounded-input px-1 py-2.5 hover:bg-paper2/60"
                    >
                      <span className="col-span-7 min-w-0">
                        <span className="block truncate text-[0.9375rem] font-medium text-ink">{p.company_name}</span>
                        <span className={cn(meta, "block truncate")}>{[p.ort, text(STATUS_ETIKETT[p.status ?? "new"] ?? { sv: "Ny", en: "New" })].filter(Boolean).join(" · ")}</span>
                      </span>
                      <span className="col-span-3 justify-self-end">
                        {typeof p.webbrevision?.modernitet === "number" ? (
                          <Badge tone={p.webbrevision.modernitet <= 4 ? "good" : "neutral"}>
                            <span className="sr-only">{text({ sv: "Webbplatsens modernitet", en: "Website modernity" })} </span>
                            {p.webbrevision.modernitet}/10
                          </Badge>
                        ) : null}
                      </span>
                      <span className="num col-span-2 text-right text-[1.0625rem] font-semibold tabular-nums text-ink">{p.score_total}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[0.875rem] text-ink-subtle">
                {text({ sv: "Inga bedömda leads än. Kör Iris så rangordnas de här.", en: "No assessed leads yet. Run Iris and they are ranked here." })}
              </p>
            )}
          </Sektion>
        ) : null}

        {support ? (
          <Sektion
            rubrik={text({ sv: "Kundtjänstens läge", en: "Customer service status" })}
            bredvid={<Lank href={vag("/dashboard/support")}>{text(T.oppnaInkorgen)}</Lank>}
          >
            <div className="flex flex-wrap items-start gap-6">
              <Andelsring
                andel={arendenNu ? losta / arendenNu : null}
                etikett={text({ sv: `Lösta av Snajp: ${andel(losta, arendenNu, locale)}`, en: `Resolved by Snajp: ${andel(losta, arendenNu, locale)}` })}
              />
              <div className="min-w-[14rem] flex-1">
                <Stapellista
                  rader={Object.entries(d.fack ?? {})
                    .filter(([, antal]) => antal > 0)
                    .map(([kod, antal]) => [fackNamn.get(kod) ?? kod, antal] as [string, number])
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 5)}
                  tomtext={text(T.ingaKlassificerade)}
                />
              </div>
            </div>
          </Sektion>
        ) : null}
      </div>

      {/* Läget sist: vad agenterna vet. */}
      <Tillstandsrad
        poster={[
          ...(leads ? [{ etikett: text(T.agenten), varde: text(T.jobbar), drift: true }] : []),
          {
            etikett: text(T.kunskapsbas),
            varde: d.kbAntal === null ? TOM : text({ sv: `${d.kbAntal} dokument`, en: `${d.kbAntal} documents` }),
            larm: d.kbAntal === 0
          },
          ...(leads
            ? [{ etikett: text(T.senasteKorning), varde: d.korningar === null ? TOM : sedan(d.korningar[0]?.created_at, locale) }]
            : []),
          ...(support
            ? [{ etikett: text(T.senasteArendet), varde: d.arenden === null ? TOM : sedan(arenden[0]?.received_at, locale) }]
            : [])
        ]}
      />
    </OversiktShell>
  );
}

/**
 * Iris just nu: en pågående körning med förloppsstapel (levererade av målet),
 * annars den senaste och vägen till nästa. Pollas medan den pågår.
 */
function IrisLive({
  rad,
  pagar,
  href,
  korHref
}: Readonly<{ rad: KorningsRad | null; pagar: boolean; href: string; korHref: string }>) {
  const { locale, text } = useLocale();
  const k = rad?.korning;
  const mal = k?.mal ?? 0;
  const levererade = k?.levererade ?? 0;
  const andelKlar = mal ? Math.min(1, levererade / mal) : 0;
  return (
    <section aria-labelledby="iris-live" className="rounded-card border border-ink/12 bg-paper p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 id="iris-live" className="text-[1.0625rem] font-semibold tracking-[-0.01em]">
          {text({ sv: "Iris", en: "Iris" })}
        </h2>
        {pagar ? (
          <span className="inline-flex items-center gap-2 text-[0.8125rem] text-ink-muted">
            <span className="relative flex h-2 w-2" aria-hidden>
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ochre opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-ochre" />
            </span>
            {text({ sv: "Kör nu", en: "Running now" })}
          </span>
        ) : rad ? (
          <span className={meta}>{sedan(rad.created_at, locale)}</span>
        ) : null}
      </div>
      {rad && k ? (
        <>
          <p className="num mt-4 text-[1.75rem] font-semibold leading-none tabular-nums text-ink">
            {levererade}
            <span className="text-[1rem] font-medium text-ink-subtle"> / {mal}</span>
          </p>
          <p className={cn(meta, "mt-1.5")}>{text({ sv: "leads levererade av beställda", en: "leads delivered of ordered" })}</p>
          <div
            className="mt-3 h-1.5 overflow-hidden rounded-full bg-ink/10"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={mal}
            aria-valuenow={levererade}
            aria-label={text({ sv: "Körningens förlopp", en: "Run progress" })}
          >
            <span className="block h-full rounded-full bg-ochre transition-[width] duration-300" style={{ width: `${Math.round(andelKlar * 100)}%` }} />
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-3 border-t border-ink/12 pt-3">
            <div>
              <dt className={etikettKlass}>{text({ sv: "Undersökta", en: "Researched" })}</dt>
              <dd className="num mt-0.5 tabular-nums text-ink">{k.undersokta}</dd>
            </div>
            <div>
              <dt className={etikettKlass}>{text({ sv: "Pågår", en: "In progress" })}</dt>
              <dd className="num mt-0.5 tabular-nums text-ink">{k.pagaende}</dd>
            </div>
          </dl>
          <Link href={href} className={cn(btnSecondary, btnLiten, "mt-4 w-full justify-center")}>
            {text({ sv: "Följ körningen", en: "Follow the run" })}
          </Link>
        </>
      ) : (
        <>
          <p className="mt-3 text-[0.9375rem] leading-6 text-ink-muted">
            {text({ sv: "Ingen körning än. Iris letar bolag som passar er målgrupp och skriver utkast.", en: "No run yet. Iris finds companies that fit your audience and writes drafts." })}
          </p>
          <Link href={korHref} className={cn(btnSecondary, btnLiten, "mt-4 w-full justify-center")}>
            {text({ sv: "Kör Iris", en: "Run Iris" })}
          </Link>
        </>
      )}
    </section>
  );
}

function Lank({ href, children }: Readonly<{ href: string; children: React.ReactNode }>) {
  return (
    <Link
      href={href}
      className="focus-ring rounded-input text-[0.875rem] text-ink-subtle underline-offset-4 transition-colors hover:text-ink hover:underline"
    >
      {children}
    </Link>
  );
}
