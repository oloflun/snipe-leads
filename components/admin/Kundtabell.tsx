"use client";

import Link from "next/link";
import { SlidersHorizontal } from "lucide-react";

import { OppnaArbetsyta } from "@/components/admin/OppnaArbetsyta";
import { Radmarke } from "@/components/admin/Radmarke";
import type { BerikadTenant } from "@/lib/admin/exempeldata";
import { a, antal, datum } from "@/lib/admin/sprak";
import { arTestyta } from "@/lib/admin/statistik";
import { useLocale } from "@/lib/i18n";

/**
 * Kundlistans tabell — avsiktligt magrare än Översikten.
 *
 * Översikten (/admin) svarar på "hur går det": intäkt, kostnad, marginal och
 * vilka kunder som kräver en åtgärd. Den här sidan svarar på "vilka är de":
 * namn, volym, när de blev kund och om avtal finns. Två frågor som ställs vid
 * olika tillfällen, och en tabell som försöker svara på båda blir svår att
 * skumma.
 *
 * Klientkomponent för språkväxlarens skull — se Portfoljvy för resonemanget.
 * Datan hämtas fortfarande i `app/admin/kunder/page.tsx`.
 *
 * Rader vars tal kommer ur `lib/admin/exempeldata.ts` bär märket "Exempel".
 * Fotnoten under tabellen räknar dem. En påhittad siffra utan ursprung är
 * precis vad sidans egen fotnot varnar för; en märkt är ett förbehåll.
 */

