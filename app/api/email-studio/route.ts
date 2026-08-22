import { NextRequest, NextResponse } from 'next/server';
import { generateText } from 'ai';
import { openai } from '@ai-sdk/openai';
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
    new_version = `${namn}\n\nJag såg ${inled(signal)} hos ${company}. Det brukar vara läget då ${inled(offer)} är som mest värt att titta på.\n\n${cta}?`;
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
    new_version = `${namn}\n\n${signal}. Det är ofta då den här frågan går från "senare" till "nu".\n\n${offer} — anpassat efter hur ni faktiskt jobbar, inte en standardlösning.\n\n${cta}?`;
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
      new_version = `${namn}\n\nJag såg det senaste som hänt hos ${company}. Det brukar vara läget då den här frågan går från "senare" till "nu".\n\nVi tar gärna fram ett förslag som utgår från hur ni faktiskt jobbar.\n\nVill ni att vi skickar över det?`;
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
**Ursprunglig version:** (om relevant)
**Ny version:**
**Förklaring av förändringarna:** (kort, referera specifik princip från marketingskills t.ex. "Ruthlessly short enligt cold-email/SKILL.md + active voice från copywriting")
**Förslag på ämnesrad:** (2–3 stycken, korta, interna, peer-liknande)
**Konfidens / Tips:** (valfritt — t.ex. förväntad reply-rate, compliance-not, förbättringsförslag)

**Few-shot examples (använd som stilguide):**
Exempel 1 (Trigger: Företag expanderar till ny lokal + rekryterar):
Subject: Hyllie-expansionen – hur hanterar ni lokala leverantörer?
Hej Elin,
Såg att Byggkompaniet Syd precis öppnat i Hyllie och stärker teamet. Flera Malmö-bolag vi jobbat med har haft exakt samma utmaning med att snabbt få pålitliga lokala partners på plats utan att tappa tempo.
Vi har hjälpt liknande bolag korta ledtiderna med 40 % genom [specifik proof].
Skulle det vara värt att jag skickar två konkreta exempel från liknande expansioner?
Mvh
[Användarnamn]

Exempel 2 (Trigger: Funding + hiring):
Subject: Series B + nya säljroller – hur ser pipeline ut?
Hej [Namn],
Grattis till Series B:n. När bolag i er storlek börjar skala säljteamet brukar utmaningen vara att hålla kvaliteten i tidiga samtal utan att bränna leads.
Vi har sett [specifik proof] hos liknande SaaS-bolag.
Vore det intressant att höra hur ni tänker kring det just nu?

**Beteende:**
- Var hjälpsam, snabb och proaktiv.
- När användaren skriver "Kortare", "Skriv om", "Förbättra", "Personalisera", "Översätt", "A/B", "Uppföljning" eller "Analysera" → utför omedelbart.
- Använd alltid svensk ton om inte annat anges (modern, rak, vänlig).
- Om kontext saknas: Be om lead-info + signaler först.
- Proaktiv: Efter varje output, föreslå nästa steg (t.ex. "Vill du ha en follow-up-sekvens eller A/B på subject line?").
- Integrera med Snipe-Leads signal-detektering: Använd befintliga expansion/rekrytering/nyhets-signaler automatiskt när de finns.

Du har tillgång till tidigare konversationer och användardata via Supabase för bättre kontext över tid.
`;

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

  try {
    const body = await request.json();
    const { action, draft = '', subject = '', body: emailBody = '', context = {}, locale = 'sv' } = body;
    // userId kommer ur SESSIONEN, aldrig ur request-body. Fältet gick förut
    // att sätta fritt av den som postade, och gick rakt in i prompten som en
    // uppgift om vem anroparen var.
    const userId = session.userId;
    const emailContent = draft || emailBody;

    // Simulation for demo (real LLM needs valid OPENAI_API_KEY)
    const key = process.env.OPENAI_API_KEY || '';
    // Anonym besökare -> alltid simulering. Det är den raden som gör att
    // marknadssidans knappar fungerar utan att en oinloggad kan nå modellen.
    const useSimulation =
      session.publikDemo || !key || key.length < 20 || key.includes('...') || key.includes('din-');
    if (useSimulation) {
      const sim = simulateAction(action, emailContent, subject, context);

      return NextResponse.json({
        success: true,
        data: {
          ...sim,
          action,
        }
      });
    }

    const userPrompt = [
      `Action: ${action}`,
      `Language: ${locale === 'sv' ? 'Swedish (sv-SE)' : 'English'}`,
      subject && `Current subject: ${subject}`,
      emailContent && `Current email body:\n${emailContent}`,
      Object.keys(context).length > 0 && `Context: ${JSON.stringify(context)}`,
      userId && `User ID: ${userId}`,
      `\n\nIMPORTANT: Follow the EXACT output sections in the system prompt. AFTER the sections, ALSO output a single valid JSON object on its own line: {"new_version":"<the new email>","explanation":"<why>","subject_suggestions":["s1","s2"],"original_version":"<orig>","confidence_tips":"..."}. No other text after the JSON.`
    ].filter(Boolean).join('\n\n');

    const { text } = await generateText({
      model: openai('gpt-4o-mini'),
      system: EMAIL_STUDIO_SYSTEM_PROMPT,
      prompt: userPrompt,
      temperature: 0.4,
      maxOutputTokens: 1800,
    });

    const rich = parseRichRefine(text); // reuse or define parse
    return NextResponse.json({
      success: true,
      data: {
        ...rich,
        action,
      }
    });
  } catch (error: any) {
    console.error('Email Studio API error:', error);
    return NextResponse.json(
      { error: error.message || 'Failed to process email studio request' },
      { status: 500 }
    );
  }
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
