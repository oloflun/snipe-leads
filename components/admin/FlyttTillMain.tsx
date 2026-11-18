"use client";

import { useEffect, useState } from "react";
import { btnPrimary } from "@/components/ui";
import { flyttaTillMain, hamtaFlyttbart, type FlyttKandidater, type FlyttStatus } from "@/lib/actions/flytt";
import { useLocale, type Localized } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Flytta till main — panelen i Byt kund (plan del E).
 *
 * Renderas BARA i development (en spegel) och bara för plattformsadmin: det
 * är den enda vägen från testmiljön till produktionen, och den ska synas som
 * exakt det. Synken går bara main → development (INV-DATA-008): det som skapas
 * här når aldrig main av sig självt. Varje flytt får ett kvitto per rad ur
 * mottagarens svar.
 */

const T = {
  rubrik: { sv: "Flytta till main", en: "Move to main" },
  forklaring: {
    sv: "Synken kopierar mains rader hit löpande, och mains version vinner när samma rad ändrats på båda håll. Det som skapats här stannar men når aldrig main av sig självt: flytta det som ska finnas i den riktiga miljön.",
    en: "The sync copies rows from main here continuously, and main's version wins when the same row changed in both. What you create here stays but never reaches main by itself: move what should exist in the live environment."
  },
  speglingSkapad: { sv: "Spegeln skapad", en: "Mirror created" },
  mejl: { sv: "Supportmejl", en: "Support email" },
  korningar: { sv: "Leadskörningar", en: "Lead runs" },
  korningarForklaring: {
    sv: "Prospekt och väntande utkast följer med körningen.",
    en: "Prospects and pending drafts move with the run."
  },
  listor: { sv: "Leadslistor", en: "Lead lists" },
  listorForklaring: {
    sv: "Flyttade listor blir skarpa i main, också de som skapades i testläge.",
    en: "Moved lists become live in main, including those created in test mode."
  },
  rader: { sv: "rader", en: "rows" },
  inga: { sv: "Inget att flytta.", en: "Nothing to move." },
  flyttar: { sv: "Flyttar…", en: "Moving…" },
  flyttade: { sv: "Flyttade", en: "Moved" },
  hamtar: { sv: "Hämtar…", en: "Loading…" },
  ejKonfigurerad: {
    sv: "Flyttvägen är inte konfigurerad (FLYTT_MAL_URL och FLYTT_NYCKEL saknas i miljön).",
    en: "The move path is not configured (FLYTT_MAL_URL and FLYTT_NYCKEL are missing in the environment)."
  },
  importerad: { sv: "flyttad", en: "moved" },
  redan: { sv: "redan flyttad", en: "already moved" },
  kompletterad: { sv: "kompletterad (det som saknades följde med)", en: "backfilled (missing parts moved)" },
  fel: { sv: "fel", en: "error" },
  test: { sv: "test", en: "test" },
  synk: { sv: "Synken från main", en: "Sync from main" },
  senastForsok: { sv: "Senaste försök", en: "Last attempt" },
  aldrigLyckad: { sv: "Ingen lyckad synk registrerad.", en: "No successful sync recorded." },
  lyckad: { sv: "lyckad", en: "succeeded" },
  avbruten: { sv: "avbruten", en: "aborted" }
} satisfies Record<string, Localized>;

/** Antal ändrade rader i senaste synken (tabell → åtgärd → antal). */
function summaAntal(antal: Record<string, Record<string, number>> | null | undefined): number {
  if (!antal) return 0;
  return Object.values(antal).reduce(
    (summa, perAtgard) => summa + Object.values(perAtgard ?? {}).reduce((s, n) => s + (Number(n) || 0), 0),
    0
  );
}

const RESULTAT: Record<string, Localized> = {
  importerad: T.importerad,
  redan_flyttad: T.redan,
  kompletterad: T.kompletterad,
  fel: T.fel
};

