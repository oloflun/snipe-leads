import { NextRequest, NextResponse } from 'next/server';
import { generateText } from 'ai';
import { openai } from '@ai-sdk/openai';
import { getWorkspaceContext } from '@/lib/workspace';

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

function simulateAction(action: string, emailContent: string, subject: string, context: any = {}) {
  const orig = emailContent || "Hej,\n\n...";
  const company = context?.companyName || "Byggkompaniet Syd";
  const signal = context?.signal || "Hyllie-expansionen och rekrytering av arbetsledare";
  const offer = context?.offer || "AI-driven outbound";
  const ctaBase = context?.cta || "Vill du att jag skickar två exempel";

  let new_version = orig;
  let explanation = "Demo: ändring baserad på marketingskills (cold-email, copywriting).";
  let subject_suggestions: string[] = [subject || "Intressant tajming"];

  if (action === "shorter") {
    // Ruthlessly short: hook + signal + 1 proof + soft CTA. ~40-60% length
    new_version = `Hej,\n\nSåg att ${company} växlar upp i Hyllie och söker arbetsledare. Rätt lokala fastighetsägare är värda mer än generiska leads.\n\nVi har hjälpt liknande team korta ledtiderna rejält med signalstyrda, personliga mejl.\n\n${ctaBase}?`;
    explanation = "Ruthlessly short enligt cold-email/SKILL.md. Tog bort utfyllnad, behöll kärnsignal + låg-friktion CTA. Aktiv, peer-ton.";
    subject_suggestions = [
      subject ? subject.substring(0, 38) + (subject.length > 38 ? "..." : "") : "Hyllie – lokala partners?",
      "Expansionen i Hyllie – relevanta leads?"
    ];
  } else if (action === "rewrite") {
    // New angle, same facts, better structure: observation → relevance → value → ask
    new_version = `Hej,\n\n${signal} hos ${company} är klassisk köpsignal för er typ av tjänst. Många B2B-bolag i Malmö-området har samma utmaning just nu: att snabbt få tag i pålitliga lokala aktörer utan att tappa fart.\n\n${offer} har hjälpt team i exakt den situationen att gå från breda listor till 3–5 högintressanta kontakter per vecka.\n\nSkulle det vara värt att titta på hur det skulle se ut för just er?`;
    explanation = "Skriv om med ny vinkel (Observation → Problem/Proof → Ask) per copywriting + cold-email. Mänsklig ton, ingen vendor-speak.";
    subject_suggestions = [
      `${company.split(" ")[0]}-expansionen – lokala leverantörer?`,
      "Signalbaserad prospektering för Hyllie",
      subject || "Hyllie-expansionen och fler lokala byggdialoger"
    ];
  } else if (action === "improve") {
    new_version = `Hej,\n\n${signal}. Det är ofta då kvaliteten på lokala partners avgör om man håller tidplanen eller inte.\n\nVi har sett hur ${offer.toLowerCase()} kan ge 2–4 kvalificerade dialoger per vecka baserat på just sådana signaler – utan cold spam.\n\nVill du se två exempel från liknande expansioner i regionen?`;
    explanation = "Förbättrad: tydligare värdeprop, aktiv röst, specifik proof, låg-friktion CTA. Enligt copywriting/SKILL.md + cold-email.";
    subject_suggestions = [subject ? "Bättre: " + subject : "Hyllie + relevanta leads", "2 exempel från er expansion?"];
  } else if (action === "personalize") {
    new_version = `Hej,\n\nSåg att ${company} precis öppnat i Hyllie och stärker teamet med fler arbetsledare. Flera av våra kunder i bygg/fastighet har haft exakt samma tajmingutmaning: att få lokala partners på plats snabbt utan att sänka kvalitetskraven.\n\nVi har hjälpt dem korta ledtiderna med 30–45 % genom signalstyrd prospektering.\n\nSkulle två konkreta exempel från Malmö-bolag i liknande läge vara intressant?`;
    explanation = "Personalisering vävd in från signal (Hyllie + rekrytering). Specifik, icke-uppenbar, per cold-email och marketing-psychology.";
    subject_suggestions = ["Hyllie-expansionen – lokala partners på plats?", subject || "Hyllie-expansionen och fler lokala byggdialoger"];
  } else if (action === "translate") {
    // Simple toggle sv/en for demo
    const isSv = /hej|ni |såg att/i.test(orig);
    if (isSv) {
      new_version = orig
        .replace(/Hej /gi, "Hi ")
        .replace(/ni /gi, "you ")
        .replace(/Såg att /gi, "Noticed that ")
        .replace(/Vill du att jag skickar två exempel/g, "Would you like me to send two examples");
    } else {
      new_version = orig
        .replace(/Hi /gi, "Hej ")
        .replace(/you /gi, "ni ")
        .replace(/Noticed that /gi, "Såg att ")
        .replace(/Would you like me to send two examples/g, "Vill du att jag skickar två exempel");
    }
    explanation = "Översättning demo (sv ↔ en). Behåller ton och fakta.";
    subject_suggestions = [subject || "Translated subject"];
  } else if (action === "ab_variants") {
    new_version = `Variant A (pain):\n${orig.replace(/Vill du att jag/, "Skulle det lösa ert problem om jag")}\n\nVariant B (opportunity):\nHej,\n\n${signal} hos ${company} öppnar ett fönster. Vi har sett hur ${offer.toLowerCase()} gett team exakt den typen av kvalificerade kontakter de behöver under expansion. Två exempel?`;
    explanation = "A/B-varianter med olika vinklar (pain vs opportunity) enligt ab-testing/SKILL.md.";
    subject_suggestions = [subject + " (A)", subject + " (B)", "Alternativ vinkel för expansionen"];
  } else if (action === "followup") {
    new_version = `${orig}\n\n--- Uppföljning ---\nHej igen,\n\nFörra veckan nämnde jag signalerna kring Hyllie. Vi har nu sett två specifika fastighetsägare i närheten som precis annonserat renoveringar. Skulle det vara relevant att titta på dem?`;
    explanation = "Uppföljning som adderar nytt värde (ny specifik info) – inte bara 'kollar in'. Per emails/SKILL.md.";
    subject_suggestions = ["Uppföljning: Hyllie-renoveringar", "Två nya signaler nära er expansion"];
  } else if (action === "analyze") {
    new_version = orig; // keep original for analyze
    explanation = "Analys: 7.5/10. Bra signalanvändning och peer-ton. Kan göras ruthlessly kortare (ta bort 'Det brukar vara ett läge...'). Stark potential enligt cold-email + copy-editing. Förväntad reply-rate: 8-15%.";
    subject_suggestions = [subject || "Analyserad version"];
  } else if (action === "longer" || action === "expand") {
    new_version = orig + `\n\nExtra kontext: Hos liknande bolag som integrerat ${offer.toLowerCase()} under expansion har man sett 40 % kortare tid till första möte. Vi kan anpassa exakt efter era kriterier för fastighetsägare. Låt mig veta om du vill ha en kort översikt över 3–4 aktuella leads.`;
    explanation = "Utökad version: la till proof + erbjudande om mer värde. Balanserad längd per copywriting.";
    subject_suggestions = [subject, "Mer om expansionen i Hyllie"];
  } else {
    new_version = orig + `\n\n[${action} tillämpad – se marketingskills för principer]`;
    explanation = `Åtgärd: ${action}`;
  }

  return {
    original_version: orig,
    new_version: new_version.trim(),
    explanation,
    subject_suggestions,
    confidence_tips: "Demo-läge (marketingskills). Ersätt OPENAI_API_KEY med giltig nyckel för riktig LLM."
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
 * Sessionsgrind. Routen anropar generateText mot OpenAI och var anonymt
 * nåbar — samma hålklass som catch-all-proxyn, men med en direkt kostnad:
 * vem som helst kunde bränna OPENAI_API_KEY genom att posta hit i en loop.
 *
 * Den togs inte upp i plattformsplanens Fas 1, som handlade om
 * snajp-support-proxyn. Den fanns ändå, och INV-SEC-010 hittar den.
 */
async function requireSession() {
  const context = await getWorkspaceContext();
  if (!context) {
    return { denied: NextResponse.json({ error: "Du måste vara inloggad." }, { status: 401 }) };
  }
  return { userId: context.user.id };
}

export async function POST(request: NextRequest) {
  const session = await requireSession();
  if (session.denied) return session.denied;

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
    const useSimulation = !key || key.length < 20 || key.includes('...') || key.includes('din-');
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
  const session = await requireSession();
  if (session.denied) return session.denied;

  return NextResponse.json({
    message: 'Email Studio API route. POST with { action, subject, body, context? } to get the system prompt + request data.',
    systemPromptLength: EMAIL_STUDIO_SYSTEM_PROMPT.length,
  });
}
