/**
 * Demons leads-kontroller — ICP, autonominivå och en godkännandekö.
 *
 * Samma skäl som `support-inbox.ts`: `/api/snajp-support/leads/*` går genom
 * `requireSnajpTenant()`, som härleder tenanten ur sessionen och medvetet
 * saknar demo-väg. En anonym besökare fick 401, och demon visade ett
 * felmeddelande i stället för produkten.
 *
 * ## Varför den här returnerar riktiga Response-objekt
 *
 * `LeadsControls` läser `response.ok` och skickar svaret vidare till
 * `readJsonBody()`. Hade demoläget returnerat råa objekt måste varje
 * anropsplats skrivas om, och de två vägarna kunde glida isär. Med ett
 * `Response` går exakt samma kod i demo som i drift — bara innehållet skiljer.
 */

type Autonomy = "draft" | "first_contact" | "meeting";

const AUTONOMY_LEVELS: { value: Autonomy; description: string }[] = [
  {
    value: "draft",
    description:
      "Agenten researchar och skriver utkast. Ingenting lämnar systemet utan att du tryckt skicka."
  },
  {
    value: "first_contact",
    description:
      "Agenten får skicka det första mejlet själv. Uppföljningar och allt därefter kräver ditt godkännande."
  },
  {
    value: "meeting",
    description:
      "Agenten får föra dialogen fram till ett bokat möte. Den bokar aldrig utan att du bekräftat tiden."
  }
];

function grundconfig() {
  return {
    autonomy: "draft" as Autonomy,
    autonomy_description: AUTONOMY_LEVELS[0].description,
    autonomy_levels: AUTONOMY_LEVELS,
    icp: {
      industries: ["Tillverkning", "Bygg", "Logistik"],
      exclude_industries: ["Bemanning", "Spel"],
      geography: ["Västra Götaland", "Skåne"],
      roles: ["VD", "Inköpschef", "Platschef"],
      must_have: ["Egen produktion", "Växer i antal anställda"],
      deal_breakers: ["Färre än 10 anställda"],
      company_size: { min: 10 as number | null, max: 250 as number | null }
    }
  };
}

function grundko() {
  return [
    {
      id: "q-1",
      prospect_email: "anna.soderberg@nordvent.se",
      subject: "Nya lokaler i Mölndal — ventilationen?",
      scheduled_at: new Date(Date.now() + 45 * 60_000).toISOString(),
      body: "Hej Anna,\n\nJag såg att Nordvent tagit över lokalerna på Aminogatan i Mölndal. Ett lokalbyte brukar betyda att ventilationsritningarna behöver ses över innan slutbesiktningen, och det är lättare att göra nu än efter inflytt.\n\nVi har gjort samma sak åt tre bolag i Mölndal det senaste året. Ska jag skicka över hur upplägget såg ut?\n\nVänliga hälsningar,\nSebastian"
    },
    {
      id: "q-2",
      prospect_email: "johan.lind@brikkonstruktion.se",
      subject: "Ni rekryterar produktionsledare",
      scheduled_at: new Date(Date.now() + 3 * 60 * 60_000).toISOString(),
      body: "Hej Johan,\n\nEr annons för produktionsledare nämner att ni ska dubbla kapaciteten i Borås. Det är oftast då planeringen blir det som sätter taket, inte maskinerna.\n\nJag skickar gärna en kort genomgång av hur två liknande verkstäder löste just den flaskhalsen. Säg till om det är intressant.\n\nVänliga hälsningar,\nSebastian"
    },
    {
      id: "q-3",
      prospect_email: "maria.ferm@stalpartner.se",
      subject: "Er nya tjänstesida om legotillverkning",
      scheduled_at: new Date(Date.now() + 26 * 60 * 60_000).toISOString(),
      body: "Hej Maria,\n\nNi lade nyligen upp en sida om legotillverkning i mindre serier. Det är ett tydligt skifte från det ni beskrev tidigare, och sådana skiften brukar komma med en period där offertflödet inte riktigt hänger med.\n\nHör av dig om du vill se hur vi brukar lösa det.\n\nVänliga hälsningar,\nSebastian"
    }
  ];
}

function svar(kropp: unknown, status = 200): Response {
  return new Response(JSON.stringify(kropp), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

/** En instans per monterad vy. Signaturen speglar `fetch(path, init)`. */
export function createDemoLeadsFetch() {
  let config = grundconfig();
  let ko = grundko();

  return async function demoFetch(path: string, init?: RequestInit): Promise<Response> {
    // Så att laddningstillstånden i UI:t hinner synas.
    await new Promise((resolve) => setTimeout(resolve, 180));

    const rutt = path.replace("/api/snajp-support", "").split("?")[0];
    const metod = init?.method ?? "GET";

    if (rutt === "/leads/config" && metod === "GET") {
      return svar(config);
    }

    if (rutt === "/leads/config" && metod === "PUT") {
      const patch = JSON.parse((init?.body as string) ?? "{}");

      // Samma spärr som i drift: en insmugglad system_prompt stryks i stället
      // för att skrivas. Demon ska visa produktens beteende, inte ett
      // förenklat som beter sig annorlunda än det kunden köper.
      const { autonomy, icp } = patch;

      if (autonomy && AUTONOMY_LEVELS.some((n) => n.value === autonomy)) {
        config = {
          ...config,
          autonomy,
          autonomy_description:
            AUTONOMY_LEVELS.find((n) => n.value === autonomy)?.description ??
            config.autonomy_description
        };
      }
      if (icp) {
        config = { ...config, icp: { ...config.icp, ...icp } };
      }
      return svar(config);
    }

    if (rutt === "/leads/queue" && metod === "GET") {
      return svar({ items: ko });
    }

    const beslut = rutt.match(/^\/leads\/queue\/(.+)\/(approve|reject)$/);
    if (beslut && metod === "POST") {
      ko = ko.filter((post) => post.id !== beslut[1]);
      return svar({ ok: true });
    }

    // Hellre ett ärligt fel än ett tyst tomt svar — en ny knapp som glömts här
    // ska synas direkt.
    return svar({ error: `Demoläget saknar ett svar för ${metod} ${rutt}.` }, 501);
  };
}
