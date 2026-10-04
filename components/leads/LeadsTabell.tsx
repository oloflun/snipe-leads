"use client";

import { X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { EjAktiverad } from "@/components/EjAktiverad";
import { Badge, Cell, SkeletonRows, Tabell, Tomt, btnPrimary, btnSecondary, etikett, btnLiten, faltDiskret, faltTatt, chip, chipAktiv, chipInaktiv, chiplista, meta, tabellRad } from "@/components/ui";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import {
  LeadsFel,
  datumFormat,
  kontaktvagAv,
  leadsAnrop,
  poangAv,
  relativTid,
  type Kontaktvag,
  type SuiteProspekt,
  type Uppgift,
  type Vy,
  type VyFilter
} from "@/lib/leads/suite";
import { LEAD_TYP_ETIKETT, STATUS_ETIKETT, STATUS_ORDNING, leadTyp, nivaEtikett, type LeadTyp } from "@/lib/prospekt";
import { cn } from "@/lib/utils";

/**
 * Iris › Bolag › Tabell (Fas 10, Leads Suite F4): alla prospekt i en tabell
 * med inline-status, nästa uppgift och sparade vyer. Statusbytet sparas
 * direkt (PATCH) och återställs om sparningen faller. Under md blir raderna
 * kort i stället för en tabell som scrollar i sidled.
 */

const T = {
  tabell: { sv: "Leads", en: "Leads" },
  hamtaFel: { sv: "Leads kunde inte hämtas.", en: "The leads could not be loaded." },
  forsokIgen: { sv: "Försök igen", en: "Try again" },
  tomt: { sv: "Inga leads ännu. Kör Iris eller importera en lista.", en: "No leads yet. Run Iris or import a list." },
  ingaTraffar: { sv: "Inga leads matchar filtret.", en: "No leads match the filter." },
  kolBolag: { sv: "Bolag", en: "Company" },
  kolStatus: { sv: "Status", en: "Status" },
  kolNiva: { sv: "Nivå", en: "Tier" },
  kolPoang: { sv: "Poäng", en: "Score" },
  kolKontakt: { sv: "Kontaktväg", en: "Contact" },
  kolSenaste: { sv: "Senaste händelse", en: "Last event" },
  kolUppgift: { sv: "Nästa uppgift", en: "Next task" },
  kolTyp: { sv: "Typ", en: "Type" },
  filterStatus: { sv: "Status", en: "Status" },
  filterNiva: { sv: "Nivå", en: "Tier" },
  filterTyp: { sv: "Typ", en: "Type" },
  filterSok: { sv: "Sök", en: "Search" },
  sokPlaceholder: { sv: "Bolag eller kontakt", en: "Company or contact" },
  alla: { sv: "Alla", en: "All" },
  vyer: { sv: "Sparade vyer", en: "Saved views" },
  vyNamn: { sv: "Namn på vyn", en: "View name" },
  vyPlaceholder: { sv: "Heta leads i Göteborg", en: "Hot leads in Gothenburg" },
  sparaVy: { sv: "Spara vy", en: "Save view" },
  sparar: { sv: "Sparar…", en: "Saving…" },
  statusSparadesInte: { sv: "Statusen sparades inte", en: "The status was not saved" },
  sidodata: {
    sv: "Uppgifter eller sparade vyer kunde inte hämtas",
    en: "Tasks or saved views could not be loaded"
  },
  ingenUppgift: { sv: "Ingen", en: "None" },
  statusFor: { sv: "Status för", en: "Status for" },
  statusAndrad: { sv: "Status ändrad till", en: "Status changed to" }
} satisfies Record<string, Localized>;

const KONTAKT_ETIKETT: Record<Kontaktvag, Localized> = {
  bada: { sv: "Tel och mejl", en: "Phone and email" },
  telefon: { sv: "Tel", en: "Phone" },
  mejl: { sv: "Mejl", en: "Email" },
  saknas: { sv: "Saknas", en: "Missing" }
};

const TYPER: LeadTyp[] = ["iris", "lista", "import", "inkorg"];

function matchar(p: SuiteProspekt, f: VyFilter): boolean {
  if (f.status && p.status !== f.status) return false;
  if (f.niva && p.niva !== f.niva) return false;
  if (f.typ && leadTyp(p.origin) !== f.typ) return false;
  const sok = f.sok?.trim().toLowerCase();
  if (sok && ![p.company_name, p.contact_name, p.contact_email].some((v) => v?.toLowerCase().includes(sok))) return false;
  return true;
}

/** Bara de nycklar som är satta, så att en sparad vy är jämförbar. */
function rensat(f: VyFilter): VyFilter {
  return Object.fromEntries(Object.entries(f).filter(([, v]) => typeof v === "string" && v.trim() !== "")) as VyFilter;
}

// Täta fält (ui.tsx faltTatt): 36 px i verktygsraden och i tabellraderna.
const faltKlass = faltTatt;

export function LeadsTabell({
  onValj,
  demo = false
}: Readonly<{ onValj?: (id: string) => void; demo?: boolean }>) {
  const { locale, text } = useLocale();
  const [prospekt, setProspekt] = useState<SuiteProspekt[] | null>(null);
  const [uppgifter, setUppgifter] = useState<Uppgift[]>([]);
  const [vyer, setVyer] = useState<Vy[]>([]);
  const [fel, setFel] = useState<string | null>(null);
  const [ejAktiverad, setEjAktiverad] = useState(false);
  const [notis, setNotis] = useState<string | null>(null);
  const [meddelande, setMeddelande] = useState<string | null>(null);
  const [fokusId, setFokusId] = useState<string | null>(null);

  // Raden kan lämna filtret efter statusbytet: fokus till samma select om den
  // finns kvar efter commit, annars till statusfiltret (2.4.3).
  useEffect(() => {
    if (fokusId) (document.getElementById(`leads-status-${fokusId}`) ?? document.getElementById("leads-filter-status"))?.focus();
  }, [fokusId, prospekt]);
  const [filter, setFilter] = useState<VyFilter>({});
  const [vyNamn, setVyNamn] = useState("");
  const [sparar, setSparar] = useState(false);

  const hamta = useCallback(async () => {
    setFel(null);
    if (demo) {
      const svar = demoOversiktSvar("/leads/prospects") as { prospects?: SuiteProspekt[] } | undefined;
      setProspekt(svar?.prospects ?? []);
      return;
    }
    try {
      const [p, u, v] = await Promise.allSettled([
        leadsAnrop<{ prospects?: SuiteProspekt[] }>("/leads/prospects"),
        leadsAnrop<{ uppgifter?: Uppgift[] }>("/leads/uppgifter?oppna=1"),
        leadsAnrop<{ vyer?: Vy[] }>("/leads/vyer")
      ]);
      if (p.status === "rejected") throw p.reason;
      setProspekt(p.value.prospects ?? []);
      setUppgifter(u.status === "fulfilled" ? (u.value.uppgifter ?? []) : []);
      setVyer(v.status === "fulfilled" ? (v.value.vyer ?? []) : []);
      const sidofel = [u, v].find((r) => r.status === "rejected") as PromiseRejectedResult | undefined;
      setNotis(sidofel ? `${text(T.sidodata)}: ${felmeddelande(sidofel.reason)}` : null);
    } catch (orsak) {
      if (orsak instanceof LeadsFel && orsak.ejAktiverad) {
        setEjAktiverad(true);
        return;
      }
      setFel(felmeddelande(orsak));
    }
  }, [demo, text]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  const nastaUppgift = useMemo(() => {
    // Backenden sorterar förfallodatum stigande med null sist: första öppna per prospekt vinner.
    const karta = new Map<string, Uppgift>();
    for (const u of uppgifter) if (!u.klar && !karta.has(u.prospect_id)) karta.set(u.prospect_id, u);
    return karta;
  }, [uppgifter]);

  const synliga = useMemo(() => (prospekt ?? []).filter((p) => matchar(p, filter)), [prospekt, filter]);

  async function bytStatus(id: string, status: string) {
    const forra = prospekt?.find((p) => p.id === id)?.status;
    if (!forra || forra === status) return;
    setProspekt((rader) => rader?.map((p) => (p.id === id ? { ...p, status } : p)) ?? null);
    const namn = prospekt?.find((p) => p.id === id)?.company_name ?? "";
    setMeddelande(`${namn}: ${text(T.statusAndrad)} ${text(STATUS_ETIKETT[status] ?? { sv: status, en: status })}`);
    setFokusId(id);
    if (demo) return;
    setNotis(null);
    try {
      await leadsAnrop(`/leads/prospects/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      setProspekt((rader) =>
        rader?.map((p) => (p.id === id ? { ...p, senaste_handelse_at: new Date().toISOString() } : p)) ?? null
      );
    } catch (orsak) {
      setProspekt((rader) => rader?.map((p) => (p.id === id ? { ...p, status: forra } : p)) ?? null);
      setNotis(`${text(T.statusSparadesInte)}: ${felmeddelande(orsak)}`);
    }
  }

  async function sparaVy() {
    const namn = vyNamn.trim();
    if (!namn || demo) return;
    setSparar(true);
    setNotis(null);
    try {
      const svar = await leadsAnrop<{ vy: Vy }>("/leads/vyer", {
        method: "POST",
        body: JSON.stringify({ namn, filter: rensat(filter) })
      });
      setVyer((forra) => [...forra, svar.vy]);
      setVyNamn("");
    } catch (orsak) {
      setNotis(felmeddelande(orsak));
    } finally {
      setSparar(false);
    }
  }

  async function raderaVy(id: string) {
    const forra = vyer;
    setVyer((v) => v.filter((x) => x.id !== id));
    try {
      await leadsAnrop(`/leads/vyer/${id}`, { method: "DELETE" });
    } catch (orsak) {
      setVyer(forra);
      setNotis(felmeddelande(orsak));
    }
  }

  if (ejAktiverad) return <EjAktiverad yta={text(T.tabell)} />;
  if (fel) {
    return (
      <div>
        <p role="alert" className="text-[15px] text-danger">
          {text(T.hamtaFel)} {fel}
        </p>
        <button type="button" onClick={() => void hamta()} className={cn(btnSecondary, "mt-4")}>
          {text(T.forsokIgen)}
        </button>
      </div>
    );
  }
  if (prospekt === null) return <SkeletonRows />;
  if (prospekt.length === 0) return <Tomt>{text(T.tomt)}</Tomt>;

  const aktivtFilter = JSON.stringify(rensat(filter));

  const statusVal = (p: SuiteProspekt) => (
    <select
      id={`leads-status-${p.id}`}
      value={p.status}
      onChange={(e) => void bytStatus(p.id, e.target.value)}
      aria-label={`${text(T.statusFor)} ${p.company_name}`}
      className={cn(faltDiskret, "w-full")}
    >
      {STATUS_ORDNING.map((s) => (
        <option key={s} value={s}>
          {text(STATUS_ETIKETT[s])}
        </option>
      ))}
      {STATUS_ORDNING.includes(p.status as (typeof STATUS_ORDNING)[number]) ? null : (
        <option value={p.status}>{p.status}</option>
      )}
    </select>
  );

  const bolag = (p: SuiteProspekt) =>
    onValj ? (
      <button
        type="button"
        onClick={() => onValj(p.id)}
        className="focus-ring -mx-1 inline-flex min-h-8 items-center rounded-input px-1 text-left font-medium decoration-ink/40 underline-offset-4 hover:underline"
      >
        {p.company_name}
      </button>
    ) : (
      <span className="font-semibold">{p.company_name}</span>
    );

  const uppgiftText = (p: SuiteProspekt) => {
    const u = nastaUppgift.get(p.id);
    if (!u) return <span className={meta}>{text(T.ingenUppgift)}</span>;
    return (
      <>
        <span className="block break-words">{u.titel}</span>
        {u.forfaller ? (
          <span className={meta}>
            {new Date(`${u.forfaller}T00:00:00`).toLocaleDateString(datumFormat(locale), { day: "numeric", month: "short" })}
          </span>
        ) : null}
      </>
    );
  };

  const kontaktChip = (p: SuiteProspekt) => {
    const vag = kontaktvagAv(p);
    return <Badge tone={vag === "saknas" ? "warn" : vag === "bada" ? "good" : "neutral"}>{text(KONTAKT_ETIKETT[vag])}</Badge>;
  };

  return (
    <div className="space-y-6">
      {vyer.length || !demo ? (
        <div>
          <p className={etikett}>{text(T.vyer)}</p>
          <ul className={cn("mt-2", chiplista)}>
            <li>
              <button
                type="button"
                aria-pressed={aktivtFilter === "{}"}
                onClick={() => setFilter({})}
                className={cn(chip, aktivtFilter === "{}" ? chipAktiv : chipInaktiv)}
              >
                {text(T.alla)}
              </button>
            </li>
            {vyer.map((vy) => {
              const aktiv = aktivtFilter === JSON.stringify(rensat(vy.filter ?? {}));
              return (
                <li key={vy.id} className="inline-flex items-center gap-1">
                  <button
                    type="button"
                    aria-pressed={aktiv}
                    onClick={() => setFilter(rensat(vy.filter ?? {}))}
                    className={cn(chip, aktiv ? chipAktiv : chipInaktiv)}
                  >
                    {vy.namn}
                  </button>
                  {demo ? null : (
                    <button
                      type="button"
                      onClick={() => void raderaVy(vy.id)}
                      aria-label={text({ sv: `Radera vyn ${vy.namn}`, en: `Delete the view ${vy.namn}` })}
                      className="focus-ring inline-flex h-8 w-8 items-center justify-center rounded-full text-ink-muted hover:bg-paper2 hover:text-ink"
                    >
                      <X className="h-4 w-4" aria-hidden />
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      <div className="flex flex-wrap items-end gap-2">
        <label className={cn(etikett, "flex flex-col gap-1")}>
          {text(T.filterStatus)}
          <select
            id="leads-filter-status"
            value={filter.status ?? ""}
            onChange={(e) => setFilter((f) => ({ ...f, status: e.target.value }))}
            className={faltKlass}
          >
            <option value="">{text(T.alla)}</option>
            {STATUS_ORDNING.map((s) => (
              <option key={s} value={s}>
                {text(STATUS_ETIKETT[s])}
              </option>
            ))}
          </select>
        </label>
        <label className={cn(etikett, "flex flex-col gap-1")}>
          {text(T.filterNiva)}
          <select
            value={filter.niva ?? ""}
            onChange={(e) => setFilter((f) => ({ ...f, niva: e.target.value }))}
            className={faltKlass}
          >
            <option value="">{text(T.alla)}</option>
            {(["A", "B", "C"] as const).map((n) => (
              <option key={n} value={n}>
                {nivaEtikett(n, locale)}
              </option>
            ))}
          </select>
        </label>
        <label className={cn(etikett, "flex flex-col gap-1")}>
          {text(T.filterTyp)}
          <select
            value={filter.typ ?? ""}
            onChange={(e) => setFilter((f) => ({ ...f, typ: e.target.value }))}
            className={faltKlass}
          >
            <option value="">{text(T.alla)}</option>
            {TYPER.map((t) => (
              <option key={t} value={t}>
                {text(LEAD_TYP_ETIKETT[t])}
              </option>
            ))}
          </select>
        </label>
        <label className={cn(etikett, "flex min-w-[200px] flex-1 flex-col gap-1")}>
          {text(T.filterSok)}
          <input
            type="search"
            value={filter.sok ?? ""}
            onChange={(e) => setFilter((f) => ({ ...f, sok: e.target.value }))}
            placeholder={text(T.sokPlaceholder)}
            className={faltKlass}
          />
        </label>
      </div>

      {demo ? null : (
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            void sparaVy();
          }}
        >
          <label className={cn(etikett, "flex min-w-[200px] flex-1 flex-col gap-1 sm:max-w-xs")}>
            {text(T.vyNamn)}
            <input
              value={vyNamn}
              onChange={(e) => setVyNamn(e.target.value)}
              placeholder={text(T.vyPlaceholder)}
              maxLength={80}
              className={faltKlass}
            />
          </label>
          <button type="submit" disabled={sparar || !vyNamn.trim()} className={cn(btnSecondary, btnLiten)}>
            {sparar ? text(T.sparar) : text(T.sparaVy)}
          </button>
        </form>
      )}

      {notis ? (
        <p role="alert" className="text-[15px] text-danger">
          {notis}
        </p>
      ) : null}
      <p role="status" className="sr-only">
        {meddelande}
      </p>

      {synliga.length === 0 ? (
        <Tomt>{text(T.ingaTraffar)}</Tomt>
      ) : (
        <>
          <div className="hidden md:block">
            <Tabell
              ariaLabel={text(T.tabell)}
              minBredd={960}
              kolumner={[
                { rubrik: text(T.kolBolag), bredd: "20%" },
                { rubrik: text(T.kolStatus), bredd: "16%" },
                { rubrik: text(T.kolNiva), bredd: "8%" },
                { rubrik: text(T.kolPoang), bredd: "6%", hoger: true },
                { rubrik: text(T.kolKontakt), bredd: "10%" },
                { rubrik: text(T.kolSenaste), bredd: "16%" },
                { rubrik: text(T.kolUppgift), bredd: "14%" },
                { rubrik: text(T.kolTyp) }
              ]}
            >
              {synliga.map((p) => (
                <tr key={p.id} className={tabellRad}>
                  <Cell titel>{bolag(p)}</Cell>
                  <Cell>{statusVal(p)}</Cell>
                  <Cell>{p.niva ? nivaEtikett(p.niva, locale) : ""}</Cell>
                  <Cell hoger>{poangAv(p)}</Cell>
                  <Cell>{kontaktChip(p)}</Cell>
                  <Cell className="truncate whitespace-nowrap text-ink-muted">{relativTid(p.senaste_handelse_at ?? p.created_at, locale)}</Cell>
                  <Cell>{uppgiftText(p)}</Cell>
                  <Cell className="text-ink-muted">{text(LEAD_TYP_ETIKETT[leadTyp(p.origin)])}</Cell>
                </tr>
              ))}
            </Tabell>
          </div>

          <ul className="space-y-3 md:hidden" aria-label={text(T.tabell)}>
            {synliga.map((p) => (
              <li key={p.id} className="rounded-card border border-ink/12 bg-paper2/40 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">{bolag(p)}</div>
                  <span className="num shrink-0 tabular-nums">{poangAv(p)}</span>
                </div>
                <p className={cn(meta, "mt-1")}>
                  {[
                    p.niva ? nivaEtikett(p.niva, locale) : null,
                    text(LEAD_TYP_ETIKETT[leadTyp(p.origin)]),
                    relativTid(p.senaste_handelse_at ?? p.created_at, locale)
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
                <div className="mt-3">{statusVal(p)}</div>
                <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
                  {kontaktChip(p)}
                  <div className="min-w-0 text-right text-[15px]">{uppgiftText(p)}</div>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
