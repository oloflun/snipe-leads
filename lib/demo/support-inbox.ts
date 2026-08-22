/**
 * Demons kundtjänstinkorg — sex svenska exempelärenden med namn.
 *
 * ## Varför den här filen finns
 *
 * `app/demo/[[...slug]]/page.tsx` slår fast att ingenting under /demo får
 * sträcka sig efter en session eller databasen. Två av dess vyer gjorde ändå
 * precis det: `<SupportDashboard />` och `<LeadsControls />` anropar
 * `/api/snajp-support/*`, som går genom `requireSnajpTenant()` — och den har
 * ingen demo-väg. En anonym besökare fick därför alltid 401, och innan
 * JSON-härdningen visades felet som webbläsarens råa
 * "Unexpected end of JSON input" mitt i demon.
 *
 * Lösningen är den demoroutens egen regel redan pekar ut: SAMMA komponenter,
 * annan indata. Den här modulen är den indatan.
 *
 * ## Varför tillståndet är föränderligt
 *
 * Knapparna måste GÖRA något. En demo där "Godkänn" inte ändrar status är
 * värre än ingen demo — den ser trasig ut precis där den ska imponera.
 * Därför hålls tillståndet i en closure per monterad vy: godkänn, avvisa och
 * ta över flyttar ärendet på riktigt, och regeländringar består.
 *
 * Ingenting här lämnar webbläsaren. Inga mejl skickas, inget skrivs någonstans.
 */

export type DemoClassification = {
  category: string;
  priority: string;
  sentiment: number | null;
  confidence: number;
  escalate: boolean;
  escalation_reason?: string | null;
  reasoning?: string;
  kb_sources: { title: string; similarity: number }[];
};

export type DemoDraft = {
  id: string;
  content: string;
  status: "pending" | "approved" | "rejected" | "auto_sent";
  auto: boolean;
  confidence: number;
};

export type DemoEmail = {
  id: string;
  from_email: string;
  from_name: string | null;
  subject: string;
  body_text: string;
  received_at: string;
  status: string;
  classification: DemoClassification | null;
  draft: DemoDraft | null;
  has_image: boolean;
  attachment_count: number;
  attachments: {
    id: string;
    filename: string;
    content_type: string;
    data_url: string | null;
    is_image: boolean;
  }[];
  decisions: { event: string; detail: Record<string, unknown>; created_at: string }[];
};

type DemoRule = { category: string; label: string; mode: "auto" | "draft" | "escalate" };

/** Relativa tider gör att demon aldrig ser gammal ut. */
function minuterSedan(minuter: number): string {
  return new Date(Date.now() - minuter * 60_000).toISOString();
}

const KATEGORI_ETIKETTER: Record<string, string> = {
  teknisk_support: "Teknisk support",
  garanti: "Garanti",
  leverans: "Leverans & frakt",
  utbildning: "Utbildning & användarstöd",
  retur_reklamation: "Reklamation & retur",
  betalning: "Betalning & faktura",
  orderstatus: "Orderstatus",
  ovrigt: "Övrigt"
};

/**
 * Exempelinkorgen. Exporterad för att demons analysvy ska kunna RÄKNA ur
 * samma rader som kundtjänstvyn visar — se lib/demo/oversikt.ts. Två
 * uppsättningar exempeldata för samma demo hade glidit isär, och den som
 * upptäcker det gör det mitt i en visning.
 */
