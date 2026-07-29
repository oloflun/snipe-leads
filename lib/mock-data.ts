import type { Localized } from "@/lib/i18n";

export type SignalType =
  | "expansion"
  | "hiring"
  | "website"
  | "press"
  | "location"
  | "digital"
  | "offer";

export type LeadStatus = "recommended" | "researching" | "queued" | "contacted" | "replied" | "suppressed";

export type Company = {
  id: string;
  name: string;
  industry: string;
  location: string;
  size: string;
  website: string;
  score: number;
  status: LeadStatus;
  latestSignal: Localized;
  summary: Localized;
  painPoints: Localized[];
  opportunities: Localized[];
  angle: Localized;
  recommendedCta: Localized;
  contacts: Contact[];
  signals: Signal[];
  sources: Source[];
};

export type Contact = {
  id: string;
  companyId: string;
  fullName: string;
  role: string;
  email: string;
  linkedin: string;
  status: LeadStatus;
  lastTouch: string;
};

export type Signal = {
  id: string;
  companyId: string;
  type: SignalType;
  title: Localized;
  summary: Localized;
  detectedAt: string;
  confidence: number;
  source: string;
};

export type Source = {
  label: string;
  url: string;
  observedAt: string;
};

export type Campaign = {
  id: string;
  name: Localized;
  segment: Localized;
  status: "active" | "draft" | "paused";
  geography: string;
  volume: number;
  replyRate: number;
  meetings: number;
  offer: Localized;
  cta: Localized;
  sequence: SequenceStep[];
};

export type SequenceStep = {
  day: number;
  label: Localized;
  goal: Localized;
};

export type EmailVariant = {
  id: string;
  companyId: string;
  contactId: string;
  length: "kort" | "medium" | "lång";
  type: "cold" | "followup-1" | "followup-2" | "final";
  subject: Localized;
  body: Localized;
};

export type AnalyticsPoint = {
  week: string;
  sent: number;
  replies: number;
  meetings: number;
};

export const businessContext = {
  product: {
    sv: "AI-driven outbound för svenska B2B-team",
    en: "AI-driven outbound for Swedish B2B teams"
  },
  icp: {
    sv: "Svenska tjänstebolag med 10-200 anställda som säljer till andra företag",
    en: "Swedish service companies with 10-200 employees selling to other businesses"
  },
  industries: ["bygg", "restaurang", "gym", "fastighet", "konsult", "e-handel", "industri", "SaaS", "vård", "utbildning"],
  geography: ["Stockholm", "Göteborg", "Malmö", "Uppsala", "Linköping", "Västerås"],
  tone: {
    sv: "Lågmäld, specifik och professionell svensk B2B-ton",
    en: "Calm, specific and professional Swedish B2B tone"
  },
  offer: {
    sv: "En tydlig första analys av var outbound kan ge möten inom 30 dagar",
    en: "A clear first analysis of where outbound can create meetings within 30 days"
  },
  cta: {
    sv: "Vill du att jag skickar två konkreta exempel på företag vi hade börjat med?",
    en: "Would you like me to send two concrete examples of companies we would start with?"
  }
} as const;

