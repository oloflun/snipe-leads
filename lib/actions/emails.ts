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
      temperature: 0.4,
      maxTokens: 1800
    });

    const rich = parseRichRefine(completion.content);

    // For simple replace actions, use first line-ish or keep existing subject if not changed in rich
    const newSubject = rich.subject_suggestions?.[0] || input.subject;
    const newBody = rich.new_version;

    if (workspaceContext && !input.emailId.startsWith("email-")) {
      const { saveEmailDraft } = await import("@/lib/data/emails");
      await saveEmailDraft({
        emailId: input.emailId,
        subject: newSubject,
        body: newBody
      });
    }

    return {
      success: true,
      data: {
        ...rich,
        subject: newSubject,
        body: newBody,
        skillCount: prompt.skillCount,
        model: completion.model,
        provider: completion.provider,
        action: input.action
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

