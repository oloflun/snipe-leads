"use client";

/* design · Operate-yta i det låsta systemet (DESIGN.md, Tier 0): samma växel,
   fält och knappar som IrisEskalering och IrisProdukter, ingen ny riktning. */

import { useCallback, useEffect, useState } from "react";
import { Vaxel } from "@/components/leads/IrisEskalering";
import { btnPrimary, btnSecondary, etikett, meta, rubrikPanel } from "@/components/ui";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { leadsAnrop } from "@/lib/leads/suite";
import { cn } from "@/lib/utils";

/**
 * Iris › Inställningar › Erbjudanden (Antons beställning 2026-10-10).
 *
 * Kunden väljer vilka erbjudanden ur katalogen (agent-core/prompts/
 * leads-erbjudanden.md) Iris ska A/B-testa i de kalla mejlen, med vikt och
 * med sina egna villkor. Villkoren är det enda mejlet får lova, och ett
 * erbjudande kan bara slås på när de är ifyllda. Resultatet per erbjudande
 * räknas ur trådarna (GET /leads/erbjudanden) och en arm kallas ledande först
 * när den håller statistiskt (app/leads/erbjudanden.py:sammanstall).
 */

type Arm = {
  nyckel: string;
  namn: string;
  utkast: number;
  skickade: number;
  svar: number;
  positiva: number;
  moten: number;
  svarsfrekvens: number | null;
  positiv_andel: number | null;
  lage: "leder" | "for_tidigt";
};
type Svar = {
  katalog: { nyckel: string; namn: string }[];
  aktiva: { nyckel: string; vikt: number }[];
  villkor: Record<string, string>;
  resultat: { armar: Arm[]; ledare: string | null; min_skickade: number };
};
type Rad = { pa: boolean; vikt: string; villkor: string };

const VILLKOR_MAX = 600;

/** Namn och förklaring per nyckel. Okända nycklar visas med katalogens namn. */
const ERBJUDANDEN: Record<string, { namn: Localized; om: Localized; exempel: Localized }> = {
  riskfri_start: {
    namn: { sv: "Riskfri start", en: "Risk-free start" },
    om: { sv: "Tar bort risken med att prova något nytt.", en: "Removes the risk of trying something new." },
    exempel: {
      sv: "Till exempel: Första månaden utan kostnad. Ingen bindningstid.",
      en: "For example: The first month free of charge. No lock-in period."
    }
  },
  se_det_forst: {
    namn: { sv: "Se det först", en: "See it first" },
    om: {
      sv: "Mottagaren får ett litet, konkret resultat innan något är bestämt.",
      en: "The recipient gets a small, concrete result before anything is decided."
    },
    exempel: {
      sv: "Till exempel: Tio bolag som passar er, med färdiga första mejl, utan kostnad.",
      en: "For example: Ten companies that fit you, with ready first emails, free of charge."
    }
  },
  forsta_resultatet: {
    namn: { sv: "Garanti på första resultatet", en: "Guarantee on the first result" },
    om: {
      sv: "Ni tar risken för att första resultatet uteblir. Aldrig löften om affärer eller möten.",
      en: "You carry the risk that the first result fails to appear. Never promises about deals or meetings."
    },
    exempel: {
      sv: "Till exempel: Har ni inte fått 20 utkast inom 14 dagar är första månaden gratis.",
      en: "For example: If you have not received 20 drafts within 14 days, the first month is free."
    }
  },
  gjort_at_er: {
    namn: { sv: "Gjort åt er", en: "Done for you" },
    om: { sv: "Ni sköter uppstarten, kunden svarar på några frågor.", en: "You handle the setup; the customer answers a few questions." },
    exempel: {
      sv: "Till exempel: Vi sätter upp det åt er. Ni behöver avsätta en halvtimme.",
      en: "For example: We set it up for you. You need to set aside half an hour."
    }
  },
  ratt_tid: {
    namn: { sv: "Rätt tid", en: "The right time" },
    om: {
      sv: "Ett verkligt tillfälle i mottagarens kalender, aldrig påhittad brådska.",
      en: "A real moment in the recipient's calendar, never invented urgency."
    },
    exempel: { sv: "Till exempel: Före bokslutet vid årsskiftet.", en: "For example: Before the year-end closing." }
  },
  tva_vagar: {
    namn: { sv: "Två vägar in", en: "Two ways in" },
    om: { sv: "Ett lätt första steg bredvid det fulla erbjudandet.", en: "An easy first step next to the full offer." },
    exempel: {
      sv: "Till exempel: Bara utkasten, eller hela flödet skött av agenten.",
      en: "For example: Just the drafts, or the whole flow handled by the agent."
    }
  }
};

