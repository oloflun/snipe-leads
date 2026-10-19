"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import type Lenis from "lenis";
import { Logo } from "@/components/Logo";
import { useLocale } from "@/lib/i18n";
import type { ProductKey } from "@/lib/routes";
import { saljbaraProdukter } from "@/lib/routes";
import { KONTAKT_MEJL, mejlaOss, productCopy, shared, varforSnajp, varforSupport } from "@/components/marketing/copy";
import { imagery, photo, sectionCopy } from "@/components/marketing/copy-sections";
import { AgentResultat } from "@/components/marketing/AgentResultat";
import { HeroText } from "@/components/marketing/LiveText";
import { ProduktBilder } from "@/components/marketing/ProduktBilder";
import { PricingSection } from "@/components/marketing/PricingSection";
import { UspSection } from "@/components/marketing/UspSection";
import { LaddaNerAppen } from "@/components/marketing/LaddaNerAppen";
import { ProductSwitch } from "@/components/marketing/ProductSwitch";
import { Sidfot } from "@/components/marketing/Sidfot";
import { SidMeny } from "@/components/marketing/SidMeny";
import { useLandingMotion } from "@/components/marketing/useLandingMotion";
import { cn } from "@/lib/utils";

/**
 * VERSION E2 — photograph-led.
 *
 * Method taken from the anti-slop-design demos (horai, calyx), read rather than
 * recalled: a real photograph carries the hero at full bleed, display type sits
 * directly on it in paper-white with roman and italic mixed inside one headline,
 * and a mono micro-label anchors the corner. No card, no scrim panel, no
 * "hero illustration".
 *
 * Photographs are verified-existing Unsplash IDs, each one looked at before it
 * was chosen. See copy-sections.ts.
 *
 * 2026-10-18 (Anton): samma sida, men med Dygnets dygnsljus som mark
 * (soluppgång under hjälten, varmvitt längst ned), GSAP + Lenis-övergångar
 * mellan alla sektioner, en isärtagen översikt efter resultatvyn, "Varför
 * Snajp finns" under "Byggt i Göteborg" och Source Serif 4 som serif. Allt
 * rörligt bor i useLandingMotion.ts; markupen bär bara data-mo-markörer.
 * Rubriker som SplitText radspaltar har `key` per produkt och språk, så att
 * React byter noden i stället för att diffa inuti ett element vars barn
 * flyttats.
 */

const pathForProduct: Record<ProductKey, string> = {
  leads: "/leads",
  support: "/support",
  bookkeeping: "/kvitton"
};

