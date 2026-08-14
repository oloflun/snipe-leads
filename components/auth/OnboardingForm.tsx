"use client";

import Link from "next/link";
import { useState, useTransition } from "react";
import { saveBusinessContext } from "@/lib/actions/onboarding";

const defaultFields = {
  product: "AI-driven outbound för svenska B2B-team",
  targetAudience: "Tjänstebolag 10-200 anställda",
  industries: "bygg, fastighet, konsult, SaaS",
  geography: "Skåne, Stockholm, Göteborg",
  tone: "lågmäld, specifik, professionell",
  offer: "första analys av outbound-potential",
  cta: "skicka två konkreta exempel",
  contactRoles: "VD, Försäljningschef, Marknadschef"
} as const;

const fieldConfig = [
  ["product", "Produkt eller tjänst"],
  ["targetAudience", "Målgrupp / ICP"],
  ["industries", "Fokusbranscher"],
  ["geography", "Geografi"],
  ["tone", "Tonalitet"],
  ["offer", "Erbjudande"],
  ["cta", "CTA"],
  ["contactRoles", "Roller att kontakta"]
] as const;

// Supportsidan. Tomma från start — det här är ERT innehåll, och en förifylld
// gissning riskerar att sparas som om den vore bolagets policy.
const supportDefaults = {
  companyName: "",
  guarantee: "",
  terms: "",
  delivery: "",
  returnsPolicy: "",
  supportEmail: ""
};

const supportFieldConfig = [
  ["companyName", "Företagsnamn", "Namnet kunden ser i svaren.", false],
  [
    "guarantee",
    "Garanti",
    "Hur lång garanti, vad den täcker och vad som krävs för att den ska gälla.",
    true
  ],
  ["terms", "Köp- och betalningsvillkor", "Betalsätt, fakturavillkor, priser.", true],
  ["delivery", "Leverans och frakt", "Leveranstider, fraktsätt, spårning.", true],
  [
    "returnsPolicy",
    "Retur och reklamation",
    "Ångerrätt, returfrist och hur en reklamation går till.",
    true
  ],
  [
    "supportEmail",
    "Adress för överlämning",
    "Dit ärenden går när agenten lämnar över till en människa.",
    false
  ]
] as const;

export function OnboardingForm() {
  const [fields, setFields] = useState(defaultFields);
  const [support, setSupport] = useState(supportDefaults);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  // Antal ifyllda fält som blir kunskapsbasartiklar. Visas löpande så kunden
  // ser vad agenten faktiskt kommer kunna svara på — i stället för att upptäcka
  // efteråt att den eskalerar allt.
  const kbCount = [support.guarantee, support.terms, support.delivery, support.returnsPolicy]
    .map((value) => value.trim())
    .filter((value) => value.length >= 10).length;

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    startTransition(async () => {
      const result = await saveBusinessContext({ ...fields, ...support });
      if (!result.success) {
        setError(result.error ?? "Kunde inte spara business context.");
      }
    });
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="mt-12 grid grid-cols-12 gap-x-8 gap-y-6">
        {fieldConfig.map(([key, label]) => (
          <label key={key} className="col-span-12 grid gap-2 border-t border-ink/15 pt-4 md:col-span-6">
            <span className="kicker text-mineral">{label}</span>
            <input
              className="h-14 border border-ink/15 bg-paper2/70 px-4 text-[15px] outline-none focus:border-ochre"
              value={fields[key]}
              onChange={(event) =>
                setFields((current) => ({
                  ...current,
                  [key]: event.target.value
                }))
              }
              required
            />
          </label>
        ))}
      </div>

      <div className="mt-16 border-t border-ink/15 pt-8">
        <h2 className="font-semibold">Vad kundservice-agenten ska kunna svara på</h2>
        <p className="mt-2 max-w-2xl text-[15px] leading-7 text-ink/62">
          Agenten svarar bara utifrån era egna villkor och gissar aldrig. Det ni skriver här
          blir dess kunskapsbas — lämnar ni ett fält tomt lämnar agenten över den frågan till
          en människa i stället för att hitta på ett svar. Ni kan fylla på när som helst.
        </p>

        <div className="mt-8 grid grid-cols-12 gap-x-8 gap-y-6">
          {supportFieldConfig.map(([key, label, hint, multiline]) => (
            <label
              key={key}
              className={`col-span-12 grid gap-2 border-t border-ink/15 pt-4 ${
                multiline ? "" : "md:col-span-6"
              }`}
            >
              <span className="kicker text-mineral">{label}</span>
              <span className="text-[13px] leading-5 text-ink/50">{hint}</span>
              {multiline ? (
                <textarea
                  rows={3}
                  className="border border-ink/15 bg-paper2/70 px-4 py-3 text-[15px] outline-none focus:border-ochre"
                  value={support[key]}
                  onChange={(event) =>
                    setSupport((current) => ({ ...current, [key]: event.target.value }))
                  }
                />
              ) : (
                <input
                  className="h-14 border border-ink/15 bg-paper2/70 px-4 text-[15px] outline-none focus:border-ochre"
                  value={support[key]}
                  onChange={(event) =>
                    setSupport((current) => ({ ...current, [key]: event.target.value }))
                  }
                />
              )}
            </label>
          ))}
        </div>

        <p className="mt-6 text-[14px] text-ink/62">
          {kbCount === 0
            ? "Agenten får inga svar än — den lämnar över allt till er tills ni fyllt i något."
            : `Agenten kommer kunna svara grundat på ${kbCount} av 4 områden.`}
        </p>
      </div>

      {error ? <p className="mt-6 text-[14px] text-ochre">{error}</p> : null}

      <div className="mt-10 flex flex-wrap gap-4">
        <button
          type="submit"
          disabled={isPending}
          className="inline-flex items-center gap-3 bg-ink px-5 py-3 font-mono text-[13px] uppercase tracking-[0.18em] text-paper transition-colors duration-500 hover:bg-ochre hover:text-ink disabled:opacity-60"
        >
          {isPending ? "Sparar..." : "Spara business context"}
          <span aria-hidden>↗</span>
        </button>
        <Link
          href="/settings/mailboxes"
          className="inline-flex items-center border border-ink/15 px-5 py-3 font-mono text-[13px] uppercase tracking-[0.18em] transition hover:border-ochre hover:text-ochre"
        >
          Koppla mailbox senare
        </Link>
      </div>
    </form>
  );
}