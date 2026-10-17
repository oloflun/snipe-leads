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
 * erbjudande kan bara slås på när de är ifyllda. Har kunden produkter skrivs
 * villkoren per produkt: ett mejl om en produkt får bara den produktens
 * villkor (ett tomt fält betyder att erbjudandet inte används för produkten).
 * Resultatet per erbjudande räknas ur trådarna (GET /leads/erbjudanden) och en
 * arm kallas ledande först när den håller statistiskt
 * (app/leads/erbjudanden.py:sammanstall).
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
  produkter: string[];
  aktiva: { nyckel: string; vikt: number }[];
  villkor: Record<string, string | Record<string, string>>;
  resultat: { armar: Arm[]; ledare: string | null; min_skickade: number };
};
/** Villkoren per produktnamn; nyckeln "" när kunden saknar produkter (en text för alla). */
type Rad = { pa: boolean; vikt: string; villkor: Record<string, string> };

const VILLKOR_MAX = 600;
const ALLA = "";

/** Namn och förklaring per nyckel. Okända nycklar visas med katalogens namn. */
const ERBJUDANDEN: Record<string, { namn: Localized; om: Localized; exempel: Localized }> = {
  gratis_prov: {
    namn: { sv: "Testa gratis", en: "Try it free" },
    om: {
      sv: "Mottagaren får ett färdigt resultat innan något är bestämt.",
      en: "The recipient gets a finished result before anything is decided."
    },
    exempel: {
      sv: "Till exempel: Fem kvalificerade leads med färdiga första mejl, utan kostnad. Svara ja så skickar vi dem inom två dagar.",
      en: "For example: Five qualified leads with ready first emails, free of charge. Reply yes and we send them within two days."
    }
  },
  garanti: {
    namn: { sv: "Garanti", en: "Guarantee" },
    om: {
      sv: "Ni tar risken: nås inte resultatet får de mer tid utan kostnad.",
      en: "You carry the risk: if the result is not reached, they get more time free of charge."
    },
    exempel: {
      sv: "Till exempel: Minst 10 nya kunddialoger inom 90 dagar, annars förlänger vi provperioden utan kostnad.",
      en: "For example: At least 10 new customer conversations within 90 days, or we extend the trial free of charge."
    }
  },
  pilot: {
    namn: { sv: "Begränsad pilot", en: "Limited pilot" },
    om: {
      sv: "Ett fåtal platser och ett pris som inte erbjuds igen, med ett ärligt skäl.",
      en: "A few places and a price that will not be offered again, with an honest reason."
    },
    exempel: {
      sv: "Till exempel: 20 pilotplatser, 50 % rabatt första året och 25 % så länge de stannar.",
      en: "For example: 20 pilot places, 50% off the first year and 25% for as long as they stay."
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
  villkorFor: { sv: "Villkor för", en: "Terms for" },
  tomtFalt: { sv: "Tomt = används inte för den produkten.", en: "Empty = not used for that product." },
  vikt: { sv: "Vikt (0–10)", en: "Weight (0–10)" },
  kravVillkor: { sv: "Fyll i villkoren för minst en produkt först.", en: "Fill in the terms for at least one product first." },
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

/** Fälten per erbjudande: ett per produkt, eller ett för alla när produkter saknas. */
function faltnycklar(svar: Svar): string[] {
  return svar.produkter.length ? svar.produkter : [ALLA];
}

function radenAv(svar: Svar): Record<string, Rad> {
  const vikter = new Map(svar.aktiva.map((a) => [a.nyckel, a.vikt]));
  return Object.fromEntries(
    svar.katalog.map(({ nyckel }) => {
      const sparat = svar.villkor[nyckel];
      // En sparad text för alla produkter fyller varje produktfält; nästa
      // sparning gör den till villkor per produkt.
      const villkor = Object.fromEntries(
        faltnycklar(svar).map((p) => {
          if (typeof sparat === "string") return [p, sparat];
          const traff = Object.entries(sparat ?? {}).find(([namn]) => namn.toLowerCase() === p.toLowerCase());
          return [p, traff?.[1] ?? ""];
        })
      );
      return [nyckel, { pa: (vikter.get(nyckel) ?? 0) > 0, vikt: String(vikter.get(nyckel) ?? 1), villkor }];
    })
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

  function andraVillkor(nyckel: string, produkt: string, varde: string) {
    setRader((forra) => ({
      ...forra,
      [nyckel]: { ...forra[nyckel], villkor: { ...forra[nyckel].villkor, [produkt]: varde } }
    }));
    setStatus("");
  }

  const faltId = (nyckel: string, produkt: string) =>
    `erbjudande-villkor-${nyckel}-${produkt.replace(/[^A-Za-z0-9]+/g, "-") || "alla"}`;

  async function spara() {
    if (busy || !data) return;
    const utanVillkor = data.katalog.find(
      ({ nyckel }) => rader[nyckel]?.pa && !Object.values(rader[nyckel].villkor).some((v) => v.trim())
    );
    if (utanVillkor) {
      setFel(`${text(ERBJUDANDEN[utanVillkor.nyckel]?.namn ?? { sv: utanVillkor.namn, en: utanVillkor.namn })}: ${text(T.kravVillkor)}`);
      document.getElementById(faltId(utanVillkor.nyckel, faltnycklar(data)[0]))?.focus();
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
          villkor: Object.fromEntries(
            data.katalog.map(({ nyckel }) => {
              const villkor = rader[nyckel]?.villkor ?? {};
              return [nyckel, data.produkter.length ? villkor : (villkor[ALLA] ?? "")];
            })
          )
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
  const perProdukt = data.produkter.length > 0;

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
                <div className="grid gap-3">
                  {perProdukt ? <p className={meta}>{text(T.tomtFalt)}</p> : null}
                  {faltnycklar(data).map((produkt) => (
                    <label key={produkt || "alla"} className="grid gap-1">
                      <span className={etikett}>
                        {produkt ? `${text(T.villkorFor)} ${produkt}` : text(T.villkor)}
                      </span>
                      <textarea
                        id={faltId(nyckel, produkt)}
                        value={rad.villkor[produkt] ?? ""}
                        maxLength={VILLKOR_MAX}
                        rows={2}
                        placeholder={info ? text(info.exempel) : undefined}
                        onChange={(e) => andraVillkor(nyckel, produkt, e.target.value)}
                        className={cn(falt, "resize-y")}
                      />
                      <span className={meta}>
                        {(rad.villkor[produkt] ?? "").length}/{VILLKOR_MAX}
                      </span>
                    </label>
                  ))}
                </div>
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
