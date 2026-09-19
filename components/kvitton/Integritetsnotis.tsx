import { ShieldCheck } from "lucide-react";

/**
 * Integritetsnotisen — synlig text, inte en länk till en policysida.
 *
 * ## Varför formuleringen ser ut som den gör
 *
 * Första utkastet löd "all bearbetning sker lokalt i din instans". Det är
 * INTE sant: kvittotexten tolkas av en extern AI-modell (Vertex AI/Gemini i
 * drift), så en absolut lokalformulering hade varit en vilseledande
 * marknadsföringsclaim. Texten nedan säger exakt vad som gäller — inget
 * säljs, inget delas utöver AI-tolkningen (under biträdesavtal), och
 * mejlens innehåll sparas inte.
 *
 * Originalet är `INTEGRITETSNOTIS` i snajp-support/app/agent/kvitto_agent.py
 * och följer med API-svaren. Den här kopian är för ögat; ändras den ena ska
 * den andra ändras i samma commit.
 */
export function Integritetsnotis() {
  return (
    <p className="flex items-start gap-2.5 rounded-card border border-ink/12 bg-paper2/40 px-4 py-3.5 text-[0.8125rem] leading-6 text-ink-muted">
      <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-moss" aria-hidden />
      <span>
        Read-only-åtkomst. Inget säljs eller delas med tredje part utöver AI-tjänsten som
        tolkar kvittotexten, under personuppgiftsbiträdesavtal. Mejlens text sparas inte,
        bara kvittofälten, avsändare, ämnesrad och en kontrollsumma.
      </span>
    </p>
  );
}
