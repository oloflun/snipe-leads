import { NextRequest, NextResponse } from 'next/server';
import { generateText } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';
import { getWorkspaceContext } from '@/lib/workspace';

/**
 * Routen väntar på ett LLM-anrop och var den ENDA under app/api som saknade
 * maxDuration. Vercels standardtak är betydligt kortare än en omskrivning tar,
 * så funktionen dödades mitt i — och ett dödat anrop svarar UTAN kropp.
 * Editorn anropade `.json()` på det tomma svaret och visade webbläsarens råa
 * "Unexpected end of JSON input" för kunden. Det var den felrapporten.
 *
 * 60 s är taket på Vercels nuvarande plan. Håll raden och lägg till den på
 * varje ny route som väntar på en modell.
 */
export const maxDuration = 60;

/**
 * Vilken modell åtgärderna körs mot.
 *
 * BAKGRUNDEN, uppmätt 2026-08-23: routen krävde `OPENAI_API_KEY`, och den var
 * inte satt på webbtjänsten i NÅGON miljö. `useSimulation` var alltså sann
 * även för en inloggad, betalande kund — alla åtta åtgärder svarade med
 * mallgenererad text som inte gick att skilja från en modellskriven
 * omskrivning. Funktionen såg ut att fungera och gjorde det inte.
 *
 * Samtidigt betalar projektet redan för DeepSeek: agenterna kör mot den, och
 * nyckeln finns på API-tjänsten. DeepSeek talar OpenAI-protokollet, så samma
 * klient når båda — bara base_url och modellnamn skiljer.
 *
 * Ordningen är avsiktlig. OPENAI_API_KEY vinner när den finns, så att ett
 * senare byte tillbaka inte kräver en kodändring. Saknas den används DeepSeek.
 * Saknas båda simulerar routen, som förut, och SÄGER det i svaret.
 */
function valjModell() {
  const openaiKey = process.env.OPENAI_API_KEY || "";
  if (dugerSomNyckel(openaiKey)) {
    return {
      klient: createOpenAI({ apiKey: openaiKey }),
      namn: process.env.EMAIL_STUDIO_MODEL || "gpt-4o-mini"
    };
  }

  const deepseekKey = process.env.DEEPSEEK_API_KEY || "";
  // DeepSeek behandlar prompten i Kina, och det som postas hit är kundens
  // utkast med namn och bolagsuppgifter. Beslutet 2026-08-24 (CLAUDE.md,
  // snajp-support/app/agent/llm.py) förbjuder det mot riktig kunddata.
  // NODE_ENV=production täcker både prod och Railway-dev (som speglar prod);
  // kvar blir lokal utveckling mot syntetiska exempel — där hör DeepSeek hemma.
  if (dugerSomNyckel(deepseekKey) && process.env.NODE_ENV !== "production") {
    return {
      // Samma base_url som snajp-support/app/agent/llm.py använder. Håll dem
      // lika — två adresser till samma leverantör är två saker att byta.
      klient: createOpenAI({ apiKey: deepseekKey, baseURL: "https://api.deepseek.com" }),
      namn: process.env.EMAIL_STUDIO_MODEL || "deepseek-chat"
    };
  }

  return null;
}

/** En platshållare är inte en nyckel. Samma villkor som backendens `_looks_real`. */
function dugerSomNyckel(key: string): boolean {
  return Boolean(key) && key.length >= 20 && !key.includes("...") && !key.includes("din-");
}

