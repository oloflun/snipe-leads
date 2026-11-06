/**
 * De sex exempelbolagen på /demo (Discovery/ExempelbolagDemo) OCH deras
 * handskrivna Email Studio-utkast och åtgärdsresultat — EN källa för båda.
 *
 * ## Bakgrunden till varför den här filen finns
 *
 * Uppmätt 2026-09-18: `simulateAction()` i app/api/email-studio/route.ts
 * byggde VARJE knappsvar ur strängmallar. `signal` föll tillbaka på
 * "det som händer hos er just nu" eftersom demoanropet aldrig skickade den,
 * `contact_name` var en ROLL ("Inköpschef") som gick rakt in som hälsning
 * ("Hej Inköpschef,"), och alla tre BOLAG-bolagen delade exakt samma
 * `pitch_varfor_nu` ("en ny lokal ska utrustas från grunden…") oavsett vad
 * deras egen `beskrivning` faktiskt sa. Resultatet: mallspråk, fel hälsning,
 * och en signal som inte hörde ihop med bolaget.
 *
 * Lösningen är INTE en bättre mall — det är att sluta generera. De sex
 * bolagen är påhittade i alla lägen (se domänerna, `.example`, och de
 * medvetet fel kontrollsiffrorna i orgnumren), så det finns inget skäl att
 * en algoritm ska hitta på deras mejl också. Varje bolag har en egen,
 * skriven signal som matchar dess `beskrivning`, en konkret hälsning på
 * kontaktens FÖRNAMN (aldrig rollen), och ett handskrivet svar för VARJE
 * knapp i EmailStudioEditor (STUDIO_ACTIONS): Kortare, Skriv om, Förbättra,
 * Personalisera, Översätt, A/B-varianter, Uppföljning, Analysera.
 *
 * ## Avsändaren
 *
 * Samma säljare i alla sex bolag: Anna på Hjärtsäker AB (hjärtstartare +
 * HLR-utbildning till arbetsplatser) — redan etablerad i det gamla `PITCH()`-
 * mönstret i den här filens föregångare och i snajp-support/app/leads/
 * exempelbolag.py. Att byta säljare hade löst ingenting och bara gjort två
 * demos (den här och backendens) inkonsekventa med varandra.
 *
 * ## Hur ett svar hittas
 *
 * app/api/email-studio/route.ts matchar den inloggningsfria (anonyma)
 * förfrågan mot ETT av de sex bolagen via `finnExempelbolag()` — i första
 * hand på `companyId` (bolagets `id`, skickat som `context.companyId` från
 * EmailStudioEditor/lib/data/emails.ts `toRefineContext`), annars på
 * bolagsnamnet. Matchar inget bolag (t.ex. det fristående exempelmejlet på
 * marknadssidan, `lib/data/emails.ts` `PUBLIKT_EXEMPELMEJL`) svarar routen med
 * en ärlig mening om att demot bara har färdiga svar till de här sex
 * bolagen — den TEXT användaren själv skrivit i fältet spelar ingen roll,
 * för svaret är alltid det handskrivna, aldrig en omskrivning av inmatningen.
 */

// Relativ import med flit, inte "@/..." — samma skäl som
// lib/llm/kvotfel.ts: filen körs direkt av `node --test` utan bundler
// (lib/demo/iris-exempel.test.ts), och alias-uppslagningen finns bara i
// Next.js/TypeScript-bygget, inte i node:s egna modulupplösning.
import { halsning } from "../agent/halsning.ts";
import type { Struktur } from "../leads/struktur.ts";

export const IRIS_AVSANDARE = {
  fornamn: "Anna",
  bolag: "Hjärtsäker AB",
  produkt: "hjärtstartare och HLR-utbildning till arbetsplatser"
} as const;

/** Åtgärderna EmailStudioEditor visar som knappar (STUDIO_ACTIONS). */
export type ExempelAction =
  | "shorter"
  | "rewrite"
  | "improve"
  | "personalize"
  | "translate"
  | "ab_variants"
  | "followup"
  | "analyze";

export const EXEMPEL_ACTIONS: ExempelAction[] = [
  "shorter",
  "rewrite",
  "improve",
  "personalize",
  "translate",
  "ab_variants",
  "followup",
  "analyze"
];

/** Åtgärder som skriver om SAMMA mejl — de får en "Ursprunglig version" att visas mot. */
export const DIREKT_OMSKRIVNING: ReadonlySet<ExempelAction> = new Set([
  "shorter",
  "rewrite",
  "improve",
  "personalize",
  "translate"
]);

/** Samma form som API:t svarar med (se RichApiPayload i EmailStudioEditor.tsx). */
export type ExempelActionResultat = {
  new_version: string;
  explanation: string;
  subject_suggestions: string[];
  confidence_tips?: string;
};

export type Utkast = { subject: string; body: string };

export type ExempelBolag = {
  id: string;
  companyName: string;
  orgnr: string;
  ort: string;
  website: string;
  anstallda: number;
  bransch: string;
  beskrivning: string;
  contactFirstName: string;
  contactLastName: string;
  contactRole: string;
  /** Trigger-händelsen — samma fakta som `beskrivning`, skriven som en hel mening. */
  signal: string;
  /** Det konkreta erbjudandet, kopplat till just den här signalen. */
  offer: string;
  /** Uppmaningen utkastet slutar med. */
  cta: string;
  /** Träffsäkerhet mot målgruppen, 0-100 — samma fält som Score i detaljpanelen. */
  score: number;
  /** Samma statusvärden som riktiga prospekt (STATUS_ETIKETT i components/leads/IrisBolag.tsx). */
  status: string;
  /** Källorna research bygger på. Alltid minst en, annars får Iris inte skriva utkastet (GRANSER i lib/iris.ts). */
  kallor: { label: string; url: string }[];
  /**
   * Utkastets struktur som standard (Sebbe 2026-11-07): de flesta exempelbolagen
   * visar B, kort och rakt på, några A. `utkast` bär båda formerna så att demons
   * Kör Iris kan visa den struktur besökaren valde (`medStruktur`).
   */
  struktur: Struktur;
  utkast: Record<Struktur, Utkast>;
  /** Standardstrukturens utkast, samma objekt som `utkast[struktur]`. */
  draft: Utkast;
  /** Åtgärdsresultaten är skrivna i standardstrukturens form. */
  resultat: Record<ExempelAction, ExempelActionResultat>;
};

/** Kontaktens fulla namn, som skickas som `contactName` — `halsning()` plockar ut förnamnet. */
export function kontaktnamn(bolag: Pick<ExempelBolag, "contactFirstName" | "contactLastName">): string {
  return `${bolag.contactFirstName} ${bolag.contactLastName}`;
}

// ---------------------------------------------------------------------------
// Omgång 1 — de tre bolagen som visas först.
// ---------------------------------------------------------------------------

const LUNDSUND_A: Utkast = {
  subject: "Ny inköpschef hos Lundsund",
  body:
      "Hej Karin,\n\n" +
      "Grattis till rollen som inköpschef. Jag såg att tjänsten stått öppen sedan i våras, så ni har säkert en hel del att komma igång med.\n\n" +
      "En sak som ofta hamnar sist på en sådan lista är hjärtstartare och HLR för teamet, trots att någon snart brukar fråga efter det. Vi monterar en hjärtstartare i lokalen och håller en kort HLR-genomgång för hela teamet, bokad innan sommaren.\n\n" +
      "Vill du att jag skickar ett förslag anpassat efter er lokal?\n\n" +
      "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
};

