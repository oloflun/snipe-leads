import { json } from "../_shared/types.ts";

Deno.serve(async (request: Request) => {
  if (request.method !== "POST") {
    return json({ ok: false, error: "Method not allowed" }, 405);
  }

  return json({
    ok: true,
    data: {
      queued: 0,
      sendWindow: "Tue-Thu 08:30-15:20 Europe/Stockholm",
      stopOnReply: true
    }
  });
});