export function FlyttTillMain({ slug }: Readonly<{ slug: string }>) {
  const { locale, text } = useLocale();
  const [lage, setLage] = useState<{ status: FlyttStatus; kandidater: FlyttKandidater } | null | "laddar">("laddar");
  const [fel, setFel] = useState<string | null>(null);
  const [valdaMejl, setValdaMejl] = useState<Set<string>>(new Set());
  const [valdaKorningar, setValdaKorningar] = useState<Set<string>>(new Set());
  const [valdaListor, setValdaListor] = useState<Set<string>>(new Set());
  const [flyttar, setFlyttar] = useState(false);
  const [kvitto, setKvitto] = useState<{ ref_id: string; resultat: string; fel?: string }[] | null>(null);

  useEffect(() => {
    let avbruten = false;
    void (async () => {
      const svar = await hamtaFlyttbart(slug);
      if (avbruten) return;
      if (svar && "error" in svar) {
        setFel(svar.error);
        setLage(null);
        return;
      }
      setLage(svar);
    })();
    return () => {
      avbruten = true;
    };
  }, [slug, kvitto]);

  if (lage === "laddar") return <p className="mt-3 px-1 text-[13px] text-ink-subtle">{text(T.hamtar)}</p>;
  if (fel) {
    return (
      <p role="alert" className="mt-3 px-1 text-[13px] text-danger">
        {fel}
      </p>
    );
  }
  if (!lage) return null;

  const { status, kandidater } = lage;
  const nar = (iso: string | null) =>
    iso ? new Date(iso).toLocaleString(locale === "en" ? "en-GB" : "sv-SE", { dateStyle: "short", timeStyle: "short" }) : "–";
  const vaxla = (set: Set<string>, setter: (s: Set<string>) => void, id: string) => {
    const nasta = new Set(set);
    if (nasta.has(id)) nasta.delete(id);
    else nasta.add(id);
    setter(nasta);
  };

  async function flytta(typ: "mejl" | "korning" | "lista", ids: string[]) {
    setFlyttar(true);
    setFel(null);
    const svar = await flyttaTillMain(slug, typ, ids);
    setFlyttar(false);
    if (svar.error) {
      setFel(svar.error);
      return;
    }
    setKvitto(svar.rader ?? []);
    setValdaMejl(new Set());
    setValdaKorningar(new Set());
    setValdaListor(new Set());
  }

  const listor = kandidater.listor ?? [];

  const konfigurerad = status.mal_konfigurerat && status.nyckel_konfigurerad;

  // Synkens insyn (runbookens steg 11). Visas när synken skrivit något i
  // spegeln; en äldre spegel utan synkkolumner visar bara raden ovan.
  const spegel = status.spegel;
  const synkVisas = Boolean(spegel && ("synkad_at" in spegel || "senaste_forsok_at" in spegel));
  const alder = status.synk_alder_min ?? null;
  const forsenad = Boolean(status.synk_forsenad);
  const sedan = (min: number) => {
    if (min < 120) return text({ sv: `${min} min sedan`, en: `${min} min ago` });
    if (min < 2880) {
      const timmar = Math.floor(min / 60);
      return text({ sv: `${timmar} timmar sedan`, en: `${timmar} hours ago` });
    }
    const dagar = Math.floor(min / 1440);
    return text({ sv: `${dagar} dagar sedan`, en: `${dagar} days ago` });
  };
  const utfall = spegel?.senaste_utfall ?? null;
  const hoppade = utfall ? /^hoppade:(\d+)$/.exec(utfall) : null;
  const utfallOk = utfall === "ok" || (hoppade !== null && Number(hoppade[1]) === 0);
  const utfallText = (() => {
    if (!utfall) return "–";
    if (utfall === "ok") return text(T.lyckad);
    if (hoppade) return text({ sv: `${hoppade[1]} rader hoppades över`, en: `${hoppade[1]} rows skipped` });
    if (utfall.startsWith("avbruten:")) return `${text(T.avbruten)}: ${utfall.slice("avbruten:".length).trim()}`;
    if (utfall.startsWith("fel:")) return `${text(T.fel)}: ${utfall.slice("fel:".length).trim()}`;
    return utfall;
  })();
  const andrade = summaAntal(spegel?.senaste_antal);

  return (
    <div className="mt-3 border-t border-ink/10 pt-3">
      <p className="px-1 text-[13px] font-semibold">{text(T.rubrik)}</p>
      <p className="mt-1 px-1 text-[12px] leading-5 text-ink-subtle">{text(T.forklaring)}</p>
      {status.spegel?.seeded_at ? (
        <p className="mt-1 px-1 text-[12px] text-ink-muted">
          {text(T.speglingSkapad)} {nar(status.spegel.seeded_at)}.
        </p>
      ) : null}
      {synkVisas ? (
        <div className="mt-2 px-1 text-[12px] leading-5">
          <p className="font-medium text-ink-muted">{text(T.synk)}</p>
          {forsenad && alder !== null ? (
            <p role="alert" className="font-medium text-danger">
              {text({
                sv: `Försenad: senaste lyckade synk för ${sedan(alder)}.`,
                en: `Delayed: last successful sync ${sedan(alder)}.`
              })}
            </p>
          ) : (
            <p className="text-ink-muted">
              {alder !== null
                ? text({ sv: `Senast lyckad för ${sedan(alder)}.`, en: `Last successful ${sedan(alder)}.` })
                : text(T.aldrigLyckad)}
            </p>
          )}
          {spegel?.senaste_forsok_at || utfall ? (
            <p className={utfallOk ? "text-ink-subtle" : "text-warning"}>
              {text(T.senastForsok)} {nar(spegel?.senaste_forsok_at ?? null)}: {utfallText}
              {andrade > 0 ? text({ sv: ` (${andrade} rader ändrade)`, en: ` (${andrade} rows changed)` }) : ""}
            </p>
          ) : null}
        </div>
      ) : null}
      {!konfigurerad ? <p className="mt-2 px-1 text-[12px] text-danger">{text(T.ejKonfigurerad)}</p> : null}

      <p className="mt-3 px-1 text-[12px] font-medium text-ink-muted">{text(T.mejl)}</p>
      {kandidater.mejl.length === 0 ? (
        <p className="px-1 text-[12px] text-ink-subtle">{text(T.inga)}</p>
      ) : (
        <ul className="mt-1 max-h-40 overflow-y-auto">
          {kandidater.mejl.map((m) => (
            <li key={m.id}>
              <label className="flex min-h-9 cursor-pointer items-center gap-2 rounded-input px-1 text-[12px] hover:bg-paper2">
                <input type="checkbox" checked={valdaMejl.has(m.id)} onChange={() => vaxla(valdaMejl, setValdaMejl, m.id)} className="h-4 w-4 accent-ink" />
                <span className="min-w-0 truncate">{m.subject || m.from_email}</span>
                <span className="ml-auto shrink-0 text-ink-subtle">
                  {m.is_test ? `${text(T.test)} · ` : ""}
                  {nar(m.received_at)}
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
      {valdaMejl.size ? (
        <button type="button" onClick={() => void flytta("mejl", [...valdaMejl])} disabled={flyttar || !konfigurerad} className={cn(btnPrimary, "mt-2 w-full disabled:opacity-60")}>
          {flyttar ? text(T.flyttar) : text({ sv: `Flytta ${valdaMejl.size} mejl till main`, en: `Move ${valdaMejl.size} emails to main` })}
        </button>
      ) : null}

      <p className="mt-3 px-1 text-[12px] font-medium text-ink-muted">{text(T.korningar)}</p>
      <p className="px-1 text-[12px] text-ink-subtle">{text(T.korningarForklaring)}</p>
      {kandidater.korningar.length === 0 ? (
        <p className="px-1 text-[12px] text-ink-subtle">{text(T.inga)}</p>
      ) : (
        <ul className="mt-1 max-h-40 overflow-y-auto">
          {kandidater.korningar.map((k) => (
            <li key={k.job_id}>
              <label className="flex min-h-9 cursor-pointer items-center gap-2 rounded-input px-1 text-[12px] hover:bg-paper2">
                <input type="checkbox" checked={valdaKorningar.has(k.job_id)} onChange={() => vaxla(valdaKorningar, setValdaKorningar, k.job_id)} className="h-4 w-4 accent-ink" />
                <span className="min-w-0 truncate">
                  {nar(k.created_at)} · {k.scope} · {k.levererade ?? "–"}/{k.mal ?? "–"}
                </span>
                <span className="ml-auto shrink-0 text-ink-subtle">{k.status}</span>
              </label>
            </li>
          ))}
        </ul>
      )}
      {valdaKorningar.size ? (
        <button type="button" onClick={() => void flytta("korning", [...valdaKorningar])} disabled={flyttar || !konfigurerad} className={cn(btnPrimary, "mt-2 w-full disabled:opacity-60")}>
          {flyttar ? text(T.flyttar) : text({ sv: `Flytta ${valdaKorningar.size} körningar till main`, en: `Move ${valdaKorningar.size} runs to main` })}
        </button>
      ) : null}

      <p className="mt-3 px-1 text-[12px] font-medium text-ink-muted">{text(T.listor)}</p>
      <p className="px-1 text-[12px] text-ink-subtle">{text(T.listorForklaring)}</p>
      {listor.length === 0 ? (
        <p className="px-1 text-[12px] text-ink-subtle">{text(T.inga)}</p>
      ) : (
        <ul className="mt-1 max-h-40 overflow-y-auto">
          {listor.map((l) => (
            <li key={l.id}>
              <label className="flex min-h-9 cursor-pointer items-center gap-2 rounded-input px-1 text-[12px] hover:bg-paper2">
                <input type="checkbox" checked={valdaListor.has(l.id)} onChange={() => vaxla(valdaListor, setValdaListor, l.id)} className="h-4 w-4 accent-ink" />
                <span className="min-w-0 truncate">{l.titel ?? l.id}</span>
                <span className="ml-auto shrink-0 text-ink-subtle">
                  {l.is_test ? `${text(T.test)} · ` : ""}
                  {l.rader ?? 0} {text(T.rader)}
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
      {valdaListor.size ? (
        <button type="button" onClick={() => void flytta("lista", [...valdaListor])} disabled={flyttar || !konfigurerad} className={cn(btnPrimary, "mt-2 w-full disabled:opacity-60")}>
          {flyttar ? text(T.flyttar) : text({ sv: `Flytta ${valdaListor.size} listor till main`, en: `Move ${valdaListor.size} lists to main` })}
        </button>
      ) : null}

      {kvitto ? (
        <ul role="status" className="mt-2 px-1 text-[12px] text-ink-muted">
          {kvitto.map((r) => (
            <li key={r.ref_id} className={r.resultat === "fel" ? "text-danger" : ""}>
              {r.ref_id.slice(0, 8)}… {RESULTAT[r.resultat] ? text(RESULTAT[r.resultat]) : r.resultat}
              {r.fel ? `: ${r.fel}` : ""}
            </li>
          ))}
        </ul>
      ) : null}
      {kandidater.flyttade.length ? (
        <p className="mt-2 px-1 text-[12px] text-ink-subtle">
          {text(T.flyttade)}: {kandidater.flyttade.filter((f) => f.resultat === "ok").length}
        </p>
      ) : null}
    </div>
  );
}
