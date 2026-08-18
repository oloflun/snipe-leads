import { notFound } from "next/navigation";
import { PageShell } from "@/components/AppShell";
import { Overview } from "@/components/dashboard/Overview";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { Dashboard as SupportDashboard } from "@/components/snajp/Dashboard";
import {
  AnalyticsView,
  AssistantView,
  CompaniesView,
  CompanyDetailView,
  ContactDetailView,
  ContactsView,
  InboxView,
  LeadsView
} from "@/components/WorkspaceViews";
import { LeadsControls } from "@/components/leads/LeadsControls";
import { loadEmailStudioData } from "@/lib/data/emails";
import { resolveDashboardState } from "@/lib/data/dashboard";
import type { ProductKey } from "@/lib/routes";

/**
 * One dispatcher for the whole workspace. An optional catch-all cannot coexist
 * with sibling static routes, and ten near-identical page files would be ten
 * places to forget the entitlement check.
 */
const sectionProduct: Record<string, ProductKey> = {
  leads: "leads",
  companies: "leads",
  contacts: "leads",
  emails: "leads",
  inbox: "leads",
  analytics: "leads",
  assistant: "leads",
  support: "support"
};

export default async function Page({
  params
}: Readonly<{ params: Promise<{ slug?: string[] }> }>) {
  const { slug = [] } = await params;
  const [section, id] = slug;

  if (!section) {
    return <Overview />;
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
    case "leads":
      // /dashboard/leads/kontroll. Egen sektion i sectionProduct hade betytt
      // /dashboard/kontroll, vilket inte är där kontrollerna hör hemma —
      // de gäller leads och ska ligga under leads.
      return id === "kontroll" ? <LeadsControlSection /> : <LeadsView />;
    case "companies":
      return id ? <CompanyDetailView id={id} /> : <CompaniesView />;
    case "contacts":
      return id ? <ContactDetailView id={id} /> : <ContactsView />;
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
      title="Vad agenten får göra"
      description="Hur långt den får gå, vilka bolag den ska leta efter, och vad som väntar på ditt godkännande."
    >
      <LeadsControls />
    </PageShell>
  );
}

function SupportSection() {
  return (
    <PageShell
      kicker="Kundtjänst"
      title="Inkorg och utkast"
      description="Inkommande ärenden, agentens klassificering och de svar som väntar på godkännande."
    >
      <SupportDashboard />
    </PageShell>
  );
}
