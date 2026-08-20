"use client";

import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { Badge, SkeletonRows, btnSecondary } from "@/components/ui";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { createDemoSupportApi } from "@/lib/demo/support-inbox";
import { readJsonBody } from "@/lib/http/json";
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

/** "3 dagar sedan". Tom sträng in ger em-streck ut. */
function sedan(iso: string | null | undefined): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms)) return "—";
  const minuter = Math.floor(ms / 60000);
  if (minuter < 1) return "nyss";
  if (minuter < 60) return `${minuter} min sedan`;
  const timmar = Math.floor(minuter / 60);
  if (timmar < 24) return `${timmar} h sedan`;
  const dagar = Math.floor(timmar / 24);
  return dagar === 1 ? "i går" : `${dagar} dagar sedan`;
}

function andel(del: number, av: number): string {
  if (!av) return "—";
  return new Intl.NumberFormat("sv-SE", { style: "percent", maximumFractionDigits: 0 }).format(
    del / av
  );
}

/** Räknar förekomster och returnerar de N vanligaste. */
function vanligast(varden: (string | null | undefined)[], antal: number): [string, number][] {
  const räknare = new Map<string, number>();
  for (const värde of varden) {
    const rent = (värde ?? "").trim();
    if (!rent) continue;
    räknare.set(rent, (räknare.get(rent) ?? 0) + 1);
  }
  return [...räknare.entries()].sort((a, b) => b[1] - a[1]).slice(0, antal);
}

// -- Delade byggstenar -----------------------------------------------------

type Tillstand = { etikett: string; varde: string; larm?: boolean };

/**
 * Raden överst: vad agenten vet och vad den får göra, på en rad.
 *
 * Den finns för att båda talen under är meningslösa utan den. Noll ärenden
 * besvarade betyder en sak när kunskapsbasen har 40 dokument och en helt annan
 * när den är tom, och den skillnaden syntes ingenstans tidigare.
 */
