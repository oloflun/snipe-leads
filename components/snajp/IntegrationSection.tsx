"use client";

import { KeyRound, Plug, Webhook } from "lucide-react";
import { Badge } from "@/components/ui";
import { useLocale } from "@/lib/i18n";

const endpoints = [
  { method: "POST", path: "/api/chat", note: { sv: "Skicka kundmeddelande → 202 + job_id", en: "Submit customer message → 202 + job_id" } },
  { method: "GET", path: "/api/jobs/{job_id}", note: { sv: "Polla tills svaret är klart", en: "Poll until the reply is ready" } },
  { method: "POST", path: "/api/triage", note: { sv: "Sortera en batch mail i fack + utkast", en: "Sort a batch of emails + drafts" } },
  { method: "GET", path: "/api/tickets/{id}", note: { sv: "Hämta ärende med hela historiken", en: "Fetch ticket with full history" } },
  { method: "GET", path: "/api/customers/{id}/history", note: { sv: "Kundens samtliga ärenden (CRM)", en: "Customer's full ticket record (CRM)" } },
  { method: "POST", path: "/api/keys", note: { sv: "Utfärda API-nyckel per kund (master)", en: "Issue per-tenant API key (master)" } }
];

const curlExample = `curl -X POST https://api.snipra.se/snajp-support/api/chat \\
  -H "X-API-Key: snajp_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "Min faktura drogs två gånger",
    "channel": "email",
    "customer_email": "kund@example.com",
    "attachments": [{ "data_url": "data:image/jpeg;base64,..." }]
  }'`;

export function IntegrationSection() {
  const { text } = useLocale();

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="space-y-6">
        <div className="rounded-[10px] border border-ink/12 bg-paper p-6 shadow-hairline">
          <div className="flex items-center gap-2">
            <Plug className="h-4 w-4 text-ochre" />
            <h3 className="font-semibold">{text({ sv: "Headless via API", en: "Headless via API" })}</h3>
          </div>
          <p className="mt-3 text-sm leading-6 text-ink/65">
            {text({
              sv: "Agenten är helt headless: samma backend som driver demon ovan exponeras som ett REST-API. Koppla ert affärssystem, e-postflöde eller webbformulär direkt mot endpointsen — varje kund får en egen API-nyckel och all historik lagras som ett komplett CRM i PostgreSQL.",
              en: "The agent is fully headless: the same backend that powers the demo above is exposed as a REST API. Wire your business system, email flow or web form straight to the endpoints — each customer gets their own API key and all history is stored as a complete CRM in PostgreSQL."
            })}
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <tbody className="divide-y divide-ink/10">
                {endpoints.map((endpoint) => (
                  <tr key={endpoint.path}>
                    <td className="py-2.5 pr-3">
                      <Badge tone={endpoint.method === "POST" ? "warn" : "neutral"}>{endpoint.method}</Badge>
                    </td>
                    <td className="py-2.5 pr-3 font-mono text-xs">{endpoint.path}</td>
                    <td className="py-2.5 text-xs text-ink/60">{text(endpoint.note)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-[10px] border border-ink/12 bg-paper p-6 shadow-hairline">
          <div className="flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-ochre" />
            <h3 className="font-semibold">{text({ sv: "API-nycklar per kund", en: "Per-tenant API keys" })}</h3>
          </div>
          <p className="mt-3 text-sm leading-6 text-ink/65">
            {text({
              sv: "Varje företag som ansluter får en egen nyckel (snajp_live_…). Nyckeln skickas i X-API-Key-headern, lagras enbart som SHA-256-hash och kan spärras per kund. Er data isoleras per nyckel.",
              en: "Each connecting company gets its own key (snajp_live_…). The key is sent in the X-API-Key header, stored only as a SHA-256 hash, and can be revoked per tenant. Data is isolated per key."
            })}
          </p>
        </div>

        <div className="rounded-[10px] border border-ink/12 bg-paper p-6 shadow-hairline">
          <div className="flex items-center gap-2">
            <Webhook className="h-4 w-4 text-ochre" />
            <h3 className="font-semibold">{text({ sv: "Kanaler & webhooks", en: "Channels & webhooks" })}</h3>
          </div>
          <p className="mt-3 text-sm leading-6 text-ink/65">
            {text({
              sv: "Web, e-post och WhatsApp har egna tonlägen och maxlängder. Inkommande mail kan pekas mot triage-endpointen via er e-postleverantörs webhook — svaren hamnar färdiga som utkast i ert system, eller skickas automatiskt.",
              en: "Web, email and WhatsApp have their own tone and length settings. Inbound email can be pointed at the triage endpoint via your email provider's webhook — replies land as ready drafts in your system, or are sent automatically."
            })}
          </p>
        </div>
      </div>

      <div className="rounded-[10px] border border-ink/15 bg-ink p-6 text-paper shadow-lift">
        <p className="kicker text-paper/50">Exempel · cURL</p>
        <pre className="mt-4 overflow-x-auto font-mono text-xs leading-6 text-paper/85">
          <code>{curlExample}</code>
        </pre>
        <div className="mt-6 border-t border-paper/15 pt-5">
          <p className="kicker text-paper/50">{text({ sv: "Svar (jobb klart)", en: "Response (job done)" })}</p>
          <pre className="mt-3 overflow-x-auto font-mono text-xs leading-6 text-paper/85">
            <code>{`{
  "status": "completed",
  "result": {
    "reply": "Hej! Tack för att du hör av dig…",
    "category": "betalning",
    "ticket_id": "9f2c…",
    "sentiment": 0.4,
    "escalated": false,
    "kb_sources": [{ "title": "Dubbeldragning…", "similarity": 0.91 }]
  }
}`}</code>
          </pre>
        </div>
      </div>
    </div>
  );
}
