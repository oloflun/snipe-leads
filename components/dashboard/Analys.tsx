"use client";

import { AlertTriangle, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  Cell,
  Sektion,
  SkeletonRows,
  Tabell,
  Tomt,
  btnLiten,
  btnSecondary,
  etikett as etikettKlass,
  meta
} from "@/components/ui";
import { EjAktiverad, arEjAktiverad } from "@/components/EjAktiverad";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Analysvyn — veckovis utfall ur kundens EGEN tenant.
 *
 * ## Vad den ersatte
 *
 * Fram till nu renderade `/dashboard/analytics` konstanten `analyticsSeries`
 * ur `lib/mock-data.ts`: v16-v21, 188 skick, 21 svar, 6 möten. Samma sex
 * veckor för varje inloggad kund, utan en rad som sa att talen var påhittade.
 * Det är värre än en tom vy — en ifylld tabell blir trodd, och den här låg i
 * produkten bakom en inloggning kunder betalar för.
 *
 * ## Reglerna som gör den trovärdig
 *
 *  1. **En vecka utan trafik är en nolla.** Serien byggs ur kalendern i
 *     backenden, inte ur raderna, så en tyst vecka syns som en tyst vecka i
 *     stället för att försvinna ur kurvan.
 *  2. **Ett mätvärde utan källa är ett streck, inte en nolla.** `coverage`
 *     avgör vilket. Möten står som streck överallt eftersom ingenting skriver
 *     bokade möten till databasen (se ANALYTICS_COVERAGE i storage/base.py).
 *     Skillnaden mellan "noll möten" och "vi mäter inte möten" är hela
 *     skillnaden mellan ett svar och en gissning.
 *  3. **Ett trasigt anrop tömmer inte vyn — det säger att det är trasigt.**
 *     Backenden sover på fri nivå; en tabell som visar noll när tjänsten inte
 *     svarade hade varit ett mätfel presenterat som ett mätvärde.
 *
 * Tenanten härleds i `requireSnajpTenant()` ur sessionen. Ingenting i den här
 * filen väljer kund, och den ska aldrig göra det.
 */

type Vecka = {
  week: string;
  start: string | null;
  sent: number;
  replies: number;
  leads_runs: number;
  support_runs: number;
  tickets: number;
  escalated: number;
  resolved: number;
};

type Tackning = Record<string, boolean>;

type Svar = { weeks?: Vecka[]; coverage?: Tackning };

type Lage =
  | { fas: "laddar" }
  | { fas: "ejAktiverad" }
  | { fas: "fel"; meddelande: string }
  | { fas: "klar"; veckor: Vecka[]; tackning: Tackning };

const VECKOR = 8;

function procent(del: number, av: number): string | null {
  if (!av) return null;
  return new Intl.NumberFormat("sv-SE", {
    style: "percent",
    maximumFractionDigits: 0
  }).format(del / av);
}

