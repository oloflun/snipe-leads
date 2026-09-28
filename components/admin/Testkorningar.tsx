"use client";

import { useState } from "react";
import { ExempelbolagDemo } from "@/components/leads/ExempelbolagDemo";
import { LeadsRunForm } from "@/components/leads/LeadsRunForm";
import { LeadsSnabbsok } from "@/components/leads/LeadsSnabbsok";
import { Sektion, btnSecondary, etikett } from "@/components/ui";
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
          // Fas 2.5 (snipe-vxq): löftet att admintester aldrig räknas som
          // kundvolym var tomt. Fältet fanns inte i ChatRequest förrän nu, så
          // de räknades.
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
      throw new Error("Svaret tog för lång tid. Backenden kan ha somnat. Försök igen.");
    } catch (fel) {
      setSupportFel(felmeddelande(fel));
    } finally {
      setSupportBusy(false);
    }
  }

  return (
    <div>
      {/* -------------------------------------------------- LEADS */}
      {/* Två kolumner på bred skärm: körningsformuläret till vänster (capat
          760px sedan tidigare), snabbsökpanelen och exempellistan staplade i
          högerkolumnen. Exempellistan visar hur ett färdigt resultat ser ut
          utan att någon behöver bränna en körning. På smalare skärmar (under
          xl) staplas allt i en kolumn under formuläret.

          Sektionsnamnen är produktens (railens Iris och Kundtjänst). Hjälp-
          texten är det enda formuläret kräver för att användas: vad ett tomt
          fält betyder och att inget sparas. `is_test`-märkningen syns inte;
          den förklaras i filens docstring och är ingenting man väljer. */}
      <Sektion title="Iris">
        <div className="grid grid-cols-1 gap-8 xl:grid-cols-2 xl:items-start">
          <LeadsRunForm
            isTest
            rubrik={
              <p className="max-w-[65ch] text-[0.9375rem] text-ink-muted">
                Tomma fält tar värdet från arbetsytans sparade målgrupp, och det du fyller i gäller
                bara den här körningen.
              </p>
            }
          />
          <div className="grid gap-8">
            <LeadsSnabbsok isTest />
            <ExempelbolagDemo />
          </div>
        </div>
      </Sektion>

      {/* ------------------------------------------------ SUPPORT */}
      {/* Ett svar som eskalerar i stället för att gissa är också ett giltigt
          testresultat: det betyder att kunskapsbasen saknade underlaget. */}
      <Sektion title="Kundtjänst">
        <div className="max-w-[760px]">
          <label className="block">
            <span className={etikett}>Fråga</span>
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
          <p role="status" className="mt-3 text-[0.9375rem] text-ink-muted">
            Första svaret kan ta upp till en minut om backenden sovit.
          </p>
        ) : null}

        {supportFel ? (
          <p role="alert" className="mt-5 max-w-[70ch] break-words text-[15px] text-danger">
            {supportFel}
          </p>
        ) : null}

        {/* paper2 alltid MED hårlinje (DESIGN.md): utan den är plattan nästan
            osynlig mot pappret. Samma yta som Tomt. */}
        {supportSvar ? (
          <div className="mt-5 max-w-[70ch] whitespace-pre-wrap rounded-input border border-ink/10 bg-paper2 p-5 text-[15px] leading-7">
            {supportSvar}
          </div>
        ) : null}
      </Sektion>
    </div>
  );
}