const LUNDSUND_B: Utkast = {
  subject: "Hjärtstartare på listan?",
  body:
        "Hej Karin,\n\n" +
        "Grattis till rollen som inköpschef.\n\n" +
        "Om vi monterade en hjärtstartare i er lokal och höll en HLR-genomgång för hela teamet innan sommaren, utan att det tar mer än en förmiddag av er tid, skulle det vara till nytta?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB"
};

const LUNDSUND: ExempelBolag = {
  id: "1",
  companyName: "Lundsund Bygg & Partner AB",
  orgnr: "556438-7011",
  ort: "Umeå",
  website: "lundsundbyggpartnerab.example",
  anstallda: 13,
  bransch: "Bygg",
  beskrivning:
    "Bygg i Umeå med 13 anställda. Har precis anställt en ny inköpschef efter att tjänsten stått öppen sedan i våras.",
  contactFirstName: "Karin",
  contactLastName: "Öhman",
  contactRole: "Inköpschef",
  signal: "Ni har precis anställt en ny inköpschef efter att tjänsten stått öppen sedan i våras.",
  offer: "En hjärtstartare monterad i lokalen och en kort HLR-genomgång för hela teamet, bokad innan sommaren.",
  cta: "Vill du att jag skickar ett förslag anpassat efter er lokal?",
  score: 82,
  status: "ready",
  kallor: [
    { label: "Platsannons", url: "https://platsbanken.example/annons/lundsund-inkopschef" },
    { label: "Företagets webbplats", url: "https://lundsundbyggpartnerab.example/om-oss" }
  ],
  struktur: "b",
  utkast: { a: LUNDSUND_A, b: LUNDSUND_B },
  draft: LUNDSUND_B,
  resultat: {
    shorter: {
      new_version:
        "Hej Karin,\n\n" +
        "Om vi monterade en hjärtstartare i er lokal och höll en HLR-genomgång för teamet innan sommaren, skulle det vara till nytta?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Kortare: gratulationen är borta och frågan står ensam. Fortfarande B: en fråga om utfallet, och den sist.",
      subject_suggestions: ["Kort fråga till Lundsund", "Hjärtstartare hos Lundsund?"]
    },
    rewrite: {
      new_version:
        "Hej Karin,\n\n" +
        "Har ni en hjärtstartare på plats, eller ligger det på listan som ny inköpschef?\n\n" +
        "Om vi löste både den och HLR för teamet på en förmiddag innan sommaren, skulle det hjälpa dig?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Skriven om: öppnar med en fråga om läget i stället för en gratulation, men behåller B-formen med frågan om utfallet sist.",
      subject_suggestions: ["En fråga till nya inköpschefen", "Redan koll på hjärtstartaren?"]
    },
    improve: {
      new_version:
        "Hej Karin,\n\n" +
        "Grattis till rollen som inköpschef på Lundsund.\n\n" +
        "Om en hjärtstartare satt monterad i er lokal och hela teamet kunde HLR redan innan sommaren, utan att det kostar er mer än en förmiddag, vore det till nytta för dig?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Förbättrad: bolagsnamnet i gratulationen, utfallet före villkoret i frågan, och frågan riktad till henne, inte till bolaget.",
      subject_suggestions: ["Hjärtstartare in på listan?", "En sak till inköpschefslistan"]
    },
    personalize: {
      new_version:
        "Hej Karin,\n\n" +
        "En tjänst som stått öppen sedan i våras lämnar en lång lista att gå igenom.\n\n" +
        "Om hjärtstartaren och HLR för teamet var avbockade innan sommaren, utan att du själv behöver driva det, skulle det vara till nytta?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Personaliserad kring signalen: tjänsten var obesatt länge, så listan är lång. Frågan erbjuder att ta en punkt från den.",
      subject_suggestions: ["Det som blivit liggande sedan i våras", "Till nya inköpschefen på Lundsund"]
    },
    translate: {
      new_version:
        "Hi Karin,\n\n" +
        "Congratulations on the purchasing manager role.\n\n" +
        "If we mounted a defibrillator on your premises and ran a short CPR session for the whole team before summer, taking no more than a morning of your time, would that be useful?\n\n" +
        "Best regards,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Hela mejlet på engelska, samma korta form: en mening om dem, en fråga om utfallet, frågan sist.",
      subject_suggestions: ["A quick question for Lundsund's new purchasing manager"]
    },
    ab_variants: {
      new_version:
        "Variant A (gratulationen först):\n" +
        "Hej Karin,\n\n" +
        "Grattis till rollen som inköpschef.\n\n" +
        "Om vi monterade en hjärtstartare i er lokal och höll en HLR-genomgång för teamet innan sommaren, skulle det vara till nytta?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB\n\n" +
        "Variant B (bara frågan):\n" +
        "Hej Karin,\n\n" +
        "Om en hjärtstartare och HLR för hela teamet var klart innan sommaren, på en förmiddag, vore det till nytta för dig som ny inköpschef?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Två korta varianter: A har en mening om dem före frågan, B går rakt på frågan. Båda slutar med frågan.",
      subject_suggestions: ["Hjärtstartare på listan? (A)", "En förmiddag innan sommaren (B)"]
    },
    followup: {
      new_version:
        "Hej Karin,\n\n" +
        "Jag hörde av mig förra veckan om hjärtstartare och HLR-utbildning till er nya lokal. Sedan dess har vi satt ihop ett kort underlag som visar hur snabbt både montering och genomgång brukar gå för ett team i er storlek.\n\n" +
        "Vill du ha underlaget, eller är det bättre att höras om några veckor när listan hunnit kortas?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Uppföljning som tillför nytt underlag i stället för att bara påminna. Ger också ett alternativ (höras senare) i stället för att bara upprepa frågan.",
      subject_suggestions: ["Uppföljning: hjärtstartare hos Lundsund", "Ett kort underlag till er lista"]
    },
    analyze: {
      new_version:
        "Hej Karin,\n\n" +
        "Grattis till rollen som inköpschef.\n\n" +
        "Om vi monterade en hjärtstartare i er lokal och höll en HLR-genomgång för hela teamet innan sommaren, utan att det tar mer än en förmiddag av er tid, skulle det vara till nytta?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Bedömning: Struktur B, 34 ord i brödtexten, en sak före frågan och frågan sist. Signalen (ny inköpschef) bär gratulationen, och frågan beskriver ett konkret utfall med en tidsgräns. Villkoret 'utan att det tar mer än en förmiddag' gör frågan lätt att svara ja på. Ämnesraden är en fråga, vilket passar formen.",
      subject_suggestions: [],
      confidence_tips: "Nästa steg: prova Skriv om för en annan ingång, eller A/B för två frågor att välja mellan."
    }
  }
};

const VIKSUND_A: Utkast = {
  subject: "Servicelöftet på er nya hemsida",
  body:
      "Hej Mikael,\n\n" +
      "Jag såg att ni lagt om hemsidan och lyfter fram service som ert löfte till kunderna. Det löftet syns snabbast i sådant kunder faktiskt möter på plats.\n\n" +
      "En hjärtstartare synlig i entrén och en HLR-utbildning för teamet är precis den sortens detalj, och den går att nämna i löftet ni redan skrivit.\n\n" +
      "Vill du ha ett kort förslag du kan väga in i servicelöftet?\n\n" +
      "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
};

const VIKSUND_B: Utkast = {
  subject: "En sak till servicelöftet",
  body:
        "Hej Mikael,\n\n" +
        "Ni lyfter fram service som löfte på nya hemsidan.\n\n" +
        "Om en hjärtstartare satt synlig i er entré och hela teamet kunde HLR, något ni kan nämna i just det löftet, vore det intressant för er?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB"
};

