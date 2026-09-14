import { NextRequest, NextResponse } from 'next/server';
import { generateText } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';
import { getWorkspaceContext } from '@/lib/workspace';
import { valjModell, type Modellval } from '@/lib/llm/modellval';
import { hamtaVertexToken } from '@/lib/llm/vertex';
import { kanForsokasOm, klassaModellfel, statuskod, type Modellfelklass } from '@/lib/llm/kvotfel';

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
 * Vilken modell åtgärderna körs mot: se lib/llm/modellval.ts för ordningen
 * (OpenAI → Vertex AI → GEMINI_API_KEY → DeepSeek) och dataskyddsspärren.
 *
 * BAKGRUNDEN, uppmätt 2026-08-23: routen krävde `OPENAI_API_KEY`, och den var
 * inte satt på webbtjänsten i NÅGON miljö — alla åtta åtgärder svarade med
 * mallgenererad text även för en inloggad, betalande kund. 2026-09 hände
 * samma sak igen från andra hållet: Google tog bort Cloud-krediterna från AI
 * Studio, GEMINI_API_KEY blev gratisnivå (20 anrop/dygn), och backenden gick
 * över till Vertex AI medan den här routen inte kände till Vertex.
 *
 * ## Varför `.chat()` och inte `klient(namn)`
 *
 * I @ai-sdk/openai v4 går `klient(namn)` mot OpenAI:s RESPONSES-API
 * (`POST {baseURL}/responses`). Varken Gemini, Vertex eller DeepSeek har den
 * endpointen — de talar Chat Completions. Gemini-grenen här kunde alltså
 * aldrig lyckas, och varje anrop blev ett "tillfälligt fel". OpenAI själv
 * klarar båda och får behålla standardvägen.
 */
async function byggSprakmodell(val: Modellval) {
  if (val.provider === "openai") {
    return createOpenAI({ apiKey: val.apiKey })(val.namn);
  }
  // Vertex: kortlivad OAuth2-token i stället för nyckel. Cachen i
  // lib/llm/vertex.ts gör att bara det första anropet i timmen växlar token.
  const apiKey = val.provider === "vertex" ? await hamtaVertexToken(val.serviceAccount) : val.apiKey;
  return createOpenAI({ apiKey, baseURL: val.baseURL }).chat(val.namn);
}

/**
 * GOOGLE_SERVICE_ACCOUNT_JSON satt men oanvändbar (trasig JSON, fält saknas)
 * faller tyst vidare till nästa leverantör i modellval.ts. Tyst är fel för en
 * operatör, så det sägs i loggen — utan innehållet, som bär privatnyckeln.
 */
