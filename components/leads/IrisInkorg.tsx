"use client";

import { useCallback, useEffect, useState } from "react";
import { SkickatLista, type SkickatRad } from "@/components/leads/SkickatLista";
import type { Signatur } from "@/components/leads/IrisGranskning";
import { Dashboard } from "@/components/snajp/Dashboard";
import { chip, chipAktiv, chipInaktiv, chiplista } from "@/components/ui";
import { felmeddelande } from "@/lib/http/json";
import { useLocale } from "@/lib/i18n";
import { leadsAnrop } from "@/lib/leads/suite";
import { LEADS_UPPDATERADE } from "@/lib/leads/utkast";
import { cn } from "@/lib/utils";

/**
 * Leads › Inkorg (plan del D, migration 084; flikarna Fas 4, 2026-10-08).
 *
 * **Inkommande** är samma vy som kundtjänstinkorgen, filtrerad på
 * klass='lead': svar från prospekt och nya inkommande leads, sorterade dit av
 * reglerna eller Jev i app/email_pipeline/klassning.py. En kund med bara
 * leads-paketet kopplar sin brevlåda med syfte "leads" (Inställningar ›
 * Inkorgar) och får allt hit. Ett supportutkast skrivs aldrig för en rad här.
 *
 * **Skickat** är varje leadsmejl som gått ut (GET /leads/skickat), med
 * leadets nuvarande status och filter. Kontaktade leads tar inte längre plats
 * i Iris-listan; de bor här, och ett svar flyttar dem mellan filtren.
 * Adressen bär fliken (`?vy=inkorg&flik=skickat`), så Iris-listans
 * Skickat-chip länkar hit.
 */
export function IrisInkorg({
  flik = "inkommande",
  onFlik,
  onValjLead
}: Readonly<{
  flik?: "inkommande" | "skickat";
  onFlik?: (flik: "inkommande" | "skickat") => void;
  onValjLead?: (prospektId: string) => void;
}> = {}) {
  const { text } = useLocale();
  const [rader, setRader] = useState<SkickatRad[] | null>(null);
  const [signatur, setSignatur] = useState<Signatur | null>(null);
  const [fel, setFel] = useState<string | null>(null);

  const hamta = useCallback(async () => {
    try {
      const svar = await leadsAnrop<{ skickat?: SkickatRad[]; signatur?: Signatur }>("/leads/skickat?limit=500");
      setRader(svar.skickat ?? []);
      setSignatur(svar.signatur ?? null);
      setFel(null);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
      setRader((nu) => nu ?? []);
    }
  }, []);

  // Antalet står på fliken, så listan hämtas direkt; den hämtas om när ett
  // utskick, ett svar eller en massåtgärd ändrat något.
  useEffect(() => {
    void hamta();
    const uppdatera = () => void hamta();
    window.addEventListener(LEADS_UPPDATERADE, uppdatera);
    return () => window.removeEventListener(LEADS_UPPDATERADE, uppdatera);
  }, [hamta]);

  const flikar = [
    { id: "inkommande" as const, etikett: text({ sv: "Inkommande", en: "Incoming" }), antal: null },
    { id: "skickat" as const, etikett: text({ sv: "Skickat", en: "Sent" }), antal: rader?.length ?? null }
  ];

  return (
    <div className="space-y-6">
      <ul className={chiplista} aria-label={text({ sv: "Inkorgens vyer", en: "Inbox views" })}>
        {flikar.map((f) => (
          <li key={f.id}>
            <button
              type="button"
              aria-pressed={flik === f.id}
              onClick={() => onFlik?.(f.id)}
              className={cn(chip, flik === f.id ? chipAktiv : chipInaktiv)}
            >
              {f.etikett}
              {f.antal !== null ? (
                <>
                  {" "}
                  <span className={cn("num tabular-nums", flik === f.id ? "text-paper-muted" : "text-ink-subtle")}>
                    {f.antal}
                  </span>
                </>
              ) : null}
            </button>
          </li>
        ))}
      </ul>
      {flik === "skickat" ? (
        <SkickatLista rader={rader} fel={fel} onValj={onValjLead} filtrerbar signatur={signatur} />
      ) : (
        <Dashboard lager="leads" />
      )}
    </div>
  );
}
