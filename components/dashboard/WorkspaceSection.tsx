import { notFound, redirect } from "next/navigation";
import { PageShell } from "@/components/AppShell";
import { AgentSajtKnapp } from "@/components/AgentSajtKnapp";
import { KvittoVy } from "@/components/kvitton/KvittoVy";
import { StartView } from "@/components/dashboard/StartView";
import { SupportWorkspaceTabs } from "@/components/snajp/SupportWorkspaceTabs";
import {
  AgentLarandeView,
  AnalyticsView,
  AssistantView,
  CompaniesView,
  CompanyDetailView,
  ContactsView,
  InboxView
} from "@/components/WorkspaceViews";
import { IrisBolag } from "@/components/leads/LeadsSida";
import { AttGora } from "@/components/leads/AttGora";
import { Aktivitet } from "@/components/dashboard/Aktivitet";
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
  // Iris gamla undersidor (före Snajp Suite 2026-10-03). Grindas som Leads och
  // omdirigeras sedan i switchen nedan, så att en spärrad arbetsyta får samma
  // svar på den gamla adressen som på den nya. "emails" redirectas ovan.
  iris: "leads",
  companies: "leads",
  contacts: "leads",
  inbox: "leads",
  analytics: "leads",
  assistant: "leads",
  support: "support",
  // Kvittohanteraren (f.d. bokföringen) grindas på entitlement — produktnyckeln
  // "bookkeeping" är databasens värde och står kvar, se lib/routes.ts.
  kvitton: "bookkeeping"
};

export async function WorkspaceSection({
  slug = [],
  base = "/dashboard"
}: Readonly<{
  slug?: string[];
  /**
   * `/dashboard` för kundens yta, `/admin` inifrån adminytan — se
   * `app/admin/[...slug]/page.tsx`. Varje `redirect()` i den här filen måste
   * gå genom `base`, annars landar en admin som klickar ett gammalt Iris-
   * bokmärke på `/dashboard/iris` och studsas rakt tillbaka till `/admin` av
   * `app/dashboard/layout.tsx` — samma fälla som AppShells `useArbetsvag()`
   * finns för att undvika i vanlig navigering.
   */
  base?: string;
}>) {
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

  // Gamla adressen. Bokföringsagenten byggdes om till Kvittohanteraren
  // 2026-09-16 och fliken bytte slug — bokmärken och gamla länkar ska landa
  // rätt, inte i en 404.
  if (section === "bokforing") {
    redirect(`${base}/kvitton`);
  }

  // Aktivitet är delad: innehållet följer vilka agenter arbetsytan har (se
  // components/dashboard/Aktivitet.tsx), så inloggningen bär grinden.
  if (section === "aktivitet") {
    if (id) notFound();
    return (
      <PageShell title={{ sv: "Aktivitet", en: "Activity" }}>
        <Aktivitet />
      </PageShell>
    );
  }

  // Att göra är delad på samma sätt: kön visar bara agenter arbetsytan har.
  if (section === "att-gora") {
    if (id) notFound();
    return (
      <PageShell title={{ sv: "Att göra", en: "To do" }}>
        <AttGora />
      </PageShell>
    );
  }

  if (section === "emails") {
    redirect(`${base}/leads`);
  }

  // Iris inställningar bor i /settings sedan Snajp Suite (2026-10-03).
  const leadsInstallningar = base === "/admin" ? "/admin/installningar/leads" : "/settings/leads";

  const product = sectionProduct[section];
  if (!product) {
    notFound();
  }

  // Entitlement is enforced here, on the server. Hiding a nav item is a courtesy;
  // this is the actual gate.
  const { products, workspaceName } = await resolveDashboardState();
  if (!products.includes(product)) {
    // De tre agentytorna: menyn visar dem MÖRKLAGDA (AppShell), och klicket
    // ska landa i agentens erbjudande — inte i en 404. Grinden är densamma:
    // ingen data för agenten renderas, bara pitchen. Preview-ytorna
    // (companies, contacts …) behåller 404:an — de står inte i någon meny.
    if (section === "leads" || section === "iris" || section === "support" || section === "kvitton") {
      const { AgentLast } = await import("@/components/dashboard/AgentLast");
      return <AgentLast product={product} />;
    }
    notFound();
  }

  switch (section) {
    case "kvitton":
      // Menyklicket landar HÄR, i den inbyggda vyn. Den fristående
      // agentsajten och SSO-bron dit ("Kör Agent"-knappen) togs bort
      // 2026-09-19 — Kvittohanteraren är bara den här vyn nu.
      return <KvittoVy />;
    case "leads": {
      // Ett objekt, en sida: Pipeline, Tabell och Listor är vyer (?vy=) på
      // Leads, inte egna adresser. De två äldsta adresserna under /leads
      // (före Iris 2026-09-19) leder fortfarande rätt.
      const gammal: Record<string, string> = {
        listor: `${base}/leads?vy=listor`,
        kontroll: leadsInstallningar
      };
      if (id) {
        if (gammal[id]) redirect(gammal[id]);
        notFound();
      }
      return <IrisBolag />;
    }
    case "iris": {
      // Iris sex undersidor före Snajp Suite. Bokmärken och mejllänkar ska
      // landa på sin nya plats, inte i en 404.
      const ny: Record<string, string> = {
        "": `${base}/leads`,
        pipeline: `${base}/leads`,
        korningar: `${base}/leads?vy=korningar`,
        inkorg: `${base}/leads?vy=inkorg`,
        granskning: `${base}/leads?vy=utkast`,
        installningar: leadsInstallningar
      };
      const mal = ny[id ?? ""];
      if (!mal) notFound();
      redirect(mal);
    }
    // eslint-disable-next-line no-fallthrough -- redirect/notFound kastar, nås aldrig
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
        redirect(`${base}/companies/${id}`);
      }
      return <ContactsView />;
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

function SupportSection({ workspaceName }: Readonly<{ workspaceName: string | null }>) {
  // Fas 5 (Testchatt, plan 2026-08-28 §6.1, bd snipe-0r9): "Kundtjänst" (den
  // interna inkorgen/utkasten) och "Testchatt" (riktig AI mot den inloggade
  // tenantens egen kunskapsbas, märkt is_test i agent_runs) bredvid varandra
  // — mönstret i components/snajp/SnajpSupportDemo.tsx, i dag oanvänd i
  // produkten men färdigt.
  return (
    <PageShell title={{ sv: "Kundtjänst", en: "Customer service" }}>
      <AgentSajtKnapp agent="support" />
      <SupportWorkspaceTabs workspaceName={workspaceName} />
    </PageShell>
  );
}
