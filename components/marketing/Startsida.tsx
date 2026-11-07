"use client";

/* Snajp · genre: nordic-editorial · design-system: DESIGN.md · designed-as-app */
/* design · pre-emit critique: P4 H4 E4 S4 R4 V4 */

import Link from "next/link";
import { useLocale, type Localized } from "@/lib/i18n";
import { landningsPost } from "@/lib/landningar";
import { cn } from "@/lib/utils";
import { HeroText } from "@/components/marketing/LiveText";
import { PRODUKTYTOR, ProduktBilder, type Yta } from "@/components/marketing/ProduktBilder";
import { LOFTET } from "@/components/marketing/UspSection";
import { RESULTAT, RESULTAT_NOT, StatRad } from "@/components/marketing/AgentResultat";
import { leadsCopy, productCopy, shared, supportCopy } from "@/components/marketing/copy";
import { imagery, photo } from "@/components/marketing/copy-sections";

/**
 * Startsidan, delarna som bara finns på `/` (Anton 2026-11-07).
 *
 * `/` och `/leads` var samma sida med samma H1, och `/` skrevs om till `/leads`
 * i adressfältet. Nu har `/` en egen hjälte (koncept 2a: fotot från 1a, de två
 * agenternas produktytor svävande över himlen) och en sektion per agent. Skalet
 * runt, sidhuvudet, dygnsljuset och sektionerna efter Haga-bilden, är
 * LandingPhotos (läget `hem`), så att det gemensamma bara finns på ett ställe.
 *
 * Agentsektionen är de tre sektioner som stod per agent på produktsidan, i
 * Antons ordning: löftet, sedan resultatvyns tal och panel under det, sedan
 * demon med texten bredvid i stället för i hela bredden. Copyn är den godkända
 * (LOFTET, RESULTAT, productCopy); det enda nya är rubriken, raderna under
 * ytorna och "Läs mer".
 *
 * Rörelsen bor i useLandingMotion: `data-mo="svav"` (ytornas ankomst, vila och
 * hovring) och `data-mo="steg"` (flödet, en sak i taget när den står helt i
 * bild). Utan JS står allt synligt.
 */

type Agent = "leads" | "support";

const COPY = {
  rubrik: {
    sv: "AI-agenter för leads och kundtjänst, på *svenska*.",
    en: "AI agents for leads and customer service, in *Swedish*."
  },
  lasMer: { sv: "Läs mer", en: "Read more" }
} satisfies Record<string, Localized>;

const AGENTER: Record<
  Agent,
  {
    namn: Localized;
    etikett: Localized;
    vad: Localized;
    prova: Localized;
    lasMerOm: Localized;
    helaDemon: Localized;
    demo: string;
    ankare: string;
    panel: string;
    yta: Yta;
  }
> = {
  leads: {
    namn: { sv: "Iris", en: "Iris" },
    etikett: { sv: "Iris, leadsagenten", en: "Iris, the leads agent" },
    // Sökordssidans mening (/svensk-ai-sdr) utan subjektet: namnet står redan ovanför.
    vad: {
      sv: "Hittar rätt bolag, läser på om dem och skriver säljmejlet.",
      en: "Finds the right companies, reads up on them and writes the sales email."
    },
    prova: { sv: "Prova Iris", en: "Try Iris" },
    lasMerOm: { sv: "Läs mer om Iris", en: "Read more about Iris" },
    helaDemon: shared.demoLeads,
    demo: "/demo/leads",
    ankare: "iris",
    panel: "Email Studio",
    yta: PRODUKTYTOR.irisUtkast
  },
  support: {
    namn: { sv: "Supportagenten", en: "The support agent" },
    etikett: { sv: "Supportagenten", en: "The support agent" },
    // Sökordssidans mening (/ai-supportagent) utan subjektet.
    vad: {
      sv: "Sorterar kundmejlen, skriver svaren och lämnar över det som kräver en människa.",
      en: "Sorts customer emails, writes the replies and hands over what needs a person."
    },
    prova: { sv: "Prova supportagenten", en: "Try the support agent" },
    lasMerOm: { sv: "Läs mer om supportagenten", en: "Read more about the support agent" },
    helaDemon: shared.demoSupport,
    demo: "/demo/support",
    ankare: "support",
    panel: "Snajp Support",
    yta: PRODUKTYTOR.inkorg
  }
};

const ORDNING: Agent[] = ["leads", "support"];

