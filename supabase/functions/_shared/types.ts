export type JsonResponse<T> = {
  ok: boolean;
  data?: T;
  error?: string;
};

export type OutreachRequest = {
  workspaceId: string;
  companyId: string;
  contactId: string;
  length: "kort" | "medium" | "lång";
  variantType: "cold" | "followup-1" | "followup-2" | "final";
};

export type EmailRefineAction =
  | "shorter"
  | "more_personal"
  | "clearer_cta"
  | "rewrite"
  | "more_professional"
  | "more_human"
  | "more_persuasive";

export type RefineEmailRequest = {
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

export function json<T>(payload: JsonResponse<T>, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8"
    }
  });
}
