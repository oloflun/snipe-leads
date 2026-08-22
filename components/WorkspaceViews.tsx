"use client";

import Link from "next/link";

import { SoulEditor } from "@/components/SoulEditor";
import { PageShell, useArbetsvag } from "@/components/AppShell";
import { btnPrimary, btnSecondary } from "@/components/ui";
import { LoginForm } from "@/components/auth/LoginForm";
import { SignOutButton } from "@/components/auth/SignOutButton";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { Analys } from "@/components/dashboard/Analys";
import { Discovery } from "@/components/leads/Discovery";
import { LeadsControls } from "@/components/leads/LeadsControls";
import { Affarskontext } from "@/components/settings/Affarskontext";
import { KunskapsbasPanel } from "@/components/settings/Kunskapsbas";
import { SupportRegler } from "@/components/settings/SupportRegler";
import { SettingsNav } from "@/components/settings/SettingsNav";
import { TeamSettings } from "@/components/settings/TeamSettings";
import { AddonSettings } from "@/components/settings/AddonSettings";
import { Inkorgar } from "@/components/settings/Inkorgar";
import { PlanSettings } from "@/components/settings/PlanSettings";
import { OnboardingForm } from "@/components/auth/OnboardingForm";
import { signOut } from "@/lib/actions/auth";
import {
  businessContext,
  companies,
  contacts,
  emailVariants,
  findCompany,
  findContact,
  signals,
  workflowSteps
} from "@/lib/mock-data";
import type { Company, Contact } from "@/lib/mock-data";
import type { SettingsSectionKey } from "@/lib/routes";
import { useLocale } from "@/lib/i18n";
import { cn, formatDate } from "@/lib/utils";

function EditorialButton({ href, children, dark = false }: Readonly<{ href: string; children: React.ReactNode; dark?: boolean }>) {
  return (
    <Link href={href} className={cn(dark ? btnSecondary : btnPrimary)}>
      {children}
      <span aria-hidden>↗</span>
    </Link>
  );
}

function LedgerMetric({ label, value, detail }: Readonly<{ label: string; value: string; detail: string }>) {
  return (
    <div className="border-t border-ink/15 pt-4">
      <dt className="kicker text-mineral">{label}</dt>
      <dd className="num mt-3 text-[1.75rem] font-semibold tabular-nums tracking-[-0.02em]">{value}</dd>
      <p className="mt-2 text-[14px] leading-6 text-ink/65">{detail}</p>
    </div>
  );
}

function StatusWord({ value }: Readonly<{ value: string }>) {
  const accent = ["recommended", "active", "replied", "queued"].includes(value);
  return <span className={`kicker ${accent ? "text-ochre" : "text-mineral"}`}>{value}</span>;
}

