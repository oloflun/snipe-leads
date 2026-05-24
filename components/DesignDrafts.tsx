"use client";

import { createContext, useContext } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  Building2,
  ChartNoAxesColumn,
  CircleDot,
  Mail,
  MessageSquare,
  Search,
  Settings,
  Sparkles,
  UsersRound
} from "lucide-react";
import {
  analyticsSeries,
  businessContext,
  campaigns,
  companies,
  contacts,
  emailVariants,
  findCampaign,
  findCompany,
  findContact,
  workflowSteps
} from "@/lib/mock-data";
import type { Company, Contact } from "@/lib/mock-data";
import type { DraftVariant } from "@/lib/design-drafts";
import { useLocale } from "@/lib/i18n";
import type { Localized } from "@/lib/i18n";
import { cn, formatCurrency, formatDate, formatPercent } from "@/lib/utils";

// ─── Portal nav context ──────────────────────────────────────────────────────
// Holds the base path for all internal portal links so the portal renders
// correctly both at /design-drafts/editorial-clean/portal and at /dashboard.

const PortalNavContext = createContext("/design-drafts/editorial-clean/portal");
function usePortalNav() { return useContext(PortalNavContext); }

// ─── Static data ────────────────────────────────────────────────────────────

const customerBand = [
  "Bergslagens Plåt",
  "Fjord Fastigheter",
  "Havre Restauranggrupp",
  "Lyft Gymkedja",
  "Klaravik Fastighet",
  "Care Nordic",
  "Måleri & Skala",
  "Sundsval Logistik",
  "Granér Revision",
  "Södra Dataateljén"
];

const landingSignals: { title: Localized; body: Localized }[] = [
  {
    title: { sv: "Signaler", en: "Signals" },
    body: { sv: "Nya lokaler, rekrytering, tjänstesidor och lokala nyheter blir konkreta öppningar.", en: "New offices, hiring, service pages and local news become concrete entry points." }
  },
  {
    title: { sv: "Tonläge", en: "Tone" },
    body: { sv: "Produkt, målgrupp, erbjudande och CTA följer med varje emailvariant.", en: "Product, audience, offer and CTA carry through every email variant." }
  },
  {
    title: { sv: "Skickhälsa", en: "Inbox health" },
    body: { sv: "Mailbox, suppression och stop-on-reply ligger nära sekvensen.", en: "Mailbox, suppression and stop-on-reply stay close to the sequence." }
  },
  {
    title: { sv: "Lärande", en: "Learning" },
    body: { sv: "Svar, möten och segment kopplas tillbaka till nästa prioritering.", en: "Replies, meetings and segments feed back into the next prioritisation." }
  }
];

const modernNavItems = [
  { href: "portal",              sv: "Översikt",      en: "Overview"    },
  { href: "portal/assistant",    sv: "AI-assistent",  en: "AI Assistant" },
  { href: "portal/leads",        sv: "Leads",         en: "Leads"       },
  { href: "portal/companies",    sv: "Företag",       en: "Companies"   },
  { href: "portal/contacts",     sv: "Kontakter",     en: "Contacts"    },
  { href: "portal/campaigns",    sv: "Kampanjer",     en: "Campaigns"   },
  { href: "portal/emails",       sv: "Email studio",  en: "Email studio" },
  { href: "portal/analytics",    sv: "Analys",        en: "Analytics"   },
  { href: "portal/inbox",        sv: "Inkorg",        en: "Inbox"       },
  { href: "portal/settings",     sv: "Inställningar", en: "Settings"    }
];

const scrollSections: { id: string; kicker: Localized; title: Localized; desc: Localized }[] = [
  {
    id: "overview",
    kicker: { sv: "Vecka 21", en: "Week 21" },
    title: { sv: "Outboundöversikt", en: "Outbound overview" },
    desc: { sv: "Prioriterade konton, svar och nästa handling.", en: "Priority accounts, replies and next action." }
  },
  {
    id: "leads",
    kicker: { sv: "Discovery", en: "Discovery" },
    title: { sv: "Lead discovery", en: "Lead discovery" },
    desc: { sv: "Sparade sökningar och bolag sorterade efter timing.", en: "Saved searches and companies sorted by timing." }
  },
  {
    id: "assistant",
    kicker: { sv: "Assistant", en: "Assistant" },
    title: { sv: "AI-assistent", en: "AI assistant" },
    desc: { sv: "Sök, analysera och skriv i arbetsflödet.", en: "Search, analyse and write within the workflow." }
  },
  {
    id: "companies",
    kicker: { sv: "Companies", en: "Companies" },
    title: { sv: "Företagsintelligens", en: "Company intelligence" },
    desc: { sv: "Bolag, källor, vinklar och rekommenderad CTA.", en: "Companies, sources, angles and recommended CTA." }
  },
  {
    id: "campaigns",
    kicker: { sv: "Campaigns", en: "Campaigns" },
    title: { sv: "Kampanjer och sekvenser", en: "Campaigns and sequences" },
    desc: { sv: "Sekvenssteg, volym och utfall samlat per segment.", en: "Sequence steps, volume and outcome per segment." }
  },
  {
    id: "emails",
    kicker: { sv: "Email studio", en: "Email studio" },
    title: { sv: "Email studio", en: "Email studio" },
    desc: { sv: "Personalisering, signaler och CTA i samma skrivyta.", en: "Personalisation, signals and CTA in one workspace." }
  },
  {
    id: "analytics",
    kicker: { sv: "Analytics", en: "Analytics" },
    title: { sv: "Resultat och signaler", en: "Results and signals" },
    desc: { sv: "Utskick, svar och möten per vecka och segment.", en: "Sends, replies and meetings per week and segment." }
  },
  {
    id: "inbox",
    kicker: { sv: "Inbox", en: "Inbox" },
    title: { sv: "Inkorg", en: "Inbox" },
    desc: { sv: "Svar klassificeras så teamet ser nästa steg.", en: "Replies classified so the team sees what to do next." }
  }
];

const pageCopy = {
  dashboard: ["Vecka 21", "Outboundöversikt", "Prioriterade konton, svar och nästa handling."],
  assistant: ["Assistant", "AI-assistent", "Sök, analysera och skriv i arbetsflödet."],
  leads: ["Discovery", "Lead discovery", "Sparade sökningar och bolag sorterade efter timing."],
  companies: ["Companies", "Företagsintelligens", "Bolag, källor, vinklar och rekommenderade CTA."],
  contacts: ["Contacts", "Kontaktpersoner med roll och källa", "Roll, bolag, provider och status."],
  campaigns: ["Campaigns", "Kampanjer och sekvenser", "Sekvenssteg, volym och utfall per segment."],
  emails: ["Email studio", "Email studio", "Personalisering, signaler och CTA i samma skrivyta."],
  analytics: ["Analytics", "Resultat och signaler", "Utskick, svar och möten per vecka och segment."],
  inbox: ["Inbox", "Inkorg", "Svar klassificeras så teamet ser nästa steg."],
  settings: ["Admin", "Inställningar", "Business context, mailboxes, teamroller och billing."]
} satisfies Record<string, [string, string, string]>;

// ─── Helpers ────────────────────────────────────────────────────────────────

function draftPath(variant: DraftVariant, href = "") {
  return `/design-drafts/${variant}/${href}`.replace(/\/$/, "");
}

function otherVariant(variant: DraftVariant): DraftVariant {
  return variant === "editorial-clean" ? "modern-blend" : "editorial-clean";
}

function isModern(variant: DraftVariant) {
  return variant === "modern-blend";
}

function surface(variant: DraftVariant) {
  return isModern(variant)
    ? "rounded-[18px] border border-ink/10 bg-paper/78 shadow-[0_28px_90px_oklch(var(--ink)/0.08)]"
    : "border-y border-ink/15 bg-paper/42";
}

// ─── Route parsing ──────────────────────────────────────────────────────────

type PortalRoute =
  | { kind: "dashboard"; navKey: string }
  | { kind: "assistant"; navKey: string }
  | { kind: "leads"; navKey: string }
  | { kind: "companies"; navKey: string; id?: string }
  | { kind: "contacts"; navKey: string; id?: string }
  | { kind: "campaigns"; navKey: string; id?: string }
  | { kind: "emails"; navKey: string }
  | { kind: "analytics"; navKey: string }
  | { kind: "inbox"; navKey: string }
  | { kind: "settings"; navKey: string; section: "general" | "mailboxes" | "team" | "billing" };

function parsePortalSlug(slug: string[]): PortalRoute {
  const [first, second] = slug;
  if (!first) return { kind: "dashboard", navKey: "portal" };
  if (first === "companies") return { kind: "companies", navKey: "companies", id: second };
  if (first === "contacts") return { kind: "contacts", navKey: "contacts", id: second };
  if (first === "campaigns") return { kind: "campaigns", navKey: "campaigns", id: second };
  if (first === "settings") {
    const section = ["mailboxes", "team", "billing"].includes(second) ? second : "general";
    return { kind: "settings", navKey: "settings", section: section as "general" | "mailboxes" | "team" | "billing" };
  }
  if (["assistant", "leads", "emails", "analytics", "inbox"].includes(first)) {
    return { kind: first as "assistant" | "leads" | "emails" | "analytics" | "inbox", navKey: first };
  }
  return { kind: "dashboard", navKey: "portal" };
}

// ─── Shared UI atoms ─────────────────────────────────────────────────────────

function LangToggle({ className }: Readonly<{ className?: string }>) {
  const { locale, toggleLocale } = useLocale();
  return (
    <button
      type="button"
      onClick={toggleLocale}
      className={cn("kicker text-mineral transition hover:text-ochre active:scale-95", className)}
    >
      {locale === "sv" ? "EN" : "SV"}
    </button>
  );
}

function DraftLogo({ compact = false, light = false }: Readonly<{ compact?: boolean; light?: boolean }>) {
  return (
    <span className="relative inline-flex items-center">
      <span className="relative z-10 -mr-2 block h-12 w-[78px] md:h-14 md:w-[92px]">
        <Image
          src="/snipe_logo.svg"
          alt=""
          fill
          priority
          sizes="92px"
          className={cn("object-contain object-left", light ? "invert" : "")}
        />
      </span>
      {!compact ? (
        <span className="relative z-0 flex flex-col leading-none">
          <span className={cn("font-display text-2xl font-semibold tracking-normal md:text-3xl", light ? "text-paper" : "text-ink")}>
            Snipra
          </span>
          <span className={cn("kicker mt-2", light ? "text-paper/55" : "text-mineral")}>sales os</span>
        </span>
      ) : null}
    </span>
  );
}