function parseRichRefine(content: string) {
  const trimmed = content.trim();

  // 1) Try pure JSON
  try {
    const p = JSON.parse(trimmed);
    if (p && typeof p.new_version === "string") {
      return {
        original_version: p.original_version ?? null,
        new_version: p.new_version.trim(),
        explanation: (p.explanation || "").trim(),
        subject_suggestions: Array.isArray(p.subject_suggestions) ? p.subject_suggestions.map((s: any) => String(s).trim()) : [],
        confidence_tips: p.confidence_tips
      };
    }
  } catch {}

  // 2) Try fenced ```json ... ```
  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced) {
    try {
      const p = JSON.parse(fenced[1]);
      if (p && typeof p.new_version === "string") {
        return {
          original_version: p.original_version ?? null,
          new_version: p.new_version.trim(),
          explanation: (p.explanation || "").trim(),
          subject_suggestions: Array.isArray(p.subject_suggestions) ? p.subject_suggestions.map((s: any) => String(s).trim()) : [],
          confidence_tips: p.confidence_tips
        };
      }
    } catch {}
  }

  // 3) Parse the exact sectioned format from the system prompt ( **Ny version:** etc )
  function extractSection(src: string, labels: string[]): string | null {
    for (const label of labels) {
      const re = new RegExp(`\\*\\*${label}\\*\\*[:：]?\\s*([\\s\\S]*?)(?=\\n\\*\\*|\\n[A-ZÅÄÖa-zåäö]|$)`, 'i');
      const m = src.match(re);
      if (m && m[1]) return m[1].trim();
    }
    return null;
  }

  const new_version = extractSection(trimmed, ['Ny version', 'New version', 'NY VERSION']) || extractSection(trimmed, ['version']);
  const explanation = extractSection(trimmed, ['Förklaring av förändringarna', 'Explanation of changes', 'Förklaring']);
  const subjectsRaw = extractSection(trimmed, ['Förslag på ämnesrad', 'Subject suggestions', 'Ämnesrad']);
  const tips = extractSection(trimmed, ['Konfidens / Tips', 'Confidence', 'Tips']);

  let subject_suggestions: string[] = [];
  if (subjectsRaw) {
    subject_suggestions = subjectsRaw
      .split(/\n|•|-/)
      .map(s => s.trim())
      .filter(Boolean)
      .slice(0, 3);
  }

  if (new_version) {
    return {
      original_version: extractSection(trimmed, ['Ursprunglig version', 'Original version']) ?? null,
      new_version,
      explanation: explanation || "Ändring utförd enligt marketingskills.",
      subject_suggestions: subject_suggestions.length ? subject_suggestions : [],
      confidence_tips: tips
    };
  }

  // 4) Fallback: whole content (last resort)
  return {
    original_version: null,
    new_version: trimmed,
    explanation: "Oformaterat svar från agenten.",
    subject_suggestions: [],
    confidence_tips: undefined
  };
}

/**
 * Demoläget: en deterministisk omskrivning utan LLM.
 *
 * ## Varför den inte får innehålla ett bolagsnamn
 *
 * Varenda gren här var tidigare skriven kring exempelmejlet om Byggkompaniet
 * Syd och Hyllie: "Såg att X växlar upp i Hyllie", "Uppföljning:
 * Hyllie-renoveringar". När exempelmejlet på marknadssidan byttes svarade
 * knapparna alltså om en stadsdel som inte stod någonstans i mejlet man just
 * läst. Allt konkret kommer nu ur `context` — bolag, signal, erbjudande,
 * uppmaning och mottagare — och ingen ort eller bransch står skriven i koden.
 */
