"use client";

import { AlertTriangle, Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useArbetsvag } from "@/components/AppShell";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { Badge, Rad, Radlista, SkeletonRows, btnSecondary, etikett as etikettKlass, meta } from "@/components/ui";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { createDemoSupportApi } from "@/lib/demo/support-inbox";
import { readJsonBody } from "@/lib/http/json";
import { KORNINGSSTATUS, korningsTyp, type KorningsRad } from "@/components/leads/IrisKorningar";
import { STATUS_ETIKETT, STATUS_ORDNING } from "@/lib/prospekt";
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
      <p className={etikettKlass}>{etikett}</p>
      {/* Talet står i bläck, alltid. Ochre bär larmet som LINJE över rutan:
          2,17:1 för ochre text mot papper är under 3:1-golvet för stor text,
          och ingen grad räddar det. Linjen har inget kontrastkrav och syns
          dessutom i ögonvrån, vilket en textfärg inte gör. */}
      <p className="num mt-3 text-[2.5rem] font-semibold leading-none tabular-nums tracking-[-0.03em] text-ink">
        {varde}
      </p>
      <p className="mt-2.5 text-[0.8125rem] leading-5 text-ink-muted">{detalj}</p>
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
      <span className="text-ink-muted">{children}</span>
    </p>
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
  return (
    <section aria-label={text(T.attGora)} className="rounded-card bg-ink p-6 text-paper md:p-8">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-4">
        <h2 className="text-[1.25rem] font-semibold tracking-[-0.01em]">
          {rader.length === 1
            ? text({ sv: "1 sak väntar på dig", en: "1 item waiting for you" })
            : text({
                sv: `${rader.length} saker väntar på dig`,
                en: `${rader.length} items waiting for you`
              })}
        </h2>
        <Link
          href={href}
          className="focus-ring inline-flex min-h-11 items-center rounded-input bg-paper px-5 text-[0.9375rem] font-semibold text-ink transition-colors hover:bg-paper/85"
        >
          {knapp}
        </Link>
      </div>
      {/* Samma spannlogik som Stapellista, i mörk färgvärld: rubrik/underrad
          8 spann, meta 4, deklarerat på VARJE rad — metakolumnen ritas även
          tom, så den står på samma plats oavsett om en rad har meta. */}
      <ul className="mt-5 border-t border-paper/15">
        {rader.slice(0, 5).map((rad) => (
          <li key={rad.id} className="border-b border-paper/15">
            <Link
              href={rad.href ?? href}
              // text-paper uttryckligen: globals.css sätter `a { color: ink }`,
              // och utan den här klassen står rubriken bläck-på-bläck. Uppmätt
              // i skärmdump: raden såg ut att sakna sin rubrikrad helt.
              className="focus-ring -mx-3 grid grid-cols-12 gap-x-4 rounded-input px-3 py-3.5 text-paper transition-colors hover:bg-paper/10"
            >
              <span className="col-span-12 min-w-0 sm:col-span-8">
                <span className="block truncate text-[0.9375rem] font-semibold">{rad.rubrik}</span>
                <span className="mt-0.5 block truncate text-[0.8125rem] text-paper-muted">
                  {rad.under}
                </span>
              </span>
              <span className="col-span-12 mt-1 truncate text-[0.8125rem] text-paper-muted sm:col-span-4 sm:mt-0 sm:self-center sm:text-right">
                {rad.meta ?? ""}
              </span>
            </Link>
          </li>
        ))}
      </ul>
      {fler > 0 ? (
        <p className="mt-4 text-[0.8125rem] text-paper-muted">
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

type LedgerRad = { id: string; vanster: string; mitten: string; hoger: string; ton?: "neutral" | "good" | "warn" | "danger" };

function Ledger({ rader, tomtext }: Readonly<{ rader: LedgerRad[]; tomtext: string }>) {
  if (rader.length === 0) {
    return <p className="max-w-[62ch] text-[0.875rem] leading-6 text-ink-subtle">{tomtext}</p>;
  }
  return (
    <div className="divide-y divide-ink/10 border-y border-ink/15">
      {rader.map((rad) => (
        <div key={rad.id} className="row grid grid-cols-12 items-baseline gap-x-4 gap-y-1 py-3.5">
          <span className={cn(meta, "col-span-12 sm:col-span-3")}>{rad.vanster}</span>
          <span className="col-span-12 truncate text-[0.875rem] sm:col-span-6" title={rad.mitten}>
            {rad.mitten}
          </span>
          <span className="col-span-12 sm:col-span-3 sm:text-right">
            {rad.ton && rad.ton !== "neutral" ? (
              <Badge tone={rad.ton}>{rad.hoger}</Badge>
            ) : (
              <span className="num text-[0.875rem] tabular-nums text-ink-muted">{rad.hoger}</span>
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
  status?: string | null;
  origin?: string | null;
  created_at?: string | null;
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
const VECKA_MS = 7 * 24 * 3600 * 1000;

function senasteVeckan(iso: string | null | undefined): boolean {
  if (!iso) return false;
  const t = new Date(iso).getTime();
  return !Number.isNaN(t) && Date.now() - t < VECKA_MS;
}

type Data = {
  prospekt: Prospekt[] | null;
  ko: Koartikel[] | null;
  korningar: KorningsRad[] | null;
  leadsMejl: { received_at: string }[] | null;
  onboarding: Onboarding | null;
  arenden: Arende[] | null;
  fack: Record<string, number> | null;
  regler: Regel[] | null;
  kbAntal: number | null;
};

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

  useEffect(() => {
    let avbruten = false;
    setLaddar(true);
    const ingen = Promise.resolve(null);
    // Oberoende hämtningar. En som faller tar inte med sig de andra.
    void Promise.all([
      leads ? hamta<{ prospects?: Prospekt[] }>("/leads/prospects") : ingen,
      leads ? hamta<{ items?: Koartikel[] }>("/leads/queue") : ingen,
      leads ? hamta<{ korningar?: KorningsRad[] }>("/leads/korningar?limit=5") : ingen,
      leads ? hamta<{ emails?: { received_at: string }[] }>(`/inbox?klass=lead&limit=${ARENDETAK}`) : ingen,
      leads ? hamta<Onboarding>("/leads/onboarding/status") : ingen,
      support
        ? hamta<{ emails?: Arende[]; category_counts?: Record<string, number> }>(`/inbox?limit=${ARENDETAK}`)
        : ingen,
      support ? hamta<{ rules?: Regel[] }>("/rules") : ingen,
      hamta<{ articles?: unknown[] }>("/kb")
    ]).then(([p, q, k, lm, o, i, r, kb]) => {
      if (avbruten) return;
      setD({
        prospekt: p ? (p.prospects ?? []) : null,
        ko: q ? (q.items ?? []) : null,
        // Demon har ingen jobbliggare: tom lista, inte "kunde inte hämtas".
        korningar: k ? (k.korningar ?? []) : demo ? [] : null,
        leadsMejl: lm ? (lm.emails ?? []) : demo ? [] : null,
        onboarding: o,
        arenden: i ? (i.emails ?? []) : null,
        fack: i ? (i.category_counts ?? {}) : null,
        regler: r ? (r.rules ?? []) : null,
        kbAntal: kb ? (kb.articles?.length ?? 0) : null
      });
      setLaddar(false);
    });
    return () => {
      avbruten = true;
    };
  }, [hamta, nyckel, leads, support, demo]);

  if (!d) {
    return <OversiktShell laddar ofullstandig={false} uppdatera={() => undefined}>{null}</OversiktShell>;
  }

  const prospekt = (d.prospekt ?? []).filter((p) => p.origin !== "example");
  const nyaLeads = prospekt.filter((p) => senasteVeckan(p.created_at)).length;
  const moten = prospekt.filter((p) => p.status === "meeting").length;
  const vunna = prospekt.filter((p) => p.status === "won").length;
  const svar = (d.leadsMejl ?? []).filter((m) => senasteVeckan(m.received_at)).length;
  const arenden = d.arenden ?? [];
  const vantarSupport = arenden.filter((a) => a.status === "awaiting_approval");
  const eskalerade = arenden.filter((a) => a.status === "escalated");
  const klarade = arenden.filter((a) => a.status === "auto_sent" || a.status === "sent").length;
  const veckansArenden = arenden.filter((a) => senasteVeckan(a.received_at)).length;
  const fackNamn = new Map((d.regler ?? []).map((r) => [r.category, r.label]));

  const ofullstandig =
    (leads && (d.prospekt === null || d.ko === null || d.korningar === null || d.leadsMejl === null)) ||
    (support && (d.arenden === null || d.regler === null)) ||
    d.kbAntal === null;

  // Allt som väntar på ett beslut, från alla agenter, nyast först.
  const vantar: (AttGoraRad & { nar: string })[] = [
    ...(d.ko ?? []).map((post) => ({
      id: `iris-${post.id}`,
      rubrik: post.company_name ?? post.prospect_email ?? text(T.utkast),
      under: post.subject ?? text(T.utanAmnesrad),
      meta: text({ sv: "Iris · utkast", en: "Iris · draft" }),
      href: vag("/dashboard/att-gora"),
      nar: post.scheduled_at ?? ""
    })),
    ...[...vantarSupport, ...eskalerade].map((a) => ({
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

  const vantarAntal = leads || support ? vantar.length : 0;
  const tom = (v: unknown[] | null) => v === null;

  const pipeline = STATUS_ORDNING.filter((s) => s !== "suppressed")
    .map((s) => [text(STATUS_ETIKETT[s]), prospekt.filter((p) => (p.status ?? "new") === s).length] as [string, number])
    .filter(([, antal]) => antal > 0);

  return (
    <OversiktShell laddar={laddar} ofullstandig={ofullstandig} uppdatera={() => setNyckel((n) => n + 1)}>
      {/* Nyckeltalen först (Antons beställning 2026-10-03: "många viktiga
          mätvärden gömda längre ned"). En rad, bara agenter arbetsytan har. */}
      <dl className="grid grid-cols-2 gap-x-6 gap-y-8 sm:grid-cols-3 xl:grid-cols-6">
        <Tal
          etikett={text(T.vantarPaDig)}
          varde={String(vantarAntal)}
          detalj={text({ sv: "utkast och eskaleringar", en: "drafts and escalations" })}
          larm={vantarAntal > 0}
        />
        {leads ? (
          <>
            <Tal
              etikett={text({ sv: "Nya leads", en: "New leads" })}
              varde={tom(d.prospekt) ? TOM : String(nyaLeads)}
              detalj={text({ sv: "senaste 7 dagarna", en: "last 7 days" })}
            />
            <Tal
              etikett={text({ sv: "Svar från leads", en: "Replies from leads" })}
              varde={tom(d.leadsMejl) ? TOM : String(svar)}
              detalj={text({ sv: "senaste 7 dagarna", en: "last 7 days" })}
            />
            <Tal
              etikett={text({ sv: "Möten", en: "Meetings" })}
              varde={tom(d.prospekt) ? TOM : String(moten)}
              detalj={text({ sv: `leads i status Möte · ${vunna} vunna`, en: `leads in Meeting · ${vunna} won` })}
            />
          </>
        ) : null}
        {support ? (
          <>
            <Tal
              etikett={text(T.arenden)}
              varde={tom(d.arenden) ? TOM : String(veckansArenden)}
              detalj={
                arenden.length >= ARENDETAK
                  ? text({ sv: `senaste 7 dagarna, av de ${ARENDETAK} senaste`, en: `last 7 days, of the latest ${ARENDETAK}` })
                  : text({ sv: "senaste 7 dagarna", en: "last 7 days" })
              }
            />
            <Tal
              etikett={text(T.klaradeSjalv)}
              varde={tom(d.arenden) ? TOM : andel(klarade, arenden.length, locale)}
              detalj={
                arenden.length
                  ? text({ sv: `${klarade} av ${arenden.length} ärenden`, en: `${klarade} of ${arenden.length} tickets` })
                  : text(T.ingaArenden)
              }
            />
          </>
        ) : null}
      </dl>

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

      <div className="grid gap-12 lg:grid-cols-2">
        {leads ? (
          <Sektion
            rubrik={text({ sv: "Pipeline", en: "Pipeline" })}
            bredvid={<Lank href={vag("/dashboard/leads?vy=pipeline")}>{text({ sv: "Öppna pipelinen", en: "Open the pipeline" })}</Lank>}
          >
            <Stapellista rader={pipeline} tomtext={text({ sv: "Inga leads ännu.", en: "No leads yet." })} />
          </Sektion>
        ) : null}

        {leads ? (
          <Sektion
            rubrik={text({ sv: "Iris senaste körningar", en: "Iris latest runs" })}
            bredvid={<Lank href={vag("/dashboard/aktivitet")}>{text({ sv: "Öppna aktiviteten", en: "Open activity" })}</Lank>}
          >
            <Ledger
              rader={(d.korningar ?? []).map((k) => ({
                id: k.job_id,
                vanster: sedan(k.created_at, locale),
                mitten: text(korningsTyp(k)),
                hoger: text(KORNINGSSTATUS[k.status]),
                ton: k.status === "failed" ? "danger" : k.status === "completed" ? "good" : "neutral"
              }))}
              tomtext={text({ sv: "Inga körningar än.", en: "No runs yet." })}
            />
          </Sektion>
        ) : null}

        {support ? (
          <Sektion rubrik={text(T.vadArendena)}>
            <Stapellista
              rader={Object.entries(d.fack ?? {})
                .filter(([, antal]) => antal > 0)
                .map(([kod, antal]) => [fackNamn.get(kod) ?? kod, antal] as [string, number])
                .sort((a, b) => b[1] - a[1])}
              tomtext={text(T.ingaKlassificerade)}
            />
          </Sektion>
        ) : null}

        {support ? (
          <Sektion
            rubrik={text(T.senasteArendena)}
            bredvid={<Lank href={vag("/dashboard/support")}>{text(T.oppnaInkorgen)}</Lank>}
          >
            <Ledger
              rader={arenden.slice(0, 5).map((a) => {
                const status = STATUSORD[a.status] ?? STATUSORD.new;
                return {
                  id: a.id,
                  vanster: sedan(a.received_at, locale),
                  mitten: `${a.subject || text(T.utanAmne)} · ${a.from_name ?? a.from_email}`,
                  hoger: text(status.text),
                  ton: status.ton
                };
              })}
              tomtext={text(T.inkorgenTom)}
            />
          </Sektion>
        ) : null}
      </div>

      {/* Läget sist: vad agenterna vet. Siffrorna ovan är meningslösa om
          kunskapsbasen är tom, därför står bristen kvar här med larmprick. */}
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

/** Speglar STATUS_META i components/snajp/Dashboard.tsx — samma ord, samma ton. */
const STATUSORD: Record<string, { text: Localized; ton: "neutral" | "good" | "warn" | "danger" }> = {
  new: { text: { sv: "Ny", en: "New" }, ton: "neutral" },
  processing: { text: { sv: "Bearbetas", en: "Processing" }, ton: "neutral" },
  awaiting_approval: { text: { sv: "Väntar", en: "Waiting" }, ton: "warn" },
  auto_sent: { text: { sv: "Autosvar", en: "Auto-reply" }, ton: "good" },
  sent: { text: { sv: "Besvarat", en: "Answered" }, ton: "good" },
  escalated: { text: { sv: "Eskalerat", en: "Escalated" }, ton: "danger" },
  rejected: { text: { sv: "Avvisat", en: "Rejected" }, ton: "neutral" },
  taken_over: { text: { sv: "Övertaget", en: "Taken over" }, ton: "neutral" },
  failed: { text: { sv: "Fel", en: "Error" }, ton: "danger" }
};
