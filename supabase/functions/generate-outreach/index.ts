import { json, type OutreachRequest } from "../_shared/types.ts";

Deno.serve(async (request: Request) => {
  if (request.method !== "POST") {
    return json({ ok: false, error: "Method not allowed" }, 405);
  }

  const payload = (await request.json()) as OutreachRequest;

  if (!payload.workspaceId || !payload.companyId || !payload.contactId) {
    return json({ ok: false, error: "workspaceId, companyId and contactId are required" }, 400);
  }

  return json({
    ok: true,
    data: {
      subject: "Signalbaserad öppning för svensk B2B-outbound",
      body:
        "Hej,\n\nJag såg en konkret signal som gör tajmingen relevant. Snipra skulle här generera ett lågmält, specifikt och källbundet mejl baserat på bolagsanalys, business context och suppression-regler.\n\nVill du att jag skickar två exempel?",
      variantLength: payload.length,
      variantType: payload.variantType,
      guardrails: ["sv-SE", "low-pressure", "source-grounded", "no-linkedin-scraping"]
    }
  });
});