export const companies: Company[] = [
  {
    id: "byggkompaniet-syd",
    name: "Byggkompaniet Syd",
    industry: "bygg",
    location: "Malmö",
    size: "48 anställda",
    website: "byggkompanietsyd.se",
    score: 91,
    status: "recommended",
    latestSignal: {
      sv: "Ny projektlokal i Hyllie och fyra platsannonser för arbetsledare",
      en: "New project office in Hyllie and four job posts for site supervisors"
    },
    summary: {
      sv: "Regional byggpartner med tydlig expansion i södra Skåne och flera parallella ROT-projekt.",
      en: "Regional construction partner expanding in southern Scania with several parallel renovation projects."
    },
    painPoints: [
      { sv: "Fler projekt kräver bättre kvalificering av inkommande förfrågningar.", en: "More projects require better qualification of incoming requests." },
      { sv: "Lokala beslutsfattare behöver nås innan upphandlingarna låser sig.", en: "Local decision-makers need to be reached before tenders lock in." }
    ],
    opportunities: [
      { sv: "Outreach mot fastighetsägare i Malmö med konkret expansionssignal.", en: "Outreach to property owners in Malmö using the expansion signal." },
      { sv: "Sekvens för projektchefer som nyligen fått nya lokaler eller större hyresgäster.", en: "Sequence for project managers with new premises or larger tenants." }
    ],
    angle: {
      sv: "Koppla deras nya Hyllie-närvaro till snabbare identifiering av lokala fastighetsägare med renoveringsbehov.",
      en: "Connect their new Hyllie presence to faster identification of local property owners with renovation needs."
    },
    recommendedCta: {
      sv: "Vill du se en kort lista på Malmö-bolag där signalerna redan finns?",
      en: "Would you like to see a short list of Malmö companies where the signals already exist?"
    },
    contacts: [
      {
        id: "elin-nordin",
        companyId: "byggkompaniet-syd",
        fullName: "Elin Nordin",
        role: "Försäljningschef",
        email: "elin.nordin@example.se",
        linkedin: "company-page-reference",
        status: "recommended",
        lastTouch: "2026-05-20"
      }
    ],
    signals: [
      {
        id: "sig-hyllie",
        companyId: "byggkompaniet-syd",
        type: "expansion",
        title: { sv: "Expansion i Hyllie", en: "Expansion in Hyllie" },
        summary: {
          sv: "Bolaget nämner ny projektlokal och rekryterar arbetsledare i Malmö.",
          en: "The company mentions a new project office and is hiring site supervisors in Malmö."
        },
        detectedAt: "2026-05-18T08:30:00.000Z",
        confidence: 0.87,
        source: "Karriärsida + lokal nyhet"
      }
    ],
    sources: [
      { label: "Karriärsida", url: "https://example.se/karriar", observedAt: "2026-05-18" },
      { label: "Nyhetsnotis", url: "https://example.se/nyheter/hyllie", observedAt: "2026-05-17" }
    ]
  },
  {
    id: "atelje-maltid",
    name: "Ateljé Måltid",
    industry: "restaurang",
    location: "Göteborg",
    size: "31 anställda",
    website: "ateljemaltid.se",
    score: 84,
    status: "researching",
    latestSignal: {
      sv: "Lanserar catering mot företag och uppdaterar bokningsflöde",
      en: "Launching corporate catering and updating booking flow"
    },
    summary: {
      sv: "Göteborgsbaserad restauranggrupp som rör sig från kvällsservering mot företagsluncher och event.",
      en: "Gothenburg restaurant group moving from evening service toward corporate lunches and events."
    },
    painPoints: [
      { sv: "Nya B2B-erbjudandet behöver nå HR- och office managers utan att kännas massutskickat.", en: "The new B2B offer needs to reach HR and office managers without feeling generic." }
    ],
    opportunities: [
      { sv: "Personalisera utifrån kontorsflyttar, konferenssignaler och växande team i Göteborg.", en: "Personalize based on office moves, conference signals and growing teams in Gothenburg." }
    ],
    angle: {
      sv: "Positionera företagsluncher som ett praktiskt sätt att göra interna dagar enklare när team växer.",
      en: "Position corporate lunches as a practical way to simplify internal days as teams grow."
    },
    recommendedCta: {
      sv: "Ska jag skicka tre företag i Göteborg där tajmingen ser rimlig ut?",
      en: "Should I send three Gothenburg companies where timing looks reasonable?"
    },
    contacts: [
      {
        id: "mikael-berg",
        companyId: "atelje-maltid",
        fullName: "Mikael Berg",
        role: "Grundare",
        email: "mikael.berg@example.se",
        linkedin: "manual-input-needed",
        status: "researching",
        lastTouch: "2026-05-16"
      }
    ],
    signals: [
      {
        id: "sig-catering",
        companyId: "atelje-maltid",
        type: "offer",
        title: { sv: "Nytt B2B-erbjudande", en: "New B2B offer" },
        summary: {
          sv: "Webbplatsen har ny sida för catering och företagsevent.",
          en: "The website has a new page for catering and corporate events."
        },
        detectedAt: "2026-05-14T11:20:00.000Z",
        confidence: 0.82,
        source: "Webbplats"
      }
    ],
    sources: [{ label: "Tjänstesida", url: "https://example.se/catering", observedAt: "2026-05-14" }]
  },
  {
    id: "nordic-sweat-studios",
    name: "Nordic Sweat Studios",
    industry: "gym",
    location: "Stockholm",
    size: "76 anställda",
    website: "nordicsweat.se",
    score: 88,
    status: "queued",
    latestSignal: {
      sv: "Öppnar tredje studio och söker platschef till Vasastan",
      en: "Opening third studio and hiring a studio manager in Vasastan"
    },
    summary: {
      sv: "Boutique-gymkedja med tydlig expansion i innerstan och medlemskap riktat mot yrkesverksamma.",
      en: "Boutique gym chain expanding in central Stockholm with memberships for professionals."
    },
    painPoints: [
      { sv: "Expansionen skapar behov av lokal B2B-räckvidd mot arbetsgivare och kontorskluster.", en: "Expansion creates need for local B2B reach toward employers and office clusters." }
    ],
    opportunities: [
      { sv: "Kampanj mot People/HR-roller i bolag nära den nya studion.", en: "Campaign to People/HR roles at companies near the new studio." }
    ],
    angle: {
      sv: "Använd ny studio i Vasastan som konkret öppning för arbetsplatsnära friskvård.",
      en: "Use the new Vasastan studio as a concrete opener for workplace wellness."
    },
    recommendedCta: {
      sv: "Vill du ha en första lista på HR-kontakter inom tio minuter från studion?",
      en: "Would you like a first list of HR contacts within ten minutes of the studio?"
    },
    contacts: [
      {
        id: "sara-wiklund",
        companyId: "nordic-sweat-studios",
        fullName: "Sara Wiklund",
        role: "Marknadschef",
        email: "sara.wiklund@example.se",
        linkedin: "company-page-reference",
        status: "queued",
        lastTouch: "2026-05-21"
      }
    ],
    signals: [
      {
        id: "sig-vasastan",
        companyId: "nordic-sweat-studios",
        type: "location",
        title: { sv: "Ny studio i Vasastan", en: "New studio in Vasastan" },
        summary: {
          sv: "Ny adress publicerad och platschef-roll annonserad.",
          en: "New address published and studio manager role advertised."
        },
        detectedAt: "2026-05-21T09:10:00.000Z",
        confidence: 0.9,
        source: "Google Business + karriärsida"
      }
    ],
    sources: [{ label: "Google Business", url: "https://example.se/place", observedAt: "2026-05-21" }]
  },
  {
    id: "klaravik-fastighet",
    name: "Klaravik Fastighet",
    industry: "fastighet",
    location: "Uppsala",
    size: "112 anställda",
    website: "klaravikfastighet.se",
    score: 79,
    status: "contacted",
    latestSignal: {
      sv: "Nya kommersiella lokaler och uppdaterad uthyrningssida",
      en: "New commercial premises and updated leasing page"
    },
    summary: {
      sv: "Fastighetsbolag med blandad portfölj och växande kommersiell uthyrning i Uppsala.",
      en: "Property company with mixed portfolio and growing commercial leasing in Uppsala."
    },
    painPoints: [
      { sv: "Många objekt kräver kontinuerlig dialog med rätt hyresgäster.", en: "Many properties require ongoing dialogue with the right tenants." }
    ],
    opportunities: [
      { sv: "Identifiera bolag med flytt- och expansionssignaler i regionen.", en: "Identify companies with move and expansion signals in the region." }
    ],
    angle: {
      sv: "Visa hur signalbaserad prospektering kan minska vakanstid utan breda massutskick.",
      en: "Show how signal-based prospecting can reduce vacancy time without broad blasts."
    },
    recommendedCta: {
      sv: "Vill du se hur vi hade prioriterat era tre senaste objekt?",
      en: "Would you like to see how we would prioritize your three latest properties?"
    },
    contacts: [
      {
        id: "jonas-akerstrom",
        companyId: "klaravik-fastighet",
        fullName: "Jonas Åkerström",
        role: "Operations",
        email: "jonas.akerstrom@example.se",
        linkedin: "external-provider",
        status: "contacted",
        lastTouch: "2026-05-19"
      }
    ],
    signals: [
      {
        id: "sig-uthyrning",
        companyId: "klaravik-fastighet",
        type: "website",
        title: { sv: "Uppdaterad uthyrningssida", en: "Updated leasing page" },
        summary: {
          sv: "Flera objekt markerades som nyligen tillagda.",
          en: "Several properties were marked as recently added."
        },
        detectedAt: "2026-05-12T12:00:00.000Z",
        confidence: 0.74,
        source: "Webbplats"
      }
    ],
    sources: [{ label: "Objektsida", url: "https://example.se/lokaler", observedAt: "2026-05-12" }]
  },
  {
    id: "sodra-dataateljen",
    name: "Södra Dataateljén",
    industry: "konsult",
    location: "Linköping",
    size: "24 anställda",
    website: "sodradata.se",
    score: 73,
    status: "replied",
    latestSignal: {
      sv: "Nytt partnerskap inom cybersäkerhet",
      en: "New cybersecurity partnership"
    },
    summary: {
      sv: "Teknikkonsult som växer inom säkerhet, drift och modern arbetsplats för medelstora bolag.",
      en: "Technology consultancy growing in security, operations and modern workplace for mid-market companies."
    },
    painPoints: [
      { sv: "Behöver nå IT-chefer i rätt läge snarare än generiska branschlistor.", en: "Needs to reach IT leaders at the right moment instead of generic industry lists." }
    ],
    opportunities: [
      { sv: "Signaldrivna öppningsrader kring säkerhetsprojekt och nyanställningar.", en: "Signal-driven openers around security projects and hiring." }
    ],
    angle: {
      sv: "Bygg outreach runt deras nya säkerhetspartner och lokala medelstora bolag med regulatoriska krav.",
      en: "Build outreach around their new security partner and local mid-sized companies with regulatory needs."
    },
    recommendedCta: {
      sv: "Ska jag ta fram en provsekvens mot IT-chefer i Östergötland?",
      en: "Should I draft a sample sequence for IT leaders in Östergötland?"
    },
    contacts: [
      {
        id: "amal-hassan",
        companyId: "sodra-dataateljen",
        fullName: "Amal Hassan",
        role: "VD",
        email: "amal.hassan@example.se",
        linkedin: "user-authorized-input",
        status: "replied",
        lastTouch: "2026-05-17"
      }
    ],
    signals: [
      {
        id: "sig-partner",
        companyId: "sodra-dataateljen",
        type: "press",
        title: { sv: "Nytt säkerhetspartnerskap", en: "New security partnership" },
        summary: {
          sv: "Pressnotis beskriver nytt erbjudande för medelstora bolag.",
          en: "Press note describes a new offer for mid-sized companies."
        },
        detectedAt: "2026-05-10T10:10:00.000Z",
        confidence: 0.78,
        source: "Pressrum"
      }
    ],
    sources: [{ label: "Pressrum", url: "https://example.se/press", observedAt: "2026-05-10" }]
  }
];

