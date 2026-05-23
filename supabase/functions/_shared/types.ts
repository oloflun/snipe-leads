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

export function json<T>(payload: JsonResponse<T>, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8"
    }
  });
}