const VIKSUND: ExempelBolag = {
  id: "2",
  companyName: "Viksund Bygg Gruppen AB",
  orgnr: "556859-7318",
  ort: "Umeå",
  website: "viksundbygggruppenab.example",
  anstallda: 14,
  bransch: "Bygg",
  beskrivning: "Bygg i Umeå med 14 anställda. Har precis lagt om sin hemsida och lyfter fram service som löfte till kunderna.",
  contactFirstName: "Mikael",
  contactLastName: "Strand",
  contactRole: "Platschef",
  signal: "Ni har precis lagt om hemsidan och lyfter fram service som ert löfte till kunderna.",
  offer: "En hjärtstartare synlig i entrén och en HLR-utbildning för teamet, något ni kan nämna i just det servicelöftet.",
  cta: "Vill du ha ett kort förslag du kan väga in i servicelöftet?",
  score: 69,
  status: "researching",
  kallor: [
    { label: "Företagets webbplats", url: "https://viksundbygggruppenab.example/service" },
    { label: "Pressmeddelande", url: "https://viksundbygggruppenab.example/nyheter/ny-hemsida" }
  ],
  struktur: "b",
  utkast: { a: VIKSUND_A, b: VIKSUND_B },
  draft: VIKSUND_B,
  resultat: {
    shorter: {
      new_version:
        "Hej Mikael,\n\n" +
        "Om en hjärtstartare satt synlig i er entré och hela teamet kunde HLR, vore det intressant för er?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Kortare: meningen om hemsidan är borta, frågan står ensam och slutar mejlet.",
      subject_suggestions: ["Hjärtstartare i entrén?", "Kort fråga till Viksund"]
    },
    rewrite: {
      new_version:
        "Hej Mikael,\n\n" +
        "Vad i servicelöftet på nya hemsidan ser kunderna först när de kliver in hos er?\n\n" +
        "Om det var en hjärtstartare i entrén och ett team som kan HLR, skulle det vara värt att titta på?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Skriven om: öppnar med en fråga om löftet i stället för ett konstaterande, och frågan om utfallet står kvar sist.",
      subject_suggestions: ["Det första kunderna ser", "Servicelöftet i entrén"]
    },
    improve: {
      new_version:
        "Hej Mikael,\n\n" +
        "Ni lyfter fram service som ert löfte på nya hemsidan.\n\n" +
        "Om en hjärtstartare satt synlig i entrén och hela teamet kunde HLR, en konkret sak att nämna i löftet, vore det intressant för er?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Förbättrad: 'ert löfte' kopplar till deras ord, och utfallet står som en konkret sak i löftet i stället för 'något'.",
      subject_suggestions: ["En konkret sak i servicelöftet", "Service som syns i entrén"]
    },
    personalize: {
      new_version:
        "Hej Mikael,\n\n" +
        "Servicelöftet på nya hemsidan märks mest i det kunderna möter på plats.\n\n" +
        "Om en hjärtstartare syntes i er entré och teamet kunde HLR, skulle det passa in i löftet ni redan skrivit?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Personaliserad kring signalen: löftet står på hemsidan, och frågan handlar om att göra det synligt på plats.",
      subject_suggestions: ["Löftet som syns på plats", "Till servicelöftet hos Viksund"]
    },
    translate: {
      new_version:
        "Hi Mikael,\n\n" +
        "Your new website puts service at the heart of your promise to customers.\n\n" +
        "If a defibrillator sat visibly in your entrance hall with a team trained in CPR, something to mention in that promise, would that be of interest?\n\n" +
        "Best regards,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Hela mejlet på engelska, samma korta form, frågan sist.",
      subject_suggestions: ["A detail for Viksund's service promise"]
    },
    ab_variants: {
      new_version:
        "Variant A (hemsidan först):\n" +
        "Hej Mikael,\n\n" +
        "Ni lyfter fram service som löfte på nya hemsidan.\n\n" +
        "Om en hjärtstartare satt synlig i entrén och teamet kunde HLR, vore det intressant för er?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB\n\n" +
        "Variant B (bara frågan):\n" +
        "Hej Mikael,\n\n" +
        "Om en hjärtstartare satt synlig i er entré och hela teamet kunde HLR, något att nämna i ert servicelöfte, skulle det vara värt ett kort förslag?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Två korta varianter: A konstaterar hemsidan först, B går rakt på frågan. Båda slutar med frågan.",
      subject_suggestions: ["Till servicelöftet (A)", "Ett kort förslag (B)"]
    },
    followup: {
      new_version:
        "Hej Mikael,\n\n" +
        "Jag hörde av mig förra veckan om hjärtstartaren i entrén. Sedan dess har jag pratat med ett par byggbolag som gjort samma sak och fått den nämnd i kundsamtal, inte bara på hemsidan.\n\n" +
        "Är det värt att höras en kort stund om det?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Uppföljning som tillför en ny iakttagelse (andra bolag som nämner det i kundsamtal) i stället för att bara påminna om förra mejlet.",
      subject_suggestions: ["Uppföljning: entrén hos Viksund", "Det kunder faktiskt nämner"]
    },
    analyze: {
      new_version:
        "Hej Mikael,\n\n" +
        "Ni lyfter fram service som löfte på nya hemsidan.\n\n" +
        "Om en hjärtstartare satt synlig i er entré och hela teamet kunde HLR, något ni kan nämna i just det löftet, vore det intressant för er?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Bedömning: Struktur B, 31 ord i brödtexten. Ingången är en mening om deras egna ord på hemsidan, och frågan beskriver ett utfall de kan se i entrén. Bisatsen 'något ni kan nämna i just det löftet' binder ihop utfallet med signalen. Ämnesraden pekar på löftet, inte på produkten, vilket passar en kall första kontakt.",
      subject_suggestions: [],
      confidence_tips: "Nästa steg: prova Skriv om för en annan ingång, eller A/B för två frågor att välja mellan."
    }
  }
};

const HAMMARNAS_A: Utkast = {
  subject: "Den nya lokalen hos Hammarnäs",
  body:
      "Hej Sara,\n\n" +
      "Grattis till den nya, större lokalen. Med fler kvadratmeter och 31 anställda på plats blir avståndet till en hjärtstartare snabbt en annan fråga än i den gamla lokalen.\n\n" +
      "Vi monterar en hjärtstartare i den nya lokalen och håller en HLR-genomgång för hela teamet, uppdelad på två pass så att produktionen inte behöver stå still.\n\n" +
      "Vill du att jag skickar ett förslag anpassat efter de 31 anställda?\n\n" +
      "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
};

const HAMMARNAS_B: Utkast = {
  subject: "Hjärtstartare i nya lokalen?",
  body:
        "Hej Sara,\n\n" +
        "Grattis till den nya, större lokalen.\n\n" +
        "Om vi monterade en hjärtstartare där och höll HLR-genomgången för alla 31 i två pass, så att produktionen inte står still, skulle det vara till nytta?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB"
};

