import { json } from "../_shared/types.ts";

Deno.serve(async (request: Request) => {
  if (request.method !== "POST") {
    return json({ ok: false, error: "Method not allowed" }, 405);
  }

  return json({
    ok: true,
    data: {
      synced: 0,
      classified: 0,
      nextStep: "Connect mailbox provider and persist email_events."
    }
  });
});