export function Kundtabell({ kunder }: Readonly<{ kunder: BerikadTenant[] }>) {
  const { locale, text } = useLocale();

  const sorterade = [...kunder].sort((x, y) =>
    x.name.localeCompare(y.name, locale === "sv" ? "sv" : "en")
  );
  const exempelrader = sorterade.filter((k) => k.ar_exempel).length;

  if (sorterade.length === 0) {
    return <p className="mt-10 text-[15px] text-mineral">{a("ingaRegistrerade", locale)}</p>;
  }

  return (
    <>
      <div className="mt-10 overflow-x-auto">
        <table className="w-full min-w-[900px] border-collapse text-[15px]">
          <thead>
            <tr className="border-b border-ink/15 text-left">
              <th className="py-3 pr-6 font-medium text-mineral">{a("kolKund", locale)}</th>
              <th className="py-3 pr-6 font-medium text-mineral">{a("kolSlug", locale)}</th>
              <th className="py-3 pr-6 text-right font-medium text-mineral">
                {a("kolKundSedan", locale)}
              </th>
              <th className="py-3 pr-6 text-right font-medium text-mineral">
                {a("kolAvtal", locale)}
              </th>
              <th className="py-3 pr-6 text-right font-medium text-mineral">
                {a("kolArenden", locale)}
              </th>
              <th className="py-3 pr-6 text-right font-medium text-mineral">
                {a("kolKorningar", locale)}
              </th>
              <th className="py-3 pr-6 text-right font-medium text-mineral">
                {a("kolFel", locale)}
              </th>
              <th className="py-3 pr-6 text-right font-medium text-mineral">
                {a("kolSenastAktiv", locale)}
              </th>
              <th className="py-3 text-right font-medium text-mineral">
                <span className="sr-only">{a("profilOchArbetsyta", locale)}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {sorterade.map((kund) => (
              <tr key={kund.id} className="border-b border-ink/8">
                <td className="py-3 pr-6">
                  {/* Namnet är vägen till registeruppgifterna. Ochre bara på
                      hover — en hel kolumn i accentfärg är ingen accent. */}
                  <span className="inline-flex items-baseline gap-2">
                    <Link
                      href={`/admin/kunder/${kund.id}/data`}
                      className="focus-ring rounded-input underline decoration-ink/25 underline-offset-4 hover:text-ochre"
                    >
                      {kund.name}
                    </Link>
                    {/* Testarbetsytan får ett neutralt märke i stället för att
                        se ut som en kund utan aktivitet: dess körningar bär
                        is_test och syns därför inte i kolumnen Körningar. */}
                    {arTestyta(kund.slug) ? (
                      <Radmarke>{text({ sv: "Testarbetsyta", en: "Test workspace" })}</Radmarke>
                    ) : null}
                    {kund.active === false ? (
                      <Radmarke>{text({ sv: "Inaktiv", en: "Inactive" })}</Radmarke>
                    ) : null}
                    {kund.ar_exempel ? (
                      <span
                        title={a("exempeldataMarkning", locale)}
                        className="shrink-0 rounded-[3px] border border-ink/20 px-1.5 py-px font-mono text-[10px] uppercase tracking-[0.14em] text-mineral"
                      >
                        {a("exempel", locale)}
                      </span>
                    ) : null}
                  </span>
                </td>
                <td className="py-3 pr-6 font-mono text-[13px] text-ink-subtle">
                  {kund.slug ?? <span className="text-danger">{a("saknas", locale)}</span>}
                </td>
                <td className="py-3 pr-6 text-right tabular-nums text-ink-muted">
                  {datum(kund.kund_sedan, locale)}
                </td>
                {/* Ett datum ÄR avtalsstatusen: null betyder att inget avtal
                    är registrerat, och det sägs med ett ord i stället för
                    ett tomt hål som ser ut som saknad data. */}
                <td className="py-3 pr-6 text-right tabular-nums text-ink-muted">
                  {kund.avtal_signerat ? (
                    datum(kund.avtal_signerat, locale)
                  ) : (
                    <span className="text-ink-subtle">{a("inget", locale)}</span>
                  )}
                </td>
                <td className="py-3 pr-6 text-right tabular-nums">{antal(kund.tickets, locale)}</td>
                <td className="py-3 pr-6 text-right tabular-nums">
                  {antal(kund.runs, locale)}
                  {/* Samma redovisning som Översikten: testkörningar räknas
                      inte som kundvolym men göms inte heller. */}
                  {kund.test_runs ? (
                    <span className="block text-[0.8125rem] text-ink-subtle">
                      +{kund.test_runs} {a("test", locale)}
                    </span>
                  ) : null}
                </td>
                <td className="py-3 pr-6 text-right tabular-nums">
                  {kund.errors > 0 ? <span className="text-danger">{kund.errors}</span> : "0"}
                </td>
                <td className="py-3 pr-6 text-right tabular-nums text-ink-muted">
                  {datum(kund.last_activity, locale)}
                </td>
                {/* Två vägar in, och de gör olika saker: "Profil" ändrar hur
                    agenten beter sig, "Öppna" visar kundens vy som den ser ut
                    för kunden. Att bara ha den senare var vad som saknades —
                    det gick att TITTA på varje kund men inte att styra någon. */}
                <td className="py-3 text-right">
                  <div className="inline-flex items-center gap-2">
                    {/* "Profil och tillägg", inte bara "Profil": tilläggen
                        (Leadslistor m.fl.) slås på på samma sida, och testaren
                        letade efter dem utan att ana att de låg bakom en
                        knapp som bara sa Profil. */}
                    <Link
                      href={`/admin/kunder/${kund.id}`}
                      aria-label={text({
                        sv: `Öppna agentprofil och tillägg för ${kund.name}`,
                        en: `Open agent profile and add-ons for ${kund.name}`
                      })}
                      className="focus-ring inline-flex min-h-9 items-center gap-1.5 whitespace-nowrap rounded-input bg-paper2 px-3 text-[13px] font-medium text-ink hover:bg-paper2/70"
                    >
                      <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden />
                      {text({ sv: "Profil och tillägg", en: "Profile and add-ons" })}
                    </Link>
                    {kund.slug ? <OppnaArbetsyta slug={kund.slug} namn={kund.name} /> : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {exempelrader > 0 ? (
        <p className="mt-4 max-w-[80ch] text-[0.8125rem] leading-6 text-mineral">
          <strong className="text-ink-muted">
            {text({
              sv: `${exempelrader} av ${sorterade.length} rader visar exempeldata`,
              en: `${exempelrader} of ${sorterade.length} rows show example data`
            })}
          </strong>{" "}
          {text({
            sv: "och är märkta med Exempel. Arbetsytorna finns, men har ingen egen aktivitet — talen är påhittade så att vyn går att bedöma, och de är härledda ur arbetsytans id, alltså desamma vid varje laddning. Stäng av dem med NEXT_PUBLIC_ADMIN_EXEMPELDATA=av.",
            en: "and carry an Example tag. Those workspaces exist but have no activity of their own — the figures are fabricated so the view can be evaluated, derived from the workspace id and therefore identical on every load. Turn them off with NEXT_PUBLIC_ADMIN_EXEMPELDATA=av."
          })}
        </p>
      ) : null}
    </>
  );
}
