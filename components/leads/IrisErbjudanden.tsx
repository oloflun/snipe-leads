"use client";

/* design · Operate-yta i det låsta systemet (DESIGN.md, Tier 0): samma växel,
   fält och knappar som IrisEskalering och IrisProdukter, ingen ny riktning. */

import { Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Vaxel } from "@/components/leads/IrisEskalering";
import { btnPrimary, btnSecondary, btnLiten, etikett, meta, rubrikPanel } from "@/components/ui";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { leadsAnrop } from "@/lib/leads/suite";
import { cn } from "@/lib/utils";

/**
 * Leads › Erbjudanden (Antons beställning 2026-10-10, flyttad hit ur
 * Inställningar och utökad 2026-10-25).
 *
 * Kunden slår på de erbjudanden Iris ska A/B-testa i de kalla mejlen, med
 * vikt och egna villkor: katalogens tre, och egna erbjudanden med namn och
 * mejlform (A rakt på, B med en fråga). Två erbjudanden med samma villkor och
 * olika form A/B-testar formen. Villkoren är det enda mejlet får lova, och ett
 * erbjudande kan bara slås på när de är ifyllda. Har kunden produkter skrivs
 * villkoren per produkt: ett mejl om en produkt får bara den produktens
 * villkor (ett tomt fält betyder att erbjudandet inte används för produkten).
 * Resultatet per erbjudande räknas ur trådarna (GET /leads/erbjudanden) och ett
 * erbjudande kallas ledande först när det håller statistiskt
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
type Form = "rak" | "fraga";
type Svar = {
  katalog: { nyckel: string; namn: string; form: Form; egen: boolean }[];
  produkter: string[];
  aktiva: { nyckel: string; vikt: number }[];
  villkor: Record<string, string | Record<string, string>>;
  egna: Record<string, { namn: string; form: Form }>;
  resultat: { armar: Arm[]; ledare: string | null; min_skickade: number };
};
/** Villkoren per produktnamn; nyckeln "" när kunden saknar produkter (en text för alla). */
type Rad = {
  nyckel: string;
  namn: string;
  form: Form;
  egen: boolean;
  pa: boolean;
  vikt: string;
  villkor: Record<string, string>;
};

const VILLKOR_MAX = 600;
const NAMN_MAX = 60;
const ALLA = "";

/** Namn och förklaring per katalognyckel. Egna erbjudanden bär kundens namn. */
const ERBJUDANDEN: Record<string, { namn: Localized; om: Localized; exempel: Localized }> = {
  gratis_prov: {
    namn: { sv: "Testa gratis", en: "Try it free" },
    om: {
      sv: "Mottagaren får ett färdigt resultat innan något är bestämt.",
      en: "The recipient gets a finished result before anything is decided."
    },
    exempel: {
      sv: "Till exempel: Fem kvalificerade leads med färdiga första mejl, utan kostnad. Handling: vill de ha dem räcker ett svar på mejlet.",
      en: "For example: Five qualified leads with ready first emails, free of charge. Action: if they want them, a reply to the email is enough."
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
      sv: "Till exempel: 20 företag i en pilot, tre månader utan kostnad, sedan 50 % rabatt för den som stannar.",
      en: "For example: 20 companies in a pilot, three months free of charge, then 50% off for those who stay."
    }
  }
};

const FORMER: Record<Form, { namn: Localized; om: Localized }> = {
  rak: {
    namn: { sv: "Form A, rakt på", en: "Form A, straight to the point" },
    om: {
      sv: "Utmaningen i deras arbete, vad agenten gör, erbjudandet och en inbjudan.",
      en: "The challenge in their work, what the agent does, the offer and an invitation."
    }
  },
  fraga: {
    namn: { sv: "Form B, med en fråga", en: "Form B, with a question" },
    om: {
      sv: "Som A, men efter ingången en fråga om vilket av två moment som tar mest tid för dem.",
      en: "Like A, but after the opening a question about which of two tasks takes them the most time."
    }
  }
};