function simulateAction(action: string, emailContent: string, subject: string, context: any = {}) {
  const orig = emailContent || "Hej,\n\n...";
  const company = context?.companyName || "bolaget";
  const signal = context?.signal || "det som händer hos er just nu";
  const offer = context?.offer || "vårt erbjudande";
  const cta = String(context?.cta || "Vill ni att vi hör av oss med ett konkret förslag?").replace(/\?+$/, "");
  const namn = context?.contactName ? `Hej ${context.contactName},` : "Hej,";

  /**
   * Lite språkvariation även utan modell — men deterministisk: samma indata
   * ger samma svar, så demon går att visa två gånger utan att se slumpad ut.
   * Valet styrs av innehållet, inte av Math.random().
   */
  const variant = (fraser: string[]) => {
    let summa = action.length + orig.length + company.length;
    for (let i = 0; i < company.length; i++) summa += company.charCodeAt(i);
    return fraser[summa % fraser.length];
  };
  const lagesfras = variant([
    "Det brukar vara läget då",
    "Det är ofta precis då",
    "Erfarenhetsmässigt är det då"
  ]);
  const skiftesfras = variant([
    'går från "senare" till "nu"',
    "hamnar överst på bordet",
    "blir svår att skjuta på"
  ]);

  /**
   * Gemen begynnelsebokstav, inte gemen mening. `toLowerCase()` på hela
   * signalen gjorde "Ny lokal i Göteborg" till "ny lokal i göteborg" mitt i
   * ett mejl — ett egennamn med litet g är precis den sortens detalj som
   * avslöjar en maskin.
   */
  const inled = (v: string) => (v ? v.charAt(0).toLowerCase() + v.slice(1) : v);

  let new_version = orig;
  let explanation = "Demo: ändring baserad på marketingskills (cold-email, copywriting).";
  let subject_suggestions: string[] = [subject || "Intressant tajming"];

  if (action === "shorter") {
    new_version = `${namn}\n\nJag såg ${inled(signal)} hos ${company}. ${lagesfras} ${inled(offer)} är som mest värt att titta på.\n\n${cta}?`;
    explanation = "Ruthlessly short enligt cold-email/SKILL.md: kärnsignalen, en mening om värdet och en låg-friktions-CTA. Utfyllnaden är borta.";
    subject_suggestions = [
      subject ? subject.substring(0, 38) + (subject.length > 38 ? "..." : "") : `${company} — kort fråga`,
      `${company}: rätt läge nu?`
    ];
  } else if (action === "rewrite") {
    new_version = `${namn}\n\n${signal} hos ${company} är en tydlig köpsignal för det vi gör. Bolag i samma läge brukar ha samma fråga: hur mycket som behöver vara på plats direkt, och vad som kan vänta.\n\n${offer} är byggt för precis det steget.\n\n${cta}?`;
    explanation = "Omskriven med ny struktur (Observation, problem, värde, fråga) per copywriting och cold-email. Samma fakta, mänsklig ton.";
    subject_suggestions = [
      `${company.split(" ")[0]} — tajmingen just nu`,
      "En fråga om nästa steg",
      subject || `${company} och nästa steg`
    ];
  } else if (action === "improve") {
    new_version = `${namn}\n\n${signal}. ${lagesfras} den här frågan ${skiftesfras}.\n\n${offer} — anpassat efter hur ni faktiskt jobbar, inte en standardlösning.\n\n${cta}?`;
    explanation = "Förbättrad: tydligare värde, aktiv röst, konkret uppmaning. Enligt copywriting/SKILL.md och cold-email.";
    subject_suggestions = [subject ? "Bättre: " + subject : `${company} — rätt läge`, `${company}: två konkreta förslag?`];
  } else if (action === "personalize") {
    new_version = `${namn}\n\nJag såg ${inled(signal)} hos ${company}. Flera bolag vi jobbar med har haft exakt samma tajmingfråga i det läget: vad som måste vara på plats direkt och vad som kan vänta.\n\nVi löser det med ${inled(offer)}.\n\n${cta}?`;
    explanation = "Personaliserad utifrån signalen om bolaget. Specifik och icke-uppenbar, per cold-email och marketing-psychology.";
    subject_suggestions = [`${company} — sett er senaste nyhet`, subject || `${company} och tajmingen`];
  } else if (action === "translate") {
    /**
     * Skriver hela mejlet på målspråket.
     *
     * Två fällor, båda sedda i drift på marknadssidan:
     *
     * 1. Den gamla varianten körde fyra `replace` över svenskan och lämnade
     *    resten kvar: "I noticed that techbolaget E-Tech växlar upp med en ny
     *    lokal". En halv översättning ser ut som ett fel i produkten.
     * 2. Nästa försök vävde in `signal` och `offer` i en engelsk mening — men
     *    de fälten kommer från sidans svenska exempeldata, så resultatet blev
     *    engelska med svenska satser mitt i.
     *
     * Därför bär den här grenen bara det som är språkneutralt: bolagsnamnet
     * och mottagaren. Riktig översättning av innehållet kräver modellen, och
     * den vägen är öppen så fort man är inloggad.
     */
    const isSv = /[åäö]|hej|såg att/i.test(orig);
    if (isSv) {
      const enNamn = context?.contactName ? `Hi ${context.contactName},` : "Hi there,";
      new_version = `${enNamn}\n\nI saw the recent news at ${company}. That is usually the point where this question moves from "later" to "now".\n\nWe would be glad to put together a proposal built around how you actually work.\n\nWould you like us to send it over?`;
    } else {
      new_version = `${namn}\n\nJag såg det senaste som hänt hos ${company}. ${lagesfras} den här frågan ${skiftesfras}.\n\nVi tar gärna fram ett förslag som utgår från hur ni faktiskt jobbar.\n\nVill ni att vi skickar över det?`;
    }
    explanation = "Översättning i demoläge: hela mejlet skrivs på målspråket. Innehållet hålls generellt eftersom demon inte kör någon modell — logga in för en översättning av just den här texten.";
    subject_suggestions = [subject || "Translated subject"];
  } else if (action === "ab_variants") {
    new_version = `Variant A (problem):\n${namn}\n\n${signal} hos ${company} brukar betyda att en sak plötsligt blir brådskande. ${offer} finns för det steget.\n\n${cta}?\n\nVariant B (möjlighet):\n${namn}\n\n${signal} hos ${company} öppnar ett fönster. Vi har sett hur ${inled(offer)} ger mest effekt just när något nytt precis kommit på plats.\n\n${cta}?`;
    explanation = "A/B-varianter med olika vinklar (problem mot möjlighet) enligt ab-testing/SKILL.md.";
    subject_suggestions = [`${subject} (A)`, `${subject} (B)`, "Alternativ vinkel"];
  } else if (action === "followup") {
    new_version = `${orig}\n\n--- Uppföljning ---\n${namn}\n\nJag hörde av mig förra veckan om ${inled(signal)}. Sedan dess har vi tagit fram ett konkret underlag för bolag i exakt det läget.\n\n${cta}?`;
    explanation = "Uppföljning som tillför något nytt i stället för att bara stämma av. Per emails/SKILL.md.";
    subject_suggestions = ["Uppföljning: nästa steg", `${company} — ett konkret underlag`];
  } else if (action === "analyze") {
    new_version = orig;
    explanation = `Analys: 7,5/10. Signalen om ${company} bär mejlet och tonen är jämbördig. Kan kortas ytterligare, och uppmaningen tjänar på att vara en enda fråga. Förväntad svarsfrekvens: 8 till 15 %.`;
    subject_suggestions = [subject || "Analyserad version"];
  } else if (action === "longer" || action === "expand") {
    new_version = `${orig}\n\nExtra kontext: hos bolag i samma läge som ${company} brukar det här steget gå snabbare när underlaget finns färdigt från början. Vi anpassar efter era krav och återkommer med ett förslag ni kan säga ja eller nej till.`;
    explanation = "Utökad version: la till kontext och ett tydligt nästa steg. Balanserad längd per copywriting.";
    subject_suggestions = [subject, `Mer om ${company}`];
  } else {
    new_version = orig + `\n\n[${action} tillämpad, se marketingskills för principer]`;
    explanation = `Åtgärd: ${action}`;
  }

  return {
    original_version: orig,
    new_version: new_version.trim(),
    explanation,
    subject_suggestions,
    confidence_tips: "Demoläge: svaret är förskrivet och kostar inget modellanrop. Logga in för att köra åtgärden mot modellen."
  };
}

