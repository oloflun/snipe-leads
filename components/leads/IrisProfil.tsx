"use client";

import { useCallback, useEffect, useState } from "react";
import { Sektion, Tomt, btnLiten, btnSecondary, etikett, meta, rubrikPanel } from "@/components/ui";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";
import { useLocale, type Localized } from "@/lib/i18n";

/** Ett fel vars text vi själva skrivit, och därför har på båda språken. */
class AnropsFel extends Error {
  constructor(readonly lokal: Localized) {
    super(lokal.sv);
  }
}

function felText(error: unknown): Localized {
  if (error instanceof AnropsFel) return error.lokal;
  const m = felmeddelande(error);
  return { sv: m, en: m };
}

/**
 * Iris-profilen — hur Iris tolkat kundens affärskontext och filter.
 *
 * Profilen (snajp-support/app/leads/profil.py) är kundens egen
 * instruktionsfil: sökningen, förfiltret, kvalificeringen och utkasten läser
 * den. Den visas här med kundens EGNA meningar bredvid varje kriterium, så att
 * en feltolkning syns innan den kostar en körning (Alunix 2026-09-29: kundens
 * egen bransch lästes som målbransch). Rättelser görs i målgruppen nedan eller
 * i Affärskontext — strukturerat vinner alltid över tolkningen, och profilen
 * tolkas om automatiskt när underlaget ändras.
 */

type Profil = {
  kalla: "ai" | "regler";
  anmarkning?: string;
  egen_bransch: string | null;
  erbjudande: string;
  malgrupp: string;
  branscher: string[];
  undvik_branscher: string[];
  kommuner: string[];
  omraden?: string[];
  geo_prioritet: { etikett: string; postnr_prefix: string[] }[];
  anstallda_min: number | null;
  anstallda_max: number | null;
  utan_webbplats: boolean;
  kriterier: { id: string; text: string; krav: "maste" | "bor"; kallmening: string }[];
  uteslut: { text: string; kallmening: string }[];
  roller: string[];
  ej_tolkat: string[];
  otolkat?: string[];
};

type JevStatistik = {
  lage: string;
  triagerade: number;
  jev_skulle_falla: number;
  falska_bortval: number;
  falska_bortval_andel: number | null;
  klassade: number;
  klassning_overens_med_niva: number | null;
};