export function grundmejl(): DemoEmail[] {
  return [
    {
      id: "demo-1",
      from_email: "anna.lindqvist@mail.se",
      from_name: "Anna Lindqvist",
      subject: "Kan inte logga in",
      body_text:
        "Hej! Jag försöker logga in på mitt konto men får bara felmeddelande. Har försökt återställa lösenordet men inget mail kommer. Kan ni hjälpa mig?",
      received_at: minuterSedan(12),
      status: "awaiting_approval",
      has_image: false,
      attachment_count: 0,
      attachments: [],
      classification: {
        category: "teknisk_support",
        priority: "hög",
        sentiment: 0.35,
        confidence: 0.91,
        escalate: false,
        reasoning:
          "Inloggningsproblem med utebliven återställningslänk. Standardärende med känt svar i kunskapsbasen.",
        kb_sources: [
          { title: "Återställa lösenord när mejlet inte kommer fram", similarity: 0.82 },
          { title: "Vanliga inloggningsfel", similarity: 0.64 }
        ]
      },
      draft: {
        id: "draft-1",
        status: "pending",
        auto: false,
        confidence: 0.91,
        content:
          "Hej Anna,\n\nTack för att du hörde av dig. Att återställningsmejlet uteblir beror nästan alltid på att det hamnat i skräpposten, eller på att adressen är registrerad med en annan stavning.\n\nGör så här:\n1. Sök på \"återställ\" i din skräppost.\n2. Får du ingen träff, svara på det här mejlet så skickar jag en ny länk manuellt.\n\nJag håller ärendet öppet tills du är inne igen.\n\nVänliga hälsningar,\nKundtjänst"
      },
      decisions: [
        { event: "received", detail: {}, created_at: minuterSedan(12) },
        { event: "classified", detail: { category: "teknisk_support" }, created_at: minuterSedan(11) },
        { event: "draft_created", detail: {}, created_at: minuterSedan(11) }
      ]
    },
    {
      id: "demo-2",
      from_email: "johan.berg@mail.se",
      from_name: "Johan Berg",
      subject: "Var är mitt paket?",
      body_text:
        "Beställde för en vecka sedan och spårningen har inte uppdaterats på fyra dagar. Leveransen skulle ta 2–4 vardagar. När kommer paketet?",
      received_at: minuterSedan(38),
      status: "awaiting_approval",
      has_image: false,
      attachment_count: 0,
      attachments: [],
      classification: {
        category: "leverans",
        priority: "normal",
        sentiment: 0.4,
        confidence: 0.88,
        escalate: false,
        reasoning: "Fördröjd leverans med stillastående spårning. Kunskapsbasen täcker rutinen.",
        kb_sources: [{ title: "Försenad leverans — vad vi gör", similarity: 0.79 }]
      },
      draft: {
        id: "draft-2",
        status: "pending",
        auto: false,
        confidence: 0.88,
        content:
          "Hej Johan,\n\nTack för att du hörde av dig, och ledsen för väntan. En spårning som stått stilla i fyra dagar betyder oftast att paketet fastnat i en terminal.\n\nJag har begärt en eftersökning hos transportören. Den tar normalt 1–2 arbetsdagar, och du hör från mig så snart jag vet mer. Är paketet borta skickar vi en ny leverans utan kostnad.\n\nVänliga hälsningar,\nKundtjänst"
      },
      decisions: [
        { event: "received", detail: {}, created_at: minuterSedan(38) },
        { event: "classified", detail: { category: "leverans" }, created_at: minuterSedan(37) },
        { event: "draft_created", detail: {}, created_at: minuterSedan(37) }
      ]
    },
    {
      id: "demo-3",
      from_email: "sara.nystrom@mail.se",
      from_name: "Sara Nyström",
      subject: "Dubbeldragning på kortet",
      body_text:
        "Jag ser två dragningar på exakt samma belopp för min beställning. Har ni debiterat mig dubbelt? Vill gärna få det utrett.",
      received_at: minuterSedan(64),
      status: "escalated",
      has_image: false,
      attachment_count: 0,
      attachments: [],
      classification: {
        category: "betalning",
        priority: "hög",
        sentiment: 0.3,
        confidence: 0.72,
        escalate: true,
        escalation_reason:
          "Ärendet rör en faktisk dubbeldebitering. Agenterna får inte bekräfta eller neka en återbetalning utan att en människa kontrollerat transaktionerna.",
        reasoning: "Ekonomisk avvikelse som kräver manuell kontroll mot betalleverantören.",
        kb_sources: [{ title: "Dubbeldragning och reserverade belopp", similarity: 0.68 }]
      },
      draft: null,
      decisions: [
        { event: "received", detail: {}, created_at: minuterSedan(64) },
        { event: "classified", detail: { category: "betalning" }, created_at: minuterSedan(63) },
        {
          event: "escalated",
          detail: { reason: "Kräver manuell kontroll av transaktioner" },
          created_at: minuterSedan(63)
        }
      ]
    },
    {
      id: "demo-4",
      from_email: "erik.holm@mail.se",
      from_name: "Erik Holm",
      subject: "Trasig vara, kräver återbetalning",
      body_text:
        "Vasen kom fram i tusen bitar trots bubbelplast. Helt oacceptabelt!! Jag vill ha pengarna tillbaka omgående, annars anmäler jag er till ARN.",
      received_at: minuterSedan(95),
      status: "awaiting_approval",
      has_image: true,
      attachment_count: 1,
      attachments: [
        {
          id: "att-1",
          filename: "trasig-vas.jpg",
          content_type: "image/jpeg",
          data_url: null,
          is_image: true
        }
      ],
      classification: {
        category: "retur_reklamation",
        priority: "hög",
        sentiment: 0.12,
        confidence: 0.84,
        escalate: false,
        reasoning:
          "Transportskada med bifogad bild. Tonläget är hårt men riktas mot situationen, inte mot handläggaren — ärendet besvaras normalt.",
        kb_sources: [
          { title: "Transportskada — ersättning och rutin", similarity: 0.81 },
          { title: "Reklamationsrätt kontra garanti", similarity: 0.59 }
        ]
      },
      draft: {
        id: "draft-4",
        status: "pending",
        auto: false,
        confidence: 0.84,
        content:
          "Hej Erik,\n\nTack för bilden, och tråkigt att vasen kom fram skadad. Det ska självklart inte hända.\n\nDu har rätt till ersättning vid transportskada. Jag har registrerat reklamationen och du får välja: en ny vara skickad utan kostnad, eller full återbetalning till samma kort inom 3–5 bankdagar. Svara vilket du föredrar så ordnar jag det direkt.\n\nDu behöver inte skicka tillbaka den trasiga vasen.\n\nVänliga hälsningar,\nKundtjänst"
      },
      decisions: [
        { event: "received", detail: {}, created_at: minuterSedan(95) },
        { event: "classified", detail: { category: "retur_reklamation" }, created_at: minuterSedan(94) },
        { event: "draft_created", detail: {}, created_at: minuterSedan(94) }
      ]
    },
    {
      id: "demo-5",
      from_email: "maria.ek@mail.se",
      from_name: "Maria Ek",
      subject: "Radera mina uppgifter",
      body_text:
        "Hej, jag vill radera mitt konto och alla personuppgifter ni har om mig enligt GDPR. Hur går jag tillväga?",
      received_at: minuterSedan(140),
      status: "escalated",
      has_image: false,
      attachment_count: 0,
      attachments: [],
      classification: {
        category: "ovrigt",
        priority: "hög",
        sentiment: 0.5,
        confidence: 0.79,
        escalate: true,
        escalation_reason:
          "Begäran om radering enligt GDPR har rättslig verkan och en lagstadgad svarsfrist. Den hanteras alltid av en människa.",
        reasoning: "Registrerads rättigheter — får aldrig besvaras automatiskt.",
        kb_sources: [{ title: "GDPR — radering och registerutdrag", similarity: 0.86 }]
      },
      draft: null,
      decisions: [
        { event: "received", detail: {}, created_at: minuterSedan(140) },
        { event: "classified", detail: { category: "ovrigt" }, created_at: minuterSedan(139) },
        { event: "escalated", detail: { reason: "GDPR-begäran" }, created_at: minuterSedan(139) }
      ]
    },
    {
      id: "demo-6",
      from_email: "lars.strand@mail.se",
      from_name: "Lars Strand",
      subject: "Rabattkoden funkar inte?",
      body_text:
        "Försökte använda välkomstkoden i kassan men den gick inte igenom. Är den bara för första köpet eller vad gäller?",
      received_at: minuterSedan(210),
      status: "auto_sent",
      has_image: false,
      attachment_count: 0,
      attachments: [],
      classification: {
        category: "betalning",
        priority: "låg",
        sentiment: 0.62,
        confidence: 0.95,
        escalate: false,
        reasoning:
          "Ren informationsfråga med entydigt svar i kunskapsbasen. Konfidensen ligger över tröskeln för autosvar.",
        kb_sources: [{ title: "Villkor för välkomstkoden", similarity: 0.93 }]
      },
      draft: {
        id: "draft-6",
        status: "auto_sent",
        auto: true,
        confidence: 0.95,
        content:
          "Hej Lars,\n\nVälkomstkoden gäller endast vid ditt första köp och kan inte kombineras med andra erbjudanden. Den kräver också ett ordervärde på minst 300 kr.\n\nStämmer det inte med ditt fall skickar jag gärna en ny kod — säg bara till.\n\nVänliga hälsningar,\nKundtjänst"
      },
      decisions: [
        { event: "received", detail: {}, created_at: minuterSedan(210) },
        { event: "classified", detail: { category: "betalning" }, created_at: minuterSedan(209) },
        { event: "draft_created", detail: {}, created_at: minuterSedan(209) },
        { event: "auto_sent", detail: { confidence: 0.95 }, created_at: minuterSedan(208) }
      ]
    }
  ];
}

