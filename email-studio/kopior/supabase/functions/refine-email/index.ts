import { createChatCompletion } from "../_shared/llm.ts";
import { buildEmailStudioPrompt, type EmailStudioAction } from "../_shared/prompts/email-studio.ts";
import { json } from "../_shared/types.ts";

type RefineEmailRequest = {
  subject: string;
  body: string;
  action: EmailStudioAction;
  locale?: "sv" | "en";
  businessContext?: {
    product: string;
    target_audience: string;
    tone: string;
    offer: string;
    cta: string;
  } | null;
  companyName?: string;
  signal?: string;
  offer?: string;
  cta?: string;
  contactName?: string;
};

export type RichRefineResult = {
  original_version?: string | null;
  new_version: string;
  explanation: string;
  subject_suggestions: string[];
  confidence_tips?: string;
  // For special actions
  variants?: string[];
  analysis?: string;
};

function parseRichRefine(content: string): RichRefineResult {
  const trimmed = content.trim();

  // Try direct JSON
  try {
    const p = JSON.parse(trimmed);
    if (p && typeof p.new_version === "string") {
      return {
        original_version: p.original_version ?? null,
        new_version: p.new_version.trim(),
        explanation: (p.explanation || "").trim(),
        subject_suggestions: Array.isArray(p.subject_suggestions) ? p.subject_suggestions.map((s: string) => s.trim()) : [],
        confidence_tips: p.confidence_tips || undefined
      };
    }
  } catch {}

  // Try fenced
  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced) {
    try {
      const p = JSON.parse(fenced[1]);
      if (p && typeof p.new_version === "string") {
        return {
          original_version: p.original_version ?? null,
          new_version: p.new_version.trim(),
          explanation: (p.explanation || "").trim(),
          subject_suggestions: Array.isArray(p.subject_suggestions) ? p.subject_suggestions.map((s: string) => s.trim()) : [],
          confidence_tips: p.confidence_tips || undefined
        };
      }
    } catch {}
  }

  // Fallback: treat whole as new body
  return {
    original_version: null,
    new_version: trimmed,
    explanation: "Agent returnerade oformaterat svar. Använder rå text som ny version.",
    subject_suggestions: [],
    confidence_tips: undefined
  };
}

Deno.serve(async (request: Request) => {
  if (request.method !== "POST") {
    return json({ ok: false, error: "Method not allowed" }, 405);
  }

  try {
    const payload = (await request.json()) as RefineEmailRequest;

    if (!payload.subject || !payload.body || !payload.action) {
      return json({ ok: false, error: "subject, body and action are required" }, 400);
    }

    const prompt = buildEmailStudioPrompt({
      subject: payload.subject,
      body: payload.body,
      action: payload.action,
      locale: payload.locale ?? "sv",
      businessContext: payload.businessContext ?? null,
      companyName: payload.companyName,
      signal: payload.signal,
      offer: payload.offer,
      cta: payload.cta,
      contactName: payload.contactName
    });

    const completion = await createChatCompletion({
      messages: [
        { role: "system", content: prompt.system },
        { role: "user", content: prompt.user }
      ],
      responseFormat: "json_object",
      temperature: 0.4,
      maxTokens: 1800
    });

    const rich = parseRichRefine(completion.content);

    return json({
      ok: true,
      data: {
        ...rich,
        skillCount: prompt.skillCount,
        model: completion.model,
        provider: completion.provider,
        action: payload.action
      }
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return json({ ok: false, error: message }, 500);
  }
});