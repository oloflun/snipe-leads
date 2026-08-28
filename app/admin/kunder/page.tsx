import type { Metadata } from "next";
import Link from "next/link";
import { SlidersHorizontal } from "lucide-react";

import { FelOchEskaleringar } from "@/components/admin/FelOchEskaleringar";
import { OppnaArbetsyta } from "@/components/admin/OppnaArbetsyta";
import { Kundstatistik } from "@/components/admin/Kundstatistik";
import { beraknaKundstatistik } from "@/lib/admin/statistik";
import { listEvents, listTenants, unwrap } from "@/lib/data/admin";

export const dynamic = "force-dynamic";

export const metadata: Metadata = { title: "Snajp - Kunder&Data" };

/**
 * Backenden ligger på Renders gratisnivå och tar upp till ~35 s att vakna.
 * Utan detta dödar Vercel renderingen mitt i uppvakningen. Se app/admin/page.tsx.
 */
export const maxDuration = 60;

/**
 * Kundlistan — avsiktligt magrare än Översikten.
 *
 * Översikten (/admin) svarar på "hur går det": intäkt, kostnad, marginal och
 * vilka kunder som kräver en åtgärd. Den här sidan svarar på "vilka är de":
 * namn, volym, när de blev kund och om avtal finns. Två frågor som ställs vid
 * olika tillfällen, och en tabell som försöker svara på båda blir svår att
 * skumma.
 *
 * Inga uppskattningar här — bara räknade tal ur agent_runs och ss_tickets,
 * plus kundregistret (053). Marginalen bor i Översikten, med sitt förbehåll.
 *
 * Kundnamnet länkar till registeruppgifterna (kontaktpersoner, fakturering,
 * avtal); "Profil"-knappen till agentprofilen. Två vägar in som gör olika
 * saker — se kommentaren vid knapparna.
 */

function datum(värde: string | null): string {
  if (!värde) return "—";
  const d = new Date(värde);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString("sv-SE");
}

/** Händelsetaket. Fullt svar => talen i felsektionen prefixas "minst". */
const HANDELSETAK = 300;