function Display({ text: value, accentClass = "italic-disp text-warning" }: Readonly<{ text: string; accentClass?: string }>) {
  return (
    <>
      {value.split(/\*([^*]+)\*/g).map((part, i) =>
        i % 2 === 1 ? (
          <span key={i} className={accentClass}>
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

/**
 * En etikett över en rubrik. Renderar INGENTING när texten är tom: etiketterna
 * "Problemet" och "Var det kommer ifrån" togs bort ur copyn, och utan den här
 * spärren hade en tom <p> lämnat kvar sin marginal ovanför rubriken.
 */
function Label({ children, tone = "ink" }: Readonly<{ children: React.ReactNode; tone?: "ink" | "paper" }>) {
  if (typeof children === "string" && children.trim() === "") return null;

  return (
    <p className={cn("text-[0.8125rem] font-medium tracking-[0.02em]", tone === "ink" ? "text-ink-subtle" : "text-paper-muted")}>
      {children}
    </p>
  );
}

export function LandingPhoto({
  initial,
  leadsDemo,
  supportDemo
}: Readonly<{
  initial: ProductKey;
  leadsDemo: React.ReactNode;
  supportDemo: React.ReactNode;
}>) {
  const { text, locale, toggleLocale } = useLocale();
  const [product, setProduct] = useState<ProductKey>(initial);
  const demoRef = useRef<HTMLDivElement | null>(null);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const lenisRef = useRef<Lenis | null>(null);

  useLandingMotion({ root: rootRef, lenis: lenisRef }, product, locale);

  useEffect(() => {
    const next = pathForProduct[product];
    if (window.location.pathname !== next) window.history.replaceState(null, "", next);
  }, [product]);

  const scrollToDemo = useCallback(() => {
    const el = demoRef.current;
    if (!el) return;
    // Lenis äger skrollen när den finns; scrollIntoView hade slagits med den.
    if (lenisRef.current) lenisRef.current.scrollTo(el, { offset: -64 });
    else el.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const copy = productCopy[product];
  const sec = sectionCopy[product];
  const nyckel = `${product}-${locale}`;

  return (
    <div ref={rootRef} className="landing serif-fet min-h-screen text-ink">
      {/* Dörren före första målningen: körs av webbläsaren medan HTML:en
          tolkas, alltså innan hjälten nedanför målas. Ett <style> i <head>
          (som React inte äger: en klass på <html> gav hydreringsvarning)
          döljer hjältens delar tills rörelsen tagit över med samma värden
          inline och tar bort det (useLandingMotion), eller tills timern
          tar bort det efter 3 s om modulen aldrig laddar. React kör aldrig
          om ett inline-skript på klienten, så vid en klientnavigering hit
          spelas dörren inte om. */}
      <script
        dangerouslySetInnerHTML={{
          __html:
            "(function(){var s=document.createElement('style');s.id='door-armed';s.textContent='.landing [data-mo=hero-h1],.landing [data-mo=hero-lede],.landing [data-mo=hero-acts],.landing [data-mo=hero-side],.landing [data-mo=header]{opacity:0}.landing [data-mo=hero-img]{transform:scale(1.06)}.landing [data-mo=hero-scrim]{opacity:.4}';document.head.appendChild(s);setTimeout(function(){s.remove()},3000)})();"
        }}
      />
      {/* Dygnsljuset: marken och ljuslagret skrivs bara av ljusmotorn i useLandingMotion. */}
      <div data-mo="ground" className="ground" aria-hidden="true" />
      <div data-mo="light" className="light" aria-hidden="true">
        <div className="light__panes"><i /><i /><i /><i /></div>
      </div>
      <a
        href="#demo"
        className="focus-ring sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-input focus:bg-ink focus:px-4 focus:py-2 focus:text-paper"
      >
        {text(shared.skipToContent)}
      </a>

      {/* Header sits over the photograph, so it carries no ground of its own. */}
      <header data-mo="header" className="absolute inset-x-0 top-0 z-30">
        {/* `items-start`, inte `items-center`. Märket är nu flera gånger högre
            än kontrollerna, och centrerat hade raden hamnat mitt på logotypen i
            stället för i överkant — se utkastet: båda börjar på samma höjd och
            märket växer nedåt. */}
        {/* 2026-08-25: padding halverad i takt med att märket krympte 50% —
            annars stod den gamla luften kvar runt en mycket mindre logotyp. */}
        <div className="mx-auto flex max-w-[1480px] items-start justify-between gap-4 px-6 pb-3 pt-[clamp(9px,1.7vw,26px)] md:px-10">
          <Link href="/" className="focus-ring inline-flex items-center rounded-input text-paper">
            <Logo tone="paper" hjalte />
          </Link>
          {/* `whitespace-nowrap`: kontrollerna får krympa i mellanrum, aldrig
              brytas mitt i ett ord. "Logga in" blev "Logga / in" på 390px när
              logotypen växte, och en tvåradig länk i en enradig rad ser ut som
              ett fel även när den är läsbar. */}
          <div className="flex items-center gap-1 whitespace-nowrap sm:gap-2">
            <button
              type="button"
              onClick={toggleLocale}
              className="focus-ring min-h-11 rounded-input px-3 text-sm font-medium text-paper-muted transition-colors hover:text-paper"
            >
              {locale === "sv" ? "EN" : "SV"}
            </button>
            <Link
              href="/login"
              className="focus-ring inline-flex min-h-11 items-center rounded-input px-3 text-sm font-medium text-paper-muted transition-colors hover:text-paper"
            >
              {text(shared.navLogin)}
            </Link>
            <a
              href={mejlaOss()}
              className="focus-ring hidden min-h-11 items-center rounded-input border border-paper/35 px-5 text-sm font-semibold text-paper transition-colors hover:bg-paper hover:text-ink sm:inline-flex"
            >
              {text(shared.secondaryCta)}
            </a>
            {/* Menyn sist i raden, efter den primära uppmaningen. Det som ska
                sticka ut är "Skriv till oss"; det här är sådant som är bra att
                hitta men som ingen kom hit för att göra. */}
            <SidMeny />
          </div>
        </div>
      </header>

      <main id="main">
        {/* HERO. The photograph is the design. Type sits on it directly. */}
        {/* data-hole: hjälten lyfts ur dygnsljuset och står som den är. */}
        <section data-mo="hero" data-hole className="relative min-h-[92vh] overflow-hidden">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            data-mo="hero-img"
            src={photo(imagery.hero.src)}
            alt={text(imagery.hero.alt)}
            className="absolute inset-0 h-full w-full bg-ink object-cover object-center"
            fetchPriority="high"
          />
          {/* Two scrims: one for the header, one carrying the headline block. */}
          <div
            data-mo="hero-scrim"
            className="absolute inset-0"
            aria-hidden="true"
            style={{
              background:
                "linear-gradient(to bottom, oklch(var(--ink) / 0.55) 0%, oklch(var(--ink) / 0.18) 28%, oklch(var(--ink) / 0.30) 55%, oklch(var(--ink) / 0.82) 100%)"
            }}
          />
          {/* Mobil: ingressen hamnar över den ljusa horisonten. Ett mjukt
              mörkare band i fotot, inte en skugga bakom texten. */}
          <div aria-hidden="true" className="hero-band absolute inset-0 lg:hidden" />

          <div className="relative mx-auto flex min-h-[92vh] max-w-[1480px] flex-col justify-end px-6 pb-14 pt-32 md:px-10 md:pb-20">
            <div className="max-w-[min(100%,980px)]">
              <p
                key={nyckel}
                data-mo="hero-h1"
                className="font-display text-[clamp(2.25rem,5.9vw,5.75rem)] font-semibold leading-[0.99] tracking-[-0.035em] text-paper"
              >
                <HeroText text={text(copy.headline)} />
              </p>
            </div>

            <div className="mt-10 grid grid-cols-12 gap-y-8 lg:gap-x-10">
              <div className="col-span-12 lg:col-span-5">
                {/* Helt papper och en mjuk skugga, inte paper-muted: på mobil
                    hamnar ingressen över den ljusa horisonten i fotot och var
                    knappt läsbar (Anton 2026-10-19). */}
                <p data-mo="hero-lede" className="hero-lede max-w-[46ch] text-[1.0625rem] leading-[1.65] text-paper">
                  {text(copy.lede)}
                </p>
                <div data-mo="hero-acts" className="mt-8 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={scrollToDemo}
                    className="focus-ring inline-flex min-h-12 items-center rounded-input bg-paper px-6 text-[0.9375rem] font-semibold text-ink transition-colors hover:bg-paper2"
                  >
                    {text(copy.cta)}
                  </button>
                  <a
                    href={mejlaOss()}
                    className="focus-ring inline-flex min-h-12 items-center rounded-input border border-paper/40 px-6 text-[0.9375rem] font-semibold text-paper transition-colors hover:border-paper"
                  >
                    {text(shared.secondaryCta)}
                  </a>
                </div>
              </div>

              {/* Blocket ankras mot sidhuvudet, inte mot kolumnen.
                  `w-[219px]` plus `ml-auto` gör att innehållet börjar exakt
                  219px från kolumnens högerkant — och det är mittlinjen mellan
                  "Logga in" och "Skriv till oss" i sidhuvudet ovanför.
                  Uppmätt vid tre bredder, och avståndet är DETSAMMA i alla tre
                  (1280, 1440, 1600) eftersom både sidhuvudets poster och den här
                  kolumnen är högerankrade. Därför håller linjen utan media
                  queries.
                  219px räcker: bredaste innehållet är "Prova kundtjänstagenten →"
                  på 200px. Krymper man det måttet bryter den länken till två
                  rader.
                  Beroendet är värt att känna till: byter sidhuvudets etiketter
                  längd — till exempel i engelsk lokalisering — flyttar mittlinjen
                  och siffran här stämmer inte längre. */}
              <div data-mo="hero-side" className="col-span-12 self-end lg:col-span-3 lg:col-start-10 lg:ml-auto lg:w-[219px]">
                {/* 1.1875rem och inte 1.5rem. Tre produkter på EN rad mäter
                    257px vid 24px, och kolumnen är 219 — den gamla graden
                    tvingade fram en radbrytning som lade "Bokföring" under
                    "Leads", alltså till vänster om "Support".
                    Graden är uppmätt vid båda språken och det är ENGELSKAN som
                    sätter den: "Bookkeeping" är 25px bredare än "Bokföring",
                    och vid 21px låg dess högerkant 20px utanför kolumnen. Byts
                    ett produktnamn mot ett längre ord måste måttet mätas om —
                    raden kan inte längre brytas, den skulle sticka ut i stället. */}
                <div className="font-display text-[1.1875rem] leading-[1.15] tracking-[-0.02em] text-paper">
                  <ProductSwitch value={product} onChange={setProduct} tone="paper" />
                </div>
                {/* Under växeln, inte bredvid.
                    Bredvid krävde en fjärde kolumn, och den bredden drog hela
                    blocket ur högerkanten — växeln började 92px längre in.
                    Staplat får båda: knappen ryms i tre kolumner (148px av
                    ~290px) och blocket hänger kvar längst ut. */}
                <div className="mt-4">
                  <LaddaNerAppen tone="paper" />
                </div>
                {/* Tre vägar rakt in i produkten, en per agent.
                    Växeln ovanför byter vad SIDAN beskriver; de här tar
                    besökaren till agenten som gör det. Att bara kunna läsa om
                    en agent på en sida som har en fungerande demo är att gömma
                    det enda som övertygar.
                    Kvittohanterarens länk togs bort 2026-10-17: den är ett
                    vilande tillägg till Support och säljs inte (lib/routes.ts). */}
                <div className="mt-5 flex flex-col gap-2 border-t border-paper/25 pt-4">
                  <Link
                    href="/demo/leads"
                    className="focus-ring group inline-flex items-center gap-2 text-[0.9375rem] font-medium text-paper-muted transition-colors hover:text-paper"
                  >
                    {text(shared.demoLeads)}
                    <span aria-hidden className="transition-transform group-hover:translate-x-0.5">→</span>
                  </Link>
                  <Link
                    href="/demo/support"
                    className="focus-ring group inline-flex items-center gap-2 text-[0.9375rem] font-medium text-paper-muted transition-colors hover:text-paper"
                  >
                    {text(shared.demoSupport)}
                    <span aria-hidden className="transition-transform group-hover:translate-x-0.5">→</span>
                  </Link>
                </div>

                <div className="mt-4">
                  {/* "Sverige · GDPR · RLS" stod här. Två av tre var interna
                      förkortningar — RLS är en databasmekanism — och en
                      besökare som inte bygger programvara läser raden som brus.
                      Efterlevnaden finns kvar, i sidfoten, med plats att
                      förklaras. */}
                  <Label tone="paper">{text(shared.heroTrust)}</Label>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* LÖFTET, direkt efter hjältebilden. Det här är det första en
            besökare läser efter rubriken, och det ska svara på "vad får jag"
            innan sidan hinner beskriva problemet. */}
        <UspSection product={product} />

        {/* PRODUKTBILDERNA. Ersatte problemtexten 2026-09-21: två renderade
            produktytor per agent (widget + inkorg, utkast + leadslista,
            kvitton + verifikat), med sidorna växlade per flik. Texten som
            stod här bar problemet i ord; ytorna visar det i stället.
            Se components/marketing/ProduktBilder.tsx. */}
        <ProduktBilder product={product} locale={locale} />


        {/* STATEMENT. One line, a photograph almost fully darkened behind it.
            The page needs a moment that is not information. */}
        {/* data-mo="band": bandet skrubbas fram ur marken, fotot glider sakta
            bakom orden, och orden fylls av sin egen position i vyn. */}
        <section data-mo="band" className="relative overflow-hidden">
          <div
            data-parallax
            className="parallax absolute -inset-y-[8%] inset-x-0 bg-ink"
            aria-hidden="true"
            style={{ backgroundImage: `url(${photo(imagery.street.src)})` }}
          />
          <div
            className="absolute inset-0"
            aria-hidden="true"
            /* Two layers. The ink gradient darkens; the ochre wash pulls the
               photograph back toward the palette. The Haga street is cool cream
               and green, and under ink alone the whole band read blue against a
               warm page. Same fix the facade divider needed. */
            style={{
              background:
                "linear-gradient(to bottom, oklch(var(--ink) / 0.93), oklch(var(--ink) / 0.86)), " +
                "linear-gradient(to bottom, oklch(var(--ochre) / 0.10), oklch(var(--ochre) / 0.06))"
            }}
          />
          <div className="relative mx-auto max-w-[1480px] px-6 py-28 text-center md:px-10 md:py-40">
            <p className="text-[0.8125rem] font-medium tracking-[0.14em] text-warning">
              {text(sec.statementLabel).toUpperCase()}
            </p>
            <p
              key={nyckel}
              data-mo="words"
              className="mx-auto mt-8 max-w-[20ch] font-display text-[clamp(2rem,5.2vw,4.5rem)] font-semibold leading-[1.12] tracking-[-0.005em] text-paper"
            >
              {text(sec.statement)}
            </p>
          </div>
        </section>

        {/* DEMO. */}
        <section id="demo" ref={demoRef} className="scroll-mt-16 bg-paper2/45">
          <div className="mx-auto max-w-[1480px] px-6 py-24 md:px-10 md:py-28">
            <div className="max-w-[50ch]">
              <h2
                key={nyckel}
                data-mo="lines"
                className="font-display text-[clamp(1.875rem,3.6vw,2.875rem)] font-semibold leading-[1.06] tracking-[-0.028em]"
              >
                <Display text={text(copy.demoHeading)} />
              </h2>
              <p data-mo="up" className="mt-4 text-[1.0625rem] leading-[1.65] text-ink-muted">{text(copy.demoLede)}</p>
            </div>
            <div data-case data-from="up" data-hole className="mt-10 overflow-hidden rounded-panel border border-ink/12 bg-paper">
              <div className="flex items-center justify-between gap-4 border-b border-ink/10 bg-paper2/60 px-5 py-3.5">
                {/* Etiketten per produkt, inte "allt som inte är leads är
                    support": den grenen visade "Snajp Support" ovanför
                    bokföringsdemon — fel produktnamn på en sida som säljer en
                    annan produkt. */}
                <span className="text-[0.8125rem] font-medium tracking-[0.02em] text-ink-subtle">
                  {product === "leads" ? "Email Studio" : "Snajp Support"}
                </span>
                {/* Ingen statusuppgift här: supportchatten rapporterar sitt
                    eget läge, och backenden kan gå i simulering. Två sanningar
                    på samma panel är en för mycket. */}
              </div>
              <div className="p-4 sm:p-6 md:p-8">
              {saljbaraProdukter.map((key) => (
                <div
                  key={key}
                  id={`product-panel-${key}`}
                  role="tabpanel"
                  aria-labelledby={`product-tab-${key}`}
                  hidden={key !== product}
                >
                  {/* En gren per produkt. Tvågrenaren `leads ? … : supportDemo`
                      lät bokföringsfliken rendera supportchatten — fel agent,
                      fel varumärkesetikett ("Nordlys Handel") och fel
                      förslagsfrågor på /bokforing. */}
                  {/* Bara säljbara produkter har en panel (lib/routes.ts:
                      saljbaraProdukter). Kvittodemon (KvittoDemo) kopplas in här
                      igen när tillägget släpps. */}
                  {key === "leads" ? leadsDemo : supportDemo}
                </div>
              ))}
              </div>
            </div>
            {/* Label renders its own <p>, so the wrapper is a div. It was a <p>
                and nested paragraphs are invalid HTML: React bailed out of
                hydration and re-rendered the whole page on the client. */}
            {/* Label renderar sin egen <p>, så omslaget är en div. Det var en
                <p>, och nästlade stycken är ogiltig HTML: React avbröt
                hydreringen och renderade om hela sidan på klienten.
                Leads-demon har ingen finstilt rad; Label returnerar null då. */}
            <div className="mt-4"><Label>{text(copy.exampleNote)}</Label></div>
          </div>
        </section>

        {/* RESULTATVYN. Direkt efter demon: besökaren har just provat HUR
            agenten arbetar, det här visar VAD arbetet ger — per agent, med
            exempeldata inuti produktpanelen och en rad som säger det. Se
            components/marketing/AgentResultat.tsx för förebilderna. */}
        <AgentResultat product={product} />

        {/* PLACE. Photograph and copy share the row; the image is content here,
            not decoration, so it carries a real alt. */}
        <section data-mo="place">
          <div className="mx-auto grid max-w-[1480px] grid-cols-12 items-center gap-y-10 px-6 py-24 md:px-10 md:py-32 lg:gap-x-14">
            {/* Avtäcks från vänster, fotot glider sakta i sin ram. */}
            <figure data-mo="plate" data-dir="left" className="col-span-12 overflow-hidden rounded-panel bg-paper2 lg:col-span-7 lg:-ml-6 lg:rounded-l-none xl:-ml-10">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                data-parallax
                src={photo(imagery.street.src)}
                alt={text(imagery.street.alt)}
                loading="lazy"
                className="h-[380px] w-full object-cover md:h-[600px]"
              />
            </figure>
            <div className="col-span-12 lg:col-span-4 lg:col-start-9">
              <Label>{text(sec.placeLabel)}</Label>
              {/* 16ch, inte 15: SplitText mäter accentens ord och punkten
                  efter som egna block, och vid 15ch föll punkten i
                  "effektivisera arbetet." ensam på en fjärde rad. */}
              <h2
                key={nyckel}
                data-mo="lines"
                className="mt-5 max-w-[16ch] font-display text-[clamp(2rem,4.2vw,3.25rem)] font-semibold leading-[1.04] tracking-[-0.03em]"
              >
                <Display text={text(sec.placeHeading)} />
              </h2>
              <p data-mo="up" className="mt-6 max-w-[44ch] text-[1.0625rem] leading-[1.7] text-ink-muted">
                {text(sec.placeBody)}
              </p>
              {/* "Varför Snajp finns" från /vart-team, styckena utan rubriken
                  (Anton 2026-10-18). Samma källa som teamsidan: copy.ts. */}
              {(product === "support" ? varforSupport : varforSnajp).map((stycke) => (
                <p key={stycke.sv.slice(0, 24)} data-mo="up" className="mt-5 max-w-[44ch] text-[1rem] leading-[1.7] text-ink-muted">
                  {text(stycke)}
                </p>
              ))}
              {/* Länken till teamsidan flyttade hit när "Vilka är vi" togs bort:
                  utan den nås /vart-team bara via den hopfällda menyn. */}
              <Link
                href="/vart-team"
                data-mo="up"
                className="focus-ring mt-7 inline-block text-[0.9375rem] font-medium underline underline-offset-4 hover:text-ochre"
              >
                {text(shared.vilkaLank)}
              </Link>
            </div>
          </div>
        </section>

        {/* "Tre steg" och "Vilka är vi" togs bort 2026-10-19 (Anton): stegen
            upprepade löftets punkter under hjälten, och Vilka är vi upprepade
            Byggt i Göteborg, som står kvar och bär länken till teamsidan. */}

        {/* DIVIDER. A facade of identical windows under a heavy scrim: the flat
            run of text sections needed one more break, and the image rhymes with
            "the same email to a hundred companies". */}
        <section data-mo="band" className="relative h-[220px] overflow-hidden md:h-[300px]">
          <div
            data-parallax
            className="parallax absolute -inset-y-[10%] inset-x-0 bg-seal"
            aria-hidden="true"
            style={{ backgroundImage: `url(${photo(imagery.grid.src)})` }}
          />
          <div
            className="absolute inset-0"
            aria-hidden="true"
            style={{
              background:
                "linear-gradient(to bottom, oklch(var(--ink) / 0.90), oklch(var(--ink) / 0.80)), radial-gradient(120% 100% at 50% 100%, oklch(var(--ochre) / 0.22) 0%, transparent 70%)"
            }}
          />
        </section>

        {/* OBJECTIONS. Real questions, answered plainly. */}
        <section id="fragor" className="relative scroll-mt-24 bg-paper2/40">
          <i aria-hidden="true" data-mo="rule" className="mo-rule" />
          <div className="mx-auto max-w-[1480px] px-6 py-24 md:px-10 md:py-32">
            <div className="grid grid-cols-12 gap-y-12 lg:gap-x-14">
              <div className="col-span-12 lg:col-span-4">
                <h2
                  key={nyckel}
                  data-mo="lines"
                  className="max-w-[14ch] font-display text-[clamp(1.875rem,3.6vw,2.875rem)] font-semibold leading-[1.06] tracking-[-0.028em]"
                >
                  <Display text={text(sec.objectionsHeading)} />
                </h2>
              </div>
              <dl className="col-span-12 lg:col-span-7 lg:col-start-6">
                {sec.objections.map((item) => (
                  <div key={item.q.sv} data-mo="row" className="hrule py-7 first:border-t-0 first:pt-0">
                    <dt className="font-display text-[1.25rem] font-semibold leading-snug tracking-[-0.015em]">
                      {text(item.q)}
                    </dt>
                    <dd className="mt-3 max-w-[62ch] text-[1rem] leading-[1.7] text-ink-muted">
                      {text(item.a)}
                    </dd>
                  </div>
                ))}
                {/* De tre ovan är produktens invändningar, valda för att de
                    kommer FÖRST. Resten — pris, uppsägning, var datan kommer
                    ifrån, hur GDPR hanteras — bor på /faq, eftersom de ställs
                    av någon som redan bestämt sig för att titta närmare och
                    inte hör hemma mitt i argumentet. */}
                <Link
                  href="/faq"
                  data-mo="up"
                  className="focus-ring mt-8 inline-block text-[0.9375rem] font-medium underline underline-offset-4 hover:text-ochre"
                >
                  {text(shared.fragorLank)}
                </Link>
              </dl>
            </div>
          </div>
        </section>

        {/* LIMITS on ink, then the close. */}
        <section data-mo="band" className="bg-ink text-paper">
          <div className="mx-auto max-w-[1480px] px-6 py-24 md:px-10 md:py-28">
            <h2
              key={nyckel}
              data-mo="lines"
              className="max-w-[22ch] font-display text-[clamp(1.875rem,3.6vw,2.875rem)] font-semibold leading-[1.06] tracking-[-0.028em]"
            >
              {text(copy.limitsHeading)}
            </h2>
            <ul className="mt-10 grid grid-cols-1 gap-x-14 md:grid-cols-2">
              {copy.limits.map((limit) => (
                <li key={limit.sv} data-mo="row" className="flex items-start gap-5 border-t border-paper/15 py-5">
                  {/* Punkt, inte siffra. Numreringen läste som en rangordning
                      av spärrar som gäller lika mycket allihop. Punkten är vit
                      medan texten behåller sin dämpade ton. */}
                  <span aria-hidden="true" className="mt-[0.6em] h-1.5 w-1.5 shrink-0 rounded-full bg-paper" />
                  <span className="text-[1rem] leading-[1.6] text-paper-muted">{text(limit)}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Priset är den sista frågan läsaren har innan kontaktuppmaningen,
            alltså före avslutningssektionen och inte efter den. */}
        <PricingSection />

        <section data-mo="plate" className="relative overflow-hidden">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            data-parallax
            src={photo(imagery.desk.src)}
            alt={text(imagery.desk.alt)}
            loading="lazy"
            className="absolute inset-0 h-full w-full bg-paper2 object-cover"
          />
          <div
            className="absolute inset-0"
            aria-hidden="true"
            style={{ background: "linear-gradient(to right, oklch(var(--paper) / 0.94) 0%, oklch(var(--paper) / 0.72) 38%, oklch(var(--paper) / 0.10) 78%, transparent 100%)" }}
          />
          <div className="relative mx-auto min-h-[520px] max-w-[1480px] px-6 py-28 md:min-h-[600px] md:px-10 md:py-36">
            <div className="max-w-[30ch]">
              <h2
                key={nyckel}
                data-mo="lines"
                className="font-display text-[clamp(2.25rem,5vw,3.75rem)] font-semibold leading-[1.02] tracking-[-0.03em]"
              >
                <Display text={text(shared.closingHeading)} />
              </h2>
              <p data-mo="row" className="mt-6 max-w-[46ch] text-[1.0625rem] leading-[1.7] text-ink-muted">
                {text(shared.closingBody)}
              </p>
              <a
                href={mejlaOss()}
                data-mo="row"
                className="focus-ring mt-9 inline-flex min-h-12 items-center rounded-input bg-ink px-7 text-[1rem] font-semibold text-paper transition-colors hover:bg-ink2"
              >
                {text(shared.closingCta)}
              </a>
            </div>
          </div>
        </section>
      </main>

      {/* Sidfoten bär numera det som stod i hjältebilden — och mer, eftersom
          det finns plats att förklara här. Tre kolumner: vilka vi är, hur man
          når oss, och vad som gäller kunddata. Den sista är inte en
          artighetsrad: den är den vanligaste invändningen i svensk B2B, och ett
          svar på tre förkortningar duger inte som svar. */}
      <footer className="relative">
        <i aria-hidden="true" data-mo="rule" className="mo-rule" />
        <div className="mx-auto max-w-[1480px] px-6 py-12 md:px-10 md:py-16">
          <div className="grid grid-cols-12 gap-y-10 lg:gap-x-12">
            <div data-mo="row" className="col-span-12 lg:col-span-4">
              <Logo />
              <p className="mt-4 text-[0.875rem] text-ink-subtle">{text(shared.footerPlats)}</p>
            </div>

            <div id="kontakt" data-mo="row" className="col-span-12 scroll-mt-24 sm:col-span-5 lg:col-span-3">
              <Label>{text(shared.footerKontakt)}</Label>
              <a
                href={mejlaOss()}
                className="focus-ring mt-4 inline-block text-[1.0625rem] font-medium underline underline-offset-4 hover:text-ochre"
              >
                {KONTAKT_MEJL}
              </a>
            </div>

            <div id="dataskydd" data-mo="row" className="col-span-12 scroll-mt-24 sm:col-span-7 lg:col-span-5">
              {/* Etiketten "Dataskydd" är borttagen; rubriken under säger redan
                  vad stycket handlar om. Ankaret #dataskydd finns kvar, menyn
                  pekar på det. */}
              <h2 className="max-w-[28ch] text-[1.0625rem] font-semibold leading-snug tracking-[-0.01em]">
                {text(shared.gdprRubrik)}
              </h2>
              <p className="mt-3 max-w-[52ch] text-[0.9375rem] leading-[1.6] text-ink-muted">
                {text(shared.gdprText)}
              </p>
              {/* Ersätter raden "Sverige · GDPR · RLS". Tre förkortningar var
                  ett påstående utan täckning; en länk till dokumentet är ett
                  påstående som går att kontrollera — och det är den enda
                  sortens trygghetssignal som håller för en inköpares jurist. */}
              <Link
                href="/integritetspolicy"
                className="focus-ring mt-4 inline-block text-[0.9375rem] font-medium underline underline-offset-4 hover:text-ochre"
              >
                {text(shared.gdprLank)}
              </Link>
            </div>
          </div>
        </div>

        {/* Bolagsidentifikationen och de juridiska länkarna. Egen komponent
            därför att de måste finnas på VARJE publik sida, inte bara här —
            se components/marketing/Sidfot.tsx. */}
        <Sidfot />
      </footer>
    </div>
  );
}