function grundregler(): DemoRule[] {
  return [
    { category: "teknisk_support", label: KATEGORI_ETIKETTER.teknisk_support, mode: "draft" },
    { category: "garanti", label: KATEGORI_ETIKETTER.garanti, mode: "escalate" },
    { category: "leverans", label: KATEGORI_ETIKETTER.leverans, mode: "draft" },
    { category: "utbildning", label: KATEGORI_ETIKETTER.utbildning, mode: "draft" },
    { category: "retur_reklamation", label: KATEGORI_ETIKETTER.retur_reklamation, mode: "draft" },
    { category: "betalning", label: KATEGORI_ETIKETTER.betalning, mode: "auto" },
    { category: "orderstatus", label: KATEGORI_ETIKETTER.orderstatus, mode: "auto" },
    { category: "ovrigt", label: KATEGORI_ETIKETTER.ovrigt, mode: "escalate" }
  ];
}

/**
 * En instans per monterad vy. Returnerar samma form som den riktiga
 * `api()`-helpern i Dashboard, så komponenten inte behöver veta vilken av dem
 * den pratar med.
 */
export function createDemoSupportApi() {
  let mejl = grundmejl();
  let regler = grundregler();

  /**
   * Inkorgen är FYLLD direkt. Mot en riktig backend börjar den tom tills någon
   * klickar "Hämta testmail", men en demo som möter besökaren med "Inkorgen är
   * tom" ser trasig ut precis där den ska visa produkten — och den som bara
   * scrollar förbi klickar aldrig. Knappen fungerar fortfarande och laddar om
   * exempeldatan.
   */
  let seedad = true;

  function synligaMejl(search: string): DemoEmail[] {
    const params = new URLSearchParams(search);
    const q = params.get("q")?.toLowerCase().trim();
    const status = params.get("status");
    const category = params.get("category");

    return mejl.filter((m) => {
      if (status && m.status !== status) return false;
      if (category && m.classification?.category !== category) return false;
      if (q) {
        const halm = `${m.from_email} ${m.from_name ?? ""} ${m.subject} ${m.body_text}`.toLowerCase();
        if (!halm.includes(q)) return false;
      }
      return true;
    });
  }

  function kategoriRakning(): Record<string, number> {
    const rakning: Record<string, number> = {};
    for (const kategori of Object.keys(KATEGORI_ETIKETTER)) {
      rakning[kategori] = 0;
    }
    for (const m of mejl) {
      const kategori = m.classification?.category;
      if (kategori && kategori in rakning) rakning[kategori] += 1;
    }
    return rakning;
  }

  function hitta(id: string): DemoEmail | undefined {
    return mejl.find((m) => m.id === id);
  }

  function nu(): string {
    return new Date().toISOString();
  }

  return async function demoApi<T = unknown>(path: string, init?: RequestInit): Promise<T> {
    // Liten fördröjning så att laddningstillstånden i UI:t faktiskt syns.
    await new Promise((resolve) => setTimeout(resolve, 180));

    const [rutt, search = ""] = path.split("?");
    const metod = init?.method ?? "GET";

    if (rutt === "/inbox" && metod === "GET") {
      return {
        emails: seedad ? synligaMejl(search) : [],
        category_counts: seedad ? kategoriRakning() : {}
      } as T;
    }

    if (rutt === "/rules" && metod === "GET") {
      return { rules: regler } as T;
    }

    if (rutt === "/rules" && metod === "PUT") {
      const { category, mode } = JSON.parse((init?.body as string) ?? "{}");
      regler = regler.map((r) => (r.category === category ? { ...r, mode } : r));
      return { ok: true } as T;
    }

    // Demon har ingen riktig inkorg kopplad, och säger det. Utan den här
    // grenen föll anropet igenom till "okänd väg" och Dashboard visade
    // "Synka inkorg" på en yta där det inte finns något att synka.
    if (rutt === "/inbox/mailboxes" && metod === "GET") {
      return { mailboxes: [], global_konfigurerad: false, kan_synka: false } as T;
    }

    if (rutt === "/inbox/mock" && metod === "POST") {
      // Samma kontrakt som backenden: med `category` byts BARA det facket,
      // utan byts allt. Demon måste bete sig likadant, annars beter sig
      // knapparna olika på /demo och i en riktig arbetsyta.
      const { category } = JSON.parse((init?.body as string) ?? "{}");
      const nya = grundmejl();
      if (category) {
        const behall = mejl.filter((m) => m.classification?.category !== category);
        const tillskott = nya.filter((m) => m.classification?.category === category);
        mejl = [...tillskott, ...behall];
        seedad = true;
        return { ingested: tillskott.length, processing: false, category } as T;
      }
      mejl = nya;
      seedad = true;
      return { ingested: mejl.length, processing: false, category: null } as T;
    }

    if (rutt === "/inbox/sync" && metod === "POST") {
      return {
        fetched: 0,
        processed: 0,
        connected: false,
        error: "Ingen inkorg är kopplad i demon."
      } as T;
    }

    const godkann = rutt.match(/^\/drafts\/(.+)\/approve$/);
    if (godkann && metod === "POST") {
      const { edited_content } = JSON.parse((init?.body as string) ?? "{}");
      const traff = mejl.find((m) => m.draft?.id === godkann[1]);
      if (traff?.draft) {
        traff.draft = {
          ...traff.draft,
          status: "approved",
          content: edited_content ?? traff.draft.content
        };
        traff.status = "sent";
        traff.decisions = [
          ...traff.decisions,
          {
            event: "approved_and_sent",
            detail: edited_content ? { edited: true } : {},
            created_at: nu()
          }
        ];
      }
      return { ok: true } as T;
    }

    const avvisa = rutt.match(/^\/drafts\/(.+)\/reject$/);
    if (avvisa && metod === "POST") {
      const traff = mejl.find((m) => m.draft?.id === avvisa[1]);
      if (traff?.draft) {
        traff.draft = { ...traff.draft, status: "rejected" };
        traff.status = "rejected";
        traff.decisions = [
          ...traff.decisions,
          { event: "draft_rejected", detail: {}, created_at: nu() }
        ];
      }
      return { ok: true } as T;
    }

    const overta = rutt.match(/^\/inbox\/(.+)\/takeover$/);
    if (overta && metod === "POST") {
      const traff = hitta(overta[1]);
      if (traff) {
        traff.status = "taken_over";
        traff.decisions = [
          ...traff.decisions,
          { event: "taken_over", detail: {}, created_at: nu() }
        ];
      }
      return { ok: true } as T;
    }

    const detalj = rutt.match(/^\/inbox\/(.+)$/);
    if (detalj && metod === "GET") {
      const traff = hitta(detalj[1]);
      if (!traff) {
        throw new Error("Ärendet finns inte i exempeldatan.");
      }
      return traff as T;
    }

    // Hellre ett ärligt fel än ett tyst tomt svar: en ny knapp som glömts här
    // ska synas direkt, inte se ut att fungera.
    throw new Error(`Demoläget saknar ett svar för ${metod} ${rutt}.`);
  };
}
