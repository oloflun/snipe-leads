"use client";

import { useState } from "react";
import { btnPrimary, btnSecondary } from "@/components/ui";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Provkörning av båda agenterna, inifrån adminytan.
 *
 * ## Varför den finns
 *
 * Att veta att en agent SVARAR har hittills krävt antingen en riktig kund eller
 * ett curl-anrop med en API-nyckel. Det första går inte att göra på beställning,
 * det andra gör ingen under tidspress — så agenterna har i praktiken bara
 * testats när något redan gått fel.
 *
 * ## Varför körningarna märks
 *
 * Varje körning skriver en rad i `agent_runs`, och portföljvyn räknar dem.
 * En provkörning mot en kunds tenant hade därför fått kunden att se aktiv ut
 * för att VI testat. `is_test` (migration 036) skiljer dem åt; siffror som inte
 * går att lita på är värre än inga siffror, eftersom de fattar beslut åt en.
 *
 * ## Varför överskrivningarna inte är inställningar
 *
 * Fälten nedan gäller ENBART den startade körningen och rör aldrig arbetsytans
 * sparade ICP. Alternativet — ändra målgruppen, köra, ändra tillbaka — går fel
 * den gång man glömmer sista steget, och då bearbetas nästa riktiga körning fel
 * målgrupp utan att någon ser det.
 */

type Jobb = { job_id: string; prospect_id?: string };

type LeadsSvar = {
  jobs?: Jobb[];
  count?: number;
  scope?: string;
  is_test?: boolean;
  overrides?: Record<string, unknown> | null;
  error?: string;
  detail?: string;
};

const fältklass =
  "w-full rounded-input border border-ink/15 bg-paper px-3 py-2 text-[15px] focus-ring";

function Rad({ etikett, hint, children }: Readonly<{ etikett: string; hint?: string; children: React.ReactNode }>) {
  return (
    <label className="block">
      <span className="text-[13px] font-medium text-ink/70">{etikett}</span>
      {hint ? <span className="ml-2 text-[12px] text-ink/45">{hint}</span> : null}
      <div className="mt-1.5">{children}</div>
    </label>
  );
}

/** "Bygg, Tillverkning" → ["Bygg","Tillverkning"]. Tom sträng → undefined. */
function lista(värde: string): string[] | undefined {
  const delar = värde
    .split(",")
    .map((d) => d.trim())
    .filter(Boolean);
  return delar.length ? delar : undefined;
}

function tal(värde: string): number | undefined {
  const n = Number(värde.trim());
  return värde.trim() && Number.isFinite(n) ? n : undefined;
}

