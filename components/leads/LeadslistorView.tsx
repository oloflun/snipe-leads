"use client";

import { useCallback, useEffect, useState } from "react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { btnPrimary, btnSecondary, EmptyState, SkeletonRows } from "@/components/ui";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Leadslistor — tillägget vid sidan av de riktade körningarna.
 *
 * Kunden beställer en lista med titel och antal; agenten bygger den i
 * bakgrunden (ingen sändning, inga utkast) och raderna landar här som en
 * granskningsbar tabell med kontaktväg, källa och signal per bolag, plus
 * CSV-export. Grinden sitter i WorkspaceSection: den här vyn renderas bara
 * när arbetsytan har tillägget "leadlists".
 *
 * Backendkontraktet (byggs i snajp-support, migration 060):
 *   POST /leads/listor            {titel, antal, is_test?} → 202 {list_id, job_id}
 *   GET  /leads/listor            → {lists: [...]}
 *   GET  /leads/listor/{id}       → {list: {...}, items: [...]}
 * 429 betyder budgettak — feltexten kommer i `detail` och visas som den är.
 */

type Lista = {
  id: string;
  titel: string;
  antal: number;
  /** bestalld | byggs | klar | fel — speglar check-villkoret i migration 060. */
  status: string;
  felorsak?: string | null;
  created_at?: string | null;
  completed_at?: string | null;
  item_count?: number | null;
};

type ListRad = {
  company_name: string;
  website?: string | null;
  ort?: string | null;
  contact_name?: string | null;
  contact_role?: string | null;
  contact_email?: string | null;
  contact_level?: string | null;
  source_name?: string | null;
  source_url?: string | null;
  signal?: string | null;
  signal_detalj?: string | null;
};

/** Backendens statusvärden, på svenska — samma mönster som Bolagsregistret. */
const STATUS_ETIKETT: Record<string, string> = {
  bestalld: "Beställd",
  byggs: "Byggs",
  klar: "Klar",
  fel: "Fel"
};

/** Status som betyder att agenten fortfarande arbetar — de pollas. */
const PAGAENDE = new Set(["bestalld", "byggs"]);

// Samma fält- och radmönster som LeadsRunForm. Speglas med flit i stället för
// att delas — samma resonemang som `anropa` nedan och som Bolagssida.tsx: en
// delad hjälpare hade tvingat fram en export ur en fil vars docstring säger
// att den bara har två ytor.
const fältklass =
  "w-full rounded-input border border-ink/15 bg-paper px-3 py-2 text-[15px] focus-ring";

function Rad({
  etikett,
  hint,
  children
}: Readonly<{ etikett: string; hint?: string; children: React.ReactNode }>) {
  return (
    <label className="block">
      <span className="text-[13px] font-medium text-ink/70">{etikett}</span>
      {hint ? <span className="ml-2 text-[12px] text-ink/45">{hint}</span> : null}
      <div className="mt-1.5">{children}</div>
    </label>
  );
}

/**
 * Speglar `anropa()` i LeadsRunForm.tsx med flit i stället för att delas —
 * samma resonemang som Bolagssida.tsx: Pydantics 422 lägger en LISTA i
 * `detail`, en handskriven HTTPException (t.ex. 429-budgettaket) en STRÄNG,
 * och båda ska bli läsbar svenska i stället för "[object Object]".
 */
async function anropa<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/snajp-support${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init
  });
  const kropp =
    (await readJsonBody<T & { error?: string; detail?: unknown }>(response)) ?? ({} as T);
  if (!response.ok) {
    const k = kropp as { error?: string; detail?: unknown };
    const detaljtext = Array.isArray(k.detail)
      ? k.detail
          .map((d) =>
            d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)
          )
          .join("; ")
      : typeof k.detail === "string"
        ? k.detail
        : undefined;
    throw new Error(detaljtext ?? k.error ?? `Anropet avvisades (${response.status}).`);
  }
  return kropp;
}

/** Kontaktvägen som EN sträng: namn/roll om de finns, annars adressen. */
function kontakt(rad: ListRad): string {
  const namnRoll = [rad.contact_name, rad.contact_role].filter(Boolean).join(", ");
  return namnRoll || rad.contact_email || "—";
}

function signaltext(rad: ListRad): string {
  return [rad.signal, rad.signal_detalj].filter(Boolean).join(" — ") || "—";
}

/** RFC 4180-citering. Semikolon som avgränsare och BOM först: svensk Excel
 *  öppnar annars hela filen i en kolumn och läser å/ä/ö som mojibake. */
