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
  draft: { subject: string; body: string };
  resultat: Record<ExempelAction, ExempelActionResultat>;
};

/** Kontaktens fulla namn, som skickas som `contactName` — `halsning()` plockar ut förnamnet. */
export function kontaktnamn(bolag: Pick<ExempelBolag, "contactFirstName" | "contactLastName">): string {
  return `${bolag.contactFirstName} ${bolag.contactLastName}`;
}

// ---------------------------------------------------------------------------
// Omgång 1 — de tre bolagen som visas först.
// ---------------------------------------------------------------------------

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
  draft: {
    subject: "Ny inköpschef hos Lundsund",
    body:
      "Hej Karin,\n\n" +
      "Grattis till rollen som inköpschef. Jag såg att tjänsten stått öppen sedan i våras, så ni har säkert en hel del att komma igång med.\n\n" +
      "En sak som ofta hamnar sist på en sådan lista är hjärtstartare och HLR för teamet, trots att den snabbt blir en fråga någon efterfrågar. Vi monterar en hjärtstartare i lokalen och håller en kort HLR-genomgång för hela teamet, bokad innan sommaren.\n\n" +
      "Vill du att jag skickar ett förslag anpassat efter er lokal?\n\n" +
      "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
  },
  resultat: {
    shorter: {
      new_version:
        "Hej Karin,\n\n" +
        "Grattis till rollen som inköpschef. En hjärtstartare och en kort HLR-genomgång brukar hamna sist på en sådan lista, trots att den efterfrågas snabbt.\n\n" +
        "Vill du ha ett förslag anpassat efter er lokal?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Kortare: bakgrunden om tjänsten är borta, en enda mening bär signalen och erbjudandet, och CTA:n står kvar oförändrad.",
      subject_suggestions: ["Kort fråga till Lundsund", "Hjärtstartare hos Lundsund?"]
    },
    rewrite: {
      new_version:
        "Hej Karin,\n\n" +
        "Har ni redan en hjärtstartare på plats, eller ligger det på listan som ny inköpschef?\n\n" +
        "Många byggbolag i er storlek skjuter den frågan framför sig tills någon efterfrågar den. Vi löser det i ett svep: hjärtstartare monterad i lokalen och en HLR-genomgång för hela teamet, klart innan sommaren.\n\n" +
        "Är det något att titta på nu när du ändå går igenom listan?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Skriven om till Fråga → Värde → Fråga i stället för observation → erbjudande. Samma fakta, ny ingång via en direkt fråga till den nya rollen.",
      subject_suggestions: ["En fråga till nya inköpschefen", "Redan koll på hjärtstartaren?"]
    },
    improve: {
      new_version:
        "Hej Karin,\n\n" +
        "Grattis till rollen som inköpschef på Lundsund. Tjänsten har stått öppen sedan i våras, så listan är sannolikt lång redan.\n\n" +
        "Hjärtstartare och HLR-utbildning brukar hamna långt ner på den, trots att den är snabb att lösa: vi monterar hjärtstartaren i lokalen och håller en HLR-genomgång för hela teamet, bokad innan sommaren.\n\n" +
        "Ska jag skicka ett förslag anpassat efter er lokal?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Förbättrad: aktiv röst genomgående, CTA:n skärpt till en direkt fråga i stället för 'vill du att', och ämnesraden pekar på vad mejlet faktiskt handlar om.",
      subject_suggestions: ["Hjärtstartare in på listan?", "En sak till inköpschefslistan"]
    },
    personalize: {
      new_version:
        "Hej Karin,\n\n" +
        "Att en inköpschefstjänst stått öppen sedan i våras säger något om hur mycket som samlats på hög under tiden. Hjärtstartare och HLR brukar vara precis den sortens punkt: viktig, men aldrig akut nog för att gå före allt annat.\n\n" +
        "Vi tar det steget åt er: en hjärtstartare monterad i lokalen och en HLR-genomgång för hela teamet, bokad innan sommaren.\n\n" +
        "Vill du att jag skickar ett förslag anpassat efter er lokal?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Personaliserad kring den faktiska signalen: en länge obesatt tjänst, inte bara att den är ny. Kopplar direkt till varför hjärtstartarfrågan blivit liggande.",
      subject_suggestions: ["Det som blivit liggande sedan i våras", "Till nya inköpschefen på Lundsund"]
    },
    translate: {
      new_version:
        "Hi Karin,\n\n" +
        "Congratulations on the purchasing manager role. I saw the position had been open since spring, so the list is probably already long.\n\n" +
        "Defibrillators and CPR training tend to end up near the bottom of that list, even though they are quick to sort out. We mount a defibrillator on site and run a short CPR session for the whole team, arranged before summer.\n\n" +
        "Would you like a proposal tailored to your premises?\n\n" +
        "Best regards,\nAnna, Hjärtsäker AB",
      explanation:
        "Hela mejlet skrivet på engelska, tonen bevarad. Titeln 'purchasing manager' används i stället för en ordagrann översättning av 'inköpschef'.",
      subject_suggestions: ["A note for Lundsund's new purchasing manager"]
    },
    ab_variants: {
      new_version:
        "Variant A (problemet som blir liggande):\n" +
        "Hej Karin,\n\n" +
        "En inköpschefstjänst som stått öppen sedan i våras brukar betyda en lista av saker som fått vänta. Hjärtstartare och HLR är ofta en av dem, trots att den är enkel att lösa.\n\n" +
        "Vi monterar en hjärtstartare i lokalen och håller en HLR-genomgång för hela teamet, bokad innan sommaren.\n\n" +
        "Vill du att jag skickar ett förslag anpassat efter er lokal?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB\n\n" +
        "Variant B (ett enkelt förstaval):\n" +
        "Hej Karin,\n\n" +
        "Grattis till rollen. Om du letar efter något enkelt att bocka av tidigt: en hjärtstartare monterad i lokalen och en HLR-genomgång för hela teamet, klart innan sommaren.\n\n" +
        "Ska jag skicka ett förslag anpassat efter er lokal?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Två vinklar: A utgår från det som blivit liggande, B presenterar det som ett enkelt förstaval i den nya rollen. Olika öppning och olika CTA-formulering.",
      subject_suggestions: ["Det som blivit liggande (A)", "Ett enkelt förstaval (B)"]
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
        "Grattis till rollen som inköpschef. Jag såg att tjänsten stått öppen sedan i våras, så ni har säkert en hel del att komma igång med.\n\n" +
        "En sak som ofta hamnar sist på en sådan lista är hjärtstartare och HLR för teamet, trots att den snabbt blir en fråga någon efterfrågar. Vi monterar en hjärtstartare i lokalen och håller en kort HLR-genomgång för hela teamet, bokad innan sommaren.\n\n" +
        "Vill du att jag skickar ett förslag anpassat efter er lokal?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Bedömning: Signalen (ny inköpschef, tjänsten öppen sedan i våras) bär mejlet och gör det tydligt varför just nu. Stycke två är en aning långt för en kall första kontakt och kan kortas till en mening. CTA:n är bra: låg tröskel och specifik. Ämnesraden är korrekt men lite trög, en fråga i ämnesraden brukar öppnas oftare.",
      subject_suggestions: [],
      confidence_tips: "Nästa steg: prova Kortare för att se stycke två skalat ner, eller A/B på ämnesraden."
    }
  }
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
  draft: {
    subject: "Servicelöftet på er nya hemsida",
    body:
      "Hej Mikael,\n\n" +
      "Jag såg att ni lagt om hemsidan och lyfter fram service som ert löfte till kunderna. Det löftet syns snabbast i sådant kunder faktiskt möter på plats.\n\n" +
      "En hjärtstartare synlig i entrén och en HLR-utbildning för teamet är precis den sortens detalj, och den går att nämna i löftet ni redan skrivit.\n\n" +
      "Vill du ha ett kort förslag du kan väga in i servicelöftet?\n\n" +
      "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
  },
  resultat: {
    shorter: {
      new_version:
        "Hej Mikael,\n\n" +
        "Ni lyfter fram service på nya hemsidan. En hjärtstartare i entrén och en HLR-utbildning för teamet är den sortens detalj som syns direkt.\n\n" +
        "Vill du ha ett förslag du kan väga in i löftet?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Kortare: bakgrundsmeningen om varför är struken, kärnan (synlig hjärtstartare, HLR för teamet) står kvar i en mening.",
      subject_suggestions: ["Kort fråga om servicelöftet", "Till Viksund om entrén"]
    },
    rewrite: {
      new_version:
        "Hej Mikael,\n\n" +
        "Ett servicelöfte på hemsidan är ett löfte kunder minns när de går genom entrén, inte bara när de läser texten.\n\n" +
        "Många byggbolag skriver om service utan att ha något konkret att peka på i lokalen. En hjärtstartare synlig i entrén och en HLR-utbildning för teamet är ett sätt att göra löftet påtagligt, inte bara skrivet.\n\n" +
        "Är det värt ett kort förslag?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Ny struktur: Observation → Problem (löfte utan motsvarighet i lokalen) → Idé → Fråga. Annat öppningsord än originalet.",
      subject_suggestions: ["Ett löfte som syns i entrén", "Service på hemsidan, och i lokalen"]
    },
    improve: {
      new_version:
        "Hej Mikael,\n\n" +
        "Ni har lyft fram service som löfte på nya hemsidan. En hjärtstartare synlig i entrén och en HLR-utbildning för teamet gör det löftet konkret för alla som går in genom dörren.\n\n" +
        "Ska jag skicka ett förslag du kan väga in i löftet?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Förbättrad: två stycken i stället för tre, aktiv röst, och CTA:n skärpt till en direkt fråga.",
      subject_suggestions: ["Gör servicelöftet synligt", "En detalj till entrén"]
    },
    personalize: {
      new_version:
        "Hej Mikael,\n\n" +
        "Att skriva 'service' på hemsidan är enkelt. Det som gör löftet trovärdigt är sådant kunder ser med egna ögon när de kliver in, inte det som står i texten.\n\n" +
        "En hjärtstartare synlig i entrén och en HLR-utbildning för teamet är precis den sortens detalj, och den kostar er inget att nämna i löftet ni redan skrivit.\n\n" +
        "Vill du ha ett kort förslag du kan väga in i servicelöftet?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Personaliserad kring den faktiska iakttagelsen: ett skrivet löfte utan synlig motsvarighet i lokalen, inte bara att hemsidan bytts.",
      subject_suggestions: ["Det som gör löftet trovärdigt", "Till Viksund om service i praktiken"]
    },
    translate: {
      new_version:
        "Hi Mikael,\n\n" +
        "I noticed you have updated your website and now highlight service as your promise to customers. That promise shows fastest in what customers actually see on site.\n\n" +
        "A defibrillator visible in the entrance and CPR training for the team is exactly that kind of detail, and it fits naturally into the promise you already wrote.\n\n" +
        "Would you like a short proposal you can weigh into the service promise?\n\n" +
        "Best regards,\nAnna, Hjärtsäker AB",
      explanation: "Engelsk version av hela mejlet. 'Servicelöfte' blir 'service promise' snarare än en ordagrann översättning.",
      subject_suggestions: ["The service promise on your new site"]
    },
    ab_variants: {
      new_version:
        "Variant A (löftet blir påtagligt):\n" +
        "Hej Mikael,\n\n" +
        "Ni lyfter fram service på nya hemsidan. En hjärtstartare synlig i entrén och en HLR-utbildning för teamet gör det löftet påtagligt för alla som kliver in.\n\n" +
        "Vill du ha ett kort förslag du kan väga in i löftet?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB\n\n" +
        "Variant B (nyfikenhet):\n" +
        "Hej Mikael,\n\n" +
        "Har ni redan en hjärtstartare i lokalen, eller är det något som hamnat på 'ska göra'-listan sedan hemsidan skrevs om?\n\n" +
        "Vi löser båda delarna i ett svep: hjärtstartare i entrén och HLR-utbildning för teamet.\n\n" +
        "Värt en kort fråga?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Två vinklar: A kopplar direkt till löftet på hemsidan, B öppnar med en nyfiken fråga om nuläget. Olika öppning och olika CTA.",
      subject_suggestions: ["Löftet, påtagligt (A)", "En fråga om nuläget (B)"]
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
        "Jag såg att ni lagt om hemsidan och lyfter fram service som ert löfte till kunderna. Det löftet syns snabbast i sådant kunder faktiskt möter på plats.\n\n" +
        "En hjärtstartare synlig i entrén och en HLR-utbildning för teamet är precis den sortens detalj, och den går att nämna i löftet ni redan skrivit.\n\n" +
        "Vill du ha ett kort förslag du kan väga in i servicelöftet?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Bedömning: kopplingen mellan hemsidans servicelöfte och ett konkret objekt i entrén är stark och icke-uppenbar, den bär hela mejlet. Sista stycket före CTA:n är en aning defensivt formulerat ('går att nämna') och kan bytas till ett rakare påstående. Ämnesraden är tydlig men säger inte vad avsändaren erbjuder.",
      subject_suggestions: [],
      confidence_tips: "Nästa steg: prova Förbättra för en rakare mening före CTA:n, eller Kortare om mejlet ska ner till tre rader."
    }
  }
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
  draft: {
    subject: "Den nya lokalen hos Hammarnäs",
    body:
      "Hej Sara,\n\n" +
      "Grattis till den nya, större lokalen. Med fler kvadratmeter och 31 anställda på plats blir avstånd till en hjärtstartare snabbt en annan fråga än i den gamla lokalen.\n\n" +
      "Vi monterar en hjärtstartare i den nya lokalen och håller en HLR-genomgång för hela teamet, uppdelad på två pass så att produktionen inte behöver stå still.\n\n" +
      "Vill du att jag skickar ett förslag anpassat efter de 31 anställda?\n\n" +
      "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
  },
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
        "Grattis till den nya, större lokalen. Med fler kvadratmeter och 31 anställda på plats blir avstånd till en hjärtstartare snabbt en annan fråga än i den gamla lokalen.\n\n" +
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
  draft: {
    subject: "Tre nya i produktionen hos Granstrand",
    body:
      "Hej Erik,\n\n" +
      "Jag såg att ni har tre annonser ute till produktionen samtidigt. Fler på golvet är bra, men det betyder också fler att introducera i säkerhetsrutinerna innan de står vid maskinerna själva.\n\n" +
      "Vi sätter en hjärtstartare i produktionslokalen och lägger en HLR-genomgång direkt i introduktionen, så att den följer med automatiskt för alla nya.\n\n" +
      "Vill du att HLR-genomgången läggs in i introduktionen för de nya?\n\n" +
      "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
  },
  resultat: {
    shorter: {
      new_version:
        "Hej Erik,\n\n" +
        "Tre annonser ute till produktionen betyder tre nya att introducera i säkerhetsrutinerna. Vi lägger en HLR-genomgång direkt i introduktionen och sätter en hjärtstartare i lokalen.\n\n" +
        "Vill du att den läggs in för de nya redan nu?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Kortare: två stycken slås ihop till ett, och upprepningen av 'innan de står vid maskinerna själva' är struken eftersom poängen redan finns i 'säkerhetsrutinerna'.",
      subject_suggestions: ["Kort fråga om introduktionen", "Granstrand: tre nya i produktionen"]
    },
    rewrite: {
      new_version:
        "Hej Erik,\n\n" +
        "Tre samtidiga rekryteringar till produktionen är tre introduktioner som ska hålla samma standard, oavsett vem som håller i dem den veckan.\n\n" +
        "Vi löser en del av det: en hjärtstartare i lokalen och en HLR-genomgång som ligger fast i introduktionen, inte beroende av vem som visar runt.\n\n" +
        "Är det värt att lägga in redan för de tre som börjar nu?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Ny struktur: problemet (introduktioner som varierar i kvalitet) före lösningen, i stället för observation följt av erbjudande.",
      subject_suggestions: ["Samma introduktion, oavsett vem", "En fråga om introduktionen"]
    },
    improve: {
      new_version:
        "Hej Erik,\n\n" +
        "Ni har tre annonser ute till produktionen samtidigt. Fler på golvet betyder fler att introducera i säkerhetsrutinerna innan de står vid maskinerna själva.\n\n" +
        "Vi sätter en hjärtstartare i lokalen och lägger en HLR-genomgång direkt i introduktionen, så att den följer med automatiskt för alla nya.\n\n" +
        "Ska HLR-genomgången läggas in i introduktionen för de tre som börjar nu?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Förbättrad: CTA:n skärpt till en direkt fråga med siffran tre kvar, vilket gör den konkret i stället för generell.",
      subject_suggestions: ["In i introduktionen redan nu", "Säkerheten för de tre nya"]
    },
    personalize: {
      new_version:
        "Hej Erik,\n\n" +
        "Tre annonser ute samtidigt säger något: ni har antagligen redan en introduktion som ska hinna med mycket på kort tid. Säkerhetsdelen är lätt att den hamnar sist i en sådan lista, trots att den borde ligga tidigt.\n\n" +
        "Vi sätter en hjärtstartare i produktionslokalen och lägger en HLR-genomgång direkt i introduktionen, så att den inte beror på vem som visar runt den veckan.\n\n" +
        "Vill du att HLR-genomgången läggs in i introduktionen för de nya?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Personaliserad kring en icke-uppenbar följd av tre samtidiga rekryteringar: en pressad introduktion där säkerhet lätt hamnar sist.",
      subject_suggestions: ["Det som lätt hamnar sist i introduktionen", "Till Granstrand om de tre nya"]
    },
    translate: {
      new_version:
        "Hi Erik,\n\n" +
        "I saw you have three job ads out for production at the same time. More people on the floor also means more people to introduce to safety routines before they are on their own by the machines.\n\n" +
        "We install a defibrillator in the production area and build CPR training directly into the induction, so it follows automatically for every new hire.\n\n" +
        "Would you like the CPR training added to the induction for the new hires?\n\n" +
        "Best regards,\nAnna, Hjärtsäker AB",
      explanation: "Engelsk version. 'Introduktion' blir 'induction', den vanliga termen i engelskt HR-språk snarare än en bokstavlig översättning.",
      subject_suggestions: ["Three new hires at Granstrand"]
    },
    ab_variants: {
      new_version:
        "Variant A (introduktionen som grund):\n" +
        "Hej Erik,\n\n" +
        "Tre annonser ute till produktionen betyder tre introduktioner som ska hålla samma standard. Vi lägger en HLR-genomgång direkt i introduktionen och sätter en hjärtstartare i lokalen.\n\n" +
        "Vill du att den läggs in för de nya redan nu?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB\n\n" +
        "Variant B (praktisk nyfikenhet):\n" +
        "Hej Erik,\n\n" +
        "Ingår HLR i introduktionen ni kör för nya i produktionen, eller är det något som tas separat, om alls?\n\n" +
        "Vi kan lägga in både hjärtstartare och genomgång så att det följer med automatiskt.\n\n" +
        "Värt en kort fråga?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Två vinklar: A utgår från standarden i introduktionen, B ställer en rak fråga om hur det ser ut idag. Olika öppning och olika CTA-ton.",
      subject_suggestions: ["Samma standard för alla tre (A)", "Ingår HLR redan? (B)"]
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
        "Jag såg att ni har tre annonser ute till produktionen samtidigt. Fler på golvet är bra, men det betyder också fler att introducera i säkerhetsrutinerna innan de står vid maskinerna själva.\n\n" +
        "Vi sätter en hjärtstartare i produktionslokalen och lägger en HLR-genomgång direkt i introduktionen, så att den följer med automatiskt för alla nya.\n\n" +
        "Vill du att HLR-genomgången läggs in i introduktionen för de nya?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Bedömning: kopplingen mellan tre samtidiga rekryteringar och introduktionens innehåll är stark och konkret, siffran tre gör mejlet specifikt. Första stycket är en aning långt, meningen om att stå vid maskinerna själva upprepar det 'säkerhetsrutinerna' redan sagt. CTA:n är tydlig och lätt att svara ja eller nej på.",
      subject_suggestions: [],
      confidence_tips: "Nästa steg: prova Kortare för att se första stycket kortat, eller Analysera igen efter en omskrivning."
    }
  }
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
  draft: {
    subject: "Bytet av affärssystem hos Sjöhaga",
    body:
      "Hej Lina,\n\n" +
      "Jag läste inlägget om att ni bytt affärssystem. När ett sånt byte väl är gjort brukar man passa på att se över annat som ändå legat och väntat, innan allt sätter sig igen.\n\n" +
      "Vi sätter en hjärtstartare i lagerlokalen och lägger en HLR-genomgång som går att boka digitalt, samma väg som ni redan lagt om till för annat.\n\n" +
      "Vill du ha ett förslag du kan boka direkt digitalt?\n\n" +
      "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
  },
  resultat: {
    shorter: {
      new_version:
        "Hej Lina,\n\n" +
        "Ni har precis bytt affärssystem. Ett sånt byte brukar vara läget att också se över annat som väntat, som en hjärtstartare i lagerlokalen och en HLR-genomgång.\n\n" +
        "Vill du ha ett förslag du kan boka digitalt?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Kortare: bakgrunden om bloggen är struken, systembytet och kopplingen till hjärtstartaren står kvar i en mening.",
      subject_suggestions: ["Kort fråga om lagerlokalen", "Sjöhaga: efter systembytet"]
    },
    rewrite: {
      new_version:
        "Hej Lina,\n\n" +
        "Ett systembyte är sällan bara ett system. Det brukar vara den punkt där man ändå går igenom vad mer som legat och väntat.\n\n" +
        "Hjärtstartare i lagerlokalen och en HLR-genomgång hör ofta till den listan. Vi löser båda, och genomgången går att boka digitalt, precis som ni redan lagt om till för annat.\n\n" +
        "Värt att titta på nu medan ni ändå är i det läget?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Ny struktur: ett generellt konstaterande om systembyten som öppning, i stället för att direkt referera bloggen.",
      subject_suggestions: ["Sällan bara ett system", "En fråga medan ni ändå är i läget"]
    },
    improve: {
      new_version:
        "Hej Lina,\n\n" +
        "Jag läste att ni bytt affärssystem. Ett sånt byte brukar vara läget att också se över annat som legat och väntat.\n\n" +
        "Vi sätter en hjärtstartare i lagerlokalen och lägger en HLR-genomgång som går att boka digitalt, samma väg som ni redan lagt om till.\n\n" +
        "Vill du ha ett förslag du kan boka direkt?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation: "Förbättrad: den överflödiga bisatsen om att allt 'sätter sig igen' är struken, och CTA:n kortad till 'boka direkt'.",
      subject_suggestions: ["Läget efter systembytet", "Digital bokning hos Sjöhaga"]
    },
    personalize: {
      new_version:
        "Hej Lina,\n\n" +
        "Att skriva om systembytet på bloggen säger att ni gillar att göra saker ordentligt och visa hur det går till, inte bara byta i det tysta. Det säger också att digitala lösningar är vägen ni väljer när ni kan.\n\n" +
        "En hjärtstartare i lagerlokalen och en HLR-genomgång som går att boka digitalt passar samma linje.\n\n" +
        "Vill du ha ett förslag du kan boka direkt digitalt?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Personaliserad kring en icke-uppenbar detalj: att de valt att skriva om bytet offentligt säger något om hur de vill göra saker, inte bara att bytet skedde.",
      subject_suggestions: ["Samma linje som systembytet", "Till Sjöhaga om digital bokning"]
    },
    translate: {
      new_version:
        "Hi Lina,\n\n" +
        "I read that you switched business systems. A change like that is usually the moment when other things that have been waiting also get looked at.\n\n" +
        "We install a defibrillator in the warehouse and set up CPR training that can be booked digitally, the same route you already moved other things to.\n\n" +
        "Would you like a proposal you can book directly online?\n\n" +
        "Best regards,\nAnna, Hjärtsäker AB",
      explanation: "Engelsk version. 'Lagerlokalen' blir 'warehouse' snarare än en ordagrann 'storage premises'.",
      subject_suggestions: ["After the system switch at Sjöhaga"]
    },
    ab_variants: {
      new_version:
        "Variant A (rätt läge):\n" +
        "Hej Lina,\n\n" +
        "Ett systembyte brukar vara läget att också se över annat som legat och väntat. Hjärtstartare i lagerlokalen och en HLR-genomgång hör ofta dit.\n\n" +
        "Vill du ha ett förslag du kan boka direkt digitalt?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB\n\n" +
        "Variant B (samma linje):\n" +
        "Hej Lina,\n\n" +
        "Ni valde en digital väg för affärssystemet. Vi erbjuder samma sak för HLR-genomgången: bokas digitalt, ingen extra administration.\n\n" +
        "Värt att titta på?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Två vinklar: A utgår från tajmingen efter bytet, B kopplar till att de redan valt digitala lösningar. Olika öppning, olika betoning i CTA:n.",
      subject_suggestions: ["Rätt läge efter bytet (A)", "Samma digitala linje (B)"]
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
        "Jag läste inlägget om att ni bytt affärssystem. När ett sånt byte väl är gjort brukar man passa på att se över annat som ändå legat och väntat, innan allt sätter sig igen.\n\n" +
        "Vi sätter en hjärtstartare i lagerlokalen och lägger en HLR-genomgång som går att boka digitalt, samma väg som ni redan lagt om till för annat.\n\n" +
        "Vill du ha ett förslag du kan boka direkt digitalt?\n\n" +
        "Vänliga hälsningar,\nAnna, Hjärtsäker AB",
      explanation:
        "Bedömning: kopplingen mellan systembytet och 'rätt läge att se över annat' är rimlig men något generisk, den skulle kunna gälla vilket bolag som helst efter ett systembyte. Det digitala bokningserbjudandet är däremot en stark, specifik koppling till just den här signalen och kunde lyftas fram tidigare i mejlet. CTA:n är bra och låg tröskel.",
      subject_suggestions: [],
      confidence_tips: "Nästa steg: prova Personalisera för att flytta fram den digitala kopplingen, eller Skriv om med den som öppning."
    }
  }
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
  draft: {
    subject: "Servicelöftet till hyresgästerna hos Almnäs",
    body:
      "Hej Jonas,\n\n" +
      "Jag såg er nya tjänstesida och löftet om service till hyresgästerna. Ett sånt löfte märks mest i sådant som finns på plats i huset, inte bara i texten om det.\n\n" +
      "En hjärtstartare i fastighetens gemensamma utrymme och en HLR-genomgång för personalen är precis den sortens sak, och går att lyfta fram i löftet ni redan skrivit.\n\n" +
      "Vill du ha ett förslag att väga in i servicelöftet till hyresgästerna?\n\n" +
      "Vänliga hälsningar,\nAnna, Hjärtsäker AB"
  },
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
