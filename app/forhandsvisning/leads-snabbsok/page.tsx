"use client";

/**
 * OKOMMITTERAD granskningssida för Leads-snabbsöket (2026-09-02).
 *
 * Samma mönster som /forhandsvisning/exempelbolag: panelen ligger bakom
 * admin-inloggning i produkten, så det här är enda sättet att granska
 * pixlarna utan konto. All data är påhittad; fetch stubbas i klienten så
 * att knappen ger ett deterministiskt resultat utan backend.
 */

import { useEffect, useState } from "react";
import { LeadsRunForm } from "@/components/leads/LeadsRunForm";
import { LeadsSnabbsok } from "@/components/leads/LeadsSnabbsok";

const SVAR: Record<string, unknown> = {
  "/api/snajp-support/leads/runs/batch": {
    jobs: [{ job_id: "prov-1" }],
    fase: "soker"
  },
  "/api/snajp-support/leads/jobb/prov-1": {
    status: "completed",
    result: {
      fase: "klar",
      count: 3,
      utan_kontakt: 2,
      prospects: [
        {
          prospect_id: "p1",
          company_name: "Nordvik Bygg AB",
          website: "https://nordvikbygg.example",
          ort: "Malmö",
          contact_name: "Sara Lindqvist",
          contact_role: "VD",
          contact_email: "sara.lindqvist@nordvikbygg.example",
          contact_level: "named_role_match",
          contact_form_url: null
        },
        {
          prospect_id: "p2",
          company_name: "Sundfjord El & Installation AB",
          website: "https://sundfjordel.example",
          ort: "Helsingborg",
          contact_name: null,
          contact_role: null,
          contact_email: "info@sundfjordel.example",
          contact_level: "role_address",
          contact_form_url: null
        },
        {
          prospect_id: "p3",
          company_name: "Åkerberg & Söner Måleri AB",
          website: "https://akerbergmaleri.example",
          ort: "Lund",
          contact_name: null,
          contact_role: null,
          contact_email: null,
          contact_level: "contact_form",
          contact_form_url: "https://akerbergmaleri.example/kontakt"
        }
      ]
    }
  }
};

export default function Sida() {
  const [klar, setKlar] = useState(false);

  useEffect(() => {
    const riktig = window.fetch.bind(window);
    window.fetch = async (input, init) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      const väg = url.replace(/^https?:\/\/[^/]+/, "");
      if (väg in SVAR) {
        await new Promise((r) => setTimeout(r, 400));
        return new Response(JSON.stringify(SVAR[väg]), {
          status: väg.includes("/runs/batch") ? 202 : 200,
          headers: { "Content-Type": "application/json" }
        });
      }
      return riktig(input, init);
    };
    setKlar(true);
    return () => {
      window.fetch = riktig;
    };
  }, []);

  if (!klar) return null;

  return (
    <main className="mx-auto max-w-[1400px] px-4 py-8 md:px-6 md:py-10">
      <h1 className="font-display text-3xl tracking-[-0.02em]">
        Granskning: Leads-snabbsöket
      </h1>
      <p className="mt-2 max-w-[70ch] text-[15px] text-mineral">
        Repliken av leads-sektionen på /admin/testkorningar. Skriv något i
        sökraden och tryck Sök Leads — svaret är stubbat och deterministiskt.
      </p>
      <section className="mt-10 border-t border-ink/15 pt-8">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,760px)_minmax(320px,1fr)] lg:items-start">
          <LeadsRunForm
            isTest
            rubrik={
              <>
                <h2 className="font-display text-2xl tracking-[-0.02em]">Leads-agenten</h2>
                <p className="mt-2 max-w-[65ch] text-[15px] text-mineral">
                  Kör research över prospekten. Lämna ett fält tomt för att använda arbetsytans
                  sparade värde.
                </p>
              </>
            }
          />
          <LeadsSnabbsok isTest />
        </div>
      </section>
    </main>
  );
}