const T = {
  rubrik: { sv: "Erbjudanden i mejlen", en: "Offers in the emails" },
  om: {
    sv: "Iris fördelar de påslagna erbjudandena mellan bolagen efter vikten och mäter vad som ger svar. Mejlet lovar bara det som står i villkoren. Ändringar gäller nya utkast.",
    en: "Iris spreads the offers that are switched on across companies by weight and measures what gets replies. The email only promises what the terms say. Changes apply to new drafts."
  },
  villkor: { sv: "Villkor, som mejlet får lova dem", en: "Terms, as the email may promise them" },
  vikt: { sv: "Vikt (0–10)", en: "Weight (0–10)" },
  kravVillkor: { sv: "Fyll i villkoren först.", en: "Fill in the terms first." },
  skickade: { sv: "Skickade", en: "Sent" },
  svar: { sv: "Svar", en: "Replies" },
  positiva: { sv: "Positiva", en: "Positive" },
  moten: { sv: "Möten", en: "Meetings" },
  leder: { sv: "Leder", en: "Leading" },
  tidigt: { sv: "För tidigt att säga", en: "Too early to tell" },
  spara: { sv: "Spara erbjudanden", en: "Save offers" },
  sparar: { sv: "Sparar…", en: "Saving…" },
  sparat: { sv: "Sparat. Gäller nya utkast.", en: "Saved. Applies to new drafts." },
  hamtaFel: {
    sv: "Erbjudandena kunde inte hämtas, så inget kan sparas här just nu:",
    en: "The offers could not be loaded, so nothing can be saved here right now:"
  },
  forsokIgen: { sv: "Försök igen", en: "Try again" }
} satisfies Record<string, Localized>;

const falt = "focus-ring w-full rounded-input border border-ink/15 bg-paper px-3 py-2.5 text-[16px] leading-6";

function procent(andel: number | null): string {
  return andel === null ? "–" : `${Math.round(andel * 100)} %`;
}

function radenAv(svar: Svar): Record<string, Rad> {
  const vikter = new Map(svar.aktiva.map((a) => [a.nyckel, a.vikt]));
  return Object.fromEntries(
    svar.katalog.map(({ nyckel }) => [
      nyckel,
      { pa: (vikter.get(nyckel) ?? 0) > 0, vikt: String(vikter.get(nyckel) ?? 1), villkor: svar.villkor[nyckel] ?? "" }
    ])
  );
}