const HAMMARNAS: ExempelBolag = {
  id: "3",
  companyName: "Hammarnäs Bygg Sverige AB",
  orgnr: "556201-4453",
  ort: "Umeå",
  website: "hammarnasbyggsverigeab.example",
  anstallda: 31,
  bransch: "Bygg",
  beskrivning: "Bygg i Umeå med 31 anställda. Har precis flyttat till en större lokal.",
  contactFirstName: "Sara",
  contactLastName: "Lindqvist",
  contactRole: "Inköpschef",
  signal: "Ni har precis flyttat till en större lokal.",
  offer:
    "En hjärtstartare i den nya, större lokalen och en HLR-genomgång för alla 31 anställda, uppdelad på två pass så att produktionen inte står still.",
  cta: "Vill du att jag skickar ett förslag anpassat efter de 31 anställda?",
  score: 91,
  status: "ready",
  kallor: [
    { label: "Företagets webbplats", url: "https://hammarnasbyggsverigeab.example/kontakt" },
    { label: "Pressmeddelande", url: "https://hammarnasbyggsverigeab.example/nyheter/ny-lokal" }
  ],
  struktur: "a",
  utkast: { a: HAMMARNAS_A, b: HAMMARNAS_B },
  draft: HAMMARNAS_A,
  resultat: {
    shorter: {
      new_version:
        "Hej Sara,\n\n" +
        "Grattis till den nya lokalen. Med fler kvadratmeter och 31 anställda blir avståndet till en hjärtstartare en annan fråga än förut.\n\n" +
        "Vill du ha ett förslag anpassat efter teamet?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Kortare: detaljen om de två passen är struken ur själva mejlet, kärnan står kvar i en mening.",
      subject_suggestions: ["Kort fråga om nya lokalen", "Hammarnäs: hjärtstartare i nya lokalen?"]
    },
    rewrite: {
      new_version:
        "Hej Sara,\n\n" +
        "Hur långt är det till närmaste hjärtstartare i den nya lokalen?\n\n" +
        "Med 31 anställda på en större yta är det en fråga värd att ställa sig, även om ingen ställt den ännu. Vi löser den: en hjärtstartare på plats och en HLR-genomgång för hela teamet, uppdelad på två pass.\n\n" +
        "Värt att titta på nu när ni ändå är i flyttläge?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Skriven om till en direkt fråga som öppning i stället för en gratulation. Samma fakta, ny ingång.",
      subject_suggestions: ["Hur långt till närmaste hjärtstartare?", "En fråga i flyttläget"]
    },
    improve: {
      new_version:
        "Hej Sara,\n\n" +
        "Grattis till den nya, större lokalen. Fler kvadratmeter och 31 anställda gör avståndet till en hjärtstartare till en annan fråga än i den gamla lokalen.\n\n" +
        "Vi monterar en hjärtstartare på plats och håller en HLR-genomgång för hela teamet, uppdelad på två pass så att produktionen går på som vanligt.\n\n" +
        "Ska jag skicka ett förslag anpassat efter teamet?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Förbättrad: CTA:n skärpt till en direkt fråga, och den vaga inledningen bytt mot en rakare formulering.",
      subject_suggestions: ["Avståndet i den nya lokalen", "31 anställda, en lokal"]
    },
    personalize: {
      new_version:
        "Hej Sara,\n\n" +
        "En flytt till större lokal löser utrymmet men flyttar sällan med sig sådant som satt sig i den gamla, som var hjärtstartaren stod. Med 31 anställda på en ny yta är det värt att kolla innan någon frågar.\n\n" +
        "Vi monterar en hjärtstartare i den nya lokalen och håller en HLR-genomgång för hela teamet, uppdelad på två pass.\n\n" +
        "Vill du att jag skickar ett förslag anpassat efter de 31 anställda?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Personaliserad kring det icke-uppenbara: en flytt löser inte automatiskt säkerhetsrutinerna, den kan tvärtom lämna dem kvar i den gamla lokalen.",
      subject_suggestions: ["Det som inte flyttar med av sig själv", "Till Hammarnäs om nya lokalen"]
    },
    translate: {
      new_version:
        "Hi Sara,\n\n" +
        "Congratulations on the move to a larger site. With more square meters and 31 employees, the distance to a defibrillator becomes a different question than it was in the old premises.\n\n" +
        "We mount a defibrillator on site and run CPR training for the whole team, split into two sessions so production is not affected.\n\n" +
        "Would you like a proposal tailored to the 31 employees?\n\n" +
        "Best regards,\nAnna, Hjärtsäker AB",
      explanation: "Hela mejlet på engelska, samma struktur och ton som originalet.",
      subject_suggestions: ["The new site at Hammarnäs"]
    },
    ab_variants: {
      new_version:
        "Variant A (praktisk fråga):\n" +
        "Hej Sara,\n\n" +
        "Grattis till den nya lokalen. Hur långt är det till närmaste hjärtstartare där ni sitter nu?\n\n" +
        "Vi monterar en på plats och håller en HLR-genomgång för hela teamet, uppdelad på två pass.\n\n" +
        "Vill du ha ett förslag anpassat efter de 31 anställda?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB\n\n" +
        "Variant B (möjlighetsfönster):\n" +
        "Hej Sara,\n\n" +
        "En flytt är ett av de få tillfällena då säkerhetsrutiner faktiskt går att se över utan att störa något pågående. Hjärtstartare och HLR hör hemma på den listan.\n\n" +
        "Ska jag skicka ett förslag anpassat efter teamet på 31?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Två vinklar: A ställer en praktisk fråga om avstånd, B ramar in flytten som ett tillfälle. Olika öppning, samma tydliga CTA i olika ordval.",
      subject_suggestions: ["Avståndsfrågan (A)", "Rätt läge att se över (B)"]
    },
    followup: {
      new_version:
        "Hej Sara,\n\n" +
        "Jag hörde av mig förra veckan om hjärtstartaren i den nya lokalen. Sedan dess har jag räknat på hur montering och en HLR-genomgång för 31 personer brukar läggas upp i praktiken, uppdelat så att produktionen inte påverkas.\n\n" +
        "Vill du se upplägget, eller passar det bättre att höras när ni landat i den nya lokalen?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Uppföljning som tillför ett konkret upplägg i stället för att bara fråga igen, och ger ett alternativ i tid.",
      subject_suggestions: ["Uppföljning: nya lokalen hos Hammarnäs", "Upplägget för 31 personer"]
    },
    analyze: {
      new_version:
        "Hej Sara,\n\n" +
        "Grattis till den nya, större lokalen. Med fler kvadratmeter och 31 anställda på plats blir avståndet till en hjärtstartare snabbt en annan fråga än i den gamla lokalen.\n\n" +
        "Vi monterar en hjärtstartare i den nya lokalen och håller en HLR-genomgång för hela teamet, uppdelad på två pass så att produktionen inte behöver stå still.\n\n" +
        "Vill du att jag skickar ett förslag anpassat efter de 31 anställda?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Bedömning: flytten är en stark, tydlig signal och kopplingen till avstånd/hjärtstartare är logisk utan att vara långsökt. Andra stycket är det tyngsta i mejlet, en mening kortare hade gjort det snabbare att läsa. CTA:n är specifik (nämner antalet anställda), vilket är bra.",
      subject_suggestions: [],
      confidence_tips: "Nästa steg: prova Kortare om andra stycket ska ner till en mening, eller Skriv om för en fråga som öppning."
    }
  }
};

// ---------------------------------------------------------------------------
// Omgång 2 — visas efter "Uppdatera".
// ---------------------------------------------------------------------------

const GRANSTRAND_A: Utkast = {
  subject: "Tre nya i produktionen hos Granstrand",
  body:
      "Hej Erik,\n\n" +
      "Jag såg att ni har tre annonser ute till produktionen samtidigt. Fler på golvet är bra, men det betyder också fler att introducera i säkerhetsrutinerna innan de står vid maskinerna själva.\n\n" +
      "Vi sätter en hjärtstartare i produktionslokalen och lägger en HLR-genomgång direkt i introduktionen, så att den följer med automatiskt för alla nya.\n\n" +
      "Vill du att HLR-genomgången läggs in i introduktionen för de nya?\n\n" +
      "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
};

const GRANSTRAND_B: Utkast = {
  subject: "HLR i introduktionen för de nya?",
  body:
        "Hej Erik,\n\n" +
        "Ni tar in tre nya till produktionen just nu.\n\n" +
        "Om HLR-genomgången låg färdig i introduktionen för alla nya och en hjärtstartare satt i produktionslokalen innan de börjar, skulle det hjälpa er?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB"
};

