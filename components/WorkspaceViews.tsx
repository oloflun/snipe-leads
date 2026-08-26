"use client";

import Link from "next/link";

import { SoulEditor } from "@/components/SoulEditor";
import { Agentinstruktioner } from "@/components/admin/Agentinstruktioner";
import { PageShell, useArbetsvag } from "@/components/AppShell";
import { btnPrimary, btnSecondary } from "@/components/ui";
import { LoginForm } from "@/components/auth/LoginForm";
import { SignOutButton } from "@/components/auth/SignOutButton";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { Analys } from "@/components/dashboard/Analys";
import { AgentLarande } from "@/components/leads/AgentLarande";
import { Bolagsregister } from "@/components/leads/Bolagsregister";
import { Bolagssida } from "@/components/leads/Bolagssida";
import { Kontakter } from "@/components/leads/Kontakter";
import { Svar } from "@/components/leads/Svar";
import { Discovery } from "@/components/leads/Discovery";
import { LeadsControls } from "@/components/leads/LeadsControls";
import { Affarskontext } from "@/components/settings/Affarskontext";
import { KunskapsbasPanel } from "@/components/settings/Kunskapsbas";
import { SupportRegler } from "@/components/settings/SupportRegler";
import { SettingsNav } from "@/components/settings/SettingsNav";
import { TeamSettings } from "@/components/settings/TeamSettings";
import { AddonSettings } from "@/components/settings/AddonSettings";
import { Inkorgar } from "@/components/settings/Inkorgar";
import { NotisSettings } from "@/components/settings/NotisSettings";
import { TemaSettings } from "@/components/settings/TemaSettings";
import { PlanSettings } from "@/components/settings/PlanSettings";
import { OnboardingForm } from "@/components/auth/OnboardingForm";
import { signOut } from "@/lib/actions/auth";
// Kvar ur mock-data: BARA `workflowSteps`, som är AssistantViews stegkedja —
// en beskrivning av hur agenten arbetar, inte kunddata som utger sig för att
// vara kundens. Allt annat härifrån (companies, contacts, emailVariants,
// signals, findCompany, findContact) är borta: det renderades som kundens egna
// bolag, kontakter, mejl och svar i en betald arbetsyta.
import { workflowSteps } from "@/lib/mock-data";
import type { SettingsSectionKey } from "@/lib/routes";
import type { Tema } from "@/lib/tema";

/**
 * Assistenten — MÄRKT som exempel, eftersom den inte är kopplad än.
 *
 * Samtalet nedan är skrivet, inte kört: det finns ingen assistent-endpoint i
 * backenden att hämta det ur. Så länge det är så måste sidan SÄGA det.
 *
 * Utan märkningen är den här vyn samma fel som bolagslistan och analysvyn
 * hade — ett påhittat utfall ("37 bolag hittade") i en betald arbetsyta, som
 * ser ut som något agenten faktiskt gjort. Skillnaden mot de andra är bara att
 * det här är ett samtal och inte en tabell, och den skillnaden märker ingen
 * som skummar.
 *
 * Ta bort rutan samma dag samtalet kommer ur en körning. Inte innan.
 */
export function AssistantView() {
  return (
    <PageShell
      kicker="Assistant"
      title="Assistenten är ett reglage i arbetsflödet, inte ett chattfönster."
      description="Varje kommando landar i discovery, research, sekvens, email eller analys. Det går att följa exakt vilken signal som styrde texten."
    >
      <p className="mb-8 border-y border-ochre/40 bg-ochre/10 px-4 py-3 text-[15px] text-ink/80">
        <strong className="font-semibold">Exempel.</strong> Samtalet nedan visar hur assistenten
        är tänkt att fungera. Den är inte kopplad till din arbetsyta ännu, så ingenting här är
        körningar hos dig.
      </p>
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
        <Bolagsregister demo={demo} />
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

export function CompaniesView({ demo = false }: Readonly<{ demo?: boolean }>) {
  return (
    <PageShell
      kicker="Företag"
      title="Företagsintelligens, källor och säljvinklar i samma vy."
      description="Bolagen agenten hittat åt dig, med signalen som motiverade poängen."
    >
      <Bolagsregister demo={demo} />
    </PageShell>
  );
}

export function CompanyDetailView({ id, demo = false }: Readonly<{ id: string; demo?: boolean }>) {
  // Innehållet bor i components/leads/Bolagssida.tsx. Här låg tidigare
  // `findCompany(id)` ur mock-data, som faller tillbaka på FÖRSTA exempelbolaget
  // när id:t inte finns — varje klick på ett riktigt prospekt visade alltså
  // Byggkompaniet Syds påhittade promemoria under det riktiga bolagets namn.
  return <Bolagssida id={id} demo={demo} />;
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

export function ContactsView({ demo = false }: Readonly<{ demo?: boolean }>) {
  return (
    <PageShell
      kicker="Kontakter"
      title="Personerna bakom bolagen."
      description="Kontaktpersonen agenten hittat per bolag, och var prospektet står."
    >
      <Kontakter demo={demo} />
    </PageShell>
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

export function InboxView({ demo = false }: Readonly<{ demo?: boolean }>) {
  return (
    <PageShell
      kicker="Svar"
      title="Svaren från bolagen agenten kontaktat."
      description="Vem som svarat, vad de skrev och var prospektet står nu."
    >
      <Svar demo={demo} />
    </PageShell>
  );
}

export function AgentLarandeView() {
  return (
    <PageShell
      kicker="Lärande"
      title="Det agenterna lärt sig — och väntar på ditt ok för."
      description="Kunskapsluckor ur supportärenden och marknadsinsikter ur research. Inget skrivs in i ditt underlag utan att du godkänner det här."
    >
      <AgentLarande />
    </PageShell>
  );
}

export function SettingsView({
  section = "foretaget",
  tema = "ljust"
}: Readonly<{ section?: SettingsSectionKey; tema?: Tema }>) {
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
    notiser: "Notiser",
    tema: "Tema",
    addons: "Tillägg",
    agentinstruktioner: "Globala agentinstruktioner"
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
    notiser:
      "När vi ska mejla dig, och om vad. Gäller dig personligen — inte dina kollegor i samma arbetsyta.",
    tema: "Ljus eller mörk arbetsyta. Valet gäller den här webbläsaren och slår igenom direkt.",
    addons: "Det agenterna kan göra utöver det som ingår i er plan.",
    agentinstruktioner:
      "Reglerna varje agent läser först, för varje kund. Policy och säkerhet — ton och röst hör hemma hos kunden."
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
          {section === "notiser" ? <NotisSettings /> : null}
          {section === "tema" ? <TemaSettings initial={tema} /> : null}
          {section === "mailboxes" ? <Inkorgar /> : null}
          {section === "team" ? <TeamSettings /> : null}
          {section === "addons" ? <AddonSettings /> : null}
          {section === "billing" ? <PlanSettings /> : null}
          {/* Plattformens egen sida. Grinden står i SettingsSection, på servern —
              att posten inte renderas i menyn är inte en grind. */}
          {section === "agentinstruktioner" ? <Agentinstruktioner /> : null}
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
