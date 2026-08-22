import { grundmejl } from "@/lib/demo/support-inbox";
import { analyticsSeries, companies } from "@/lib/mock-data";

/**
 * Översiktens svar på /demo — exempeldata, ingen session, ingen databas.
 *
 * ## Varför den här filen finns
 *
 * `createDemoSupportApi` svarar på `/inbox` och `/rules`, alltså kundtjänstens
 * vägar. Leads-översikten frågar efter fem andra, och demoläget kastar
 * medvetet ett fel på en väg det inte känner — vilket är rätt beteende där, men
 * hade gjort leads-översikten på `/demo` till fem em-streck och en varningsrad.
 *
 * Talen härleds ur `lib/mock-data.ts` i stället för att skrivas som konstanter.
 * En hårdkodad "18 möten" kan inte motsägas av listan under sig; ett tal som
 * RÄKNAS ur samma rader som visas kan det. Demon ska visa hur vyn beter sig,
 * inte hur bra det gick.
 *
 * Regeln från app/demo/[[...slug]]/page.tsx gäller här: ingenting i den här
 * filen får sträcka sig efter en session eller databasen.
 */

/** Samma text som backendens `autonomy.describe("draft")`. Inte en parafras. */
const AUTONOMI_DRAFT = "Agenterna researchar och skriver. Ingenting skickas förrän du tryckt skicka.";

/**
 * Exempeldatans statusord → backendens värdemängd (migration 010).
 *
 * `recommended` och `queued` finns inte i produkten; de är kvar från
 * mock-erans vokabulär. Kartan hålls här och inte i komponenten, så att
 * översättningen sker en gång, på demons väg in.
 */
const DEMOSTATUS: Record<string, string> = {
  recommended: "ready",
  researching: "researching",
  queued: "ready",
  contacted: "contacted",
  replied: "replied"
};

function timmarSedan(timmar: number): string {
  return new Date(Date.now() - timmar * 3_600_000).toISOString();
}

/** Returnerar `undefined` för en väg demon inte äger — anroparen faller vidare. */
export function demoOversiktSvar(path: string): unknown | undefined {
  const [rutt] = path.split("?");

  if (rutt === "/leads/prospects") {
    return {
      prospects: companies.map((bolag, index) => ({
        id: bolag.id,
        company_name: bolag.name,
        contact_name: bolag.contacts[0]?.fullName ?? null,
        contact_email: bolag.contacts[0]?.email ?? null,
        website: bolag.website ?? null,
        score_total: bolag.score,
        // Exempeldatans egna statusord ("recommended", "queued") är INTE
        // backendens värdemängd. Att låta dem gå ut orenderade var precis
        // varför statuskolumnen en gång togs bort ur den kundvända tabellen —
        // och en demo som visar tillstånd produkten inte kan producera lovar
        // något den inte har. Därför översätts de hit, till migration 010:s
        // faktiska värden.
        status: DEMOSTATUS[bolag.status] ?? "new",
        // Signalen som motiverade poängen. Riktiga prospekt bär den i
        // `score_breakdown` (migration 031); exempelbolagen har den som text.
        score_breakdown: [
          {
            etikett: "Signal",
            utfall: "träff",
            motivering: bolag.latestSignal.sv,
            hart: false
          }
        ],
        origin: index % 3 === 0 ? "example" : "manual",
        ort: bolag.location,
        sni: bolag.industry,
        icp_fit: Math.min(1, bolag.score / 100),
        qualified: bolag.score >= 70,
        disqualifiers: bolag.score >= 70 ? [] : ["Utanför storleksspannet"],
        created_at: timmarSedan(index * 9 + 2)
      }))
    };
  }

  if (rutt === "/leads/runs") {
    return {
      runs: companies.slice(0, 5).map((bolag, index) => ({
        id: `demo-run-${bolag.id}`,
        agent_type: "leads",
        created_at: timmarSedan(index * 14 + 3),
        step_log: [
          { skill: "research", escalated: false, latency_ms: 2400 },
          { skill: "kvalificering", escalated: index === 2, latency_ms: 1800 },
          ...(index % 2 === 0 ? [{ skill: "utkast", escalated: false, latency_ms: 3100 }] : [])
        ]
      }))
    };
  }

  if (rutt === "/leads/queue") {
    return {
      items: companies.slice(0, 2).map((bolag) => ({
        id: `demo-ko-${bolag.id}`,
        company_name: bolag.name,
        prospect_email: bolag.contacts[0]?.email ?? null,
        subject: `Fråga om ${bolag.industry.toLowerCase()} i ${bolag.location}`,
        scheduled_at: timmarSedan(5)
      }))
    };
  }

  if (rutt === "/leads/onboarding/status") {
    // Demons arbetsyta är konfigurerad, så "Innan agenten kan börja" ska inte
    // synas här. Explicit svar i stället för att förlita sig på att demoläget
    // kastar på en okänd väg — ett tyst fel är inte ett svar.
    return { complete: true, missing: [] };
  }

  if (rutt === "/leads/config") {
    return {
      autonomy: "draft",
      autonomy_description: AUTONOMI_DRAFT,
      // Branschen ligger redan som läsbar text i exempeldatan, så kartan är tom
      // med flit: översikten faller tillbaka på råvärdet när koden saknas.
      options: { sni: [] }
    };
  }

  if (rutt === "/kb") {
    return {
      articles: [
        { title: "Leveranstider och frakt" },
        { title: "Ångerrätt och returer" },
        { title: "Garanti på maskiner" },
        { title: "Fakturafrågor" }
      ]
    };
  }

  if (rutt === "/analytics/weekly") {
    /**
     * Samma FORM som backendens svar, inklusive `coverage`.
     *
     * Möteskolumnen är borta här, och det är avsiktligt: `analyticsSeries` har
     * ett `meetings`-fält, men ingenting i drift skriver bokade möten (se
     * ANALYTICS_COVERAGE i storage/base.py). En demo som visar en kolumn
     * produkten inte kan fylla säljer in en funktion som inte finns — och den
     * frågan kommer efter köpet, inte före.
     */
    // Kundtjänstsiffrorna räknas ur exempelinkorgen — samma rader som
    // /demo/support visar — och skalas per vecka med leads-seriens form. Att
    // härleda dem i stället för att skriva konstanter är samma regel som
    // filens docstring: ett tal som räknas ur synliga rader kan motsägas av
    // dem, ett hårdkodat kan det inte.
    const mejl = grundmejl();
    const eskaleradeAndel = mejl.filter((m) => m.status === "escalated").length / mejl.length;
    const avslutadeAndel = mejl.filter((m) => m.status === "auto_sent").length / mejl.length;
    const toppSkick = Math.max(...analyticsSeries.map((p) => p.sent), 1);

    return {
      weeks: analyticsSeries.map((punkt) => {
        const arenden = Math.round(mejl.length * (punkt.sent / toppSkick) * 3);
        return {
          week: punkt.week,
          start: null,
          sent: punkt.sent,
          replies: punkt.replies,
          leads_runs: Math.round(punkt.sent / 4),
          support_runs: arenden,
          tickets: arenden,
          escalated: Math.round(arenden * eskaleradeAndel),
          resolved: Math.round(arenden * avslutadeAndel)
        };
      }),
      coverage: {
        sent: true,
        replies: true,
        leads_runs: true,
        support_runs: true,
        tickets: true,
        escalated: true,
        resolved: true,
        // Även i demon. Möten mäts inte i drift, och en demo som visar en
        // möteskolumn säljer in en funktion som inte finns.
        meetings: false
      }
    };
  }

  return undefined;
}
