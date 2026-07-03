import { createChatCompletion } from "../_shared/llm.ts";
import { buildEmailStudioPrompt, type EmailRefineAction } from "../_shared/prompts/email-studio.ts";
import { json } from "../_shared/types.ts";

type RefineEmailRequest = {
  subject: string;
  body: string;
  action: EmailRefineAction;
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

function parseRefinedEmail(content: string) {
  const trimmed = content.trim();

  try {
    const parsed = JSON.parse(trimmed) as { subject?: string; body?: string };
    if (parsed.subject && parsed.body) {
      return { subject: parsed.subject.trim(), body: parsed.body.trim() };
    }
  } catch {
    // continue
  }

  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced) {
    const parsed = JSON.parse(fenced[1]) as { subject?: string; body?: string };
    if (parsed.subject && parsed.body) {
      return { subject: parsed.subject.trim(), body: parsed.body.trim() };
    }
  }

  throw new Error("Could not parse refined email");
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
      temperature: 0.35,
      maxTokens: 1400
    });

    const refined = parseRefinedEmail(completion.content);

    return json({
      ok: true,
      data: {
        subject: refined.subject,
        body: refined.body,
        skillCount: prompt.skillCount,
        model: completion.model,
        provider: completion.provider
      }
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return json({ ok: false, error: message }, 500);
  }
});