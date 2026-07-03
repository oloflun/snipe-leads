"use server";

import { buildEmailStudioPrompt, type EmailRefineAction } from "@/lib/agent/email-studio-prompt";
import { createChatCompletion } from "@/lib/agent/llm";

export type RefineEmailInput = {
  emailId: string;
  subject: string;
  body: string;
  action: EmailRefineAction;
  locale?: "sv" | "en";
  context?: {
    companyName?: string;
    signal?: string;
    offer?: string;
    cta?: string;
    contactName?: string;
  };
};

export type RefineEmailResult = {
  success: boolean;
  data?: {
    subject: string;
    body: string;
    skillCount: number;
    model: string;
    provider: string;
  };
  error?: string;
};

function parseRefinedEmail(content: string): { subject: string; body: string } {
  const trimmed = content.trim();

  try {
    const parsed = JSON.parse(trimmed) as { subject?: string; body?: string };
    if (parsed.subject && parsed.body) {
      return { subject: parsed.subject.trim(), body: parsed.body.trim() };
    }
  } catch {
    // fall through
  }

  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced) {
    const parsed = JSON.parse(fenced[1]) as { subject?: string; body?: string };
    if (parsed.subject && parsed.body) {
      return { subject: parsed.subject.trim(), body: parsed.body.trim() };
    }
  }

  throw new Error("Kunde inte tolka agentens svar");
}

export async function refineEmail(input: RefineEmailInput): Promise<RefineEmailResult> {
  try {
    const { getWorkspaceContext } = await import("@/lib/workspace");
    const workspaceContext = await getWorkspaceContext();
    const locale = input.locale ?? (workspaceContext?.workspace.locale === "en" ? "en" : "sv");

    const prompt = buildEmailStudioPrompt({
      subject: input.subject,
      body: input.body,
      action: input.action,
      locale,
      businessContext: workspaceContext?.businessContext ?? null,
      companyName: input.context?.companyName,
      signal: input.context?.signal,
      offer: input.context?.offer,
      cta: input.context?.cta,
      contactName: input.context?.contactName
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

    if (workspaceContext && !input.emailId.startsWith("email-")) {
      const { saveEmailDraft } = await import("@/lib/data/emails");
      await saveEmailDraft({
        emailId: input.emailId,
        subject: refined.subject,
        body: refined.body
      });
    }

    return {
      success: true,
      data: {
        subject: refined.subject,
        body: refined.body,
        skillCount: prompt.skillCount,
        model: completion.model,
        provider: completion.provider
      }
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Okänt fel vid omskrivning";
    return { success: false, error: message };
  }
}

export async function persistEmailDraft(input: {
  emailId: string;
  subject: string;
  body: string;
}): Promise<{ success: boolean; error?: string }> {
  const { saveEmailDraft } = await import("@/lib/data/emails");
  return saveEmailDraft(input);
}

