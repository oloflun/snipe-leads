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
 * exakt det. Raden "Nästa spegling" säger rakt ut att allt oflyttat försvinner
 * då. Varje flytt får ett kvitto per rad ur mottagarens svar.
 */

const T = {
  rubrik: { sv: "Flytta till main", en: "Move to main" },
  forklaring: {
    sv: "Development speglas från main varje natt. Det som ska sparas till den riktiga miljön måste flyttas hit innan dess.",
    en: "Development is mirrored from main every night. Anything to keep in the live environment must be moved before then."
  },
  nastaSpegling: { sv: "Nästa spegling", en: "Next mirror" },
  forsvinner: { sv: "Allt oflyttat försvinner då.", en: "Everything not moved disappears then." },
  senastSpeglad: { sv: "senast speglad", en: "last mirrored" },
  mejl: { sv: "Supportmejl", en: "Support email" },
  korningar: { sv: "Leadskörningar", en: "Lead runs" },
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
  fel: { sv: "fel", en: "error" },
  test: { sv: "test", en: "test" }
} satisfies Record<string, Localized>;

const RESULTAT: Record<string, Localized> = { importerad: T.importerad, redan_flyttad: T.redan, fel: T.fel };

export function FlyttTillMain({ slug }: Readonly<{ slug: string }>) {
  const { locale, text } = useLocale();
  const [lage, setLage] = useState<{ status: FlyttStatus; kandidater: FlyttKandidater } | null | "laddar">("laddar");
  const [fel, setFel] = useState<string | null>(null);
  const [valdaMejl, setValdaMejl] = useState<Set<string>>(new Set());
  const [valdaKorningar, setValdaKorningar] = useState<Set<string>>(new Set());
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

  async function flytta(typ: "mejl" | "korning", ids: string[]) {
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
  }

  const konfigurerad = status.mal_konfigurerat && status.nyckel_konfigurerad;

  return (
    <div className="mt-3 border-t border-ink/10 pt-3">
      <p className="px-1 text-[13px] font-semibold">{text(T.rubrik)}</p>
      <p className="mt-1 px-1 text-[12px] leading-5 text-ink-subtle">{text(T.forklaring)}</p>
      <p className="mt-1 px-1 text-[12px] text-ink-muted">
        {text(T.nastaSpegling)}: {status.nasta_spegling}. {text(T.forsvinner)}
        {status.spegel?.seeded_at ? ` (${text(T.senastSpeglad)} ${nar(status.spegel.seeded_at)})` : ""}
      </p>
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
