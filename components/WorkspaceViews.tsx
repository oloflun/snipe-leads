"use client";

import Link from "next/link";

import { SoulEditor } from "@/components/SoulEditor";
import { Agentinstruktioner } from "@/components/admin/Agentinstruktioner";
import { PageShell, useArbetsvag } from "@/components/AppShell";
import { Badge, Rad, Radlista, btnPrimary, btnSecondary, etikett, meta, rubrikPanel } from "@/components/ui";
import { LoginForm } from "@/components/auth/LoginForm";
import { SignOutButton } from "@/components/auth/SignOutButton";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { Analys } from "@/components/dashboard/Analys";
import { AgentLarande } from "@/components/leads/AgentLarande";
import { Bolagsregister } from "@/components/leads/Bolagsregister";
import { Bolagssida } from "@/components/leads/Bolagssida";
import { Kontakter } from "@/components/leads/Kontakter";
import { Svar } from "@/components/leads/Svar";
import { LeadsControls } from "@/components/leads/LeadsControls";
import { Affarskontext } from "@/components/settings/Affarskontext";
import { KunskapsbasPanel } from "@/components/settings/Kunskapsbas";
import { SupportEskalering } from "@/components/settings/SupportEskalering";
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
import { cn } from "@/lib/utils";

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
    <PageShell title="Assistenten">
      <p className="mb-8 border-y border-ochre/40 bg-ochre/10 px-4 py-3 text-[0.9375rem] text-ink-muted">
        <strong className="font-semibold">Exempel:</strong> assistenten är inte kopplad till din
        arbetsyta ännu, och inget av det här har körts hos dig.
      </p>
      {/* gap-x först från md: se kommentaren i SettingsView om grid-cols-12 vid 320px. */}
      <div className="grid grid-cols-12 gap-x-0 gap-y-10 md:gap-x-8">
        <Radlista ariaLabel="Exempelsamtal" className="col-span-12 md:col-span-7">
          {[
            ["Du", "Hitta byggbolag i Malmö med expansions- eller rekryteringssignal."],
            ["Snajp", "37 bolag hittade. Byggkompaniet Syd är starkast: ny lokal i Hyllie, fyra platsannonser och tydlig kontaktroll."],
            ["Du", "Generera ett första mejl i mediumlängd."],
            ["Snajp", "Jag använder Hyllie-signalen, arbetsledarrekryteringen och CTA:n från business context. Tonen hålls lågmäld."]
          ].map(([speaker, message]) => (
            <Rad key={`${speaker}-${message}`}>
              <p className={etikett}>{speaker}</p>
              <p className="mt-1 text-[0.9375rem] leading-6 text-ink">{message}</p>
            </Rad>
          ))}
        </Radlista>
        <div className="col-span-12 md:col-span-5">
          <h2 className={rubrikPanel}>Arbetsflöde</h2>
          <Radlista ariaLabel="Arbetsflöde" className="mt-4">
            {workflowSteps.map((step, index) => (
              <Rad key={step} className="flex gap-4">
                <span className={cn(meta, "num w-6 shrink-0")}>{index + 1}</span>
                <span className="min-w-0 text-[0.9375rem]">{step}</span>
              </Rad>
            ))}
          </Radlista>
        </div>
      </div>
    </PageShell>
  );
}

// LeadsBody/LeadsView bodde här: Discovery (körformuläret) + Bolagsregister
// (tabellen). Ersatta 2026-09-19 av components/leads/IrisBolag.tsx, som slår
// ihop dem till EN master/detalj-sida under Iris i railen — se
// WorkspaceSection.tsx (case "iris") och app/demo/[[...slug]]/page.tsx.
// Discovery.tsx är borttagen (ingen annan anropare); Bolagsregister.tsx och
// Bolagssida.tsx lever kvar och driver den fristående, olänkade
// /dashboard/companies-förhandsvyn nedan (CompaniesView/CompanyDetailView).

export function CompaniesView({ demo = false }: Readonly<{ demo?: boolean }>) {
  return (
    <PageShell title="Företag">
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
      <h2 className={rubrikPanel}>{title}</h2>
      <div className="mt-4 divide-y divide-ink/15 border-y border-ink/15">
        {items.map((item) => (
          <p key={item} className="py-4 text-[15px] leading-6 text-ink-muted">{item}</p>
        ))}
      </div>
    </div>
  );
}

export function ContactsView({ demo = false }: Readonly<{ demo?: boolean }>) {
  return (
    <PageShell title="Kontakter">
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
    <PageShell title="Analys">
      <Analys demo={demo} />
    </PageShell>
  );
}

export function InboxView({ demo = false }: Readonly<{ demo?: boolean }>) {
  return (
    <PageShell title="Svar">
      <Svar demo={demo} />
    </PageShell>
  );
}

