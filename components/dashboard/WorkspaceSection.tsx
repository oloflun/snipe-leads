import { notFound, redirect } from "next/navigation";
import { PageShell } from "@/components/AppShell";
import { BookkeepingView } from "@/components/bookkeeping/BookkeepingView";
import { StartView } from "@/components/dashboard/StartView";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { SupportWorkspaceTabs } from "@/components/snajp/SupportWorkspaceTabs";
import {
  AgentLarandeView,
  AnalyticsView,
  AssistantView,
  CompaniesView,
  CompanyDetailView,
  ContactsView,
  InboxView,
  LeadsView
} from "@/components/WorkspaceViews";
import { LeadsControls } from "@/components/leads/LeadsControls";
import { LeadslistorView } from "@/components/leads/LeadslistorView";
import { mejlaOss } from "@/components/marketing/copy";
import { loadEmailStudioData } from "@/lib/data/emails";
import { resolveDashboardState } from "@/lib/data/dashboard";
import { addonSpec } from "@/lib/addons";
import type { ProductKey } from "@/lib/routes";

/**
 * Arbetsytans sektioner — EN dispatcher, två ytor.
 *
 * Låg tidigare direkt i `app/dashboard/[[...slug]]/page.tsx`. Den bröts ut när
 * adminytan skulle visa samma flikar: alternativet var att kopiera tio
 * `case`-grenar till en andra fil, och två dispatchrar blir förr eller senare
 * två olika produkter. Entitlement-kontrollen är dessutom EN rad här — i två
 * filer är den en rad man glömmer i den ena.
 *
 * Anroparna är tunna med flit:
 *   app/dashboard/[[...slug]]/page.tsx  — kundens arbetsyta
 *   app/admin/[...slug]/page.tsx        — samma flikar inuti adminytan
 *
 * Att den ena är en OPTIONAL catch-all och den andra inte är det är inte
 * godtycke: `[[...slug]]` matchar även föräldrapaten och kan därför inte
 * samexistera med syskonroutes, vilket /admin har (kunder, korningar,
 * handelser). `[...slug]` låter de statiska syskonen vinna.
 */

const sectionProduct: Record<string, ProductKey> = {
  leads: "leads",
  companies: "leads",
  contacts: "leads",
  emails: "leads",
  inbox: "leads",
  analytics: "leads",
  assistant: "leads",
  support: "support",
  // Bokföringen grindas på entitlement sedan den blev en riktig produkt.
  // Låg tidigare i en egen gren ovanför, kontrollerad mot isPlatformAdmin —
  // se lib/routes.ts, AppRoute.adminOnly, för vad den grenen fanns till.
  bokforing: "bookkeeping"
};

export async function WorkspaceSection({ slug = [] }: Readonly<{ slug?: string[] }>) {
  const [section, id] = slug;

  if (!section) {
    return <StartView />;
  }

  // Lärandet spänner BÅDA agenterna (supportens KB-förslag, leads insikter)
  // och kan därför inte grindas på EN produkt som raderna nedan — varje
  // inloggad arbetsyta med någon produkt har agenter som lär sig. Inloggningen
  // bär grinden, precis som för startvyn ovanför.
  if (section === "larande") {
    return <AgentLarandeView />;
  }

  const product = sectionProduct[section];
  if (!product) {
    notFound();
  }

  // Entitlement is enforced here, on the server. Hiding a nav item is a courtesy;
  // this is the actual gate.
  const { products, addons, workspaceName } = await resolveDashboardState();
  if (!products.includes(product)) {
    notFound();
  }

  switch (section) {
    case "bokforing":
      return <BookkeepingView />;
    case "leads":
      // /dashboard/leads/kontroll. Egen sektion i sectionProduct hade betytt
      // /dashboard/kontroll, vilket inte är där kontrollerna hör hemma —
      // de gäller leads och ska ligga under leads.
      if (id === "kontroll") {
        return <LeadsControlSection />;
      }
      // /dashboard/leads/listor — tillägget Leadslistor. Produktgrinden ovan
      // räcker inte: vyn kräver även tillägget "leadlists", och det avgörs
      // HÄR på servern. Utan tillägget renderas ett upsell-kort i stället —
      // ett låst tillägg som bara är osynligt säljer ingenting (lib/addons.ts).
      if (id === "listor") {
        return <LeadslistorSection harTillagg={addons.includes("leadlists")} />;
      }
      return <LeadsView />;
    case "companies":
      return id ? <CompanyDetailView id={id} /> : <CompaniesView />;
    case "contacts":
      /**
       * Kontaktens egen sida finns inte, och det är ett medvetet borttagande.
       *
       * Den renderade `findContact(id)` ur mock-data, som — precis som
       * findCompany — faller tillbaka på FÖRSTA exempelkontakten när id:t inte
       * hittas. Varje riktig kontakt visade alltså en påhittad persons
       * historik under rätt namn.
       *
       * Produkten har ingen kontaktentitet att visa: kontakten ÄR två fält på
       * prospektet, och de står redan på bolagssidan. Vi skickar dit i stället
       * för att bygga en sida vars innehåll måste hittas på. Id:t ÄR
       * prospektets — se components/leads/Kontakter.tsx, som länkar hit.
       */
      if (id) {
        redirect(`/dashboard/companies/${id}`);
      }
      return <ContactsView />;
    case "emails":
      return <EmailStudioSection />;
    case "inbox":
      return <InboxView />;
    case "analytics":
      return <AnalyticsView />;
    case "assistant":
      return <AssistantView />;
    case "support":
      return <SupportSection workspaceName={workspaceName} />;
    default:
      notFound();
  }
}