export const EMAIL_STUDIO_SYSTEM_PROMPT = `# Snipe-Leads Email Studio — System Prompt v1.0
Du är **Email Studio**, den autonoma AI-assistenten i Snipe-Leads-plattformen (Snajp).  

Din enda uppgift: hjälpa användare skapa extremt effektiva, personliga, mänskliga B2B cold emails som får svar — aldrig spammiga.

**KRITISK REGEL — OBRYTBAR:**  

För **VARJE** funktion du utför (Kortare, Skriv om, Förbättra, Personalisera, Översätt, A/B-varianter, Uppföljning, Analysera) **MÅSTE** du utgå från och tillämpa ramverken, principerna och bästa praxis från https://github.com/coreyhaines31/marketingskills.  

Specifikt:
- **cold-email/SKILL.md**: Skriv som en peer, inte en vendor. Ruthlessly short. Personalization som visar att du förstår deras värld. Trigger events från nyheter/LinkedIn (expansion, funding, rekrytering, ny lokal, ledarskapsbyte, produktlansering). En låg-friktion CTA. Multi-touch follow-ups som adderar nytt värde varje gång.
- **copywriting/SKILL.md + copy-editing/SKILL.md**: Hooks, struktur (Observation → Problem → Proof → Ask eller Question → Value → Ask), value propositions (benefits > features), starka CTAs, redigering (clarity > cleverness, active voice, specific > vague, no jargon).
- **ab-testing/SKILL.md**: Generera varianter med olika vinklar och testa idéer.
- **emails/SKILL.md**: För sekvenser och follow-ups.
Använd alltid principerna: "The email should read like it came from someone who understands their world — not someone trying to sell them something." "Cold email is ruthlessly short." "Lead with their world, not yours."

**Agent-arkitektur (tänk i sub-agents internt):**
- Huvudagent: Du (Email Studio) — orkestrerar allt och returnerar i exakt format.
- Research Sub-Agent: Analysera tillhandahållen LinkedIn/nyhet för köpsignaler och trigger events.
- Scoring Sub-Agent: Ge lead-score 1-10 (fit + intent + timing + relevance). Förklara. Generera bara om ≥6, annars ge råd.
- Personalization Sub-Agent: Väva in 1-2 specifika, icke-uppenbara detaljer från signaler.
- Writing/Optimization Sub-Agent: Använd cold-email + copywriting ramverk.
- Variant Sub-Agent: 2-3 varianter med olika vinklar (pain, opportunity, social proof).
- Follow-up Sub-Agent: Skapa sekvens där varje mail adderar nytt värde.
- Analyzer Sub-Agent: Betyg + konkreta förbättringar bundna till marketingskills-principer.

**Miljö & Data:**
- Next.js + Supabase + LangChain.
- Ladda användarpreferenser från Supabase (ton: professional/friendly/direct, språk: främst svenska, längd: short/medium, branschfokus, value-prop). Anpassa allt därefter.
- Spara varje interaktion + preferensuppdateringar till Supabase för långsiktig kontext.
- Registrering: Endast email + magic link (Supabase Auth). Omedelbar tillgång till Email Studio utan extra verifikation.
- Kontext som skickas med: draft-email + lead-info (företag, roll, nyhet/LinkedIn-sammanfattning, signaler från plattformen).

**Kvalitetskontroller & Compliance (alltid):**
- Mänsklig ton: Konversationell, peer-to-peer, värde först. Läs högt — låter det som en smart kollega?
- Personalisering: Måste kopplas till problemet/triggern. Ta bort den och mailet ska fortfarande kännas relevant.
- GDPR / CAN-SPAM / god email-etik: Legitimate interest för B2B. Inkludera alltid enkel unsubscribe ("Reply STOP" eller länk). Inga vilseledande subject lines, ingen fake urgency, ingen spam-taktik. Endast relevanta leads.
- Interna kontroller: Lead-score + email-quality-score innan output. Aldrig generera om det känns spammigt.

**Output-format (EXAKT detta — ingen avvikelse):**
Svara med ETT giltigt JSON-objekt och ingenting annat — ingen inledande text, ingen kodstängsel:
{"new_version":"<den nya mejltexten>","explanation":"<kort, referera specifik princip, t.ex. 'Ruthlessly short enligt cold-email/SKILL.md'>","subject_suggestions":["<2-3 korta, interna, peer-liknande ämnesrader>"],"original_version":"<ursprungstexten eller null>","confidence_tips":"<valfritt: förväntad reply-rate, compliance-not eller nästa steg>"}

**Språk och variation (viktigt):**
- Variera ditt språk. Upprepa inte samma fraser, meningsöppningar eller ordval inom en konversation eller mellan förslag. Om du nyss skrev "Såg att..." — öppna nästa gång annorlunda.
- Använd ett brett men naturligt och professionellt ordförråd anpassat till svensk affärskontext. Skriv som en skicklig, initierad människa — inte som en mall.
- Undvik robotaktiga standardfraser: "Jag förstår att...", "Hoppas allt är bra", "Jag ville bara höra av mig", "I dagens snabbrörliga värld".
- Variera meningslängd och rytm. Tre meningar i rad med samma struktur låter maskinskrivet.

**Exempel på bra kontra dåligt (stilguide, kopiera aldrig ordagrant):**
DÅLIGT (mallspråk, upprepning): "Hej! Jag hoppas att allt är bra. Jag ville bara höra av mig angående era behov. Vi erbjuder marknadsledande lösningar. Hör gärna av er!"
BRA (signalburen, konkret, kort): "Hej Elin, ni rekryterar tre montörer till nya anläggningen — det brukar vara punkten där leverantörskedjan blir flaskhalsen. Vi har kortat den biten hos två bolag i samma läge. Värt ett underlag?"
DÅLIGT (uppföljning utan nytt värde): "Hej igen! Jag ville bara följa upp mitt förra mejl. Har ni hunnit titta på det?"
BRA (uppföljning som tillför): "Hej igen — sedan sist har vi satt ihop en jämförelse av hur tre bolag i er storlek löste precis det här steget. Vill du ha den?"
DÅLIGT (analys utan handling): "Mejlet är bra men kan förbättras. Jobba på ämnesraden och CTA:n."
BRA (analys med precisa drag): "7/10. Signalen bär mejlet, men stycke två säljer i stället för att observera — stryk det. Ämnesraden lovar mer än texten håller; 'Kort fråga om Hylliebygget' är ärligare och öppnas oftare."

**Beteende:**
- Var hjälpsam, snabb och proaktiv. Utför åtgärden omedelbart — leverera alltid ett användbart förslag.
- Använd alltid svensk ton om inte annat anges (modern, rak, vänlig).
- Om utkastet är tomt eller mycket kort: ge INTE upp och be INTE bara om mer information. Skriv ett komplett förslag utifrån den kontext som finns (bolag, signal, erbjudande, CTA), och säg i explanation vilka uppgifter som skulle göra nästa version vassare.
- Proaktiv: Använd confidence_tips till att föreslå nästa steg (t.ex. "Vill du ha en follow-up-sekvens eller A/B på ämnesraden?").
- Integrera med Snipe-Leads signal-detektering: Använd befintliga expansion/rekrytering/nyhets-signaler automatiskt när de finns.
`;