export function Analys({ demo = false }: Readonly<{ demo?: boolean }>) {
  const [lage, setLage] = useState<Lage>({ fas: "laddar" });

  const hamta = useCallback(async () => {
    setLage({ fas: "laddar" });

    if (demo) {
      // Samma väg som översikten: demoläget svarar i webbläsaren och rör
      // varken session eller databas. Se app/demo/[[...slug]]/page.tsx.
      const svar = demoOversiktSvar(`/analytics/weekly?weeks=${VECKOR}`) as Svar | undefined;
      setLage({
        fas: "klar",
        veckor: svar?.weeks ?? [],
        tackning: svar?.coverage ?? {}
      });
      return;
    }

    try {
      const response = await fetch(`/api/snajp-support/analytics/weekly?weeks=${VECKOR}`, {
        cache: "no-store"
      });
      // response.ok FÖRE tolkningen: en sovande backend svarar med en
      // HTML-sida, och `.json()` på den ger kunden webbläsarens råa felmeddelande.
      if (response.status === 409) {
        // Kroppen måste läsas ÄVEN vid felstatus här: koden bor i den, och
        // 409 betyder två olika saker (se arEjAktiverad).
        const kropp = await readJsonBody<unknown>(response).catch(() => null);
        if (arEjAktiverad(response.status, kropp)) {
          setLage({ fas: "ejAktiverad" });
          return;
        }
      }
      if (!response.ok) {
        setLage({
          fas: "fel",
          meddelande:
            response.status >= 500
              ? "Tjänsten svarar inte just nu. Den vaknar ur viloläge och kan ta upp till en minut."
              : `Kunde inte hämta statistiken (status ${response.status}).`
        });
        return;
      }
      const kropp = await readJsonBody<Svar & { offline?: boolean }>(response);
      if (!kropp || kropp.offline) {
        setLage({ fas: "fel", meddelande: "Backenden svarade utan innehåll." });
        return;
      }
      setLage({
        fas: "klar",
        veckor: kropp.weeks ?? [],
        tackning: kropp.coverage ?? {}
      });
    } catch (error) {
      setLage({
        fas: "fel",
        meddelande: error instanceof Error ? error.message : "Kunde inte nå servern."
      });
    }
  }, [demo]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  if (lage.fas === "laddar") {
    return <SkeletonRows />;
  }

  if (lage.fas === "ejAktiverad") {
    return <EjAktiverad yta="Analys" />;
  }

  if (lage.fas === "fel") {
    return (
      <div className="flex items-start gap-3 border-y border-ochre/40 bg-ochre/10 px-4 py-4">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden />
        <div className="min-w-0">
          <p className="text-[0.9375rem] font-medium text-ink">Statistiken kunde inte hämtas</p>
          <p className="mt-1 text-[0.9375rem] text-ink-muted">{lage.meddelande}</p>
          <button
            type="button"
            onClick={() => void hamta()}
            className={cn(btnSecondary, btnLiten, "mt-3")}
          >
            Försök igen
          </button>
        </div>
      </div>
    );
  }

  const { veckor, tackning } = lage;

  // Ingen rad alls betyder att arbetsytan aldrig kört något — inte att den
  // presterat noll. De två ser likadana ut i en tabell och ska därför inte
  // renderas som samma sak.
  const harTrafik = veckor.some(
    (v) => v.sent || v.replies || v.leads_runs || v.support_runs || v.tickets
  );

  // "Tomt betyder tomt, inga siffror räknas fram i förväg" stod efter
  // meningen här. Den försvarade sidans egna val i stället för att säga
  // något om kundens data (F-018) och togs bort 2026-09-27.
  if (!veckor.length || !harTrafik) {
    return (
      <Tomt>
        Ingen data ännu. Här visas skick, svarsfrekvens och ärenden per vecka så fort agenterna har
        kört mot din arbetsyta.
      </Tomt>
    );
  }

  return (
    <div>
      <AgentBlock
        rubrik="Iris"
        veckor={veckor}
        kolumner={[
          { nyckel: "sent", etikett: "Skick", tacks: tackning.sent },
          { nyckel: "replies", etikett: "Svar", tacks: tackning.replies },
          {
            nyckel: "svarsfrekvens",
            etikett: "Svarsfrekvens",
            tacks: tackning.sent && tackning.replies,
            varde: (v) => procent(v.replies, v.sent)
          },
          { nyckel: "meetings", etikett: "Möten", tacks: tackning.meetings },
          { nyckel: "leads_runs", etikett: "Körningar", tacks: tackning.leads_runs }
        ]}
        kurva={(v) => v.sent}
        kurvetikett="Skick per vecka"
      />

      <AgentBlock
        rubrik="Kundtjänst"
        veckor={veckor}
        kolumner={[
          { nyckel: "tickets", etikett: "Ärenden", tacks: tackning.tickets },
          { nyckel: "resolved", etikett: "Avslutade", tacks: tackning.resolved },
          { nyckel: "escalated", etikett: "Eskalerade", tacks: tackning.escalated },
          { nyckel: "support_runs", etikett: "Körningar", tacks: tackning.support_runs }
        ]}
        kurva={(v) => v.tickets}
        kurvetikett="Ärenden per vecka"
      />

      <OtackadeFotnot tackning={tackning} />
    </div>
  );
}

// -- Byggstenar ------------------------------------------------------------

type Kolumn = {
  nyckel: string;
  etikett: string;
  tacks?: boolean;
  varde?: (v: Vecka) => string | null;
};

/**
 * Ett block per agent: `Sektion` med rubrik, trendkurva och veckotabell.
 *
 * Underrubrikerna ("Utskick och svar per vecka.") togs bort 2026-09-27: de
 * beskrev tabellen som stod direkt under, och kolumnhuvudena säger detsamma.
 */
function AgentBlock({
  rubrik,
  veckor,
  kolumner,
  kurva,
  kurvetikett
}: Readonly<{
  rubrik: string;
  veckor: Vecka[];
  kolumner: Kolumn[];
  kurva: (v: Vecka) => number;
  kurvetikett: string;
}>) {
  // Ett block där INGEN kolumn har en källa blir annars en tabell av streck —
  // sex rader gånger fyra kolumner som alla säger samma sak. En rad som säger
  // det en gång är samma information och ser inte trasig ut.
  const nagotMats = kolumner.some((k) => k.tacks);

  return (
    <Sektion title={rubrik}>
      {!nagotMats ? (
        <Tomt>Ingenting mäts för {rubrik.toLowerCase()} ännu.</Tomt>
      ) : (
        <>
          <Trend veckor={veckor} varde={kurva} etikett={kurvetikett} />

          {/* `Tabell` ur components/ui.tsx: fast layout, etikett-huvuden, och
              intern scroll under minbredden i stället för en egen kortlayout
              på mobil (plans/2026-09-27-appytor-enhetlighet.md, regel 3:
              aldrig kort-i-lista, aldrig en rå <table>). Veckokolumnen har en
              deklarerad bredd och talkolumnerna delar resten lika, så
              siffrorna står i samma spalt oavsett antal kolumner. */}
          <div className="mt-6">
            <Tabell
              ariaLabel={`${rubrik} per vecka`}
              minBredd={560}
              kolumner={[
                { rubrik: "Vecka", bredd: "16%" },
                ...kolumner.map((k) => ({
                  rubrik: k.etikett,
                  bredd: `${84 / kolumner.length}%`,
                  hoger: true
                }))
              ]}
            >
              {veckor.map((v) => (
                <tr key={v.week}>
                  <Cell titel className="font-medium text-ink">
                    {v.week}
                  </Cell>
                  {kolumner.map((k) => (
                    <Cell key={k.nyckel} hoger className="text-ink-muted">
                      <Varde kolumn={k} vecka={v} />
                    </Cell>
                  ))}
                </tr>
              ))}
            </Tabell>
          </div>
        </>
      )}
    </Sektion>
  );
}

/**
 * Ett mätvärde utan källa blir ett tankstreck (aldrig em-streck) med en titel
 * som säger varför. Hette `Cell` före 2026-09-27; bytte namn för att inte
 * skugga `Cell` ur components/ui.tsx.
 */
function Varde({ kolumn, vecka }: Readonly<{ kolumn: Kolumn; vecka: Vecka }>) {
  if (!kolumn.tacks) {
    return (
      <span className="text-ink-subtle" title="Mäts inte ännu.">
        –
      </span>
    );
  }
  if (kolumn.varde) {
    return <>{kolumn.varde(vecka) ?? <span className="text-ink-subtle">–</span>}</>;
  }
  return <>{(vecka as unknown as Record<string, number>)[kolumn.nyckel] ?? 0}</>;
}

/**
 * Trendkurvan. Ren SVG, ingen chart-modul: sex till åtta punkter motiverar
 * inte ett bibliotek i klientbundeln, och en `<title>` gör den läsbar för
 * skärmläsare vilket en canvas inte hade varit.
 */
function Trend({
  veckor,
  varde,
  etikett
}: Readonly<{ veckor: Vecka[]; varde: (v: Vecka) => number; etikett: string }>) {
  const tal = veckor.map(varde);
  const tak = Math.max(...tal, 1);

  return (
    <div className="border-y border-ink/15 py-4">
      <p className={cn(etikettKlass, "mb-3")}>{etikett}</p>
      {/* `items-stretch` (default) och INTE `items-end`: kolumnerna måste ärva
          den bestämda höjden från h-24. Med items-end blev varje kolumn så hög
          som sitt innehåll, spåret under fick ingen bestämd höjd, och
          stapelns `height: X%` löste ut till NOLL. Diagrammet ritade då bara
          veckoetiketterna — synligt i en skärmbild, osynligt för ett test som
          bara räknar rader.

          Stapeln är absolut positionerad mot ett `relative` spår i stället för
          att vara en flexbox-unge med procenthöjd, eftersom det är den enda
          varianten där procenten alltid har något bestämt att räkna på. */}
      <div className="flex h-32 gap-1.5" role="img" aria-label={etikett}>
        {veckor.map((v, i) => {
          const höjd = Math.round((tal[i] / tak) * 100);
          return (
            <div key={v.week} className="flex min-w-0 flex-1 flex-col gap-1.5">
              <div className="relative min-h-0 flex-1">
                <div
                  className={cn(
                    // Bredden är kapad och stapeln centrerad. Full bredd gav
                    // sex block à ~300px på en desktopskärm, och då läser
                    // skillnaden mellan 188 och 318 som ingen skillnad alls —
                    // formen försvinner i ytan. Talen står exakt i tabellen
                    // under; diagrammets uppgift är kurvan, inte precisionen.
                    "absolute bottom-0 left-1/2 w-full max-w-[64px] -translate-x-1/2 rounded-t-sm",
                    tal[i] ? "bg-ochre" : "bg-ink/10"
                  )}
                  // Noll ska synas som en synlig grundlinje och inte som
                  // ingenting — annars går en tyst vecka inte att skilja från
                  // en vecka som saknas.
                  style={{ height: `${Math.max(höjd, 2)}%` }}
                />
              </div>
              <span className={cn(meta, "num truncate text-center")}>{v.week}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function OtackadeFotnot({ tackning }: Readonly<{ tackning: Tackning }>) {
  const saknas = Object.entries(tackning)
    .filter(([, tacks]) => !tacks)
    .map(([nyckel]) => nyckel);

  if (!saknas.length) {
    return null;
  }

  const etiketter: Record<string, string> = {
    meetings: "möten",
    sent: "skick",
    replies: "svar",
    tickets: "ärenden",
    escalated: "eskalerade",
    resolved: "avslutade",
    leads_runs: "leads-körningar",
    support_runs: "kundtjänstkörningar"
  };

  // En mening i brödtextstorlek. Stod tidigare som tre meningar i 14 px som
  // förklarade skillnaden mellan noll och streck; det läsaren behöver är
  // vilka värden som inte mäts.
  const namn = saknas.map((n) => etiketter[n] ?? n);
  const lista =
    namn.length > 1 ? `${namn.slice(0, -1).join(", ")} och ${namn[namn.length - 1]}` : namn[0];

  return (
    <p className="mt-6 text-[0.9375rem] text-ink-muted">
      {lista.charAt(0).toUpperCase() + lista.slice(1)} mäts inte ännu och står därför som streck,
      inte som noll.
    </p>
  );
}