export const contacts = companies.flatMap((company) => company.contacts);
export const signals = companies.flatMap((company) => company.signals);

export const campaigns: Campaign[] = [
  {
    id: "lokal-expansion-syd",
    name: { sv: "Lokal expansion Syd", en: "Local expansion South" },
    segment: { sv: "Bygg, fastighet och konsultbolag med expansionssignal", en: "Construction, property and consulting companies with expansion signals" },
    status: "active",
    geography: "Skåne + Göteborg",
    volume: 312,
    replyRate: 0.172,
    meetings: 18,
    offer: businessContext.offer,
    cta: businessContext.cta,
    sequence: [
      { day: 0, label: { sv: "Första kontakt", en: "First touch" }, goal: { sv: "Visa relevant signal och föreslå två exempel.", en: "Show relevant signal and suggest two examples." } },
      { day: 4, label: { sv: "Uppföljning", en: "Follow-up" }, goal: { sv: "Knyta tillbaka till timing utan press.", en: "Return to timing without pressure." } },
      { day: 11, label: { sv: "Sista försök", en: "Final attempt" }, goal: { sv: "Ge enkel utväg och behåll relationen.", en: "Give an easy out and keep the relationship." } }
    ]
  },
  {
    id: "hr-friskvard-stockholm",
    name: { sv: "HR och friskvård Stockholm", en: "HR and wellness Stockholm" },
    segment: { sv: "HR-roller nära nya träningsstudios", en: "HR roles near new fitness studios" },
    status: "draft",
    geography: "Stockholm",
    volume: 145,
    replyRate: 0.093,
    meetings: 4,
    offer: { sv: "Pilot med 30 lokala arbetsgivare kring den nya studion", en: "Pilot with 30 local employers around the new studio" },
    cta: { sv: "Vill du se vilka arbetsgivare vi hade prioriterat först?", en: "Would you like to see which employers we would prioritize first?" },
    sequence: [
      { day: 0, label: { sv: "Signalbaserad öppning", en: "Signal-based opener" }, goal: { sv: "Koppla ny lokal till arbetsplatsnära friskvård.", en: "Connect new location to workplace wellness." } },
      { day: 5, label: { sv: "Exempel", en: "Example" }, goal: { sv: "Skicka tre hypotetiska konton.", en: "Send three hypothetical accounts." } }
    ]
  }
];