function Tillstandsrad({ poster }: Readonly<{ poster: Tillstand[] }>) {
  return (
    <dl className="grid gap-x-8 gap-y-4 border-y border-ink/15 py-4 sm:grid-cols-2 lg:grid-cols-4">
      {poster.map((post) => (
        <div key={post.etikett} className="min-w-0">
          <dt className="kicker text-mineral">{post.etikett}</dt>
          <dd
            className={cn(
              "mt-1.5 flex items-center gap-2 truncate text-[0.9375rem]",
              post.larm ? "font-semibold text-ink" : "text-ink/75"
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
          </dd>
        </div>
      ))}
    </dl>
  );
}

/**
 * Ett tal. Geist med `tnum`, inte Fraunces: DESIGN.md sätter data i tables och
 * tiles i brödtextfamiljen och reserverar den serifa displayfiguren för list-
 * och stegnummer. En displayfigur i en UI-etikett är dessutom på Operate-lägets
 * lista över vad man inte gör.
 *
 * `larm` färgar talet ochre. Det är ett TILLSTÅND — något väntar på dig — och
 * inte en dekoration, vilket är den enda formen accenten får ta här.
 */
function Tal({
  etikett,
  varde,
  detalj,
  larm = false
}: Readonly<{ etikett: string; varde: string; detalj: string; larm?: boolean }>) {
  return (
    <div className={cn("border-t pt-4", larm ? "border-ochre" : "border-ink/15")}>
      <p className="kicker text-mineral">{etikett}</p>
      {/* Talet står i bläck, alltid. Ochre bär larmet som LINJE över rutan:
          2,17:1 för ochre text mot papper är under 3:1-golvet för stor text,
          och ingen grad räddar det. Linjen har inget kontrastkrav och syns
          dessutom i ögonvrån, vilket en textfärg inte gör. */}
      <p className="num mt-3 text-[2.5rem] font-semibold leading-none tabular-nums tracking-[-0.03em] text-ink">
        {varde}
      </p>
      <p className="mt-2.5 text-[0.8125rem] leading-5 text-ink/60">{detalj}</p>
    </div>
  );
}

function Talrad({ children }: Readonly<{ children: React.ReactNode }>) {
  return <dl className="grid grid-cols-2 gap-x-6 gap-y-8 lg:grid-cols-4">{children}</dl>;
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
    return <p className="max-w-[60ch] text-[0.875rem] leading-6 text-ink/55">{tomtext}</p>;
  }
  const varden = rader.map(([, värde]) => värde);
  const störst = Math.max(...varden);
  // Ochre pekar ut vilket värde som LEDER. Är alla lika finns ingen ledare, och
  // att färga varje stapel hade gjort accenten till en tapet i stället för till
  // information — uppmätt i skärmdump: fem lika stora ochre staplar i rad.
  const harLedare = störst > Math.min(...varden);
  return (
    <ul className="divide-y divide-ink/10 border-y border-ink/15">
      {rader.map(([etikett, värde]) => (
        <li key={etikett} className="grid grid-cols-12 items-center gap-x-4 py-3">
          <span className="col-span-6 truncate text-[0.875rem]" title={etikett}>
            {etikett}
          </span>
          <span className="col-span-4">
            <span className="block h-1.5 overflow-hidden rounded-full bg-ink/8">
              <span
                className={cn(
                  "block h-full rounded-full",
                  harLedare && värde === störst ? "bg-ochre" : "bg-ink/30"
                )}
                style={{ width: `${Math.max(4, Math.round((värde / störst) * 100))}%` }}
              />
            </span>
          </span>
          <span className="num col-span-2 text-right text-[0.875rem] tabular-nums text-ink/70">
            {värde}
          </span>
        </li>
      ))}
    </ul>
  );
}

/**
 * En mening i stor grad — sidans enda ställe där ochre står i brödtextgrad.
 *
 * Meningen är inte pynt: den säger vad agenten får göra på egen hand, vilket
 * är det man behöver veta innan man litar på talen ovanför. Texten kommer ur
 * `autonomy_description` respektive reglerna, alltså ur samma källa som styr
 * beteendet — aldrig ur en hårdkodad sträng som kan bli osann.
 */
function Pastaende({
  children,
  markerat
}: Readonly<{ children: React.ReactNode; markerat?: string }>) {
  return (
    <p className="max-w-[52ch] border-t border-ink/15 pt-6 text-[1.25rem] leading-[1.45] tracking-[-0.01em]">
      {/* Ochre som PLATTA, inte som textfärg. Samma skäl som ovan, och samma
          grepp som Badge redan använder: accenten står kvar i display-grad
          medan texten stannar i bläck. */}
      {markerat ? (
        <span className="mr-1.5 rounded-input bg-ochre/25 px-2 py-0.5 font-semibold text-ink">
          {markerat}
        </span>
      ) : null}
      <span className="text-ink/80">{children}</span>
    </p>
  );
}

type AttGoraRad = { id: string; rubrik: string; under: string; meta?: string };

/**
 * Det enda blocket på sidan som är HANDLING och inte information.
 *
 * Ligger i tonal inversion när kön inte är tom — sidans enda, och den betyder
 * "du måste göra något". Är kön tom blir den en mening på papper: en tom svart
 * ruta hade skrikit lika högt som en full, vilket är precis fel signal.
 */
function AttGora({
  rader,
  href,
  knapp,
  tomtext
}: Readonly<{ rader: AttGoraRad[]; href: string; knapp: string; tomtext: string }>) {
  if (rader.length === 0) {
    return (
      <p className="max-w-[62ch] rounded-card bg-paper2/50 px-5 py-4 text-[0.875rem] leading-6 text-ink/60">
        {tomtext}
      </p>
    );
  }
  return (
    <div className="rounded-card bg-ink p-5 text-paper md:p-6">
      <ul className="divide-y divide-paper/15">
        {rader.slice(0, 5).map((rad) => (
          <li key={rad.id} className="grid grid-cols-12 gap-x-4 py-3 first:pt-0 last:pb-0">
            <div className="col-span-12 min-w-0 sm:col-span-8">
              <p className="truncate text-[0.9375rem] font-semibold">{rad.rubrik}</p>
              <p className="mt-0.5 truncate text-[0.8125rem] text-paper/60">{rad.under}</p>
            </div>
            {rad.meta ? (
              <p className="col-span-12 mt-1 text-[0.8125rem] text-paper/55 sm:col-span-4 sm:mt-0 sm:text-right">
                {rad.meta}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
      <Link
        href={href}
        className="focus-ring mt-5 inline-flex min-h-11 items-center rounded-input bg-paper px-5 text-[0.9375rem] font-semibold text-ink transition-colors hover:bg-paper/85"
      >
        {knapp}
      </Link>
    </div>
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
        Innan agenten kan börja
      </h2>
      <ul className="mt-4 grid gap-4">
        {rader.map((rad) => (
          <li key={rad.href} className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
            <p className="max-w-[62ch] text-[0.9375rem] leading-6 text-ink/70">{rad.text}</p>
            <Link href={rad.href} className={cn(btnSecondary, "shrink-0")}>
              {rad.knapp}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

type LedgerRad = { id: string; vanster: string; mitten: string; hoger: string; ton?: "neutral" | "good" | "warn" | "danger" };

function Ledger({ rader, tomtext }: Readonly<{ rader: LedgerRad[]; tomtext: string }>) {
  if (rader.length === 0) {
    return <p className="max-w-[62ch] text-[0.875rem] leading-6 text-ink/55">{tomtext}</p>;
  }
  return (
    <div className="divide-y divide-ink/10 border-y border-ink/15">
      {rader.map((rad) => (
        <div key={rad.id} className="row grid grid-cols-12 items-baseline gap-x-4 gap-y-1 py-3.5">
          <span className="kicker col-span-12 text-mineral sm:col-span-3">{rad.vanster}</span>
          <span className="col-span-12 truncate text-[0.875rem] sm:col-span-6" title={rad.mitten}>
            {rad.mitten}
          </span>
          <span className="col-span-12 sm:col-span-3 sm:text-right">
            {rad.ton && rad.ton !== "neutral" ? (
              <Badge tone={rad.ton}>{rad.hoger}</Badge>
            ) : (
              <span className="num text-[0.875rem] tabular-nums text-ink/65">{rad.hoger}</span>
            )}
          </span>
        </div>
      ))}
    </div>
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
          className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-card bg-paper2/60 px-4 py-3 text-[0.875rem] text-ink/70"
        >
          <AlertTriangle className="h-4 w-4 shrink-0 text-ochre" aria-hidden />
          En del av siffrorna kunde inte hämtas och visas som streck. Resten stämmer.
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
            Försök igen
          </button>
        </p>
      ) : null}
      {children}
    </div>
  );
}

// -- Leads -----------------------------------------------------------------

type Prospekt = {
  id: string;
  company_name: string;
  contact_name?: string | null;
  status?: string | null;
  origin?: string | null;
  ort?: string | null;
  sni?: string | null;
  icp_fit?: number | null;
  qualified?: boolean | null;
  disqualifiers?: string[] | null;
  created_at?: string | null;
};

type Steg = { skill?: string; escalated?: boolean; latency_ms?: number };
type Korning = { id: string; agent_type?: string; created_at?: string; step_log?: Steg[] | null };
type Koartikel = {
  id: string;
  company_name?: string | null;
  prospect_email?: string | null;
  subject?: string | null;
  scheduled_at?: string | null;
};
type LeadsConfig = {
  autonomy?: string;
  autonomy_description?: string;
  options?: { sni?: { value: string; label: string }[] };
};
/** `missing` är kontextdokument agenten saknar — se leads/onboarding_state.py. */
type Onboarding = { complete?: boolean; missing?: string[] };

/** Backendens tak. Skrivs ut i vyn när listan ligger på dem — se docstringen. */
const PROSPEKTTAK = 100;
const KORNINGSTAK = 200;

const AUTONOMI_KORT: Record<string, string> = {
  draft: "Skriver utkast",
  first_contact: "Skickar första mejlet",
  meeting: "Driver mot möte",
  auto_send: "Skickar självt"
};

export function LeadsOversikt({ demo = false }: Readonly<{ demo?: boolean }>) {
  const hamta = useHamtare(demo);
  const vag = useArbetsvag();
  const { workspaceName } = useDashboard();
  const [laddar, setLaddar] = useState(true);
  const [nyckel, setNyckel] = useState(0);

  const [prospekt, setProspekt] = useState<Prospekt[] | null>(null);
  const [korningar, setKorningar] = useState<Korning[] | null>(null);
  const [ko, setKo] = useState<Koartikel[] | null>(null);
  const [config, setConfig] = useState<LeadsConfig | null>(null);
  const [kbAntal, setKbAntal] = useState<number | null>(null);
  const [onboarding, setOnboarding] = useState<Onboarding | null>(null);

  useEffect(() => {
    let avbruten = false;
    setLaddar(true);

    // Sex oberoende hämtningar. En som faller tar inte med sig de andra.
    void Promise.all([
      hamta<{ prospects?: Prospekt[] }>("/leads/prospects"),
      hamta<{ runs?: Korning[] }>(`/leads/runs?agent_type=leads&limit=${KORNINGSTAK}`),
      hamta<{ items?: Koartikel[] }>("/leads/queue"),
      hamta<LeadsConfig>("/leads/config"),
      hamta<{ articles?: unknown[] }>("/kb"),
      hamta<Onboarding>("/leads/onboarding/status")
    ]).then(([p, r, q, c, kb, o]) => {
      if (avbruten) return;
      setProspekt(p ? (p.prospects ?? []) : null);
      setKorningar(r ? (r.runs ?? []) : null);
      setKo(q ? (q.items ?? []) : null);
      setConfig(c);
      setKbAntal(kb ? (kb.articles?.length ?? 0) : null);
      setOnboarding(o);
      setLaddar(false);
    });

    return () => {
      avbruten = true;
    };
  }, [hamta, nyckel]);

  const rader = prospekt ?? [];
  const exempel = rader.filter((p) => p.origin === "example").length;
  const kvalificerade = rader.filter((p) => p.qualified === true).length;
  const bedomda = rader.filter((p) => typeof p.icp_fit === "number");
  const snittFit = bedomda.length
    ? bedomda.reduce((summa, p) => summa + (p.icp_fit ?? 0), 0) / bedomda.length
    : null;

  const veckan = Date.now() - 7 * 24 * 3600 * 1000;
  const veckansKorningar = (korningar ?? []).filter(
    (k) => k.created_at && new Date(k.created_at).getTime() >= veckan
  );
  const eskaleradeSteg = veckansKorningar.reduce(
    (summa, k) => summa + (k.step_log ?? []).filter((steg) => steg.escalated).length,
    0
  );

  const sniNamn = new Map((config?.options?.sni ?? []).map((o) => [o.value, o.label]));
  const branscher = vanligast(
    rader.map((p) => (p.sni ? (sniNamn.get(p.sni) ?? p.sni) : null)),
    5
  );
  const orter = vanligast(
    rader.map((p) => p.ort),
    5
  );
  const bortvalda = vanligast(
    rader.flatMap((p) => p.disqualifiers ?? []),
    4
  );

  const ofullstandig =
    prospekt === null || korningar === null || ko === null || config === null || kbAntal === null;

  return (
    <OversiktShell
      laddar={laddar}
      ofullstandig={ofullstandig}
      uppdatera={() => setNyckel((n) => n + 1)}
    >
      <Tillstandsrad
        poster={[
          { etikett: "Arbetsyta", varde: workspaceName ?? "—" },
          {
            etikett: "Agenten får",
            varde: config?.autonomy ? (AUTONOMI_KORT[config.autonomy] ?? config.autonomy) : "—"
          },
          {
            etikett: "Kunskapsbas",
            varde: kbAntal === null ? "—" : `${kbAntal} dokument`,
            larm: kbAntal === 0
          },
          {
            etikett: "Senaste körning",
            varde: korningar === null ? "—" : sedan(korningar[0]?.created_at)
          }
        ]}
      />

      <Komigang
        rader={
          onboarding?.missing?.includes("product_marketing")
            ? [
                {
                  text: "Agenten vet inte vad ni säljer. Utan den texten kan den varken välja bolag eller skriva ett utkast som håller.",
                  href: vag("/settings/affarskontext"),
                  knapp: "Fyll i affärskontexten"
                }
              ]
            : []
        }
      />

      <Talrad>
        <Tal
          etikett="Prospekt"
          varde={prospekt === null ? "—" : String(rader.length)}
          detalj={
            prospekt === null
              ? "kunde inte hämtas"
              : rader.length >= PROSPEKTTAK
                ? `${exempel} exempelbolag · av de ${PROSPEKTTAK} senaste`
                : exempel
                  ? `${exempel} av dem är exempelbolag`
                  : "inga exempelbolag"
          }
        />
        <Tal
          etikett="Kvalificerade"
          varde={prospekt === null ? "—" : String(kvalificerade)}
          detalj={
            snittFit === null
              ? "ingen bedömning ännu"
              : `snittpassning ${andel(snittFit, 1)} mot ert ICP`
          }
        />
        <Tal
          etikett="Väntar på dig"
          varde={ko === null ? "—" : String(ko.length)}
          detalj={ko?.length ? "utkast i granskningskön" : "granskningskön är tom"}
          larm={Boolean(ko?.length)}
        />
        <Tal
          etikett="Körningar 7 dgr"
          varde={korningar === null ? "—" : String(veckansKorningar.length)}
          detalj={
            korningar === null
              ? "kunde inte hämtas"
              : eskaleradeSteg
                ? `${eskaleradeSteg} steg eskalerade till dig`
                : "inga steg eskalerade"
          }
        />
      </Talrad>

      {config?.autonomy_description ? (
        <Pastaende markerat={AUTONOMI_KORT[config.autonomy ?? ""]}>
          {config.autonomy_description}
        </Pastaende>
      ) : null}

      <Sektion rubrik="Att göra">
        <AttGora
          rader={(ko ?? []).map((post) => ({
            id: post.id,
            rubrik: post.company_name ?? post.prospect_email ?? "Utkast",
            under: post.subject ?? "Utan ämnesrad",
            meta: post.scheduled_at ? `köat ${sedan(post.scheduled_at)}` : undefined
          }))}
          href={vag("/dashboard/leads")}
          knapp="Öppna granskningskön"
          tomtext="Ingenting väntar på ditt godkännande. Utkast agenten skriver hamnar här."
        />
      </Sektion>

      <div className="grid gap-10 lg:grid-cols-12">
        <div className="min-w-0 lg:col-span-4">
          <Sektion rubrik="Var agenten letar">
            <Stapellista rader={orter} tomtext="Ingen ort utläst ur prospekten ännu." />
          </Sektion>
        </div>
        <div className="min-w-0 lg:col-span-4">
          <Sektion rubrik="Vad den hittar">
            <Stapellista rader={branscher} tomtext="Ingen bransch utläst ur prospekten ännu." />
          </Sektion>
        </div>
        <div className="min-w-0 lg:col-span-4">
          <Sektion rubrik="Varför bolag valdes bort">
            <Stapellista
              rader={bortvalda}
              tomtext="Inget prospekt har valts bort med angiven orsak ännu. Orsakerna sparas när agenten researchat."
            />
          </Sektion>
        </div>
      </div>

      <Sektion
        rubrik="Senaste körningarna"
        bredvid={
          <Link
            href={vag("/dashboard/leads")}
            className="focus-ring rounded-input text-[0.875rem] text-ink/55 underline-offset-4 transition-colors hover:text-ink hover:underline"
          >
            Starta en körning
          </Link>
        }
      >
        <Ledger
          rader={veckansKorningar.slice(0, 6).map((k) => {
            const steg = k.step_log ?? [];
            const eskalerade = steg.filter((s) => s.escalated).length;
            const skills = steg.map((s) => s.skill).filter(Boolean).join(", ");
            return {
              id: k.id,
              vanster: sedan(k.created_at),
              mitten: steg.length
                ? `${steg.length} steg${skills ? ` · ${skills}` : ""}`
                : "Ingen stegloggning på körningen",
              hoger: eskalerade ? `${eskalerade} eskalerade` : "utan eskalering",
              ton: eskalerade ? ("warn" as const) : ("neutral" as const)
            };
          })}
          tomtext="Inga körningar den senaste veckan."
        />
      </Sektion>
    </OversiktShell>
  );
}

// -- Kundtjänst ------------------------------------------------------------

/** Nyckeltal utan stapel: värdena är inte jämförbara med varandra. */
function Faktalista({ rader }: Readonly<{ rader: { etikett: string; varde: string; larm?: boolean }[] }>) {
  return (
    <dl className="divide-y divide-ink/10 border-y border-ink/15">
      {rader.map((rad) => (
        <div key={rad.etikett} className="grid grid-cols-12 items-baseline gap-x-4 py-3">
          <dt className="col-span-8 text-[0.875rem] text-ink/75">{rad.etikett}</dt>
          <dd
            className={cn(
              "num col-span-4 flex items-center justify-end gap-2 text-right text-[0.875rem] tabular-nums",
              rad.larm ? "font-semibold text-ink" : "text-ink/70"
            )}
          >
            {/* Samma sak som i Tal: pricken bär larmet, inte textfärgen. */}
            {rad.larm ? <span className="h-2 w-2 rounded-full bg-ochre" aria-hidden /> : null}
            {rad.varde}
          </dd>
        </div>
      ))}
    </dl>
  );
}

type Klassificering = {
  category: string;
  confidence: number;
  escalate: boolean;
  kb_sources?: { title: string }[];
};
type Arende = {
  id: string;
  from_email: string;
  from_name?: string | null;
  subject: string;
  received_at: string;
  status: string;
  classification?: Klassificering | null;
  draft?: { id: string; confidence: number } | null;
};
type Regel = { category: string; label: string; mode: "auto" | "draft" | "escalate" };

/** Backendens tak för inkorgslistan. Skrivs ut när listan ligger på det. */
const ARENDETAK = 200;

/** Speglar STATUS_META i components/snajp/Dashboard.tsx — samma ord, samma ton. */
const STATUSORD: Record<string, { text: string; ton: "neutral" | "good" | "warn" | "danger" }> = {
  new: { text: "Ny", ton: "neutral" },
  processing: { text: "Bearbetas", ton: "neutral" },
  awaiting_approval: { text: "Väntar", ton: "warn" },
  auto_sent: { text: "Autosvar", ton: "good" },
  sent: { text: "Besvarat", ton: "good" },
  escalated: { text: "Eskalerat", ton: "danger" },
  rejected: { text: "Avvisat", ton: "neutral" },
  taken_over: { text: "Övertaget", ton: "neutral" },
  failed: { text: "Fel", ton: "danger" }
};

export function SupportOversikt({ demo = false }: Readonly<{ demo?: boolean }>) {
  const hamta = useHamtare(demo);
  const vag = useArbetsvag();
  const { workspaceName } = useDashboard();
  const [laddar, setLaddar] = useState(true);
  const [nyckel, setNyckel] = useState(0);

  const [arenden, setArenden] = useState<Arende[] | null>(null);
  const [fack, setFack] = useState<Record<string, number> | null>(null);
  const [regler, setRegler] = useState<Regel[] | null>(null);
  const [kbAntal, setKbAntal] = useState<number | null>(null);

  useEffect(() => {
    let avbruten = false;
    setLaddar(true);

    void Promise.all([
      hamta<{ emails?: Arende[]; category_counts?: Record<string, number> }>(
        `/inbox?limit=${ARENDETAK}`
      ),
      hamta<{ rules?: Regel[] }>("/rules"),
      hamta<{ articles?: unknown[] }>("/kb")
    ]).then(([i, r, kb]) => {
      if (avbruten) return;
      setArenden(i ? (i.emails ?? []) : null);
      setFack(i ? (i.category_counts ?? {}) : null);
      setRegler(r ? (r.rules ?? []) : null);
      setKbAntal(kb ? (kb.articles?.length ?? 0) : null);
      setLaddar(false);
    });

    return () => {
      avbruten = true;
    };
  }, [hamta, nyckel]);

  const rader = arenden ?? [];
  const vantar = rader.filter((a) => a.status === "awaiting_approval");
  const eskalerade = rader.filter((a) => a.status === "escalated");
  const klarade = rader.filter((a) => a.status === "auto_sent" || a.status === "sent");
  const klassade = rader.filter((a) => a.classification);
  const medKalla = klassade.filter((a) => (a.classification?.kb_sources ?? []).length > 0);
  const snittKonfidens = klassade.length
    ? klassade.reduce((summa, a) => summa + (a.classification?.confidence ?? 0), 0) / klassade.length
    : null;
  // Det tal som pekar rakt på luckorna i basen: agenten lämnade över för att
  // den inte hittade något att grunda svaret i, inte för att ärendet var svårt.
  const eskaleratUtanKalla = eskalerade.filter(
    (a) => (a.classification?.kb_sources ?? []).length === 0
  ).length;

  const auto = (regler ?? []).filter((r) => r.mode === "auto");
  const utkast = (regler ?? []).filter((r) => r.mode === "draft").length;
  const alltidManniska = (regler ?? []).filter((r) => r.mode === "escalate").length;
  const fackNamn = new Map((regler ?? []).map((r) => [r.category, r.label]));

  const ofullstandig = arenden === null || regler === null || kbAntal === null;

  return (
    <OversiktShell
      laddar={laddar}
      ofullstandig={ofullstandig}
      uppdatera={() => setNyckel((n) => n + 1)}
    >
      <Tillstandsrad
        poster={[
          { etikett: "Arbetsyta", varde: workspaceName ?? "—" },
          {
            etikett: "Regler",
            varde:
              regler === null
                ? "—"
                : `${auto.length} auto · ${utkast} utkast · ${alltidManniska} eskalera`
          },
          {
            etikett: "Kunskapsbas",
            varde: kbAntal === null ? "—" : `${kbAntal} dokument`,
            larm: kbAntal === 0
          },
          {
            etikett: "Senaste ärendet",
            varde: arenden === null ? "—" : sedan(rader[0]?.received_at)
          }
        ]}
      />

      <Komigang
        rader={
          kbAntal === 0
            ? [
                {
                  text: "Kunskapsbasen är tom. Agenten gissar aldrig — den eskalerar varje ärende den inte kan grunda, så inkorgen blir en lista med röda rader tills det ligger något här.",
                  href: vag("/settings/kunskapsbas"),
                  knapp: "Fyll kunskapsbasen"
                }
              ]
            : []
        }
      />

      <Talrad>
        <Tal
          etikett="Ärenden"
          varde={arenden === null ? "—" : String(rader.length)}
          detalj={
            arenden === null
              ? "kunde inte hämtas"
              : rader.length >= ARENDETAK
                ? `de ${ARENDETAK} senaste i inkorgen`
                : "i inkorgen"
          }
        />
        <Tal
          etikett="Klarade själv"
          varde={arenden === null ? "—" : String(klarade.length)}
          detalj={
            rader.length ? `${andel(klarade.length, rader.length)} av ärendena` : "inga ärenden ännu"
          }
        />
        <Tal
          etikett="Väntar på dig"
          varde={arenden === null ? "—" : String(vantar.length)}
          detalj={vantar.length ? "utkast att godkänna" : "inget utkast att granska"}
          larm={vantar.length > 0}
        />
        <Tal
          etikett="Eskalerade"
          varde={arenden === null ? "—" : String(eskalerade.length)}
          detalj={
            rader.length
              ? `${andel(eskalerade.length, rader.length)} gick till en människa`
              : "inga ärenden ännu"
          }
        />
      </Talrad>

      {regler === null ? null : (
        <Pastaende
          markerat={
            auto.length === 0
              ? "Ingenting"
              : `${auto.length} ${auto.length === 1 ? "fack" : "fack"}`
          }
        >
          {auto.length === 0
            ? "skickas utan att du sett det. Varje svar ligger som utkast tills du godkänt det. Pengar, juridik, GDPR och arga kunder går alltid till en människa."
            : `besvaras av agenten självt: ${auto.map((r) => r.label.toLowerCase()).join(", ")}. Pengar, juridik, GDPR och arga kunder går alltid till en människa, oavsett regel.`}
        </Pastaende>
      )}

      <Sektion rubrik="Att göra">
        <AttGora
          rader={vantar.map((a) => ({
            id: a.id,
            rubrik: a.subject || "(utan ämne)",
            under: a.from_name ? `${a.from_name} · ${a.from_email}` : a.from_email,
            meta: a.draft
              ? `konfidens ${andel(a.draft.confidence, 1)}`
              : sedan(a.received_at)
          }))}
          href={vag("/dashboard/support")}
          knapp="Granska utkasten"
          tomtext="Inget utkast väntar på ditt godkännande. Svar agenten skriver hamnar här först."
        />
      </Sektion>

      <div className="grid gap-10 lg:grid-cols-12">
        <div className="min-w-0 lg:col-span-7">
          <Sektion rubrik="Vad ärendena handlar om">
            <Stapellista
              rader={Object.entries(fack ?? {})
                .map(([kod, antal]) => [fackNamn.get(kod) ?? kod, antal] as [string, number])
                .sort((a, b) => b[1] - a[1])}
              tomtext="Inga klassificerade ärenden ännu."
            />
          </Sektion>
        </div>
        <div className="min-w-0 lg:col-span-5">
          <Sektion rubrik="Hur väl agenten kan grunda svaren">
            <Faktalista
              rader={[
                {
                  etikett: "Ärenden med träff i kunskapsbasen",
                  varde: klassade.length ? `${medKalla.length} av ${klassade.length}` : "—"
                },
                {
                  etikett: "Snittkonfidens i klassificeringen",
                  varde: snittKonfidens === null ? "—" : andel(snittKonfidens, 1)
                },
                {
                  etikett: "Eskalerade utan träff i basen",
                  varde: arenden === null ? "—" : String(eskaleratUtanKalla),
                  larm: eskaleratUtanKalla > 0
                }
              ]}
            />
            {eskaleratUtanKalla > 0 ? (
              <p className="mt-4 max-w-[52ch] text-[0.875rem] leading-6 text-ink/60">
                De ärendena lämnades över för att agenten inte hittade något att svara ur, inte för
                att frågan var svår.{" "}
                <Link
                  href={vag("/settings/kunskapsbas")}
                  className="focus-ring rounded-input underline underline-offset-4 hover:text-ochre"
                >
                  Fyll på kunskapsbasen
                </Link>{" "}
                så minskar de.
              </p>
            ) : null}
          </Sektion>
        </div>
      </div>

      <Sektion
        rubrik="Senaste ärendena"
        bredvid={
          <Link
            href={vag("/dashboard/support")}
            className="focus-ring rounded-input text-[0.875rem] text-ink/55 underline-offset-4 transition-colors hover:text-ink hover:underline"
          >
            Öppna inkorgen
          </Link>
        }
      >
        <Ledger
          rader={rader.slice(0, 6).map((a) => {
            const status = STATUSORD[a.status] ?? STATUSORD.new;
            return {
              id: a.id,
              vanster: sedan(a.received_at),
              mitten: `${a.subject || "(utan ämne)"} · ${a.from_name ?? a.from_email}`,
              hoger: status.text,
              ton: status.ton
            };
          })}
          tomtext="Inkorgen är tom. Koppla en inkorg under Inställningar, eller hämta testmail i kundtjänstvyn."
        />
      </Sektion>
    </OversiktShell>
  );
}