export function Testkorningar() {
  // --- Leads
  const [limit, setLimit] = useState("3");
  const [scope, setScope] = useState<"research" | "research_and_draft">("research");
  const [branscher, setBranscher] = useState("");
  const [undvik, setUndvik] = useState("");
  const [geografi, setGeografi] = useState("");
  // Roller, krävs och diskvalificerar ÄR nischen — bransch och geografi säger
  // bara var man letar. Utan dem gick en provkörning mot en särskild nisch inte
  // att styra: de tre kom alltid från arbetsytans sparade ICP.
  const [roller, setRoller] = useState("");
  const [kravs, setKravs] = useState("");
  const [diskvalificerar, setDiskvalificerar] = useState("");
  const [minAnst, setMinAnst] = useState("");
  const [maxAnst, setMaxAnst] = useState("");
  const [leadsSvar, setLeadsSvar] = useState<LeadsSvar | null>(null);
  const [leadsFel, setLeadsFel] = useState<string | null>(null);
  const [leadsBusy, setLeadsBusy] = useState(false);

  // --- Support
  const [fråga, setFråga] = useState("Vad kostar Snajp Duo och vad ingår?");
  const [supportSvar, setSupportSvar] = useState<string | null>(null);
  const [supportFel, setSupportFel] = useState<string | null>(null);
  const [supportBusy, setSupportBusy] = useState(false);

  async function körLeads() {
    setLeadsBusy(true);
    setLeadsFel(null);
    setLeadsSvar(null);
    try {
      // Tomma fält skickas INTE. null betyder "använd arbetsytans sparade ICP",
      // vilket inte är samma sak som "inga branscher alls".
      const overrides = {
        industries: lista(branscher),
        exclude_industries: lista(undvik),
        geography: lista(geografi),
        roles: lista(roller),
        must_have: lista(kravs),
        deal_breakers: lista(diskvalificerar),
        anstallda_min: tal(minAnst),
        anstallda_max: tal(maxAnst)
      };
      const harNågot = Object.values(overrides).some((v) => v !== undefined);

      const response = await fetch("/api/snajp-support/leads/runs/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          limit: Number(limit) || 1,
          scope,
          is_test: true,
          ...(harNågot ? { overrides } : {})
        })
      });
      const svar = (await readJsonBody<LeadsSvar>(response)) ?? {};
      if (!response.ok) {
        throw new Error(svar.detail ?? svar.error ?? `Körningen avvisades (${response.status}).`);
      }
      setLeadsSvar(svar);
    } catch (fel) {
      setLeadsFel(felmeddelande(fel));
    } finally {
      setLeadsBusy(false);
    }
  }

  async function körSupport() {
    setSupportBusy(true);
    setSupportFel(null);
    setSupportSvar(null);
    try {
      const start = await fetch("/api/snajp-support/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: fråga,
          channel: "web",
          customer_email: "admin-test@session.snajp.se",
          customer_name: "Admin testkörning",
          session_key: `admin-test-${Date.now()}`
        })
      });
      const startSvar = (await readJsonBody<{ job_id?: string; error?: string }>(start)) ?? {};
      if (!start.ok || !startSvar.job_id) {
        throw new Error(startSvar.error ?? `Kunde inte starta körningen (${start.status}).`);
      }

      // Kallstart på Renders gratisnivå tar upp till ~35 s, och agentens svar
      // ytterligare tid. 90 försök täcker det utan att hänga för evigt.
      for (let försök = 0; försök < 90; försök += 1) {
        await new Promise((r) => setTimeout(r, försök < 5 ? 800 : 2000));
        const jobb = await fetch(`/api/snajp-support/jobs/${startSvar.job_id}`);
        const j =
          (await readJsonBody<{ status?: string; result?: { reply?: string }; error?: string }>(
            jobb
          )) ?? {};
        if (j.status === "completed" && j.result?.reply) {
          setSupportSvar(j.result.reply);
          return;
        }
        if (j.status === "failed") {
          throw new Error(j.error ?? "Agentkörningen misslyckades.");
        }
      }
      throw new Error("Svaret tog för lång tid. Backenden kan ha somnat — försök igen.");
    } catch (fel) {
      setSupportFel(felmeddelande(fel));
    } finally {
      setSupportBusy(false);
    }
  }

  return (
    <div className="grid gap-12">
      <p className="max-w-[70ch] text-[15px] leading-7 text-mineral">
        Körningar startade härifrån märks <code className="font-mono text-[13px]">is_test</code> och
        räknas aldrig som kundvolym i Översikten. Inställningarna gäller bara den enskilda
        körningen — arbetsytans sparade målgrupp rörs inte.
      </p>

      {/* -------------------------------------------------- LEADS */}
      <section className="border-t border-ink/15 pt-8">
        <h2 className="font-display text-2xl tracking-[-0.02em]">Leads-agenten</h2>
        <p className="mt-2 max-w-[65ch] text-[15px] text-mineral">
          Kör research över befintliga prospekt. Lämna ett fält tomt för att använda arbetsytans
          sparade värde.
        </p>

        <div className="mt-6 grid max-w-[760px] gap-5 sm:grid-cols-2">
          <Rad etikett="Antal prospekt" hint="1–50">
            <input
              type="number"
              min={1}
              max={50}
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
              className={fältklass}
            />
          </Rad>
          <Rad etikett="Omfattning">
            <select
              value={scope}
              onChange={(e) => setScope(e.target.value as typeof scope)}
              className={fältklass}
            >
              <option value="research">Bara research</option>
              <option value="research_and_draft">Research och utkast</option>
            </select>
          </Rad>
          <Rad etikett="Branscher" hint="komma emellan">
            <input value={branscher} onChange={(e) => setBranscher(e.target.value)} placeholder="Bygg, Tillverkning" className={fältklass} />
          </Rad>
          <Rad etikett="Undvik branscher">
            <input value={undvik} onChange={(e) => setUndvik(e.target.value)} placeholder="Bemanning" className={fältklass} />
          </Rad>
          <Rad etikett="Geografi">
            <input value={geografi} onChange={(e) => setGeografi(e.target.value)} placeholder="Västra Götaland" className={fältklass} />
          </Rad>
          <Rad etikett="Beslutsfattarroller" hint="vem agenten ska leta efter">
            <input value={roller} onChange={(e) => setRoller(e.target.value)} placeholder="VD, inköpschef" className={fältklass} />
          </Rad>
          <Rad etikett="Signaler som krävs" hint="nischen">
            <input value={kravs} onChange={(e) => setKravs(e.target.value)} placeholder="Egen produktion, växer" className={fältklass} />
          </Rad>
          <Rad etikett="Diskvalificerar">
            <input value={diskvalificerar} onChange={(e) => setDiskvalificerar(e.target.value)} placeholder="Under 10 anställda" className={fältklass} />
          </Rad>
          <div className="grid grid-cols-2 gap-3">
            <Rad etikett="Anställda, min">
              <input type="number" min={0} value={minAnst} onChange={(e) => setMinAnst(e.target.value)} className={fältklass} />
            </Rad>
            <Rad etikett="max">
              <input type="number" min={0} value={maxAnst} onChange={(e) => setMaxAnst(e.target.value)} className={fältklass} />
            </Rad>
          </div>
        </div>

        <button type="button" onClick={() => void körLeads()} disabled={leadsBusy} className={cn(btnPrimary, "mt-6")}>
          {leadsBusy ? "Startar…" : "Starta testkörning"}
        </button>

        {leadsFel ? (
          <p role="alert" className="mt-5 max-w-[70ch] break-words text-[15px] text-danger">
            {leadsFel}
          </p>
        ) : null}

        {leadsSvar ? (
          <div className="mt-5 rounded-card bg-paper2/60 p-5">
            <p className="text-[15px]">
              {leadsSvar.count} jobb startade · omfattning{" "}
              <span className="font-mono text-[13px]">{leadsSvar.scope}</span>
              {leadsSvar.is_test ? " · märkt som testkörning" : null}
            </p>
            {leadsSvar.overrides ? (
              // Ekar tillbaka vad körningen FAKTISKT kördes med, inte vad
              // formuläret råkade innehålla när knappen trycktes.
              <pre className="thin-scrollbar mt-3 overflow-x-auto rounded-input bg-paper p-3 font-mono text-[12px] text-ink/70">
                {JSON.stringify(leadsSvar.overrides, null, 2)}
              </pre>
            ) : (
              <p className="mt-2 text-[13px] text-ink/55">Inga överskrivningar — arbetsytans ICP användes.</p>
            )}
          </div>
        ) : null}
      </section>

      {/* ------------------------------------------------ SUPPORT */}
      <section className="border-t border-ink/15 pt-8">
        <h2 className="font-display text-2xl tracking-[-0.02em]">Kundtjänstagenten</h2>
        <p className="mt-2 max-w-[65ch] text-[15px] text-mineral">
          Ställ en fråga och se det grundade svaret. Går agenten inte att grunda i kunskapsbasen ska
          den eskalera i stället för att gissa — det är också ett giltigt testresultat.
        </p>

        <div className="mt-6 max-w-[760px]">
          <Rad etikett="Fråga">
            <textarea
              value={fråga}
              onChange={(e) => setFråga(e.target.value)}
              rows={3}
              className={cn(fältklass, "resize-y")}
            />
          </Rad>
        </div>

        <button type="button" onClick={() => void körSupport()} disabled={supportBusy || !fråga.trim()} className={cn(btnSecondary, "mt-5")}>
          {supportBusy ? "Väntar på svar…" : "Ställ frågan"}
        </button>

        {supportBusy ? (
          <p className="mt-3 text-[13px] text-ink/55">
            Första svaret kan ta upp till en minut om backenden sovit.
          </p>
        ) : null}

        {supportFel ? (
          <p role="alert" className="mt-5 max-w-[70ch] break-words text-[15px] text-danger">
            {supportFel}
          </p>
        ) : null}

        {supportSvar ? (
          <div className="mt-5 max-w-[70ch] whitespace-pre-wrap rounded-card bg-paper2/60 p-5 text-[15px] leading-7">
            {supportSvar}
          </div>
        ) : null}
      </section>
    </div>
  );
}
