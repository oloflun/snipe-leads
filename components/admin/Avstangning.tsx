"use client";

import { useState, useTransition } from "react";

import { btnBase, btnSecondary } from "@/components/ui";
import { sattKundAktiv } from "@/lib/actions/avstangning";

/**
 * Manuell avstängning av kontot — trial-konverteringens mänskliga väg.
 *
 * Beslutet 2026-09-20: ingen automatisk konvertering vid trial-slut. I
 * stället stängs kontot av HÄR, i två steg: knappen öppnar en
 * bekräftelsepanel som säger exakt vad som händer, kräver en orsak (den blir
 * raden i händelseloggen som förklarar avstängningen om ett halvår), och
 * först "Stäng av <kundnamn>" skriver. Samma tvåstegsmönster som CrmDemo:s
 * töm-bekräftelse — huset har ingen modal för det här, och behöver ingen:
 * panelen ligger i flödet och skyddar mot ett felklick, inte mot en
 * beslutsam människa.
 *
 * Återaktiveringen är medvetet ett klick utan panel: den öppnar, raderar
 * inget och är själv ångervägen. Symmetrisk friktion hade bara gjort
 * misstaget "stängde av fel kund" långsammare att rätta.
 */
export function Avstangning({
  tenantId,
  namn,
  aktiv,
  trialSlut,
  avtalSignerat
}: Readonly<{
  tenantId: string;
  namn: string;
  aktiv: boolean;
  trialSlut: string | null;
  avtalSignerat: string | null;
}>) {
  const [bekraftar, setBekraftar] = useState(false);
  const [arAktiv, setArAktiv] = useState(aktiv);
  const [orsak, setOrsak] = useState("");
  const [fel, setFel] = useState<string | null>(null);
  const [pending, start] = useTransition();

  const trialDatum = trialSlut ? trialSlut.slice(0, 10) : null;
  // "Idag" i Europe/Stockholm på BÅDA sidor av hydreringen, som i Kundtabell:
  // Date.now() i render ger olika svar på servern (UTC-dygn) och i
  // webbläsaren kring midnatt — hydreringskrocken den här kodbasen redan
  // betalat för. sv-SE-formatet är YYYY-MM-DD, så strängjämförelsen håller.
  const idag = new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Stockholm" }).format(
    new Date()
  );
  const trialSlutPasserad = trialDatum !== null && trialDatum < idag && !avtalSignerat;

  const skriv = (active: boolean, orsakstext: string) => {
    start(async () => {
      setFel(null);
      const svar = await sattKundAktiv(tenantId, active, orsakstext);
      if (svar.error) {
        setFel(svar.error);
        return;
      }
      setArAktiv(active);
      setBekraftar(false);
      setOrsak("");
    });
  };

  return (
    <section className="mt-14 border-t border-ink/15 pt-8">
      <h2 className="font-display text-2xl tracking-[-0.03em]">Avstängning</h2>

      {arAktiv ? (
        <>
          <p className="mt-3 max-w-[70ch] text-[0.9375rem] leading-7 text-mineral">
            {avtalSignerat
              ? `Avtal signerat ${avtalSignerat.slice(0, 10)} — kunden betalar. Avstängning härifrån är för uppsägning, inte trial.`
              : trialSlutPasserad
                ? `Provperioden gick ut ${trialDatum} och inget avtal är registrerat. Att stänga av kontot är den manuella trial-konverteringens nej — ingenting stängs av automatiskt.`
                : trialDatum
                  ? `Provperioden löper till ${trialDatum}. Kunden mejlas 7 dagar och 1 dag innan; avstängning före det datumet är ett aktivt ingripande, inte en konvertering.`
                  : "Ingen provperiod är registrerad för kontot."}
          </p>

          {!bekraftar ? (
            <button
              type="button"
              onClick={() => {
                setBekraftar(true);
                if (!orsak && trialSlutPasserad) {
                  setOrsak(`Provperioden gick ut ${trialDatum} utan avtal.`);
                }
              }}
              className={`${btnSecondary} mt-6 !text-danger hover:!bg-danger/10`}
            >
              Stäng av kontot …
            </button>
          ) : (
            <div className="mt-6 max-w-[70ch] rounded-input border border-danger/40 bg-danger/5 p-5">
              <p className="text-[0.9375rem] leading-7 text-ink">
                Avstängningen låser ute alla tre agenterna, den inloggade arbetsytan,
                portalen och den publika chatten i samma ögonblick. Ingenting raderas —
                data och inställningar står orörda, och en återaktivering öppnar allt
                igen.
              </p>
              <label className="mt-4 block text-[13px] font-medium text-ink">
                Orsak — hamnar i händelseloggen
                <input
                  type="text"
                  value={orsak}
                  onChange={(event) => setOrsak(event.target.value)}
                  placeholder="Provperioden gick ut utan avtal."
                  maxLength={500}
                  className="focus-ring mt-1.5 block w-full rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[0.9375rem]"
                />
              </label>
              <div className="mt-5 flex flex-wrap gap-3">
                <button
                  type="button"
                  disabled={pending || !orsak.trim()}
                  onClick={() => skriv(false, orsak)}
                  className={`${btnBase} bg-danger text-paper hover:bg-danger/90`}
                >
                  {pending ? "Stänger av …" : `Stäng av ${namn}`}
                </button>
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => {
                    setBekraftar(false);
                    setFel(null);
                  }}
                  className={btnSecondary}
                >
                  Avbryt
                </button>
              </div>
            </div>
          )}
        </>
      ) : (
        <>
          <p className="mt-3 max-w-[70ch] text-[0.9375rem] leading-7 text-mineral">
            Kontot är avstängt: nycklarna avvisas och ingen av agenterna svarar.
            Data och inställningar står orörda — återaktiveringen öppnar allt igen.
          </p>
          <button
            type="button"
            disabled={pending}
            onClick={() => skriv(true, "Återaktiverad från adminytan.")}
            className={`${btnSecondary} mt-6`}
          >
            {pending ? "Aktiverar …" : "Aktivera kontot igen"}
          </button>
        </>
      )}

      {fel ? (
        <p role="alert" className="mt-4 max-w-[70ch] rounded-input bg-danger/10 px-4 py-3 text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}
    </section>
  );
}
