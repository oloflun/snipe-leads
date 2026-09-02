"use client";

import { useState } from "react";
import { ExempelbolagDemo } from "@/components/leads/ExempelbolagDemo";
import { LeadsRunForm } from "@/components/leads/LeadsRunForm";
import { LeadsSnabbsok } from "@/components/leads/LeadsSnabbsok";
import { btnSecondary } from "@/components/ui";
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
 * ## Varför leads-formuläret ligger i components/leads
 *
 * Kundens leads-flik körde discovery som fyra knappar utan `onClick`. Den
 * skulle ha samma formulär som det här — och två kopior av ett formulär med tio
 * fält glider isär: adminens fick roller och signaler i augusti, kundens hade
 * fortfarande inte fått dem. `LeadsRunForm` är därför delad, med `is_test` som
 * enda skillnad mellan ytorna.
 */

export function Testkorningar() {
  const [fråga, setFråga] = useState("Vad kostar Snajp Duo och vad ingår?");
  const [supportSvar, setSupportSvar] = useState<string | null>(null);
  const [supportFel, setSupportFel] = useState<string | null>(null);
  const [supportBusy, setSupportBusy] = useState(false);

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
          session_key: `admin-test-${Date.now()}`,
          // Fas 2.5 (snipe-vxq): löftet i beskrivningen nedanför var tomt —
          // fältet fanns inte i ChatRequest förrän nu, så admintester
          // räknades som kundvolym.
          is_test: true
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
      {/* Två kolumner på bred skärm: körningsformuläret till vänster (capat
          760px sedan tidigare), snabbsökpanelen och exempellistan staplade i
          högerkolumnen. Exempellistan visar hur ett färdigt resultat ser ut
          utan att någon behöver bränna en körning. På smalare skärmar (under
          xl) staplas allt i en kolumn under formuläret. */}
      <section className="border-t border-ink/15 pt-8">
        <div className="grid grid-cols-1 gap-8 xl:grid-cols-2 xl:items-start">
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
          <div className="grid gap-8">
            <LeadsSnabbsok isTest />
            <ExempelbolagDemo />
          </div>
        </div>
      </section>

      {/* ------------------------------------------------ SUPPORT */}
      <section className="border-t border-ink/15 pt-8">
        <h2 className="font-display text-2xl tracking-[-0.02em]">Kundtjänstagenten</h2>
        <p className="mt-2 max-w-[65ch] text-[15px] text-mineral">
          Ställ en fråga och se det grundade svaret. Går svaret inte att grunda i kunskapsbasen ska
          agenten eskalera i stället för att gissa — det är också ett giltigt testresultat.
        </p>

        <div className="mt-6 max-w-[760px]">
          <label className="block">
            <span className="text-[13px] font-medium text-ink/70">Fråga</span>
            <div className="mt-1.5">
              <textarea
                value={fråga}
                onChange={(e) => setFråga(e.target.value)}
                rows={3}
                className="w-full resize-y rounded-input border border-ink/15 bg-paper px-3 py-2 text-[15px] focus-ring"
              />
            </div>
          </label>
        </div>

        <button
          type="button"
          onClick={() => void körSupport()}
          disabled={supportBusy || !fråga.trim()}
          className={cn(btnSecondary, "mt-5")}
        >
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