const GRANSTRAND: ExempelBolag = {
  id: "4",
  companyName: "Granstrand Tillverkning AB",
  orgnr: "556744-1288",
  ort: "Jönköping",
  website: "granstrandtillverkningab.example",
  anstallda: 37,
  bransch: "Tillverkning",
  beskrivning: "Tillverkning i Jönköping med 37 anställda. Rekryterar till produktionen, tre annonser ute samtidigt.",
  contactFirstName: "Erik",
  contactLastName: "Palm",
  contactRole: "Produktionschef",
  signal: "Ni rekryterar till produktionen med tre annonser ute samtidigt.",
  offer: "En hjärtstartare i produktionslokalen och en HLR-genomgång som går in i introduktionen för alla nya som börjar nu.",
  cta: "Vill du att HLR-genomgången läggs in i introduktionen för de nya?",
  score: 74,
  status: "new",
  kallor: [
    { label: "Platsannons", url: "https://platsbanken.example/annons/granstrand-produktion" },
    { label: "Företagets webbplats", url: "https://granstrandtillverkningab.example/jobba-hos-oss" }
  ],
  struktur: "b",
  utkast: { a: GRANSTRAND_A, b: GRANSTRAND_B },
  draft: GRANSTRAND_B,
  resultat: {
    shorter: {
      new_version:
        "Hej Erik,\n\n" +
        "Om HLR-genomgången låg färdig i introduktionen för de nya och en hjärtstartare satt i produktionslokalen, skulle det hjälpa er?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Kortare: meningen om rekryteringen är borta, frågan står ensam och slutar mejlet.",
      subject_suggestions: ["HLR i introduktionen?", "Kort fråga till Granstrand"]
    },
    rewrite: {
      new_version:
        "Hej Erik,\n\n" +
        "Vad får de tre nya i produktionen lära sig första veckan?\n\n" +
        "Om HLR låg i introduktionen och en hjärtstartare satt i lokalen innan de står vid maskinerna själva, skulle det vara värt att titta på?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Skriven om: öppnar med en fråga om introduktionen i stället för ett konstaterande, och frågan om utfallet står sist.",
      subject_suggestions: ["Första veckan för de nya", "Innan de står vid maskinerna"]
    },
    improve: {
      new_version:
        "Hej Erik,\n\n" +
        "Ni tar in tre nya till produktionen just nu.\n\n" +
        "Om HLR-genomgången följde med automatiskt i introduktionen för alla nya och en hjärtstartare satt i produktionslokalen innan de börjar, skulle det hjälpa dig?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Förbättrad: 'följde med automatiskt' säger vad utfallet är i vardagen, och frågan riktas till honom, inte till bolaget.",
      subject_suggestions: ["HLR som följer med introduktionen", "Tre nya i produktionen"]
    },
    personalize: {
      new_version:
        "Hej Erik,\n\n" +
        "Tre annonser samtidigt betyder tre introduktioner i säkerhetsrutinerna på kort tid.\n\n" +
        "Om HLR var en färdig punkt i den introduktionen och hjärtstartaren redan satt på plats, skulle det hjälpa er?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Personaliserad kring signalen: tre annonser samtidigt, alltså flera introduktioner på en gång. Frågan erbjuder en färdig punkt i dem.",
      subject_suggestions: ["Tre introduktioner på kort tid", "Till produktionen hos Granstrand"]
    },
    translate: {
      new_version:
        "Hi Erik,\n\n" +
        "You are bringing three new people into production right now.\n\n" +
        "If CPR training sat ready in the onboarding for every new hire, with a defibrillator mounted in the production hall before they start, would that help you?\n\n" +
        "Best regards,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Hela mejlet på engelska, samma korta form, frågan sist.",
      subject_suggestions: ["CPR in onboarding at Granstrand?"]
    },
    ab_variants: {
      new_version:
        "Variant A (rekryteringen först):\n" +
        "Hej Erik,\n\n" +
        "Ni tar in tre nya till produktionen just nu.\n\n" +
        "Om HLR låg i introduktionen och en hjärtstartare satt i lokalen innan de börjar, skulle det hjälpa er?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB\n\n" +
        "Variant B (bara frågan):\n" +
        "Hej Erik,\n\n" +
        "Om HLR-genomgången var en färdig punkt i introduktionen för alla nya i produktionen, med hjärtstartaren på plats innan de börjar, vore det till nytta?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Två korta varianter: A konstaterar rekryteringen först, B går rakt på frågan. Båda slutar med frågan.",
      subject_suggestions: ["HLR i introduktionen (A)", "En färdig punkt (B)"]
    },
    followup: {
      new_version:
        "Hej Erik,\n\n" +
        "Jag hörde av mig förra veckan om att lägga HLR i introduktionen för de tre nya i produktionen. Sedan dess har jag pratat med ett tillverkningsbolag i er storlek som gjorde precis det, och genomgången tar numera under en timme per grupp.\n\n" +
        "Är det värt att höras om hur det skulle se ut hos er?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Uppföljning som tillför en ny detalj (tidsåtgången hos ett jämförbart bolag) i stället för att bara upprepa frågan.",
      subject_suggestions: ["Uppföljning: introduktionen hos Granstrand", "Under en timme per grupp"]
    },
    analyze: {
      new_version:
        "Hej Erik,\n\n" +
        "Ni tar in tre nya till produktionen just nu.\n\n" +
        "Om HLR-genomgången låg färdig i introduktionen för alla nya och en hjärtstartare satt i produktionslokalen innan de börjar, skulle det hjälpa er?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Bedömning: Struktur B, 32 ord i brödtexten. Ingången är en mening om rekryteringen, och frågan beskriver utfallet i deras egen rutin (introduktionen) med en tidpunkt (innan de börjar). Frågan riktar sig till 'er', vilket kan bli 'dig' för att träffa produktionschefen direkt. Ämnesraden är en fråga som speglar mejlets fråga.",
      subject_suggestions: [],
      confidence_tips: "Nästa steg: prova Skriv om för en annan ingång, eller A/B för två frågor att välja mellan."
    }
  }
};

const SJOHAGA_A: Utkast = {
  subject: "Bytet av affärssystem hos Sjöhaga",
  body:
      "Hej Lina,\n\n" +
      "Jag läste inlägget om att ni bytt affärssystem. När ett sånt byte väl är gjort brukar man passa på att se över annat som ändå legat och väntat, innan allt sätter sig igen.\n\n" +
      "Vi sätter en hjärtstartare i lagerlokalen och lägger en HLR-genomgång som går att boka digitalt, samma väg som ni redan lagt om till för annat.\n\n" +
      "Vill du ha ett förslag du kan boka direkt digitalt?\n\n" +
      "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
};

const SJOHAGA_B: Utkast = {
  subject: "Bokas digitalt, som resten",
  body:
        "Hej Lina,\n\n" +
        "Jag läste inlägget om bytet av affärssystem.\n\n" +
        "Om en hjärtstartare i lagerlokalen och en HLR-genomgång för teamet gick att boka digitalt, samma väg som ni redan lagt om till, skulle det vara användbart?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB"
};

