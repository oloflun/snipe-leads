"use client";

import { CreditCard, ExternalLink, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { btnPrimary, btnSecondary } from "@/components/ui";
import { hamtaKortbetalning, type Kortbetalningslage } from "@/lib/actions/kortbetalning";

/**
 * Kortbetalning via Stripe — Checkout för det aktiva paketet och Stripes
 * kundportal för allt efteråt (kort, fakturor, uppsägning).
 *
 * Renderar INGENTING när Stripe inte är aktiverat i miljön. Då står
 * Betalsatt-formuläret (testkort) ensamt som förut; den här ytan ersätter det
 * inte, den läggs ovanpå den dag nycklarna sätts.
 *
 * Paketet väljs i Planvaljare, inte här. Den här knappen betalar för det
 * paket arbetsytan HAR — en andra väljare hade gett två ställen att byta
 * paket på, och de hade kunnat säga olika saker.
 */

const STATUSTEXT: Record<string, string> = {
  active: "Aktivt",
  trialing: "Provperiod",
  past_due: "Betalning misslyckades",
  unpaid: "Obetalt",
  canceled: "Uppsagt",
  incomplete: "Väntar på betalning",
  incomplete_expired: "Betalningen gick inte igenom",
  paused: "Pausat"
};

export function Kortbetalning({ paketId }: Readonly<{ paketId: string | undefined }>) {
  const [lage, setLage] = useState<Kortbetalningslage | null>(null);
  const [retur, setRetur] = useState<string | null>(null);

  useEffect(() => {
    let avbruten = false;
    void hamtaKortbetalning(paketId).then((svar) => {
      if (!avbruten) setLage(svar);
    });
    // Stripe skickar tillbaka hit med ?betalning=klar|avbruten.
    const status = new URLSearchParams(window.location.search).get("betalning");
    if (status === "klar") {
      setRetur("Tack! Betalningen är mottagen. Det kan ta en halv minut innan abonnemanget syns här.");
    } else if (status === "avbruten") {
      setRetur("Betalningen avbröts. Ingenting har debiterats.");
    }
    return () => {
      avbruten = true;
    };
  }, [paketId]);

  if (!lage?.aktiverad) return null;
  return <KortbetalningVy lage={lage} paketId={paketId} retur={retur} />;
}

/** Själva ytan, utan hämtning — skild från laddaren så att den går att
 *  rendera och granska med givna lägen. */
export function KortbetalningVy({
  lage,
  paketId,
  retur
}: Readonly<{ lage: Kortbetalningslage; paketId: string | undefined; retur: string | null }>) {
  const [busy, setBusy] = useState<"checkout" | "portal" | null>(null);
  const [fel, setFel] = useState<string | null>(null);

  async function till(vag: "checkout" | "portal") {
    setBusy(vag);
    setFel(null);
    try {
      const svar = await fetch(`/api/billing/${vag}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(vag === "checkout" ? { paket: paketId } : {})
      });
      const data = (await svar.json().catch(() => ({}))) as { url?: string; error?: string };
      if (!svar.ok || !data.url) {
        setFel(data.error ?? "Något gick fel. Försök igen om en stund.");
        setBusy(null);
        return;
      }
      window.location.assign(data.url);
    } catch {
      setFel("Kunde inte nå betalningstjänsten. Försök igen om en stund.");
      setBusy(null);
    }
  }

  const abonnemang = lage.abonnemang;
  const status = abonnemang?.status ?? "none";
  const harAbonnemang = Boolean(abonnemang?.stripe_customer_id);
  const aktivt = status === "active" || status === "trialing";
  // Ett nytt köp är bara rätt när det INTE finns en levande prenumeration. Vid
  // ett misslyckat kortdrag lagas kortet i portalen; en ny Checkout där hade
  // gett kunden två prenumerationer och två dragningar.
  const kanKopa = status === "none" || status === "canceled" || status === "incomplete_expired";
  const betalningsproblem = status === "past_due" || status === "unpaid";
  // Datumet sägs bara om ett abonnemang som faktiskt löper. "Förnyas" om en
  // betalning som just misslyckats vore ett löfte vi inte kan hålla.
  const periodSlut =
    aktivt && abonnemang?.current_period_end
      ? new Date(abonnemang.current_period_end).toLocaleDateString("sv-SE", { timeZone: "Europe/Stockholm" })
      : null;

  return (
    <div>
      <h2 className="kicker text-mineral">Kortbetalning</h2>
      <div className="mt-4 border-y border-ink/15 py-5">
        {lage.testlage ? (
          <p className="mb-4 max-w-[62ch] text-[0.875rem] leading-6 text-warning">
            Testläge: Stripe kör med testnycklar. Använd testkortet 4242 4242 4242 4242, ingenting debiteras.
          </p>
        ) : null}

        {retur ? (
          <p role="status" className="mb-4 max-w-[62ch] text-[0.9375rem] leading-6 text-ink">
            {retur}
          </p>
        ) : null}

        {abonnemang && status !== "none" ? (
          <>
            <p className="max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">
              <span className="font-semibold text-ink">{STATUSTEXT[status] ?? status}</span>
              {periodSlut
                ? abonnemang.cancel_at_period_end
                  ? ` · avslutas ${periodSlut}`
                  : ` · förnyas ${periodSlut}`
                : null}
            </p>
            {betalningsproblem ? (
              <p className="mt-2 max-w-[62ch] text-[0.9375rem] leading-6 text-danger">
                Kortdraget gick inte igenom. Uppdatera kortet i kundportalen så fortsätter abonnemanget.
              </p>
            ) : null}
          </>
        ) : (
          <p className="max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">
            Betala ert paket med kort, månadsvis. Kvitton och fakturor finns sedan i Stripes kundportal.
          </p>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-2">
          {kanKopa ? (
            <button
              type="button"
              onClick={() => void till("checkout")}
              disabled={busy !== null || !lage.paketHarPris}
              title={lage.paketHarPris ? undefined : "Ert paket saknar kortpris. Välj ett paket i listan ovan."}
              className={btnPrimary}
            >
              {busy === "checkout" ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <CreditCard className="h-4 w-4" aria-hidden />
              )}
              Betala med kort
            </button>
          ) : null}
          {harAbonnemang ? (
            <button
              type="button"
              onClick={() => void till("portal")}
              disabled={busy !== null}
              className={btnSecondary}
            >
              {busy === "portal" ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <ExternalLink className="h-4 w-4" aria-hidden />
              )}
              Hantera abonnemang och fakturor
            </button>
          ) : null}
        </div>

        {!lage.paketHarPris && kanKopa ? (
          <p className="mt-3 max-w-[62ch] text-[0.8125rem] leading-5 text-ink-subtle">
            Ert nuvarande paket kan inte betalas med kort än. Välj ett paket ovan, eller skriv till oss.
          </p>
        ) : null}

        {fel ? (
          <p role="alert" className="mt-3 max-w-[62ch] text-[0.875rem] text-danger">
            {fel}
          </p>
        ) : null}
      </div>
    </div>
  );
}