async function EmailStudioSection() {
  const data = await loadEmailStudioData();

  return (
    <PageShell
      kicker="Email studio"
      title="Skriv och skriv om"
      description="Ämnesrad, brödtext och uppföljning. Varje åtgärd visar vad den ändrade och varför."
    >
      <EmailStudioEditor data={data} />
    </PageShell>
  );
}

/**
 * Leadslistor — tilläggsgrindad, till skillnad från grannarna.
 *
 * `harTillagg` avgörs i dispatchern ovan ur samma serverlästa state som
 * produktgrinden. Utan tillägget renderas INTE en 404: sidan finns och säljer
 * sig själv med samma ruled kort som /settings/addons använder — vad kunden
 * får, varför det inte ingår, och en "Hör av dig"-CTA.
 */
function LeadslistorSection({ harTillagg }: Readonly<{ harTillagg: boolean }>) {
  const spec = addonSpec("leadlists");
  return (
    <PageShell
      kicker="Leads · listor"
      title="Färdiga leadslistor att granska och exportera"
      description="Agenten bygger listan åt er — verifierade svenska B2B-bolag med kontaktväg, källa och signal per rad. Ingenting skickas."
    >
      {harTillagg ? (
        <LeadslistorView />
      ) : (
        // Samma form som AddonSettings låsta kort: ruled rad, vad/varför,
        // mejl-CTA. Ingen gråad yta och ingen fejkad vy — den som inte har
        // tillägget ska se vad det ÄR, inte en avstängd version av det.
        <div className="min-w-0 border-t border-ink/15 py-6">
          <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
            <h4 className="min-w-0 break-words text-[17px]">{spec.name}</h4>
            <span className="kicker shrink-0 text-mineral">Tillval</span>
          </div>
          <p className="mt-3 max-w-[64ch] text-[15px] leading-7">{spec.what}</p>
          <p className="mt-2 max-w-[64ch] text-[14px] leading-6 text-mineral">{spec.why}</p>
          <a
            href={mejlaOss(`Tillägg: ${spec.name}`)}
            className="mt-4 inline-block text-[13px] underline underline-offset-4 transition hover:text-ochre"
          >
            Hör av dig om {spec.name.toLowerCase()}
          </a>
        </div>
      )}
    </PageShell>
  );
}

function LeadsControlSection() {
  return (
    <PageShell
      kicker="Leads · kontroll"
      title="Vad agenterna får göra"
      description="Hur långt de får gå, vilka bolag de ska leta efter, och vad som väntar på ditt godkännande."
    >
      <LeadsControls />
    </PageShell>
  );
}

function SupportSection({ workspaceName }: Readonly<{ workspaceName: string | null }>) {
  // Fas 5 (Testchatt, plan 2026-08-28 §6.1, bd snipe-0r9): "Kundtjänst" (den
  // interna inkorgen/utkasten) och "Testchatt" (riktig AI mot den inloggade
  // tenantens egen kunskapsbas, märkt is_test i agent_runs) bredvid varandra
  // — mönstret i components/snajp/SnajpSupportDemo.tsx, i dag oanvänd i
  // produkten men färdigt.
  return (
    <PageShell title="Inkorg och utkast">
      <SupportWorkspaceTabs workspaceName={workspaceName} />
    </PageShell>
  );
}