/**
 * Instruktion per knapp. Fanns tidigare bara i lib/agent/email-studio-prompt.ts
 * — en fil som ingenting anropar — så den levande routen skickade bara den råa
 * slugen ("ab_variants") utan förklaring. Varje instruktion pekar ut FLERA
 * vägar att lösa uppgiften, så att modellen kan variera sig mellan körningar.
 */
const ACTION_INSTRUCTIONS: Record<string, string> = {
  shorter:
    "Gör mejlet kortare och mer slagkraftigt — ruthlessly short enligt cold-email. Behåll kärnsignal och CTA. " +
    "Välj den väg som passar texten: stryk hela stycken snarare än ord, slå ihop observation och värde till en mening, eller ersätt förklaringen med en fråga.",
  rewrite:
    "Skriv om mejlet med ny vinkel eller bättre struktur. Samma fakta. Välj ett mönster som skiljer sig från originalets: " +
    "Observation → Problem → Bevis → Fråga; Fråga → Värde → Fråga; en rak, nästan torr konstaterande ton; eller börja i mottagarens värld och nämn avsändaren sist.",
  improve:
    "Optimera ämnesrad, öppning, CTA och språk. Tydlig nytta, stark men låg-friktions-CTA. Peka i explanation ut exakt vad som lyftes och varför.",
  personalize:
    "Väv in 1–2 specifika, icke-uppenbara detaljer från signalen/kontexten och koppla dem till ett problem mottagaren rimligen har just nu. " +
    "Personaliseringen ska sitta i resonemanget, inte bara i att bolagsnamnet nämns.",
  translate:
    "Översätt troget till det andra språket (sv <-> en) utan att tappa ton eller signal. Idiomatisk målspråkstext, ingen ord-för-ord-översättning.",
  ab_variants:
    "Generera 2–3 varianter med tydligt olika vinklar (t.ex. pain, opportunity, social proof, ren nyfikenhet) enligt ab-testing. " +
    "Märk varje variant (Variant A/B/C) och låt dem skilja sig i mer än ordval — olika öppning, olika CTA.",
  followup:
    "Skapa en uppföljning som adderar nytt värde — aldrig 'jag ville bara följa upp'. Nytt underlag, en insikt, ett konkret exempel eller en ny vinkel på samma signal.",
  analyze:
    "Ge betyg (1–10) och konkreta, precisa förbättringar bundna till marketingskills-principer. Lägg analysen i explanation och behåll originaltexten i new_version.",
  longer:
    "Utöka mejlet med relevant kontext och ett tydligt nästa steg — utan att tappa den korta, jämbördiga tonen.",
  expand:
    "Utöka mejlet med relevant kontext och ett tydligt nästa steg — utan att tappa den korta, jämbördiga tonen."
};

