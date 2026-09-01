"use client";

import { useState } from "react";
import { btnPrimary } from "@/components/ui";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Leads-snabbsökningen ("Sök Leads") — tilläggstjänstens panel.
 *
 * ## Vad den är
 *
 * En rad att beskriva vilka kunder man behöver (och till vilken produkt), en
 * knapp, och en lista med 10–15 leads. Inget mer. Panelen kör backendens
 * `scope="sok"` (EN Gemini-sökning, inga researchjobb, inga utkast) — det är
 * den billigaste vägen genom leads-kedjan, byggd för exakt det här: snabbt
 * svar på "finns det bolag där ute som matchar?".
 *
 * ## Varför sökraden blir `must_have`-override
 *
 * Texten läggs som en signal OVANPÅ arbetsytans sparade målgrupp i just den
 * här körningen — den ersätter aldrig ICP:n. Så nischar sökningen ner sig på
 * det kunden redan valt, plus radens precisering, i stället för att leta
 * brett. Tomma fält faller tillbaka på det sparade, precis som i
 * LeadsRunForm.
 *
 * ## Kontaktkravet
 *
 * Backenden listar bara träffar med en kontaktväg (kontaktperson, arbetsmejl
 * eller kontaktformulär på bolagets egen domän). Träffar utan kontakt räknas
 * i `utan_kontakt` och visas som en fotnot — de finns i registret för
 * komplettering, men de säljs inte här som färdiga leads.
 */

type SnabbLead = {
  prospect_id: string;
  company_name: string | null;
  website: string | null;
  ort: string | null;
  contact_name: string | null;
  contact_role: string | null;
  contact_email: string | null;
  contact_level: string | null;
  contact_form_url: string | null;
};

type SokResultat = {
  fase?: string;
  prospects?: SnabbLead[];
  count?: number;
  utan_kontakt?: number;
};

const KONTAKTETIKETT: Record<string, string> = {
  named_role_match: "Namngiven beslutsfattare",
  named_other: "Namngiven kontakt",
  role_address: "Rolladress",
  contact_form: "Kontaktformulär"
};

async function pollaJobb<T>(jobId: string): Promise<T> {
  for (let försök = 0; försök < 90; försök += 1) {
    await new Promise((r) => setTimeout(r, försök < 5 ? 800 : 2000));
    const svar = await fetch(`/api/snajp-support/leads/jobb/${jobId}`);
    const j =
      (await readJsonBody<{ status?: string; result?: T; error?: string }>(svar)) ?? {};
    if (j.status === "completed" && j.result) return j.result;
    if (j.status === "failed") throw new Error(j.error ?? "Sökningen misslyckades.");
  }
  throw new Error("Sökningen tog för lång tid. Försök igen om en stund.");
}

