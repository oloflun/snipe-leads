import { notFound, redirect } from "next/navigation";
import { PageShell } from "@/components/AppShell";
import { BookkeepingView } from "@/components/bookkeeping/BookkeepingView";
import { StartView } from "@/components/dashboard/StartView";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { Dashboard as SupportDashboard } from "@/components/snajp/Dashboard";
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
import { loadEmailStudioData } from "@/lib/data/emails";
import { resolveDashboardState } from "@/lib/data/dashboard";
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
  const { products } = await resolveDashboardState();
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
      return id === "kontroll" ? <LeadsControlSection /> : <LeadsView />;
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
      return <SupportSection />;
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

function SupportSection() {
  return (
    <PageShell title="Inkorg och utkast">
      <SupportDashboard />
    </PageShell>
  );
}