function CompanyLedger({ rows = companies }: Readonly<{ rows?: Company[] }>) {
  const { text } = useLocale();
  const vag = useArbetsvag();
  return (
    <div className="overflow-x-auto border-y border-ink/15">
      <div className="hidden min-w-[1120px] grid-cols-12 gap-x-6 border-b border-ink/15 py-4 md:grid">
        {/* Utan kolumnen "Status". Den visade det råa statusordet
            ("recommended", "queued") i en kundvänd tabell — våra interna
            värden, oöversatta, i en vy där resten är skriven på svenska. */}
        {["Bolag", "Segment", "Kontakt", "Signal", "Score"].map((head, index) => (
          <div key={head} className={cn("kicker text-mineral", index === 0 ? "col-span-3" : index === 3 ? "col-span-3" : "col-span-2", index > 3 ? "text-right" : "")}>
            {head}
          </div>
        ))}
      </div>
      <div className="min-w-[1120px] divide-y divide-ink/15">
        {rows.map((company) => {
          const contact = company.contacts[0];
          return (
            <Link key={company.id} href={vag(`/dashboard/companies/${company.id}`)} className="row grid grid-cols-12 gap-x-6 py-5 transition hover:bg-paper2/60">
              <div className="ticker col-span-3">
                <p className="text-[1.0625rem] font-semibold tracking-[-0.01em]">{company.name}</p>
                <p className="mt-1 text-sm text-ink/55">{company.website}</p>
              </div>
              <div className="kicker col-span-2 mt-2 text-mineral">{company.industry} · {company.location}</div>
              <div className="col-span-2 mt-1">
                <p className="text-[15px]">{contact.fullName}</p>
                <p className="mt-1 text-sm text-ink/55">{contact.role}</p>
              </div>
              <div className="col-span-3 text-[15px] leading-6 text-ink/72">{text(company.latestSignal)}</div>
              <div className="num col-span-2 text-right text-[1.0625rem] font-semibold tabular-nums">{company.score}</div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function SignalTimeline({ company }: Readonly<{ company: Company }>) {
  const { text } = useLocale();
  return (
    <div className="space-y-6">
      {company.signals.map((signal) => (
        <div key={signal.id} className="grid grid-cols-12 gap-x-6 border-t border-ink/15 pt-5">
          <div className="kicker col-span-12 text-mineral md:col-span-3">{formatDate(signal.detectedAt)}</div>
          <div className="col-span-12 mt-3 md:col-span-9 md:mt-0">
            <h3 className="text-[1.0625rem] font-semibold tracking-[-0.01em]">{text(signal.title)}</h3>
            <p className="mt-2 max-w-[65ch] text-[15px] leading-6 text-ink/70">{text(signal.summary)}</p>
            <p className="kicker mt-4 text-ink/45">{signal.source} · {Math.round(signal.confidence * 100)} % confidence</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export function AssistantView() {
  return (
    <PageShell
      kicker="Assistant · embedded"
      title="Assistenten är ett reglage i arbetsflödet, inte ett chattfönster."
      description="Varje kommando landar i discovery, research, sekvens, email eller analys. Det går att följa exakt vilken signal som styrde texten."
    >
      <div className="grid grid-cols-12 gap-x-8 gap-y-10">
        <div className="col-span-12 border-y border-ink/15 md:col-span-7">
          {[
            ["Du", "Hitta byggbolag i Malmö med expansions- eller rekryteringssignal."],
            ["Snajp", "37 bolag hittade. Byggkompaniet Syd är starkast: ny lokal i Hyllie, fyra platsannonser och tydlig kontaktroll."],
            ["Du", "Generera ett första mejl i mediumlängd."],
            ["Snajp", "Jag använder Hyllie-signalen, arbetsledarrekryteringen och CTA:n från business context. Tonen hålls lågmäld."]
          ].map(([speaker, message]) => (
            <div key={`${speaker}-${message}`} className="grid grid-cols-12 gap-x-6 border-b border-ink/15 py-5 last:border-b-0">
              <div className="kicker col-span-3 text-mineral">{speaker}</div>
              <p className="col-span-9 text-[16px] leading-7 text-ink/78">{message}</p>
            </div>
          ))}
        </div>
        <div className="col-span-12 md:col-span-5">
          <div className="kicker text-mineral">Stateful workflow</div>
          <div className="mt-4 divide-y divide-ink/15 border-y border-ink/15">
            {workflowSteps.map((step, index) => (
              <div key={step} className="grid grid-cols-12 py-3">
                <span className="num col-span-2 font-mono text-sm text-ink/45">{String(index + 1).padStart(2, "0")}</span>
                <span className="col-span-10 text-[15px]">{step}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </PageShell>
  );
}

/**
 * Leads-vyns innehåll utan skal, så att startsidan kan montera den bredvid
 * kundtjänstvyn utan att nästla två PageShell (alltså två headers).
 *
 * Discovery-formuläret är det som FAKTISKT startar en körning; bolagsregistret
 * under är exempeldata tills körningen skrivit riktiga prospekt.
 */
export function LeadsBody({ demo = false }: Readonly<{ demo?: boolean }>) {
  return (
    <>
      <Discovery demo={demo} />
      <div className="mt-12">
        <CompanyLedger />
      </div>
    </>
  );
}

export function LeadsView({ demo = false }: Readonly<{ demo?: boolean }>) {
  return (
    <PageShell
      title="Bolag sorterade efter din produkt och ton, inte efter en mall."
      description="Specificera vilka typer av kunder ni söker. Agenterna letar upp potentiella bolag baserat på dina ord."
    >
      <LeadsBody demo={demo} />
    </PageShell>
  );
}

export function CompaniesView() {
  return (
    <PageShell
      kicker="Companies"
      title="Företagsintelligens, källor och säljvinklar i samma vy."
      description="Ingen bolagssida får vara en kortsamling. Den ska läsa som en researchpromemoria."
    >
      <CompanyLedger />
    </PageShell>
  );
}

export function CompanyDetailView({ id }: Readonly<{ id: string }>) {
  const { text } = useLocale();
  const company = findCompany(id);
  const vag = useArbetsvag();
  return (
    <PageShell
      kicker={`${company.industry} · ${company.location}`}
      title={company.name}
      description={text(company.summary)}
      action={<EditorialButton href={vag("/dashboard/emails")}>Generera email</EditorialButton>}
    >
      <div className="grid grid-cols-12 gap-x-8 gap-y-12">
        <dl className="col-span-12 grid grid-cols-12 gap-x-8 gap-y-8">
          <div className="col-span-6 md:col-span-3"><LedgerMetric label="Lead score" value={`${company.score}/100`} detail={text(company.latestSignal)} /></div>
          <div className="col-span-6 md:col-span-3"><LedgerMetric label="Storlek" value={company.size.replace(" anställda", "")} detail="anställda" /></div>
          <div className="col-span-6 md:col-span-3"><LedgerMetric label="Källor" value={String(company.sources.length)} detail="provenance-poster" /></div>
          <div className="col-span-6 md:col-span-3"><LedgerMetric label="Status" value={company.status} detail="nuvarande leadläge" /></div>
        </dl>
        <section className="col-span-12 md:col-span-7">
          <h2 className="kicker text-mineral">Signal timeline</h2>
          <div className="mt-6"><SignalTimeline company={company} /></div>
        </section>
        <aside className="col-span-12 border-y border-ink/15 py-6 md:col-span-5">
          <h2 className="text-[1.25rem] font-semibold tracking-[-0.02em]">Rekommenderad säljvinkel</h2>
          <p className="mt-4 text-[16px] leading-7 text-ink/75">{text(company.angle)}</p>
          <div className="rule my-6 text-ink" />
          <p className="kicker text-mineral">Recommended CTA</p>
          <p className="mt-3 text-[17px] leading-7">{text(company.recommendedCta)}</p>
        </aside>
        <section className="col-span-12 grid grid-cols-12 gap-x-8 gap-y-8">
          <TextList title="Pain points" items={company.painPoints.map(text)} />
          <TextList title="Möjligheter" items={company.opportunities.map(text)} />
          <TextList title="Källor" items={company.sources.map((source) => `${source.label} · ${source.observedAt}`)} />
        </section>
      </div>
    </PageShell>
  );
}

function TextList({ title, items }: Readonly<{ title: string; items: string[] }>) {
  return (
    <div className="col-span-12 md:col-span-4">
      <h2 className="kicker text-mineral">{title}</h2>
      <div className="mt-4 divide-y divide-ink/15 border-y border-ink/15">
        {items.map((item) => (
          <p key={item} className="py-4 text-[15px] leading-6 text-ink/72">{item}</p>
        ))}
      </div>
    </div>
  );
}

export function ContactsView() {
  return (
    <PageShell kicker="Contacts" title="Kontaktpersoner med roll, källa och suppression-status." description="Kontaktlagret är tydligt med vad som är känt, vad som är adapterbaserat och vad som kräver manuell enrichment.">
      <div className="divide-y divide-ink/15 border-y border-ink/15">
        {contacts.map((contact) => <ContactRow key={contact.id} contact={contact} />)}
      </div>
    </PageShell>
  );
}

function ContactRow({ contact }: Readonly<{ contact: Contact }>) {
  const company = findCompany(contact.companyId);
  const vag = useArbetsvag();
  return (
    <Link href={vag(`/dashboard/contacts/${contact.id}`)} className="row grid grid-cols-12 gap-x-6 py-5 transition hover:bg-paper2/60">
      <div className="ticker col-span-12 md:col-span-4">
        <p className="text-[1.0625rem] font-semibold tracking-[-0.01em]">{contact.fullName}</p>
        <p className="mt-1 text-sm text-ink/55">{contact.email}</p>
      </div>
      <div className="kicker col-span-6 mt-3 text-mineral md:col-span-2 md:mt-0">{contact.role}</div>
      <div className="col-span-6 mt-3 text-[15px] md:col-span-3 md:mt-0">{company.name}</div>
      <div className="col-span-8 mt-3 text-sm text-ink/65 md:col-span-2 md:mt-0">{contact.linkedin}</div>
      <div className="col-span-4 mt-3 text-right md:col-span-1 md:mt-0"><StatusWord value={contact.status} /></div>
    </Link>
  );
}

export function ContactDetailView({ id }: Readonly<{ id: string }>) {
  const contact = findContact(id);
  const company = findCompany(contact.companyId);
  return (
    <PageShell kicker={company.name} title={contact.fullName} description={`${contact.role}. Senaste aktivitet ${formatDate(contact.lastTouch)}. LinkedIn-lagret använder ${contact.linkedin}.`}>
      <div className="grid grid-cols-12 gap-x-8 gap-y-10">
        <dl className="col-span-12 divide-y divide-ink/15 border-y border-ink/15 md:col-span-5">
          {[
            ["Email", contact.email],
            ["Roll", contact.role],
            ["Bolag", company.name],
            ["Status", contact.status],
            ["LinkedIn provider", contact.linkedin]
          ].map(([label, value]) => (
            <div key={label} className="grid grid-cols-12 py-4">
              <dt className="kicker col-span-5 text-mineral">{label}</dt>
              <dd className="col-span-7 text-[15px]">{value}</dd>
            </div>
          ))}
        </dl>
        <div className="col-span-12 md:col-span-7"><EmailManuscript compact /></div>
      </div>
    </PageShell>
  );
}

export function EmailsView() {
  return (
    <PageShell kicker="Email studio" title="Personaliseringens manusbord." description="Ämnesrad, öppningsrad, cold email och uppföljningar visas tillsammans med signal, källa och CTA.">
      <EmailManuscript />
    </PageShell>
  );
}

function EmailManuscript({ compact = false }: Readonly<{ compact?: boolean }>) {
  const { text } = useLocale();
  const selected = emailVariants[0];
  const company = findCompany(selected.companyId);
  return (
    <div className={cn("grid grid-cols-12 gap-x-8 gap-y-10", compact ? "" : "")}>
      {!compact ? (
        <aside className="col-span-12 md:col-span-4">
          <h2 className="kicker text-mineral">Inputs</h2>
          <div className="mt-5 divide-y divide-ink/15 border-y border-ink/15">
            {[
              ["Företag", company.name],
              ["Signal", text(company.latestSignal)],
              ["Erbjudande", text(businessContext.offer)],
              ["CTA", text(businessContext.cta)]
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
          <p className="kicker text-ink/45">{selected.length} · {selected.type}</p>
          <h2 className="mt-4 text-[1.75rem] font-semibold tabular-nums tracking-[-0.02em]">{text(selected.subject)}</h2>
        </div>
        <textarea
          className="mt-6 min-h-[420px] w-full resize-y border border-ink/15 bg-paper2/70 p-6 text-[16px] leading-8 text-ink outline-none transition focus:border-ochre"
          defaultValue={text(selected.body)}
        />
        <div className="mt-5 flex flex-wrap gap-3">
          {["Kortare", "Skriv om", "Förbättra", "Personalisera", "Översätt", "A/B-varianter", "Uppföljning", "Analysera"].map((action) => (
            <button key={action} type="button" className={btnSecondary}>
              {action}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

/**
 * Analysvyn. Innehållet bor i components/dashboard/Analys.tsx.
 *
 * Här låg tidigare `analyticsSeries` ur lib/mock-data.ts, alltså v16-v21 och
 * "6 möten", renderat likadant för varje INLOGGAD kund. Talen var påhittade,
 * ingenting sa det, och tabellen såg komplett ut — vilket är precis varför
 * ingen ifrågasatte den. Se docstringen i Analys.tsx för reglerna som ersatte
 * den, och för varför möteskolumnen är borta i stället för nollställd.
 */
export function AnalyticsView({ demo = false }: Readonly<{ demo?: boolean }>) {
  return (
    <PageShell
      kicker="Analys"
      title="Analys som läser som en resultattabell, inte en chart-demo."
      description="Skick, svar och ärenden per vecka — räknat ur din egen arbetsyta."
    >
      <Analys demo={demo} />
    </PageShell>
  );
}

export function InboxView() {
  return (
    <PageShell kicker="Inbox" title="Svar klassificeras innan nästa steg." description="Reply classifier skiljer på positivt svar, invändning, frånvaro, fel person, unsubscribe och bokningsintresse.">
      <div className="divide-y divide-ink/15 border-y border-ink/15">
        {/* Alla SEX klasser beskrivningen ovan lovar. Tidigare fanns tre, och
            en demo som utlovar sex kategorier men visar tre ser ut som att
            hälften av klassificeraren är trasig — vilket är precis den frågan
            man inte vill få mitt i en pitch.

            Svaren är skrivna som riktiga svenska mejlsvar: korta, ofullständiga
            meningar, ingen artighetsfras. Ett påhittat svar som låter som en
            broschyr avslöjar att datan är påhittad. */}
        {[
          ["Amal Hassan", "Låter relevant. Skicka gärna exempel på IT-chefer i regionen.", "positive"],
          ["Elin Norberg", "Vi kan ta ett kort möte. Tisdag 14 eller torsdag 10 funkar.", "booking"],
          ["Mikael Berg", "Kan du förtydliga vad ni menar med signaler? Vi har testat liknande förut.", "objection"],
          ["Jonas Åkerström", "Inte rätt läge just nu, men återkom efter sommaren.", "later"],
          ["Karin Wikström", "Jag är föräldraledig till mars. Kontakta Petra Lund i stället.", "wrong_person"],
          ["Automatiskt svar · Sofia Ek", "Jag är på semester till den 12 augusti och läser mejl sporadiskt.", "away"],
          ["Tobias Lindqvist", "Ta bort mig från utskicken tack.", "unsubscribe"]
        ].map(([name, body, status]) => (
          <div key={name} className="grid grid-cols-12 gap-x-6 py-5">
            <div className="col-span-12 text-[1.0625rem] font-semibold tracking-[-0.01em] md:col-span-3">{name}</div>
            <p className="col-span-12 mt-3 text-[16px] leading-7 text-ink/72 md:col-span-7 md:mt-0">{body}</p>
            <div className="col-span-12 mt-3 text-right md:col-span-2 md:mt-0"><StatusWord value={status} /></div>
          </div>
        ))}
      </div>
    </PageShell>
  );
}

export function SettingsView({ section = "foretaget" }: Readonly<{ section?: SettingsSectionKey }>) {
  const titles: Record<SettingsSectionKey, string> = {
    foretaget: "Företaget",
    mailboxes: "Inkorgar",
    team: "Teamroller och audit-logik.",
    billing: "Plan och fakturering",
    affarskontext: "Affärskontext",
    kunskapsbas: "Kunskapsbas",
    leads: "Målgrupp och autonomi",
    regler: "Fack och autosvar",
    soul: "Er röst",
    addons: "Tillägg"
  };
  // Beskrivningen var tidigare EN generisk sträng för alla sektioner. På
  // röstsidan blev den både felaktig (den beskriver inte sektionen) och
  // olämplig: den räknade upp "Supabase Auth och RLS" för en KUND, som varken
  // känner igen orden eller behöver veta vår stack. Att stacken sedan byttes
  // gjorde texten dessutom osann — vilket är själva argumentet mot att skriva
  // ut infrastruktur i en kundvänd yta.
  const descriptions: Record<SettingsSectionKey, string> = {
    foretaget: "Bolaget bakom arbetsytan — namn, organisationsnummer och webbplats.",
    mailboxes: "Vilka mejladresser agenterna läser och svarar från.",
    team: "Vilka som har tillgång till arbetsytan, och vad de får göra.",
    billing: "Vilket paket arbetsytan har, och vad som ingår i det.",
    affarskontext: "Vad ni säljer och till vem. Båda agenterna läser härifrån.",
    kunskapsbas: "Dokumenten agenterna svarar ur. Ligger inget här gissar de aldrig — de eskalerar.",
    leads: "Vilka bolag agenterna ska leta efter, och hur långt de får gå på egen hand.",
    regler: "Vilka ärenden agenterna får besvara själva, och vilka som alltid går till en människa.",
    soul: "Beskriv hur ni låter. Agenterna skriver så i både utskick och svar — dokumentet är delat mellan dem.",
    addons: "Det agenterna kan göra utöver det som ingår i er plan."
  };
  return (
    <PageShell title={titles[section]} description={descriptions[section]}>
      {/* gap-x först från md. grid-cols-12 med gap-x-8 kräver 11 x 32px = 352px
          BARA till mellanrum: vid 320px-vyn (288px container) klampades alla
          tolv kolumner till 0px, och rutnätet blev 352px brett oavsett
          innehåll — "BILLING" hamnade utanför vyn, dolt av
          body{overflow-x:hidden} i stället för att synas som horisontell
          scroll. Uppmätt via gridTemplateColumns = "0px 0px 0px ...".
          På mobil ligger allt ändå staplat i col-span-12, så x-mellanrummet
          gjorde ingen nytta där. Samma mönster finns på tre ställen till i
          den här filen — de är inte visuellt verifierade och lämnas orörda. */}
      <div className="grid grid-cols-12 gap-x-0 gap-y-10 md:gap-x-8">
        {/* min-w-0: ett grid-barn har min-width:auto som default och vägrar
            därför krympa under sitt innehåll — flex-wrap får aldrig chansen
            att bryta raden. Med fyra flikar rymdes raden ändå (281px); den
            femte ("Röst") tog den till 334px mot 288px tillgängligt vid
            320px-vyn, och "BILLING" klipptes av body{overflow-x:hidden}
            i stället för att radbrytas. Uppmätt, inte gissat. */}
        {/* SettingsNav och inte en egen lista.

            Här låg tidigare sex hårdkodade Link:ar — oöversatta ("General",
            "Mailboxes", "Billing"), ogrupperade och utan aktiv-markering — och
            SAMTIDIGT renderade app/settings/layout.tsx den grupperade
            SettingsNav i en aside. Två navigationer till samma sex sidor,
            staplade i samma vy. Uppmätt i skärmdump, inte antaget.

            Grupperingen per agent är hela poängen: "Röst och tonläge" hör till
            leads-agenten och "Inkorgar" till kundtjänstagenten, och en platt
            lista tvingar läsaren att veta det innan hen klickar. */}
        <div className="col-span-12 md:col-span-3">
          <SettingsNav />
          {/* Utloggningen bor här och inte i navigationsraden: den hör till
              kontot, inte till arbetsytan, och /settings är den enda ytan som
              alltid kräver en session. */}
          <div className="mt-8 border-t border-ink/15 pt-6">
            <SignOutButton />
          </div>
        </div>
        <div className="col-span-12 md:col-span-9">
          {section === "foretaget" ? <CompanySettings /> : null}
          {section === "affarskontext" ? <Affarskontext /> : null}
          {section === "kunskapsbas" ? <KunskapsbasPanel /> : null}
          {section === "regler" ? <SupportRegler /> : null}
          {section === "leads" ? <LeadsControls /> : null}
          {section === "soul" ? <SoulEditor /> : null}
          {section === "mailboxes" ? <Inkorgar /> : null}
          {section === "team" ? <TeamSettings /> : null}
          {section === "addons" ? <AddonSettings /> : null}
          {section === "billing" ? <PlanSettings /> : null}
        </div>
      </div>
    </PageShell>
  );
}


/**
 * Företaget bakom arbetsytan. Uppgifterna kommer från onboardingen och ändras
 * där — den här sidan visar dem, den äger dem inte. Ett andra formulär mot
 * samma rad blir två sanningar den dag bara det ena sparas.
 */
function CompanySettings() {
  const { workspaceName, products, isDemo } = useDashboard();
  return (
    <div className="grid gap-5">
      <div className="grid grid-cols-12 gap-x-6 border-t border-ink/15 pt-5">
        <span className="kicker col-span-12 text-mineral md:col-span-3">Arbetsyta</span>
        <span className="col-span-12 mt-2 text-[15px] md:col-span-9 md:mt-0">
          {workspaceName ?? "—"}
          {isDemo ? <span className="ml-2 text-[13px] text-ochre">testarbetsyta</span> : null}
        </span>
      </div>
      <div className="grid grid-cols-12 gap-x-6 border-t border-ink/15 pt-5">
        <span className="kicker col-span-12 text-mineral md:col-span-3">Paket</span>
        <span className="col-span-12 mt-2 text-[15px] md:col-span-9 md:mt-0">
          {products.length === 0
            ? "—"
            : products.map((p) => (p === "leads" ? "Leads" : "Kundtjänst")).join(" och ")}
        </span>
      </div>
      <div className="grid grid-cols-12 gap-x-6 border-t border-ink/15 pt-5">
        <span className="kicker col-span-12 text-mineral md:col-span-3">Bolagsuppgifter</span>
        <p className="col-span-12 mt-2 max-w-[60ch] text-[15px] leading-7 text-ink/65 md:col-span-9 md:mt-0">
          Organisationsnummer och webbplats fylldes i vid uppstarten och används av båda
          agenterna.{" "}
          <Link href="/onboarding" className="underline underline-offset-4 hover:text-ochre">
            Ändra dem i uppstartsformuläret
          </Link>
          .
        </p>
      </div>
    </div>
  );
}

// Inkorgar och Plan bor numera i components/settings/. Båda var hårdkodade
// påhitt i en betalande kunds egna inställningar: två mailadresser som inte
// fanns, och ett pris (14 900 kr/mån) vi aldrig har tagit. Se docstringarna i
// respektive fil.

// TeamSettings bor numera i components/settings/TeamSettings.tsx och läser
// den faktiska arbetsytan. Den gamla versionen här var fyra hårdkodade
// strängar om roller som aldrig funnits i schemat ('Sales lead', 'Researcher',
// 'Viewer') — profiles.role har två värden: owner och member.

export function LoginView() {
  return (
    <main className="min-h-screen bg-paper text-ink">
      {/* gap-x först vid md — se kommentaren i OnboardingForm: under md är båda
          sektionerna col-span-12, och gapen ensamma är bredare än viewporten. */}
      <div className="mx-auto grid min-h-screen max-w-[1480px] grid-cols-12 px-6 py-10 md:gap-x-8 md:px-8">
        <section className="col-span-12 flex flex-col justify-between bg-ink p-8 text-paper md:col-span-6">
          <div>
            <p className="kicker text-paper/55">Snajp workspace</p>
            <h1 className="mt-8 text-[1.75rem] font-semibold leading-tight tracking-[-0.02em]">Logga in</h1>
          </div>
          <p className="mt-12 max-w-[44ch] text-[16px] leading-7 text-paper/70">Logga in med lösenord eller magic link. Efter första inloggningen konfigurerar du business context innan dashboarden öppnas.</p>
        </section>
        <section className="col-span-12 mt-8 flex items-center md:col-span-6 md:mt-0 md:pl-10">
          <LoginForm />
        </section>
      </div>
    </main>
  );
}

export function OnboardingView() {
  return (
    <main className="min-h-screen bg-paper text-ink">
      <div className="mx-auto max-w-[1480px] px-6 py-10 md:px-8">
        <div className="grid grid-cols-12 md:gap-x-8">
          <div className="col-span-12 md:col-span-3">
            <Link href="/" className="kicker text-mineral hover:text-ochre">Till startsidan</Link>
            <div className="rule mt-3 text-ink" />
            <form action={signOut} className="mt-3">
              <button type="submit" className="kicker text-mineral hover:text-ochre">Logga ut</button>
            </form>
            <p className="kicker mt-4 text-ink/45">Steg 1 av 4</p>
          </div>
          <div className="col-span-12 mt-8 md:col-span-9 md:mt-0">
            <h1 className="max-w-3xl text-[1.75rem] font-semibold leading-tight tracking-[-0.02em]">Berätta hur ni säljer</h1>
            <OnboardingForm />
          </div>
        </div>
      </div>
    </main>
  );
}

export function LoadingStatesView() {
  return (
    <PageShell kicker="States" title="Loading, empty och error states i Snajps formspråk." description="Gemensamma UI-states för vidare produktion.">
      <div className="grid grid-cols-12 gap-x-8 gap-y-8">
        <TextList title="Loading" items={["Fyra linjer i ledgern får låg kontrast och shimmer via opacity, inte spinner."]} />
        <TextList title="Empty" items={["Ingen kampanj vald. Välj en kampanj eller låt Snajp föreslå ett segment."]} />
        <TextList title="Error" items={["Provider saknas. LinkedIn enrichment kräver adapter eller användarauktoriserad input."]} />
      </div>
    </PageShell>
  );
}