function DraftHeader({ variant, portal = false }: Readonly<{ variant: DraftVariant; portal?: boolean }>) {
  const modern = isModern(variant);
  return (
    <header className="sticky top-0 z-30 border-b border-ink/10 bg-paper/66 shadow-[inset_0_1px_0_oklch(var(--paper)/0.8)] backdrop-blur-xl">
      <div className="relative mx-auto flex w-full max-w-full items-center justify-between gap-5 px-5 py-3 md:max-w-[1480px] md:px-8">
        <Link href={draftPath(variant)} className="focus-ring">
          <DraftLogo />
        </Link>
        <nav className={cn("hidden items-center gap-8 md:flex", modern ? "font-modern text-[13px] font-medium text-ink/70" : "kicker text-ink/70")}>
          <Link href={draftPath(variant)} className="transition hover:text-ochre">Landning</Link>
          <Link href={draftPath(variant, "portal")} className="transition hover:text-ochre">Portal</Link>
          <Link href={draftPath(otherVariant(variant))} className="transition hover:text-ochre">Byt draft</Link>
          <LangToggle />
        </nav>
        <Link
          href={draftPath(variant, portal ? "" : "portal")}
          className="group hidden shrink-0 items-center justify-center gap-2 bg-ink px-3 py-3 font-mono text-[10px] uppercase tracking-[0.14em] text-paper transition duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] hover:bg-ochre hover:text-ink active:scale-[0.98] min-[480px]:inline-flex sm:gap-3 sm:px-5 sm:text-[12px] sm:tracking-[0.16em]"
        >
          {portal ? (
            <>
              <span className="hidden min-[480px]:inline sm:hidden">Landning</span>
              <span className="hidden sm:inline">Till landning</span>
            </>
          ) : (
            <>
              <span className="hidden min-[480px]:inline sm:hidden">Portal</span>
              <span className="hidden sm:inline">Öppna portal</span>
            </>
          )}
          <span aria-hidden className="transition group-hover:translate-x-1 group-hover:-translate-y-px">↗</span>
        </Link>
      </div>
    </header>
  );
}

function EditorialLandingHeader({ variant, asMain = false }: Readonly<{ variant: DraftVariant; asMain?: boolean }>) {
  const { locale } = useLocale();
  const homeHref = asMain ? "/" : `/design-drafts/${variant}`;
  return (
    <header className="sticky top-0 z-30 border-b border-ink/12 bg-paper/30 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1480px] items-center justify-between px-6 py-5 md:px-8 md:py-6">
        <Link href={homeHref} className="focus-ring flex items-center gap-2.5">
          <span className="relative block h-11 w-[72px] shrink-0">
            <Image src="/snipe_logo.svg" alt="" fill sizes="72px" className="object-contain object-left" />
          </span>
          <span className="font-display italic-disp text-[30px] leading-none tighten md:text-[34px]">Snipra</span>
        </Link>
        <nav className="hidden items-baseline gap-12 md:flex kicker text-ink/80">
          <a href="#metod" className="transition hover:text-ochre">{locale === "sv" ? "Metod" : "Method"}</a>
          <a href="#bevis" className="transition hover:text-ochre">{locale === "sv" ? "Bevis" : "Proof"}</a>
          <Link href={asMain ? "/dashboard" : draftPath(variant, "portal")} className="transition hover:text-ochre">Portal</Link>
          <a href="#prislista" className="transition hover:text-ochre">{locale === "sv" ? "Prislista" : "Pricing"}</a>
          <LangToggle />
        </nav>
        <a
          href="#start"
          className="hidden items-center gap-3 bg-ink px-6 py-3.5 font-mono text-[13px] uppercase tracking-[0.18em] text-paper transition-colors duration-500 hover:bg-ochre hover:text-ink md:inline-flex"
        >
          {locale === "sv" ? "Starta utvärdering" : "Start evaluation"}
          <span aria-hidden className="font-mono">↗</span>
        </a>
      </div>
    </header>
  );
}

// ─── Landing page ────────────────────────────────────────────────────────────