export function IrisErbjudanden() {
  const { text } = useLocale();
  const [data, setData] = useState<Svar | null>(null);
  const [rader, setRader] = useState<Record<string, Rad>>({});
  const [laddfel, setLaddfel] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const [status, setStatus] = useState("");

  const hamta = useCallback(() => {
    setLaddfel(null);
    setData(null);
    leadsAnrop<Svar>("/leads/erbjudanden")
      .then((svar) => {
        setData(svar);
        setRader(radenAv(svar));
      })
      .catch((orsak) => setLaddfel(felmeddelande(orsak)));
  }, []);

  useEffect(() => {
    hamta();
  }, [hamta]);

  function andra(nyckel: string, andring: Partial<Rad>) {
    setRader((forra) => ({ ...forra, [nyckel]: { ...forra[nyckel], ...andring } }));
    setStatus("");
  }

  async function spara() {
    if (busy || !data) return;
    const utanVillkor = data.katalog.find(({ nyckel }) => rader[nyckel]?.pa && !rader[nyckel].villkor.trim());
    if (utanVillkor) {
      setFel(`${text(ERBJUDANDEN[utanVillkor.nyckel]?.namn ?? { sv: utanVillkor.namn, en: utanVillkor.namn })}: ${text(T.kravVillkor)}`);
      document.getElementById(`erbjudande-villkor-${utanVillkor.nyckel}`)?.focus();
      return;
    }
    setBusy(true);
    setFel(null);
    setStatus("");
    try {
      const svar = await leadsAnrop<Svar>("/leads/erbjudanden", {
        method: "PUT",
        body: JSON.stringify({
          aktiva: data.katalog
            .filter(({ nyckel }) => rader[nyckel]?.pa)
            .map(({ nyckel }) => ({ nyckel, vikt: Math.min(10, Math.max(0, Math.round(Number(rader[nyckel].vikt) || 0))) })),
          villkor: Object.fromEntries(data.katalog.map(({ nyckel }) => [nyckel, rader[nyckel]?.villkor ?? ""]))
        })
      });
      setData(svar);
      setRader(radenAv(svar));
      setStatus(text(T.sparat));
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setBusy(false);
    }
  }

  if (laddfel) {
    return (
      <div role="alert" className="grid gap-3">
        <p className="max-w-[62ch] text-[0.9375rem] leading-6 text-danger">
          {text(T.hamtaFel)} {laddfel}
        </p>
        <button type="button" onClick={hamta} className={cn(btnSecondary, "justify-self-start")}>
          {text(T.forsokIgen)}
        </button>
      </div>
    );
  }
  if (data === null) {
    return <div className="h-48 animate-pulse rounded-card bg-ink/[0.055]" aria-busy="true" />;
  }

  const armar = new Map(data.resultat.armar.map((a) => [a.nyckel, a]));

  return (
    <section aria-labelledby="iris-erbjudanden-rubrik" className="grid gap-6">
      <div>
        <h2 id="iris-erbjudanden-rubrik" className={rubrikPanel}>
          {text(T.rubrik)}
        </h2>
        <p className="mt-1 max-w-[62ch] text-[0.9375rem] leading-6 text-ink-muted">{text(T.om)}</p>
      </div>

      <ol className="divide-y divide-ink/12 border-y border-ink/15">
        {data.katalog.map(({ nyckel, namn }) => {
          const rad = rader[nyckel];
          const info = ERBJUDANDEN[nyckel];
          const arm = armar.get(nyckel);
          const visatNamn = info ? text(info.namn) : namn;
          return (
            <li key={nyckel} className="grid gap-3 pb-5">
              <Vaxel
                paslagen={rad.pa}
                etikett={visatNamn}
                beskrivning={info ? text(info.om) : ""}
                upptagen={busy}
                onByt={(pa) => andra(nyckel, { pa })}
              />
              <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_8rem]">
                <label className="grid gap-1">
                  <span className={etikett}>{text(T.villkor)}</span>
                  <textarea
                    id={`erbjudande-villkor-${nyckel}`}
                    value={rad.villkor}
                    maxLength={VILLKOR_MAX}
                    rows={2}
                    placeholder={info ? text(info.exempel) : undefined}
                    onChange={(e) => andra(nyckel, { villkor: e.target.value })}
                    className={cn(falt, "resize-y")}
                  />
                  <span className={meta}>
                    {rad.villkor.length}/{VILLKOR_MAX}
                  </span>
                </label>
                {rad.pa ? (
                  <label className="grid content-start gap-1">
                    <span className={etikett}>{text(T.vikt)}</span>
                    <input
                      type="number"
                      inputMode="numeric"
                      min={0}
                      max={10}
                      value={rad.vikt}
                      onChange={(e) => andra(nyckel, { vikt: e.target.value })}
                      className={falt}
                    />
                  </label>
                ) : null}
              </div>
              {arm && arm.utkast > 0 ? (
                <p className={cn(meta, "flex flex-wrap gap-x-4 gap-y-1")}>
                  <span>
                    {text(T.skickade)} {arm.skickade}
                  </span>
                  <span>
                    {text(T.svar)} {arm.svar} ({procent(arm.svarsfrekvens)})
                  </span>
                  <span>
                    {text(T.positiva)} {arm.positiva} ({procent(arm.positiv_andel)})
                  </span>
                  <span>
                    {text(T.moten)} {arm.moten}
                  </span>
                  <span className={arm.lage === "leder" ? "font-semibold text-ink" : undefined}>
                    {arm.lage === "leder" ? text(T.leder) : text(T.tidigt)}
                  </span>
                </p>
              ) : null}
            </li>
          );
        })}
      </ol>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <button
          type="button"
          onClick={() => void spara()}
          aria-disabled={busy || undefined}
          className={cn(btnPrimary, "aria-disabled:opacity-60")}
        >
          {busy ? text(T.sparar) : text(T.spara)}
        </button>
        <span aria-live="polite" className="text-[0.9375rem] text-ink-muted">
          {status}
        </span>
        {fel ? (
          <p role="alert" className="max-w-[62ch] break-words text-[0.9375rem] text-danger">
            {fel}
          </p>
        ) : null}
      </div>
    </section>
  );
}
