"use server";

import { buildEmailStudioPrompt, type EmailStudioAction } from "@/lib/agent/email-studio-prompt";
import { createChatCompletion } from "@/lib/agent/llm";

export type RefineEmailInput = {
  emailId: string;
  subject: string;
  body: string;
  action: EmailStudioAction;
  locale?: "sv" | "en";
  context?: {
    companyName?: string;
    signal?: string;
    offer?: string;
    cta?: string;
    contactName?: string;
  };
};

export type RichRefineData = {
  original_version?: string | null;
  new_version: string;
  explanation: string;
  subject_suggestions: string[];
  confidence_tips?: string;
  skillCount?: number;
  model?: string;
  provider?: string;
  action?: string;
};

export type RefineEmailResult = {
  success: boolean;
  data?: RichRefineData & { subject?: string; body?: string }; // compat + rich
  error?: string;
};

function parseRichRefine(content: string): { new_version: string; explanation: string; subject_suggestions: string[]; original_version?: string | null; confidence_tips?: string } {
  const trimmed = content.trim();
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
  return {
    original_version: null,
    new_version: trimmed,
    explanation: "Oformaterat svar från agenten.",
    subject_suggestions: [],
    confidence_tips: undefined
  };
}

export async function refineEmail(input: RefineEmailInput): Promise<RefineEmailResult> {
  const { getWorkspaceContext } = await import("@/lib/workspace");
  const workspaceContext = await getWorkspaceContext();
  const locale = input.locale ?? (workspaceContext?.workspace.locale === "en" ? "en" : "sv");

  const originalBody = input.body;
  const originalSubject = input.subject;

  let newBody = originalBody;
  let explanation = "";
  let newSubject = originalSubject;
  let subjectSuggestions: string[] = [originalSubject];
  let confidence = "Demo mode: simulated change (real LLM requires valid API key).";

  const action = input.action;
  const lowerBody = originalBody.toLowerCase();

  const company = input.context?.companyName || "Byggkompaniet Syd";
  const signal = input.context?.signal || "Hyllie-expansionen och rekrytering";
  const offer = input.context?.offer || "AI-driven outbound";

  if (action === "shorter") {
    newBody = `Hej,\n\nSåg att ${company} växlar upp i Hyllie och söker arbetsledare. Rätt lokala fastighetsägare är värda mer än generiska leads.\n\nVi har hjälpt liknande team korta ledtiderna rejält med signalstyrda, personliga mejl.\n\nVill du ha två exempel?`;
    explanation = "Ruthlessly short enligt cold-email/SKILL.md – tog bort utfyllnad, behöll kärnsignal + låg-friktion CTA.";
    newSubject = originalSubject.length > 40 ? originalSubject.substring(0, 40) + "..." : originalSubject;
    subjectSuggestions = [newSubject, "Expansionen i Hyllie – relevanta leads?"];
    confidence = "Demo: ruthlessly short.";
  } else if (action === "rewrite") {
    newBody = `Hej,\n\n${signal} hos ${company} är klassisk köpsignal. Många B2B-bolag har samma utmaning: att snabbt få pålitliga lokala aktörer utan att tappa fart.\n\n${offer} har hjälpt team gå från breda listor till 3–5 högintressanta kontakter per vecka.\n\nSkulle det vara värt att titta på för just er?`;
    explanation = "Skriv om med ny vinkel (Observation → Proof → Ask) enligt copywriting + cold-email. Mänsklig peer-ton.";
    newSubject = "Omskriven: " + originalSubject;
    subjectSuggestions = [`${company.split(" ")[0]}-expansionen – lokala leverantörer?`, originalSubject];
    confidence = "Demo: omskriven med bättre struktur.";
  } else if (action === "improve") {
    newBody = `Hej,\n\n${signal}. Det är ofta då kvaliteten på lokala partners avgör om man håller tidplanen.\n\nVi har sett hur ${offer.toLowerCase()} kan ge 2–4 kvalificerade dialoger per vecka baserat på signaler – utan spam.\n\nVill du se två exempel från liknande expansioner?`;
    explanation = "Förbättrad: tydligare värde, specifik proof, låg-friktion CTA enligt copywriting.";
    newSubject = "Förbättrad: " + originalSubject;
    subjectSuggestions = [newSubject, "2 exempel från er expansion?"];
    confidence = "Demo: förbättrad text.";
  } else if (action === "personalize") {
    newBody = `Hej,\n\nSåg att ${company} precis öppnat i Hyllie och stärker teamet. Flera kunder har haft exakt samma tajmingutmaning: lokala partners snabbt utan att sänka krav.\n\nVi har hjälpt dem korta ledtiderna 30–45 %.\n\nSkulle två konkreta exempel vara intressant?`;
    explanation = "Personalisering med specifik signal (Hyllie + rekrytering) per cold-email.";
    newSubject = "Personligt: " + originalSubject;
    subjectSuggestions = [newSubject];
    confidence = "Demo: personaliserad.";
  } else if (action === "translate") {
    if (locale === "sv") {
      newBody = originalBody.replace(/Hello|Hi/gi, "Hej").replace(/expand|growth/gi, "expanderar");
    } else {
      newBody = originalBody.replace(/Hej/gi, "Hello").replace(/expanderar/gi, "expanding");
    }
    explanation = "Översätt demo (sv/en) – behåller ton.";
    newSubject = originalSubject;
    subjectSuggestions = [newSubject];
    confidence = "Demo: översatt.";
  } else if (action === "ab_variants") {
    newBody = `Variant A (pain):\n${originalBody}\n\nVariant B (opportunity):\nHej,\n\n${signal} hos ${company} öppnar ett fönster. ${offer} gett team högintressanta kontakter under expansion. Två exempel?`;
    explanation = "A/B-varianter (pain vs opportunity) per ab-testing/SKILL.md.";
    newSubject = originalSubject;
    subjectSuggestions = [originalSubject + " (A)", originalSubject + " (B)"];
    confidence = "Demo: två varianter.";
  } else if (action === "followup") {
    newBody = originalBody + `\n\n--- Uppföljning ---\nHej igen,\n\nVi har sett två specifika fastighetsägare nära Hyllie som annonserar renoveringar. Relevant att titta på?`;
    explanation = "Uppföljning adderar nytt värde (ny specifik info) per emails/SKILL.";
    newSubject = "Uppföljning: " + originalSubject;
    subjectSuggestions = [newSubject, "Nya signaler nära expansionen"];
    confidence = "Demo: uppföljning.";
  } else if (action === "analyze") {
    newBody = originalBody;
    explanation = "Analys: 7.5/10. Bra signal + ton. Kan kortas (ta bort utfyllnad). Stark potential. Förväntad reply 8-15%.";
    newSubject = originalSubject;
    subjectSuggestions = [originalSubject];
    confidence = "Demo: analys + betyg.";
  } else {
    newBody = originalBody + " [ändrad för demo]";
    explanation = "Standard ändring.";
  }

  const rich = {
    original_version: originalBody,
    new_version: newBody,
    explanation,
    subject_suggestions: subjectSuggestions,
    confidence_tips: confidence,
  };

  const newS = rich.subject_suggestions?.[0] || input.subject;
  const newB = rich.new_version;

  if (workspaceContext && !input.emailId.startsWith("email-")) {
    const { saveEmailDraft } = await import("@/lib/data/emails");
    await saveEmailDraft({
      emailId: input.emailId,
      subject: newS,
      body: newB
    });
  }

  return {
    success: true,
    data: {
      ...rich,
      subject: newS,
      body: newB,
      skillCount: 0,
      model: "demo-simulator",
      provider: "demo",
      action: input.action,
    },
  };
}

export async function persistEmailDraft(input: {
  emailId: string;
  subject: string;
  body: string;
}): Promise<{ success: boolean; error?: string }> {
  const { saveEmailDraft } = await import("@/lib/data/emails");
  return saveEmailDraft(input);
}