export function DraftLanding({ variant, asMain = false }: Readonly<{ variant: DraftVariant; asMain?: boolean }>) {
  const modern = isModern(variant);
  const { locale } = useLocale();

  return (
    <main className={cn("relative min-h-screen [overflow-x:clip] bg-paper text-ink", modern ? "font-modern" : "")}>
      {/* Editorial gradient — pure CSS, no filter, not clipped by overflow */}
      {!modern && (
        <div className="pointer-events-none absolute inset-x-0 top-0 h-[860px] bg-[radial-gradient(circle_at_18%_0%,oklch(var(--ochre)/0.3)_0%,transparent_65%)] [mask-image:linear-gradient(to_bottom,black_78%,transparent_100%)]" />
      )}
      {modern ? <DraftHeader variant={variant} /> : <EditorialLandingHeader variant={variant} asMain={asMain} />}

      {/* Hero */}
      <section className="relative">
        <div className="blob pointer-events-none absolute right-0 top-60 h-[420px] w-[420px] rounded-full bg-ink/10" />
        <div className="relative mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 pb-28 pt-16 md:px-8 md:pb-32 md:pt-20">
          <div className="col-span-12 lg:col-span-2 lg:pt-2">
            <div className="kicker text-mineral">{modern ? (locale === "sv" ? "Modern portal" : "Modern portal") : (locale === "sv" ? "Svensk outbound" : "Swedish outbound")}</div>
            <div className="rule mt-3 text-ink" />
            <div className="kicker mt-3 leading-snug text-mineral">
              {locale === "sv" ? <>Signal,<br />tonläge,<br />svar.</> : <>Signal,<br />tone,<br />reply.</>}
            </div>
          </div>

          <div className="reveal col-span-12 mt-12 min-w-0 lg:col-span-7 lg:mt-0">
            <h1 className="break-words font-display text-[clamp(3.2rem,9vw,9rem)] leading-[0.92] tighten">
              {modern ? (
                locale === "sv" ? (
                  <>
                    <span className="block">Snipra</span>
                    <span className="block italic-disp text-ochre">hittar</span>
                    <span className="block">rätt läge</span>
                    <span className="block italic-disp text-ink2">för nästa mejl.</span>
                  </>
                ) : (
                  <>
                    <span className="block">Snipra</span>
                    <span className="block italic-disp text-ochre">finds</span>
                    <span className="block">the right moment</span>
                    <span className="block italic-disp text-ink2">for the next email.</span>
                  </>
                )
              ) : (
                locale === "sv" ? (
                  <>
                    <span className="block">En</span>
                    <span className="block italic-disp text-ochre">säljare</span>
                    <span className="block">som skriver</span>
                    <span className="block">i <span className="italic-disp text-ink2">ditt</span> tonläge.</span>
                  </>
                ) : (
                  <>
                    <span className="block">A</span>
                    <span className="block italic-disp text-ochre">sales rep</span>
                    <span className="block">that writes</span>
                    <span className="block">in <span className="italic-disp text-ink2">your</span> voice.</span>
                  </>
                )
              )}
            </h1>
          </div>

          <div className="reveal reveal-delay-1 col-span-12 mt-12 min-w-0 border-ink/15 lg:col-span-3 lg:mt-0 lg:border-l lg:pl-8">
            <p className="max-w-[36ch] text-[17px] leading-[1.55] text-ink/85">
              {locale === "sv"
                ? "Snipra läser svenska bolagssignaler, matchar dem mot er ICP och skriver outreach med källor, timing och CTA nära till hands."
                : "Snipra reads Swedish company signals, matches them against your ICP and writes outreach with sources, timing and CTA close at hand."}
            </p>

            <dl className="num mt-10 space-y-5">
              {[
                [locale === "sv" ? "Open rate" : "Open rate", "51,3 %", true],
                [locale === "sv" ? "Reply rate" : "Reply rate", "14,8 %", false],
                [locale === "sv" ? "Möten bokade" : "Meetings booked", "217", false]
              ].map(([label, value, accent]) => (
                <div key={String(label)}>
                  <div className="block md:grid md:grid-cols-[minmax(0,1fr)_auto] md:items-baseline md:gap-3">
                    <dt className="kicker min-w-0 text-mineral">{label}</dt>
                    <dd className={`mt-2 block font-display text-2xl italic-disp md:mt-0 md:text-right ${accent ? "text-ochre" : ""}`}>{value}</dd>
                  </div>
                  <div className="rule mt-5 text-ink" />
                </div>
              ))}
            </dl>
          </div>
        </div>

        <div className="mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 pb-6 md:px-8">
          <div className="rule col-span-12 text-ink" />
        </div>
        <div className="kicker mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 pb-12 text-mineral md:px-8">
          <div className="col-span-12 md:col-span-3">Malmö</div>
          <div className="col-span-12 mt-2 md:col-span-3 md:mt-0">{locale === "sv" ? "Svenska bolagssignaler" : "Swedish company signals"}</div>
          <div className="col-span-12 mt-2 md:col-span-3 md:mt-0">GDPR · RLS · audit logs</div>
          <div className="col-span-12 mt-2 md:col-span-3 md:mt-0 md:text-right">{locale === "sv" ? "Produktportal nedan" : "Product portal below"}</div>
        </div>
      </section>

      {/* Marquee */}
      <section className="overflow-hidden border-y border-ink/15 py-7">
        <div className="marquee whitespace-nowrap font-display text-[28px] italic-disp text-ink/45 tighten">
          {[...customerBand, ...customerBand].map((name, index) => (
            <span key={`${name}-${index}`} className="px-6">
              {name}<span className="pl-12 text-ochre">·</span>
            </span>
          ))}
        </div>
      </section>

      {/* Method */}
      <section id="metod" className="mx-auto max-w-[1480px] px-6 pb-24 pt-28 md:px-8 md:pt-32">
        <div className="mb-16 grid grid-cols-12 gap-x-8">
          <div className="col-span-12 md:col-span-3">
            <div className="kicker text-mineral">{locale === "sv" ? "Metod" : "Method"}</div>
            <div className="rule mt-3 text-ink" />
          </div>
          <div className="col-span-12 mt-8 md:col-span-8 md:mt-0">
            <h2 className="font-display text-[clamp(2.4rem,5vw,4.4rem)] leading-[0.98] tighten">
              {locale === "sv" ? "Bättre timing innan första raden skrivs." : "Better timing before the first line is written."}
            </h2>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-x-8 gap-y-12">
          {landingSignals.map((signal, index) => (
            <article key={signal.title.sv} className="col-span-12 grid grid-cols-12 gap-x-6 border-t border-ink/15 pt-8 md:col-span-6">
              <div className="col-span-3 font-mono text-[clamp(2rem,4vw,3.5rem)] leading-none text-ochre/60 num">
                {String(index + 1).padStart(2, "0")}
              </div>
              <div className="col-span-9">
                <h3 className="mb-3 font-display text-2xl tighten">{locale === "sv" ? signal.title.sv : signal.title.en}</h3>
                <p className="max-w-[48ch] text-[16px] leading-[1.65] text-ink/75">{locale === "sv" ? signal.body.sv : signal.body.en}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* Email proof */}
      <section id="bevis" className="relative overflow-hidden bg-ink text-paper">
        <div className="blob pointer-events-none absolute right-[-200px] top-40 h-[600px] w-[600px] rounded-full bg-ochre/20" />
        <div className="relative mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 py-24 md:px-8">
          <div className="col-span-12 md:col-span-3">
            <div className="kicker text-paper/55">Email proof</div>
            <p className="kicker mt-3 leading-snug text-paper/55">{locale === "sv" ? "Två utkast, samma system." : "Two drafts, one system."}</p>
          </div>
          <div className="col-span-12 mt-10 grid gap-6 md:col-span-9 md:mt-0 md:grid-cols-2">
            {[
              {
                meta: "Bygg · Skåne · 47 anställda",
                title: "Till Karin på Bergslagens Plåt",
                body: "Jag såg att ni söker en offertchef samtidigt som flera kommunala projekt i Skåne öppnar för nya underentreprenörer. Det brukar vara ett läge där rätt första lista sparar mer tid än ännu en generell prospektering.",
                bridge: "Bryggor: lokal projektsignal · ICP-likhet"
              },
              {
                meta: "Restaurang · Göteborg · 12 enheter",
                title: "Till Marcus på Havre",
                body: "Ni verkar flytta cateringdelen närmare företagsevent. Om målet är fler återkommande kontorsluncher kan Snipra hitta HR- och office-roller där tajmingen redan syns.",
                bridge: "Bryggor: nyöppning · branschspecifik datapunkt"
              }
            ].map((mail) => (
              <article key={mail.title} className="border border-paper/15 p-6 md:p-8">
                <span className="kicker text-ochre">{mail.meta}</span>
                <h3 className="mb-4 mt-8 font-display text-xl text-paper tighten">{mail.title}</h3>
                <p className="text-[16px] leading-[1.7] text-paper/82">{mail.body}</p>
                <div className="kicker mt-8 text-paper/55">{mail.bridge}</div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* Inline portal showcase — editorial scroll through all sections */}
      {!modern ? (
        <div id="portal">
          {scrollSections.map((section, index) => (
            <section key={section.id} id={section.id} className="border-t border-ink/15">
              <div className="mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 py-16 md:px-8 md:py-20">
                <div className="col-span-12 md:col-span-3">
                  <div className="flex items-center gap-4">
                    <span className="num font-mono text-sm text-ochre">{String(index + 1).padStart(2, "0")}</span>
                    <span className="kicker text-mineral">{locale === "sv" ? section.kicker.sv : section.kicker.en}</span>
                  </div>
                  <div className="rule mt-3 text-ink" />
                </div>
                <div className="col-span-12 mt-6 md:col-span-9 md:mt-0">
                  <h2 className="font-display text-[clamp(2rem,4.5vw,4rem)] leading-[0.98] tighten">
                    {locale === "sv" ? section.title.sv : section.title.en}
                  </h2>
                  <p className="mt-4 max-w-[60ch] text-[16px] leading-7 text-ink/68">
                    {locale === "sv" ? section.desc.sv : section.desc.en}
                  </p>
                </div>
                <div className="col-span-12 mt-10">
                  <ScrollSectionContent sectionId={section.id} variant={variant} />
                </div>
              </div>
            </section>
          ))}
        </div>
      ) : (
        /* Modern blend keeps the portal link table */
        <section className="mx-auto max-w-[1480px] px-6 py-24 md:px-8">
          <div className="grid grid-cols-12 gap-x-8">
            <div className="col-span-12 md:col-span-3">
              <div className="kicker text-mineral">Portal</div>
              <div className="rule mt-3 text-ink" />
            </div>
            <div className="col-span-12 mt-8 md:col-span-7 md:mt-0">
              <h2 className="font-display text-[clamp(2.2rem,4.4vw,3.6rem)] leading-[1.02] tighten">
                {locale === "sv" ? "Samma funktioner, tydligare arbetsyta." : "Same functions, clearer workspace."}
              </h2>
            </div>
          </div>
          <div className="mt-12 divide-y divide-ink/15">
            {modernNavItems.map((item) => (
              <Link key={item.href} href={draftPath(variant, item.href)} className="row grid grid-cols-12 gap-x-6 py-5 transition hover:bg-ochre/5">
                <div className="ticker col-span-12 font-display text-2xl italic-disp tighten md:col-span-4">{locale === "sv" ? item.sv : item.en}</div>
                <div className="kicker col-span-6 mt-2 text-right text-ochre md:col-span-8 md:mt-0 md:text-right">{locale === "sv" ? "öppna ↗" : "open ↗"}</div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Pricing */}
      <section id="prislista" className="border-t border-ink/15 bg-paper2/50">
        <div className="mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 py-24 md:px-8">
          <div className="col-span-12 md:col-span-3">
            <div className="kicker text-mineral">{locale === "sv" ? "Prislista" : "Pricing"}</div>
            <div className="rule mt-3 text-ink" />
            <p className="kicker mt-3 leading-snug text-mineral">
              {locale === "sv" ? <>En enkel meny.<br />Inga seat-priser.</> : <>One simple menu.<br />No per-seat pricing.</>}
            </p>
          </div>
          <ul className="col-span-12 mt-8 space-y-7 num md:col-span-9 md:mt-0">
            {[
              {
                name: "Pilot",
                nameAccent: false,
                desc: locale === "sv"
                  ? "Sex veckor. Vi sätter upp domänen, tränar tonläget, kör en kampanj på 500 leads. Du står kvar med en domän som inte är förstörd och en månadsrapport på en sida."
                  : "Six weeks. We set up the domain, train the tone, run a campaign on 500 leads. You keep a clean domain and a one-page monthly report.",
                includes: locale === "sv" ? "ingår: domän-setup, ton, en kampanj, en rapport" : "includes: domain setup, tone, one campaign, one report",
                price: "24 800 kr",
                unit: locale === "sv" ? "/ pilot" : "/ pilot"
              },
              {
                name: locale === "sv" ? "Operativ" : "Ongoing",
                nameAccent: true,
                desc: locale === "sv"
                  ? "Löpande. Du har en pipeline som lever. Vi roterar mellan tre tonlägen och sex segment. Möten landar i din kalender, inte i en CRM-rapport du måste tolka."
                  : "Ongoing. Your pipeline stays alive. We rotate across three tones and six segments. Meetings land in your calendar, not a CRM report you have to interpret.",
                includes: locale === "sv" ? "obegränsade kampanjer · bokade möten · veckorapport" : "unlimited campaigns · booked meetings · weekly report",
                price: "18 400 kr",
                unit: locale === "sv" ? "/ mån" : "/ mo"
              },
              {
                name: "Hus",
                nameAccent: false,
                desc: locale === "sv"
                  ? "För dig som har en säljchef som vill ha veckomöten med oss och en VD som vill veta varför reply rate dippade i v18. Vi kommer in, sitter med er en dag i månaden, och flyttar ratten."
                  : "For teams with a sales lead who wants weekly calls and a CEO who wants to know why reply rate dipped in week 18. We come in, sit with you one day per month, and steer.",
                includes: locale === "sv" ? "en dag på plats per månad · direktnummer" : "one on-site day per month · direct line",
                price: "42 000 kr",
                unit: locale === "sv" ? "/ mån" : "/ mo"
              }
            ].map((plan) => (
              <li key={plan.name} className="grid grid-cols-12 items-baseline gap-x-6 border-b border-ink/15 pb-7 last:border-0 last:pb-1">
                <div className="col-span-12 md:col-span-5">
                  <h3 className={cn("font-display text-3xl italic-disp tighten", plan.nameAccent ? "text-ochre" : "")}>{plan.name}</h3>
                  <p className="mt-2 max-w-[42ch] text-[15px] leading-relaxed text-ink/75">{plan.desc}</p>
                </div>
                <div className="col-span-12 mt-3 leading-snug md:col-span-3 md:mt-0 kicker text-mineral">{plan.includes}</div>
                <div className="col-span-12 mt-3 text-right font-display text-5xl italic-disp tighten md:col-span-4 md:mt-0">
                  {plan.price}<span className="kicker ml-3 text-mineral">{plan.unit}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* CTA / footer */}
      <section id="start" className="relative overflow-hidden bg-ink text-paper">
        <div className="blob pointer-events-none absolute -bottom-40 -right-40 h-[700px] w-[700px] rounded-full bg-ochre/25" />
        <div className="relative mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 py-28 md:px-8 md:py-28">
          <div className="col-span-12 md:col-span-7">
            <h2 className="font-display text-[clamp(3rem,7vw,7rem)] leading-[0.92] tighten">
              {locale === "sv" ? (
                <>Skicka <span className="italic-disp text-ochre">ett mejl</span>,<br />så svarar någon.<br /><span className="italic-disp">På riktigt.</span></>
              ) : (
                <>Send <span className="italic-disp text-ochre">one email</span>,<br />someone replies.<br /><span className="italic-disp">For real.</span></>
              )}
            </h2>
          </div>
          <div className="col-span-12 mt-8 flex flex-col justify-between border-paper/15 md:col-span-5 md:mt-0 md:border-l md:pl-10">
            <p className="max-w-[44ch] text-[17px] leading-[1.6] text-paper/85">
              {locale === "sv" ? (
                <>Mejla oss på <a href="mailto:hej@snipra.se" className="text-ochre underline decoration-ochre/40 underline-offset-[6px] decoration-[1px] transition hover:decoration-ochre">hej@snipra.se</a>. Hellre ett vanligt mejl än en demo-bokning. Vi svarar samma dag.</>
              ) : (
                <>Email us at <a href="mailto:hej@snipra.se" className="text-ochre underline decoration-ochre/40 underline-offset-[6px] decoration-[1px] transition hover:decoration-ochre">hej@snipra.se</a>. A plain email beats a demo booking. We reply the same day.</>
              )}
            </p>
            <div className="mt-10 flex flex-wrap items-center gap-5">
              <a href="mailto:hej@snipra.se" className="inline-flex items-center gap-3 bg-paper px-6 py-4 font-mono text-[13px] uppercase tracking-[0.18em] text-ink transition-colors duration-500 hover:bg-ochre">
                {locale === "sv" ? "Skriv till oss" : "Write to us"} <span className="font-mono">↗</span>
              </a>
              <a href="#prislista" className="inline-flex items-center gap-3 border border-paper/35 px-6 py-4 font-mono text-[13px] uppercase tracking-[0.18em] text-paper transition-colors hover:border-ochre hover:text-ochre">
                {locale === "sv" ? "Eller läs prislistan" : "Or see pricing"}
              </a>
            </div>
          </div>
        </div>
        <div className="border-t border-paper/15">
          <div className="mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 py-8 md:px-8 kicker text-paper/55">
            <div className="col-span-12 md:col-span-3">Snipra AB · Föreningsgatan 41 · Malmö</div>
            <div className="col-span-12 mt-2 md:col-span-3 md:mt-0">Org. 559412-8804</div>
            <div className="col-span-12 mt-2 md:col-span-3 md:mt-0">hej@snipra.se · 040-220 814</div>
            <div className="col-span-12 mt-2 md:col-span-3 md:mt-0 md:text-right">© MMXXVI · {locale === "sv" ? "Tryckt i en webbläsare" : "Printed in a browser"}</div>
          </div>
        </div>
      </section>
    </main>
  );
}

// ─── Editorial Clean: scroll showcase portal ──────────────────────────────────

function EditorialScrollShowcase({ variant }: Readonly<{ variant: DraftVariant }>) {
  const { locale } = useLocale();

  return (
    <main className="min-h-screen overflow-x-hidden bg-paper text-ink">
      <DraftHeader variant={variant} portal />

      {/* Intro */}
      <div className="mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 pb-20 pt-20 md:px-8 md:pt-24">
        <div className="col-span-12 md:col-span-3">
          <div className="kicker text-mineral">Produktindex</div>
          <div className="rule mt-3 text-ink" />
        </div>
        <div className="col-span-12 mt-8 md:col-span-8 md:mt-0">
          <h1 className="font-display text-[clamp(2.8rem,6vw,6rem)] leading-[0.94] tighten">
            {locale === "sv" ? (
              <><span className="italic-disp text-ochre">Portalen</span> — ett arbetsblad<br />från signal till svar.</>
            ) : (
              <><span className="italic-disp text-ochre">The portal</span> — a workspace<br />from signal to reply.</>
            )}
          </h1>
          <p className="mt-8 max-w-[54ch] text-[17px] leading-[1.6] text-ink/75">
            {locale === "sv"
              ? "Alla vyer i ett flöde. Scrolla för att se hur Snipra hanterar discovery, research, skrivarbete och analys i en sammanhängande arbetsyta."
              : "All views in one flow. Scroll to see how Snipra handles discovery, research, copywriting and analytics in a connected workspace."}
          </p>
        </div>
      </div>

      {/* Scroll sections */}
      {scrollSections.map((section, index) => (
        <section key={section.id} id={section.id} className="border-t border-ink/15">
          <div className="mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 py-16 md:px-8 md:py-20">
            {/* Section header */}
            <div className="col-span-12 md:col-span-3">
              <div className="flex items-center gap-4">
                <span className="num font-mono text-sm text-ochre">{String(index + 1).padStart(2, "0")}</span>
                <span className="kicker text-mineral">{locale === "sv" ? section.kicker.sv : section.kicker.en}</span>
              </div>
              <div className="rule mt-3 text-ink" />
            </div>
            <div className="col-span-12 mt-6 md:col-span-9 md:mt-0">
              <h2 className="font-display text-[clamp(2rem,4.5vw,4rem)] leading-[0.98] tighten">
                {locale === "sv" ? section.title.sv : section.title.en}
              </h2>
              <p className="mt-4 max-w-[60ch] text-[16px] leading-7 text-ink/68">
                {locale === "sv" ? section.desc.sv : section.desc.en}
              </p>
            </div>
            {/* Content */}
            <div className="col-span-12 mt-10">
              <ScrollSectionContent sectionId={section.id} variant={variant} />
            </div>
          </div>
        </section>
      ))}

      {/* Footer CTA */}
      <section className="relative overflow-hidden bg-ink text-paper">
        <div className="blob pointer-events-none absolute -right-40 top-40 h-[500px] w-[500px] rounded-full bg-ochre/20" />
        <div className="relative mx-auto grid max-w-[1480px] grid-cols-12 gap-x-8 px-6 py-20 md:px-8">
          <div className="col-span-12 md:col-span-7">
            <h2 className="font-display text-[clamp(2.4rem,5vw,5rem)] leading-[0.94] tighten">
              {locale === "sv" ? (
                <>{locale === "sv" ? "Välj riktning." : "Choose direction."}</>
              ) : (
                <>Choose direction.</>
              )}
            </h2>
          </div>
          <div className="col-span-12 mt-8 flex flex-wrap items-center gap-5 md:col-span-5 md:mt-0 md:items-end md:justify-end">
            <Link href={draftPath(variant)} className="inline-flex items-center gap-3 bg-paper px-6 py-4 font-mono text-[13px] uppercase tracking-[0.18em] text-ink transition-colors hover:bg-ochre">
              {locale === "sv" ? "Till landning" : "Back to landing"} ↗
            </Link>
            <Link href={draftPath(otherVariant(variant))} className="inline-flex items-center gap-3 border border-paper/35 px-6 py-4 font-mono text-[13px] uppercase tracking-[0.18em] text-paper transition-colors hover:border-ochre hover:text-ochre">
              {locale === "sv" ? "Byt draft" : "Switch draft"}
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

function ScrollSectionContent({ sectionId, variant }: Readonly<{ sectionId: string; variant: DraftVariant }>) {
  if (sectionId === "overview") return <DashboardShowcase variant={variant} />;
  if (sectionId === "leads") return <LeadsShowcase variant={variant} />;
  if (sectionId === "assistant") return <AssistantShowcase variant={variant} />;
  if (sectionId === "companies") return <CompanyDetailShowcase variant={variant} id={companies[0].id} />;
  if (sectionId === "campaigns") return <CampaignsShowcase variant={variant} />;
  if (sectionId === "emails") return <EmailShowcase variant={variant} />;
  if (sectionId === "analytics") return <AnalyticsShowcase variant={variant} />;
  if (sectionId === "inbox") return <InboxShowcase variant={variant} />;
  return null;
}

// ─── Modern Blend: app shell portal ──────────────────────────────────────────

// ─── Editorial Clean: iteration 1 portal shell ──────────────────────────────

const editorialPortalNav = [
  { key: "portal", href: "portal", label: "Översikt", Icon: ChartNoAxesColumn },
  { key: "assistant", href: "portal/assistant", label: "AI-assistent", Icon: Sparkles },
  { key: "leads", href: "portal/leads", label: "Leads", Icon: Search },
  { key: "companies", href: "portal/companies", label: "Företag", Icon: Building2 },
  { key: "contacts", href: "portal/contacts", label: "Kontakter", Icon: UsersRound },
  { key: "campaigns", href: "portal/campaigns", label: "Kampanjer", Icon: CircleDot },
  { key: "emails", href: "portal/emails", label: "Email studio", Icon: Mail },
  { key: "analytics", href: "portal/analytics", label: "Analys", Icon: ChartNoAxesColumn },
  { key: "inbox", href: "portal/inbox", label: "Inkorg", Icon: MessageSquare },
  { key: "settings", href: "portal/settings", label: "Inställningar", Icon: Settings }
];

function EditorialIterationPortal({ slug }: Readonly<{ slug: string[] }>) {
  const route = parsePortalSlug(slug);
  const navBase = usePortalNav();

  return (
    <div className="min-h-screen bg-paper font-modern text-ink">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[243px] border-r border-ink/10 bg-paper/88 px-4 py-5 backdrop-blur-xl lg:flex lg:flex-col">
        <Link href="/" className="flex items-center gap-3">
          <span className="relative block h-11 w-[72px] shrink-0">
            <Image src="/snipe_logo.svg" alt="" fill sizes="72px" className="object-contain object-left" priority />
          </span>
          <span className="font-display italic-disp text-[28px] leading-none tighten">Snipra</span>
        </Link>

        <nav className="mt-7 space-y-1">
          {editorialPortalNav.map(({ key, href, label, Icon }) => {
            const active = route.navKey === key || (key === "portal" && route.kind === "dashboard");
            const navHref = href === "portal" ? navBase : `${navBase}/${href.replace(/^portal\//, "")}`;
            return (
              <Link
                key={key}
                href={navHref}
                className={cn(
                  "flex h-[42px] items-center gap-3 rounded-[8px] px-3 text-[15px] font-semibold transition",
                  active ? "bg-ink text-paper" : "text-ink hover:bg-ink/5"
                )}
              >
                <Icon className="h-[17px] w-[17px] shrink-0" strokeWidth={1.9} />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto rounded-[9px] border border-ink/12 bg-paper/62 p-4 shadow-[inset_0_1px_0_oklch(var(--paper)/0.9)]">
          <div className="kicker text-mineral">Showcase</div>
          <p className="mt-4 text-[14px] leading-[1.7] text-ink/88">
            Alla nuvarande produktområden finns kvar som preview-sidor i draften.
          </p>
        </div>
      </aside>

      <div className="lg:pl-[243px]">
        <main className="px-6 py-7 lg:px-10">
          <EditorialIterationContent route={route} />
        </main>
      </div>
    </div>
  );
}

function EditorialIterationContent({ route }: Readonly<{ route: PortalRoute }>) {
  const heading = editorialPortalHeading(route);

  return (
    <div className="space-y-7">
      <EditorialIterationHeader kicker={heading.kicker} title={heading.title} desc={heading.desc} />
      {route.kind === "dashboard" ? <EditorialIterationOverview /> : null}
      {route.kind === "leads" ? <EditorialIterationLeads /> : null}
      {route.kind !== "dashboard" && route.kind !== "leads" ? <PortalContent variant="editorial-clean" route={route} /> : null}
    </div>
  );
}

function editorialPortalHeading(route: PortalRoute) {
  if (route.kind === "dashboard") {
    return {
      kicker: "Vecka 21",
      title: "Outboundöversikt",
      desc: "Prioriterade konton, svar och nasta handling i en lugnare arbetsyta."
    };
  }
  if (route.kind === "leads") {
    return {
      kicker: "Discovery",
      title: "Lead discovery",
      desc: "Sparade sokningar och rekommenderade bolag sorterade efter signal, score och kontaktbarhet."
    };
  }
  const [, title, desc] = route.kind === "settings" ? pageCopy.settings : pageCopy[route.kind];
  return {
    kicker: route.kind === "settings" ? "Admin" : route.kind,
    title: getRouteTitle(route, title),
    desc: getRouteDescription(route, desc)
  };
}

function EditorialIterationHeader({ kicker, title, desc }: Readonly<{ kicker: string; title: string; desc: string }>) {
  return (
    <section className="relative overflow-hidden rounded-[10px] border border-ink/10 bg-paper px-7 py-5 shadow-[inset_0_1px_0_oklch(var(--paper)/0.9)] lg:px-8 lg:py-6">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_88%_28%,oklch(var(--ochre)/0.28),transparent_34%),linear-gradient(118deg,oklch(var(--paper)/0.95)_0%,oklch(var(--paper)/0.72)_55%,oklch(var(--ochre)/0.22)_100%)]" />
      <div className="relative grid grid-cols-12 items-end gap-x-8 gap-y-5">
        <div className="col-span-12 xl:col-span-9">
          <div className="kicker text-mineral">{kicker}</div>
          <h1 className="mt-3 font-display text-[clamp(2.4rem,3.2vw,4rem)] leading-[0.94] tracking-[-0.015em]">
            {title}
          </h1>
          <p className="mt-3 max-w-[720px] text-[15px] leading-[1.6] text-ink/75">{desc}</p>
        </div>
        <div className="col-span-12 flex justify-start gap-3 xl:col-span-3 xl:justify-end">
          <button type="button" className="rounded-[10px] border border-ink/10 bg-paper/62 px-5 py-2.5 text-[15px] font-semibold text-ink/60 transition hover:border-ochre hover:text-ochre">
            Export
          </button>
          <button type="button" className="rounded-[10px] bg-ink px-5 py-2.5 text-[15px] font-semibold text-paper transition hover:bg-ochre hover:text-ink">
            Ny handling
          </button>
        </div>
      </div>
    </section>
  );
}

function EditorialIterationOverview() {
  const latest = analyticsSeries.at(-1);
  const sent = latest?.sent ?? 297;
  const replies = latest?.replies ?? 49;

  return (
    <>
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
        {[
          ["Skickade", String(sent), "denna vecka", false],
          ["Svar", formatPercent(replies / sent), "reply rate", true],
          ["Möten", "18", "bokade", false],
          ["Pipeline", formatCurrency(842000), "attribuerad", false]
        ].map(([label, value, detail, accent]) => (
          <article key={String(label)} className="rounded-[10px] border border-ink/10 bg-[linear-gradient(135deg,oklch(var(--paper)/0.9),oklch(var(--ochre)/0.08))] p-5 shadow-[inset_0_1px_0_oklch(var(--paper)/0.9)]">
            <div className="kicker text-mineral">{label}</div>
            <div className={cn("mt-5 text-[38px] font-bold leading-none tracking-[-0.025em]", accent ? "text-ochre" : "text-ink")}>{value}</div>
            <div className="mt-3 text-[18px] leading-none text-ink/82">{detail}</div>
          </article>
        ))}
      </div>

      <div className="grid grid-cols-12 gap-6">
        <section className="col-span-12 xl:col-span-8">
          <EditorialCompanyTable mode="overview" />
        </section>
        <aside className="col-span-12 rounded-[10px] border border-ink/10 bg-[linear-gradient(135deg,oklch(var(--paper)/0.88),oklch(var(--ochre)/0.08))] p-6 xl:col-span-4">
          <h2 className="text-[18px] font-bold">Nästa handling</h2>
          <div className="mt-5 divide-y divide-ink/12">
            {[
              ["Byggkompaniet Syd", "Generera mediumvariant med Hyllie-signalen."],
              ["Nordic Sweat Studios", "Kontrollera ny studio innan uppföljning."],
              ["Fjord Fastigheter", "Lägg till lokal referens i öppningsrad."]
            ].map(([title, body]) => (
              <div key={title} className="py-4">
                <h3 className="text-[17px] font-semibold leading-snug">{title}</h3>
                <p className="mt-2 text-[15px] leading-[1.5] text-ink/72">{body}</p>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </>
  );
}

function EditorialIterationLeads() {
  return (
    <>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          ["Sökning 01", "Bygg i Malmö"],
          ["Sökning 02", "Gym i Stockholm"],
          ["Sökning 03", "Fastighet Uppsala"],
          ["Sökning 04", "SaaS med rekrytering"]
        ].map(([label, title]) => (
          <article key={label} className="rounded-[10px] border border-ink/10 bg-[linear-gradient(135deg,oklch(var(--paper)/0.9),oklch(var(--ochre)/0.08))] p-5 shadow-[inset_0_1px_0_oklch(var(--paper)/0.9)]">
            <div className="kicker text-mineral">{label}</div>
            <h2 className="mt-5 font-display text-[22px] italic-disp tighten">{title}</h2>
          </article>
        ))}
      </div>

      <EditorialCompanyTable mode="leads" />
    </>
  );
}

function EditorialCompanyTable({ mode }: Readonly<{ mode: "overview" | "leads" }>) {
  const navBase = usePortalNav();
  const rows = companies.slice(0, 5);
  const grid = mode === "leads"
    ? "grid-cols-[1.15fr_0.85fr_0.85fr_1.25fr_0.45fr_0.8fr]"
    : "grid-cols-[1.15fr_0.75fr_0.85fr_1.2fr_0.42fr_0.78fr]";

  return (
    <div className="overflow-hidden rounded-[10px] border border-ink/10 bg-paper/58">
      <div className={cn("hidden gap-x-7 border-b border-ink/10 px-5 py-5 md:grid", grid)}>
        {["Bolag", "Segment", "Kontakt", "Signal", "Score", "Status"].map((head) => (
          <div key={head} className="kicker text-mineral">{head}</div>
        ))}
      </div>
      <div className="divide-y divide-ink/10">
        {rows.map((company) => {
          const contact = company.contacts[0];
          return (
            <Link
              key={company.id}
              href={`${navBase}/companies/${company.id}`}
              className={cn("grid gap-x-7 gap-y-4 px-5 py-6 text-[18px] leading-[1.45] transition hover:bg-ochre/5 md:grid", grid)}
            >
              <div>
                <div className="font-bold">{company.name}</div>
                <div className="mt-1 text-ink/82">{company.website}</div>
              </div>
              <div>{company.industry} · {company.location}</div>
              <div>
                <div>{contact.fullName}</div>
                <div>{contact.role}</div>
              </div>
              <div>{company.latestSignal.sv}</div>
              <div className="font-bold text-ochre">{company.score}</div>
              <div>
                <EditorialStatusPill value={company.status} />
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function EditorialStatusPill({ value }: Readonly<{ value: string }>) {
  const highlighted = value === "recommended" || value === "queued";
  return <span className={cn("kicker", highlighted ? "text-ochre" : "text-mineral")}>{value}</span>;
}

function ModernPortal({ slug }: Readonly<{ slug: string[] }>) {
  const route = parsePortalSlug(slug);
  const { locale, toggleLocale } = useLocale();

  return (
    <div className="flex h-screen overflow-hidden bg-paper font-modern text-ink">
      {/* Sidebar */}
      <aside className="thin-scrollbar flex w-56 shrink-0 flex-col overflow-y-auto bg-ink text-paper">
        {/* Logo */}
        <div className="border-b border-paper/10 px-5 py-4">
          <Link href="/design-drafts/modern-blend" className="focus-ring">
            <DraftLogo light />
          </Link>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4">
          {modernNavItems.map((item) => {
            const active = route.navKey === item.href.replace("portal/", "") || (item.href === "portal" && route.kind === "dashboard");
            return (
              <Link
                key={item.href}
                href={`/design-drafts/modern-blend/${item.href}`}
                className={cn(
                  "flex items-center justify-between rounded px-3 py-2 text-[13px] transition",
                  active ? "bg-paper/12 text-ochre" : "text-paper/65 hover:bg-paper/8 hover:text-paper"
                )}
              >
                <span>{locale === "sv" ? item.sv : item.en}</span>
                {active ? <span className="kicker text-ochre/70">aktiv</span> : null}
              </Link>
            );
          })}
        </nav>

        {/* Sidebar footer */}
        <div className="border-t border-paper/10 px-5 py-4">
          <button
            type="button"
            onClick={toggleLocale}
            className="kicker text-paper/45 transition hover:text-ochre"
          >
            {locale === "sv" ? "Switch to EN" : "Växla till SV"}
          </button>
        </div>
      </aside>

      {/* Right panel */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-12 shrink-0 items-center border-b border-ink/10 bg-paper px-6 gap-4">
          <nav className="kicker flex items-center gap-2 text-mineral">
            <span>Design draft</span>
            <span>/</span>
            <span className="text-ink">Modern blend</span>
            {route.kind !== "dashboard" ? (
              <>
                <span>/</span>
                <span className="text-ink capitalize">{route.kind}</span>
              </>
            ) : null}
          </nav>
          <div className="ml-auto flex items-center gap-4">
            <Link
              href={`/design-drafts/editorial-clean/portal`}
              className="kicker text-mineral transition hover:text-ochre"
            >
              {locale === "sv" ? "Byt draft" : "Switch draft"}
            </Link>
            <Link
              href="/design-drafts/modern-blend"
              className="kicker flex items-center gap-1 border border-ink/15 px-3 py-1.5 text-ink/70 transition hover:border-ochre hover:text-ochre"
            >
              {locale === "sv" ? "Landning" : "Landing"} ↗
            </Link>
          </div>
        </header>

        {/* Content */}
        <main className="thin-scrollbar flex-1 overflow-y-auto">
          <ModernPortalContent route={route} />
        </main>
      </div>
    </div>
  );
}

function ModernPortalContent({ route }: Readonly<{ route: PortalRoute }>) {
  const { locale } = useLocale();

  const [kicker, titleSv, descSv] = route.kind === "dashboard" ? pageCopy.dashboard : pageCopy[route.kind];
  const title = getRouteTitle(route, titleSv);
  const desc = getRouteDescription(route, descSv);

  return (
    <div className="px-8 py-8 md:px-10">
      {/* Page header */}
      <div className="mb-8 flex items-start justify-between gap-6">
        <div>
          <div className="kicker text-mineral">{kicker}</div>
          <h1 className="mt-2 font-display text-[clamp(1.8rem,3.5vw,3rem)] leading-[1.02] tighten">{title}</h1>
          <p className="mt-2 max-w-[60ch] text-[14px] leading-6 text-ink/60">{desc}</p>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <button type="button" className="border border-ink/15 px-4 py-2 text-[13px] text-ink/65 transition hover:border-ochre hover:text-ochre">
            {locale === "sv" ? "Exportera" : "Export"}
          </button>
          <button type="button" className="bg-ink px-4 py-2 text-[13px] text-paper transition hover:bg-ochre hover:text-ink">
            {locale === "sv" ? "Ny handling" : "New action"}
          </button>
        </div>
      </div>

      {/* Section content */}
      <PortalContent variant="modern-blend" route={route} />
    </div>
  );
}

// ─── DraftPortal entry point ──────────────────────────────────────────────────

export function DraftPortal({ variant, slug, asMain = false }: Readonly<{ variant: DraftVariant; slug: string[]; asMain?: boolean }>) {
  const navBase = asMain ? "/dashboard" : `/design-drafts/${variant}/portal`;
  if (isModern(variant)) {
    return <PortalNavContext.Provider value={navBase}><ModernPortal slug={slug} /></PortalNavContext.Provider>;
  }
  return <PortalNavContext.Provider value={navBase}><EditorialIterationPortal slug={slug} /></PortalNavContext.Provider>;
}

// ─── Shared content components ────────────────────────────────────────────────

function getRouteTitle(route: PortalRoute, fallback: string) {
  if (route.kind === "companies" && route.id) return findCompany(route.id).name;
  if (route.kind === "contacts" && route.id) return findContact(route.id).fullName;
  if (route.kind === "campaigns" && route.id) return findCampaign(route.id).name.sv;
  if (route.kind === "settings" && route.section !== "general") {
    return route.section === "mailboxes" ? "Mailboxes" : route.section === "team" ? "Team" : "Billing";
  }
  return fallback;
}

function getRouteDescription(route: PortalRoute, fallback: string) {
  if (route.kind === "companies" && route.id) return findCompany(route.id).summary.sv;
  if (route.kind === "contacts" && route.id) {
    const contact = findContact(route.id);
    return `${contact.role}. Senaste aktivitet ${formatDate(contact.lastTouch)}.`;
  }
  if (route.kind === "campaigns" && route.id) return findCampaign(route.id).segment.sv;
  return fallback;
}

function PortalContent({ variant, route }: Readonly<{ variant: DraftVariant; route: PortalRoute }>) {
  if (route.kind === "dashboard") return <DashboardShowcase variant={variant} />;
  if (route.kind === "assistant") return <AssistantShowcase variant={variant} />;
  if (route.kind === "leads") return <LeadsShowcase variant={variant} />;
  if (route.kind === "companies") return route.id ? <CompanyDetailShowcase variant={variant} id={route.id} /> : <CompaniesShowcase variant={variant} />;
  if (route.kind === "contacts") return route.id ? <ContactDetailShowcase variant={variant} id={route.id} /> : <ContactsShowcase variant={variant} />;
  if (route.kind === "campaigns") return route.id ? <CampaignDetailShowcase variant={variant} id={route.id} /> : <CampaignsShowcase variant={variant} />;
  if (route.kind === "emails") return <EmailShowcase variant={variant} />;
  if (route.kind === "analytics") return <AnalyticsShowcase variant={variant} />;
  if (route.kind === "inbox") return <InboxShowcase variant={variant} />;
  return <SettingsShowcase variant={variant} section={route.section} />;
}

function DashboardShowcase({ variant }: Readonly<{ variant: DraftVariant }>) {
  const latest = analyticsSeries.at(-1);
  const sent = latest?.sent ?? 0;
  const replies = latest?.replies ?? 0;
  const { locale } = useLocale();

  return (
    <div className="grid gap-10">
      <MetricStrip
        variant={variant}
        metrics={[
          [locale === "sv" ? "Skickade" : "Sent",    String(sent),                    locale === "sv" ? "denna vecka"  : "this week"],
          [locale === "sv" ? "Svar"     : "Replies", formatPercent(replies / sent),    "reply rate"],
          [locale === "sv" ? "Möten"    : "Meetings","18",                             locale === "sv" ? "bokade"       : "booked"],
          ["Pipeline",                                formatCurrency(842000),          locale === "sv" ? "attribuerad"  : "attributed"]
        ]}
      />
      <div className="grid grid-cols-12 gap-x-8 gap-y-10">
        <section className="col-span-12 xl:col-span-8">
          <CompanyLedger variant={variant} rows={companies.slice(0, 5)} />
        </section>
        <aside className={cn("col-span-12 px-5 py-5 xl:col-span-4", surface(variant))}>
          <div className="kicker text-mineral">{locale === "sv" ? "Nästa handling" : "Next action"}</div>
          <div className="mt-5 divide-y divide-ink/15 border-y border-ink/15">
            {[
              ["Byggkompaniet Syd", locale === "sv" ? "Generera mediumvariant med Hyllie-signalen." : "Generate medium variant with the Hyllie signal."],
              ["Nordic Sweat Studios", locale === "sv" ? "Kontrollera ny studio innan uppföljning." : "Check new studio before follow-up."],
              ["Fjord Fastigheter", locale === "sv" ? "Lägg till lokal referens i öppningsrad." : "Add local reference to opening line."]
            ].map(([title, body]) => (
              <div key={title} className="py-5">
                <h3 className="font-display text-2xl italic-disp tighten">{title}</h3>
                <p className="mt-2 text-[15px] leading-6 text-ink/70">{body}</p>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}

function AssistantShowcase({ variant }: Readonly<{ variant: DraftVariant }>) {
  const { locale } = useLocale();
  const messages = locale === "sv" ? [
    ["Du", "Hitta byggbolag i Malmö med expansions- eller rekryteringssignal."],
    ["Snipra", "37 bolag hittade. Byggkompaniet Syd är starkast: ny lokal i Hyllie, fyra platsannonser och tydlig kontaktroll."],
    ["Du", "Generera ett första mejl i mediumlängd."],
    ["Snipra", "Jag använder Hyllie-signalen, rekryteringen och CTA:n från business context."]
  ] : [
    ["You", "Find construction companies in Malmö with expansion or hiring signals."],
    ["Snipra", "37 companies found. Byggkompaniet Syd is strongest: new office in Hyllie, four job listings and a clear contact role."],
    ["You", "Generate a first email in medium length."],
    ["Snipra", "Using the Hyllie signal, the hiring and the CTA from business context."]
  ];

  return (
    <div className="grid grid-cols-12 gap-x-8 gap-y-10">
      <section className={cn("col-span-12 xl:col-span-7", surface(variant))}>
        <div className="px-5 py-4">
          <div className="border border-ink/15 bg-paper2/55 px-4 py-3 text-[15px] text-ink/55">
            {locale === "sv" ? "Sök, analysera, skriv eller pausa..." : "Search, analyse, write or pause..."}
          </div>
        </div>
        <div className="divide-y divide-ink/15 border-t border-ink/15">
          {messages.map(([speaker, message]) => (
            <div key={`${speaker}-${message}`} className="grid grid-cols-12 gap-x-6 px-5 py-5">
              <div className="kicker col-span-3 text-mineral">{speaker}</div>
              <p className="col-span-9 text-[16px] leading-7 text-ink/76">{message}</p>
            </div>
          ))}
        </div>
      </section>
      <section className={cn("col-span-12 px-5 py-5 xl:col-span-5", surface(variant))}>
        <div className="kicker text-mineral">Workflow</div>
        <div className="mt-5 divide-y divide-ink/15 border-y border-ink/15">
          {workflowSteps.map((step, index) => (
            <div key={step} className="grid grid-cols-12 py-4">
              <span className="num col-span-2 font-mono text-sm text-ochre">{String(index + 1).padStart(2, "0")}</span>
              <span className="col-span-10 text-[15px] leading-6">{step}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function LeadsShowcase({ variant }: Readonly<{ variant: DraftVariant }>) {
  const { locale } = useLocale();
  const searches = locale === "sv"
    ? ["Bygg i Malmö", "Gym i Stockholm", "Fastighet Uppsala", "SaaS med rekrytering"]
    : ["Construction in Malmö", "Gyms in Stockholm", "Property in Uppsala", "SaaS with hiring"];

  return (
    <div className="grid gap-10">
      <div className="divide-y divide-ink/15 border-y border-ink/15">
        {searches.map((item, index) => (
          <div key={item} className="grid grid-cols-12 gap-x-6 py-4">
            <span className="kicker col-span-3 text-mineral">{locale === "sv" ? "Sökning" : "Search"} {String(index + 1).padStart(2, "0")}</span>
            <span className="ticker col-span-8 font-display text-xl italic-disp tighten">{item}</span>
            <span className="kicker col-span-1 text-right text-ochre">↗</span>
          </div>
        ))}
      </div>
      <CompanyLedger variant={variant} rows={companies} />
    </div>
  );
}

function CompaniesShowcase({ variant }: Readonly<{ variant: DraftVariant }>) {
  return <CompanyLedger variant={variant} rows={companies} />;
}

function CompanyDetailShowcase({ variant, id }: Readonly<{ variant: DraftVariant; id: string }>) {
  const company = findCompany(id);
  const { locale } = useLocale();
  return (
    <div className="grid gap-10">
      <MetricStrip
        variant={variant}
        metrics={[
          ["Lead score",                            `${company.score}/100`,                     locale === "sv" ? "prioritet"    : "priority"],
          [locale === "sv" ? "Storlek" : "Size",    company.size.replace(" anställda", ""),     locale === "sv" ? "anställda"    : "employees"],
          [locale === "sv" ? "Källor" : "Sources",  String(company.sources.length),             locale === "sv" ? "observerade"  : "observed"],
          ["Status",                                company.status,                             locale === "sv" ? "leadläge"     : "lead stage"]
        ]}
      />
      <div className="grid grid-cols-12 gap-x-8 gap-y-10">
        <section className="col-span-12 xl:col-span-7">
          <div className="kicker text-mineral">{locale === "sv" ? "Signaler" : "Signals"}</div>
          <div className="mt-5 divide-y divide-ink/15 border-y border-ink/15">
            {company.signals.map((signal) => (
              <div key={signal.id} className="grid grid-cols-12 gap-x-6 py-5">
                <div className="kicker col-span-12 text-mineral md:col-span-3">{formatDate(signal.detectedAt)}</div>
                <div className="col-span-12 mt-3 md:col-span-9 md:mt-0">
                  <h3 className="font-display text-2xl italic-disp tighten">{locale === "sv" ? signal.title.sv : signal.title.en}</h3>
                  <p className="mt-2 max-w-[65ch] text-[15px] leading-6 text-ink/70">{locale === "sv" ? signal.summary.sv : signal.summary.en}</p>
                  <p className="kicker mt-4 text-ochre">{signal.source} · {Math.round(signal.confidence * 100)} % confidence</p>
                </div>
              </div>
            ))}
          </div>
        </section>
        <aside className={cn("col-span-12 px-5 py-5 xl:col-span-5", surface(variant))}>
          <h2 className="font-display text-3xl italic-disp tighten text-ochre">{locale === "sv" ? "Rekommenderad säljvinkel" : "Recommended angle"}</h2>
          <p className="mt-4 text-[16px] leading-7 text-ink/75">{locale === "sv" ? company.angle.sv : company.angle.en}</p>
          <div className="rule my-6 text-ink" />
          <p className="kicker text-mineral">CTA</p>
          <p className="mt-3 text-[17px] leading-7">{locale === "sv" ? company.recommendedCta.sv : company.recommendedCta.en}</p>
        </aside>
      </div>
    </div>
  );
}

function ContactsShowcase({ variant }: Readonly<{ variant: DraftVariant }>) {
  return (
    <div className="divide-y divide-ink/15 border-y border-ink/15">
      {contacts.map((contact) => <ContactRow key={contact.id} contact={contact} />)}
    </div>
  );
}

function ContactRow({ contact }: Readonly<{ contact: Contact }>) {
  const navBase = usePortalNav();
  const company = findCompany(contact.companyId);
  return (
    <Link href={`${navBase}/contacts/${contact.id}`} className="row grid grid-cols-12 gap-x-6 py-5 transition hover:bg-ochre/5">
      <div className="ticker col-span-12 md:col-span-4">
        <p className="font-display text-2xl italic-disp tighten">{contact.fullName}</p>
        <p className="mt-1 text-sm text-ink/55">{contact.email}</p>
      </div>
      <div className="kicker col-span-6 mt-3 text-mineral md:col-span-2 md:mt-0">{contact.role}</div>
      <div className="col-span-6 mt-3 text-[15px] md:col-span-3 md:mt-0">{company.name}</div>
      <div className="col-span-8 mt-3 text-sm text-ink/65 md:col-span-2 md:mt-0">{contact.linkedin}</div>
      <div className="col-span-4 mt-3 text-right md:col-span-1 md:mt-0"><StatusWord value={contact.status} /></div>
    </Link>
  );
}

function ContactDetailShowcase({ variant, id }: Readonly<{ variant: DraftVariant; id: string }>) {
  const contact = findContact(id);
  const company = findCompany(contact.companyId);
  const { locale } = useLocale();
  return (
    <div className="grid grid-cols-12 gap-x-8 gap-y-10">
      <dl className="col-span-12 divide-y divide-ink/15 border-y border-ink/15 md:col-span-5">
        {[
          ["Email", contact.email],
          [locale === "sv" ? "Roll" : "Role", contact.role],
          [locale === "sv" ? "Bolag" : "Company", company.name],
          ["Status", contact.status],
          ["LinkedIn provider", contact.linkedin]
        ].map(([label, value]) => (
          <div key={label} className="grid grid-cols-12 py-4">
            <dt className="kicker col-span-5 text-mineral">{label}</dt>
            <dd className="col-span-7 text-[15px]">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="col-span-12 md:col-span-7"><EmailComposer variant={variant} compact /></div>
    </div>
  );
}

function CampaignsShowcase({ variant }: Readonly<{ variant: DraftVariant }>) {
  const navBase = usePortalNav();
  const { locale } = useLocale();
  return (
    <div className="divide-y divide-ink/15 border-y border-ink/15">
      {campaigns.map((campaign) => (
        <Link key={campaign.id} href={`${navBase}/campaigns/${campaign.id}`} className="row grid grid-cols-12 gap-x-6 py-6 transition hover:bg-ochre/5">
          <div className="ticker col-span-12 md:col-span-4">
            <h2 className="font-display text-3xl italic-disp tighten">{locale === "sv" ? campaign.name.sv : campaign.name.en}</h2>
            <p className="mt-2 max-w-[44ch] text-[15px] leading-6 text-ink/65">{locale === "sv" ? campaign.segment.sv : campaign.segment.en}</p>
          </div>
          <div className="kicker col-span-6 mt-4 text-mineral md:col-span-2 md:mt-0">{campaign.geography}</div>
          <div className="num col-span-2 mt-4 font-display text-2xl italic-disp md:mt-0">{campaign.volume}</div>
          <div className="num col-span-2 mt-4 font-display text-2xl italic-disp text-ochre md:mt-0">{formatPercent(campaign.replyRate)}</div>
          <div className="num col-span-2 mt-4 text-right font-display text-2xl italic-disp md:mt-0">{campaign.meetings}</div>
        </Link>
      ))}
    </div>
  );
}

function CampaignDetailShowcase({ variant, id }: Readonly<{ variant: DraftVariant; id: string }>) {
  const campaign = findCampaign(id);
  const { locale } = useLocale();
  return (
    <div className="grid grid-cols-12 gap-x-8 gap-y-10">
      <section className="col-span-12 md:col-span-7">
        <h2 className="kicker text-mineral">{locale === "sv" ? "Sekvenssteg" : "Sequence steps"}</h2>
        <div className="mt-5 divide-y divide-ink/15 border-y border-ink/15">
          {campaign.sequence.map((step) => (
            <div key={`${step.day}-${step.label.sv}`} className="grid grid-cols-12 gap-x-6 py-5">
              <div className="num col-span-2 font-display text-3xl italic-disp text-ochre">D{step.day}</div>
              <div className="col-span-10">
                <p className="font-display text-2xl italic-disp tighten">{locale === "sv" ? step.label.sv : step.label.en}</p>
                <p className="mt-2 text-[15px] leading-6 text-ink/68">{locale === "sv" ? step.goal.sv : step.goal.en}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
      <aside className={cn("col-span-12 px-5 py-5 md:col-span-5", surface(variant))}>
        <h2 className="kicker text-mineral">Guardrails</h2>
        <div className="mt-5 space-y-4 text-[16px] leading-7 text-ink/75">
          <p>{locale === "sv" ? "Stop on reply är aktiverat." : "Stop on reply is active."}</p>
          <p>{locale === "sv" ? "Skickfönster: tisdag till torsdag, 08:30 till 15:20." : "Send window: Tuesday to Thursday, 08:30 to 15:20."}</p>
          <p>{locale === "sv" ? "Suppression kontrolleras före varje queue." : "Suppression is checked before every queue."}</p>
          <p>{locale === "sv" ? "Ton:" : "Tone:"} {locale === "sv" ? businessContext.tone.sv : businessContext.tone.en}</p>
        </div>
      </aside>
    </div>
  );
}

function EmailShowcase({ variant }: Readonly<{ variant: DraftVariant }>) {
  return <EmailComposer variant={variant} />;
}

function EmailComposer({ variant, compact = false }: Readonly<{ variant: DraftVariant; compact?: boolean }>) {
  const selected = emailVariants[0];
  const company = findCompany(selected.companyId);
  const { locale } = useLocale();
  return (
    <div className={cn("grid grid-cols-12 gap-x-8 gap-y-10")}>
      {!compact ? (
        <aside className="col-span-12 md:col-span-4">
          <h2 className="kicker text-mineral">Inputs</h2>
          <div className="mt-5 divide-y divide-ink/15 border-y border-ink/15">
            {[
              [locale === "sv" ? "Företag" : "Company", company.name],
              [locale === "sv" ? "Signal" : "Signal", locale === "sv" ? company.latestSignal.sv : company.latestSignal.en],
              [locale === "sv" ? "Erbjudande" : "Offer", locale === "sv" ? businessContext.offer.sv : businessContext.offer.en],
              ["CTA", locale === "sv" ? businessContext.cta.sv : businessContext.cta.en]
            ].map(([label, value]) => (
              <div key={label} className="py-4">
                <p className="kicker text-mineral">{label}</p>
                <p className="mt-2 text-[15px] leading-6 text-ink/72">{value}</p>
              </div>
            ))}
          </div>
        </aside>
      ) : null}
      <section className={cn("col-span-12", compact ? "" : "md:col-span-8")}>
        <div className="border-y border-ink/15 py-5">
          <p className="kicker text-ochre">{selected.length} · {selected.type}</p>
          <h2 className="mt-4 font-display text-4xl italic-disp tighten">{locale === "sv" ? selected.subject.sv : selected.subject.en}</h2>
        </div>
        <textarea
          className="mt-6 min-h-[420px] w-full resize-y border border-ink/15 bg-paper2/70 p-6 text-[16px] leading-8 text-ink outline-none transition focus:border-ochre"
          defaultValue={locale === "sv" ? selected.body.sv : selected.body.en}
        />
        <div className="mt-5 flex flex-wrap gap-3">
          {(locale === "sv"
            ? ["Kortare", "Tydligare CTA", "Mer personlig", "Skriv om"]
            : ["Shorter", "Clearer CTA", "More personal", "Rewrite"]
          ).map((action) => (
            <button key={action} type="button" className="border border-ink/15 px-4 py-3 font-mono text-xs uppercase tracking-[0.16em] transition hover:border-ochre hover:text-ochre active:translate-y-px">
              {action}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

function AnalyticsShowcase({ variant }: Readonly<{ variant: DraftVariant }>) {
  const { locale } = useLocale();
  return (
    <div className={cn("divide-y divide-ink/15 border-y border-ink/15", isModern(variant) ? "font-modern" : "")}>
      {analyticsSeries.map((point) => (
        <div key={point.week} className="grid grid-cols-12 gap-x-6 py-5">
          <div className="kicker col-span-3 text-mineral">{point.week}</div>
          <div className="num col-span-3 font-display text-2xl italic-disp">{point.sent} {locale === "sv" ? "skick" : "sent"}</div>
          <div className="num col-span-3 font-display text-2xl italic-disp text-ochre">{formatPercent(point.replies / point.sent)} {locale === "sv" ? "svar" : "reply"}</div>
          <div className="num col-span-3 text-right font-display text-2xl italic-disp">{point.meetings} {locale === "sv" ? "möten" : "meetings"}</div>
          <div className="col-span-12 mt-4 h-2 bg-ink/10">
            <div className="h-2 bg-ochre" style={{ width: `${Math.min(92, (point.replies / point.sent) * 420)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function InboxShowcase({ variant }: Readonly<{ variant: DraftVariant }>) {
  const { locale } = useLocale();
  const rows = locale === "sv" ? [
    ["Amal Hassan", "Låter relevant. Skicka gärna exempel på IT-chefer i regionen.", "positive"],
    ["Jonas Åkerström", "Inte rätt läge just nu, men återkom efter sommaren.", "later"],
    ["Mikael Berg", "Kan du förtydliga vad ni menar med signaler?", "objection"]
  ] : [
    ["Amal Hassan", "Sounds relevant. Feel free to send examples of IT managers in the region.", "positive"],
    ["Jonas Åkerström", "Not the right timing now, but reach out after summer.", "later"],
    ["Mikael Berg", "Can you clarify what you mean by signals?", "objection"]
  ];

  return (
    <div className={cn("divide-y divide-ink/15 border-y border-ink/15", isModern(variant) ? "font-modern" : "")}>
      {rows.map(([name, body, status]) => (
        <div key={name} className="grid grid-cols-12 gap-x-6 py-5">
          <div className="font-display col-span-12 text-2xl italic-disp tighten md:col-span-3">{name}</div>
          <p className="col-span-12 mt-3 text-[16px] leading-7 text-ink/72 md:col-span-7 md:mt-0">{body}</p>
          <div className="col-span-12 mt-3 text-right md:col-span-2 md:mt-0"><StatusWord value={status} /></div>
        </div>
      ))}
    </div>
  );
}

function SettingsShowcase({
  variant,
  section
}: Readonly<{ variant: DraftVariant; section: "general" | "mailboxes" | "team" | "billing" }>) {
  const { locale } = useLocale();
  return (
    <div className="grid grid-cols-12 gap-x-8 gap-y-10">
      <nav className="kicker col-span-12 flex flex-wrap gap-5 text-mineral md:col-span-3 md:block md:space-y-4">
        {[
          [`/design-drafts/${variant}/portal/settings`,          "General"],
          [`/design-drafts/${variant}/portal/settings/mailboxes`,"Mailboxes"],
          [`/design-drafts/${variant}/portal/settings/team`,     "Team"],
          [`/design-drafts/${variant}/portal/settings/billing`,  "Billing"]
        ].map(([href, label]) => <Link key={href} href={href} className="block hover:text-ochre">{label}</Link>)}
      </nav>
      <div className="col-span-12 md:col-span-9">
        {section === "general" ? <BusinessContextSettings locale={locale} /> : null}
        {section === "mailboxes" ? <TextList title="Mailbox health" items={["sales@snipra-demo.se · healthy · 96 skick per dag", "elin@kundbolag.se · warming · 34 skick per dag"]} /> : null}
        {section === "team" ? <TextList title={locale === "sv" ? "Teamroller" : "Team roles"} items={[locale === "sv" ? "Owner · full åtkomst" : "Owner · full access", locale === "sv" ? "Sales lead · kampanjer och inbox" : "Sales lead · campaigns and inbox", locale === "sv" ? "Researcher · bolag och signaler" : "Researcher · companies and signals", locale === "sv" ? "Viewer · läsbehörighet" : "Viewer · read access"]} /> : null}
        {section === "billing" ? <TextList title="Billing" items={[locale === "sv" ? "Plan · Team · 14 900 kr/mån" : "Plan · Team · SEK 14,900/mo", locale === "sv" ? "Leads · 312 av 1000 denna månad" : "Leads · 312 of 1,000 this month", locale === "sv" ? "Seats · 4 av 8 aktiva användare" : "Seats · 4 of 8 active users"]} /> : null}
      </div>
    </div>
  );
}

function BusinessContextSettings({ locale }: Readonly<{ locale: string }>) {
  return (
    <div className="grid gap-5">
      {[
        [locale === "sv" ? "Produkt" : "Product",      locale === "sv" ? businessContext.product.sv : businessContext.product.en],
        ["ICP",                                         locale === "sv" ? businessContext.icp.sv     : businessContext.icp.en],
        [locale === "sv" ? "Tonalitet" : "Tone",       locale === "sv" ? businessContext.tone.sv    : businessContext.tone.en],
        [locale === "sv" ? "Erbjudande" : "Offer",     locale === "sv" ? businessContext.offer.sv   : businessContext.offer.en],
        ["CTA",                                         locale === "sv" ? businessContext.cta.sv     : businessContext.cta.en]
      ].map(([label, value]) => (
        <label key={label} className="grid grid-cols-12 gap-x-6 border-t border-ink/15 pt-5">
          <span className="kicker col-span-12 text-mineral md:col-span-3">{label}</span>
          <textarea className="col-span-12 mt-3 min-h-24 border border-ink/15 bg-paper2/70 p-4 text-[15px] leading-6 outline-none focus:border-ochre md:col-span-9 md:mt-0" defaultValue={value} />
        </label>
      ))}
    </div>
  );
}

function TextList({ title, items }: Readonly<{ title: string; items: string[] }>) {
  return (
    <div>
      <h2 className="kicker text-mineral">{title}</h2>
      <div className="mt-4 divide-y divide-ink/15 border-y border-ink/15">
        {items.map((item) => (
          <p key={item} className="py-4 text-[15px] leading-6 text-ink/72">{item}</p>
        ))}
      </div>
    </div>
  );
}

function MetricStrip({ variant, metrics }: Readonly<{ variant: DraftVariant; metrics: string[][] }>) {
  const modern = isModern(variant);
  return (
    <dl className={cn("grid grid-cols-12 gap-x-8 gap-y-8", modern ? "font-modern" : "")}>
      {metrics.map(([label, value, detail], index) => (
        <div key={label} className={cn("border-t border-ink/15 pt-4", modern ? "col-span-6 md:col-span-3" : "col-span-6 md:col-span-3")}>
          <dt className="kicker text-mineral">{label}</dt>
          <dd className={`num mt-3 font-display text-4xl italic-disp tighten ${index === 1 ? "text-ochre" : ""}`}>{value}</dd>
          <p className="mt-2 text-[14px] leading-6 text-ink/65">{detail}</p>
        </div>
      ))}
    </dl>
  );
}

function CompanyLedger({ variant, rows }: Readonly<{ variant: DraftVariant; rows: Company[] }>) {
  const navBase = usePortalNav();
  const { locale } = useLocale();
  return (
    <div className={cn("border-y border-ink/15", isModern(variant) ? "font-modern" : "")}>
      <div className="hidden grid-cols-12 gap-x-5 border-b border-ink/15 py-4 md:grid">
        <div className="kicker col-span-4 text-mineral">{locale === "sv" ? "Bolag" : "Company"}</div>
        <div className="kicker col-span-3 text-mineral">{locale === "sv" ? "Segment" : "Segment"}</div>
        <div className="kicker col-span-3 text-mineral">{locale === "sv" ? "Kontakt" : "Contact"}</div>
        <div className="kicker col-span-2 text-right text-mineral">Score</div>
      </div>
      <div className="divide-y divide-ink/15">
        {rows.map((company) => {
          const contact = company.contacts[0];
          return (
            <Link key={company.id} href={`${navBase}/companies/${company.id}`} className="row grid grid-cols-12 gap-x-5 gap-y-3 py-5 transition hover:bg-ochre/5">
              <div className="ticker col-span-8 md:col-span-4">
                <p className="font-display text-[22px] italic-disp leading-none tighten">{company.name}</p>
                <p className="mt-1 text-sm text-ink/55">{company.website}</p>
              </div>
              <div className="kicker col-span-8 mt-1 text-mineral md:col-span-3 md:mt-2">{company.industry} · {company.location}</div>
              <div className="col-span-8 mt-1 md:col-span-3">
                <p className="text-[15px]">{contact.fullName}</p>
                <p className="mt-1 text-sm text-ink/55">{contact.role}</p>
              </div>
              <div className="num col-span-4 row-start-1 text-right font-display text-2xl italic-disp leading-none text-ochre md:col-span-2 md:row-auto md:mt-1">{company.score}</div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function StatusWord({ value }: Readonly<{ value: string }>) {
  const accent = ["recommended", "active", "replied", "queued", "positive"].includes(value);
  return <span className={`kicker ${accent ? "text-ochre" : "text-mineral"}`}>{value}</span>;
}
