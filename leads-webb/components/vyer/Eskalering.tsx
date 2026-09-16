"use client";

import { useEffect, useState } from "react";
import {
  ESKALERING_STANDARD,
  lasEskaleringsregler,
  sparaEskaleringsregler,
  type Eskaleringsregler
} from "@/lib/iris";
import { cn } from "@/lib/utils";

/**
 * Eskaleringsreglerna: när Iris ska lämna över till en människa i stället
 * för att hantera vidare själv. Redigerbara HÄR, till skillnad från
 * målgruppen och autonomin ovanför: eskaleringen är den här ytans eget
 * kontrakt med användaren, den finns inte i huvudappens kontrollpanel.
 *
 * Sparas i webbläsaren tills backenden bär fältet. Vyn säger det rakt ut i
 * stället för att låtsas vara synkad; en inställning som ser molnsparad ut
 * men inte är det är ett brutet löfte den dag kunden byter dator.
 */

function Vaxel({
  paslagen,
  etikett,
  beskrivning,
  onByt
}: Readonly<{
  paslagen: boolean;
  etikett: string;
  beskrivning: string;
  onByt: (v: boolean) => void;
}>) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-x-8 gap-y-2 py-4">
      <div className="min-w-0 max-w-[56ch] flex-1 basis-72">
        <p className="text-[0.9375rem] font-semibold text-ink">{etikett}</p>
        <p className="mt-0.5 text-[0.875rem] leading-6 text-ink/60">{beskrivning}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={paslagen}
        aria-label={etikett}
        onClick={() => onByt(!paslagen)}
        className={cn(
          "focus-ring relative h-7 w-12 shrink-0 rounded-full transition-colors",
          paslagen ? "bg-ink" : "bg-ink/20"
        )}
      >
        <span
          aria-hidden
          className={cn(
            "absolute top-1 h-5 w-5 rounded-full bg-paper transition-[left]",
            paslagen ? "left-6" : "left-1"
          )}
        />
      </button>
    </div>
  );
}

export function Eskalering() {
  const [regler, setRegler] = useState<Eskaleringsregler>(ESKALERING_STANDARD);
  const [laddad, setLaddad] = useState(false);
  const [sparfel, setSparfel] = useState(false);

  // localStorage finns bara i webbläsaren — läs efter mount, aldrig i render.
  useEffect(() => {
    setRegler(lasEskaleringsregler());
    setLaddad(true);
  }, []);

  function uppdatera(andring: Partial<Eskaleringsregler>) {
    setRegler((forra) => {
      const nya = { ...forra, ...andring };
      setSparfel(!sparaEskaleringsregler(nya));
      return nya;
    });
  }

  return (
    <section className="max-w-[42rem]" aria-label="Eskalering till människa">
      <h2 className="font-display text-[1.25rem]">När Iris lämnar över till dig</h2>
      <p className="mt-1 max-w-[62ch] text-[0.9375rem] leading-6 text-ink/60">
        Reglerna avgör när ett lead eller ett svar går till dig i stället för att hanteras
        vidare automatiskt. Avstängd regel betyder att Iris fortsätter enligt sitt vanliga
        flöde, fortfarande med granskningskön som sista spärr.
      </p>

      {!laddad ? (
        <div className="mt-3 h-40 animate-pulse rounded-[7px] bg-ink/[0.055]" />
      ) : (
        <div className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
          <Vaxel
            paslagen={regler.osakerKvalificering}
            etikett="Osäker kvalificering"
            beskrivning="Bolag under träffsäkerhetströskeln får inget utkast; de läggs i stället till dig för bedömning."
            onByt={(v) => uppdatera({ osakerKvalificering: v })}
          />
          {regler.osakerKvalificering ? (
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 py-4">
              <label htmlFor="troskel" className="text-[0.9375rem] font-medium text-ink">
                Träffsäkerhetströskel
              </label>
              <div className="flex items-center gap-2">
                <input
                  id="troskel"
                  type="number"
                  min={0}
                  max={100}
                  step={5}
                  value={regler.kvalificeringstroskel}
                  onChange={(e) =>
                    uppdatera({
                      kvalificeringstroskel: Math.min(100, Math.max(0, Number(e.target.value) || 0))
                    })
                  }
                  className="focus-ring h-11 w-24 rounded-input border border-ink/15 bg-paper px-3 text-[16px]"
                />
                <span className="text-[0.9375rem] text-ink/60">procent</span>
              </div>
              <p className="w-full text-[0.8125rem] leading-5 text-ink/50">
                Under {regler.kvalificeringstroskel} procent mot din målgrupp eskaleras bolaget
                till dig.
              </p>
            </div>
          ) : null}
          <Vaxel
            paslagen={regler.prisforhandling}
            etikett="Pris och avtal"
            beskrivning="Svar som tar upp pris, rabatt eller avtalsvillkor lämnas alltid till dig. Iris föreslår aldrig en siffra själv."
            onByt={(v) => uppdatera({ prisforhandling: v })}
          />
          <Vaxel
            paslagen={regler.negativtSentiment}
            etikett="Negativt svar"
            beskrivning="Irriterade eller avvisande svar går till dig, och all uppföljning mot bolaget stoppas tills du sagt något annat."
            onByt={(v) => uppdatera({ negativtSentiment: v })}
          />
          <Vaxel
            paslagen={regler.juridik}
            etikett="Juridik och personuppgifter"
            beskrivning="Frågor om avtal, juridik eller personuppgifter besvaras aldrig av Iris; de eskaleras alltid till dig."
            onByt={(v) => uppdatera({ juridik: v })}
          />
        </div>
      )}

      {sparfel ? (
        <p role="alert" className="mt-2 text-[0.875rem] text-danger">
          Reglerna kunde inte sparas i webbläsaren. De gäller ändå tills du laddar om sidan.
        </p>
      ) : (
        <p className="mt-2 text-[0.8125rem] leading-5 text-ink/50">
          Sparas i din webbläsare på den här ytan. Målgrupp och autonomi ställs som förut in i
          arbetsytan på Snajp-webben.
        </p>
      )}
    </section>
  );
}