/** `*ord*` blir det markerade ordet i textsäker ockra, som `Display` i LandingPhoto. */
function Markerad({ text: varde }: Readonly<{ text: string }>) {
  return (
    <>
      {varde.split(/\*([^*]+)\*/g).map((del, i) =>
        i % 2 === 1 ? (
          <span key={i} className="italic-disp text-warning">
            {del}
          </span>
        ) : (
          <span key={i}>{del}</span>
        )
      )}
    </>
  );
}

/* ------------------------------------------------------------------ Hjälten */

/**
 * En agents yta i hjälten. Tre lager, ett per rörelse (F-030): figuren glider in,
 * `.svav-flyt` svävar i vila och `.svav-lut` lutar sig mot pekaren. Texten under
 * står still, så att ytan läses som den som svävar.
 */
function Svavare({ agent, andra }: Readonly<{ agent: Agent; andra: boolean }>) {
  const { text, locale } = useLocale();
  const a = AGENTER[agent];
  const Yta = a.yta;
  return (
    // data-case: LiveText i ytan skriver fram utkastet när ytan har landat.
    <figure data-mo="svav" data-case className={cn("min-w-0", andra ? "ml-5 md:ml-0 md:mt-24" : "mr-5 md:mr-0")}>
      <div className="svav-flyt">
        <div className="svav-lut">
          {/* YTA: produktens egen yta på fast papper, NOT ett glaskort över fotot (F-006). */}
          <div data-hole className="hem-yta overflow-hidden rounded-panel border border-ink/12 bg-paper">
            <Yta locale={locale} kompakt />
          </div>
        </div>
      </div>
      <figcaption data-svav-text className="mt-5">
        <p className="font-display text-[1.375rem] font-semibold leading-tight tracking-[-0.02em] text-paper">{text(a.namn)}</p>
        <p className="hero-lede mt-1.5 max-w-[36ch] text-[0.9375rem] leading-[1.55] text-paper">{text(a.vad)}</p>
        <div className="mt-1 flex flex-wrap items-center gap-x-6">
          <Link
            href={a.demo}
            className="focus-ring group inline-flex min-h-11 items-center gap-2 rounded-input text-[0.9375rem] font-semibold text-paper"
          >
            {text(a.prova)}
            <span aria-hidden className="transition-transform group-hover:translate-x-0.5">→</span>
          </Link>
          {/* Två "Läs mer" på sidan: aria-label säger vilken agent, och börjar med den synliga texten (WCAG 2.5.3). */}
          <a
            href={`#${a.ankare}`}
            aria-label={text(a.lasMerOm)}
            className="focus-ring inline-flex min-h-11 items-center rounded-input text-[0.9375rem] font-medium text-paper-muted underline underline-offset-4 transition-colors hover:text-paper"
          >
            {text(COPY.lasMer)}
          </a>
        </div>
      </figcaption>
    </figure>
  );
}

export function HemHjalte() {
  const { text, locale } = useLocale();
  return (
    // HERO: 1a:s foto och rubrik, ytorna svävar över himlen. NOT ett produktreglage.
    <section data-mo="hero" data-hole className="relative overflow-hidden bg-ink md:min-h-[100svh]">
      {/* Mobil: fotot har en fast höjd och tonar ut i bläck (hem-scrim), så att
          rubriken står på staden och aldrig på den ljusa horisonten. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        data-mo="hero-img"
        src={photo(imagery.hero.src)}
        alt={text(imagery.hero.alt)}
        className="absolute inset-x-0 top-0 h-[640px] w-full bg-ink object-cover object-center md:h-full"
        fetchPriority="high"
      />
      <div data-mo="hero-scrim" className="hem-scrim absolute inset-0" aria-hidden="true" />

      <div className="relative mx-auto grid max-w-[1480px] grid-cols-12 gap-y-12 px-6 pb-16 pt-[290px] md:min-h-[100svh] md:px-10 md:pb-20 md:pt-36 xl:items-end xl:gap-x-10">
        <div className="col-span-12 xl:col-span-6">
          {/* key per språk: HeroText skriver fram en ny rubrik när språket byts. */}
          <h1
            key={locale}
            data-mo="hero-h1"
            className="max-w-[15ch] font-display text-[clamp(2.25rem,5.6vw,5.5rem)] font-semibold leading-[0.99] tracking-[-0.035em] text-paper"
          >
            <HeroText text={text(COPY.rubrik)} />
          </h1>
          <p data-mo="hero-lede" className="hero-lede mt-7 max-w-[42ch] text-[1.0625rem] leading-[1.65] text-paper">
            {text(landningsPost("/ai-agenter").kort)}
          </p>
        </div>
        <div className="col-span-12 grid gap-12 md:grid-cols-2 md:gap-6 xl:col-span-6 xl:self-center xl:pt-10">
          {ORDNING.map((agent, i) => (
            <Svavare key={agent} agent={agent} andra={i === 1} />
          ))}
        </div>
      </div>
    </section>
  );
}

