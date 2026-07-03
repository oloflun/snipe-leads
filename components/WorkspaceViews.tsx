"use client";

import Link from "next/link";
import { PageShell } from "@/components/AppShell";
import { LoginForm } from "@/components/auth/LoginForm";
import { OnboardingForm } from "@/components/auth/OnboardingForm";
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
  signals,
  workflowSteps
} from "@/lib/mock-data";
import type { Campaign, Company, Contact } from "@/lib/mock-data";
import { useLocale } from "@/lib/i18n";
import { cn, formatCurrency, formatDate, formatPercent } from "@/lib/utils";

function EditorialButton({ href, children, dark = false }: Readonly<{ href: string; children: React.ReactNode; dark?: boolean }>) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex items-center gap-3 px-5 py-3 font-mono text-[13px] uppercase tracking-[0.18em] transition-colors duration-500",
        dark ? "bg-paper text-ink hover:bg-ochre" : "bg-ink text-paper hover:bg-ochre hover:text-ink"
      )}
    >
      {children}
      <span aria-hidden>↗</span>
    </Link>
  );
}

function LedgerMetric({ label, value, detail, accent = false }: Readonly<{ label: string; value: string; detail: string; accent?: boolean }>) {
  return (
    <div className="border-t border-ink/15 pt-4">
      <dt className="kicker text-mineral">{label}</dt>
      <dd className={`num mt-3 font-display text-4xl italic-disp tighten ${accent ? "text-ochre" : ""}`}>{value}</dd>
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
            <Link key={company.id} href={`/companies/${company.id}`} className="row grid grid-cols-12 gap-x-6 py-5 transition hover:bg-ochre/5">
              <div className="ticker col-span-3">
                <p className="font-display text-2xl italic-disp tighten">{company.name}</p>
                <p className="mt-1 text-sm text-ink/55">{company.website}</p>
              </div>
              <div className="kicker col-span-2 mt-2 text-mineral">{company.industry} · {company.location}</div>
              <div className="col-span-2 mt-1">
                <p className="text-[15px]">{contact.fullName}</p>
                <p className="mt-1 text-sm text-ink/55">{contact.role}</p>
              </div>
              <div className="col-span-3 text-[15px] leading-6 text-ink/72">{text(company.latestSignal)}</div>
              <div className="num col-span-1 text-right font-display text-2xl italic-disp text-ochre">{company.score}</div>
              <div className="col-span-1 text-right"><StatusWord value={company.status} /></div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function CampaignLedger({ rows = campaigns }: Readonly<{ rows?: Campaign[] }>) {
  const { text } = useLocale();
  return (
    <div className="divide-y divide-ink/15 border-y border-ink/15">
      {rows.map((campaign) => (
        <Link key={campaign.id} href={`/campaigns/${campaign.id}`} className="row grid grid-cols-12 gap-x-6 py-6 transition hover:bg-ochre/5">
          <div className="ticker col-span-12 md:col-span-4">
            <h2 className="font-display text-3xl italic-disp tighten">{text(campaign.name)}</h2>
            <p className="mt-2 max-w-[44ch] text-[15px] leading-6 text-ink/65">{text(campaign.segment)}</p>
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

function SignalTimeline({ company }: Readonly<{ company: Company }>) {
  const { text } = useLocale();
  return (
    <div className="space-y-6">
      {company.signals.map((signal) => (
        <div key={signal.id} className="grid grid-cols-12 gap-x-6 border-t border-ink/15 pt-5">
          <div className="kicker col-span-12 text-mineral md:col-span-3">{formatDate(signal.detectedAt)}</div>
          <div className="col-span-12 mt-3 md:col-span-9 md:mt-0">
            <h3 className="font-display text-2xl italic-disp tighten">{text(signal.title)}</h3>
            <p className="mt-2 max-w-[65ch] text-[15px] leading-6 text-ink/70">{text(signal.summary)}</p>
            <p className="kicker mt-4 text-ochre">{signal.source} · {Math.round(signal.confidence * 100)} % confidence</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export function DashboardView() {
  const latest = analyticsSeries.at(-1);
  const sent = latest?.sent ?? 0;
  const replies = latest?.replies ?? 0;
  return (
    <PageShell
      kicker="Arbetsyta · vecka 21"
      title="Dagens outbound-läge, skrivet som en säljjournal."
      description="Snipra prioriterar bolag, signaler, tonläge och nästa handling utan att förvandla arbetsytan till en generisk dashboard."
      action={<EditorialButton href="/assistant">Öppna assistant</EditorialButton>}
    >
      <dl className="grid grid-cols-12 gap-x-8 gap-y-8">
        <div className="col-span-6 md:col-span-3"><LedgerMetric label="Skickade" value={String(sent)} detail="denna vecka" /></div>
        <div className="col-span-6 md:col-span-3"><LedgerMetric label="Svar" value={formatPercent(replies / sent)} detail="efter suppression-filter" accent /></div>
        <div className="col-span-6 md:col-span-3"><LedgerMetric label="Möten" value="18" detail="sex med expansionssignal" /></div>
        <div className="col-span-6 md:col-span-3"><LedgerMetric label="Pipeline" value={formatCurrency(842000)} detail="mockad attribuering" /></div>
      </dl>
      <section className="mt-16">
        <div className="grid grid-cols-12 gap-x-8">
          <div className="col-span-12 md:col-span-3">
            <div className="kicker text-mineral">AI rekommenderar</div>
            <div className="rule mt-3 text-ink" />
          </div>
          <div className="col-span-12 mt-8 md:col-span-9 md:mt-0">
            <CompanyLedger rows={companies.slice(0, 4)} />
          </div>
        </div>
      </section>
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
            ["Snipra", "37 bolag hittade. Byggkompaniet Syd är starkast: ny lokal i Hyllie, fyra platsannonser och tydlig kontaktroll."],
            ["Du", "Generera ett första mejl i mediumlängd."],
            ["Snipra", "Jag använder Hyllie-signalen, arbetsledarrekryteringen och CTA:n från business context. Tonen hålls lågmäld."]
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
                <span className="num col-span-2 font-mono text-sm text-ochre">{String(index + 1).padStart(2, "0")}</span>
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
  return (
    <PageShell
      kicker="Lead discovery"
      title="Svenska bolag sorterade efter tajming, inte efter mall."
      description="Filter, sparade sökningar och AI-rekommendationer visas som ett fältblad där varje rad går att revidera."
      action={<EditorialButton href="/assistant">Kör discovery</EditorialButton>}
    >
      <div className="mb-12 grid grid-cols-12 gap-x-6 gap-y-4">
        {["Bygg i Malmö", "Gym i Stockholm", "Fastighet Uppsala", "SaaS med rekrytering"].map((item, index) => (
          <button key={item} type="button" className="row col-span-12 border-t border-ink/15 pt-4 text-left transition hover:text-ochre md:col-span-3">
            <span className="kicker text-mineral">Sparad sökning 0{index + 1}</span>
            <span className="ticker mt-3 block font-display text-2xl italic-disp tighten">{item}</span>
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
  return (
    <PageShell
      kicker={`${company.industry} · ${company.location}`}
      title={company.name}
      description={text(company.summary)}
      action={<EditorialButton href="/emails">Generera email</EditorialButton>}
    >
      <div className="grid grid-cols-12 gap-x-8 gap-y-12">
        <dl className="col-span-12 grid grid-cols-12 gap-x-8 gap-y-8">
          <div className="col-span-6 md:col-span-3"><LedgerMetric label="Lead score" value={`${company.score}/100`} detail={text(company.latestSignal)} accent /></div>
          <div className="col-span-6 md:col-span-3"><LedgerMetric label="Storlek" value={company.size.replace(" anställda", "")} detail="anställda" /></div>
          <div className="col-span-6 md:col-span-3"><LedgerMetric label="Källor" value={String(company.sources.length)} detail="provenance-poster" /></div>
          <div className="col-span-6 md:col-span-3"><LedgerMetric label="Status" value={company.status} detail="nuvarande leadläge" /></div>
        </dl>
        <section className="col-span-12 md:col-span-7">
          <h2 className="kicker text-mineral">Signal timeline</h2>
          <div className="mt-6"><SignalTimeline company={company} /></div>
        </section>
        <aside className="col-span-12 border-y border-ink/15 py-6 md:col-span-5">
          <h2 className="font-display text-3xl italic-disp tighten text-ochre">Rekommenderad säljvinkel</h2>
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
  return (
    <Link href={`/contacts/${contact.id}`} className="row grid grid-cols-12 gap-x-6 py-5 transition hover:bg-ochre/5">
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

export function CampaignsView() {
  return (
    <PageShell kicker="Campaigns" title="Sekvenser som stannar vid svar och lär av signalen." description="Kampanjerna visas som operativa utgåvor: segment, volym, reply rate och mötesutfall.">
      <CampaignLedger />
    </PageShell>
  );
}

export function CampaignDetailView({ id }: Readonly<{ id: string }>) {
  const { text } = useLocale();
  const campaign = findCampaign(id);
  return (
    <PageShell kicker={campaign.geography} title={text(campaign.name)} description={text(campaign.segment)} action={<EditorialButton href="/emails">Öppna email studio</EditorialButton>}>
      <div className="grid grid-cols-12 gap-x-8 gap-y-10">
        <section className="col-span-12 md:col-span-7">
          <h2 className="kicker text-mineral">Sequence steps</h2>
          <div className="mt-5 divide-y divide-ink/15 border-y border-ink/15">
            {campaign.sequence.map((step) => (
              <div key={`${step.day}-${text(step.label)}`} className="grid grid-cols-12 gap-x-6 py-5">
                <div className="num col-span-2 font-display text-3xl italic-disp text-ochre">D{step.day}</div>
                <div className="col-span-10">
                  <p className="font-display text-2xl italic-disp tighten">{text(step.label)}</p>
                  <p className="mt-2 text-[15px] leading-6 text-ink/68">{text(step.goal)}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
        <aside className="col-span-12 border-y border-ink/15 py-6 md:col-span-5">
          <h2 className="kicker text-mineral">Guardrails</h2>
          <div className="mt-5 space-y-4 text-[16px] leading-7 text-ink/75">
            <p>Stop on reply är aktiverat.</p>
            <p>Skickfönster: tisdag till torsdag, 08:30 till 15:20.</p>
            <p>Suppression kontrolleras före varje queue.</p>
            <p>Ton: {text(businessContext.tone)}</p>
          </div>
        </aside>
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
          <p className="kicker text-ochre">{selected.length} · {selected.type}</p>
          <h2 className="mt-4 font-display text-4xl italic-disp tighten">{text(selected.subject)}</h2>
        </div>
        <textarea
          className="mt-6 min-h-[420px] w-full resize-y border border-ink/15 bg-paper2/70 p-6 text-[16px] leading-8 text-ink outline-none transition focus:border-ochre"
          defaultValue={text(selected.body)}
        />
        <div className="mt-5 flex flex-wrap gap-3">
          {["Make shorter", "More persuasive", "More professional", "More human", "Rewrite"].map((action) => (
            <button key={action} type="button" className="border border-ink/15 px-4 py-3 font-mono text-xs uppercase tracking-[0.16em] transition hover:border-ochre hover:text-ochre active:translate-y-px">
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
            <div className="num col-span-3 font-display text-2xl italic-disp">{point.sent} skick</div>
            <div className="num col-span-3 font-display text-2xl italic-disp text-ochre">{formatPercent(point.replies / point.sent)} svar</div>
            <div className="num col-span-3 text-right font-display text-2xl italic-disp">{point.meetings} möten</div>
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
        {[
          ["Amal Hassan", "Låter relevant. Skicka gärna exempel på IT-chefer i regionen.", "positive"],
          ["Jonas Åkerström", "Inte rätt läge just nu, men återkom efter sommaren.", "later"],
          ["Mikael Berg", "Kan du förtydliga vad ni menar med signaler?", "objection"]
        ].map(([name, body, status]) => (
          <div key={name} className="grid grid-cols-12 gap-x-6 py-5">
            <div className="font-display col-span-12 text-2xl italic-disp tighten md:col-span-3">{name}</div>
            <p className="col-span-12 mt-3 text-[16px] leading-7 text-ink/72 md:col-span-7 md:mt-0">{body}</p>
            <div className="col-span-12 mt-3 text-right md:col-span-2 md:mt-0"><StatusWord value={status} /></div>
          </div>
        ))}
      </div>
    </PageShell>
  );
}

export function SettingsView({ section = "general" }: Readonly<{ section?: "general" | "mailboxes" | "team" | "billing" }>) {
  const titles = {
    general: "Business context som alla agentmoduler använder.",
    mailboxes: "Mailboxar och skickhälsa i svensk takt.",
    team: "Teamroller och audit-logik.",
    billing: "Plan, fakturering och användning."
  };
  return (
    <PageShell kicker="Settings" title={titles[section]} description="Inställningarna är ett arbetsblad för Supabase Auth, RLS, teamroller, mailboxes och billing.">
      <div className="grid grid-cols-12 gap-x-8 gap-y-10">
        <nav className="kicker col-span-12 flex flex-wrap gap-5 text-mineral md:col-span-3 md:block md:space-y-4">
          {[
            ["/settings", "General"],
            ["/settings/mailboxes", "Mailboxes"],
            ["/settings/team", "Team"],
            ["/settings/billing", "Billing"]
          ].map(([href, label]) => <Link key={href} href={href} className="block hover:text-ochre">{label}</Link>)}
        </nav>
        <div className="col-span-12 md:col-span-9">
          {section === "general" ? <BusinessContextSettings /> : null}
          {section === "mailboxes" ? <MailboxSettings /> : null}
          {section === "team" ? <TeamSettings /> : null}
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
  return <TextList title="Mailbox health" items={["sales@snipra-demo.se · healthy · 96 skick per dag", "elin@kundbolag.se · warming · 34 skick per dag"]} />;
}

function TeamSettings() {
  return <TextList title="Teamroller" items={["Owner · full åtkomst", "Sales lead · kampanjer och inbox", "Researcher · bolag och signaler", "Viewer · läsbehörighet"]} />;
}

function BillingSettings() {
  return <TextList title="Billing" items={["Plan · Team · 14 900 kr/mån", "Leads · 312 av 1000 denna månad", "Seats · 4 av 8 aktiva användare"]} />;
}

export function LoginView() {
  return (
    <main className="min-h-screen bg-paper text-ink">
      <div className="mx-auto grid min-h-screen max-w-[1480px] grid-cols-12 gap-x-8 px-6 py-10 md:px-8">
        <section className="col-span-12 flex flex-col justify-between bg-ink p-8 text-paper md:col-span-6">
          <div>
            <p className="kicker text-paper/55">Snipra workspace</p>
            <h1 className="mt-8 break-words font-display text-[clamp(2.15rem,10vw,7rem)] leading-[0.92] tighten">Logga in till din svenska AI-SDR.</h1>
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
        <div className="grid grid-cols-12 gap-x-8">
          <div className="col-span-12 md:col-span-3">
            <Link href="/" className="kicker text-mineral hover:text-ochre">Till startsidan</Link>
            <div className="rule mt-3 text-ink" />
            <p className="kicker mt-4 text-ochre">Steg 1 av 4</p>
          </div>
          <div className="col-span-12 mt-8 md:col-span-9 md:mt-0">
            <h1 className="max-w-5xl break-words font-display text-[clamp(2.15rem,10vw,7rem)] leading-[0.9] tighten">Lär Snipra hur ni säljer innan första leadet hämtas.</h1>
            <OnboardingForm />
          </div>
        </div>
      </div>
    </main>
  );
}

export function LoadingStatesView() {
  return (
    <PageShell kicker="States" title="Loading, empty och error states i Snipras formspråk." description="Gemensamma UI-states för vidare produktion.">
      <div className="grid grid-cols-12 gap-x-8 gap-y-8">
        <TextList title="Loading" items={["Fyra linjer i ledgern får låg kontrast och shimmer via opacity, inte spinner."]} />
        <TextList title="Empty" items={["Ingen kampanj vald. Välj en kampanj eller låt Snipra föreslå ett segment."]} />
        <TextList title="Error" items={["Provider saknas. LinkedIn enrichment kräver adapter eller användarauktoriserad input."]} />
      </div>
    </PageShell>
  );
}