function varnaOmTrasigServiceAccount(val: Modellval | null) {
  if (process.env.GOOGLE_SERVICE_ACCOUNT_JSON && val?.provider !== "vertex" && val?.provider !== "openai") {
    console.error(
      "[email-studio:vertex-konfig] GOOGLE_SERVICE_ACCOUNT_JSON är satt men går inte att läsa " +
        "(JSON, client_email, private_key eller project_id saknas) — Vertex AI används inte."
    );
  }
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

  // 2b) Trunkerad JSON (svar klippt av tokentaket: oppningsstaket finns men
  //     inget avslut, eller avslutande } saknas). new_version ligger FORST i
  //     schemat och ar da komplett aven nar resten klipptes. Faltet plockas
  //     med en JSON-strangtolerant regex och avkodas via JSON.parse av just
  //     strangen, sa "\n" och '\"' blir riktiga tecken.
  {
    const plocka = (falt: string): string | null => {
      const m = trimmed.match(new RegExp('"' + falt + '"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"'));
      if (!m) return null;
      try { return String(JSON.parse('"' + m[1] + '"')).trim(); } catch { return null; }
    };
    const nv = plocka("new_version");
    if (nv) {
      const amnen = trimmed.match(/"subject_suggestions"\s*:\s*\[([\s\S]*?)\]/);
      let subject_suggestions: string[] = [];
      if (amnen) {
        try { subject_suggestions = (JSON.parse("[" + amnen[1] + "]") as unknown[]).map((x) => String(x).trim()).slice(0, 3); } catch {}
      }
      return {
        original_version: null,
        new_version: nv,
        explanation: plocka("explanation") || "",
        subject_suggestions,
        confidence_tips: plocka("confidence_tips") ?? undefined
      };
    }
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

  // 4) Fallback: whole content (last resort) — men ALDRIG JSON-bråte.
  // Uppmätt 2026-09-15: ett svar trunkerat INNE i new_version-strängen
  // passerade hit och kunden fick ```json-skräp presenterat som "Ny
  // version" — och det läckte vidare in i redigeringsfältet. Ser texten
  // ut som ett kodstaket eller ett JSON-objekt är den ett HAVERERAT
  // strukturerat svar, inte en mejltext: returnera tomt så att routens
  // tomt-svar-väg ger den ärliga mallfallbacken i stället.
  if (trimmed.startsWith("```") || trimmed.startsWith("{")) {
    return {
      original_version: null,
      new_version: "",
      explanation: "",
      subject_suggestions: [],
      confidence_tips: undefined
    };
  }
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
type Simuleringsorsak = "anonym" | "ingen modellnyckel" | Modellfelklass;

/**
 * Tipsraden under ett förskrivet svar, per orsak. Den stod förut hårt som
 * "Logga in för att köra åtgärden mot modellen" för VARJE simulering — också
 * när en inloggad kund föll på kvoten. Samma orsaker som editorns
 * SIMULERINGSORSAKER; den här raden är svarets egen, den där är notisen.
 */
const SIMULERINGSTIPS: Record<Simuleringsorsak, string> = {
  anonym: "Demoläge: svaret är förskrivet och kostar inget modellanrop. Logga in för att köra åtgärden mot modellen.",
  "ingen modellnyckel": "Förskrivet förslag utifrån din kontext: AI-hjälpen är inte påslagen i den här miljön.",
  kreditslut:
    "Förskrivet förslag utifrån din kontext: AI-krediterna är slut hos oss, så ingen modell kördes. Din text är orörd.",
  kvot: "AI-leverantörens kvot är slut just nu, så det här är ett förskrivet förslag utifrån din kontext. Prova åtgärden igen om en stund.",
  "tillfälligt fel":
    "Modellen svarade inte just nu, så det här är ett förskrivet förslag utifrån din kontext. Prova åtgärden igen om en liten stund."
};

function simulateAction(
  action: string,
  emailContent: string,
  subject: string,
  context: any = {},
  orsak: Simuleringsorsak = "anonym"
) {
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
    // "Logga in" bara när det är orsaken — en inloggad kund som föll på
    // kvoten ska inte få höra det.
    explanation =
      orsak === "anonym"
        ? "Översättning i demoläge: hela mejlet skrivs på målspråket. Innehållet hålls generellt eftersom demon inte kör någon modell — logga in för en översättning av just den här texten."
        : "Förskriven översättning: hela mejlet skrivs på målspråket, men innehållet hålls generellt eftersom ingen modell kördes. En översättning av just den här texten kräver modellen.";
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
    confidence_tips: SIMULERINGSTIPS[orsak]
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

**HÅRDA UTDATAREGLER — bryts ALDRIG, oavsett åtgärd:**
1. Mejlet får ALDRIG innehålla produktkataloger, paketnamn, priser, volymtak
   eller uppräkningar av vad avsändaren säljer. HÖGST EN kort mening om vad
   avsändaren gör — resten av mejlet handlar om MOTTAGARENS värld.
   (Bakgrund: "Personalisera" klistrade in hela affärskontexten — tre agenter,
   fem paket, priser per månad — i ett kallmejl. Det är motsatsen till
   "ruthlessly short" och avslöjar dessutom intern prisinformation.)
2. BAKGRUND-avsnittet i användarens meddelande är för din förståelse. Det får
   aldrig citeras, sammanfattas eller klistras in i new_version. Det styr TON
   och VINKEL, inte innehåll.
3. Målet med varje mejl är ETT bokat möte. En enda låg-friktions-CTA.
   Inga djupdykningar i erbjudandet — det hör hemma i mötet, inte i mejlet.
4. Brödtexten är högst ~120 ord. Längre är fel även om innehållet är bra.
5. Mottagarens namn: använd ENDAST namnet under "Mejl-kontext → Kontakt".
   Står inget namn där: inled med "Hej," utan namn. Hitta ALDRIG på ett namn,
   och behåll ALDRIG ett namn ur den gamla brödtexten om det motsäger
   Mejl-kontext — den gamla texten kan gälla fel mottagare.
6. Påstå aldrig något om mottagarens bolag som inte står i Signal-fältet.

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
{"new_version":"<den nya mejltexten>","explanation":"<kort, referera specifik princip, t.ex. 'Ruthlessly short enligt cold-email/SKILL.md'>","subject_suggestions":["<2-3 korta, interna, peer-liknande ämnesrader>"],"original_version":null,"confidence_tips":"<valfritt: förväntad reply-rate, compliance-not eller nästa steg>"}

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
 * Modellanrop med omtag: upp till tre försök med exponentiell paus (1 s, 2 s)
 * för transienta fel, varje försök med egen tidsgräns. Budgeten är medvetet
 * räknad mot maxDuration = 60: 3 × 15 s + 3 s paus = 48 s, så routen hinner
 * alltid skriva en egen svarskropp i stället för att dödas utan kropp.
 *
 * Vad som räknas som transient avgör `kanForsokasOm` (lib/llm/kvotfel.ts).
 * Förut togs VARJE 429 om — också kreditslut, där tre anrop mot en tom kredit
 * bara är tre avvisningar och tre sekunders väntan för kunden.
 */
async function generateMedForsok(opts: {
  model: Parameters<typeof generateText>[0]["model"];
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
        // 1800 klipptes mitt i JSON-svaret nar Vertex gemini-2.5-flash drog
        // tanktokens ur SAMMA budget (uppmatt 2026-09-15: svaret slutade utan
        // avslutande staket och kunden sag ra JSON under "Oformaterat svar").
        // Ekot av ursprungstexten i prompten ar ocksa borttaget av samma skal.
        maxOutputTokens: 3000,
        // SDK:n har egna omtag; de stängs av så att loopens tidsbudget håller.
        maxRetries: 0,
        // 15 s var budgeterat mot Vercels maxDuration=60 — men appen kör på
        // Railway, där det taket inte finns. Uppmätt 2026-09-15: Vertex
        // gemini-2.5-flash med tänktokens + 3000-tokensbudget tar ibland
        // >15 s, och kunden fick då mallfallbacken ("Modellen svarade inte
        // just nu") trots att modellen var frisk. 25 s per försök ger
        // 3 × 25 + 3 s paus = 78 s värsta fall — acceptabelt för en knapp
        // som uttryckligen visar arbetsläge, och normalfallet är opåverkat.
        abortSignal: AbortSignal.timeout(25_000),
        // Tänkandet stängs av: Vertex gemini-2.5-flash drar annars en
        // GODTYCKLIG andel av maxOutputTokens till tänktokens (uppmätt
        // 2026-09-15: ett svar klipptes inne i new_version-strängen trots
        // 3000-budget). Googles OpenAI-kompatibla lager mappar
        // reasoning_effort="none" till thinking_budget=0 för 2.5-flash.
        // En knapptryckning i mejleditorn behöver formulering, inte
        // resonemang — samma slutsats som THINKING=disabled i leadskedjan.
        // "none" AVVISAS av Vertex-kompatlagret (uppmätt 2026-09-15, 400:
        // "Expected ... one of: 'high', 'low', 'max', 'medium', 'minimal'");
        // "minimal" är lägsta accepterade och gav 200 i samma mätning.
        providerOptions: { openai: { reasoningEffort: "minimal" } }
      });
      return text;
    } catch (error) {
      sista = error;
      if (!kanForsokasOm(error) || forsok === 2) throw error;
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
  const modell = session.publikDemo ? null : valjModell(process.env);
  if (!session.publikDemo) varnaOmTrasigServiceAccount(modell);
  if (modell === null) {
    const orsak: Simuleringsorsak = session.publikDemo ? "anonym" : "ingen modellnyckel";
    const sim = simulateAction(kandAction, emailContent, subject, context, orsak);

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
        simulated_reason: orsak
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
    // Kontexten delas i två avsnitt med olika kontrakt, i stället för en rå
    // JSON-klump. Med `Context: ${JSON.stringify(...)}` fanns ingen skillnad
    // mellan fakta om mottagaren och avsändarens interna affärskontext — och
    // "Personalisera" klistrade in hela erbjudandet, paketen och priserna i
    // kallmejlet. Mejl-kontexten är det modellen FÅR använda i texten;
    // bakgrunden styr bara ton och vinkel (hård regel 1-2 i systemprompten).
    [
      "Mejl-kontext (fakta om mottagaren — det enda som får synas i mejlet):",
      context.companyName ? `- Företag: ${context.companyName}` : "- Företag: (okänt)",
      context.contactName ? `- Kontakt: ${context.contactName}` : "- Kontakt: (inget namn — inled utan namn)",
      context.signal ? `- Signal / trigger: ${context.signal}` : ""
    ].filter(Boolean).join("\n"),
    (context.offer || context.cta) &&
      [
        "BAKGRUND — avsändarens erbjudande. Får ALDRIG klistras in i mejlet (hård regel 1-2); högst EN kort mening får sammanfatta vad avsändaren gör:",
        context.offer ? `- Erbjudande: ${String(context.offer).slice(0, 800)}` : "",
        context.cta ? `- Önskat nästa steg: ${String(context.cta).slice(0, 200)}` : ""
      ].filter(Boolean).join("\n"),
    `\n\nIMPORTANT: Answer with ONE valid JSON object only, exactly as specified in the system prompt. No prose before or after it.`
  ].filter(Boolean).join('\n\n');

  let text: string;
  try {
    text = await generateMedForsok({
      // Tokenväxlingen för Vertex sker här, INNE i try: ett avvisat
      // service account-konto ska klassas och besvaras som vilket modellfel
      // som helst, inte bli en 500 utan kropp.
      model: await byggSprakmodell(modell),
      system: EMAIL_STUDIO_SYSTEM_PROMPT,
      prompt: userPrompt
    });
  } catch (error: any) {
    /**
     * Modellen svarade inte trots omtagen. Kunden får ALDRIG se leverantörens
     * råtext: diagnosen loggas server-side, och svaret blir det deterministiska
     * förslaget med en ärlig markering om VARFÖR — kreditslut, kvot eller
     * tillfälligt fel är tre olika besked (lib/llm/kvotfel.ts).
     *
     * Loggraden bär status och meddelande, inte hela felobjektet. AI-SDK:ns
     * APICallError har `requestBodyValues`, alltså hela prompten med kundens
     * utkast och mottagarens namn — att logga objektet rakt av skrev
     * kunddata till driftloggen vid varje fel.
     *
     * Taggarna `[email-studio:modellfel]` och `[email-studio:kreditslut]` är
     * stabila med flit: de är det man söker efter i Railways logg.
     */
    const klass = klassaModellfel(error);
    const status = statuskod(error);
    const meddelande = String(error?.message ?? error).slice(0, 300);
    console.error(
      `[email-studio:modellfel] klass=${klass} provider=${modell.provider} modell=${modell.namn} status=${status ?? "-"}`,
      meddelande
    );
    if (klass === "kreditslut") {
      // Nyckeln per dygn speglar `larma_kreditslut` i snajp-support/app/kvotfel.py.
      // Next-appen har ännu ingen väg att skriva platform_events eller skicka
      // det prioriterade mejlet — raden här är larmet tills den finns.
      console.error(
        `[email-studio:kreditslut] larmnyckel=kreditslut:${new Date().toISOString().slice(0, 10)} provider=${modell.provider} — ` +
          "leverantören avvisar anropen (kredit slut eller fakturering avstängd). Varje Email Studio-åtgärd svarar med förskriven text tills det är åtgärdat."
      );
    }
    const sim = simulateAction(kandAction, emailContent, subject, context, klass);
    return NextResponse.json({
      success: true,
      data: {
        ...sim,
        action: kandAction,
        simulated: true,
        simulated_reason: klass
      }
    });
  }

  const rich = parseRichRefine(text);
  // Ett tomt modellsvar får inte se ut som en lyckad omskrivning — då står
  // kundens gamla text kvar under rubriken "Ny version" utan förklaring.
  if (!rich.new_version || !rich.new_version.trim()) {
    console.error(`[email-studio:modellfel] klass=tomt-svar provider=${modell.provider} modell=${modell.namn} åtgärd=${kandAction}`);
    const sim = simulateAction(kandAction, emailContent, subject, context, "tillfälligt fel");
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
      // Explicit false, inte frånvaro: kontrollen i Fas 1 ("svaret returnerar
      // simulated: false") ska gå att läsa rakt ur JSON, och en klient ska
      // aldrig behöva veta att frånvaro råkar betyda samma sak.
      simulated: false,
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