/* --------------------------------------------------------------- Agenterna */

/**
 * En agents sektion, i Antons ordning (2026-11-07): löftet med produktsidans två
 * rutor direkt under, sedan resultatets tal och panel som sista del före demon,
 * sist demon med texten bredvid. Varje del är ett `steg` eller en ruta som visas
 * när den står helt i bild, i kö efter den förra (useLandingMotion), och
 * resultatets tal räknas först när deras rad har visats (RaknaUpp). Inget
 * skrubbas, så inget backar eller försvinner när man skrollar tillbaka.
 */
export function AgentFlode({ agent, demo }: Readonly<{ agent: Agent; demo: React.ReactNode }>) {
  const { text, locale } = useLocale();
  const a = AGENTER[agent];
  const lofte = LOFTET[agent];
  const resultat = RESULTAT[agent];
  const pc = productCopy[agent];

  return (
    <section id={a.ankare} aria-labelledby={`${a.ankare}-rubrik`} className="relative scroll-mt-6">
      <i aria-hidden="true" data-mo="rule" className="mo-rule" />
      {/* Kort botten, som på produktsidan: rutorna nedanför fortsätter löftets punkter. */}
      <div className="mx-auto max-w-[1480px] px-6 pb-12 pt-24 md:px-10 md:pb-16 md:pt-32">
        {/* LÖFTET: rubrik, ingress och tre punkter i en rad, NOT tre kort. */}
        <p data-mo="steg" className="text-[0.8125rem] font-medium tracking-[0.02em] text-ink-subtle">
          {text(a.etikett)}
        </p>
        <h2
          id={`${a.ankare}-rubrik`}
          data-mo="steg"
          className="mt-4 max-w-[22ch] font-display text-[clamp(2rem,4.6vw,3.5rem)] font-semibold leading-[1.03] tracking-[-0.03em]"
        >
          {text(lofte.rubrik)}
        </h2>
        <p data-mo="steg" className="mt-6 max-w-[58ch] text-[1.125rem] leading-[1.65] text-ink-muted">
          {text(lofte.lede)}
        </p>
        <div className="mt-14 grid gap-8 md:grid-cols-3 md:gap-10">
          {lofte.punkter[locale].map(([rubrik, brod]) => (
            <div key={rubrik} data-mo="steg" className="border-t border-ink/15 pt-5">
              <h3 className="text-[1.0625rem] font-semibold tracking-[-0.01em]">{rubrik}</h3>
              <p className="mt-2 max-w-[42ch] text-[0.9375rem] leading-[1.6] text-ink-muted">{brod}</p>
            </div>
          ))}
        </div>
      </div>

      {/* DE TVÅ RUTORNA under löftet, samma som på produktsidan: de glider in en i
          taget när de står helt i bild, och bildtexten avtäcks när de landat. */}
      <ProduktBilder product={agent} locale={locale} fullt />

      <div className="mx-auto max-w-[1480px] px-6 pb-24 pt-20 md:px-10 md:pb-32 md:pt-28">
        {/* RESULTATET efter rutorna: vad verktyget ger, med talen som räknas fram,
            som sista del före demon. */}
        <div className="grid grid-cols-12 gap-y-12 lg:gap-x-14">
          <div className="col-span-12 lg:col-span-5">
            <h3
              data-mo="steg"
              className="max-w-[16ch] font-display text-[clamp(1.75rem,3.4vw,2.75rem)] font-semibold leading-[1.05] tracking-[-0.03em]"
            >
              <Markerad text={text(resultat.rubrik)} />
            </h3>
            <p data-mo="steg" className="mt-6 max-w-[48ch] text-[1.0625rem] leading-[1.7] text-ink-muted">
              {text(resultat.brod)}
            </p>
            <div data-mo="steg" className="mt-10">
              <StatRad stats={resultat.stats} />
            </div>
          </div>
          <div className="col-span-12 lg:col-span-6 lg:col-start-7">
            {/* Glider in från höger på fjädern när den står helt i bild. */}
            <div data-case data-from="right" data-full>
              {resultat.panel}
            </div>
            <p data-mo="steg" className="mt-4 text-[0.8125rem] font-medium text-ink-subtle">
              {text(RESULTAT_NOT)}
            </p>
          </div>
        </div>

        {/* DEMON: inte i hela bredden; texten bredvid väger upp de mindre rutorna ovanför. */}
        <div
          id={`demo-${a.ankare}`}
          className="mt-28 grid scroll-mt-16 grid-cols-12 items-start gap-y-10 md:mt-36 lg:gap-x-14"
        >
          <div className="col-span-12 lg:sticky lg:top-28 lg:col-span-4 lg:col-start-9 lg:row-start-1">
            <h3
              data-mo="steg"
              className="max-w-[18ch] font-display text-[clamp(1.75rem,3.2vw,2.5rem)] font-semibold leading-[1.06] tracking-[-0.028em]"
            >
              <Markerad text={text(pc.demoHeading)} />
            </h3>
            <p data-mo="steg" className="mt-5 max-w-[40ch] text-[1.0625rem] leading-[1.65] text-ink-muted">
              {text(pc.demoLede)}
            </p>
            {text(pc.exampleNote) ? (
              <p data-mo="steg" className="mt-4 max-w-[40ch] text-[0.8125rem] font-medium text-ink-subtle">
                {text(pc.exampleNote)}
              </p>
            ) : null}
            <div data-mo="steg" className="mt-6">
              <Link
                href={a.demo}
                className="focus-ring group inline-flex min-h-11 items-center gap-2 rounded-input text-[0.9375rem] font-semibold underline underline-offset-4 hover:text-warning"
              >
                {text(a.helaDemon)}
                <span aria-hidden className="transition-transform group-hover:translate-x-0.5">→</span>
              </Link>
            </div>
          </div>
          <div className="col-span-12 lg:col-span-8 lg:row-start-1">
            <div data-case data-from="left" data-full data-hole className="overflow-hidden rounded-panel border border-ink/12 bg-paper">
              <div className="border-b border-ink/10 bg-paper2/60 px-5 py-3.5">
                <span className="text-[0.8125rem] font-medium tracking-[0.02em] text-ink-subtle">{a.panel}</span>
              </div>
              <div className="p-4 sm:p-6">{demo}</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ Gränser */

/**
 * Gränserna för båda agenterna: en spalt per agent, och raden som stod i båda
 * listorna en gång under dem. Samma godkända rader som på produktsidorna.
 */
const gemensamma = leadsCopy.limits.filter((rad) => supportCopy.limits.some((s) => s.sv === rad.sv));

function Rad({ rad }: Readonly<{ rad: Localized }>) {
  const { text } = useLocale();
  return (
    <li data-mo="row" className="flex items-start gap-5 border-t border-paper/15 py-5">
      <span aria-hidden="true" className="mt-[0.6em] h-1.5 w-1.5 shrink-0 rounded-full bg-paper" />
      <span className="text-[1rem] leading-[1.6] text-paper-muted">{text(rad)}</span>
    </li>
  );
}

export function HemGranser() {
  const { text, locale } = useLocale();

  return (
    <section data-mo="band" className="bg-ink text-paper">
      <div className="mx-auto max-w-[1480px] px-6 py-24 md:px-10 md:py-28">
        <h2
          key={locale}
          data-mo="lines"
          className="max-w-[22ch] font-display text-[clamp(1.875rem,3.6vw,2.875rem)] font-semibold leading-[1.06] tracking-[-0.028em]"
        >
          {text(leadsCopy.limitsHeading)}
        </h2>
        <div className="mt-10 grid grid-cols-1 gap-x-14 gap-y-10 md:grid-cols-2">
          {ORDNING.map((agent) => (
            <div key={agent}>
              <h3 className="font-display text-[1.375rem] font-semibold tracking-[-0.015em] text-ochre">
                {text(AGENTER[agent].namn)}
              </h3>
              <ul className="mt-4">
                {productCopy[agent].limits
                  .filter((rad) => !gemensamma.some((g) => g.sv === rad.sv))
                  .map((rad) => (
                    <Rad key={rad.sv} rad={rad} />
                  ))}
              </ul>
            </div>
          ))}
        </div>
        <ul className="mt-2">
          {gemensamma.map((rad) => (
            <Rad key={rad.sv} rad={rad} />
          ))}
        </ul>
      </div>
    </section>
  );
}
