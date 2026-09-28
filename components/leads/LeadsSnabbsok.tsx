"use client";

import { useState } from "react";
import { Badge, Rad, Radlista, btnPrimary, meta, rubrikPanel } from "@/components/ui";
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
  // ~5 min: den grundade sökningen tog 55–156 s i mätningen 2026-09-15 och
  // backendens tak är ~3,3 min (discovery._SOKNING_TIMEOUT). Formuläret ska
  // aldrig ge upp före backenden.
  for (let försök = 0; försök < 150; försök += 1) {
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
      <h3 id="leads-snabbsok" className={rubrikPanel}>
        Sök bolag
      </h3>

      {/* Ingen ingress under rubriken (F-016). Det enda fältet inte själv säger
          är att sökningen smalnar av den SPARADE målgruppen i stället för att
          leta brett, och det står som hjälptext under fältet, där det används.
          Att varje träff har en kontaktväg syns i raderna och i fotnoten. */}
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
          // Samma tak som backendens normalize_icp (MAX_CHARS_PER_ITEM=200):
          // utan det kapas en längre inklistring TYST på servern, och
          // sökningen svarar på en annan rad än den kunden ser i fältet.
          maxLength={200}
          placeholder="T.ex. byggbolag i Skåne som saknar chattsupport"
          aria-label="Vilka kunder behöver du, och till vilken produkt?"
          aria-describedby="leads-snabbsok-hjalp"
          // min-w-[180px] och inte min-w-0: med noll krymper fältet till en
          // springa bredvid knappen på 320px-skärmar. Med ett golv radbryts
          // knappen (flex-wrap på formen) och fältet förblir skrivbart.
          className="min-h-11 min-w-[180px] flex-1 rounded-input border border-ink/15 bg-paper px-3 py-2 text-base focus-ring"
        />
        <button type="submit" disabled={busy || !fråga.trim()} className={cn(btnPrimary)}>
          {busy ? "Söker…" : "Sök"}
        </button>
      </form>
      <p id="leads-snabbsok-hjalp" className="mt-2 text-[0.9375rem] text-ink-muted">
        Sökningen letar inom arbetsytans sparade målgrupp.
      </p>

      {busy ? (
        <p role="status" className="mt-3 text-[0.9375rem] text-ink-muted">
          Söker bolag mot målgruppen. Det tar vanligen under en minut.
        </p>
      ) : null}

      {fel ? (
        <p role="alert" className="mt-4 break-words text-[15px] text-danger">
          {fel}
        </p>
      ) : null}

      {/* Inte "formuläret till vänster": under xl ligger formuläret ovanför. */}
      {leads && leads.length === 0 ? (
        <p className="mt-4 text-[0.9375rem] text-ink-muted">
          Inga bolag med kontaktväg hittades. Prova en bredare beskrivning, eller starta en full
          körning i formuläret.
        </p>
      ) : null}

      {/* Radens anatomi som i resten av appen: bolaget med kontaktnivån som
          bricka till höger, kontakten under, ort och webbplats som meta. */}
      {leads && leads.length > 0 ? (
        <Radlista className="mt-4">
          {leads.map((lead) => (
            <Rad key={lead.prospect_id} className="min-w-0">
              <div className="flex min-w-0 flex-wrap items-start justify-between gap-x-3 gap-y-1">
                <p className="min-w-0 break-words text-[0.9375rem] font-medium">{lead.company_name}</p>
                {lead.contact_level ? (
                  <Badge>{KONTAKTETIKETT[lead.contact_level] ?? lead.contact_level}</Badge>
                ) : null}
              </div>
              <p className="mt-1 break-words text-[0.9375rem] text-ink-muted">
                {lead.contact_name ? (
                  <>
                    {lead.contact_name}
                    {lead.contact_role ? `, ${lead.contact_role}` : null}
                    {lead.contact_email ? ` · ${lead.contact_email}` : null}
                  </>
                ) : lead.contact_email ? (
                  lead.contact_email
                ) : lead.contact_form_url ? (
                  "Kontaktformulär på bolagets webbplats"
                ) : null}
              </p>
              {lead.ort || lead.website ? (
                <p className={cn(meta, "mt-1 break-words")}>
                  {lead.ort}
                  {lead.website ? (
                    <>
                      {lead.ort ? " · " : null}
                      <a
                        href={lead.website}
                        target="_blank"
                        rel="noreferrer"
                        className="focus-ring underline decoration-ink/25 underline-offset-2 hover:decoration-ink/60"
                      >
                        {lead.website.replace(/^https?:\/\//, "")}
                      </a>
                    </>
                  ) : null}
                </p>
              ) : null}
            </Rad>
          ))}
        </Radlista>
      ) : null}

      {leads && utanKontakt > 0 ? (
        <p className="mt-3 text-[0.9375rem] text-ink-muted">
          {utanKontakt} träff{utanKontakt === 1 ? "" : "ar"} utan kontaktväg listas inte här, men
          finns i bolagsregistret för komplettering.
        </p>
      ) : null}
    </section>
  );
}
