"use client";

import { ArrowRight, CheckCircle2, Loader2, Mail, ScanLine } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Integritetsnotis } from "@/components/Integritetsnotis";
import { PageHeader } from "@/components/PageHeader";
import { PeriodValjare } from "@/components/PeriodValjare";
import { Badge, btnLiten, btnPrimary } from "@/components/ui";
import { kronor } from "@/lib/format";
import { HttpJsonError, felmeddelande, readJson } from "@/lib/http/json";
import {
  KVBAS,
  type Handelse,
  type Kvitto,
  type Sammanfattning,
  useKvitton
} from "@/lib/kvitton";
import { cn } from "@/lib/utils";

/**
 * Inkorgen — Kvittohanterarens huvudvy. Skanningen görs i ETT backendanrop
 * och SPELAS UPP: mejlen glider in i tur och ordning och beloppet markeras i
 * det ögonblick det identifierats. Varje rad är en riktig händelse ur
 * körningen, inte en inspelning. Reduced motion hoppar till slutläget.
 */

const STEG_MS = 420;

function feltext(orsak: unknown): string {
  if (orsak instanceof HttpJsonError) {
    const kropp =
      orsak.body && typeof orsak.body === "object" ? (orsak.body as Record<string, unknown>) : {};
    return (
      (typeof kropp.error === "string" && kropp.error) ||
      (typeof kropp.detail === "string" && kropp.detail) ||
      orsak.message
    );
  }
  return felmeddelande(orsak);
}

