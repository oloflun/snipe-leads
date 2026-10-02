"use client";

import { useEffect, useRef, useState } from "react";
import type { Eskaleringsregler } from "@/lib/iris";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";
import { useLocale, type Localized } from "@/lib/i18n";

const UTAN_REGLER: Localized = {
  sv: "Backenden svarade utan eskaleringsregler.",
  en: "The backend replied without escalation rules."
};

function somText(orsak: unknown): Localized {
  const m = felmeddelande(orsak);
  return { sv: m, en: m };
}

/**
 * Eskaleringsreglerna: när Iris ska lämna över till en människa i stället
 * för att hantera vidare själv.
 *
 * Portad från `leads-webb/components/vyer/Eskalering.tsx` till huvudappens
 * API-konventioner (samma `/api/snajp-support/leads/config`-anrop som
 * `components/leads/LeadsControls.tsx` redan använder, i stället för
 * leads-webbs egna proxy/session). Läses och sparas mot backenden
 * (PUT /leads/config, fältvis under nyckeln "eskalering"), där reglerna också
 * verkställs. En växel sparas direkt och återställs om sparningen faller; en
 * inställning som ser sparad ut men inte är det är ett brutet löfte.
 */

type LeadsConfig = { eskalering?: Eskaleringsregler };

type Lage =
  | { fas: "laddar" }
  | { fas: "klar"; regler: Eskaleringsregler }
  | { fas: "fel"; text: Localized };

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
        <p className="mt-0.5 text-[0.875rem] leading-6 text-ink-muted">{beskrivning}</p>
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

export function IrisEskalering() {
  const { text } = useLocale();
  const [lage, setLage] = useState<Lage>({ fas: "laddar" });
  const [troskelText, setTroskelText] = useState("");
  const [sparar, setSparar] = useState(false);
  const [sparfel, setSparfel] = useState<Localized | null>(null);
  const [sparad, setSparad] = useState(false);
  const sparadTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const response = await fetch("/api/snajp-support/leads/config", { cache: "no-store" });
        const config = await readJsonBody<LeadsConfig>(response);
        if (!response.ok || !config?.eskalering) {
          setLage({ fas: "fel", text: UTAN_REGLER });
          return;
        }
        setLage({ fas: "klar", regler: config.eskalering });
        setTroskelText(String(config.eskalering.kvalificeringstroskel));
      } catch (orsak) {
        setLage({ fas: "fel", text: somText(orsak) });
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
    const aterstall = (orsak: Localized) => {
      setLage({ fas: "klar", regler: forra });
      setTroskelText(String(forra.kvalificeringstroskel));
      setSparfel({
        sv: `Ändringen sparades inte: ${orsak.sv}`,
        en: `The change was not saved: ${orsak.en}`
      });
    };
    try {
      const response = await fetch("/api/snajp-support/leads/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ eskalering: andring })
      });
      const svar = await readJsonBody<LeadsConfig>(response);
      if (!response.ok || !svar?.eskalering) {
        aterstall(UTAN_REGLER);
        return;
      }
      setLage({ fas: "klar", regler: svar.eskalering });
      setTroskelText(String(svar.eskalering.kvalificeringstroskel));
      setSparad(true);
      if (sparadTimer.current) clearTimeout(sparadTimer.current);
      sparadTimer.current = setTimeout(() => setSparad(false), 2500);
    } catch (orsak) {
      aterstall(somText(orsak));
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
    <section aria-label={text({ sv: "Eskalering till människa", en: "Escalation to a person" })}>
      <h3 className="kicker text-mineral">{text({ sv: "När Iris lämnar över till dig", en: "When Iris hands over to you" })}</h3>

      {lage.fas === "laddar" ? (
        <div className="mt-5 grid gap-px">
          {[0, 1, 2, 3].map((row) => (
            <div key={row} className="h-16 animate-pulse border-t border-ink/15 bg-ink/[0.03]" />
          ))}
        </div>
      ) : lage.fas === "fel" ? (
        <p role="alert" className="mt-5 border-y border-ink/15 py-4 text-[15px] text-danger">
          {text({ sv: "Reglerna kunde inte hämtas:", en: "The rules could not be fetched:" })} {text(lage.text)}
        </p>
      ) : (
        <div className="mt-5 divide-y divide-ink/12 border-y border-ink/15">
          <Vaxel
            paslagen={lage.regler.osaker_kvalificering}
            etikett={text({ sv: "Osäker kvalificering", en: "Uncertain qualification" })}
            beskrivning={text({
              sv: "Bolag under tröskeln får inget automatiskt utkast.",
              en: "Companies below the threshold get no automatic draft."
            })}
            upptagen={sparar}
            onByt={(v) => void spara({ osaker_kvalificering: v })}
          />
          {lage.regler.osaker_kvalificering ? (
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 py-4">
              <label htmlFor="iris-troskel" className="text-[0.9375rem] font-medium text-ink">
                {text({ sv: "Träffsäkerhetströskel", en: "Confidence threshold" })}
              </label>
              <div className="flex items-center gap-2">
                <input
                  id="iris-troskel"
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
                <span className="text-[0.9375rem] text-ink-muted">{text({ sv: "procent", en: "percent" })}</span>
              </div>
            </div>
          ) : null}
          <Vaxel
            paslagen={lage.regler.prisfragor}
            etikett={text({ sv: "Pris och budget", en: "Price and budget" })}
            beskrivning={text({
              sv: "Svar om pris, rabatt eller budget går till dig.",
              en: "Replies about price, discounts or budget go to you."
            })}
            upptagen={sparar}
            onByt={(v) => void spara({ prisfragor: v })}
          />
          <Vaxel
            paslagen={lage.regler.negativt_svar}
            etikett={text({ sv: "Negativt svar", en: "Negative reply" })}
            beskrivning={text({
              sv: "Mejl till dig när ett bolag svarar avvisande.",
              en: "An email to you when a company replies negatively."
            })}
            upptagen={sparar}
            onByt={(v) => void spara({ negativt_svar: v })}
          />
          <Vaxel
            paslagen={lage.regler.juridik}
            etikett={text({ sv: "Avtal, juridik och personuppgifter", en: "Contracts, legal and personal data" })}
            beskrivning={text({
              sv: "Svar om avtal, juridik eller personuppgifter går till dig.",
              en: "Replies about contracts, legal matters or personal data go to you."
            })}
            upptagen={sparar}
            onByt={(v) => void spara({ juridik: v })}
          />
        </div>
      )}

      <p
        role={sparfel ? "alert" : "status"}
        className={cn("mt-2 min-h-5 text-[0.8125rem] leading-5", sparfel ? "text-danger" : "text-ink-subtle")}
      >
        {sparfel ? text(sparfel) : sparad ? text({ sv: "Sparat.", en: "Saved." }) : null}
      </p>
    </section>
  );
}
