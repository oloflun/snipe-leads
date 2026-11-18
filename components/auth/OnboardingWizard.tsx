"use client";

import { ArrowLeft, ArrowRight, Check, ExternalLink, Loader2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import { Logo } from "@/components/Logo";
import { etikett } from "@/components/ui";
import { saveBusinessContext } from "@/lib/actions/onboarding";
import { signOut } from "@/lib/actions/auth";
import { BRANSCHER, type Bransch } from "@/lib/bransch";
import { useLocale, type Localized } from "@/lib/i18n";
import { formateraOrgnr, orgnrFel } from "@/lib/orgnr";
import { PAKET, type Paket } from "@/lib/pricing";
import { cn } from "@/lib/utils";

/**
 * Onboardingen som ett flöde i fem steg — företaget, branschen,
 * kontaktpersonen, målgruppen, paketet — i stället för ett formulär med allt
 * på en gång.
 *
 * Målgruppen ligger FÖRE paketet och visas alltid, med enbart valfria fält:
 * paketsteget bär villkoren och inskickningen och ska förbli sista steget, och
 * ett steg som dyker upp eller försvinner beroende på ett senare val hade gjort
 * stegraden opålitlig. Utan leadsagenten i paketet används svaren helt enkelt
 * inte.
 *
 * ## Varför steg och inte ett långt formulär
 *
 * EN fråga i taget, synligt var man är, och det som redan är ifyllt står kvar
 * när man går tillbaka. Svaren härifrån är bokstavligen det agenterna säljer
 * och svarar utifrån.
 *
 * ## Vad som händer när man trycker "Öppna arbetsytan"
 *
 * Allt går till `saveBusinessContext` (lib/actions/onboarding.ts) i ETT
 * anrop: affärskontexten sparas, arbetsytan får företagets namn, paketet sätts,
 * arbetsytan får sin egen backend-tenant, agenterna får standardinställningar
 * ur kundens eget underlag, och kontaktpersonen + orgnr landar i vårt
 * kundregister. Stegen innan dess rör aldrig servern — den som stänger fliken
 * mitt i har inte skrivit något.
 *
 * ## Det den visuella genomgången 2026-11-18 ändrade, och varför
 *
 * - Formulären har `noValidate` och validerar själva. Webbläsarens egen
 *   kontroll av `type="url"` nekade "exempel.se" utan protokoll, den inmatning
 *   serversidan uttryckligen godtar, och dess bubbla kom på webbläsarens språk
 *   medan vårt eget, gamla fel stod kvar under.
 * - ALLA fel i ett steg visas på en gång, vid sitt fält, och första felet får
 *   fokus. Förut kom ett i taget, längst ner.
 * - Ett nytt steg börjar överst med fokus på rubriken. Efter det långa
 *   målgruppssteget öppnades paketsteget annars nedscrollat, med rubriken
 *   ovanför skärmen.
 * - Etiketterna är brödtext i läsbar storlek (`etikett`), inte spärrad mono
 *   i 10,5 px, och fälten är 16 px så att iOS inte zoomar in (DESIGN.md).
 *
 * Tvåspråkigt: texten bor i `T` och `STEG`. Branschvärdet som skickas till
 * servern är alltid det svenska ur lib/bransch.ts; bara etiketten översätts.
 */

const STEG = [
  {
    kicker: { sv: "Företaget", en: "Company" },
    rubrik: { sv: "Berätta om företaget", en: "Tell us about the company" }
  },
  {
    kicker: { sv: "Bransch", en: "Industry" },
    rubrik: { sv: "Vilken bransch är ni i?", en: "Which industry are you in?" }
  },
  {
    kicker: { sv: "Kontaktperson", en: "Contact person" },
    rubrik: { sv: "Vem pratar vi med hos er?", en: "Who do we talk to at your company?" }
  },
  {
    kicker: { sv: "Målgrupp", en: "Target group" },
    rubrik: { sv: "Vilka bolag vill Iris hitta?", en: "Which companies should Iris find?" }
  },
  {
    kicker: { sv: "Paket", en: "Plan" },
    rubrik: { sv: "Välj era agenter", en: "Choose your agents" }
  }
] as const satisfies readonly { kicker: Localized; rubrik: Localized }[];

const PLACEHOLDER = {
  foretag: { sv: "Exempelbolaget AB", en: "Example Company AB" },
  orgnr: "556824-9022",
  webbplats: "exempel.se",
  produkt: {
    sv: "Utbildning i hjärt-lungräddning och första hjälpen för arbetsplatser",
    en: "CPR and first aid training for workplaces"
  },
  branscher: { sv: "Bygg, Fastighetsförvaltning", en: "Construction, Property management" },
  orter: { sv: "Göteborg, Mölndal", en: "Göteborg, Mölndal" },
  roller: { sv: "VD, Inköpschef", en: "CEO, Head of purchasing" },
  undvik: { sv: "Offentlig sektor, Konkurrent AB", en: "Public sector, Competitor AB" },
  fokus: {
    sv: "Vi vill helst nå bolag som redan köpt hjärtstartare men saknar utbildning",
    en: "We would rather reach companies that already bought a defibrillator but lack training"
  },
  erbjudanden: {
    sv: "Första utbildningstillfället utan kostnad för arbetsplatser med upp till 20 anställda. Vill de veta mer bokar vi ett kort samtal.",
    en: "The first training session free of charge for workplaces with up to 20 employees. If they want to know more, we book a short call."
  }
} as const;

/** Etiketten per bransch. Värdet som sparas är alltid den svenska nyckeln. */
const BRANSCH_ETIKETT: Record<Bransch, Localized> = {
  "Bygg & hantverk": { sv: "Bygg & hantverk", en: "Construction & trades" },
  "Industri & tillverkning": { sv: "Industri & tillverkning", en: "Industry & manufacturing" },
  "IT & mjukvara": { sv: "IT & mjukvara", en: "IT & software" },
  "E-handel & detaljhandel": { sv: "E-handel & detaljhandel", en: "E-commerce & retail" },
  Utbildning: { sv: "Utbildning", en: "Education" },
  "Vård & omsorg": { sv: "Vård & omsorg", en: "Health & social care" },
  "Hotell & restaurang": { sv: "Hotell & restaurang", en: "Hotels & restaurants" },
  "Transport & logistik": { sv: "Transport & logistik", en: "Transport & logistics" },
  Fastighet: { sv: "Fastighet", en: "Real estate" },
  "Ekonomi & juridik": { sv: "Ekonomi & juridik", en: "Finance & legal" },
  "Marknadsföring & media": { sv: "Marknadsföring & media", en: "Marketing & media" },
  Konsulttjänster: { sv: "Konsulttjänster", en: "Consulting" },
  "Offentlig sektor & föreningar": { sv: "Offentlig sektor & föreningar", en: "Public sector & associations" },
  Annat: { sv: "Annat", en: "Other" }
};

const T = {
  felForetag: { sv: "Fyll i företagets namn.", en: "Enter the company name." },
  felOrgnrTomt: { sv: "Fyll i organisationsnumret.", en: "Enter the registration number." },
  felOrgnrLangd: {
    sv: "Ett organisationsnummer har tio siffror. Skriv det som 556824-9022.",
    en: "A registration number has ten digits. Write it as 556824-9022."
  },
  felOrgnrKontroll: {
    sv: "Kontrollsiffran stämmer inte, vilket nästan alltid betyder ett skrivfel. Kontrollera numret mot en faktura eller registreringsbeviset.",
    en: "The check digit does not match, which almost always means a typo. Check the number against an invoice or the certificate of registration."
  },
  felWebbplats: {
    sv: "Fyll i webbplatsen. Det är den agenterna läser för att förstå er.",
    en: "Enter the website. It is what the agents read to understand you."
  },
  felWebbadress: {
    sv: "Adressen går inte att läsa. Skriv den som exempel.se.",
    en: "The address cannot be read. Write it as example.com."
  },
  felProdukt: {
    sv: "Skriv en rad om vad ni säljer. Det är det agenterna ska sälja.",
    en: "Write a line about what you sell. That is what the agents will sell."
  },
  felGata: { sv: "Fyll i gatuadressen fakturan ska till.", en: "Enter the street address for the invoice." },
  felPostnummer: { sv: "Postnumret ska ha fem siffror.", en: "The postcode must have five digits." },
  felOrt: { sv: "Fyll i orten.", en: "Enter the city." },
  felBransch: {
    sv: "Välj den bransch som ligger närmast. Annat funkar också.",
    en: "Pick the closest industry. Other works too."
  },
  felKontaktNamn: { sv: "Fyll i vem som är kontaktperson hos er.", en: "Enter who your contact person is." },
  felKontaktMejl: { sv: "Fyll i kontaktpersonens e-postadress.", en: "Enter the contact person's email address." },
  felHeltal: {
    sv: "Skriv antalet som ett heltal, eller lämna fältet tomt.",
    en: "Enter the number as a whole number, or leave the field empty."
  },
  felMinMax: {
    sv: "Minsta antal anställda är större än största.",
    en: "The minimum number of employees is larger than the maximum."
  },
  felVillkor: {
    sv: "Kryssa i att ni godkänner villkoren för att kunna starta gratisperioden.",
    en: "Tick the box to accept the terms so you can start the free period."
  },
  felSpara: { sv: "Kunde inte spara. Försök igen.", en: "Could not save. Try again." },
  tillStartsidan: { sv: "Snajp, till startsidan", en: "Snajp, back to home" },
  stegIUppstarten: { sv: "Steg i uppstarten", en: "Setup steps" },
  klart: { sv: "Klart", en: "Done" },
  nu: { sv: "Nu", en: "Now" },
  vantar: { sv: "Väntar", en: "Waiting" },
  steg: { sv: "Steg", en: "Step" },
  av: { sv: "av", en: "of" },
  loggaUt: { sv: "Logga ut", en: "Sign out" },
  intro0: {
    sv: "Agenterna läser er webbplats och lär sig resten själva: hur ni beskriver er, vad ni säljer och vilka ord er bransch använder.",
    en: "The agents read your website and learn the rest on their own: how you describe yourselves, what you sell and which words your industry uses."
  },
  foretag: { sv: "Företagets namn", en: "Company name" },
  foretagHint: {
    sv: "Så heter er arbetsyta, och så står ni som avsändare i sidfoten på utskicken.",
    en: "This names your workspace, and it is how you appear as sender in the footer of the emails."
  },
  orgnr: { sv: "Organisationsnummer", en: "Company registration number" },
  orgnrHint: {
    sv: "Identifierar er, och krävs enligt lag i sidfoten på varje utskick.",
    en: "Identifies you, and is required by law in the footer of every email sent."
  },
  testarbetsyta: { sv: "Testarbetsyta", en: "Test workspace" },
  testarbetsytaText: {
    sv: ": hoppa över organisationsnumret. Bara för test, arbetsytan märks som testkund.",
    en: ": skip the registration number. For testing only; the workspace is marked as a test customer."
  },
  webbplats: { sv: "Webbplats", en: "Website" },
  webbplatsHint: {
    sv: "Den här läser agenterna. Utan den vet de bara ert nummer.",
    en: "This is what the agents read. Without it they only know your number."
  },
  produkt: { sv: "Vad ni säljer", en: "What you sell" },
  produktHint: {
    sv: "En rad räcker. Agenterna fyller på från sajten.",
    en: "One line is enough. The agents fill in the rest from the site."
  },
  faktura: { sv: "Faktureringsadress", en: "Billing address" },
  fakturaHint: {
    sv: "Hit går fakturan. Först efter gratisperioden, alltid i efterhand.",
    en: "Where the invoice goes. Only after the free period, always in arrears."
  },
  postnummer: { sv: "Postnummer", en: "Postcode" },
  ort: { sv: "Ort", en: "City" },
  intro1: {
    sv: "Branschen ger agenterna rätt ordförråd från första dagen. En offert i bygg låter inte som en i vården.",
    en: "The industry gives the agents the right vocabulary from day one. A quote in construction does not sound like one in healthcare."
  },
  bransch: { sv: "Bransch", en: "Industry" },
  intro2: {
    sv: "Er kontakt hos oss är en människa, inte en kö. Vi hör av oss när agenterna behöver ett beslut, och innan er gratisperiod tar slut.",
    en: "Your contact with us is a person, not a queue. We get in touch when the agents need a decision, and before your free period ends."
  },
  namn: { sv: "Namn", en: "Name" },
  namnHint: { sv: "Den hos er som äger frågan om agenterna.", en: "The person at your company who owns the agents." },
  roll: { sv: "Roll (valfritt)", en: "Role (optional)" },
  rollHint: {
    sv: "Till exempel VD, marknadschef eller kontorsansvarig.",
    en: "For example CEO, marketing manager or office manager."
  },
  rollExempel: { sv: "VD", en: "CEO" },
  epost: { sv: "E-post", en: "Email" },
  epostHint: { sv: "Hit går besked som rör kontot. Aldrig reklam.", en: "Account notices go here. Never advertising." },
  epostExempel: { sv: "anna@bolag.se", en: "anna@company.com" },
  telefon: { sv: "Telefon (valfritt)", en: "Phone (optional)" },
  telefonHint: { sv: "Om något brådskar ringer vi hellre än mejlar.", en: "If something is urgent we would rather call than email." },
  intro3: {
    sv: "Iris, leadsagenten, letar bolag inom de här ramarna. Allt är valfritt och går att ändra när som helst. Tomt betyder att Iris inte filtrerar på det. Utan leadsagenten i paketet används det inte.",
    en: "Iris, the leads agent, looks for companies within these limits. Everything is optional and can be changed at any time. Empty means Iris does not filter on it. Without the leads agent in your plan, none of this is used."
  },
  branscher: { sv: "Branscher att söka i", en: "Industries to search" },
  branscherHint: { sv: "Skilj med komma. Tomt = alla branscher.", en: "Separate with commas. Empty = all industries." },
  orter: { sv: "Orter och områden", en: "Towns and areas" },
  orterHint: { sv: "Skilj med komma. Tomt = hela Sverige.", en: "Separate with commas. Empty = all of Sweden." },
  anstMin: { sv: "Anställda, minst", en: "Employees, at least" },
  anstMinHint: { sv: "Tomt = ingen nedre gräns.", en: "Empty = no lower limit." },
  anstMax: { sv: "Anställda, högst", en: "Employees, at most" },
  anstMaxHint: { sv: "Tomt = ingen övre gräns.", en: "Empty = no upper limit." },
  roller: { sv: "Roller att nå", en: "Roles to reach" },
  rollerHint: { sv: "Vem mejlet ska till. Skilj med komma.", en: "Who the email should go to. Separate with commas." },
  undvik: { sv: "Undvik", en: "Avoid" },
  undvikHint: {
    sv: "Branscher eller bolag Iris ska hoppa över. Skilj med komma.",
    en: "Industries or companies Iris should skip. Separate with commas."
  },
  fokus: { sv: "Särskilt fokus", en: "Particular focus" },
  fokusHint: {
    sv: "En nisch, ett segment ni vill åt, eller något Iris ska veta om vilka som brukar köpa.",
    en: "A niche, a segment you want to reach, or something Iris should know about who tends to buy."
  },
  erbjudanden: { sv: "Erbjudandet i utskicken", en: "The offer in the emails" },
  erbjudandenHint: {
    sv: "Det Iris ska erbjuda bolagen: vad de får, vad det kostar och hur de går vidare. Har ni flera, skriv ett per stycke med en tom rad emellan, så testar Iris dem mot varandra. Iris anpassar erbjudandet till varje bolags verksamhet, och ni ändrar det under Leads › Erbjudanden.",
    en: "What Iris should offer the companies: what they get, what it costs and how they take the next step. If you have several, write one per paragraph with a blank line in between, and Iris tests them against each other. Iris adapts the offer to each company's business, and you change it under Leads › Offers."
  },
  intro4: {
    sv: "Alla paket börjar med två månader gratis, utan betalningsuppgifter nu. Byta paket går när som helst under Inställningar → Plan.",
    en: "Every plan starts with two months free, and no payment details now. You can change plan at any time under Settings → Plan."
  },
  paket: { sv: "Paket", en: "Plan" },
  popularast: { sv: "Populärast", en: "Most popular" },
  prisVidKontakt: { sv: "Pris vid kontakt", en: "Price on request" },
  fran: { sv: "från", en: "from" },
  krManad: { sv: "kr/mån", en: "SEK/month" },
  exklMoms: { sv: "Priserna är exklusive moms.", en: "Prices exclude VAT." },
  osakra: { sv: "Osäkra?", en: "Not sure?" },
  utforska: { sv: "Utforska agenterna i demon", en: "Explore the agents in the demo" },
  nyFlik: {
    sv: "Den öppnas i en ny flik, det här flödet står kvar.",
    en: "It opens in a new tab, and this flow stays put."
  },
  gratisRubrik: { sv: "Testa gratis i 2 månader", en: "Try free for 2 months" },
  gratisText: {
    sv: "Gratisperioden börjar direkt och löper i två kalendermånader. Ingen bindningstid, inget kort. Vi hör av oss i god tid innan perioden tar slut, och att sluta kostar ingenting.",
    en: "The free period starts right away and runs for two calendar months. No minimum term and no card. We get in touch well before the period ends, and stopping costs nothing."
  },
  jagGodkanner: { sv: "Jag godkänner", en: "I accept the" },
  villkorLank: { sv: "användarvillkoren", en: "terms of service" },
  harTagitDel: { sv: "och har tagit del av", en: "and have read the" },
  angerrattLank: {
    sv: "informationen om distansavtalslagen och ångerrätt",
    en: "information about the Distance Contracts Act and the right of withdrawal"
  },
  notiser: { sv: "Notiser", en: "Notifications" },
  jaMejla: { sv: "Ja, mejla mig", en: "Yes, email me" },
  notiserText: {
    sv: "när ett nytt lead landar eller när kundtjänstagenten lämnar över ett ärende till en människa. Inget annat.",
    en: "when a new lead arrives or when the support agent hands a case over to a human. Nothing else."
  },
  tillbaka: { sv: "Tillbaka", en: "Back" },
  oppnaMed: { sv: "Öppna arbetsytan med", en: "Open the workspace with" },
  valtPaket: { sv: "valt paket", en: "the chosen plan" },
  laggerUpp: { sv: "Lägger upp er arbetsyta", en: "Setting up your workspace" },
  laggerUppText: {
    sv: "Vi sparar uppgifterna och ställer in agenterna. Det brukar gå på under en halv minut. Stäng inte fliken.",
    en: "We are saving your details and setting up the agents. It usually takes less than half a minute. Keep this tab open."
  },
  ingetSkickas: {
    sv: "Inget skickas till någon mottagare av det här. Agenterna läser er sajt och förbereder underlag. Utskick kräver att ni själva slår på det, och de tre första granskas alltid av en människa.",
    en: "Nothing is sent to anyone by this. The agents read your site and prepare material. Sending requires you to switch it on yourselves, and the first three are always reviewed by a human."
  },
  villkorNav: { sv: "Villkor och juridisk information", en: "Terms and legal information" },
  lankVillkor: { sv: "Användarvillkor", en: "Terms of service" },
  lankAngerratt: { sv: "Distansavtal & ångerrätt", en: "Distance contracts & withdrawal" },
  lankPolicy: { sv: "Integritetspolicy", en: "Privacy policy" },
  lankCookies: { sv: "Cookies", en: "Cookies" },
  fortsatt: { sv: "Fortsätt", en: "Continue" }
} satisfies Record<string, Localized>;

/** Besked från servern kommer på svenska; samma text i båda halvorna. */
function ordagrant(varde: string): Localized {
  return { sv: varde, en: varde };
}

/** lib/orgnr.ts svarar på svenska. Här får beskedet sitt engelska par. */
function orgnrBesked(fel: string): Localized {
  if (fel.startsWith("Fyll i")) return T.felOrgnrTomt;
  if (fel.startsWith("Kontrollsiffran")) return T.felOrgnrKontroll;
  // Längdfelet bär antalet siffror på svenska; engelskan säger regeln.
  return { sv: fel, en: T.felOrgnrLangd.en };
}

/** Heltal eller tomt — samma regel som serversidans tolkning. */
const HELTAL = /^\d*$/;
const EPOST = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** "exempel.se" → "https://exempel.se". Samma regel som serversidans. */
function medProtokoll(rå: string): string {
  const text = rå.trim();
  if (!text) return "";
  return /^https?:\/\//i.test(text) ? text : `https://${text}`;
}

function arWebbadress(rå: string): boolean {
  try {
    const { hostname } = new URL(medProtokoll(rå));
    return hostname.includes(".") && !hostname.endsWith(".");
  } catch {
    return false;
  }
}

/** "41101" → "411 01". Lämnar allt annat orört, så att felet syns. */
function formateraPostnummer(rå: string): string {
  const siffror = rå.replace(/\s/g, "");
  return /^\d{5}$/.test(siffror) ? `${siffror.slice(0, 3)} ${siffror.slice(3)}` : rå.trim();
}

type FaltId =
  | "foretag"
  | "orgnr"
  | "webbplats"
  | "produkt"
  | "faktGata"
  | "faktPostnr"
  | "faktOrt"
  | "kontaktNamn"
  | "kontaktMejl"
  | "anstMin"
  | "anstMax"
  | "villkor";

type Faltfel = Partial<Record<FaltId, Localized>>;

/** Fältens id i DOM:en, så att första felet kan få fokus. */
const faltDomId = (id: string) => `ob-${id}`;

export function OnboardingWizard({
  epost,
  namn,
  standardMalgrupp
}: Readonly<{
  epost?: string | null;
  namn?: string | null;
  /** Förifyllningen ur lib/snajp/standard.ts (server-only, därför en prop). */
  standardMalgrupp: { roller: string[]; anstallda: [number, number] };
}>) {
  const { text } = useLocale();
  const [steg, setSteg] = useState(0);
  /** Högsta steget som nåtts — stegraden låter en hoppa TILLBAKA, aldrig fram. */
  const [maxNatt, setMaxNatt] = useState(0);

  // Steg 1 — företaget.
  const [foretag, setForetag] = useState("");
  const [orgnr, setOrgnr] = useState("");
  const [testkund, setTestkund] = useState(false);
  const [webbplats, setWebbplats] = useState("");
  const [produkt, setProdukt] = useState("");

  // Steg 2 — branschen.
  const [bransch, setBransch] = useState<string | null>(null);

  // Steg 3 — kontaktpersonen. Mejlen förifylls med kontots adress: den som
  // registrerar sig ÄR oftast kontaktpersonen, och ett förifyllt sant värde
  // är motsatsen till de påhittade defaultvärden det gamla formuläret hade.
  const [kontaktNamn, setKontaktNamn] = useState(namn ?? "");
  const [kontaktRoll, setKontaktRoll] = useState("");
  const [kontaktMejl, setKontaktMejl] = useState(epost ?? "");
  const [kontaktTelefon, setKontaktTelefon] = useState("");

  // Steg 4 — målgruppen, leadsagentens grundfilter. Allt valfritt; tomt
  // betyder "inget filter". Roller och storlek förifylls med samma defaultar
  // som standardinställningarna annars hade skrivit. Fokus är fri text och
  // landar i produkttexten som "Särskilt fokus".
  const [branscher, setBranscher] = useState("");
  const [orter, setOrter] = useState("");
  const [anstMin, setAnstMin] = useState(String(standardMalgrupp.anstallda[0]));
  const [anstMax, setAnstMax] = useState(String(standardMalgrupp.anstallda[1]));
  const [roller, setRoller] = useState(standardMalgrupp.roller.join(", "));
  const [undvik, setUndvik] = useState("");
  const [fokus, setFokus] = useState("");
  // Erbjudandena utskicken bygger på (Anton 2026-10-25). Ett per stycke.
  const [erbjudanden, setErbjudanden] = useState("");

  // Steg 5 — paketet. Duo förvalt: det är paketet vi vill sälja (pricing.ts).
  const [paket, setPaket] = useState<Paket["id"]>("duo");
  const [notiser, setNotiser] = useState(true);
  // Faktureringsadressen — dit fakturan går efter gratisperioden. Krävs för
  // riktiga kunder; en testarbetsyta har inget bolag att fakturera.
  const [faktGata, setFaktGata] = useState("");
  const [faktPostnr, setFaktPostnr] = useState("");
  const [faktOrt, setFaktOrt] = useState("");
  // Villkorsgodkännandet. Startar okryssad med flit — ett förkryssat samtycke
  // är inget samtycke.
  const [villkor, setVillkor] = useState(false);

  /** Fel vid ett visst fält. Visas där, och försvinner när fältet ändras. */
  const [faltFel, setFaltFel] = useState<Faltfel>({});
  /** Fel som inte hör till ett fält: branschvalet och serverns besked. */
  const [error, setError] = useState<Localized | null>(null);
  const [isPending, startTransition] = useTransition();

  const valtPaket = useMemo(() => PAKET.find((p) => p.id === paket), [paket]);

  // Ett nytt steg börjar överst, med fokus på rubriken: skärmläsaren läser
  // vad steget heter, och tangentbordet står före första fältet. Jämförelsen
  // mot förra steget håller effekten stilla vid första renderingen.
  const rubrik = useRef<HTMLHeadingElement>(null);
  const forraSteget = useRef(steg);
  useEffect(() => {
    if (forraSteget.current === steg) return;
    forraSteget.current = steg;
    window.scrollTo({ top: 0 });
    rubrik.current?.focus({ preventScroll: true });
  }, [steg]);

  /** Sätter värdet och släcker fältets fel i samma tag. */
  function andra(id: FaltId, satt: (v: string) => void) {
    return (v: string) => {
      satt(v);
      setError(null);
      setFaltFel((fel) => {
        if (!fel[id]) return fel;
        const { [id]: _borta, ...kvar } = fel;
        return kvar;
      });
    };
  }

  function satFaltfel(id: FaltId, fel: Localized | null) {
    setFaltFel((nu) => {
      const { [id]: _borta, ...kvar } = nu;
      return fel ? { ...kvar, [id]: fel } : kvar;
    });
  }

  function vidBlurOrgnr() {
    if (!orgnr.trim()) return satFaltfel("orgnr", null);
    const fel = orgnrFel(orgnr);
    satFaltfel("orgnr", fel ? orgnrBesked(fel) : null);
    if (!fel) setOrgnr(formateraOrgnr(orgnr));
  }

  function vidBlurWebbplats() {
    if (!webbplats.trim()) return;
    if (arWebbadress(webbplats)) setWebbplats(medProtokoll(webbplats));
    else satFaltfel("webbplats", T.felWebbadress);
  }

  /** Alla fel i ett steg, i fältens ordning: det första får fokus. */
  function validera(vilket: number): { falt: Faltfel; allmant: Localized | null } {
    const falt: Faltfel = {};
    let allmant: Localized | null = null;
    if (vilket === 0) {
      if (foretag.trim().length < 2) falt.foretag = T.felForetag;
      if (!webbplats.trim()) falt.webbplats = T.felWebbplats;
      else if (!arWebbadress(webbplats)) falt.webbplats = T.felWebbadress;
      const orgFel = testkund ? null : orgnrFel(orgnr);
      if (orgFel) falt.orgnr = orgnrBesked(orgFel);
      if (!produkt.trim()) falt.produkt = T.felProdukt;
      if (!testkund) {
        if (!faktGata.trim()) falt.faktGata = T.felGata;
        if (!/^\d{5}$/.test(faktPostnr.replace(/\s/g, ""))) falt.faktPostnr = T.felPostnummer;
        if (!faktOrt.trim()) falt.faktOrt = T.felOrt;
      }
    }
    if (vilket === 1 && !bransch) allmant = T.felBransch;
    if (vilket === 2) {
      if (!kontaktNamn.trim()) falt.kontaktNamn = T.felKontaktNamn;
      if (!EPOST.test(kontaktMejl.trim())) falt.kontaktMejl = T.felKontaktMejl;
    }
    if (vilket === 3) {
      const min = anstMin.trim();
      const max = anstMax.trim();
      if (!HELTAL.test(min)) falt.anstMin = T.felHeltal;
      if (!HELTAL.test(max)) falt.anstMax = T.felHeltal;
      if (!falt.anstMin && !falt.anstMax && min && max && Number(min) > Number(max))
        falt.anstMax = T.felMinMax;
    }
    if (vilket === 4 && !villkor) falt.villkor = T.felVillkor;
    return { falt, allmant };
  }

  /** Sant när steget håller. Annars visas felen och första felet får fokus. */
  function haller(vilket: number): boolean {
    const { falt, allmant } = validera(vilket);
    setFaltFel(falt);
    setError(allmant);
    const forsta = Object.keys(falt)[0];
    if (forsta) {
      // Mitt i skärmen, inte i överkanten: annars klipps fältets etikett.
      const falt = document.getElementById(faltDomId(forsta));
      falt?.focus({ preventScroll: true });
      falt?.scrollIntoView({ block: "center" });
    }
    return !forsta && !allmant;
  }

  function nasta(event?: React.FormEvent) {
    event?.preventDefault();
    if (!haller(steg)) return;
    const ny = Math.min(steg + 1, STEG.length - 1);
    setSteg(ny);
    setMaxNatt((m) => Math.max(m, ny));
  }

  function gaTill(vilket: number) {
    setError(null);
    setFaltFel({});
    setSteg(vilket);
  }

  function skickaIn() {
    // Sista steget validerar som de andra — kryssrutan är inte dekor, och
    // serversidan gör om samma kontroll för den som kringgår det.
    if (!haller(4)) return;
    startTransition(async () => {
      const result = await saveBusinessContext({
        foretag,
        orgnr: testkund ? "" : orgnr,
        webbplats,
        produkt,
        fokus,
        erbjudanden,
        malgrupp: {
          branscher,
          orter,
          undvik,
          roller,
          anstalldaMin: anstMin,
          anstalldaMax: anstMax
        },
        bransch: bransch ?? "",
        kontaktNamn,
        kontaktRoll,
        kontaktMejl,
        kontaktTelefon,
        paket,
        testkund,
        notiser,
        villkorGodkanda: villkor,
        faktureringsadress: testkund
          ? null
          : { gata: faktGata, postnummer: faktPostnr, ort: faktOrt }
      });
      if (!result.success) {
        setError(result.error ? ordagrant(result.error) : T.felSpara);
      }
    });
  }

  const felText = error ? text(error) : null;
  const fel = (id: FaltId) => (faltFel[id] ? text(faltFel[id]) : null);

  return (
    <div className="grid grid-cols-12 md:gap-x-8">
      {/* Stegraden — Fraunces-numeraler i ochre, systemets signatur. */}
      <aside className="col-span-12 md:col-span-4 lg:col-span-3">
        <div className="flex items-center justify-between gap-4">
          <Link
            href="/"
            aria-label={text(T.tillStartsidan)}
            className="focus-ring inline-flex rounded-input"
          >
            <Logo />
          </Link>
          {/* Mobilen saknade vägen ut: utloggningen stod bara i sidospalten,
              som inte finns under md. */}
          <form action={signOut} className="md:hidden">
            <button
              type="submit"
              className="focus-ring min-h-11 rounded-input px-2 text-[0.875rem] font-medium text-ink-muted hover:text-ink"
            >
              {text(T.loggaUt)}
            </button>
          </form>
        </div>
        <div className="rule mt-4 text-ink" />

        <ol className="mt-8 hidden md:block" aria-label={text(T.stegIUppstarten)}>
          {STEG.map((s, i) => {
            const klar = i < steg;
            const aktiv = i === steg;
            const nabar = i <= maxNatt && i !== steg && !isPending;
            return (
              <li key={s.kicker.sv} className={cn("border-t border-ink/15", i === 0 && "border-t-0")}>
                <button
                  type="button"
                  disabled={!nabar}
                  aria-current={aktiv ? "step" : undefined}
                  onClick={() => gaTill(i)}
                  className={cn(
                    "focus-ring flex w-full items-baseline gap-4 rounded-input py-4 text-left",
                    nabar && "cursor-pointer hover:text-ink",
                    !nabar && "cursor-default"
                  )}
                >
                  <span
                    className={cn(
                      "font-display text-[2rem] leading-none",
                      aktiv ? "text-warning" : klar ? "text-ink" : "text-ink-subtle"
                    )}
                    aria-hidden
                  >
                    {i + 1}
                  </span>
                  <span className="min-w-0">
                    <span
                      className={cn(
                        "block text-[0.9375rem] font-semibold",
                        aktiv ? "text-ink" : klar ? "text-ink-muted" : "text-ink-subtle"
                      )}
                    >
                      {text(s.kicker)}
                    </span>
                    <span className="mt-0.5 flex items-center gap-1.5 text-[13px] text-ink-subtle">
                      {klar ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-moss" aria-hidden />
                          {text(T.klart)}
                        </>
                      ) : aktiv ? (
                        text(T.nu)
                      ) : (
                        text(T.vantar)
                      )}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>

        {/* Mobil: en rad + tunn mätare i stället för hela listan. */}
        <div className="mt-6 md:hidden">
          <p className={etikett}>
            {text(T.steg)} {steg + 1} {text(T.av)} {STEG.length}: {text(STEG[steg].kicker)}
          </p>
          <div className="mt-2 h-[3px] overflow-hidden rounded-full bg-ink/10">
            <div
              className="h-full rounded-full bg-ochre transition-[width] duration-300"
              style={{ width: `${((steg + 1) / STEG.length) * 100}%` }}
            />
          </div>
        </div>

        <form action={signOut} className="mt-8 hidden md:block">
          <button
            type="submit"
            className="focus-ring inline-flex min-h-8 items-center rounded-input text-[0.875rem] font-medium text-ink-muted hover:text-ink"
          >
            {text(T.loggaUt)}
          </button>
        </form>
      </aside>

      {/* Steginnehållet. key={steg} + animate-mejl-in: varje steg glider in
          med systemets egen rörelse. */}
      <div className="col-span-12 mt-10 md:col-span-8 md:mt-0 lg:col-span-9">
        <div key={steg} className="animate-mejl-in max-w-[720px]">
          <h1
            ref={rubrik}
            tabIndex={-1}
            className="font-display text-[clamp(1.75rem,3.5vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.02em] outline-none"
          >
            {text(STEG[steg].rubrik)}
          </h1>

          {steg === 0 ? (
            <form onSubmit={nasta} noValidate>
              <p className="mt-4 max-w-[62ch] text-[15px] leading-[1.65] text-ink-muted">
                {text(T.intro0)}
              </p>
              <div className="mt-8 grid grid-cols-12 gap-y-6 md:gap-x-8">
                <Falt
                  id="foretag"
                  label={text(T.foretag)}
                  hint={text(T.foretagHint)}
                  span="md:col-span-6"
                  value={foretag}
                  onChange={andra("foretag", setForetag)}
                  placeholder={text(PLACEHOLDER.foretag)}
                  fel={fel("foretag")}
                  autoComplete="organization"
                />
                {/* Text och inte type="url": webbläsarens egen kontroll nekar
                    "exempel.se" utan protokoll, som servern godtar. */}
                <Falt
                  id="webbplats"
                  label={text(T.webbplats)}
                  hint={text(T.webbplatsHint)}
                  span="md:col-span-6"
                  value={webbplats}
                  onChange={andra("webbplats", setWebbplats)}
                  onBlur={vidBlurWebbplats}
                  placeholder={PLACEHOLDER.webbplats}
                  fel={fel("webbplats")}
                  inputMode="url"
                  autoComplete="url"
                />
                <Falt
                  id="orgnr"
                  label={text(T.orgnr)}
                  hint={text(T.orgnrHint)}
                  span="md:col-span-6"
                  value={orgnr}
                  onChange={andra("orgnr", setOrgnr)}
                  onBlur={vidBlurOrgnr}
                  placeholder={PLACEHOLDER.orgnr}
                  fel={testkund ? null : fel("orgnr")}
                  disabled={testkund}
                  inputMode="numeric"
                  autoComplete="off"
                />
                <label className="col-span-12 flex items-start gap-3 border-t border-ink/15 pt-4 md:col-span-6">
                  <input
                    type="checkbox"
                    checked={testkund}
                    onChange={(e) => {
                      setTestkund(e.target.checked);
                      if (e.target.checked) {
                        satFaltfel("orgnr", null);
                        satFaltfel("faktGata", null);
                        satFaltfel("faktPostnr", null);
                        satFaltfel("faktOrt", null);
                      }
                    }}
                    className="focus-ring mt-1 h-4 w-4 shrink-0"
                  />
                  <span className="text-[14px] leading-6 text-ink-muted">
                    <span className="font-medium text-ink">{text(T.testarbetsyta)}</span>
                    {text(T.testarbetsytaText)}
                  </span>
                </label>
                {/* Flera rader: en mening om vad man säljer får inte plats i
                    ett enradsfält i halv bredd, och klipptes av. */}
                <Falt
                  id="produkt"
                  label={text(T.produkt)}
                  hint={text(T.produktHint)}
                  span="md:col-span-12"
                  value={produkt}
                  onChange={andra("produkt", setProdukt)}
                  placeholder={text(PLACEHOLDER.produkt)}
                  fel={fel("produkt")}
                  rader={2}
                />
                {/* Faktureringsadressen hör till bolagsuppgifterna och fylls i
                    här, inte vid paketvalet. Döljs för testarbetsytor: inget
                    bolag, ingen faktura, och ett obligatoriskt fält utan bolag
                    bakom lär bara folk att skriva påhitt. */}
                {!testkund ? (
                  <>
                    <Falt
                      id="faktGata"
                      label={text(T.faktura)}
                      hint={text(T.fakturaHint)}
                      span="md:col-span-12"
                      value={faktGata}
                      onChange={andra("faktGata", setFaktGata)}
                      placeholder="Storgatan 1"
                      fel={fel("faktGata")}
                      autoComplete="street-address"
                    />
                    <Falt
                      id="faktPostnr"
                      label={text(T.postnummer)}
                      span="md:col-span-4"
                      value={faktPostnr}
                      onChange={andra("faktPostnr", setFaktPostnr)}
                      onBlur={() => setFaktPostnr(formateraPostnummer(faktPostnr))}
                      placeholder="111 22"
                      fel={fel("faktPostnr")}
                      inputMode="numeric"
                      autoComplete="postal-code"
                    />
                    <Falt
                      id="faktOrt"
                      label={text(T.ort)}
                      span="md:col-span-8"
                      value={faktOrt}
                      onChange={andra("faktOrt", setFaktOrt)}
                      placeholder="Stockholm"
                      fel={fel("faktOrt")}
                      autoComplete="address-level2"
                    />
                  </>
                ) : null}
              </div>
              <Stegfot error={felText} />
            </form>
          ) : null}

          {steg === 1 ? (
            <form onSubmit={nasta} noValidate>
              <p className="mt-4 max-w-[62ch] text-[15px] leading-[1.65] text-ink-muted">
                {text(T.intro1)}
              </p>
              <div className="mt-8 flex flex-wrap gap-2" role="radiogroup" aria-label={text(T.bransch)}>
                {BRANSCHER.map((b) => {
                  const vald = bransch === b;
                  return (
                    <button
                      key={b}
                      type="button"
                      role="radio"
                      aria-checked={vald}
                      onClick={() => {
                        setBransch(b);
                        setError(null);
                      }}
                      // Samma vikt vald som ovald: fetstil ändrar bredden, och
                      // raden under hoppar när valet flyttar. Valet bärs av
                      // ink-ramen och ochre-plattan, som syns utan att läsas.
                      className={cn(
                        "focus-ring min-h-11 rounded-input border px-4 py-2.5 text-[0.9375rem] font-medium transition-colors",
                        vald
                          ? "border-ink bg-ochre/25 text-ink ring-1 ring-ink"
                          : "border-ink/15 bg-paper2/50 text-ink-muted hover:border-ink/30 hover:text-ink"
                      )}
                    >
                      {text(BRANSCH_ETIKETT[b])}
                    </button>
                  );
                })}
              </div>
              <Stegfot error={felText} onTillbaka={() => gaTill(0)} />
            </form>
          ) : null}

          {steg === 2 ? (
            <form onSubmit={nasta} noValidate>
              <p className="mt-4 max-w-[62ch] text-[15px] leading-[1.65] text-ink-muted">
                {text(T.intro2)}
              </p>
              <div className="mt-8 grid grid-cols-12 gap-y-6 md:gap-x-8">
                <Falt
                  id="kontaktNamn"
                  label={text(T.namn)}
                  hint={text(T.namnHint)}
                  span="md:col-span-6"
                  value={kontaktNamn}
                  onChange={andra("kontaktNamn", setKontaktNamn)}
                  placeholder="Anna Andersson"
                  fel={fel("kontaktNamn")}
                  autoComplete="name"
                />
                <Falt
                  id="kontaktRoll"
                  label={text(T.roll)}
                  hint={text(T.rollHint)}
                  span="md:col-span-6"
                  value={kontaktRoll}
                  onChange={setKontaktRoll}
                  placeholder={text(T.rollExempel)}
                  autoComplete="organization-title"
                />
                <Falt
                  id="kontaktMejl"
                  label={text(T.epost)}
                  hint={text(T.epostHint)}
                  span="md:col-span-6"
                  value={kontaktMejl}
                  onChange={andra("kontaktMejl", setKontaktMejl)}
                  placeholder={text(T.epostExempel)}
                  fel={fel("kontaktMejl")}
                  type="email"
                  autoComplete="email"
                />
                <Falt
                  id="kontaktTelefon"
                  label={text(T.telefon)}
                  hint={text(T.telefonHint)}
                  span="md:col-span-6"
                  value={kontaktTelefon}
                  onChange={setKontaktTelefon}
                  placeholder="070-123 45 67"
                  type="tel"
                  autoComplete="tel"
                />
              </div>
              <Stegfot error={felText} onTillbaka={() => gaTill(1)} />
            </form>
          ) : null}

          {steg === 3 ? (
            <form onSubmit={nasta} noValidate>
              <p className="mt-4 max-w-[62ch] text-[15px] leading-[1.65] text-ink-muted">
                {text(T.intro3)}
              </p>
              <div className="mt-8 grid grid-cols-12 gap-y-6 md:gap-x-8">
                <Falt
                  id="branscher"
                  label={text(T.branscher)}
                  hint={text(T.branscherHint)}
                  span="md:col-span-6"
                  value={branscher}
                  onChange={setBranscher}
                  placeholder={text(PLACEHOLDER.branscher)}
                />
                <Falt
                  id="orter"
                  label={text(T.orter)}
                  hint={text(T.orterHint)}
                  span="md:col-span-6"
                  value={orter}
                  onChange={setOrter}
                  placeholder={text(PLACEHOLDER.orter)}
                />
                <Falt
                  id="anstMin"
                  label={text(T.anstMin)}
                  hint={text(T.anstMinHint)}
                  span="col-span-6 md:col-span-3"
                  value={anstMin}
                  onChange={andra("anstMin", setAnstMin)}
                  placeholder={String(standardMalgrupp.anstallda[0])}
                  fel={fel("anstMin")}
                  inputMode="numeric"
                  autoComplete="off"
                />
                <Falt
                  id="anstMax"
                  label={text(T.anstMax)}
                  hint={text(T.anstMaxHint)}
                  span="col-span-6 md:col-span-3"
                  value={anstMax}
                  onChange={andra("anstMax", setAnstMax)}
                  placeholder={String(standardMalgrupp.anstallda[1])}
                  fel={fel("anstMax")}
                  inputMode="numeric"
                  autoComplete="off"
                />
                <Falt
                  id="roller"
                  label={text(T.roller)}
                  hint={text(T.rollerHint)}
                  span="md:col-span-6"
                  value={roller}
                  onChange={setRoller}
                  placeholder={text(PLACEHOLDER.roller)}
                />
                <Falt
                  id="undvik"
                  label={text(T.undvik)}
                  hint={text(T.undvikHint)}
                  span="md:col-span-12"
                  value={undvik}
                  onChange={setUndvik}
                  placeholder={text(PLACEHOLDER.undvik)}
                />
                {/* Fri text, inte ett filter: Iris läser den som riktning, och
                    fälten ovan vinner alltid när de säger emot. */}
                <Falt
                  id="fokus"
                  label={text(T.fokus)}
                  hint={text(T.fokusHint)}
                  span="md:col-span-12"
                  value={fokus}
                  onChange={setFokus}
                  placeholder={text(PLACEHOLDER.fokus)}
                  rader={3}
                />
                {/* Erbjudandet styr utskicken (Anton 2026-10-25): varje stycke
                    blir ett eget erbjudande i Leads › Erbjudanden, och Iris
                    anpassar det till varje bolags verksamhet. */}
                <Falt
                  id="erbjudanden"
                  label={text(T.erbjudanden)}
                  hint={text(T.erbjudandenHint)}
                  span="md:col-span-12"
                  value={erbjudanden}
                  onChange={setErbjudanden}
                  placeholder={text(PLACEHOLDER.erbjudanden)}
                  rader={4}
                />
              </div>
              <Stegfot error={felText} onTillbaka={() => gaTill(2)} />
            </form>
          ) : null}

          {steg === 4 ? (
            <form
              noValidate
              onSubmit={(e) => {
                e.preventDefault();
                skickaIn();
              }}
            >
              <p className="mt-4 max-w-[62ch] text-[15px] leading-[1.65] text-ink-muted">
                {text(T.intro4)}
              </p>

              <div
                role="radiogroup"
                aria-label={text(T.paket)}
                className="mt-8 divide-y divide-ink/10 overflow-hidden rounded-card border border-ink/15 bg-paper"
              >
                {PAKET.map((p) => {
                  const vald = paket === p.id;
                  return (
                    <button
                      key={p.id}
                      type="button"
                      role="radio"
                      aria-checked={vald}
                      disabled={isPending}
                      onClick={() => setPaket(p.id)}
                      className={cn(
                        "focus-ring relative block w-full px-5 py-4 text-left transition-colors",
                        vald ? "bg-ochre/[0.12]" : "hover:bg-ink/[0.03]"
                      )}
                    >
                      <span
                        aria-hidden
                        className={cn(
                          "absolute bottom-0 left-0 top-0 w-[3px] bg-ochre transition-opacity",
                          vald ? "opacity-100" : "opacity-0"
                        )}
                      />
                      <span className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                        <span className="text-[1.0625rem] font-semibold">{p.namn}</span>
                        {p.populärast ? (
                          <span className="rounded-input border border-ochre/40 bg-ochre/10 px-2 py-0.5 text-[0.75rem] font-medium text-warning">
                            {text(T.popularast)}
                          </span>
                        ) : null}
                        <span className="ml-auto text-[0.9375rem] tabular-nums text-ink-muted">
                          {p.prisPerManad === null
                            ? text(T.prisVidKontakt)
                            : `${text(T.fran)} ${p.prisPerManad.toLocaleString("sv-SE")} ${text(T.krManad)}`}
                        </span>
                      </span>
                      <span className="mt-1 block max-w-[58ch] text-[14px] leading-6 text-ink-muted">
                        {text(p.beskrivning)}
                      </span>
                      {vald ? (
                        <span className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
                          {p.ingar.map((rad) => (
                            <span
                              key={rad.sv}
                              className="flex items-center gap-1.5 text-[13px] text-ink-subtle"
                            >
                              <Check className="h-3.5 w-3.5 shrink-0 text-moss" aria-hidden />
                              {text(rad)}
                            </span>
                          ))}
                        </span>
                      ) : null}
                    </button>
                  );
                })}
              </div>

              <p className="mt-4 text-[14px] leading-6 text-ink-muted">
                {text(T.exklMoms)} {text(T.osakra)}{" "}
                <a
                  href="/demo"
                  target="_blank"
                  rel="noopener"
                  className="focus-ring inline-flex items-center gap-1 rounded-input font-medium text-ink underline underline-offset-4 hover:text-warning"
                >
                  {text(T.utforska)}
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                </a>
                {". "}
                {text(T.nyFlik)}
              </p>

              {/* Gratisperioden + villkorsgodkännandet. Kryssrutan startar
                  okryssad — ett förkryssat samtycke är inget samtycke — och
                  länkarna öppnas i nya flikar så att flödet står kvar. */}
              <div
                className={cn(
                  "mt-8 rounded-panel border bg-ochre/[0.07] p-5",
                  faltFel.villkor ? "border-danger" : "border-ochre/40"
                )}
              >
                <h2 className="text-[1.0625rem] font-semibold">{text(T.gratisRubrik)}</h2>
                <p className="mt-2 max-w-[58ch] text-[14px] leading-6 text-ink-muted">
                  {text(T.gratisText)}
                </p>
                <label className="mt-4 flex items-start gap-3">
                  <input
                    id={faltDomId("villkor")}
                    type="checkbox"
                    checked={villkor}
                    aria-invalid={Boolean(faltFel.villkor)}
                    aria-describedby={faltFel.villkor ? `${faltDomId("villkor")}-fel` : undefined}
                    onChange={(e) => {
                      setVillkor(e.target.checked);
                      if (e.target.checked) satFaltfel("villkor", null);
                    }}
                    className="focus-ring mt-1 h-4 w-4 shrink-0"
                  />
                  <span className="text-[14px] leading-6 text-ink-muted">
                    {text(T.jagGodkanner)}{" "}
                    <a
                      href="/villkor"
                      target="_blank"
                      rel="noopener"
                      className="focus-ring rounded-input font-medium text-ink underline underline-offset-4 hover:text-warning"
                    >
                      {text(T.villkorLank)}
                    </a>{" "}
                    {text(T.harTagitDel)}{" "}
                    <a
                      href="/angerratt"
                      target="_blank"
                      rel="noopener"
                      className="focus-ring rounded-input font-medium text-ink underline underline-offset-4 hover:text-warning"
                    >
                      {text(T.angerrattLank)}
                    </a>
                    .
                  </span>
                </label>
                {faltFel.villkor ? (
                  <p
                    id={`${faltDomId("villkor")}-fel`}
                    role="alert"
                    className="mt-3 text-[14px] font-medium text-danger"
                  >
                    {text(faltFel.villkor)}
                  </p>
                ) : null}
              </div>

              <div className="mt-6 rounded-panel border border-ink/15 bg-paper2/50 p-5">
                <h2 className="text-[1.0625rem] font-semibold">{text(T.notiser)}</h2>
                <label className="mt-3 flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={notiser}
                    onChange={(e) => setNotiser(e.target.checked)}
                    className="focus-ring mt-1 h-4 w-4 shrink-0"
                  />
                  <span className="text-[14px] leading-6 text-ink-muted">
                    <span className="font-medium text-ink">{text(T.jaMejla)}</span>{" "}
                    {text(T.notiserText)}
                  </span>
                </label>
              </div>

              {felText ? (
                <p role="alert" className="mt-6 text-[15px] font-medium text-danger">
                  {felText}
                </p>
              ) : null}

              {/* Sparningen tar tio till femton sekunder (uppmätt 14 s lokalt):
                  arbetsytan läggs upp i backenden. En snurra i en knapp räcker
                  inte för den väntan, så raden byts mot ett besked om vad som
                  händer och att fliken ska stå kvar. */}
              {isPending ? (
                <div
                  role="status"
                  className="mt-8 flex items-start gap-4 rounded-panel border border-ink/15 bg-paper2/60 p-5"
                >
                  <Loader2 className="mt-0.5 h-5 w-5 shrink-0 animate-spin text-warning" aria-hidden />
                  <div>
                    <p className="text-[1.0625rem] font-semibold">{text(T.laggerUpp)}</p>
                    <p className="mt-1 max-w-[52ch] text-[14px] leading-6 text-ink-muted">
                      {text(T.laggerUppText)}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="mt-8 flex flex-wrap items-center gap-4">
                  <button
                    type="button"
                    onClick={() => gaTill(3)}
                    className="focus-ring inline-flex min-h-12 items-center gap-2 rounded-input px-4 text-[0.9375rem] font-medium text-ink-muted hover:text-ink"
                  >
                    <ArrowLeft className="h-4 w-4" aria-hidden />
                    {text(T.tillbaka)}
                  </button>
                  <button
                    type="submit"
                    className="focus-ring inline-flex min-h-12 items-center gap-2 rounded-input bg-ink px-7 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2"
                  >
                    {text(T.oppnaMed)} {valtPaket?.namn ?? text(T.valtPaket)}
                  </button>
                </div>
              )}

              <p className="mt-4 max-w-[62ch] text-[13px] leading-[1.55] text-ink-subtle">
                {text(T.ingetSkickas)}
              </p>
            </form>
          ) : null}
        </div>
      </div>

      {/* Villkorsraden — samma plats längst ner på VARJE steg, så villkoren
          aldrig är mer än en blick bort oavsett var i flödet man står.
          Blå med flit (beställd 2026-09-29): länkarna ska se ut som länkar
          och inte konkurrera med ochre-accenten, som är flödets eget språk.
          Öppnas i nya flikar — det ifyllda står kvar. */}
      <nav
        aria-label={text(T.villkorNav)}
        className="col-span-12 mt-16 flex flex-wrap gap-x-6 gap-y-2 border-t border-ink/15 pt-4 text-[13px]"
      >
        {[
          { href: "/villkor", text: T.lankVillkor },
          { href: "/angerratt", text: T.lankAngerratt },
          { href: "/integritetspolicy", text: T.lankPolicy },
          { href: "/cookies", text: T.lankCookies }
        ].map((lank) => (
          <a
            key={lank.href}
            href={lank.href}
            target="_blank"
            rel="noopener"
            className="focus-ring inline-flex min-h-6 items-center rounded-input text-[#23538f] underline underline-offset-4 hover:text-ink"
          >
            {text(lank.text)}
          </a>
        ))}
      </nav>
    </div>
  );
}

/** Fortsätt/Tillbaka-raden för steg 1–4. Sista steget har sin egen. */
function Stegfot({
  error,
  onTillbaka
}: Readonly<{ error: string | null; onTillbaka?: () => void }>) {
  const { text } = useLocale();
  return (
    <>
      {error ? (
        <p role="alert" className="mt-6 text-[15px] font-medium text-danger">
          {error}
        </p>
      ) : null}
      <div className="mt-8 flex flex-wrap items-center gap-4">
        {onTillbaka ? (
          <button
            type="button"
            onClick={onTillbaka}
            className="focus-ring inline-flex min-h-12 items-center gap-2 rounded-input px-4 text-[0.9375rem] font-medium text-ink-muted hover:text-ink"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            {text(T.tillbaka)}
          </button>
        ) : null}
        <button
          type="submit"
          className="focus-ring inline-flex min-h-12 items-center gap-2 rounded-input bg-ink px-7 text-[0.9375rem] font-semibold text-paper transition-colors hover:bg-ink2"
        >
          {text(T.fortsatt)}
          <ArrowRight className="h-4 w-4" aria-hidden />
        </button>
      </div>
    </>
  );
}

/**
 * Ett fält med etikett, hjälptext och fel. Felet tar hjälptextens plats och
 * pekas ut med `aria-describedby`, så att skärmläsaren läser det med fältet.
 * `rader` ger ett flerradsfält med samma etikett och samma felhantering.
 */
function Falt({
  id,
  label,
  hint,
  span,
  value,
  onChange,
  onBlur,
  placeholder,
  fel,
  rader,
  disabled = false,
  type = "text",
  inputMode,
  autoComplete
}: Readonly<{
  id: string;
  label: string;
  hint?: string;
  span: string;
  value: string;
  onChange: (v: string) => void;
  onBlur?: () => void;
  placeholder: string;
  fel?: string | null;
  rader?: number;
  disabled?: boolean;
  type?: string;
  inputMode?: "numeric" | "text" | "url";
  autoComplete?: string;
}>) {
  const domId = faltDomId(id);
  const beskrivning = fel ?? hint;
  const gemensamt = {
    id: domId,
    value,
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => onChange(e.target.value),
    onBlur,
    placeholder,
    disabled,
    "aria-invalid": Boolean(fel),
    "aria-describedby": beskrivning ? `${domId}-text` : undefined
  };
  // 16 px (text-base): under det zoomar iOS Safari in på fältet vid fokus.
  const ruta = cn(
    "w-full rounded-input border bg-paper2/70 px-4 text-base text-ink focus:border-ochre disabled:opacity-50",
    fel ? "border-danger" : "border-ink/15"
  );
  return (
    <div
      className={cn(
        "grid content-start gap-2 border-t border-ink/15 pt-4",
        // Full bredd på mobil om inte anropet själv säger annat.
        !span.startsWith("col-span-") && "col-span-12",
        span
      )}
    >
      <label htmlFor={domId} className={etikett}>
        {label}
      </label>
      {rader ? (
        <textarea {...gemensamt} rows={rader} className={cn(ruta, "py-3 leading-[1.6]")} />
      ) : (
        <input
          {...gemensamt}
          className={cn(ruta, "h-12")}
          type={type}
          inputMode={inputMode}
          autoComplete={autoComplete}
        />
      )}
      {beskrivning ? (
        <p
          id={`${domId}-text`}
          className={cn("text-[13px] leading-[1.5]", fel ? "font-medium text-danger" : "text-ink-subtle")}
        >
          {beskrivning}
        </p>
      ) : null}
    </div>
  );
}
