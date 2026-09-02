"use client";

import { useEffect, useMemo, useState } from "react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { bytVy } from "@/lib/actions/vy";
import { readJsonBody } from "@/lib/http/json";

type Kund = { slug: string; name: string };

/**
 * Sökbar växel in i en kunds profil. Samma server action som "Öppna" på
 * Kunder-raden — cookien måste sitta innan nästa render, annars ser knappen
 * ut att missa.
 *
 * Listan hämtas först när fältet öppnas, inte på varje sidladdning: adminytan
 * ska inte vänta på alla tenants för att visa en header.
 *
 * ## Varför /api/admin/kunder och inte /api/admin/tenants
 *
 * Den senare är backendens lista över ALLA tenants, och flera av dem har ingen
 * arbetsyta i Next-appens databas — `public-demo`, gamla testtenants. Klickade
 * man på en sådan svarade varje yta i kundens profil 409 "Ingen backend-nyckel
 * för …". Växeln erbjöd alltså kunder som inte gick att öppna. Den nya routen
 * listar arbetsytorna, alltså exakt de som har en tenant att gå in i.
 */
export function BytKund() {
  const { isPlatformAdmin, impersonation } = useDashboard();
  const [oppen, setOppen] = useState(false);
  const [q, setQ] = useState("");
  const [kunder, setKunder] = useState<Kund[] | null>(null);
  const [fel, setFel] = useState<string | null>(null);

  useEffect(() => {
    if (!oppen || kunder) return;
    let avbruten = false;
    void (async () => {
      try {
        const response = await fetch("/api/admin/kunder", { cache: "no-store" });
        const kropp = await readJsonBody<{ tenants?: { slug?: string | null; name?: string }[] }>(
          response
        );
        if (avbruten) return;
        if (!response.ok || !kropp?.tenants) {
          setFel("Kundlistan gick inte att hämta.");
          return;
        }
        setKunder(
          kropp.tenants
            .filter((t): t is { slug: string; name: string } => Boolean(t.slug && t.name))
            .map((t) => ({ slug: t.slug, name: t.name }))
        );
      } catch {
        if (!avbruten) setFel("Kundlistan gick inte att hämta.");
      }
    })();
    return () => {
      avbruten = true;
    };
  }, [oppen, kunder]);

  const filtrerade = useMemo(() => {
    const n = q.trim().toLowerCase();
    const lista = kunder ?? [];
    if (!n) return lista.slice(0, 12);
    return lista
      .filter((k) => k.name.toLowerCase().includes(n) || k.slug.toLowerCase().includes(n))
      .slice(0, 12);
  }, [kunder, q]);

  if (!isPlatformAdmin) {
    return null;
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOppen((v) => !v)}
        aria-expanded={oppen}
        className="focus-ring inline-flex min-h-9 items-center rounded-input bg-paper2 px-2.5 text-[13px] font-medium text-ink/70 transition-colors hover:text-ink"
      >
        {impersonation ? impersonation.namn : "Byt kund"}
      </button>
      {oppen ? (
        <div className="absolute right-0 z-40 mt-1 w-[min(20rem,calc(100vw-2rem))] rounded-input border border-ink/15 bg-paper p-2 shadow-sm">
          <input
            type="search"
            value={q}
            onChange={(event) => setQ(event.target.value)}
            placeholder="Sök kund eller slug…"
            autoFocus
            className="focus-ring min-h-11 w-full rounded-input bg-paper2 px-3 text-sm outline-none placeholder:text-ink/35"
          />
          {fel ? <p className="mt-2 px-1 text-[13px] text-danger">{fel}</p> : null}
          {!fel && kunder === null ? (
            <p className="mt-2 px-1 text-[13px] text-ink/50">Hämtar…</p>
          ) : null}
          <ul className="mt-1 max-h-64 overflow-y-auto">
            {filtrerade.map((kund) => (
              <li key={kund.slug}>
                <form action={bytVy}>
                  <button
                    type="submit"
                    name="vy"
                    value={`kund:${kund.slug}`}
                    className="focus-ring flex min-h-11 w-full items-center rounded-input px-3 text-left text-[13px] hover:bg-paper2"
                  >
                    <span className="min-w-0 truncate font-medium">{kund.name}</span>
                    <span className="ml-auto shrink-0 pl-3 font-mono text-[11px] text-ink/40">
                      {kund.slug}
                    </span>
                  </button>
                </form>
              </li>
            ))}
          </ul>
          {kunder && filtrerade.length === 0 ? (
            <p className="px-1 py-2 text-[13px] text-ink/50">Ingen kund matchade.</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