export function LeadsSnabbsok({ isTest = false }: { isTest?: boolean }) {
  const [fråga, setFråga] = useState("");
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const [leads, setLeads] = useState<SnabbLead[] | null>(null);
  const [utanKontakt, setUtanKontakt] = useState(0);

  async function sök() {
    setBusy(true);
    setFel(null);
    setLeads(null);
    setUtanKontakt(0);
    try {
      const start = await fetch("/api/snajp-support/leads/runs/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scope: "sok",
          limit: 12,
          is_test: isTest,
          overrides: { must_have: [fråga.trim()] }
        })
      });
      const startSvar =
        (await readJsonBody<{ jobs?: { job_id: string }[]; detail?: unknown; error?: string }>(
          start
        )) ?? {};
      const jobId = startSvar.jobs?.[0]?.job_id;
      if (!start.ok || !jobId) {
        const detalj =
          typeof startSvar.detail === "string" ? startSvar.detail : startSvar.error;
        throw new Error(detalj ?? `Kunde inte starta sökningen (${start.status}).`);
      }
      const resultat = await pollaJobb<SokResultat>(jobId);
      setLeads(resultat.prospects ?? []);
      setUtanKontakt(resultat.utan_kontakt ?? 0);
      // Bolagsregistret lyssnar redan på händelsen från LeadsRunForm — de nya
      // raderna finns där också, så registret ska uppdatera sig här med.
      window.dispatchEvent(new Event("snipra:leads-korning-klar"));
    } catch (e) {
      setFel(felmeddelande(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="leads-snabbsok" className="rounded-card bg-paper2/60 p-5">
      <h3 id="leads-snabbsok" className="font-display text-xl tracking-[-0.02em]">
        Sök Leads
      </h3>
      <p className="mt-2 text-[14px] leading-6 text-mineral">
        Beskriv vilka kunder du behöver och till vilken produkt. Sökningen utgår från arbetsytans
        sparade målgrupp och nischar ner mot raden — varje träff har en kontaktväg.
      </p>

      <form
        className="mt-4 flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (!busy && fråga.trim()) void sök();
        }}
      >
        <input
          type="text"
          value={fråga}
          onChange={(e) => setFråga(e.target.value)}
          placeholder="T.ex. byggbolag i Skåne som saknar chattsupport"
          aria-label="Vilka kunder behöver du, och till vilken produkt?"
          className="min-w-0 flex-1 rounded-input border border-ink/15 bg-paper px-3 py-2 text-[15px] focus-ring"
        />
        <button type="submit" disabled={busy || !fråga.trim()} className={cn(btnPrimary)}>
          {busy ? "Söker…" : "Sök Leads"}
        </button>
      </form>

      {busy ? (
        <p className="mt-3 text-[13px] text-ink/55">
          Söker bolag mot målgruppen — tar vanligen under en minut.
        </p>
      ) : null}

      {fel ? (
        <p role="alert" className="mt-4 break-words text-[14px] text-danger">
          {fel}
        </p>
      ) : null}

      {leads && leads.length === 0 ? (
        <p className="mt-4 text-[14px] text-mineral">
          Inga bolag med kontaktväg hittades på den raden. Prova en bredare beskrivning, eller kör
          en full körning i formuläret till vänster.
        </p>
      ) : null}

      {leads && leads.length > 0 ? (
        <ul className="mt-4 divide-y divide-ink/10">
          {leads.map((lead) => (
            <li key={lead.prospect_id} className="py-3">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <span className="text-[15px] font-medium">{lead.company_name}</span>
                {lead.ort ? <span className="text-[13px] text-ink/55">{lead.ort}</span> : null}
              </div>
              <p className="mt-1 text-[13px] leading-5 text-mineral">
                {lead.contact_name ? (
                  <>
                    {lead.contact_name}
                    {lead.contact_role ? ` — ${lead.contact_role}` : null}
                    {lead.contact_email ? ` · ${lead.contact_email}` : null}
                  </>
                ) : lead.contact_email ? (
                  lead.contact_email
                ) : lead.contact_form_url ? (
                  "Kontaktformulär på bolagets webbplats"
                ) : null}
              </p>
              <p className="mt-0.5 text-[12px] text-ink/45">
                {lead.contact_level ? (KONTAKTETIKETT[lead.contact_level] ?? lead.contact_level) : null}
                {lead.website ? (
                  <>
                    {lead.contact_level ? " · " : null}
                    <a
                      href={lead.website}
                      target="_blank"
                      rel="noreferrer"
                      className="underline decoration-ink/25 underline-offset-2 hover:decoration-ink/60"
                    >
                      {lead.website.replace(/^https?:\/\//, "")}
                    </a>
                  </>
                ) : null}
              </p>
            </li>
          ))}
        </ul>
      ) : null}

      {leads && utanKontakt > 0 ? (
        <p className="mt-3 text-[12px] text-ink/45">
          {utanKontakt} träff{utanKontakt === 1 ? "" : "ar"} utan kontaktväg listas inte här men
          finns i bolagsregistret för komplettering.
        </p>
      ) : null}
    </section>
  );
}
