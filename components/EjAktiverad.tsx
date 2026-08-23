"use client";

import { Clock } from "lucide-react";

/**
 * "Din arbetsyta aktiveras" — det en NY kund ska möta, inte ett 409.
 *
 * ## Vad den ersätter
 *
 * `requireSnajpTenant()` svarar 409 med texten "Arbetsytan är inte kopplad till
 * någon kund ännu. Sätt workspaces.slug och ss_tenant_id." Den meningen är
 * skriven för den som ska laga något, och den är rätt sak att säga till OSS.
 * Den gick rakt genom proxyn och ut i gränssnittet, så en kund som registrerat
 * sig och klickade på Kundtjänst möttes av en instruktion om databaskolumner.
 *
 * ## Varför läget finns kvar över huvud taget
 *
 * Det vore tekniskt möjligt att skapa tenanten automatiskt vid registrering —
 * testarbetsytor får sin så. För en RIKTIG kund är det ett medvetet nej:
 * lib/snajp/testtenant.ts skriver ut varför. En människa väljer sluggen,
 * kontrollerar organisationsnumret och lägger upp kunskapsbasen. En delad eller
 * felvald tenant betyder delad inkorg och delad kunskapsbas, och
 * grundningsgrinden kan inte se att en artikel kom från fel företag.
 *
 * Väntetiden är alltså designad. Det som inte var designat var att den såg ut
 * som ett fel.
 *
 * ## Ton
 *
 * Neutral, inte larmande: ingen röd ram, ingen varningstriangel. Ingenting är
 * trasigt och kunden behöver inte göra något. Därför `bg-paper2` och en klocka,
 * inte `ochre` som bär tillstånd som VÄNTAR på användaren.
 */
export function EjAktiverad({ yta }: Readonly<{ yta?: string }>) {
  return (
    <div className="rounded-input border border-ink/15 bg-paper2/60 px-5 py-6">
      <div className="flex items-start gap-3">
        <Clock className="mt-0.5 h-4 w-4 shrink-0 text-mineral" aria-hidden />
        <div className="min-w-0">
          <p className="text-[1.0625rem] font-semibold tracking-[-0.01em] text-ink">
            Din arbetsyta aktiveras
          </p>
          <p className="mt-2 max-w-[62ch] text-[15px] leading-7 text-ink/70">
            {yta ? `${yta} är` : "Den här vyn är"} redo så fort vi kopplat er till agenterna. Vi
            går igenom er webbplats och bygger kunskapsbasen först — det är den som gör att svaren
            blir era och inte generiska.
          </p>
          <p className="mt-3 max-w-[62ch] text-[15px] leading-7 text-ink/55">
            Du behöver inte göra något. Hör gärna av dig om det dröjer.
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * Känner igen läget i ett proxysvar.
 *
 * Läser `kod` och inte meddelandetexten: texten kan skrivas om, koden är
 * kontraktet (se SnajpTenantKod i lib/snajp/tenant.ts). Statuskoden ensam
 * räcker inte — 409 används även för en kopplad kund vars nyckel saknas, och
 * det är ett driftfel som ska synas som ett fel.
 */
export function arEjAktiverad(status: number, kropp: unknown): boolean {
  return (
    status === 409 &&
    typeof kropp === "object" &&
    kropp !== null &&
    (kropp as { kod?: string }).kod === "ej_aktiverad"
  );
}
