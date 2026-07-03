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

export function OnboardingForm() {
  const [fields, setFields] = useState(defaultFields);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    startTransition(async () => {
      const result = await saveBusinessContext(fields);
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