export default async function Page() {
  // Parallellt: två oberoende backendanrop, och sidan är redan den
  // långsammaste i adminytan när backenden vaknar.
  const [tenantsSvar, eventsSvar] = await Promise.all([
    listTenants(),
    listEvents(`?limit=${HANDELSETAK}`)
  ]);
  const { data, error } = unwrap(tenantsSvar);
  const { data: events } = unwrap(eventsSvar);

  if (error) {
    return (
      <div>
        <h1 className="font-display text-4xl tracking-[-0.03em]">Kunder</h1>
        <p role="alert" className="mt-6 max-w-[70ch] break-words text-[15px] text-danger">
          {error}
        </p>
      </div>
    );
  }

  const kunder = [...(data ?? [])].sort((a, b) => a.name.localeCompare(b.name, "sv"));

  return (
    <div>
      <h1 className="font-display text-4xl tracking-[-0.03em]">Kunder &amp; Data</h1>
      <p className="mt-3 max-w-[70ch] text-[15px] leading-7 text-mineral">
        Alla registrerade kunder med volym, avtal och senaste aktivitet. Klicka på
        kundnamnet för kontaktpersoner och faktureringsuppgifter. Ekonomin och
        hälsobedömningen ligger under Översikt.
      </p>

      {kunder.length === 0 ? (
        <p className="mt-10 text-[15px] text-mineral">Inga kunder registrerade ännu.</p>
      ) : (
        <div className="mt-10 overflow-x-auto">
          <table className="w-full min-w-[900px] border-collapse text-[15px]">
            <thead>
              <tr className="border-b border-ink/15 text-left">
                <th className="py-3 pr-6 font-medium text-mineral">Kund</th>
                <th className="py-3 pr-6 font-medium text-mineral">Slug</th>
                <th className="py-3 pr-6 text-right font-medium text-mineral">Kund sedan</th>
                <th className="py-3 pr-6 text-right font-medium text-mineral">Avtal</th>
                <th className="py-3 pr-6 text-right font-medium text-mineral">Ärenden</th>
                <th className="py-3 pr-6 text-right font-medium text-mineral">Körningar</th>
                <th className="py-3 pr-6 text-right font-medium text-mineral">Fel</th>
                <th className="py-3 pr-6 text-right font-medium text-mineral">Senast aktiv</th>
                <th className="py-3 text-right font-medium text-mineral">
                  <span className="sr-only">Profil och arbetsyta</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {kunder.map((kund) => (
                <tr key={kund.id} className="border-b border-ink/8">
                  <td className="py-3 pr-6">
                    {/* Namnet är vägen till registeruppgifterna. Ochre bara på
                        hover — en hel kolumn i accentfärg är ingen accent. */}
                    <Link
                      href={`/admin/kunder/${kund.id}/data`}
                      className="focus-ring rounded-input underline decoration-ink/25 underline-offset-4 hover:text-ochre"
                    >
                      {kund.name}
                    </Link>
                  </td>
                  <td className="py-3 pr-6 font-mono text-[13px] text-ink/55">
                    {kund.slug ?? <span className="text-danger">saknas</span>}
                  </td>
                  <td className="py-3 pr-6 text-right tabular-nums text-ink/70">
                    {datum(kund.kund_sedan ?? null)}
                  </td>
                  {/* Ett datum ÄR avtalsstatusen: null betyder att inget avtal
                      är registrerat, och det sägs med ett ord i stället för
                      ett tomt hål som ser ut som saknad data. */}
                  <td className="py-3 pr-6 text-right tabular-nums text-ink/70">
                    {kund.avtal_signerat ? datum(kund.avtal_signerat) : <span className="text-ink/40">inget</span>}
                  </td>
                  <td className="py-3 pr-6 text-right tabular-nums">{kund.tickets}</td>
                  <td className="py-3 pr-6 text-right tabular-nums">{kund.runs}</td>
                  <td className="py-3 pr-6 text-right tabular-nums">
                    {kund.errors > 0 ? <span className="text-danger">{kund.errors}</span> : "0"}
                  </td>
                  <td className="py-3 pr-6 text-right tabular-nums text-ink/70">
                    {datum(kund.last_activity)}
                  </td>
                  {/* Två vägar in, och de gör olika saker: "Profil" ändrar hur
                      agenten beter sig, "Öppna" visar kundens vy som den ser ut
                      för kunden. Att bara ha den senare var vad som saknades —
                      det gick att TITTA på varje kund men inte att styra någon. */}
                  <td className="py-3 text-right">
                    <div className="inline-flex items-center gap-2">
                      <Link
                        href={`/admin/kunder/${kund.id}`}
                        aria-label={`Öppna agentprofilen för ${kund.name}`}
                        className="focus-ring inline-flex min-h-9 items-center gap-1.5 rounded-input bg-paper2 px-3 text-[13px] font-medium text-ink hover:bg-paper2/70"
                      >
                        <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden />
                        Profil
                      </Link>
                      {kund.slug ? <OppnaArbetsyta slug={kund.slug} namn={kund.name} /> : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Statistiken räknas på SAMMA rader som tabellen ovan, inte en egen
          hämtning — två uträkningar av samma tal blir förr eller senare två
          olika tal. `new Date()` är okej i en force-dynamic server component:
          sidan renderas per anrop. */}
      {kunder.length > 0 ? (
        <Kundstatistik stat={beraknaKundstatistik(kunder, new Date())} />
      ) : null}

      {/* Fel & eskaleringar: sammanfattar det som redan loggas. Renderas även
          när händelselistan inte gick att hämta — då med tom lista, eftersom
          eskaleringstalet kommer ur tenantraderna och står på egna ben. */}
      {kunder.length > 0 ? (
        <FelOchEskaleringar
          tenants={kunder}
          events={events ?? []}
          taketNaddes={(events?.length ?? 0) >= HANDELSETAK}
        />
      ) : null}

      {/* Intäkter och utgifter har MEDVETET ingen sektion här: det finns
          ingen riktig betal- eller bokföringskälla i systemet ännu
          (betalsätten är simulerade testkort, fakturor finns inte i kod).
          Uppskattad månadsintäkt och tokenkostnad — tydligt märkta som
          uppskattningar — ligger under Översikt. Bygg inte in siffror här
          förrän en riktig datakälla är vald. */}
      <p className="mt-14 max-w-[70ch] border-t border-ink/15 pt-5 text-[0.8125rem] leading-6 text-mineral">
        Intäkter och utgifter visas inte här ännu: det finns ingen riktig betal-
        eller bokföringskälla i systemet, och påhittade siffror är värre än inga.
        Uppskattad månadsintäkt och tokenkostnad finns under Översikt, märkta som
        uppskattningar.
      </p>
    </div>
  );
}
