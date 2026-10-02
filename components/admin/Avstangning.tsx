"use client";

import { useState, useTransition } from "react";

import { btnBase, btnSecondary } from "@/components/ui";
import { sattKundAktiv } from "@/lib/actions/avstangning";
import { ordagrant } from "@/lib/admin/sprak";
import { useLocale, type Localized } from "@/lib/i18n";

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
  const [fel, setFel] = useState<Localized | null>(null);
  const [pending, start] = useTransition();
  const { text } = useLocale();

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
        setFel(ordagrant(svar.error));
        return;
      }
      setArAktiv(active);
      setBekraftar(false);
      setOrsak("");
    });
  };

  return (
    <section className="mt-14 border-t border-ink/15 pt-8">
      <h2 className="font-display text-2xl tracking-[-0.03em]">
        {text({ sv: "Avstängning", en: "Suspension" })}
      </h2>

      {arAktiv ? (
        <>
          <p className="mt-3 max-w-[70ch] text-[0.9375rem] leading-7 text-mineral">
            {avtalSignerat
              ? text({
                  sv: `Avtal signerat ${avtalSignerat.slice(0, 10)} — kunden betalar. Avstängning härifrån är för uppsägning, inte trial.`,
                  en: `Contract signed ${avtalSignerat.slice(0, 10)}, the customer pays. Suspending from here is for termination, not trial.`
                })
              : trialSlutPasserad
                ? text({
                    sv: `Provperioden gick ut ${trialDatum} och inget avtal är registrerat. Att stänga av kontot är den manuella trial-konverteringens nej — ingenting stängs av automatiskt.`,
                    en: `The trial ended ${trialDatum} and no contract is registered. Suspending the account is the manual trial conversion's no. Nothing is suspended automatically.`
                  })
                : trialDatum
                  ? text({
                      sv: `Provperioden löper till ${trialDatum}. Kunden mejlas 7 dagar och 1 dag innan; avstängning före det datumet är ett aktivt ingripande, inte en konvertering.`,
                      en: `The trial runs until ${trialDatum}. The customer is emailed 7 days and 1 day before. Suspending before that date is an active intervention, not a conversion.`
                    })
                  : text({
                      sv: "Ingen provperiod är registrerad för kontot.",
                      en: "No trial is registered for this account."
                    })}
          </p>

          {!bekraftar ? (
            <button
              type="button"
              onClick={() => {
                setBekraftar(true);
                if (!orsak && trialSlutPasserad) {
                  setOrsak(
                    text({
                      sv: `Provperioden gick ut ${trialDatum} utan avtal.`,
                      en: `The trial ended ${trialDatum} without a contract.`
                    })
                  );
                }
              }}
              className={`${btnSecondary} mt-6 !text-danger hover:!bg-danger/10`}
            >
              {text({ sv: "Stäng av kontot …", en: "Suspend the account …" })}
            </button>
          ) : (
            <div className="mt-6 max-w-[70ch] rounded-input border border-danger/40 bg-danger/5 p-5">
              <p className="text-[0.9375rem] leading-7 text-ink">
                {text({
                  sv: "Avstängningen låser ute alla tre agenterna, den inloggade arbetsytan, portalen och den publika chatten i samma ögonblick. Ingenting raderas — data och inställningar står orörda, och en återaktivering öppnar allt igen.",
                  en: "Suspension locks out all three agents, the signed-in workspace, the portal and the public chat at once. Nothing is deleted. Data and settings stay untouched, and reactivating opens everything again."
                })}
              </p>
              <label className="mt-4 block text-[13px] font-medium text-ink">
                {text({ sv: "Orsak — hamnar i händelseloggen", en: "Reason, goes into the event log" })}
                <input
                  type="text"
                  value={orsak}
                  onChange={(event) => setOrsak(event.target.value)}
                  placeholder={text({
                    sv: "Provperioden gick ut utan avtal.",
                    en: "The trial ended without a contract."
                  })}
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
                  {pending
                    ? text({ sv: "Stänger av …", en: "Suspending …" })
                    : text({ sv: `Stäng av ${namn}`, en: `Suspend ${namn}` })}
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
                  {text({ sv: "Avbryt", en: "Cancel" })}
                </button>
              </div>
            </div>
          )}
        </>
      ) : (
        <>
          <p className="mt-3 max-w-[70ch] text-[0.9375rem] leading-7 text-mineral">
            {text({
              sv: "Kontot är avstängt: nycklarna avvisas och ingen av agenterna svarar. Data och inställningar står orörda — återaktiveringen öppnar allt igen.",
              en: "The account is suspended: keys are rejected and none of the agents answer. Data and settings stay untouched. Reactivating opens everything again."
            })}
          </p>
          <button
            type="button"
            disabled={pending}
            onClick={() => skriv(true, "Återaktiverad från adminytan.")} // inte-copy: händelseloggens orsak
            className={`${btnSecondary} mt-6`}
          >
            {pending
              ? text({ sv: "Aktiverar …", en: "Activating …" })
              : text({ sv: "Aktivera kontot igen", en: "Reactivate the account" })}
          </button>
        </>
      )}

      {fel ? (
        <p role="alert" className="mt-4 max-w-[70ch] rounded-input bg-danger/10 px-4 py-3 text-[0.875rem] text-danger">
          {text(fel)}
        </p>
      ) : null}
    </section>
  );
}