/**
 * Transienta fel går att försöka om; resten inte. AI-SDK:ns APICallError bär
 * statusCode och isRetryable; nätverksfel och timeouts saknar status helt.
 */
function arTransientFel(error: unknown): boolean {
  const e = error as { statusCode?: number; isRetryable?: boolean; name?: string } | null;
  if (!e) return false;
  if (e.isRetryable === true) return true;
  if (typeof e.statusCode === "number") {
    return e.statusCode === 408 || e.statusCode === 429 || e.statusCode >= 500;
  }
  // Ingen statuskod = anropet nådde aldrig fram (nätverk, DNS, abort/timeout).
  return true;
}

/**
 * Modellanrop med omtag: upp till tre försök med exponentiell paus (1 s, 2 s)
 * för transienta fel, varje försök med egen tidsgräns. Budgeten är medvetet
 * räknad mot maxDuration = 60: 3 × 15 s + 3 s paus = 48 s, så routen hinner
 * alltid skriva en egen svarskropp i stället för att dödas utan kropp.
 */
async function generateMedForsok(opts: {
  model: ReturnType<ReturnType<typeof createOpenAI>>;
  system: string;
  prompt: string;
}): Promise<string> {
  let sista: unknown;
  for (let forsok = 0; forsok < 3; forsok++) {
    try {
      const { text } = await generateText({
        model: opts.model,
        system: opts.system,
        prompt: opts.prompt,
        temperature: 0.7,
        maxOutputTokens: 1800,
        // SDK:n har egna omtag; de stängs av så att loopens tidsbudget håller.
        maxRetries: 0,
        abortSignal: AbortSignal.timeout(15_000)
      });
      return text;
    } catch (error) {
      sista = error;
      if (!arTransientFel(error) || forsok === 2) throw error;
      await new Promise((klar) => setTimeout(klar, 1000 * 2 ** forsok));
    }
  }
  throw sista;
}

