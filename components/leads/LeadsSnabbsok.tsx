"use client";

import { useState } from "react";
import { Badge, Rad, Radlista, btnPrimary, meta, rubrikPanel } from "@/components/ui";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";
import { useLocale, type Localized } from "@/lib/i18n";

/** Ett fel vars text vi själva skrivit, och därför har på båda språken. */
class LokalFel extends Error {
  constructor(readonly lokal: Localized) {
    super(lokal.sv);
  }
}

function felText(error: unknown): Localized {
  if (error instanceof LokalFel) return error.lokal;
  const m = felmeddelande(error);
  return { sv: m, en: m };
}

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

const KONTAKTETIKETT: Record<string, Localized> = {
  named_role_match: { sv: "Namngiven beslutsfattare", en: "Named decision-maker" },
  named_other: { sv: "Namngiven kontakt", en: "Named contact" },
  role_address: { sv: "Rolladress", en: "Role address" },
  contact_form: { sv: "Kontaktformulär", en: "Contact form" }
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
    if (j.status === "failed") {
      if (j.error) throw new Error(j.error);
      throw new LokalFel({ sv: "Sökningen misslyckades.", en: "The search failed." });
    }
  }
  throw new LokalFel({
    sv: "Sökningen tog för lång tid. Försök igen om en stund.",
    en: "The search took too long. Try again in a while."
  });
}

export function LeadsSnabbsok({ isTest = false }: { isTest?: boolean }) {
  const { text } = useLocale();
  const [fråga, setFråga] = useState("");
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<Localized | null>(null);
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
        if (detalj) throw new Error(detalj);
        throw new LokalFel({
          sv: `Kunde inte starta sökningen (${start.status}).`,
          en: `Could not start the search (${start.status}).`
        });
      }
      const resultat = await pollaJobb<SokResultat>(jobId);
      setLeads(resultat.prospects ?? []);
      setUtanKontakt(resultat.utan_kontakt ?? 0);
      // Bolagsregistret lyssnar redan på händelsen från LeadsRunForm — de nya
      // raderna finns där också, så registret ska uppdatera sig här med.
      window.dispatchEvent(new Event("snipra:leads-korning-klar"));
    } catch (e) {
      setFel(felText(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="leads-snabbsok" className="rounded-card bg-paper2/60 p-5">
      <h3 id="leads-snabbsok" className={rubrikPanel}>
        {text({ sv: "Sök bolag", en: "Search companies" })}
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
          placeholder={text({ sv: "T.ex. byggbolag i Skåne som saknar chattsupport", en: "E.g. construction firms in Skåne without chat support" })}
          aria-label={text({ sv: "Vilka kunder behöver du, och till vilken produkt?", en: "Which customers do you need, and for which product?" })}
          aria-describedby="leads-snabbsok-hjalp"
          // min-w-[180px] och inte min-w-0: med noll krymper fältet till en
          // springa bredvid knappen på 320px-skärmar. Med ett golv radbryts
          // knappen (flex-wrap på formen) och fältet förblir skrivbart.
          className="min-h-11 min-w-[180px] flex-1 rounded-input border border-ink/15 bg-paper px-3 py-2 text-base focus-ring"
        />
        <button type="submit" disabled={busy || !fråga.trim()} className={cn(btnPrimary)}>
          {busy ? text({ sv: "Söker…", en: "Searching…" }) : text({ sv: "Sök", en: "Search" })}
        </button>
      </form>
      <p id="leads-snabbsok-hjalp" className="mt-2 text-[0.9375rem] text-ink-muted">
        {text({
          sv: "Sökningen letar inom arbetsytans sparade målgrupp.",
          en: "The search looks within the workspace's saved target group."
        })}
      </p>

      {busy ? (
        <p role="status" className="mt-3 text-[0.9375rem] text-ink-muted">
          {text({
            sv: "Söker bolag mot målgruppen. Det tar vanligen under en minut.",
            en: "Searching for companies in the target group. It usually takes under a minute."
          })}
        </p>
      ) : null}

      {fel ? (
        <p role="alert" className="mt-4 break-words text-[15px] text-danger">
          {text(fel)}
        </p>
      ) : null}

      {/* Inte "formuläret till vänster": under xl ligger formuläret ovanför. */}
      {leads && leads.length === 0 ? (
        <p className="mt-4 text-[0.9375rem] text-ink-muted">
          {text({
            sv: "Inga bolag med kontaktväg hittades. Prova en bredare beskrivning, eller starta en full körning i formuläret.",
            en: "No companies with a way to contact them were found. Try a broader description, or start a full run in the form."
          })}
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
                  <Badge>{KONTAKTETIKETT[lead.contact_level] ? text(KONTAKTETIKETT[lead.contact_level]) : lead.contact_level}</Badge>
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
                  text({ sv: "Kontaktformulär på bolagets webbplats", en: "Contact form on the company website" })
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
          {text({
            sv: `${utanKontakt} träff${utanKontakt === 1 ? "" : "ar"} utan kontaktväg listas inte här, men finns i bolagsregistret för komplettering.`,
            en: `${utanKontakt} ${utanKontakt === 1 ? "hit without a contact route is" : "hits without a contact route are"} not listed here, but can be completed in the company register.`
          })}
        </p>
      ) : null}
    </section>
  );
}