export const emailVariants: EmailVariant[] = [
  {
    id: "email-byggkompaniet-cold",
    companyId: "byggkompaniet-syd",
    contactId: "elin-nordin",
    length: "medium",
    type: "cold",
    subject: {
      sv: "Hyllie-expansionen och fler lokala byggdialoger",
      en: "The Hyllie expansion and more local construction conversations"
    },
    body: {
      sv: "Hej Elin,\n\nJag såg att Byggkompaniet Syd verkar växla upp i Hyllie samtidigt som ni söker fler arbetsledare i Malmö. Det brukar vara ett läge där rätt lokala fastighetsägare är värda mer än en bred lista med generiska leads.\n\nSnajp hjälper svenska B2B-team att hitta företag med konkreta signaler, analysera varför tajmingen är relevant och skriva lågmälda, personliga mejl som en svensk säljare faktiskt hade skickat.\n\nVill du att jag skickar två exempel på Malmö-bolag där signalerna redan pekar mot renovering eller lokalförändring?",
      en: "Hi Elin,\n\nI noticed that Byggkompaniet Syd seems to be scaling up in Hyllie while hiring more site supervisors in Malmö. That is often a point where the right local property owners are worth more than a broad list of generic leads.\n\nSnajp helps Swedish B2B teams find companies with concrete signals, analyze why timing is relevant and write calm, personal emails a Swedish salesperson would actually send.\n\nWould you like me to send two examples of Malmö companies where the signals already point toward renovation or property changes?"
    }
  },
  {
    id: "email-sweat-followup",
    companyId: "nordic-sweat-studios",
    contactId: "sara-wiklund",
    length: "kort",
    type: "followup-1",
    subject: {
      sv: "Kort följdfråga om Vasastan",
      en: "Quick follow-up on Vasastan"
    },
    body: {
      sv: "Hej Sara,\n\nKort följdfråga: vill du se hur vi hade hittat HR-kontakter inom gångavstånd från den nya studion i Vasastan?\n\nDet handlar inte om en stor kampanj, mer en första signalbaserad lista med rimliga öppningar.",
      en: "Hi Sara,\n\nQuick follow-up: would you like to see how we would find HR contacts within walking distance of the new Vasastan studio?\n\nNot a large campaign, more a first signal-based list with reasonable openers."
    }
  }
];