export function AgentLarandeView() {
  return (
    <PageShell title="Lärande">
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
    team: "Team",
    billing: "Plan och fakturering",
    // Samma ord som menyposten som leder hit (lib/routes.ts settingsGroups).
    // Fyra sidor hette något annat än länken man klickat på.
    affarskontext: "Vad ni säljer",
    kunskapsbas: "Kunskapsbas",
    leads: "Vilka bolag ni vill nå",
    regler: "När agenten får svara själv",
    soul: "Så ska agenten låta",
    notiser: "Notiser",
    tema: "Tema",
    addons: "Tillägg",
    agentinstruktioner: "Globala agentinstruktioner"
  };
  // Ingen beskrivning under rubriken. Här låg en mening per sektion, och
  // nästan alla beskrev sidan ("Vilka mejladresser agenterna läser och svarar
  // från."). De få som bar något användaren behöver för att fylla i rätt står
  // nu vid fältet de gäller, i sektionens egen komponent (F-016,
  // plans/2026-09-27-appytor-enhetlighet.md).
  return (
    <PageShell title={titles[section]}>
      {/* gap-x först från md. grid-cols-12 med gap-x-8 kräver 11 x 32px = 352px
          BARA till mellanrum: vid 320px-vyn (288px container) klampades alla
          tolv kolumner till 0px, och rutnätet blev 352px brett oavsett
          innehåll — "BILLING" hamnade utanför vyn, dolt av
          body{overflow-x:hidden} i stället för att synas som horisontell
          scroll. Uppmätt via gridTemplateColumns = "0px 0px 0px ...".
          På mobil ligger allt ändå staplat i col-span-12, så x-mellanrummet
          gjorde ingen nytta där. Samma mönster finns på tre ställen till i
          den här filen; AssistantView och LoadingStatesView rättades 2026-09-27. */}
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
        {/* order-last under md: på mobil fyllde menyn hela första skärmen på
            varje inställningssida, och inställningen man öppnat låg under den.
            Innehållet först, menyn efter. */}
        <div className="order-last col-span-12 md:order-none md:col-span-3">
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
          {section === "regler" ? (
            <>
              <SupportRegler />
              <SupportEskalering />
            </>
          ) : null}
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
  // Radformen för alla inställningar: etikett (och ev. en mening hjälp) till
  // vänster, värde eller kontroll till höger. Under sm staplas de.
  const rad = "grid gap-x-6 gap-y-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center";
  return (
    <Radlista ariaLabel="Företaget">
      <Rad className={rad}>
        <span className={rubrikPanel}>Arbetsyta</span>
        <span className="flex flex-wrap items-center gap-2 text-[0.9375rem] sm:justify-end">
          {workspaceName ?? "–"}
          {isDemo ? <Badge tone="warn">Testarbetsyta</Badge> : null}
        </span>
      </Rad>
      <Rad className={rad}>
        <span className={rubrikPanel}>Paket</span>
        <span className="text-[0.9375rem] sm:text-right">
          {products.length === 0
            ? "–"
            : // Railens namn. Den gamla tvåvägsmappningen kallade Kvitton för Kundtjänst.
              new Intl.ListFormat("sv", { type: "conjunction" }).format(
                products.map((p) => ({ leads: "Iris", support: "Kundtjänst", bookkeeping: "Kvitton" })[p])
              )}
        </span>
      </Rad>
      <Rad className={rad}>
        <span className="min-w-0">
          <span className={cn(rubrikPanel, "block")}>Organisationsnummer och webbplats</span>
          <span id="bolagsuppgifter-hjalp" className="mt-1 block max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">
            Används av båda agenterna och ändras i uppstartsformuläret.
          </span>
        </span>
        <Link
          href="/onboarding"
          aria-describedby="bolagsuppgifter-hjalp"
          className={cn(btnSecondary, "justify-self-start sm:justify-self-end")}
        >
          Ändra
        </Link>
      </Rad>
    </Radlista>
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
            {/* Etiketten i etikett-form (inte kicker); paper-muted eftersom
                grunden här är den mörka ink-ytan. */}
            <p className="text-[0.8125rem] font-medium text-paper-muted">Snajp</p>
            <h1 className="mt-8 text-[1.75rem] font-semibold leading-tight tracking-[-0.02em]">Logga in</h1>
          </div>
          <p className="mt-12 max-w-[44ch] text-[16px] leading-7 text-paper-muted">Logga in med lösenord eller magic link. Efter första inloggningen konfigurerar du business context innan dashboarden öppnas.</p>
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
            <Link href="/" className={cn(etikett, "focus-ring inline-flex min-h-11 items-center rounded-input hover:text-ink")}>
              Till startsidan
            </Link>
            <div className="rule text-ink" />
            <form action={signOut}>
              <button type="submit" className={cn(etikett, "focus-ring inline-flex min-h-11 items-center rounded-input hover:text-ink")}>
                Logga ut
              </button>
            </form>
            <p className={cn(meta, "mt-2")}>Steg 1 av 4</p>
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
    <PageShell title="Tillstånd">
      <div className="grid grid-cols-12 gap-x-0 gap-y-8 md:gap-x-8">
        <TextList title="Loading" items={["Fyra linjer i ledgern får låg kontrast och shimmer via opacity, inte spinner."]} />
        <TextList title="Empty" items={["Ingen kampanj vald. Välj en kampanj eller låt Snajp föreslå ett segment."]} />
        <TextList title="Error" items={["Provider saknas. LinkedIn enrichment kräver adapter eller användarauktoriserad input."]} />
      </div>
    </PageShell>
  );
}