async function hamtaJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/snajp-support${path}`, { cache: "no-store", ...init });
  const kropp = await readJsonBody<T & { detail?: string }>(response);
  if (!response.ok || !kropp) {
    const detail = (kropp as { detail?: string } | null)?.detail;
    if (detail) throw new Error(detail);
    throw new AnropsFel({
      sv: `Anropet avvisades (${response.status}).`,
      en: `The request was rejected (${response.status}).`
    });
  }
  return kropp;
}

/** Var kriteriet kommer ifrån: kundens filter (backendens "Kundens filter: …") eller en mening i kundens text. */
function kalla(kallmening: string): Localized {
  const filter = /^Kundens filter:\s*/i;
  if (filter.test(kallmening)) {
    const rest = kallmening.replace(filter, "").toLowerCase();
    return { sv: `Från era filter: ${rest}`, en: `From your filters: ${rest}` };
  }
  return { sv: `Ur er text: ”${kallmening}”`, en: `From your text: “${kallmening}”` };
}

function Falt({ etikett: namn, children }: Readonly<{ etikett: string; children: React.ReactNode }>) {
  return (
    <div className="border-t border-ink/10 pt-3">
      <dt className={etikett}>{namn}</dt>
      <dd className="mt-1 text-[0.9375rem] leading-7 text-ink">{children}</dd>
    </div>
  );
}

export function IrisProfil({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { text } = useLocale();
  const [profil, setProfil] = useState<Profil | null>(null);
  const [jev, setJev] = useState<JevStatistik | null>(null);
  const [fel, setFel] = useState<Localized | null>(null);
  const [tolkar, setTolkar] = useState(false);

  const ladda = useCallback(async () => {
    setFel(null);
    if (demo) {
      setProfil((demoOversiktSvar("/leads/profil") as { profil: Profil }).profil);
      return;
    }
    try {
      const [p, j] = await Promise.all([
        hamtaJson<{ profil: Profil }>("/leads/profil"),
        hamtaJson<JevStatistik>("/leads/jev/statistik").catch(() => null)
      ]);
      setProfil(p.profil);
      setJev(j);
    } catch (error) {
      setFel(felText(error));
    }
  }, [demo]);

  useEffect(() => {
    void ladda();
  }, [ladda]);

  async function tolkaOm() {
    setTolkar(true);
    setFel(null);
    try {
      const p = await hamtaJson<{ profil: Profil }>("/leads/profil/tolka-om", { method: "POST" });
      setProfil(p.profil);
    } catch (error) {
      setFel(felText(error));
    } finally {
      setTolkar(false);
    }
  }

  if (fel && !profil) {
    return <p role="alert" className="text-[0.9375rem] text-danger">{text(fel)}</p>;
  }
  if (!profil) {
    return <div className="h-40 animate-pulse rounded-card bg-ink/[0.03]" />;
  }

  const lo = profil.anstallda_min;
  const hi = profil.anstallda_max;
  const saknas = [...(profil.otolkat ?? [])];

  return (
    <Sektion
      title={text({ sv: "Iris-profil", en: "Iris profile" })}
      action={
        <button type="button" onClick={() => void tolkaOm()} disabled={tolkar || demo} className={cn(btnSecondary, btnLiten)}>
          {tolkar ? text({ sv: "Tolkar…", en: "Interpreting…" }) : text({ sv: "Tolka om", en: "Reinterpret" })}
        </button>
      }
    >
      {profil.kalla !== "ai" ? (
        <Tomt>
          {text({ sv: "Fritexten är inte tolkad än", en: "The free text has not been interpreted yet" })}
          {profil.anmarkning ? ` (${profil.anmarkning})` : ""}.{" "}
          {text({
            sv: "Iris använder bara de ifyllda filtren tills tolkningen lyckas.",
            en: "Iris only uses the filled-in filters until the interpretation succeeds."
          })}
        </Tomt>
      ) : null}

      <dl className="mt-4 grid gap-x-10 gap-y-4 sm:grid-cols-2">
        <Falt etikett={text({ sv: "Ni säljer", en: "You sell" })}>{profil.erbjudande || text({ sv: "Inte angivet", en: "Not specified" })}</Falt>
        <Falt etikett={text({ sv: "Målgrupp", en: "Target group" })}>{profil.malgrupp || text({ sv: "Inte angiven", en: "Not specified" })}</Falt>
        <Falt etikett={text({ sv: "Branscher", en: "Industries" })}>
          {profil.branscher.length ? profil.branscher.join(", ") : text({ sv: "Alla branscher", en: "All industries" })}
          {profil.egen_bransch ? (
            <span className={cn(meta, "block")}>
              {text({
                sv: `Er egen bransch (${profil.egen_bransch}) används inte som filter.`,
                en: `Your own industry (${profil.egen_bransch}) is not used as a filter.`
              })}
            </span>
          ) : null}
        </Falt>
        <Falt etikett={text({ sv: "Område", en: "Area" })}>
          {[...profil.kommuner, ...(profil.omraden ?? [])].join(", ") || text({ sv: "Hela Sverige", en: "All of Sweden" })}
          {profil.geo_prioritet.length ? (
            <span className={cn(meta, "block")}>
              {text({ sv: "Börjar i", en: "Starts in" })}{" "}
              {profil.geo_prioritet.map((r) => r.etikett).join(text({ sv: ", sedan ", en: ", then " }))}
            </span>
          ) : null}
        </Falt>
        <Falt etikett={text({ sv: "Storlek", en: "Size" })}>
          {lo == null && hi == null
            ? text({ sv: "Alla storlekar", en: "All sizes" })
            : lo != null && hi != null
              ? text({ sv: `${lo} till ${hi} anställda`, en: `${lo} to ${hi} employees` })
              : lo != null
                ? text({ sv: `Minst ${lo} anställda`, en: `At least ${lo} employees` })
                : text({ sv: `Högst ${hi} anställda`, en: `At most ${hi} employees` })}
        </Falt>
        <Falt etikett={text({ sv: "Utan webbplats", en: "Without a website" })}>
          {profil.utan_webbplats ? text({ sv: "Ingår i målgruppen", en: "Part of the target group" }) : text({ sv: "Nej", en: "No" })}
        </Falt>
      </dl>

      <h3 className={cn(rubrikPanel, "mt-8")}>{text({ sv: "Kriterier för varje bolag", en: "Criteria for each company" })}</h3>
      {profil.kriterier.length ? (
        <ul className="mt-3 divide-y divide-ink/10 border-y border-ink/10">
          {profil.kriterier.map((k) => (
            <li key={k.id} className="py-3">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <p className="text-[0.9375rem] font-medium">{k.text}</p>
                <span className={etikett}>{k.krav === "maste" ? text({ sv: "Måste", en: "Must" }) : text({ sv: "Bör", en: "Should" })}</span>
              </div>
              {k.kallmening ? <p className={cn(meta, "mt-1 max-w-[65ch]")}>{text(kalla(k.kallmening))}</p> : null}
            </li>
          ))}
        </ul>
      ) : (
        <div className="mt-3">
          <Tomt>
            {text({
              sv: "Inga kriterier ännu. Beskriv i Affärskontext vilka bolag som passar er bäst.",
              en: "No criteria yet. Describe in Business context which companies suit you best."
            })}
          </Tomt>
        </div>
      )}

      {profil.uteslut.length ? (
        <>
          <h3 className={cn(rubrikPanel, "mt-8")}>{text({ sv: "Utesluts", en: "Excluded" })}</h3>
          <ul className="mt-3 space-y-1.5">
            {profil.uteslut.map((u) => (
              <li key={u.text} className="border-l-2 border-ink/15 pl-3 text-[0.9375rem] text-ink-muted">
                {u.text}
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {saknas.length ? (
        <div className="mt-8 border-l-2 border-ochre pl-3">
          <h3 className={rubrikPanel}>{text({ sv: "Kunde inte tolkas", en: "Could not be interpreted" })}</h3>
          <ul className="mt-2 space-y-1 text-[0.9375rem] leading-6 text-ink-muted">
            {saknas.map((m) => (
              <li key={m}>”{m}”</li>
            ))}
          </ul>
        </div>
      ) : null}

      {jev && jev.lage !== "off" ? (
        <div className="mt-8 border-t border-ink/15 pt-6">
          <h3 className={rubrikPanel}>
            Jev,{" "}
            {jev.lage === "pa" ? text({ sv: "väljer bort", en: "ruling out" }) : text({ sv: "skuggläge", en: "shadow mode" })}
          </h3>
          <p className="mt-2 max-w-[65ch] text-[0.9375rem] leading-6 text-ink-muted">
            {text({
              sv: `${jev.triagerade} bolag förbedömda, ${jev.jev_skulle_falla} hade valts bort, ${jev.falska_bortval} av dem kvalificerade ändå`,
              en: `${jev.triagerade} companies pre-screened, ${jev.jev_skulle_falla} would have been ruled out, ${jev.falska_bortval} of them qualified anyway`
            })}
            {jev.falska_bortval_andel != null ? ` (${Math.round(jev.falska_bortval_andel * 100)} %)` : ""}
            {jev.klassning_overens_med_niva != null
              ? text({
                  sv: `. Klassningen stämmer med Iris bedömning i ${Math.round(jev.klassning_overens_med_niva * 100)} % av fallen`,
                  en: `. The classification matches the Iris assessment in ${Math.round(jev.klassning_overens_med_niva * 100)} % of cases`
                })
              : ""}
            .
          </p>
        </div>
      ) : null}

      <p className={cn(meta, "mt-8")}>
        {text({
          sv: "Ändra målgruppen nedan eller Affärskontext, så tolkas profilen om inför nästa körning.",
          en: "Change the target group below or Business context, and the profile is reinterpreted before the next run."
        })}
      </p>

      {fel ? (
        <p role="alert" className="mt-4 text-[0.9375rem] text-danger">
          {text(fel)}
        </p>
      ) : null}
    </Sektion>
  );
}
