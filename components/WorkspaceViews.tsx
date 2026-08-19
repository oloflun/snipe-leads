"use client";

import Link from "next/link";

import { SoulEditor } from "@/components/SoulEditor";
import { PageShell, useArbetsvag } from "@/components/AppShell";
import { btnPrimary, btnSecondary } from "@/components/ui";
import { LoginForm } from "@/components/auth/LoginForm";
import { SignOutButton } from "@/components/auth/SignOutButton";
import { TeamSettings } from "@/components/settings/TeamSettings";
import { AddonSettings } from "@/components/settings/AddonSettings";
import { OnboardingForm } from "@/components/auth/OnboardingForm";
import { signOut } from "@/lib/actions/auth";
import {
  analyticsSeries,
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
import { useLocale } from "@/lib/i18n";
import { cn, formatCurrency, formatDate, formatPercent } from "@/lib/utils";

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
        {["Bolag", "Segment", "Kontakt", "Signal", "Score", "Status"].map((head, index) => (
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
              <div className="num col-span-1 text-right text-[1.0625rem] font-semibold tabular-nums">{company.score}</div>
              <div className="col-span-1 text-right"><StatusWord value={company.status} /></div>
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

/**
 * Body only, no PageShell. The combined overview mounts this next to the support
 * dashboard, and nesting two shells would nest two headers.
 */
export function DashboardBody() {
  const latest = analyticsSeries.at(-1);
  const sent = latest?.sent ?? 0;
  const replies = latest?.replies ?? 0;
  return (
    <>
      <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <LedgerMetric label="Skickade" value={String(sent)} detail="denna vecka" />
        <LedgerMetric label="Svar" value={formatPercent(replies / sent)} detail="efter suppression-filter" />
        <LedgerMetric label="Möten" value="18" detail="sex med expansionssignal" />
        <LedgerMetric label="Pipeline" value={formatCurrency(842000)} detail="exempeldata" />
      </dl>
      <section className="mt-10">
        <h3 className="mb-4 text-[0.8125rem] font-medium text-ink/45">AI rekommenderar</h3>
        <CompanyLedger rows={companies.slice(0, 4)} />
      </section>
    </>
  );
}

export function DashboardView() {
  const vag = useArbetsvag();
  return (
    <PageShell
      kicker="Arbetsyta"
      title="Veckans läge"
      description="Prioriterade bolag, svar och nästa handling."
      action={<EditorialButton href={vag("/dashboard/assistant")}>Öppna assistent</EditorialButton>}
    >
      <DashboardBody />
    </PageShell>
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

export function LeadsView() {
  const vag = useArbetsvag();
  return (
    <PageShell
      kicker="Lead discovery"
      title="Svenska bolag sorterade efter tajming, inte efter mall."
      description="Filter, sparade sökningar och AI-rekommendationer visas som ett fältblad där varje rad går att revidera."
      action={<EditorialButton href={vag("/dashboard/assistant")}>Kör discovery</EditorialButton>}
    >
      <div className="mb-12 grid grid-cols-12 gap-x-6 gap-y-4">
        {["Bygg i Malmö", "Gym i Stockholm", "Fastighet Uppsala", "SaaS med rekrytering"].map((item, index) => (
          <button key={item} type="button" className="row col-span-12 border-t border-ink/15 pt-4 text-left transition hover:text-ochre md:col-span-3">
            <span className="kicker text-mineral">Sparad sökning 0{index + 1}</span>
            <span className="ticker mt-3 block text-[1.0625rem] font-semibold tracking-[-0.01em]">{item}</span>
          </button>
        ))}
      </div>
      <CompanyLedger />
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

export function AnalyticsView() {
  return (
    <PageShell kicker="Analytics" title="Analys som läser som en resultattabell, inte en chart-demo." description="Svar, möten och utskick kopplas till vecka, segment och signaltyp.">
      <div className="divide-y divide-ink/15 border-y border-ink/15">
        {analyticsSeries.map((point) => (
          <div key={point.week} className="grid grid-cols-12 gap-x-6 py-5">
            <div className="kicker col-span-3 text-mineral">{point.week}</div>
            <div className="num col-span-3 text-[1.0625rem] font-semibold tabular-nums">{point.sent} skick</div>
            <div className="num col-span-3 text-[1.0625rem] font-semibold tabular-nums">{formatPercent(point.replies / point.sent)} svar</div>
            <div className="num col-span-3 text-right text-[1.0625rem] font-semibold tabular-nums">{point.meetings} möten</div>
            <div className="col-span-12 mt-4 h-2 bg-ink/10">
              <div className="h-2 bg-ochre" style={{ width: `${Math.min(92, (point.replies / point.sent) * 420)}%` }} />
            </div>
          </div>
        ))}
      </div>
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

export function SettingsView({ section = "general" }: Readonly<{ section?: "general" | "mailboxes" | "team" | "billing" | "soul" | "addons" }>) {
  const titles = {
    general: "Business context som alla agentmoduler använder.",
    mailboxes: "Mailboxar och skickhälsa i svensk takt.",
    team: "Teamroller och audit-logik.",
    billing: "Plan, fakturering och användning.",
    soul: "Er röst",
    addons: "Tillägg"
  };
  // Beskrivningen var tidigare EN generisk sträng för alla sektioner. På
  // röstsidan blev den både felaktig (den beskriver inte sektionen) och
  // olämplig: den räknade upp "Supabase Auth och RLS" för en KUND, som varken
  // känner igen orden eller behöver veta vår stack. Att stacken sedan byttes
  // gjorde texten dessutom osann — vilket är själva argumentet mot att skriva
  // ut infrastruktur i en kundvänd yta.
  const descriptions: Record<typeof section, string> = {
    general: "Ändrar du något här ändras allt agenten skriver, i alla moduler.",
    mailboxes: "Avsändaradresser och hur mycket som får skickas per dag.",
    team: "Vilka som har tillgång till arbetsytan, och vad de får göra.",
    billing: "Vad ni har förbrukat den här månaden, och vad nästa faktura blir.",
    soul: "Beskriv hur ni låter. Agenten skriver så i era mejl och svar.",
    addons: "Det agenten kan göra utöver det som ingår i er plan."
  };
  return (
    <PageShell kicker="Settings" title={titles[section]} description={descriptions[section]}>
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
        <nav className="kicker col-span-12 flex min-w-0 flex-wrap gap-5 text-mineral md:col-span-3 md:block md:space-y-4">
          {[
            ["/settings", "General"],
            ["/settings/soul", "Röst"],
            ["/settings/mailboxes", "Mailboxes"],
            ["/settings/team", "Team"],
            ["/settings/addons", "Tillägg"],
            ["/settings/billing", "Billing"]
          ].map(([href, label]) => <Link key={href} href={href} className="block hover:text-ochre">{label}</Link>)}
          {/* Utloggningen bor här och inte i navigationsraden: den hör till
              kontot, inte till arbetsytan, och /settings är den enda ytan som
              alltid kräver en session. */}
          <div className="mt-6 w-full border-t border-ink/15 pt-6 md:mt-8">
            <SignOutButton />
          </div>
        </nav>
        <div className="col-span-12 md:col-span-9">
          {section === "general" ? <BusinessContextSettings /> : null}
          {section === "soul" ? <SoulEditor /> : null}
          {section === "mailboxes" ? <MailboxSettings /> : null}
          {section === "team" ? <TeamSettings /> : null}
          {section === "addons" ? <AddonSettings /> : null}
          {section === "billing" ? <BillingSettings /> : null}
        </div>
      </div>
    </PageShell>
  );
}

function BusinessContextSettings() {
  const { text } = useLocale();
  return (
    <div className="grid gap-5">
      {[
        ["Produkt", text(businessContext.product)],
        ["ICP", text(businessContext.icp)],
        ["Tonalitet", text(businessContext.tone)],
        ["Erbjudande", text(businessContext.offer)],
        ["CTA", text(businessContext.cta)]
      ].map(([label, value]) => (
        <label key={label} className="grid grid-cols-12 gap-x-6 border-t border-ink/15 pt-5">
          <span className="kicker col-span-12 text-mineral md:col-span-3">{label}</span>
          <textarea className="col-span-12 mt-3 min-h-24 border border-ink/15 bg-paper2/70 p-4 text-[15px] leading-6 outline-none focus:border-ochre md:col-span-9 md:mt-0" defaultValue={value} />
        </label>
      ))}
    </div>
  );
}

function MailboxSettings() {
  return <TextList title="Mailbox health" items={["sales@snajp-demo.se · healthy · 96 skick per dag", "elin@kundbolag.se · warming · 34 skick per dag"]} />;
}

// TeamSettings bor numera i components/settings/TeamSettings.tsx och läser
// den faktiska arbetsytan. Den gamla versionen här var fyra hårdkodade
// strängar om roller som aldrig funnits i schemat ('Sales lead', 'Researcher',
// 'Viewer') — profiles.role har två värden: owner och member.

function BillingSettings() {
  return <TextList title="Billing" items={["Plan · Team · 14 900 kr/mån", "Leads · 312 av 1000 denna månad", "Seats · 4 av 8 aktiva användare"]} />;
}

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
