"use client";

import { X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { EjAktiverad } from "@/components/EjAktiverad";
import { Badge, Cell, SkeletonRows, Tabell, Tomt, btnSecondary, etikett, btnLiten, faltDiskret, faltTatt, chip, chipAktiv, chipInaktiv, chiplista, meta, tabellRad } from "@/components/ui";
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
 * Leads › Leads (plan 2026-10-05, fas 4): EN vy i full bredd i stället för
 * tre (Alla leads, Tabell, Pipeline). Antons beställning: alla datapunkter på
 * ett ställe, en enkel statusmarkering i stället för pipelinen, och leadsen
 * över hela ytan i stället för en halv sida "Välj ett lead i listan".
 *
 * - Statusremsan överst är pipelinen i kompakt form: varje steg är en räknare
 *   som filtrerar listan.
 * - Varje rad bär bolaget, motiveringens första mening, status (byts direkt,
 *   PATCH, återställs om sparningen faller), poäng och nivå, webbbetyget ur
 *   webbrevisionen, kontaktväg, senaste händelse, nästa uppgift och typ.
 * - Klick på bolaget öppnar detaljen (Bedömning, Mejlutkast, Tidslinje) i en
 *   låda från höger — det ägs av IrisBolag via `onValj`.
 * - Bortvalda (nivå C) ligger bakom en växel: de är Iris arbete, inte leverans.
 */

const T = {
  tabell: { sv: "Leads", en: "Leads" },
  hamtaFel: { sv: "Leads kunde inte hämtas.", en: "The leads could not be loaded." },
  forsokIgen: { sv: "Försök igen", en: "Try again" },
  tomt: { sv: "Inga leads ännu. Kör Iris eller importera en lista.", en: "No leads yet. Run Iris or import a list." },
  ingaTraffar: { sv: "Inga leads matchar filtret.", en: "No leads match the filter." },
  kolBolag: { sv: "Bolag", en: "Company" },
  kolStatus: { sv: "Status", en: "Status" },
  kolPoang: { sv: "Poäng", en: "Score" },
  kolWebb: { sv: "Webbplats", en: "Website" },
  kolKontakt: { sv: "Kontaktväg", en: "Contact" },
  kolSenaste: { sv: "Senaste händelse", en: "Last event" },
  kolUppgift: { sv: "Nästa uppgift", en: "Next task" },
  kolTyp: { sv: "Typ", en: "Type" },
  filterNiva: { sv: "Nivå", en: "Tier" },
  filterTyp: { sv: "Typ", en: "Type" },
  filterSok: { sv: "Sök", en: "Search" },
  sokPlaceholder: { sv: "Bolag eller kontakt", en: "Company or contact" },
  alla: { sv: "Alla", en: "All" },
  pipeline: { sv: "Status", en: "Status" },
  vyer: { sv: "Sparade vyer", en: "Saved views" },
  vyNamn: { sv: "Namn på vyn", en: "View name" },
  vyPlaceholder: { sv: "Heta leads i Göteborg", en: "Hot leads in Gothenburg" },
  sparaVy: { sv: "Spara vy", en: "Save view" },
  sparar: { sv: "Sparar…", en: "Saving…" },
  statusSparadesInte: { sv: "Statusen sparades inte", en: "The status was not saved" },
  bortvalda: { sv: "Bortvalda", en: "Dropped" },
  bortvaldaRubrik: { sv: "Bortvalda bolag", en: "Dropped companies" },
  bortvaldaText: {
    sv: "Bolag Iris valde bort för att de inte uppfyller kraven. Inget är raderat: de står kvar här och nästa sökning hoppar över dem. Radera går bara att göra inne på bolaget.",
    en: "Companies Iris dropped because they do not meet the requirements. Nothing is deleted: they stay here and the next search skips them. Deleting is only done on the company itself."
  },
  bortvaldaTomt: { sv: "Inga bortvalda bolag.", en: "No dropped companies." },
  bortvaldaFel: { sv: "De bortvalda bolagen kunde inte hämtas.", en: "The dropped companies could not be loaded." },
  bortvald: { sv: "Bortvald", en: "Dropped" },
  sidodata: {
    sv: "Uppgifter eller sparade vyer kunde inte hämtas",
    en: "Tasks or saved views could not be loaded"
  },
  ingenUppgift: { sv: "Ingen", en: "None" },
  statusFor: { sv: "Status för", en: "Status for" },
  statusAndrad: { sv: "Status ändrad till", en: "Status changed to" },
  exempel: { sv: "Exempel", en: "Example" },
  researchar: { sv: "Researchar", en: "Researching" },
  oppna: { sv: "Öppna", en: "Open" },
  modernitet: { sv: "Modernitet", en: "Modernity" }
} satisfies Record<string, Localized>;

const KONTAKT_ETIKETT: Record<Kontaktvag, Localized> = {
  bada: { sv: "Tel och mejl", en: "Phone and email" },
  telefon: { sv: "Tel", en: "Phone" },
  mejl: { sv: "Mejl", en: "Email" },
  saknas: { sv: "Saknas", en: "Missing" }
};

const TYPER: LeadTyp[] = ["iris", "lista", "import", "inkorg"];

/** Stegen i remsan: arbetsflödets ordning, utan Spärrad (den har egen väg). */
const REMSA = STATUS_ORDNING.filter((s) => s !== "suppressed");

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

function domanAv(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    return new URL(url.startsWith("http") ? url : `https://${url}`).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** Motiveringens första mening: raden ska gå att skumma, detaljen bär resten. */
function forstaMening(p: SuiteProspekt): string | null {
  const text = p.motivering ?? p.disqualifiers?.[0] ?? null;
  if (!text) return null;
  const slut = text.search(/[.!?](\s|$)/);
  return slut > 0 ? text.slice(0, slut + 1) : text;
}

/** Researchen är köad eller pågår: raden finns men är inte bedömd än. */
function researchPagar(p: SuiteProspekt): boolean {
  return p.origin !== "example" && !p.niva && p.score_total == null && p.icp_fit == null;
}

/** Nyaste överst — exemplen först. Sorteringen på nivå och poäng lade nya
 *  leads mitt i listan (Antons krav 2026-10-06). */
function sortera(rader: SuiteProspekt[]): SuiteProspekt[] {
  const rang = (p: SuiteProspekt) => (p.origin === "example" ? 0 : 1);
  return [...rader].sort((a, b) => rang(a) - rang(b) || (b.created_at ?? "").localeCompare(a.created_at ?? ""));
}

export function LeadsTabell({
  onValj,
  valdId = null,
  exempel = [],
  demo = false
}: Readonly<{
  onValj?: (id: string) => void;
  /** Leadet vars låda är öppen: raden markeras. */
  valdId?: string | null;
  /** Demons exempelbolag, överst i listan. */
  exempel?: SuiteProspekt[];
  demo?: boolean;
}>) {
  const { locale, text } = useLocale();
  const [prospekt, setProspekt] = useState<SuiteProspekt[] | null>(null);
  const [uppgifter, setUppgifter] = useState<Uppgift[]>([]);
  const [vyer, setVyer] = useState<Vy[]>([]);
  const [fel, setFel] = useState<string | null>(null);
  const [ejAktiverad, setEjAktiverad] = useState(false);
  const [notis, setNotis] = useState<string | null>(null);
  const [meddelande, setMeddelande] = useState<string | null>(null);
  const [fokusId, setFokusId] = useState<string | null>(null);
  const [sparaOppen, setSparaOppen] = useState(false);

  // Raden kan lämna filtret efter statusbytet: fokus till samma select om den
  // finns kvar efter commit, annars till remsans Alla (2.4.3).
  useEffect(() => {
    if (fokusId) (document.getElementById(`leads-status-${fokusId}`) ?? document.getElementById("leads-remsa-alla"))?.focus();
  }, [fokusId, prospekt]);
  const [filter, setFilter] = useState<VyFilter>({});
  // Bortvalda (nivå C): dolda som standard (Antons krav), nåbara på begäran
  // (Sebbes krav: inget får se ut som raderat). Hämtas först vid klick.
  const [visaBortvalda, setVisaBortvalda] = useState(false);
  const [bortvalda, setBortvalda] = useState<SuiteProspekt[] | null>(null);
  const [bortvaldaFel, setBortvaldaFel] = useState<string | null>(null);
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

  // En pågående körning (Kör Iris) lägger till rader medan man tittar.
  useEffect(() => {
    const uppdatera = () => void hamta();
    window.addEventListener("snipra:leads-korning-steg", uppdatera);
    window.addEventListener("snipra:leads-korning-klar", uppdatera);
    return () => {
      window.removeEventListener("snipra:leads-korning-steg", uppdatera);
      window.removeEventListener("snipra:leads-korning-klar", uppdatera);
    };
  }, [hamta]);

  const nastaUppgift = useMemo(() => {
    // Backenden sorterar förfallodatum stigande med null sist: första öppna per prospekt vinner.
    const karta = new Map<string, Uppgift>();
    for (const u of uppgifter) if (!u.klar && !karta.has(u.prospect_id)) karta.set(u.prospect_id, u);
    return karta;
  }, [uppgifter]);

  const allaRader = useMemo(() => sortera([...exempel, ...(prospekt ?? [])]), [exempel, prospekt]);
  // Bortvalda bolag når aldrig listan: API:t lämnar bara leads som uppfyller
  // kraven (snajp-support/app/api/leads.py, list_prospects).
  const urval = allaRader;
  const synliga = useMemo(() => urval.filter((p) => matchar(p, filter)), [urval, filter]);
  const harWebb = synliga.some((p) => typeof p.webbrevision?.modernitet === "number");
  const perStatus = useMemo(() => {
    const karta = new Map<string, number>();
    for (const p of urval) if (matchar(p, { ...filter, status: undefined })) karta.set(p.status, (karta.get(p.status) ?? 0) + 1);
    return karta;
  }, [urval, filter]);

  async function vaxlaBortvalda() {
    const nu = !visaBortvalda;
    setVisaBortvalda(nu);
    if (!nu || bortvalda !== null || demo) return;
    setBortvaldaFel(null);
    try {
      const svar = await leadsAnrop<{ prospects?: SuiteProspekt[] }>("/leads/prospects?bortvalda=1");
      setBortvalda(sortera(svar.prospects ?? []));
    } catch (orsak) {
      setBortvaldaFel(felmeddelande(orsak));
      setBortvalda([]);
    }
  }

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
      setSparaOppen(false);
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
  if (prospekt === null && exempel.length === 0) return <SkeletonRows />;
  if (allaRader.length === 0) return <Tomt>{text(T.tomt)}</Tomt>;

  const aktivtFilter = JSON.stringify(rensat(filter));

  const statusVal = (p: SuiteProspekt) =>
    p.origin === "example" ? (
      <span className="text-ink-muted">{text(STATUS_ETIKETT[p.status] ?? { sv: p.status, en: p.status })}</span>
    ) : (
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

  const bolag = (p: SuiteProspekt) => {
    const doman = domanAv(p.website);
    const motivering = forstaMening(p);
    return (
      <div className="min-w-0">
        <div className="flex flex-wrap items-baseline gap-x-2">
          {onValj ? (
            <button
              type="button"
              id={`iris-rad-${p.id}`}
              onClick={() => onValj(p.id)}
              aria-label={`${text(T.oppna)} ${p.company_name}`}
              className="focus-ring -mx-1 rounded-input px-1 text-left font-semibold decoration-ink/40 underline-offset-4 hover:underline"
            >
              {p.company_name}
            </button>
          ) : (
            <span className="font-semibold">{p.company_name}</span>
          )}
          {p.origin === "example" ? <Badge>{text(T.exempel)}</Badge> : null}
        </div>
        {p.ort || doman ? <p className={cn(meta, "mt-0.5 truncate")}>{[p.ort, doman].filter(Boolean).join(" · ")}</p> : null}
        {motivering ? (
          <p className="mt-1 line-clamp-2 max-w-[70ch] text-[0.875rem] leading-6 text-ink-muted">{motivering}</p>
        ) : null}
      </div>
    );
  };

  const poangCell = (p: SuiteProspekt) =>
    researchPagar(p) ? (
      <span className={meta}>{text(T.researchar)}</span>
    ) : (
      <span className="inline-flex flex-col items-end leading-tight">
        <span className="num font-semibold tabular-nums">{poangAv(p)}</span>
        {p.niva ? (
          <span className={cn("text-[0.75rem]", p.niva === "C" ? "text-danger" : "text-ink-subtle")}>
            {nivaEtikett(p.niva, locale)}
          </span>
        ) : null}
      </span>
    );

  const webbCell = (p: SuiteProspekt) => {
    const m = p.webbrevision?.modernitet;
    if (typeof m !== "number") return null;
    const brist = p.webbrevision?.brister?.[0];
    return (
      <span className="inline-flex flex-col gap-1" title={brist ?? undefined}>
        <Badge tone={m <= 4 ? "good" : m >= 7 ? "neutral" : "warn"}>
          <span className="sr-only">{text(T.modernitet)} </span>
          {m}/10
        </Badge>
        {brist ? <span className={cn(meta, "line-clamp-1 max-w-[18ch]")}>{brist}</span> : null}
      </span>
    );
  };

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
    <div className="space-y-5">
      {/* Statusremsan: pipelinen som räknare. Ett klick filtrerar, ett till släpper. */}
      <nav aria-label={text(T.pipeline)} className="-mx-1 overflow-x-auto px-1">
        <ul className="flex min-w-max gap-1.5">
          <li>
            <button
              type="button"
              id="leads-remsa-alla"
              aria-pressed={!filter.status}
              onClick={() => setFilter((f) => ({ ...f, status: undefined }))}
              className={cn(chip, !filter.status ? chipAktiv : chipInaktiv)}
            >
              {text(T.alla)} <span className="num ml-1 tabular-nums opacity-70">{urval.filter((p) => matchar(p, { ...filter, status: undefined })).length}</span>
            </button>
          </li>
          {REMSA.map((s) => {
            const antal = perStatus.get(s) ?? 0;
            const aktiv = filter.status === s;
            return (
              <li key={s}>
                <button
                  type="button"
                  aria-pressed={aktiv}
                  onClick={() => setFilter((f) => ({ ...f, status: aktiv ? undefined : s }))}
                  className={cn(chip, aktiv ? chipAktiv : chipInaktiv, antal === 0 && !aktiv && "text-ink-subtle")}
                >
                  {text(STATUS_ETIKETT[s])} <span className="num ml-1 tabular-nums opacity-70">{antal}</span>
                </button>
              </li>
            );
          })}
          <li>
            <button
              type="button"
              aria-pressed={visaBortvalda}
              onClick={() => void vaxlaBortvalda()}
              className={cn(chip, visaBortvalda ? chipAktiv : chipInaktiv)}
            >
              {text(T.bortvalda)}
              {bortvalda !== null ? (
                <span className="num ml-1 tabular-nums opacity-70">{bortvalda.length}</span>
              ) : null}
            </button>
          </li>
        </ul>
      </nav>

      <div className="flex flex-wrap items-end gap-2">
        <label className={cn(etikett, "flex flex-col gap-1")}>
          {text(T.filterNiva)}
          <select
            value={filter.niva ?? ""}
            onChange={(e) => setFilter((f) => ({ ...f, niva: e.target.value }))}
            className={faltTatt}
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
            className={faltTatt}
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
            className={faltTatt}
          />
        </label>
      </div>

      {vyer.length || !demo ? (
        <div className="flex flex-wrap items-center gap-2">
          <span className={etikett}>{text(T.vyer)}</span>
          <ul className={chiplista}>
            {vyer.map((vy) => {
              const aktiv = aktivtFilter === JSON.stringify(rensat(vy.filter ?? {}));
              return (
                <li key={vy.id} className="inline-flex items-center gap-1">
                  <button
                    type="button"
                    aria-pressed={aktiv}
                    onClick={() => setFilter(aktiv ? {} : rensat(vy.filter ?? {}))}
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
          {demo ? null : sparaOppen ? (
            <form
              className="flex flex-wrap items-center gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                void sparaVy();
              }}
            >
              <label className="sr-only" htmlFor="leads-vy-namn">
                {text(T.vyNamn)}
              </label>
              <input
                id="leads-vy-namn"
                value={vyNamn}
                onChange={(e) => setVyNamn(e.target.value)}
                placeholder={text(T.vyPlaceholder)}
                maxLength={80}
                autoFocus
                className={cn(faltTatt, "w-56")}
              />
              <button type="submit" disabled={sparar || !vyNamn.trim()} className={cn(btnSecondary, btnLiten)}>
                {sparar ? text(T.sparar) : text(T.sparaVy)}
              </button>
            </form>
          ) : (
            <button
              type="button"
              onClick={() => setSparaOppen(true)}
              className="focus-ring text-[0.8125rem] text-ink-muted underline decoration-ink/25 underline-offset-4 hover:text-ink"
            >
              {text(T.sparaVy)}
            </button>
          )}
        </div>
      ) : null}

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
          <div className="hidden lg:block">
            <Tabell
              ariaLabel={text(T.tabell)}
              minBredd={1040}
              kolumner={[
                { rubrik: text(T.kolBolag), bredd: harWebb ? "32%" : "38%" },
                { rubrik: text(T.kolStatus), bredd: "13%" },
                { rubrik: text(T.kolPoang), bredd: "7%", hoger: true },
                // Webbkolumnen bara när någon rad har ett betyg (webbrevisionen):
                // en tom kolumn är bredd utan information.
                ...(harWebb ? [{ rubrik: text(T.kolWebb), bredd: "11%" }] : []),
                { rubrik: text(T.kolKontakt), bredd: "9%" },
                { rubrik: text(T.kolSenaste), bredd: "11%" },
                { rubrik: text(T.kolUppgift), bredd: "10%" },
                { rubrik: text(T.kolTyp) }
              ]}
            >
              {synliga.map((p) => (
                <tr key={p.id} className={cn(tabellRad, "align-top", p.id === valdId && "bg-ochre/10")}>
                  <Cell titel>{bolag(p)}</Cell>
                  <Cell>{statusVal(p)}</Cell>
                  <Cell hoger>{poangCell(p)}</Cell>
                  {harWebb ? <Cell>{webbCell(p)}</Cell> : null}
                  <Cell>{kontaktChip(p)}</Cell>
                  <Cell className="text-ink-muted">{relativTid(p.senaste_handelse_at ?? p.created_at, locale)}</Cell>
                  <Cell>{uppgiftText(p)}</Cell>
                  <Cell className="text-ink-muted">{text(LEAD_TYP_ETIKETT[leadTyp(p.origin)])}</Cell>
                </tr>
              ))}
            </Tabell>
          </div>

          <ul className="space-y-3 lg:hidden" aria-label={text(T.tabell)}>
            {synliga.map((p) => (
              <li key={p.id} className={cn("rounded-card border border-ink/12 bg-paper2/40 p-4", p.id === valdId && "border-ochre/50")}>
                <div className="flex items-start justify-between gap-3">
                  {bolag(p)}
                  <div className="shrink-0 text-right">{poangCell(p)}</div>
                </div>
                <div className="mt-3 grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
                  <div>{statusVal(p)}</div>
                  <div className="flex flex-wrap items-start justify-end gap-2">
                    {webbCell(p)}
                    {kontaktChip(p)}
                  </div>
                </div>
                <p className={cn(meta, "mt-3")}>
                  {[text(LEAD_TYP_ETIKETT[leadTyp(p.origin)]), relativTid(p.senaste_handelse_at ?? p.created_at, locale)]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </li>
            ))}
          </ul>
        </>
      )}

      {/* ------------------------------------------ BORTVALDA (nivå C) */}
      {visaBortvalda ? (
        <section aria-labelledby="leads-bortvalda" className="rounded-card border border-ink/12 bg-paper2/40 p-4 sm:p-5">
          <h3 id="leads-bortvalda" className="text-[1rem] font-semibold">
            {text(T.bortvaldaRubrik)}
          </h3>
          <p className="mt-1 max-w-[72ch] text-[14px] leading-6 text-ink-subtle">{text(T.bortvaldaText)}</p>
          {bortvaldaFel ? (
            <p role="alert" className="mt-3 text-[14px] text-danger">
              {bortvaldaFel}
            </p>
          ) : bortvalda === null ? (
            <div className="mt-4">
              <SkeletonRows />
            </div>
          ) : bortvalda.length === 0 ? (
            <p className={cn(meta, "mt-3")}>{text(T.bortvaldaTomt)}</p>
          ) : (
            <ul className="mt-3 divide-y divide-ink/10">
              {bortvalda.map((p) => (
                <li key={p.id} className="py-2.5">
                  <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                    <button
                      type="button"
                      onClick={() => onValj?.(p.id)}
                      className="focus-ring min-w-0 truncate text-left text-[0.9375rem] font-medium text-ink-muted underline-offset-4 hover:text-ink hover:underline"
                    >
                      {p.company_name}
                    </button>
                    <span className="flex shrink-0 items-center gap-2">
                      <Badge tone="warn">{text(T.bortvald)}</Badge>
                      <span className={meta}>{relativTid(p.senaste_handelse_at ?? p.created_at, locale)}</span>
                    </span>
                  </div>
                  {(p.disqualifiers?.[0] || p.motivering) ? (
                    <p className={cn(meta, "mt-0.5 max-w-[80ch]")}>{p.disqualifiers?.[0] ?? p.motivering}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}
    </div>
  );
}
