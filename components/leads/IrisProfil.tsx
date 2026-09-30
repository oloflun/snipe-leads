"use client";

import { useCallback, useEffect, useState } from "react";
import { Sektion, Tomt, btnLiten, btnSecondary, etikett, meta, rubrikPanel } from "@/components/ui";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

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
    throw new Error((kropp as { detail?: string } | null)?.detail ?? `Anropet avvisades (${response.status}).`);
  }
  return kropp;
}

/** Var kriteriet kommer ifrån: kundens filter (backendens "Kundens filter: …") eller en mening i kundens text. */
function kalla(kallmening: string): string {
  const filter = /^Kundens filter:\s*/i;
  return filter.test(kallmening)
    ? `Från era filter: ${kallmening.replace(filter, "").toLowerCase()}`
    : `Ur er text: ”${kallmening}”`;
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
  const [profil, setProfil] = useState<Profil | null>(null);
  const [jev, setJev] = useState<JevStatistik | null>(null);
  const [fel, setFel] = useState<string | null>(null);
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
      setFel(felmeddelande(error));
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
      setFel(felmeddelande(error));
    } finally {
      setTolkar(false);
    }
  }

  if (fel && !profil) {
    return <p role="alert" className="text-[0.9375rem] text-danger">{fel}</p>;
  }
  if (!profil) {
    return <div className="h-40 animate-pulse rounded-card bg-ink/[0.03]" />;
  }

  const lo = profil.anstallda_min;
  const hi = profil.anstallda_max;
  const saknas = [...(profil.otolkat ?? [])];

  return (
    <Sektion
      title="Iris-profil"
      action={
        <button type="button" onClick={() => void tolkaOm()} disabled={tolkar || demo} className={cn(btnSecondary, btnLiten)}>
          {tolkar ? "Tolkar…" : "Tolka om"}
        </button>
      }
    >
      {profil.kalla !== "ai" ? (
        <Tomt>
          Fritexten är inte tolkad än{profil.anmarkning ? ` (${profil.anmarkning})` : ""}. Iris använder bara de
          ifyllda filtren tills tolkningen lyckas.
        </Tomt>
      ) : null}

      <dl className="mt-4 grid gap-x-10 gap-y-4 sm:grid-cols-2">
        <Falt etikett="Ni säljer">{profil.erbjudande || "Inte angivet"}</Falt>
        <Falt etikett="Målgrupp">{profil.malgrupp || "Inte angiven"}</Falt>
        <Falt etikett="Branscher">
          {profil.branscher.length ? profil.branscher.join(", ") : "Alla branscher"}
          {profil.egen_bransch ? (
            <span className={cn(meta, "block")}>Er egen bransch ({profil.egen_bransch}) används inte som filter.</span>
          ) : null}
        </Falt>
        <Falt etikett="Område">
          {[...profil.kommuner, ...(profil.omraden ?? [])].join(", ") || "Hela Sverige"}
          {profil.geo_prioritet.length ? (
            <span className={cn(meta, "block")}>Börjar i {profil.geo_prioritet.map((r) => r.etikett).join(", sedan ")}</span>
          ) : null}
        </Falt>
        <Falt etikett="Storlek">
          {lo == null && hi == null
            ? "Alla storlekar"
            : lo != null && hi != null
              ? `${lo} till ${hi} anställda`
              : lo != null
                ? `Minst ${lo} anställda`
                : `Högst ${hi} anställda`}
        </Falt>
        <Falt etikett="Utan webbplats">{profil.utan_webbplats ? "Ingår i målgruppen" : "Nej"}</Falt>
      </dl>

      <h3 className={cn(rubrikPanel, "mt-8")}>Kriterier för varje bolag</h3>
      {profil.kriterier.length ? (
        <ul className="mt-3 divide-y divide-ink/10 border-y border-ink/10">
          {profil.kriterier.map((k) => (
            <li key={k.id} className="py-3">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <p className="text-[0.9375rem] font-medium">{k.text}</p>
                <span className={etikett}>{k.krav === "maste" ? "Måste" : "Bör"}</span>
              </div>
              {k.kallmening ? <p className={cn(meta, "mt-1 max-w-[65ch]")}>{kalla(k.kallmening)}</p> : null}
            </li>
          ))}
        </ul>
      ) : (
        <div className="mt-3">
          <Tomt>Inga kriterier ännu. Beskriv i Affärskontext vilka bolag som passar er bäst.</Tomt>
        </div>
      )}

      {profil.uteslut.length ? (
        <>
          <h3 className={cn(rubrikPanel, "mt-8")}>Utesluts</h3>
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
          <h3 className={rubrikPanel}>Kunde inte tolkas</h3>
          <ul className="mt-2 space-y-1 text-[0.9375rem] leading-6 text-ink-muted">
            {saknas.map((m) => (
              <li key={m}>”{m}”</li>
            ))}
          </ul>
        </div>
      ) : null}

      {jev && jev.lage !== "off" ? (
        <div className="mt-8 border-t border-ink/15 pt-6">
          <h3 className={rubrikPanel}>Jev, {jev.lage === "pa" ? "väljer bort" : "skuggläge"}</h3>
          <p className="mt-2 max-w-[65ch] text-[0.9375rem] leading-6 text-ink-muted">
            {jev.triagerade} bolag förbedömda, {jev.jev_skulle_falla} hade valts bort, {jev.falska_bortval} av
            dem kvalificerade ändå
            {jev.falska_bortval_andel != null ? ` (${Math.round(jev.falska_bortval_andel * 100)} %)` : ""}
            {jev.klassning_overens_med_niva != null
              ? `. Klassningen stämmer med Iris bedömning i ${Math.round(jev.klassning_overens_med_niva * 100)} % av fallen`
              : ""}
            .
          </p>
        </div>
      ) : null}

      <p className={cn(meta, "mt-8")}>Ändra målgruppen nedan eller Affärskontext, så tolkas profilen om inför nästa körning.</p>

      {fel ? (
        <p role="alert" className="mt-4 text-[0.9375rem] text-danger">
          {fel}
        </p>
      ) : null}
    </Sektion>
  );
}
