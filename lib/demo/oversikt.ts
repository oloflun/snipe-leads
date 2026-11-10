import { EXEMPELBOLAG, kontaktnamn, type ExempelBolag } from "@/lib/demo/iris-exempel";
import { grundmejl } from "@/lib/demo/support-inbox";
import { isoVecka } from "@/lib/admin/statistik";
import type { Localized } from "@/lib/i18n";
import type { Handelse } from "@/lib/leads/suite";
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

function timmarSedan(timmar: number): string {
  return new Date(Date.now() - timmar * 3_600_000).toISOString();
}

/**
 * Demons leads är de sex exempelbolagen (lib/demo/iris-exempel.ts), inte
 * mock-datans bolag (Anton 2026-11-09). Mock-bolagen hade varken utkast eller
 * sparade källor, och deras signaler sålde Snajp i stället för demons
 * avsändare (Hjärtsäker AB), så lådan visade "Inget utkast ännu" och "Inga
 * källor sparade". Exempelbolagen bär källor, ett skrivet utkast och
 * Email Studios svar, så varje rad i listan går att öppna fullt ut.
 *
 * `skapad` och `skickad` är timmar bakåt. Viksund (2) och Sjöhaga (5) är
 * bolagen i listans uppspelade körning (LeadsTabell, DEMO_KORNING_IDS): de
 * dyker upp under research och blir klara medan besökaren tittar.
 * Almnäs (6) har fått sitt mejl och svarat, så att Skickat och tidslinjen
 * visar ett helt förlopp.
 */
type DemoLead = { status: "new" | "ready" | "replied"; skapad: number; skickad?: number; svar?: { timmar: number; text: string } };

const DEMO_LEADS: Record<string, DemoLead> = {
  "1": { status: "ready", skapad: 2 },
  "2": { status: "new", skapad: 0.1 },
  "3": { status: "ready", skapad: 11 },
  "4": { status: "ready", skapad: 26 },
  "5": { status: "new", skapad: 0.1 },
  "6": {
    status: "replied",
    skapad: 140,
    skickad: 116,
    // Skrivet som ett riktigt svar (samma skäl som /leads/svar nedan): kort,
    // utan artighetsfraser. En broschyrton avslöjar att datan är påhittad.
    svar: {
      timmar: 30,
      text: "Hej Anna,\n\nBra timing, vi går igenom de gemensamma utrymmena i tre av husen nu i höst. Skicka ett förslag för ett av husen att börja med, så tar jag upp det på ledningsmötet nästa vecka.\n\nJonas"
    }
  }
};

/** Bolagen listans uppspelade körning lägger till (LeadsTabell). */
export const DEMO_KORNING_IDS: readonly string[] = ["2", "5"];

/** Leadet vars svar demons Att göra pekar på ("Svar från leads"). */
export const DEMO_SVARAT_ID = "6";

/** Sista meningen i beskrivningen: det källan faktiskt säger, som belägg. */
function citat(b: ExempelBolag): string {
  return b.beskrivning.split(/(?<=\.)\s+/).pop() ?? b.beskrivning;
}

/** Ett exempelbolag som en rad ur `GET /leads/prospects`. */
function demoLeadrad(b: ExempelBolag) {
  const d: DemoLead = DEMO_LEADS[b.id] ?? { status: "ready", skapad: 1 };
  const skickat = d.skickad !== undefined ? timmarSedan(d.skickad) : null;
  return {
    id: b.id,
    company_name: b.companyName,
    contact_name: `${kontaktnamn(b)}, ${b.contactRole}`,
    contact_email: `${b.contactFirstName.toLowerCase()}@${b.website}`,
    website: b.website,
    orgnr: b.orgnr,
    anstallda: b.anstallda,
    score_total: b.score,
    status: d.status,
    origin: "manual",
    ort: b.ort,
    sni: b.bransch,
    icp_fit: b.score / 100,
    qualified: true,
    disqualifiers: [],
    // Iris-bedömningen (migration 079): nivån räknas i backenden ur utslagen.
    niva: b.score >= 80 ? "A" : "B",
    motivering: b.beskrivning,
    // Utfallsnycklarna är data (UTFALL_ETIKETT i lib/prospekt.ts), inte copy.
    score_breakdown: [
      { etikett: "Signal", utfall: "träff", motivering: b.signal, hart: false, belagg: [{ citat: citat(b), url: b.kallor[0].url }] },
      {
        etikett: "Storlek",
        utfall: "träff",
        motivering: `${b.anstallda} anställda, inom målgruppens 10 till 250.`,
        hart: true
      }
    ],
    utkast_status: skickat ? "skickat" : "vantar",
    queue_item_id: skickat ? null : b.id,
    skickat_at: skickat,
    created_at: timmarSedan(d.skapad),
    senaste_handelse_at: d.svar ? timmarSedan(d.svar.timmar) : (skickat ?? timmarSedan(d.skapad))
  };
}

