import { json } from "../_shared/types.ts";

type DiscoverRequest = {
  workspaceId: string;
  industries: string[];
  geography: string[];
  signals: string[];
};

Deno.serve(async (request: Request) => {
  if (request.method !== "POST") {
    return json({ ok: false, error: "Method not allowed" }, 405);
  }

  const payload = (await request.json()) as DiscoverRequest;
  if (!payload.workspaceId) {
    return json({ ok: false, error: "workspaceId is required" }, 400);
  }

  return json({
    ok: true,
    data: {
      runId: crypto.randomUUID(),
      status: "queued",
      providerPlan: ["company-websites", "public-news", "business-registers", "job-signals", "manual-notes", "enrichment-adapters"],
      guardrail: "LinkedIn personal profiles require authorized input or a provider adapter."
    }
  });
});