const SJOHAGA: ExempelBolag = {
  id: "5",
  companyName: "Sjöhaga Logistik Gruppen AB",
  orgnr: "556019-5473",
  ort: "Örebro",
  website: "sjohagalogistikgruppenab.example",
  anstallda: 22,
  bransch: "Logistik",
  beskrivning: "Logistik i Örebro med 22 anställda. Har precis bytt affärssystem och skriver om det på sin blogg.",
  contactFirstName: "Lina",
  contactLastName: "Berggren",
  contactRole: "Platschef",
  signal: "Ni har precis bytt affärssystem, vilket ni skrivit om på er egen blogg.",
  offer: "En hjärtstartare i lagerlokalen och en HLR-genomgång som går att boka digitalt, samma väg som ni redan lagt om till för annat.",
  cta: "Vill du ha ett förslag du kan boka direkt digitalt?",
  score: 63,
  status: "researching",
  kallor: [
    { label: "Företagets webbplats", url: "https://sjohagalogistikgruppenab.example/blogg/nytt-affarssystem" },
    { label: "Pressmeddelande", url: "https://sjohagalogistikgruppenab.example/nyheter/systembyte" }
  ],
  struktur: "b",
  utkast: { a: SJOHAGA_A, b: SJOHAGA_B },
  draft: SJOHAGA_B,
  resultat: {
    shorter: {
      new_version:
        "Hej Lina,\n\n" +
        "Om en hjärtstartare i lagerlokalen och en HLR-genomgång för teamet gick att boka digitalt, skulle det vara användbart?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Kortare: meningen om blogginlägget är borta, frågan står ensam och slutar mejlet.",
      subject_suggestions: ["Bokas digitalt?", "Kort fråga till Sjöhaga"]
    },
    rewrite: {
      new_version:
        "Hej Lina,\n\n" +
        "Vad mer än affärssystemet har ni lagt om till digitalt det senaste året?\n\n" +
        "Om hjärtstartaren och HLR för teamet gick samma väg, bokade direkt på webben, skulle det passa er?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Skriven om: öppnar med en fråga om omläggningen i stället för att referera inlägget, och frågan om utfallet står sist.",
      subject_suggestions: ["Samma väg som affärssystemet", "Nästa sak att lägga om"]
    },
    improve: {
      new_version:
        "Hej Lina,\n\n" +
        "Jag läste ert inlägg om bytet av affärssystem.\n\n" +
        "Om en hjärtstartare i lagerlokalen och en HLR-genomgång för teamet gick att boka digitalt, samma väg som ni redan valt för annat, skulle det vara användbart för dig?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Förbättrad: 'ert inlägg' och 'redan valt' knyter till deras eget beslut, och frågan riktas till henne.",
      subject_suggestions: ["Bokas digitalt, som affärssystemet", "Till lagret hos Sjöhaga"]
    },
    personalize: {
      new_version:
        "Hej Lina,\n\n" +
        "Ett systembyte brukar vara tillfället då annat som legat och väntat också blir gjort.\n\n" +
        "Om hjärtstartaren och HLR för teamet var en sådan sak, bokad digitalt på fem minuter, skulle det vara till nytta?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Personaliserad kring signalen: bytet som tillfälle att göra annat som väntat. Frågan gör hjärtstartaren till en av de sakerna.",
      subject_suggestions: ["Det som väntat under systembytet", "Till platschefen på Sjöhaga"]
    },
    translate: {
      new_version:
        "Hi Lina,\n\n" +
        "I read your post about switching business systems.\n\n" +
        "If a defibrillator for the warehouse with CPR training for the team could be booked online, the same route you have already chosen for other things, would that be useful?\n\n" +
        "Best regards,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Hela mejlet på engelska, samma korta form, frågan sist.",
      subject_suggestions: ["Booked online, like the rest"]
    },
    ab_variants: {
      new_version:
        "Variant A (inlägget först):\n" +
        "Hej Lina,\n\n" +
        "Jag läste inlägget om bytet av affärssystem.\n\n" +
        "Om hjärtstartaren och HLR för teamet gick att boka digitalt, skulle det vara användbart?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB\n\n" +
        "Variant B (bara frågan):\n" +
        "Hej Lina,\n\n" +
        "Om en hjärtstartare i lagerlokalen och en HLR-genomgång för teamet gick att boka direkt på webben, utan offert och telefonsamtal, vore det till nytta för er?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Två korta varianter: A refererar inlägget först, B går rakt på frågan. Båda slutar med frågan.",
      subject_suggestions: ["Bokas digitalt (A)", "Utan offert och samtal (B)"]
    },
    followup: {
      new_version:
        "Hej Lina,\n\n" +
        "Jag hörde av mig förra veckan om hjärtstartaren till lagerlokalen. Sedan dess har jag lagt upp bokningen så att hela processen, från hjärtstartare till HLR-genomgång, går att boka i ett enda digitalt steg.\n\n" +
        "Vill du se hur det ser ut, eller passar det bättre om jag hör av mig om ett par veckor?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Uppföljning som tillför något konkret nytt (en färdig digital bokningsväg) i stället för att bara fråga om de sett förra mejlet.",
      subject_suggestions: ["Uppföljning: lagerlokalen hos Sjöhaga", "Bokning i ett steg"]
    },
    analyze: {
      new_version:
        "Hej Lina,\n\n" +
        "Jag läste inlägget om bytet av affärssystem.\n\n" +
        "Om en hjärtstartare i lagerlokalen och en HLR-genomgång för teamet gick att boka digitalt, samma väg som ni redan lagt om till, skulle det vara användbart?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB",
      explanation:
        "Bedömning: Struktur B, 33 ord i brödtexten. Ingången visar att mejlet bygger på deras egen blogg, och frågan beskriver utfallet (bokas digitalt) som en fortsättning på det beslut de redan tagit. Frågan är riktad till 'det', inte till henne; 'för dig' hade gjort den mer personlig. Ämnesraden knyter an till inlägget utan att upprepa det.",
      subject_suggestions: [],
      confidence_tips: "Nästa steg: prova Skriv om för en annan ingång, eller A/B för två frågor att välja mellan."
    }
  }
};

const ALMNAS_A: Utkast = {
  subject: "Servicelöftet till hyresgästerna hos Almnäs",
  body:
      "Hej Jonas,\n\n" +
      "Jag såg er nya tjänstesida och löftet om service till hyresgästerna. Ett sånt löfte märks mest i sådant som finns på plats i huset, inte bara i texten om det.\n\n" +
      "En hjärtstartare i fastighetens gemensamma utrymme och en HLR-genomgång för personalen är precis den sortens sak, och går att lyfta fram i löftet ni redan skrivit.\n\n" +
      "Vill du ha ett förslag att väga in i servicelöftet till hyresgästerna?\n\n" +
      "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
};

const ALMNAS_B: Utkast = {
  subject: "Till servicelöftet för hyresgästerna",
  body:
        "Hej Jonas,\n\n" +
        "Ni lyfter fram service till hyresgästerna på nya tjänstesidan.\n\n" +
        "Om en hjärtstartare fanns i fastighetens gemensamma utrymme och personalen kunde HLR, något ni kan lyfta fram i det löftet, vore det intressant?\n\n" +
        "Vänliga hälsningar,\n" +
        "Anna, Hjärtsäker AB"
};

