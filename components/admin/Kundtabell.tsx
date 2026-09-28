"use client";

import Link from "next/link";
import { SlidersHorizontal } from "lucide-react";

import { OppnaArbetsyta } from "@/components/admin/OppnaArbetsyta";
import { Radmarke } from "@/components/admin/Radmarke";
import { Cell, Tabell, Tomt, btnLiten, btnSecondary, meta, tabellRad } from "@/components/ui";
import type { BerikadTenant } from "@/lib/admin/exempeldata";
import { a, antal, datum } from "@/lib/admin/sprak";
import { arTestyta } from "@/lib/admin/statistik";
import { useLocale } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Kundlistans tabell — avsiktligt magrare än Översikten.
 *
 * Översikten (/admin) svarar på "hur går det": intäkt, kostnad, marginal och
 * vilka kunder som kräver en åtgärd. Den här sidan svarar på "vilka är de":
 * namn, volym, när de blev kund och om avtal finns. Två frågor som ställs vid
 * olika tillfällen, och en tabell som försöker svara på båda blir svår att
 * skumma.
 *
 * Sorterad på namn och inte på hälsa: det här är registret man slår upp en
 * kund i, och bläddringen på kunddatasidan går i samma ordning.
 *
 * Klientkomponent för språkväxlarens skull — se Portfoljvy för resonemanget.
 * Datan hämtas fortfarande i `app/admin/kunder/page.tsx`.
 *
 * Rader vars tal kommer ur `lib/admin/exempeldata.ts` bär märket "Exempel",
 * med förklaringen i märkets title. Fotnoten som räknade dem under tabellen
 * togs bort 2026-09-27 (F-016); märket på raden är det som identifierar dem.
 */

export function Kundtabell({ kunder }: Readonly<{ kunder: BerikadTenant[] }>) {
  const { locale, text } = useLocale();

  const sorterade = [...kunder].sort((x, y) =>
    x.name.localeCompare(y.name, locale === "sv" ? "sv" : "en")
  );

  if (sorterade.length === 0) {
    return (
      <div className="mt-8">
        <Tomt>{a("ingaRegistrerade", locale)}</Tomt>
      </div>
    );
  }

  return (
    <div className="mt-8">
      <Tabell
        minBredd={1000}
        kolumner={[
          { rubrik: a("kolKund", locale), bredd: "18%" },
          { rubrik: a("kolSlug", locale), bredd: "12%" },
          { rubrik: a("kolKundSedan", locale), bredd: "9%", hoger: true },
          { rubrik: a("kolAvtal", locale), bredd: "9%", hoger: true },
          { rubrik: a("kolArenden", locale), bredd: "7%", hoger: true },
          { rubrik: a("kolKorningar", locale), bredd: "8%", hoger: true },
          { rubrik: a("kolFel", locale), bredd: "5%", hoger: true },
          { rubrik: a("kolSenastAktiv", locale), bredd: "9%", hoger: true },
          { rubrik: a("profilOchArbetsyta", locale), bredd: "23%", hoger: true, srOnly: true }
        ]}
      >
        {sorterade.map((kund) => (
          <tr key={kund.id} className={tabellRad}>
            <Cell titel>
              {/* Namnet är vägen till registeruppgifterna. Ochre bara på
                  hover — en hel kolumn i accentfärg är ingen accent. */}
              <span className="flex min-w-0 flex-wrap items-baseline gap-2">
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
                  <Radmarke title={a("exempeldataMarkning", locale)}>{a("exempel", locale)}</Radmarke>
                ) : null}
              </span>
            </Cell>
            <Cell className="break-words font-mono text-[0.8125rem] text-ink-subtle">
              {kund.slug ?? <span className="font-sans text-danger">{a("saknas", locale)}</span>}
            </Cell>
            <Cell hoger className="text-ink-muted">
              {datum(kund.kund_sedan, locale)}
            </Cell>
            {/* Ett datum ÄR avtalsstatusen: null betyder att inget avtal
                är registrerat, och det sägs med ett ord i stället för
                ett tomt hål som ser ut som saknad data. */}
            <Cell hoger className="text-ink-muted">
              {kund.avtal_signerat ? (
                datum(kund.avtal_signerat, locale)
              ) : (
                <span className="text-ink-subtle">{a("inget", locale)}</span>
              )}
            </Cell>
            <Cell hoger>{antal(kund.tickets, locale)}</Cell>
            <Cell hoger>
              {antal(kund.runs, locale)}
              {/* Samma redovisning som Översikten: testkörningar räknas
                  inte som kundvolym men göms inte heller. */}
              {kund.test_runs ? (
                <span className={cn(meta, "block")}>
                  +{kund.test_runs} {a("test", locale)}
                </span>
              ) : null}
            </Cell>
            <Cell hoger>
              {kund.errors > 0 ? <span className="text-danger">{kund.errors}</span> : "0"}
            </Cell>
            <Cell hoger className="text-ink-muted">
              {datum(kund.last_activity, locale)}
            </Cell>
            {/* Två vägar in, och de gör olika saker: "Profil" ändrar hur
                agenten beter sig, "Öppna" visar kundens vy som den ser ut
                för kunden. Att bara ha den senare var vad som saknades —
                det gick att TITTA på varje kund men inte att styra någon. */}
            <Cell hoger>
              <div className="flex flex-wrap justify-end gap-2">
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
                  className={cn(btnSecondary, btnLiten, "whitespace-nowrap")}
                >
                  <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden />
                  {text({ sv: "Profil och tillägg", en: "Profile and add-ons" })}
                </Link>
                {kund.slug ? <OppnaArbetsyta slug={kund.slug} namn={kund.name} /> : null}
              </div>
            </Cell>
          </tr>
        ))}
      </Tabell>
    </div>
  );
}