export function InkorgVy() {
  const { period, konto, hamta } = useKvitton();
  const [skannar, setSkannar] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const [handelser, setHandelser] = useState<Handelse[] | null>(null);
  const [visade, setVisade] = useState(0);
  const [resultatText, setResultatText] = useState<string | null>(null);
  const [nya, setNya] = useState(0);

  useEffect(() => {
    if (!handelser || visade >= handelser.length) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setVisade(handelser.length);
      return;
    }
    const timer = window.setTimeout(() => setVisade((n) => n + 1), STEG_MS);
    return () => window.clearTimeout(timer);
  }, [handelser, visade]);

  const klar = handelser !== null && visade >= handelser.length;

  async function skanna() {
    setSkannar(true);
    setFel(null);
    setHandelser(null);
    setVisade(0);
    setResultatText(null);
    try {
      const svar = await fetch(
        `${KVBAS}/skanna?fran=${period.fran}&till=${period.till}`,
        { method: "POST" }
      );
      const data = await readJson<{
        handelser: Handelse[];
        kvitton: Kvitto[];
        sammanfattning: Sammanfattning;
        text: string;
        nya_kvitton: number;
      }>(svar);
      setHandelser(data?.handelser ?? []);
      setResultatText(data?.text ?? null);
      setNya(data?.nya_kvitton ?? 0);
      await hamta();
    } catch (orsak) {
      setFel(feltext(orsak));
    } finally {
      setSkannar(false);
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        rubrik="Inkorgen"
        beskrivning="Agenten läser din kopplade inkorg med read-only-åtkomst, identifierar kvitton och utlägg och plockar ut beloppen — mejl som inte är kvitton lämnas orörda."
        actions={
          <>
            <PeriodValjare />
            <button
              type="button"
              disabled={skannar || konto === null || !konto.kopplad}
              onClick={() => void skanna()}
              title={
                konto === null || konto.kopplad
                  ? undefined
                  : "Ingen mejlinkorg är kopplad ännu."
              }
              className={cn(btnPrimary, btnLiten)}
            >
              {skannar ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <ScanLine className="h-4 w-4" aria-hidden />
              )}
              Skanna inkorgen
            </button>
          </>
        }
      />

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[0.875rem] text-danger">
          {fel}
        </p>
      ) : null}

      <p className="flex flex-wrap items-center gap-2 text-[0.875rem] text-ink/60">
        <Mail className="h-4 w-4 shrink-0 text-mineral" aria-hidden />
        {konto === null ? (
          "Hämtar mejlkontot…"
        ) : konto.kopplad ? (
          <>
            Kopplad inkorg: <span className="font-medium text-ink">{konto.adress}</span>
            <Badge tone="good">
              {konto.leverantor === "gmail"
                ? "Gmail"
                : konto.leverantor === "microsoft"
                  ? "Outlook/Hotmail"
                  : "Demokonto"}
            </Badge>
          </>
        ) : (
          <>
            Ingen inkorg kopplad ännu. Vi kopplar Gmail, Outlook eller Hotmail åt dig
            med read-only-åtkomst — hör av dig via Kontakt, så är det klart på ett
            kort möte.
          </>
        )}
      </p>

      {/* Uppspelningen. */}
      <section className="rounded-[10px] border border-ink/12 bg-paper2/30 p-5">
        <div className="flex items-baseline justify-between gap-4">
          <p className="text-[0.75rem] font-medium uppercase tracking-[0.12em] text-mineral">
            Senaste skanningen
          </p>
          {handelser !== null ? (
            <p className="text-[0.75rem] tabular-nums text-mineral" role="status">
              {klar
                ? `${handelser.length} mejl genomlästa`
                : `läser mejl ${Math.min(visade + 1, handelser.length)} av ${handelser.length}…`}
            </p>
          ) : null}
        </div>

        {handelser === null ? (
          <p className="mt-4 border-t border-ink/10 pt-4 text-[0.875rem] leading-6 text-ink/55">
            Tryck på Skanna inkorgen, så läser agenten mejlen ett i taget och plockar
            ut beloppen medan du tittar på. Kvitton som redan är inlästa hoppas över
            — samma kvitto räknas aldrig två gånger.
          </p>
        ) : (
          <ul className="mt-3 divide-y divide-ink/10 border-t border-ink/10">
            {handelser.slice(0, visade).map((h) => (
              <li key={h.mejl_id} className="animate-mejl-in py-2.5">
                <div className="flex min-w-0 items-baseline justify-between gap-3">
                  <p className="min-w-0 truncate text-[0.875rem] font-medium text-ink">
                    {h.avsandare}
                    <span className="ml-2 font-normal text-ink/55">{h.amne}</span>
                  </p>
                  <span className="shrink-0">
                    {h.utfall === "kvitto" ? (
                      <Badge tone="good">Kvitto</Badge>
                    ) : h.utfall === "kvitto_granska" ? (
                      <Badge tone="warn">Granska</Badge>
                    ) : h.utfall === "redan_last" ? (
                      <span className="text-[0.75rem] text-mineral">redan inläst</span>
                    ) : (
                      <span className="text-[0.75rem] text-mineral">inte ett kvitto</span>
                    )}
                  </span>
                </div>
                {h.belopp || h.belopp_original ? (
                  <p className="mt-1 font-mono text-[0.75rem] text-ink/45">
                    Belopp:{" "}
                    <mark
                      className={cn(
                        "animate-belopp rounded-[3px] px-1 py-0.5 font-semibold text-ink",
                        h.belopp ? "bg-ochre/25" : "bg-copper/20"
                      )}
                    >
                      {h.belopp ? kronor(h.belopp) : h.belopp_original}
                    </mark>
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        )}

        {klar ? (
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-ink/10 pt-3">
            <p className="flex items-center gap-2 text-[0.8125rem] text-moss">
              <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden />
              {nya === 0
                ? "Inga nya kvitton — allt var redan inläst."
                : `${nya} ${nya === 1 ? "nytt kvitto" : "nya kvitton"} inlästa.`}
            </p>
            <Link
              href="/kvitton"
              className="focus-ring inline-flex items-center gap-1.5 rounded-[4px] text-[0.8125rem] text-ink/60 underline underline-offset-4 hover:text-ink"
            >
              Till kvittolistan
              <ArrowRight className="h-3.5 w-3.5" aria-hidden />
            </Link>
          </div>
        ) : null}
      </section>

      {klar && resultatText ? (
        <section className="max-w-[72ch]">
          <p className="text-[0.75rem] font-medium uppercase tracking-[0.12em] text-mineral">
            Sammanfattning
          </p>
          <p className="mt-2 text-[0.9375rem] leading-7 text-ink/75">{resultatText}</p>
        </section>
      ) : null}

      <Integritetsnotis />
    </div>
  );
}