const ALMNAS: ExempelBolag = {
  id: "6",
  companyName: "Almnäs Fastighet AB",
  orgnr: "556352-9061",
  ort: "Västerås",
  website: "almnasfastighetab.example",
  anstallda: 14,
  bransch: "Fastighet",
  beskrivning: "Fastighet i Västerås med 14 anställda. Har precis lagt om sin tjänstesida och lyfter fram service till hyresgästerna.",
  contactFirstName: "Jonas",
  contactLastName: "Ek",
  contactRole: "VD",
  signal: "Ni har precis lagt om tjänstesidan och lyfter fram servicelöftet till era hyresgäster.",
  offer: "En hjärtstartare i fastighetens gemensamma utrymme och en HLR-genomgång ni kan lyfta fram i servicelöftet till hyresgästerna.",
  cta: "Vill du ha ett förslag att väga in i servicelöftet till hyresgästerna?",
  score: 88,
  status: "contacted",
  kallor: [
    { label: "Företagets webbplats", url: "https://almnasfastighetab.example/tjanster" },
    { label: "Pressmeddelande", url: "https://almnasfastighetab.example/nyheter/nytt-servicelofte" }
  ],
  struktur: "a",
  utkast: { a: ALMNAS_A, b: ALMNAS_B },
  draft: ALMNAS_A,
  resultat: {
    shorter: {
      new_version:
        "Hej Jonas,\n\n" +
        "Ni lyfter fram service till hyresgästerna på nya tjänstesidan. En hjärtstartare i det gemensamma utrymmet är precis den sortens sak som märks på plats.\n\n" +
        "Vill du ha ett förslag att väga in i löftet?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Kortare: HLR-genomgången nämns inte längre som en egen sak, den ryms i 'förslag', och ett helt stycke är struket.",
      subject_suggestions: ["Kort fråga om servicelöftet", "Almnäs: hjärtstartare i huset"]
    },
    rewrite: {
      new_version:
        "Hej Jonas,\n\n" +
        "Ett servicelöfte på en tjänstesida är ett löfte hyresgästerna märker först när de ser det i huset, inte i texten.\n\n" +
        "En hjärtstartare i det gemensamma utrymmet och en HLR-genomgång för personalen är ett sätt att göra löftet konkret, inte bara skrivet.\n\n" +
        "Värt ett kort förslag?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Ny struktur, samma tanke som originalet men i omvänd ordning: löftets logik före exemplet, i stället för observation följt av erbjudande.",
      subject_suggestions: ["Ett löfte hyresgästerna märker", "En fråga om tjänstesidan"]
    },
    improve: {
      new_version:
        "Hej Jonas,\n\n" +
        "Jag såg er nya tjänstesida och löftet om service till hyresgästerna. En hjärtstartare i det gemensamma utrymmet och en HLR-genomgång för personalen gör det löftet konkret, inte bara skrivet.\n\n" +
        "Ska jag skicka ett förslag att väga in i löftet?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Förbättrad: två stycken i stället för tre, och CTA:n skärpt från 'vill du ha' till en direkt fråga.",
      subject_suggestions: ["Gör löftet konkret", "En detalj till tjänstesidan"]
    },
    personalize: {
      new_version:
        "Hej Jonas,\n\n" +
        "Ett servicelöfte som VD:n själv lagt in på tjänstesidan säger att det inte bara är marknadstext, någon har tagit ställning för att stå bakom det. Det som saknas är ofta det hyresgästerna faktiskt ser i huset.\n\n" +
        "En hjärtstartare i det gemensamma utrymmet och en HLR-genomgång för personalen är precis den sortens sak, och går att lyfta fram i löftet ni redan skrivit.\n\n" +
        "Vill du ha ett förslag att väga in i servicelöftet till hyresgästerna?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Personaliserad kring att kontakten är VD, inte bara att sidan bytts: löftet är ett beslut på ledningsnivå, inte en textändring i marknadsavdelningen.",
      subject_suggestions: ["Ett löfte på ledningsnivå", "Till Almnäs om löftet i huset"]
    },
    translate: {
      new_version:
        "Hi Jonas,\n\n" +
        "I saw your new services page and the promise of service to your tenants. A promise like that shows up most clearly in what is actually in the building, not just in the text about it.\n\n" +
        "A defibrillator in the shared space and CPR training for staff is exactly that kind of detail, and it fits the promise you have already written.\n\n" +
        "Would you like a proposal to weigh into the tenant service promise?\n\n" +
        "Best regards,\nAnna, Hjärtsäker AB",
      explanation: "Engelsk version. 'Tjänstesida' blir 'services page' och 'servicelöfte' blir 'service promise'.",
      subject_suggestions: ["The tenant service promise at Almnäs"]
    },
    ab_variants: {
      new_version:
        "Variant A (löftet blir konkret):\n" +
        "Hej Jonas,\n\n" +
        "Ni lyfter fram service till hyresgästerna på nya tjänstesidan. En hjärtstartare i det gemensamma utrymmet gör det löftet konkret för alla som bor i huset.\n\n" +
        "Vill du ha ett förslag att väga in i löftet?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB\n\n" +
        "Variant B (frågan om nuläget):\n" +
        "Hej Jonas,\n\n" +
        "Finns det redan en hjärtstartare i något av era gemensamma utrymmen, eller är det något som hamnat på listan sedan tjänstesidan skrevs om?\n\n" +
        "Värt en kort fråga?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Två vinklar: A kopplar direkt till löftet, B öppnar med en nyfiken fråga om nuläget i fastigheten. Olika öppning och olika CTA-ton.",
      subject_suggestions: ["Löftet, konkret (A)", "En fråga om nuläget (B)"]
    },
    followup: {
      new_version:
        "Hej Jonas,\n\n" +
        "Jag hörde av mig förra veckan om hjärtstartaren till det gemensamma utrymmet. Sedan dess har jag tagit fram ett kort underlag som visar hur andra fastighetsbolag valt att formulera det i sitt eget servicelöfte.\n\n" +
        "Vill du se underlaget, eller är det bättre att höras när ni hunnit landa i det?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Uppföljning som tillför ett konkret underlag (hur andra formulerat det) i stället för att bara påminna om förra mejlet.",
      subject_suggestions: ["Uppföljning: löftet hos Almnäs", "Hur andra fastighetsbolag gjort"]
    },
    analyze: {
      new_version:
        "Hej Jonas,\n\n" +
        "Jag såg er nya tjänstesida och löftet om service till hyresgästerna. Ett sånt löfte märks mest i sådant som finns på plats i huset, inte bara i texten om det.\n\n" +
        "En hjärtstartare i fastighetens gemensamma utrymme och en HLR-genomgång för personalen är precis den sortens sak, och går att lyfta fram i löftet ni redan skrivit.\n\n" +
        "Vill du ha ett förslag att väga in i servicelöftet till hyresgästerna?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Bedömning: kopplingen mellan tjänstesidans löfte och ett konkret objekt i huset är tydlig och bär mejlet väl. Att kontakten är VD nämns inte i brödtexten, trots att det stärker signalen: ett beslut på ledningsnivå, inte bara en textändring. CTA:n är bra och specifik.",
      subject_suggestions: [],
      confidence_tips: "Nästa steg: prova Personalisera för att väva in att löftet kommer från VD själv, eller A/B på ämnesraden."
    }
  }
};

export const EXEMPEL_OMGANG_1: ExempelBolag[] = [LUNDSUND, VIKSUND, HAMMARNAS];
export const EXEMPEL_OMGANG_2: ExempelBolag[] = [GRANSTRAND, SJOHAGA, ALMNAS];

/** Alla sex, för uppslagning oavsett vilken omgång som visas just nu. */
export const EXEMPELBOLAG: ExempelBolag[] = [...EXEMPEL_OMGANG_1, ...EXEMPEL_OMGANG_2];

// ---------------------------------------------------------------------------
// Fler körningar i demon (Sebbe 2026-10-29): den som klickar på demolänken i
// ett utskick ska kunna köra Iris så många gånger hen vill, snabbt och utan
// riktiga körningar. Efter de sex handskrivna bolagen blir varje omgång tre
// varianter av dem: samma utkast och svar, med nytt bolagsnamn, ort och
// kontakt. Deterministiskt ur id:t, så att Email Studio-routen hittar samma
// variant på servern (finnExempelbolag).
// ---------------------------------------------------------------------------