const T = {
  rubrik: { sv: "Erbjudanden i mejlen", en: "Offers in the emails" },
  om: {
    sv: "Iris fördelar de påslagna erbjudandena mellan bolagen efter vikten och mäter vad som ger svar. Erbjudandet styr hela mejlet, och agenten anpassar det till varje bolags verksamhet. Mejlet lovar bara det som står i villkoren. Ändringar gäller nya utkast.",
    en: "Iris spreads the offers that are switched on across companies by weight and measures what gets replies. The offer shapes the whole email, and the agent adapts it to each company's business. The email only promises what the terms say. Changes apply to new drafts."
  },
  villkor: { sv: "Villkor, som mejlet får lova dem", en: "Terms, as the email may promise them" },
  villkorFor: { sv: "Villkor för", en: "Terms for" },
  tomtFalt: { sv: "Tomt = används inte för den produkten.", en: "Empty = not used for that product." },
  vikt: { sv: "Vikt (0–10)", en: "Weight (0–10)" },
  namn: { sv: "Erbjudandets namn", en: "Name of the offer" },
  form: { sv: "Mejlets form", en: "Email form" },
  egetExempel: {
    sv: "Beskriv erbjudandet med era ord: vad de får, vad det kostar och vad de gör för att få det. Till exempel: Tre månader utan kostnad, sedan 50 % rabatt. Handling: demo på er sajt, eller ett svar så bokar vi en genomgång.",
    en: "Describe the offer in your own words: what they get, what it costs and what they do to get it. For example: Three months free of charge, then 50% off. Action: a demo on your site, or a reply and we book a walkthrough."
  },
  laggTill: { sv: "Lägg till erbjudande", en: "Add offer" },
  taBort: { sv: "Ta bort", en: "Remove" },
  nyttNamn: { sv: "Nytt erbjudande", en: "New offer" },
  kravVillkor: { sv: "Fyll i villkoren för minst en produkt först.", en: "Fill in the terms for at least one product first." },
  kravNamn: { sv: "Ge erbjudandet ett namn.", en: "Give the offer a name." },
  utkast: { sv: "Utkast", en: "Drafts" },
  skickade: { sv: "Skickade", en: "Sent" },
  svar: { sv: "Svar", en: "Replies" },
  positiva: { sv: "Positiva", en: "Positive" },
  moten: { sv: "Möten", en: "Meetings" },
  leder: { sv: "Leder", en: "Leading" },
  tidigt: { sv: "För tidigt att säga", en: "Too early to tell" },
  inget: { sv: "Inga utkast med erbjudandet än.", en: "No drafts with this offer yet." },
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

function radernaAv(svar: Svar): Rad[] {
  const vikter = new Map(svar.aktiva.map((a) => [a.nyckel, a.vikt]));
  return svar.katalog.map(({ nyckel, namn, form, egen }) => {
    const sparat = svar.villkor[nyckel];
    // En sparad text för alla produkter fyller varje produktfält; nästa
    // sparning gör den till villkor per produkt.
    const villkor = Object.fromEntries(
      faltnycklar(svar).map((p) => {
        if (typeof sparat === "string") return [p, sparat];
        const traff = Object.entries(sparat ?? {}).find(([n]) => n.toLowerCase() === p.toLowerCase());
        return [p, traff?.[1] ?? ""];
      })
    );
    return { nyckel, namn, form, egen, pa: (vikter.get(nyckel) ?? 0) > 0, vikt: String(vikter.get(nyckel) ?? 1), villkor };
  });
}

export function IrisErbjudanden() {
  const { text } = useLocale();
  const [data, setData] = useState<Svar | null>(null);
  const [rader, setRader] = useState<Rad[]>([]);
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
        setRader(radernaAv(svar));
      })
      .catch((orsak) => setLaddfel(felmeddelande(orsak)));
  }, []);

  useEffect(() => {
    hamta();
  }, [hamta]);

  function andra(nyckel: string, andring: Partial<Rad>) {
    setRader((forra) => forra.map((r) => (r.nyckel === nyckel ? { ...r, ...andring } : r)));
    setStatus("");
  }

  function andraVillkor(nyckel: string, produkt: string, varde: string) {
    setRader((forra) => forra.map((r) => (r.nyckel === nyckel ? { ...r, villkor: { ...r.villkor, [produkt]: varde } } : r)));
    setStatus("");
  }

  function laggTill() {
    if (!data) return;
    // Nyckeln är bara ett id (a-z, 0-9, _ och -); kunden ser namnet.
    const nyckel = `eget-${Date.now().toString(36)}`;
    setRader((forra) => [
      ...forra,
      {
        nyckel,
        namn: "",
        form: "rak",
        egen: true,
        pa: false,
        vikt: "1",
        villkor: Object.fromEntries(faltnycklar(data).map((p) => [p, ""]))
      }
    ]);
    setStatus("");
    window.setTimeout(() => document.getElementById(`erbjudande-namn-${nyckel}`)?.focus(), 0);
  }

  function taBort(nyckel: string) {
    setRader((forra) => forra.filter((r) => r.nyckel !== nyckel));
    setStatus("");
  }

  const faltId = (nyckel: string, produkt: string) =>
    `erbjudande-villkor-${nyckel}-${produkt.replace(/[^A-Za-z0-9]+/g, "-") || "alla"}`;

  const visatNamn = (r: Rad) =>
    r.egen ? r.namn || text(T.nyttNamn) : ERBJUDANDEN[r.nyckel] ? text(ERBJUDANDEN[r.nyckel].namn) : r.namn;

  async function spara() {
    if (busy || !data) return;
    const utanNamn = rader.find((r) => r.egen && !r.namn.trim());
    if (utanNamn) {
      setFel(text(T.kravNamn));
      document.getElementById(`erbjudande-namn-${utanNamn.nyckel}`)?.focus();
      return;
    }
    const utanVillkor = rader.find((r) => r.pa && !Object.values(r.villkor).some((v) => v.trim()));
    if (utanVillkor) {
      setFel(`${visatNamn(utanVillkor)}: ${text(T.kravVillkor)}`);
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
          aktiva: rader
            .filter((r) => r.pa)
            .map((r) => ({ nyckel: r.nyckel, vikt: Math.min(10, Math.max(0, Math.round(Number(r.vikt) || 0))) })),
          villkor: Object.fromEntries(
            rader.map((r) => [r.nyckel, data.produkter.length ? r.villkor : (r.villkor[ALLA] ?? "")])
          ),
          egna: Object.fromEntries(
            rader.filter((r) => r.egen).map((r) => [r.nyckel, { namn: r.namn.trim(), form: r.form }])
          )
        })
      });
      setData(svar);
      setRader(radernaAv(svar));
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
        {rader.map((rad) => {
          const info = ERBJUDANDEN[rad.nyckel];
          const arm = armar.get(rad.nyckel);
          return (
            <li key={rad.nyckel} className="grid gap-3 py-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <Vaxel
                    paslagen={rad.pa}
                    etikett={visatNamn(rad)}
                    beskrivning={info ? text(info.om) : text(FORMER[rad.form].namn)}
                    upptagen={busy}
                    onByt={(pa) => andra(rad.nyckel, { pa })}
                  />
                </div>
                {rad.egen ? (
                  <button
                    type="button"
                    onClick={() => taBort(rad.nyckel)}
                    disabled={busy}
                    aria-label={`${text(T.taBort)}: ${visatNamn(rad)}`}
                    className={cn(btnSecondary, btnLiten)}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                    {text(T.taBort)}
                  </button>
                ) : null}
              </div>
              {rad.egen ? (
                <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,16rem)]">
                  <label className="grid gap-1">
                    <span className={etikett}>{text(T.namn)}</span>
                    <input
                      id={`erbjudande-namn-${rad.nyckel}`}
                      value={rad.namn}
                      maxLength={NAMN_MAX}
                      onChange={(e) => andra(rad.nyckel, { namn: e.target.value })}
                      className={falt}
                    />
                  </label>
                  <label className="grid gap-1">
                    <span className={etikett}>{text(T.form)}</span>
                    <select
                      value={rad.form}
                      onChange={(e) => andra(rad.nyckel, { form: e.target.value as Form })}
                      className={falt}
                    >
                      {(Object.keys(FORMER) as Form[]).map((f) => (
                        <option key={f} value={f}>
                          {text(FORMER[f].namn)}
                        </option>
                      ))}
                    </select>
                    <span className={meta}>{text(FORMER[rad.form].om)}</span>
                  </label>
                </div>
              ) : null}
              <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_8rem]">
                <div className="grid gap-3">
                  {perProdukt ? <p className={meta}>{text(T.tomtFalt)}</p> : null}
                  {faltnycklar(data).map((produkt) => (
                    <label key={produkt || "alla"} className="grid gap-1">
                      <span className={etikett}>
                        {produkt ? `${text(T.villkorFor)} ${produkt}` : text(T.villkor)}
                      </span>
                      <textarea
                        id={faltId(rad.nyckel, produkt)}
                        value={rad.villkor[produkt] ?? ""}
                        maxLength={VILLKOR_MAX}
                        rows={rad.egen ? 3 : 2}
                        placeholder={info ? text(info.exempel) : text(T.egetExempel)}
                        onChange={(e) => andraVillkor(rad.nyckel, produkt, e.target.value)}
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
                      onChange={(e) => andra(rad.nyckel, { vikt: e.target.value })}
                      className={falt}
                    />
                  </label>
                ) : null}
              </div>
              {arm && arm.utkast > 0 ? (
                <p className={cn(meta, "flex flex-wrap gap-x-4 gap-y-1")}>
                  <span>
                    {text(T.utkast)} {arm.utkast}
                  </span>
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
              ) : rad.pa ? (
                <p className={meta}>{text(T.inget)}</p>
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
        <button type="button" onClick={laggTill} disabled={busy} className={btnSecondary}>
          <Plus className="h-4 w-4" aria-hidden />
          {text(T.laggTill)}
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
