"use client";

import { Check, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useLocale } from "@/lib/i18n";
import { bytPlan } from "@/lib/actions/plan";
import { PAKET, PRIS_PREFIX, formateraPris } from "@/lib/pricing";
import { cn } from "@/lib/utils";

/**
 * Paketväxlingen — Leads, Kundtjänst eller båda.
 *
 * ## Vad ett byte faktiskt gör
 *
 * Skriver `workspaces.products`, alltså SAMMA kolumn som grindar varje flik och
 * varje inställningssida. Det finns ingen separat plan vid sidan av
 * entitlementen; paketet ÄR den. Det är därför navigationen ändrar sig direkt
 * efter ett byte, och varför det inte går att hamna i ett läge där fakturan
 * säger en sak och produkten en annan.
 *
 * ## Varför ett bekräftelsesteg på nedgraderingar
 *
 * En uppgradering ger mer och behöver inget skydd. En NEDGRADERING tar bort en
 * agent ur arbetsytan med ett klick, och den agentens vyer försvinner ur menyn
 * i samma sekund. Data raderas inte — men det syns inte på knappen, och en
 * kund som tror att ett felklick slängde deras kunskapsbas har haft en dålig
 * dag i onödan. Rutan säger vad som händer och vad som inte gör det.
 *
 * ## Varför inte en <select>
 *
 * Tre alternativ med pris och en rad förklaring vardera. En rullgardin döljer
 * två av dem bakom ett klick, och just de två är det man jämför med.
 */

const ORDNING = ["leads", "support", "duo"] as const;

export function Planvaljare({
  aktivtPaket
}: Readonly<{ aktivtPaket: string | undefined }>) {
  const { text } = useLocale();
  const router = useRouter();

  const [valt, setValt] = useState<string | undefined>(aktivtPaket);
  const [bekraftar, setBekraftar] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [klart, setKlart] = useState<string | null>(null);

  const paket = ORDNING.map((id) => PAKET.find((p) => p.id === id)).filter(
    (p): p is (typeof PAKET)[number] => Boolean(p)
  );

  /** Nedgradering = det nya paketet ger färre produkter än det nuvarande. */
  function arNedgradering(nyttId: string): boolean {
    return valt === "duo" && nyttId !== "duo";
  }

  function valj(nyttId: string) {
    setFel(null);
    setKlart(null);
    if (nyttId === valt) return;
    if (arNedgradering(nyttId)) {
      setBekraftar(nyttId);
      return;
    }
    void genomfor(nyttId);
  }

  async function genomfor(nyttId: string) {
    setBekraftar(null);
    setBusy(nyttId);
    setFel(null);
    try {
      const svar = await bytPlan(nyttId);
      if (!svar.success) {
        setFel(svar.error ?? "Kunde inte byta paket.");
        return;
      }
      setValt(nyttId);
      setKlart("Paketet är bytt. Menyn och agentvyerna följer med direkt.");
      // Serverkomponenterna — navigationen, flikraden, inställningsmenyn —
      // läser products på servern. Utan refresh står den gamla menyn kvar tills
      // användaren råkar navigera om.
      router.refresh();
    } catch (orsak) {
      setFel(orsak instanceof Error ? orsak.message : "Kunde inte byta paket.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="grid gap-3">
      <p className="kicker text-mineral">Byt paket</p>

      <div className="grid gap-2">
        {paket.map((p) => {
          const aktiv = p.id === valt;
          const laddar = busy === p.id;
          return (
            <button
              key={p.id}
              type="button"
              aria-pressed={aktiv}
              disabled={busy !== null}
              onClick={() => valj(p.id)}
              className={cn(
                "focus-ring w-full rounded-card border px-4 py-3 text-left transition-colors",
                aktiv
                  ? "border-ochre bg-ochre/10"
                  : "border-ink/15 hover:border-ink/30 hover:bg-paper2/60",
                busy !== null && !laddar ? "opacity-50" : ""
              )}
            >
              <span className="flex items-baseline gap-2">
                <span className="text-[0.9375rem] font-semibold text-ink">{p.namn}</span>
                <span className="text-[0.8125rem] text-mineral">
                  {text(PRIS_PREFIX)} {formateraPris(p.prisPerManad)}/mån
                </span>
                {laddar ? (
                  <Loader2 className="ml-auto h-4 w-4 shrink-0 animate-spin text-mineral" aria-hidden />
                ) : aktiv ? (
                  <Check className="ml-auto h-4 w-4 shrink-0 text-ochre" aria-hidden />
                ) : null}
              </span>
              <span className="mt-1 block text-[0.8125rem] leading-5 text-ink/55">
                {text(p.beskrivning)}
              </span>
              {aktiv ? <span className="sr-only">Nuvarande paket</span> : null}
            </button>
          );
        })}
      </div>

      {bekraftar ? (
        <div
          role="alertdialog"
          aria-label="Bekräfta nedgradering"
          className="rounded-card border border-warning/40 bg-warning/10 p-4"
        >
          <p className="text-[0.875rem] leading-6 text-ink">
            Nedgradering till{" "}
            <strong className="font-semibold">
              {PAKET.find((p) => p.id === bekraftar)?.namn}
            </strong>
            . Den andra agentens vyer försvinner ur menyn direkt.{" "}
            <strong className="font-semibold">Ingenting raderas</strong> — kunskapsbas,
            ärenden och prospekt ligger kvar och kommer tillbaka om ni uppgraderar igen.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void genomfor(bekraftar)}
              className="focus-ring rounded-input bg-ink px-4 py-2 text-[0.8125rem] font-semibold text-paper hover:bg-ink2"
            >
              Ja, byt paket
            </button>
            <button
              type="button"
              onClick={() => setBekraftar(null)}
              className="focus-ring rounded-input bg-paper2 px-4 py-2 text-[0.8125rem] text-ink hover:bg-paper2/70"
            >
              Avbryt
            </button>
          </div>
        </div>
      ) : null}

      {klart ? (
        <p role="status" className="text-[0.8125rem] text-moss">
          {klart}
        </p>
      ) : null}
      {fel ? (
        <p role="alert" className="max-w-[46ch] break-words text-[0.8125rem] text-danger">
          {fel}
        </p>
      ) : null}
    </div>
  );
}
