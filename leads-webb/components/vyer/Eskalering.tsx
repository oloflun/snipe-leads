"use client";

import { useEffect, useRef, useState } from "react";
import { BAS, type LeadsConfig } from "@/lib/api";
import { felmeddelande, readJson } from "@/lib/http/json";
import type { Eskaleringsregler } from "@/lib/iris";
import { cn } from "@/lib/utils";

/**
 * Eskaleringsreglerna: när Iris ska lämna över till en människa i stället
 * för att hantera vidare själv. Redigerbara HÄR, till skillnad från
 * målgruppen och autonomin ovanför: eskaleringen är den här ytans eget
 * kontrakt med användaren, den finns inte i huvudappens kontrollpanel.
 *
 * Läses och sparas mot backenden (PUT /leads/config, fältvis), där de också
 * verkställs. En växel sparas direkt och återställs om sparningen faller; en
 * inställning som ser sparad ut men inte är det är ett brutet löfte.
 */

type Lage = { fas: "laddar" } | { fas: "klar"; regler: Eskaleringsregler } | { fas: "fel"; text: string };

function Vaxel({
  paslagen,
  etikett,
  beskrivning,
  upptagen,
  onByt
}: Readonly<{
  paslagen: boolean;
  etikett: string;
  beskrivning: string;
  upptagen: boolean;
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
        disabled={upptagen}
        onClick={() => onByt(!paslagen)}
        className={cn(
          "focus-ring relative h-7 w-12 shrink-0 rounded-full transition-colors disabled:cursor-wait disabled:opacity-60",
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
  const [lage, setLage] = useState<Lage>({ fas: "laddar" });
  const [troskelText, setTroskelText] = useState("");
  const [sparar, setSparar] = useState(false);
  const [sparfel, setSparfel] = useState<string | null>(null);
  const [sparad, setSparad] = useState(false);
  const sparadTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const config = await fetch(`${BAS}/leads/config`).then((s) => readJson<LeadsConfig>(s));
        if (!config?.eskalering) throw new Error("Backenden svarade utan eskaleringsregler.");
        setLage({ fas: "klar", regler: config.eskalering });
        setTroskelText(String(config.eskalering.kvalificeringstroskel));
      } catch (orsak) {
        setLage({ fas: "fel", text: felmeddelande(orsak) });
      }
    })();
    return () => {
      if (sparadTimer.current) clearTimeout(sparadTimer.current);
    };
  }, []);

  async function spara(andring: Partial<Eskaleringsregler>) {
    if (lage.fas !== "klar") return;
    const forra = lage.regler;
    setLage({ fas: "klar", regler: { ...forra, ...andring } });
    setSparar(true);
    setSparfel(null);
    try {
      const svar = await fetch(`${BAS}/leads/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ eskalering: andring })
      }).then((s) => readJson<LeadsConfig>(s));
      if (!svar?.eskalering) throw new Error("Backenden svarade utan eskaleringsregler.");
      setLage({ fas: "klar", regler: svar.eskalering });
      setTroskelText(String(svar.eskalering.kvalificeringstroskel));
      setSparad(true);
      if (sparadTimer.current) clearTimeout(sparadTimer.current);
      sparadTimer.current = setTimeout(() => setSparad(false), 2500);
    } catch (orsak) {
      setLage({ fas: "klar", regler: forra });
      setTroskelText(String(forra.kvalificeringstroskel));
      setSparfel(`Ändringen sparades inte: ${felmeddelande(orsak)}`);
    } finally {
      setSparar(false);
    }
  }

  function sparaTroskel() {
    if (lage.fas !== "klar") return;
    const varde = Math.min(100, Math.max(0, Math.round(Number(troskelText))));
    if (troskelText.trim() === "" || Number.isNaN(varde)) {
      setTroskelText(String(lage.regler.kvalificeringstroskel));
      return;
    }
    if (varde !== lage.regler.kvalificeringstroskel) void spara({ kvalificeringstroskel: varde });
    else setTroskelText(String(varde));
  }

  return (
    <section className="max-w-[42rem]" aria-label="Eskalering till människa">
      <h2 className="font-display text-[1.25rem]">När Iris lämnar över till dig</h2>
      <p className="mt-1 max-w-[62ch] text-[0.9375rem] leading-6 text-ink/60">
        Reglerna avgör när ett lead eller ett svar går till dig i stället för att hanteras
        vidare automatiskt. Avstängd regel betyder att Iris fortsätter enligt sitt vanliga
        flöde, fortfarande med granskningskön som sista spärr.
      </p>

      {lage.fas === "laddar" ? (
        <div className="mt-3 h-40 animate-pulse rounded-[7px] bg-ink/[0.055]" />
      ) : lage.fas === "fel" ? (
        <p role="alert" className="mt-3 border-y border-ink/15 py-4 text-[0.9375rem] text-danger">
          Reglerna kunde inte hämtas: {lage.text}
        </p>
      ) : (
        <div className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
          <Vaxel
            paslagen={lage.regler.osaker_kvalificering}
            etikett="Osäker kvalificering"
            beskrivning="Bolag under träffsäkerhetströskeln får inget automatiskt utkast. De står kvar i Prospekt för din bedömning."
            upptagen={sparar}
            onByt={(v) => void spara({ osaker_kvalificering: v })}
          />
          {lage.regler.osaker_kvalificering ? (
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 py-4">
              <label htmlFor="troskel" className="text-[0.9375rem] font-medium text-ink">
                Träffsäkerhetströskel
              </label>
              <div className="flex items-center gap-2">
                <input
                  id="troskel"
                  type="number"
                  inputMode="numeric"
                  min={0}
                  max={100}
                  step={5}
                  value={troskelText}
                  disabled={sparar}
                  onChange={(e) => setTroskelText(e.target.value)}
                  onBlur={sparaTroskel}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") e.currentTarget.blur();
                  }}
                  className="focus-ring h-11 w-24 rounded-input border border-ink/15 bg-paper px-3 text-[16px] disabled:opacity-60"
                />
                <span className="text-[0.9375rem] text-ink/60">procent</span>
              </div>
              <p className="w-full text-[0.8125rem] leading-5 text-ink/50">
                Under {lage.regler.kvalificeringstroskel} procent mot din målgrupp får bolaget
                inget utkast i körningen. Sparas när du lämnar fältet.
              </p>
            </div>
          ) : null}
          <Vaxel
            paslagen={lage.regler.prisfragor}
            etikett="Pris och budget"
            beskrivning="Svar som tar upp pris, rabatt eller budget får inget utkast från Iris. Uppföljningen stoppas och du får ett mejl."
            upptagen={sparar}
            onByt={(v) => void spara({ prisfragor: v })}
          />
          <Vaxel
            paslagen={lage.regler.negativt_svar}
            etikett="Negativt svar"
            beskrivning="Du får ett mejl när ett bolag svarar avvisande. Uppföljningen mot bolaget stoppas alltid, även med regeln avstängd."
            upptagen={sparar}
            onByt={(v) => void spara({ negativt_svar: v })}
          />
          <Vaxel
            paslagen={lage.regler.juridik}
            etikett="Avtal, juridik och personuppgifter"
            beskrivning="Svar om avtal, villkor, juridik eller personuppgifter får inget utkast från Iris. Uppföljningen stoppas och du får ett mejl."
            upptagen={sparar}
            onByt={(v) => void spara({ juridik: v })}
          />
        </div>
      )}

      <p
        role={sparfel ? "alert" : "status"}
        className={cn(
          "mt-2 min-h-5 text-[0.8125rem] leading-5",
          sparfel ? "text-danger" : "text-ink/50"
        )}
      >
        {sparfel
          ? sparfel
          : sparad
            ? "Sparat. Gäller från nästa svar och nästa körning."
            : lage.fas === "klar"
              ? "Sparas i ditt konto och gäller för alla som arbetar med Iris."
              : null}
      </p>
    </section>
  );
}