export const analyticsSeries: AnalyticsPoint[] = [
  { week: "v16", sent: 188, replies: 21, meetings: 6 },
  { week: "v17", sent: 244, replies: 34, meetings: 9 },
  { week: "v18", sent: 231, replies: 29, meetings: 8 },
  { week: "v19", sent: 276, replies: 43, meetings: 13 },
  { week: "v20", sent: 318, replies: 51, meetings: 18 },
  { week: "v21", sent: 297, replies: 49, meetings: 16 }
];

export const workflowSteps = [
  "Fetch leads",
  "Enrich company",
  "Detect signals",
  "Analyze company",
  "Score relevance",
  "Generate outreach angle",
  "Generate email variants",
  "Queue sending",
  "Watch replies/events",
  "Plan follow-up",
  "Update CRM/analytics"
] as const;

export const agents = [
  "Discovery Agent",
  "Company Research Agent",
  "Signal Detection Agent",
  "Contact Prioritization Agent",
  "Personalization Agent",
  "Email Generation Agent",
  "Follow-Up Planner",
  "Reply Classifier",
  "Analytics Insight Agent"
] as const;

export function findCompany(id: string) {
  return companies.find((company) => company.id === id) ?? companies[0];
}

export function findContact(id: string) {
  return contacts.find((contact) => contact.id === id) ?? contacts[0];
}

export function findCampaign(id: string) {
  return campaigns.find((campaign) => campaign.id === id) ?? campaigns[0];
}