/**
 * Sessionsgrind — men inte en stängd dörr.
 *
 * Routen anropar generateText mot OpenAI och var först anonymt nåbar: vem som
 * helst kunde bränna OPENAI_API_KEY genom att posta hit i en loop. Grinden
 * stängde hålet och stängde samtidigt demon på marknadssidan — knapparna i
 * Email Studio svarade "Du måste vara inloggad" för varje besökare, på en
 * sida vars egen text ber dem trycka på knapparna.
 *
 * Därför två lägen i stället för ett:
 *
 *   inloggad  -> åtgärden körs mot modellen, som förut
 *   anonym    -> `simulateAction` svarar, deterministiskt och utan modellanrop
 *
 * Det som INV-SEC-010 skyddar är kostnaden och nyckeln, och den anonyma vägen
 * rör ingendera: den når aldrig `generateText`. Se `useSimulation` i POST —
 * flaggan är sann så fort sessionen saknas, och den kontrollen får inte tas
 * bort utan att det här resonemanget görs om.
 *
 * `getWorkspaceContext` står kvar och är fortfarande det enda som avgör vem
 * anroparen är. Ingenting härleds ur request-kroppen.
 */
async function requireSession(): Promise<{ userId: string | null; publikDemo: boolean }> {
  const context = await getWorkspaceContext();
  if (!context) {
    return { userId: null, publikDemo: true };
  }
  return { userId: context.user.id, publikDemo: false };
}

