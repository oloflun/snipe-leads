"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Badge, btnPrimary, btnSecondary, meta, rubrikPanel } from "@/components/ui";
import { useLocale } from "@/lib/i18n";
import { bytPlan } from "@/lib/actions/plan";
import { PAKET, PRIS_PREFIX, PRIS_SAKNAS, formateraPris } from "@/lib/pricing";
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
 * Fem alternativ med pris och en rad förklaring vardera. En rullgardin döljer
 * fyra av dem bakom ett klick, och just de fyra är det man jämför med.
 */

const ORDNING = ["leads", "support", "bookkeeping", "duo", "trio"] as const;

/**
 * Hur många produkter ett paket ger. Används för att avgöra vad som är en
 * NEDGRADERING, och därmed vad som kräver bekräftelse.
 *
 * Räknas och gissas inte: den första versionen skrev `valt === "duo" && nytt
 * !== "duo"`, vilket stämde så länge Duo var det enda paketet med två
 * produkter. Med bokföringen inne är det inte längre sant — ett byte från Duo
 * till Bokföring är fortfarande en nedgradering, men ett byte från Bokföring
 * till Duo är inte det, och en hårdkodad jämförelse mot "duo" hade fått båda
 * fel åt olika håll.
 */
const PRODUKTER_I_PAKET: Record<string, number> = {
  leads: 1,
  support: 1,
  bookkeeping: 1,
  duo: 2,
  trio: 3
};

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

  /**
   * Nedgradering = det nya paketet ger färre produkter än det nuvarande, ELLER
   * lika många men andra.
   *
   * Det andra ledet är inte överdrift: ett byte från Leads till Bokföring tar
   * bort leads-agenten lika verkligt som ett byte från Duo gör, fast antalet
   * är oförändrat. Bekräftelserutan säger att inget raderas, och det är just
   * den frågan kunden har i båda fallen.
   */
  function arNedgradering(nyttId: string): boolean {
    if (!valt || nyttId === valt) return false;
    const fore = PRODUKTER_I_PAKET[valt] ?? 0;
    const efter = PRODUKTER_I_PAKET[nyttId] ?? 0;
    if (efter < fore) return true;
    // Samma antal men annat paket: något försvinner, även om något tillkommer.
    return efter === fore;
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
      {/* Ingen egen etikett ("Byt paket"): sektionsrubriken ovanför säger det.
          Meningen under listan är den som stod i fakturastycket längst ned på
          sidan, flyttad hit där beslutet fattas. */}
      <div role="group" aria-label="Paket" aria-describedby="paket-hjalp" className="grid gap-2">
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
              <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <span className={rubrikPanel}>{p.namn}</span>
                <span className={cn(meta, "num")}>
                  {p.prisPerManad === null
                    ? text(PRIS_SAKNAS)
                    : `${text(PRIS_PREFIX)} ${formateraPris(p.prisPerManad)}/mån`}
                </span>
                {/* Ordet, inte bara bocken: markeringen var en ochrekant och
                    en ikon, och "nuvarande" fanns bara för skärmläsaren. */}
                {laddar ? (
                  <Loader2 className="ml-auto h-4 w-4 shrink-0 animate-spin text-ink-subtle" aria-hidden />
                ) : aktiv ? (
                  <span className="ml-auto">
                    <Badge>Nuvarande</Badge>
                  </span>
                ) : null}
              </span>
              <span className="mt-1 block text-[0.9375rem] leading-6 text-ink-muted">
                {text(p.beskrivning)}
              </span>
            </button>
          );
        })}
      </div>

      <p id="paket-hjalp" className="max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">
        Ett paketbyte gäller direkt, och vi justerar faktureringen vid nästa period.
      </p>

      {bekraftar ? (
        <div
          role="alertdialog"
          aria-label="Bekräfta nedgradering"
          className="rounded-card border border-warning/40 bg-warning/10 p-4"
        >
          <p className="text-[0.9375rem] leading-6 text-ink">
            Nedgradering till{" "}
            <strong className="font-semibold">
              {PAKET.find((p) => p.id === bekraftar)?.namn}
            </strong>
            . Vyerna för det ni lämnar försvinner ur menyn direkt.{" "}
            <strong className="font-semibold">Ingenting raderas:</strong> kunskapsbas,
            ärenden och prospekt ligger kvar och kommer tillbaka om ni uppgraderar igen.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" onClick={() => void genomfor(bekraftar)} className={btnPrimary}>
              Ja, byt paket
            </button>
            <button type="button" onClick={() => setBekraftar(null)} className={btnSecondary}>
              Avbryt
            </button>
          </div>
        </div>
      ) : null}

      {klart ? (
        <p role="status" className="text-[0.9375rem] text-moss">
          {klart}
        </p>
      ) : null}
      {fel ? (
        <p role="alert" className="max-w-[62ch] break-words text-[0.9375rem] text-danger">
          {fel}
        </p>
      ) : null}
    </div>
  );
}