function csvFalt(värde: string | null | undefined): string {
  const text = värde ?? "";
  return /[";\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function byggCsv(items: ListRad[]): string {
  const rader = [
    ["Bolag", "Ort", "Kontakt", "Kontaktnivå", "Signal", "Källa", "Källänk", "Webbplats", "E-post"],
    ...items.map((rad) => [
      rad.company_name,
      rad.ort ?? "",
      kontakt(rad),
      rad.contact_level ?? "",
      signaltext(rad),
      rad.source_name ?? "",
      rad.source_url ?? "",
      rad.website ?? "",
      rad.contact_email ?? ""
    ])
  ];
  return "\uFEFF" + rader.map((rad) => rad.map(csvFalt).join(";")).join("\r\n");
}

function laddaNerCsv(titel: string, items: ListRad[]) {
  const blob = new Blob([byggCsv(items)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  // Ur titeln, inte ett id: filen ska gå att hitta i en nedladdningsmapp.
  a.download = `${titel.replace(/[^\p{L}\p{N} _-]/gu, "").trim() || "leadslista"}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function datum(varde: string | null | undefined): string | null {
  if (!varde) return null;
  const d = new Date(varde);
  return Number.isNaN(d.getTime()) ? null : d.toISOString().slice(0, 10);
}

export function LeadslistorView() {
  const { isDemo, vy } = useDashboard();

  const [titel, setTitel] = useState("");
  const [antal, setAntal] = useState("25");
  const [bestaller, setBestaller] = useState(false);
  const [bestallFel, setBestallFel] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const [listor, setListor] = useState<Lista[] | null>(null);
  const [listFel, setListFel] = useState<string | null>(null);

  const [vald, setVald] = useState<{ lista: Lista; items: ListRad[] } | null>(null);
  const [oppnar, setOppnar] = useState<string | null>(null);
  const [detaljFel, setDetaljFel] = useState<string | null>(null);

  const hamtaListor = useCallback(async (tyst = false) => {
    if (!tyst) setListFel(null);
    try {
      const svar = await anropa<{ lists?: Lista[] }>("/leads/listor");
      setListor(svar.lists ?? []);
      setListFel(null);
    } catch (fel) {
      // Vid tyst pollning skrivs listan inte över av ett fel — nästa varv
      // kan lyckas, och en lista som blinkar bort är värre än en gammal.
      if (!tyst || listor === null) setListFel(felmeddelande(fel));
    }
  }, [listor]);

  useEffect(() => {
    void hamtaListor();
    // Bara vid montering — pollningen nedan äger uppdateringarna.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Pollning: så länge någon lista är beställd eller byggs hämtas läget om
  // var 5:e sekund — samma tålmodiga mönster som LeadsRunForm mot jobben,
  // men mot listresursen: timern re-armas av varje nytt svar och dör av sig
  // själv när inget längre är pågående.
  useEffect(() => {
    if (!listor?.some((l) => PAGAENDE.has(l.status))) return;
    const timer = window.setTimeout(() => void hamtaListor(true), 5000);
    return () => window.clearTimeout(timer);
  }, [listor, hamtaListor]);

  async function bestall() {
    const antalTal = Number(antal);
    if (!titel.trim()) {
      setBestallFel("Ge listan en titel — det är den ni hittar den på sedan.");
      return;
    }
    if (!Number.isInteger(antalTal) || antalTal < 1 || antalTal > 200) {
      setBestallFel("Antal bolag: minst 1, högst 200.");
      return;
    }

    setBestaller(true);
    setBestallFel(null);
    setStatus(null);
    try {
      // 429 = budgettak. `anropa` plockar redan ut feltexten ur `detail`,
      // så den visas som den är i felraden nedan.
      await anropa<{ list_id?: string; job_id?: string }>("/leads/listor", {
        method: "POST",
        body: JSON.stringify({
          titel: titel.trim(),
          antal: antalTal,
          // Demovyn räknas som test, precis som i Discovery: den ska aldrig
          // synas som kundvolym.
          is_test: isDemo || vy === "demo"
        })
      });
      setTitel("");
      setStatus("Listan är beställd. Agenten bygger den nu — status uppdateras här.");
      await hamtaListor(true);
    } catch (fel) {
      setBestallFel(felmeddelande(fel));
    } finally {
      setBestaller(false);
    }
  }

  async function oppna(lista: Lista) {
    if (lista.status !== "klar") return;
    if (vald?.lista.id === lista.id) {
      setVald(null);
      return;
    }
    setOppnar(lista.id);
    setDetaljFel(null);
    try {
      const svar = await anropa<{ list?: Lista; items?: ListRad[] }>(
        `/leads/listor/${encodeURIComponent(lista.id)}`
      );
      setVald({ lista: svar.list ?? lista, items: svar.items ?? [] });
    } catch (fel) {
      setDetaljFel(felmeddelande(fel));
    } finally {
      setOppnar(null);
    }
  }

  return (
    <div className="grid gap-12">
      {/* ------------------------------------------- BESTÄLLNING */}
      <section aria-labelledby="bestall-lista">
        <h2 id="bestall-lista" className="text-[1.125rem] font-semibold tracking-[-0.01em]">
          Beställ en lista
        </h2>
        <p className="mt-1 max-w-[65ch] text-[13px] text-ink/45">
          Agenten letar, verifierar och lägger raderna här — ingenting skickas och inga utkast
          skrivs.
        </p>

        <div className="mt-6 grid max-w-[760px] gap-5 sm:grid-cols-2">
          <Rad etikett="Titel" hint="t.ex. Bygg i Norrland, 10–50 anställda">
            <input
              value={titel}
              onChange={(e) => setTitel(e.target.value)}
              placeholder="Vad listan ska handla om"
              className={fältklass}
            />
          </Rad>
          <Rad etikett="Antal bolag" hint="1–200">
            <input
              type="number"
              min={1}
              max={200}
              value={antal}
              onChange={(e) => setAntal(e.target.value)}
              className={fältklass}
            />
          </Rad>
        </div>

        <button
          type="button"
          onClick={() => void bestall()}
          disabled={bestaller}
          className={cn(btnPrimary, "mt-6")}
        >
          {bestaller ? "Beställer…" : "Beställ lista"}
        </button>

        {status ? <p className="mt-3 text-[13px] text-ink/55">{status}</p> : null}
        {bestallFel ? (
          <p role="alert" className="mt-5 max-w-[70ch] break-words text-[15px] text-danger">
            {bestallFel}
          </p>
        ) : null}
      </section>

      {/* ---------------------------------------------- LISTORNA */}
      <section aria-labelledby="dina-listor" className="border-t border-ink/15 pt-8">
        <h2 id="dina-listor" className="text-[1.125rem] font-semibold tracking-[-0.01em]">
          Dina listor
        </h2>

        {listFel ? (
          <div className="mt-4">
            <p role="alert" className="max-w-[70ch] break-words text-[15px] text-danger">
              {listFel}
            </p>
            <button
              type="button"
              onClick={() => void hamtaListor()}
              className={cn(btnSecondary, "mt-4")}
            >
              Försök igen
            </button>
          </div>
        ) : listor === null ? (
          <div className="mt-4">
            <SkeletonRows />
          </div>
        ) : listor.length === 0 ? (
          <div className="mt-4">
            <EmptyState
              title="Inga listor ännu"
              body="Beställ en lista ovan. Den byggs i bakgrunden och dyker upp här när den är klar — listan är tom tills dess."
            />
          </div>
        ) : (
          <ul className="mt-4 divide-y divide-ink/15 border-y border-ink/15">
            {listor.map((lista) => {
              const oppen = vald?.lista.id === lista.id;
              const klar = lista.status === "klar";
              return (
                <li key={lista.id} className="py-4">
                  <button
                    type="button"
                    onClick={() => void oppna(lista)}
                    disabled={!klar}
                    aria-expanded={klar ? oppen : undefined}
                    className={cn(
                      "focus-ring block w-full rounded-input text-left",
                      !klar && "cursor-default"
                    )}
                  >
                    <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
                      <div className="min-w-0">
                        <p className="text-[15px] font-semibold tracking-[-0.01em]">
                          {lista.titel}
                        </p>
                        <p className="mt-1 text-[13px] text-ink/50">
                          {[
                            `${lista.antal} beställda`,
                            typeof lista.item_count === "number"
                              ? `${lista.item_count} träffar`
                              : null,
                            datum(lista.completed_at ?? lista.created_at)
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </p>
                      </div>
                      {/* Ochre bara på det som pågår — klart är utgångsläget,
                          fel bär danger. Samma logik som StatusOrd i registret. */}
                      <span
                        className={cn(
                          "kicker shrink-0",
                          lista.status === "fel"
                            ? "text-danger"
                            : PAGAENDE.has(lista.status)
                              ? "text-ochre"
                              : "text-mineral"
                        )}
                      >
                        {STATUS_ETIKETT[lista.status] ?? lista.status}
                      </span>
                    </div>
                    {lista.status === "fel" && lista.felorsak ? (
                      <p className="mt-2 max-w-[70ch] text-[14px] leading-6 text-danger">
                        {lista.felorsak}
                      </p>
                    ) : null}
                    {klar ? (
                      <p className="mt-2 inline-flex items-center gap-1.5 text-[13px] font-medium text-ochre">
                        {oppnar === lista.id
                          ? "Hämtar…"
                          : oppen
                            ? "Dölj listan"
                            : "Öppna listan"}
                        <span aria-hidden>{oppen ? "↑" : "→"}</span>
                      </p>
                    ) : null}
                  </button>

                  {oppen && vald ? <Listtabell lista={vald.lista} items={vald.items} /> : null}
                </li>
              );
            })}
          </ul>
        )}

        {detaljFel ? (
          <p role="alert" className="mt-5 max-w-[70ch] break-words text-[15px] text-danger">
            {detaljFel}
          </p>
        ) : null}
      </section>
    </div>
  );
}

/**
 * Raderna i EN klar lista. Samma form som Bolagsregistret: tabell från md och
 * upp, kort under — sex kolumner krympta till 375px blir oläsliga.
 */
function Listtabell({ lista, items }: Readonly<{ lista: Lista; items: ListRad[] }>) {
  if (!items.length) {
    return (
      <p className="mt-4 border-t border-ink/10 pt-4 text-[15px] text-ink/60">
        Listan är klar men innehåller inga rader.
      </p>
    );
  }

  return (
    <div className="mt-4 rounded-card border border-ink/10 bg-paper p-4 md:p-5">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <p className="text-[13px] text-ink/50">
          {items.length} {items.length === 1 ? "bolag" : "bolag"} i listan
        </p>
        {/* CSV:n byggs helt på klientsidan av raderna som redan är hämtade —
            ingen ny endpoint, och det som laddas ner är exakt det som syns. */}
        <button
          type="button"
          onClick={() => laddaNerCsv(lista.titel, items)}
          className={cn(btnSecondary)}
        >
          Ladda ner CSV
        </button>
      </div>

      <div className="mt-4 hidden overflow-x-auto border-y border-ink/15 md:block">
        <table className="w-full min-w-[860px] border-collapse text-[15px]">
          <thead>
            <tr className="border-b border-ink/15 text-left">
              {["Bolag", "Ort", "Kontakt", "Kontaktnivå", "Signal", "Källa"].map(
                (rubrik, i, alla) => (
                  <th
                    key={rubrik}
                    scope="col"
                    className={cn(
                      "kicker py-4 font-medium text-mineral",
                      i < alla.length - 1 ? "pr-6" : ""
                    )}
                  >
                    {rubrik}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-ink/15">
            {items.map((rad, index) => (
              <tr key={`${rad.company_name}-${index}`} className="transition hover:bg-paper2/60">
                <th scope="row" className="py-4 pr-6 text-left font-normal">
                  <p className="text-[15px] font-semibold tracking-[-0.01em]">
                    {rad.company_name}
                  </p>
                  {rad.website ? (
                    <p className="mt-1 break-all text-sm text-ink/55">{rad.website}</p>
                  ) : null}
                </th>
                <td className="kicker py-4 pr-6 text-mineral">{rad.ort ?? "—"}</td>
                <td className="py-4 pr-6">
                  <p className="text-[15px]">{kontakt(rad)}</p>
                  {rad.contact_email && (rad.contact_name || rad.contact_role) ? (
                    <p className="mt-1 break-all text-sm text-ink/55">{rad.contact_email}</p>
                  ) : null}
                </td>
                <td className="kicker py-4 pr-6 text-mineral">{rad.contact_level ?? "—"}</td>
                <td className="py-4 pr-6 text-[15px] leading-6 text-ink/72">{signaltext(rad)}</td>
                <td className="py-4">
                  {rad.source_url ? (
                    <a
                      href={rad.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="focus-ring text-[14px] underline underline-offset-4 transition hover:text-ochre"
                    >
                      {rad.source_name || "Källa"}
                    </a>
                  ) : (
                    <span className="text-[14px] text-ink/55">{rad.source_name ?? "—"}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="mt-4 space-y-2 md:hidden">
        {items.map((rad, index) => (
          <li
            key={`${rad.company_name}-${index}`}
            className="rounded-input border border-ink/15 px-4 py-3"
          >
            <div className="flex items-baseline justify-between gap-3">
              <span className="min-w-0 text-[15px] font-semibold tracking-[-0.01em]">
                {rad.company_name}
              </span>
              {rad.contact_level ? (
                <span className="kicker shrink-0 text-mineral">{rad.contact_level}</span>
              ) : null}
            </div>
            <p className="kicker mt-1 text-mineral">
              {[rad.ort, rad.website].filter(Boolean).join(" · ") || "—"}
            </p>
            <p className="mt-2 text-sm leading-6 text-ink/72">{signaltext(rad)}</p>
            <div className="mt-2 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
              <span className="min-w-0 break-all text-sm text-ink/60">{kontakt(rad)}</span>
              {rad.source_url ? (
                <a
                  href={rad.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="focus-ring text-[13px] underline underline-offset-4"
                >
                  {rad.source_name || "Källa"}
                </a>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
