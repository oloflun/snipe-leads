"use client";

import { KeyRound, Plus, X } from "lucide-react";
import { useState } from "react";
import { Badge, btnLiten, btnSecondary } from "@/components/ui";
import { cn } from "@/lib/utils";
import { faltklass, type Hemlighetsandringar } from "./typer";

/**
 * Redigering av nycklar som backenden aldrig lämnar ut.
 *
 * En sparad nyckel visas som "Sparad" med två val: byt eller ta bort. Värdet
 * går inte att läsa tillbaka, så "byt" betyder alltid att klistra in ett nytt.
 * Formuläret skickar bara ÄNDRINGAR (ett värde sätter, null tar bort), och
 * backenden slår ihop dem med det som redan finns. En nyckel ingen rört ligger
 * kvar, så att ändra en URL kräver inte att alla nycklar klistras in igen.
 */

export type Forslag = { namn: string; etikett: string; hjalp?: string };

const NAMNMONSTER = /^[A-Za-z_][A-Za-z0-9_]{0,39}$/;

export function Hemligheter({
  sparade,
  forslag = [],
  andringar,
  onAndra,
  friaNamn = true
}: Readonly<{
  sparade: string[];
  forslag?: Forslag[];
  andringar: Hemlighetsandringar;
  onAndra: (nya: Hemlighetsandringar) => void;
  /** Får admin lägga till egna namn (HTTP-integrationer), eller bara de föreslagna (kanaler)? */
  friaNamn?: boolean;
}>) {
  const [nyttNamn, setNyttNamn] = useState("");
  const [byter, setByter] = useState<Record<string, boolean>>({});

  const forslagsnamn = new Set(forslag.map((f) => f.namn));
  const extra = Object.keys(andringar).filter(
    (n) => !sparade.includes(n) && !forslagsnamn.has(n) && andringar[n] !== null
  );
  const rader = [
    ...forslag.map((f) => f.namn),
    ...sparade.filter((n) => !forslagsnamn.has(n)),
    ...extra
  ];

  function satt(namn: string, varde: string | null) {
    onAndra({ ...andringar, [namn]: varde });
  }

  function aterstall(namn: string) {
    const kopia = { ...andringar };
    delete kopia[namn];
    onAndra(kopia);
    setByter((b) => ({ ...b, [namn]: false }));
  }

  function laggTill() {
    const namn = nyttNamn.trim();
    if (!NAMNMONSTER.test(namn) || rader.includes(namn)) return;
    onAndra({ ...andringar, [namn]: "" });
    setNyttNamn("");
  }

  const namnFel = nyttNamn.trim() !== "" && !NAMNMONSTER.test(nyttNamn.trim());

  return (
    <div className="divide-y divide-ink/12 border-y border-ink/15">
      {rader.map((namn) => {
        const f = forslag.find((x) => x.namn === namn);
        const arSparad = sparade.includes(namn);
        const tasBort = andringar[namn] === null;
        const visaFalt = !arSparad || byter[namn];
        return (
          <div key={namn} className="py-3">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <span className="flex min-w-0 items-baseline gap-2">
                <KeyRound className="h-3.5 w-3.5 shrink-0 translate-y-0.5 text-ink/45" aria-hidden />
                <span className="text-[0.9375rem] font-medium">{f?.etikett ?? namn}</span>
                {f ? <code className="font-mono text-[0.75rem] text-ink/45">{namn}</code> : null}
              </span>
              <span className="flex items-center gap-2">
                {arSparad && !tasBort && !byter[namn] ? <Badge tone="good">Sparad</Badge> : null}
                {tasBort ? <Badge tone="danger">Tas bort vid sparning</Badge> : null}
                {arSparad && !tasBort && !byter[namn] ? (
                  <>
                    <button
                      type="button"
                      className={cn(btnSecondary, btnLiten)}
                      onClick={() => setByter((b) => ({ ...b, [namn]: true }))}
                    >
                      Byt
                    </button>
                    <button type="button" className={cn(btnSecondary, btnLiten)} onClick={() => satt(namn, null)}>
                      Ta bort
                    </button>
                  </>
                ) : null}
                {tasBort || (arSparad && byter[namn]) ? (
                  <button type="button" className={cn(btnSecondary, btnLiten)} onClick={() => aterstall(namn)}>
                    Ångra
                  </button>
                ) : null}
                {!arSparad && !f ? (
                  <button
                    type="button"
                    aria-label={`Ta bort raden ${namn}`}
                    className={cn(btnSecondary, btnLiten)}
                    onClick={() => aterstall(namn)}
                  >
                    <X className="h-3.5 w-3.5" aria-hidden />
                  </button>
                ) : null}
              </span>
            </div>
            {visaFalt && !tasBort ? (
              <label className="mt-1 block">
                <span className="sr-only">{f?.etikett ?? namn}</span>
                <input
                  type="password"
                  autoComplete="off"
                  spellCheck={false}
                  value={typeof andringar[namn] === "string" ? (andringar[namn] as string) : ""}
                  onChange={(e) => satt(namn, e.target.value)}
                  placeholder={arSparad ? "Klistra in det nya värdet" : "Klistra in värdet"}
                  className={faltklass}
                />
              </label>
            ) : null}
            {f?.hjalp ? <p className="mt-1.5 text-[0.8125rem] leading-5 text-ink/55">{f.hjalp}</p> : null}
          </div>
        );
      })}

      {friaNamn ? (
        <div className="flex flex-wrap items-end gap-3 py-3">
          <label className="block min-w-[14rem] flex-1">
            <span className="text-[0.875rem] font-medium text-ink">Ny nyckel</span>
            <input
              value={nyttNamn}
              onChange={(e) => setNyttNamn(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  laggTill();
                }
              }}
              placeholder="token"
              spellCheck={false}
              aria-invalid={namnFel || undefined}
              className={faltklass}
            />
          </label>
          <button type="button" onClick={laggTill} disabled={!nyttNamn.trim() || namnFel} className={cn(btnSecondary)}>
            <Plus className="h-4 w-4" aria-hidden />
            Lägg till nyckel
          </button>
          <p className="w-full text-[0.8125rem] leading-5 text-ink-muted">
            {namnFel
              ? "Bara bokstäver, siffror och _, och inte en siffra först."
              : "Används i konfigurationen som {{hemlighet.namn}}."}
          </p>
        </div>
      ) : null}
    </div>
  );
}