export async function POST(request: NextRequest) {
  const session = await requireSession();

  // Kroppen läses för sig: en trasig kropp är anroparens fel (400), inte vårt
  // (500), och meddelandet är skrivet för en människa — aldrig ett parse-fel.
  let body: any;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Förfrågan gick inte att läsa. Ladda om sidan och prova igen." },
      { status: 400 }
    );
  }

  const { action = "improve", draft = '', subject = '', body: emailBody = '', context = {}, locale = 'sv' } = body;
  // En okänd åtgärd (feltryck, gammal klient) ska inte bli ett fel eller en
  // rå slug i prompten — den behandlas som "förbättra", vilket alltid ger
  // ett användbart svar.
  const kandAction = typeof action === "string" && action in ACTION_INSTRUCTIONS ? action : "improve";
  const emailContent = String(draft || emailBody || "");

  // Anonym besökare -> ALLTID simulering, oavsett vilka nycklar som finns.
  // Det är den raden som gör att marknadssidans knappar fungerar utan att en
  // oinloggad kan nå modellen. Se docstringen ovan om INV-SEC-010.
  const modell = session.publikDemo ? null : valjModell();
  if (modell === null) {
    const sim = simulateAction(kandAction, emailContent, subject, context);

    return NextResponse.json({
      success: true,
      data: {
        ...sim,
        action: kandAction,
        /**
         * SÄG att det är simulerat. Fältet fanns inte, och följden var inte
         * kosmetisk: OPENAI_API_KEY är inte satt på webbtjänsten i någon
         * miljö (uppmätt 2026-08-23), så simuleringen gällde även för en
         * INLOGGAD, betalande kund. Alla åtta åtgärder svarade alltså med
         * mallgenererad text, `success: true`, och ingenting som skilde den
         * från en modellskriven omskrivning.
         *
         * Anonymt är simulering rätt svar — den skyddar nyckeln, se
         * docstringen ovan. Det som saknades var att svaret sa det.
         */
        simulated: true,
        simulated_reason: session.publikDemo ? "anonym" : "ingen modellnyckel"
      }
    });
  }

  const userPrompt = [
    `Åtgärd: ${kandAction}`,
    `Instruktion för åtgärden: ${ACTION_INSTRUCTIONS[kandAction]}`,
    `Language: ${locale === 'sv' ? 'Swedish (sv-SE)' : 'English'}`,
    subject && `Current subject: ${subject}`,
    emailContent
      ? `Current email body:\n${emailContent}`
      : `Utkastet är tomt. Skriv ett komplett förslag utifrån kontexten nedan, och säg i explanation vilka uppgifter som skulle göra nästa version vassare.`,
    Object.keys(context).length > 0 && `Context: ${JSON.stringify(context)}`,
    `\n\nIMPORTANT: Answer with ONE valid JSON object only, exactly as specified in the system prompt. No prose before or after it.`
  ].filter(Boolean).join('\n\n');

  let text: string;
  try {
    text = await generateMedForsok({
      model: modell.klient(modell.namn),
      system: EMAIL_STUDIO_SYSTEM_PROMPT,
      prompt: userPrompt
    });
  } catch (error: any) {
    /**
     * Modellen svarade inte trots omtagen. Kunden får ALDRIG se det som ett
     * fel: hela feltexten (som kan bära leverantörens payload, kvot-texter
     * och request-id:n) loggas server-side, och svaret blir det deterministiska
     * förslaget med en ärlig markering om varför. Knappen fortsätter fungera.
     */
    console.error("Email Studio: modellanropet föll efter omtag:", error);
    const sim = simulateAction(kandAction, emailContent, subject, context);
    return NextResponse.json({
      success: true,
      data: {
        ...sim,
        action: kandAction,
        simulated: true,
        simulated_reason: "tillfälligt fel",
        confidence_tips:
          "Modellen svarade inte just nu, så det här är ett förskrivet förslag utifrån din kontext. Prova åtgärden igen om en liten stund."
      }
    });
  }

  const rich = parseRichRefine(text);
  // Ett tomt modellsvar får inte se ut som en lyckad omskrivning — då står
  // kundens gamla text kvar under rubriken "Ny version" utan förklaring.
  if (!rich.new_version || !rich.new_version.trim()) {
    console.error("Email Studio: modellen svarade tomt för åtgärden", kandAction);
    const sim = simulateAction(kandAction, emailContent, subject, context);
    return NextResponse.json({
      success: true,
      data: { ...sim, action: kandAction, simulated: true, simulated_reason: "tillfälligt fel" }
    });
  }

  return NextResponse.json({
    success: true,
    data: {
      ...rich,
      action: kandAction,
    }
  });
}

export async function GET() {
  // GET beskriver routen och avslöjar bara promptens LÄNGD. Den är ändå
  // grindad: en oinloggad har inget ärende till en API-beskrivning, och
  // simuleringsundantaget gäller POST och demon, inte den här.
  const session = await requireSession();
  if (session.publikDemo) {
    return NextResponse.json({ error: "Du måste vara inloggad." }, { status: 401 });
  }

  return NextResponse.json({
    message: 'Email Studio API route. POST with { action, subject, body, context? } to get the system prompt + request data.',
    systemPromptLength: EMAIL_STUDIO_SYSTEM_PROMPT.length,
  });
}