/** Svaret ett exempelbolag skickat tillbaka, om det svarat. */
export function demoSvar(id: string): { text: string; at: string } | null {
  const svar = DEMO_LEADS[id]?.svar;
  return svar ? { text: svar.text, at: timmarSedan(svar.timmar) } : null;
}

/**
 * Leadets tidslinje i demon, i samma form som
 * `GET /leads/prospects/{id}/tidslinje` (nyast först). Härledd ur samma
 * rad som listan visar, så att tidslinjen och listan aldrig säger olika
 * saker. Ett bolag ur besökarens egen körning (Kör Iris) har bara hittats.
 */
export function demoTidslinje(bolag: ExempelBolag, text: (l: Localized) => string): Handelse[] {
  const d = DEMO_LEADS[bolag.id];
  const rad = d ? demoLeadrad(bolag) : null;
  const skapad = rad?.created_at ?? new Date().toISOString();
  const om = (iso: string, minuter: number) => new Date(new Date(iso).getTime() + minuter * 60_000).toISOString();
  const handelse = (typ: Handelse["typ"], nar: string, rubrik: string, brodtext: string | null): Handelse => ({
    typ,
    nar,
    rubrik,
    text: brodtext,
    id: null,
    klar: null
  });
  const lista: Handelse[] = [
    handelse("skapad", skapad, text({ sv: "Iris hittade bolaget", en: "Iris found the company" }), bolag.signal)
  ];
  if (!rad || rad.status === "new") return lista;
  lista.push(
    handelse(
      "status",
      om(skapad, 4),
      "new → ready",
      text({ sv: "Researchen klar och utkastet skrivet.", en: "Research done and the draft written." })
    )
  );
  if (rad.skickat_at) {
    lista.push(
      handelse("status", rad.skickat_at, "ready → contacted", null),
      handelse("mejl_ut", rad.skickat_at, bolag.draft.subject, text({ sv: `Till ${rad.contact_email}`, en: `To ${rad.contact_email}` }))
    );
  }
  const svar = demoSvar(bolag.id);
  if (svar) {
    lista.push(
      handelse("status", svar.at, "contacted → replied", null),
      handelse("mejl_in", svar.at, text({ sv: `Svar från ${kontaktnamn(bolag)}`, en: `Reply from ${kontaktnamn(bolag)}` }), svar.text)
    );
  }
  return lista.reverse();
}