/* Påhittade namn, orter och personer för varianterna. Data, inte copy. */
const STAMMAR = ["Björkvik", "Norrbacka", "Ekudden", "Tallhed", "Lövnäs", "Granby", "Älvsta", "Bergslund", "Furuvik", "Kvarnby", "Askeby", "Rönnås", "Lindhult", "Hagaberg", "Ängsvik", "Videbo", "Storå", "Klippan"]; // inte-copy: fixturdata
const ORTER = ["Luleå", "Sundsvall", "Gävle", "Karlstad", "Växjö", "Halmstad", "Uppsala", "Linköping", "Borås", "Kalmar", "Östersund", "Skellefteå"]; // inte-copy: fixturdata
const KVINNOR = ["Emma", "Johanna", "Maria", "Elin", "Sofia", "Frida", "Hanna", "Malin"]; // inte-copy: fixturdata
const MAN = ["Anders", "Johan", "Daniel", "Magnus", "Patrik", "Henrik", "Fredrik", "Oskar"]; // inte-copy: fixturdata
const EFTERNAMN = ["Nyberg", "Holm", "Sandberg", "Lund", "Forsberg", "Wikström", "Åberg", "Hedlund", "Engström", "Sjöberg"]; // inte-copy: fixturdata
const FIXTURKVINNOR = new Set(["Karin", "Sara", "Lina"]);

const VARIANT_ID = /^v(\d+)-(\d+)$/;

function ascii(s: string): string {
  return s.toLowerCase().replace(/[åä]/g, "a").replace(/ö/g, "o").replace(/é/g, "e");
}

function ersattOrd(text: string, fran: string, till: string): string {
  const monster = fran.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return text.replace(new RegExp(`(?<!\\p{L})${monster}(?!\\p{L})`, "gu"), till);
}

function djupErsatt<T>(varde: T, byt: (s: string) => string): T {
  if (typeof varde === "string") return byt(varde) as T;
  if (Array.isArray(varde)) return varde.map((v) => djupErsatt(v, byt)) as T;
  if (varde && typeof varde === "object") {
    return Object.fromEntries(Object.entries(varde).map(([k, v]) => [k, djupErsatt(v, byt)])) as T;
  }
  return varde;
}

/** Variant nummer `n` av fixturbolaget `bas`: nytt namn, ny ort, ny kontakt. */
export function exempelVariant(bas: ExempelBolag, n: number): ExempelBolag {
  const stam = bas.companyName.split(" ")[0];
  const nyStam = STAMMAR[n % STAMMAR.length];
  const nyOrt = ORTER[(n * 5) % ORTER.length];
  const fornamn = FIXTURKVINNOR.has(bas.contactFirstName) ? KVINNOR : MAN;
  const nyttFornamn = fornamn[(n * 3) % fornamn.length];
  const nyttEfternamn = EFTERNAMN[(n * 7) % EFTERNAMN.length];
  const nyttNamn = bas.companyName.replace(stam, nyStam);
  const nyttOrgnr = `5590${String(10 + (n % 90)).padStart(2, "0")}-${String(1000 + ((n * 7919) % 9000))}`;
  const byt = (s: string) => {
    let ut = s.split(bas.companyName).join(nyttNamn).split(bas.orgnr).join(nyttOrgnr);
    ut = ut.split(ascii(stam)).join(ascii(nyStam));
    ut = ut.split(`${ascii(bas.contactFirstName)}@`).join(`${ascii(nyttFornamn)}@`);
    for (const [fran, till] of [
      [stam, nyStam],
      [bas.contactFirstName, nyttFornamn],
      [bas.contactLastName, nyttEfternamn],
      [bas.ort, nyOrt]
    ] as const) {
      ut = ersattOrd(ut, fran, till);
    }
    return ut;
  };
  const ny = djupErsatt(bas, byt);
  return {
    ...ny,
    // Djupkopian gav `draft` och `utkast[struktur]` var sitt objekt; knyt ihop dem igen.
    draft: ny.utkast[ny.struktur],
    id: `v${n}-${bas.id}`,
    score: Math.max(58, Math.min(94, bas.score + ((n * 13) % 15) - 7)),
    status: "new"
  };
}

/**
 * Bolaget med utkastet i strukturen besökaren valde vid Kör Iris. Utan val
 * (eller samma som standarden) returneras bolaget orört, med sina handskrivna
 * åtgärdsresultat; med en annan struktur följer bara utkastet med, och
 * resultaten är fortfarande skrivna i standardformen.
 */
export function medStruktur(bolag: ExempelBolag, struktur: Struktur | undefined): ExempelBolag {
  if (!struktur || struktur === bolag.struktur) return bolag;
  return { ...bolag, struktur, draft: bolag.utkast[struktur] };
}

/**
 * Omgång `omgang` (0, 1, 2 …) av demons körning: först de två handskrivna
 * omgångarna, sedan tre nya varianter per omgång, utan slut. `struktur` är
 * valet i Kör Iris; utan det visar varje bolag sin standard (de flesta B).
 */
export function exempelOmgang(omgang: number, struktur?: Struktur): ExempelBolag[] {
  const bas =
    omgang === 0
      ? EXEMPEL_OMGANG_1
      : omgang === 1
        ? EXEMPEL_OMGANG_2
        : [0, 1, 2].map((i) => {
            const n = omgang * 3 + i;
            return exempelVariant(EXEMPELBOLAG[n % EXEMPELBOLAG.length], n);
          });
  return bas.map((b) => medStruktur(b, struktur));
}

/**
 * Hittar bolaget en Email Studio-förfrågan gäller. `companyId` (bolagets
 * `id`, skickat i `context.companyId`) prövas först — det är stabilt även om
 * kunden bytt bolagsnamnet i ämnesraden eller texten. Bolagsnamnet är
 * reserven för anrop som saknar id (t.ex. ett äldre klientbygge).
 *
 * Returnerar `undefined` när INGET av de sex bolagen matchar — det täcker
 * bland annat det fristående exempelmejlet på marknadssidan
 * (lib/data/emails.ts PUBLIKT_EXEMPELMEJL, bolagsnamn "E-Tech"), som inte är
 * ett av de här sex och därför inte har något handskrivet svar.
 */
export function finnExempelbolag(context: { companyId?: unknown; companyName?: unknown } | null | undefined): ExempelBolag | undefined {
  const id = typeof context?.companyId === "string" ? context.companyId.trim() : "";
  if (id) {
    const traff = EXEMPELBOLAG.find((b) => b.id === id);
    if (traff) return traff;
    // En variant ur demons fler körningar (exempelVariant) byggs om ur id:t.
    const variant = VARIANT_ID.exec(id);
    const bas = variant ? EXEMPELBOLAG.find((b) => b.id === variant[2]) : undefined;
    if (variant && bas) return exempelVariant(bas, Number(variant[1]));
  }

  const namn = typeof context?.companyName === "string" ? context.companyName.trim().toLowerCase() : "";
  if (!namn) return undefined;
  return EXEMPELBOLAG.find((b) => b.companyName.toLowerCase() === namn);
}

/**
 * Åtgärdens resultat för ett bolag. Okända/oexponerade åtgärder (t.ex.
 * `longer`/`expand`, som finns i app/api/email-studio/route.ts men aldrig
 * visas som knapp i EmailStudioEditor) faller tillbaka på "improve" — samma
 * regel som routens `kandAction`-fallback för en okänd åtgärd.
 */
export function exempelresultat(bolag: ExempelBolag, action: string): ExempelActionResultat {
  const kand = EXEMPEL_ACTIONS.includes(action as ExempelAction) ? (action as ExempelAction) : "improve";
  return bolag.resultat[kand];
}

/** `halsning()` tillämpad på bolagets kontakt — bekräftar att fixturerna verkligen hälsar rätt. */
export function forvantadHalsning(bolag: ExempelBolag): string {
  return halsning(kontaktnamn(bolag));
}