/** Returnerar `undefined` för en väg demon inte äger — anroparen faller vidare. */
export function demoOversiktSvar(path: string): unknown | undefined {
  const [rutt] = path.split("?");

  if (rutt === "/leads/prospects") {
    // Statusvärdena är backendens (migration 010) och utkastfälten samma som
    // GET /leads/prospects bär (lib/leads/utkast.ts), så att listan visar
    // "Väntar på ditt ja" och Skickat precis som i arbetsytan.
    return { prospects: EXEMPELBOLAG.map(demoLeadrad) };
  }

  if (rutt === "/leads/profil") {
    // Samma målgrupp som demons sparade filter (lib/demo/leads-controls.ts):
    // i drift vinner det strukturerade alltid över tolkningen, och demon får
    // inte visa en profil som motsäger formuläret under den.
    return {
      profil: {
        kalla: "ai",
        egen_bransch: "Utbildning och säkerhet",
        erbjudande: "Hjärtstartare och HLR-utbildning för arbetsplatser",
        malgrupp: "Tillverkande bolag som växer, med egen produktion och 10 till 250 anställda",
        branscher: ["Tillverkning", "Bygg", "Logistik"],
        undvik_branscher: ["Bemanning", "Spel"],
        kommuner: [],
        omraden: ["Västra Götaland", "Skåne"],
        geo_prioritet: [],
        anstallda_min: 10,
        anstallda_max: 250,
        utan_webbplats: false,
        kriterier: [
          {
            id: "k1",
            text: "Egen produktion",
            krav: "maste",
            kallmening: "Kundens filter: signaler som krävs"
          },
          {
            id: "k2",
            text: "Växer i antal anställda",
            krav: "maste",
            kallmening: "Kundens filter: signaler som krävs"
          },
          {
            id: "k3",
            text: "Saknar hjärtstartare eller aktuell HLR-utbildning",
            krav: "bor",
            kallmening: "Vi vill helst nå bolag som redan köpt hjärtstartare men saknar utbildning."
          }
        ],
        uteslut: [{ text: "Färre än 10 anställda", kallmening: "Kundens filter: diskvalificerar" }],
        roller: ["VD", "Inköpschef", "Platschef"],
        ej_tolkat: [],
        otolkat: []
      }
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
    // Samma utkast som demons Att göra (IrisGranskning demoKo), så att
    // översiktens antal och kön visar samma sak. Ett skickat mejl väntar inte.
    return {
      items: EXEMPELBOLAG.filter((b) => !DEMO_LEADS[b.id]?.skickad).map((b, index) => ({
        id: b.id,
        company_name: b.companyName,
        prospect_email: `${b.contactFirstName.toLowerCase()}@${b.website}`,
        subject: b.draft.subject,
        scheduled_at: timmarSedan(5 + index)
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

  if (rutt === "/leads/svar") {
    /**
     * Exempelsvaren. Skrivna som riktiga svenska mejlsvar — korta,
     * ofullständiga meningar, ingen artighetsfras — av samma skäl som stod i
     * den gamla vyn: ett påhittat svar som låter som en broschyr avslöjar att
     * datan är påhittad mitt i en visning.
     *
     * Klassificeringsordet är borta. Det fanns aldrig i databasen, och en demo
     * som visar ett agentbeslut produkten inte fattar lovar något den inte har.
     *
     * Sedan 2026-11-09 är svaren desamma som demons leads bär (DEMO_LEADS):
     * de gamla svaren gällde mock-bolag som inte fanns i listan och handlade
     * om en annan avsändares erbjudande.
     */
    return {
      replies: EXEMPELBOLAG.flatMap((bolag) => {
        const svar = demoSvar(bolag.id);
        const rad = demoLeadrad(bolag);
        return svar
          ? [
              {
                id: `demo-svar-${bolag.id}`,
                body: svar.text,
                sent_at: svar.at,
                thread_id: `demo-trad-${bolag.id}`,
                company_name: bolag.companyName,
                contact_name: kontaktnamn(bolag),
                contact_email: rad.contact_email,
                status: rad.status
              }
            ]
          : [];
      })
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

    // Veckoetiketterna räknas bakåt från innevarande vecka. Mock-seriens
    // egna (v16–v21) låg ett halvår bak i tiden bredvid "senaste 4 veckorna".
    const nu = Date.now();
    const sista = analyticsSeries.length - 1;

    return {
      weeks: analyticsSeries.map((punkt, i) => {
        const arenden = Math.round(mejl.length * (punkt.sent / toppSkick) * 3);
        return {
          week: `v${isoVecka(new Date(nu - (sista - i) * 7 * 86_400_000))}`,
          start: null,
          sent: punkt.sent,
          replies: punkt.replies,
          leads_runs: Math.round(punkt.sent / 4),
          support_runs: arenden,
          tickets: arenden,
          escalated: Math.round(arenden * eskaleradeAndel),
          resolved: Math.round(arenden * avslutadeAndel),
          // Samma form som leadsserien: ungefär en ny lead per sex skick.
          new_leads: Math.round(punkt.sent / 6)
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
        new_leads: true,
        // Även i demon. Möten mäts inte i drift, och en demo som visar en
        // möteskolumn säljer in en funktion som inte finns.
        meetings: false
      }
    };
  }

  return undefined;
}
