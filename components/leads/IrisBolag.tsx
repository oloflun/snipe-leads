"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { PageShell, useArbetsvag } from "@/components/AppShell";
import { EjAktiverad, arEjAktiverad } from "@/components/EjAktiverad";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { LeadslistorView } from "@/components/leads/LeadslistorView";
import { LeadsRunForm } from "@/components/leads/LeadsRunForm";
import {
  Badge,
  Nyckeltal,
  Radlista,
  Sektion,
  SkeletonRows,
  Tomt,
  btnLiten,
  btnPrimary,
  btnSecondary,
  etikett,
  flik,
  flikAktiv,
  flikInaktiv,
  meta,
  rubrikPanel
} from "@/components/ui";
import { mejlaOss } from "@/components/marketing/copy";
import { addonSpec } from "@/lib/addons";
import { lasOffertForUtkast } from "@/lib/actions/affarskontext";
import type { EmailStudioData } from "@/lib/data/emails";
import { demoOversiktSvar } from "@/lib/demo/oversikt";
import { EXEMPELBOLAG, EXEMPEL_OMGANG_1, EXEMPEL_OMGANG_2, kontaktnamn, type ExempelBolag } from "@/lib/demo/iris-exempel";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { GRANSER } from "@/lib/iris";
import { kriterier } from "@/lib/prospekt";
import { cn } from "@/lib/utils";

/**
 * Iris › Bolag — leadslistan och prospektdetaljerna på samma sida, ersätter
 * den tidigare uppdelningen mellan Discovery (körformuläret), Bolagsregister
 * (tabellen) och Bolagssida (en egen undersida per prospekt).
 *
 * ## Master/detalj, inte tre sidor
 *
 * Ett klick på en rad väljer prospektet och fyller detaljpanelen till höger
 * (≥lg) eller under listan (mindre skärmar) — samma mönster som
 * `components/crm/CrmDemo.tsx`. Ingen navigering till en egen URL: det är
 * det som gör raden klickbar även i demon, där en sida bakom inloggning
 * tidigare stoppade klicket (se `components/leads/Bolagsregister.tsx`s
 * gamla `demo ? <span> : <Link>`-gren).
 *
 * ## Exempelbolagen
 *
 * "Kör exempelkörningen" i den utfällda panelen lägger de sex fixturbolagen
 * ur `lib/demo/iris-exempel.ts` överst i den RIKTIGA listan, märkta Exempel —
 * inte i en egen, fristående resultatlista. Källan är medvetet den handskrivna
 * fixturen (bolag, signal, utkast) och inte `lib/demo/leads-korning.ts`, som
 * hör till en annan, äldre demoyta.
 */

type Prospekt = {
  id: string;
  company_name: string;
  contact_name: string | null;
  contact_email: string | null;
  status: string;
  origin?: string | null;
  ort: string | null;
  sni: string | null;
  website: string | null;
  orgnr: string | null;
  anstallda?: number | null;
  score_total: number | null;
  icp_fit: number | null;
  qualified: boolean | null;
  disqualifiers: string[] | null;
  score_breakdown: unknown;
};

type ExempelRad = Prospekt & { _exempel: ExempelBolag };

type ListLage =
  | { fas: "laddar" }
  | { fas: "ejAktiverad" }
  | { fas: "fel"; meddelande: string }
  | { fas: "klar"; prospekt: Prospekt[] };

const STATUS_ETIKETT: Record<string, string> = {
  new: "Ny",
  researching: "Research pågår",
  ready: "Redo",
  contacted: "Kontaktad",
  replied: "Svarat",
  meeting: "Möte",
  won: "Vunnen",
  lost: "Förlorad",
  suppressed: "Spärrad"
};

/** Status som betyder att något väntar på kunden — samma urval som Bolagsregistret. */
const AKTIV_STATUS = new Set(["ready", "replied", "meeting"]);

function domanAv(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    return new URL(url.startsWith("http") ? url : `https://${url}`).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** Meta-raden under bolagsnamnet. Tom sträng = ingen rad, aldrig ett streck. */
function segment(p: Prospekt): string {
  return [p.orgnr, p.ort, domanAv(p.website)].filter(Boolean).join(" · ");
}

function beskrivning(p: Prospekt): string | null {
  const träff = kriterier(p.score_breakdown).find((k) => k.motivering && k.utfall !== "saknas");
  return träff?.motivering ?? (p.disqualifiers?.[0] ?? null);
}

function beslutsfattareRad(p: Prospekt): string | null {
  if ("_exempel" in p) {
    const b = (p as ExempelRad)._exempel;
    return [
      `Beslutsfattare: ${kontaktnamn(b)}, ${b.contactRole}`,
      typeof b.anstallda === "number" ? `${b.anstallda} anställda` : null,
      b.bransch
    ]
      .filter(Boolean)
      .join(" · ");
  }
  return p.contact_name ? `Beslutsfattare: ${p.contact_name}` : null;
}

/** Samma brytpunkt som Tailwinds `lg` (1024px). Hela sidan är redan klientkod
 * och innan effekten hunnit köra spelar defaultvärdet ingen roll: inget är
 * valt förrän användaren klickar. */
function useDesktop(): boolean {
  const [desktop, setDesktop] = useState(true);
  useEffect(() => {
    const mql = window.matchMedia("(min-width: 1024px)");
    const uppdatera = () => setDesktop(mql.matches);
    uppdatera();
    mql.addEventListener("change", uppdatera);
    return () => mql.removeEventListener("change", uppdatera);
  }, []);
  return desktop;
}

/**
 * Poängen, eller null när ingen finns. Listraden utelämnar då talet helt —
 * ett ensamt streck ovanför statusen sa ingenting (skärmdump 2026-09-27) —
 * och detaljpanelen visar "–".
 */
function poang(p: Prospekt): string | null {
  if (typeof p.score_total === "number") return String(p.score_total);
  if (typeof p.icp_fit === "number") return String(Math.round(p.icp_fit * 100));
  return null;
}

/** "träff" → "Träff": brickor i versal/gemen som vanlig text. */
function versal(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Fixturbolaget som ett prospekt-format radlistan redan vet hur den ritar. */
function exempelTillRad(b: ExempelBolag): ExempelRad {
  return {
    id: b.id,
    company_name: b.companyName,
    contact_name: `${kontaktnamn(b)}, ${b.contactRole}`,
    contact_email: null,
    status: b.status,
    origin: "example",
    ort: b.ort,
    sni: b.bransch,
    website: b.website,
    orgnr: b.orgnr,
    anstallda: b.anstallda,
    score_total: b.score,
    icp_fit: null,
    qualified: true,
    disqualifiers: null,
    score_breakdown: [{ etikett: "Signal", utfall: "träff", motivering: b.beskrivning, hart: false }],
    _exempel: b
  };
}

export function IrisBolag({ demo = false }: Readonly<{ demo?: boolean }>) {
  const { addons, isDemo, vy } = useDashboard();
  const sokParams = useSearchParams();

  // Gammal adress /dashboard/leads/listor -> /dashboard/iris?vy=listor (se
  // WorkspaceSection.tsx) ska öppna på rätt segment, inte tyst landa på Bolag.
  const [segmentVal, setSegmentVal] = useState<"bolag" | "listor">(
    sokParams.get("vy") === "listor" ? "listor" : "bolag"
  );
  const [korOppen, setKorOppen] = useState(false);
  const [lage, setLage] = useState<ListLage>({ fas: "laddar" });
  const [exempelRader, setExempelRader] = useState<ExempelRad[]>([]);
  const [demoKorFas, setDemoKorFas] = useState<"vilar" | "kor">("vilar");
  const [valdId, setValdId] = useState<string | null>(null);
  const [oppnade, setOppnade] = useState<string[]>([]);
  const detaljRef = useRef<HTMLDivElement>(null);
  const listaRef = useRef<HTMLDivElement>(null);
  const isDesktop = useDesktop();

  const hamta = useCallback(async (tyst = false) => {
    if (!tyst) setLage({ fas: "laddar" });
    if (demo) {
      const svar = demoOversiktSvar("/leads/prospects") as { prospects?: Prospekt[] } | undefined;
      setLage({ fas: "klar", prospekt: svar?.prospects ?? [] });
      return;
    }
    try {
      const response = await fetch("/api/snajp-support/leads/prospects", { cache: "no-store" });
      if (response.status === 409) {
        const kropp = await readJsonBody<unknown>(response).catch(() => null);
        if (arEjAktiverad(response.status, kropp)) {
          setLage({ fas: "ejAktiverad" });
          return;
        }
      }
      if (!response.ok) {
        setLage({
          fas: "fel",
          meddelande:
            response.status >= 500
              ? "Tjänsten svarar inte just nu. Den vaknar ur viloläge och kan ta upp till en minut."
              : `Kunde inte hämta bolagen (status ${response.status}).`
        });
        return;
      }
      const kropp = await readJsonBody<{ prospects?: Prospekt[]; offline?: boolean }>(response);
      if (!kropp || kropp.offline) {
        setLage({ fas: "fel", meddelande: "Backenden svarade utan innehåll." });
        return;
      }
      setLage({ fas: "klar", prospekt: kropp.prospects ?? [] });
    } catch (error) {
      setLage({ fas: "fel", meddelande: felmeddelande(error) });
    }
  }, [demo]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  // Körningen (riktig eller exempel) stänger sin egen disclosure och lämnar
  // fokus/scrollen överst i listan när den är klar, så de infogade raderna
  // syns direkt i stället för att stå gömda bakom ett fortfarande öppet
  // formulär. En riktig körning håller panelen öppen ända tills den faktiskt
  // är klar — händelsen dispatchas först i slutet av LeadsRunForms kör().
  const avslutaKorning = useCallback(() => {
    setKorOppen(false);
    requestAnimationFrame(() => {
      listaRef.current?.focus();
      listaRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, []);

  useEffect(() => {
    const lyssna = () => {
      void hamta(true);
      avslutaKorning();
    };
    window.addEventListener("snipra:leads-korning-klar", lyssna);
    return () => window.removeEventListener("snipra:leads-korning-klar", lyssna);
  }, [hamta, avslutaKorning]);

  const alla = useMemo<Prospekt[]>(() => {
    if (lage.fas !== "klar") return exempelRader;
    return [...exempelRader, ...lage.prospekt];
  }, [lage, exempelRader]);

  function valjRad(id: string) {
    setOppnade((forr) => (forr.includes(id) ? forr : [...forr, id]));
    setValdId(id);
    if (!isDesktop) {
      requestAnimationFrame(() => detaljRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }));
    }
  }

  const allaExempelTillagda = exempelRader.length >= EXEMPELBOLAG.length;

  function korExempel() {
    if (demoKorFas === "kor" || allaExempelTillagda) return;
    setDemoKorFas("kor");
    window.setTimeout(() => {
      setExempelRader((forr) => {
        const redan = new Set(forr.map((r) => r.id));
        const kandidat = EXEMPEL_OMGANG_1.some((b) => !redan.has(b.id)) ? EXEMPEL_OMGANG_1 : EXEMPEL_OMGANG_2;
        const nya = kandidat.filter((b) => !redan.has(b.id)).map(exempelTillRad);
        return [...nya, ...forr];
      });
      setDemoKorFas("vilar");
      avslutaKorning();
    }, 650);
  }

  const harListaddon = addons.includes("leadlists");

  // Rubriken är undersidans namn, inte agentens: "Iris" står redan i railen
  // som förälder till Bolag/Granskning/Inställningar, och de två syskonen
  // heter efter sin undersida. Personaingressen (IRIS.persona) är struken
  // enligt F-016; att Iris aldrig skickar något utan granskning står i
  // gränslistan längst ner.
  return (
    <PageShell
      title="Bolag"
      action={
        <button
          type="button"
          aria-expanded={korOppen}
          onClick={() => setKorOppen((v) => !v)}
          className={btnPrimary}
        >
          Kör Iris
        </button>
      }
    >
      {korOppen ? (
        <div className="mb-10 rounded-card border border-ink/12 bg-paper2/40 p-5 md:p-6">
          <LeadsRunForm
            isTest={demo || isDemo || vy === "demo"}
            demo={demo}
            rubrik={
              <div>
                <h2 className={rubrikPanel}>Hitta bolag</h2>
                <p className="mt-1 text-[0.9375rem] text-ink-muted">
                  Lämna ett fält tomt för att använda er sparade målgrupp.
                </p>
              </div>
            }
            demoAction={
              // Hårlinje, inte ett kort i kortet: formuläret runt om är redan
              // den egna ytan.
              <div className="mt-6 border-t border-ink/12 pt-5">
                <p className="max-w-[65ch] text-[0.9375rem] leading-7 text-ink-muted">
                  Prova en färdiggenererad exempelkörning: bolagen läggs överst i listan nedan,
                  märkta Exempel. Ingen modell körs och inget skickas.
                </p>
                <button
                  type="button"
                  disabled={demoKorFas === "kor" || allaExempelTillagda}
                  onClick={korExempel}
                  className={cn(btnPrimary, "mt-4 whitespace-nowrap")}
                >
                  {demoKorFas === "kor" ? (
                    "Kör…"
                  ) : allaExempelTillagda ? (
                    <>
                      <span className="sm:hidden">Alla tillagda</span>
                      <span className="hidden sm:inline">Alla exempelbolag tillagda</span>
                    </>
                  ) : (
                    <>
                      <span className="sm:hidden">Kör exempel</span>
                      <span className="hidden sm:inline">Kör exempelkörningen</span>
                    </>
                  )}
                </button>
              </div>
            }
          />
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="Vy">
        <button
          type="button"
          role="tab"
          aria-selected={segmentVal === "bolag"}
          onClick={() => setSegmentVal("bolag")}
          className={cn(flik, segmentVal === "bolag" ? flikAktiv : flikInaktiv)}
        >
          Alla bolag
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={segmentVal === "listor"}
          onClick={() => setSegmentVal("listor")}
          className={cn(flik, segmentVal === "listor" ? flikAktiv : flikInaktiv)}
        >
          Listor
        </button>
      </div>

      <div className="mt-6">
        {segmentVal === "listor" ? (
          harListaddon || demo ? (
            <LeadslistorView />
          ) : (
            <ListorUpsell />
          )
        ) : (
          <div className="grid gap-8 lg:grid-cols-12 lg:items-start">
            <div
              ref={listaRef}
              tabIndex={-1}
              className={cn("min-w-0 outline-none", alla.length === 0 ? "lg:col-span-12" : "lg:col-span-5")}
            >
              {lage.fas === "laddar" && exempelRader.length === 0 ? (
                <SkeletonRows />
              ) : lage.fas === "ejAktiverad" ? (
                <EjAktiverad yta="Bolag" />
              ) : lage.fas === "fel" ? (
                <FelBox meddelande={lage.meddelande} onForsok={() => void hamta()} />
              ) : alla.length === 0 ? (
                // Ingen egen "Kör Iris" här: samma knapp står i sidhuvudet.
                <Tomt>Inga bolag ännu. Tryck Kör Iris och beskriv vilka ni söker.</Tomt>
              ) : (
                <Radlista>
                  {alla.map((p) => {
                    const vald = p.id === valdId;
                    const poangen = poang(p);
                    return (
                      <li key={p.id}>
                        <button
                          type="button"
                          onClick={() => valjRad(p.id)}
                          aria-current={vald ? "true" : undefined}
                          className={cn(
                            "focus-ring block w-full px-3 py-4 text-left transition-colors",
                            vald ? "bg-ochre/10" : "hover:bg-paper2/60"
                          )}
                        >
                          {/* Radens anatomi: rubrik → meta under → status/tal
                              till höger. Resonemanget klipps till två rader —
                              hela texten står i detaljpanelen, annars går
                              listan inte att skanna (Evolushi AB, nio rader). */}
                          <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className={rubrikPanel}>{p.company_name}</span>
                                {p.origin === "example" ? <Badge>Exempel</Badge> : null}
                              </div>
                              {segment(p) ? <p className={cn(meta, "mt-1 truncate")}>{segment(p)}</p> : null}
                            </div>
                            {p.origin !== "example" ? (
                              <div className="flex shrink-0 items-center gap-3">
                                {poangen ? (
                                  <span title="Poäng" className="num text-[1.0625rem] font-semibold">
                                    {poangen}
                                  </span>
                                ) : null}
                                <Badge tone={AKTIV_STATUS.has(p.status) ? "warn" : "neutral"}>
                                  {STATUS_ETIKETT[p.status] ?? p.status}
                                </Badge>
                              </div>
                            ) : null}
                          </div>
                          {beskrivning(p) ? (
                            <p className="mt-2 line-clamp-2 max-w-[65ch] text-[0.9375rem] leading-6 text-ink-muted">
                              {beskrivning(p)}
                            </p>
                          ) : null}
                          {beslutsfattareRad(p) ? (
                            <p className={cn(meta, "mt-2")}>{beslutsfattareRad(p)}</p>
                          ) : null}
                        </button>

                        {/* Under lg visas detaljen direkt under sin rad, inte
                            efter HELA listan. Samma instans som den sticky
                            kolumnen nedan skulle rendera, aldrig båda
                            samtidigt: `isDesktop` styr vilken av de två som
                            monterar LeadDetail (och därmed EmailStudioEditor)
                            för ett givet bolag. */}
                        {!isDesktop && oppnade.includes(p.id) ? (
                          <div
                            ref={vald ? detaljRef : undefined}
                            hidden={!vald}
                            className={vald ? "scroll-mt-6 px-3 pb-5" : undefined}
                          >
                            <LeadDetail
                              id={p.id}
                              demo={demo}
                              exempel={"_exempel" in p ? (p as ExempelRad)._exempel : undefined}
                            />
                          </div>
                        ) : null}
                      </li>
                    );
                  })}
                </Radlista>
              )}
            </div>

            {isDesktop ? (
              <div ref={detaljRef} className="min-w-0 scroll-mt-6 lg:sticky lg:top-24 lg:col-span-7">
                {/* Pekar bara på en lista som finns. */}
                {valdId || alla.length === 0 ? null : <Tomt>Välj ett bolag i listan.</Tomt>}
                {alla
                  .filter((p) => oppnade.includes(p.id))
                  .map((p) => (
                    <div key={p.id} hidden={p.id !== valdId}>
                      <LeadDetail
                        id={p.id}
                        demo={demo}
                        exempel={"_exempel" in p ? (p as ExempelRad)._exempel : undefined}
                      />
                    </div>
                  ))}
              </div>
            ) : null}
          </div>
        )}
      </div>

      <IrisGranserKompakt />
    </PageShell>
  );
}

function FelBox({ meddelande, onForsok }: Readonly<{ meddelande: string; onForsok: () => void }>) {
  return (
    <div className="flex items-start gap-3 border-y border-ochre/40 bg-ochre/10 px-4 py-4">
      <div className="min-w-0">
        <p className="text-[0.9375rem] font-medium text-ink">Bolagen kunde inte hämtas</p>
        <p className="mt-1 text-[0.9375rem] text-ink-muted">{meddelande}</p>
        <button type="button" onClick={onForsok} className={cn(btnSecondary, btnLiten, "mt-3")}>
          Försök igen
        </button>
      </div>
    </div>
  );
}

function ListorUpsell() {
  const spec = addonSpec("leadlists");
  return (
    <div className="min-w-0 border-t border-ink/15 py-6">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <h2 className={cn(rubrikPanel, "min-w-0 break-words")}>{spec.name}</h2>
        <Badge>Tillval</Badge>
      </div>
      <p className="mt-3 max-w-[64ch] text-[0.9375rem] leading-7">{spec.what}</p>
      <p className="mt-2 max-w-[64ch] text-[0.9375rem] leading-7 text-ink-muted">{spec.why}</p>
      <a
        href={mejlaOss(`Tillägg: ${spec.name}`)}
        className="focus-ring mt-4 inline-block text-[0.9375rem] font-medium text-warning underline underline-offset-4 hover:text-ink"
      >
        Hör av dig om {spec.name.toLowerCase()}
      </a>
    </div>
  );
}

/**
 * Kompakt gränslista längst ner på Bolag, med en länk vidare till hela listan
 * i Inställningar. En riktig `Sektion` (h2) sedan 2026-09-27: kickern som stod
 * här i stället för en rubrik (axe heading-order 2026-09-19) var mikrotext
 * enligt F-016, och h1 → h2 är ingen nivåhoppning.
 */
function IrisGranserKompakt() {
  return (
    <Sektion title="Så arbetar Iris">
      <Radlista>
        {GRANSER.slice(0, 3).map((grans) => (
          <li key={grans.rubrik} className="py-3">
            <p className="text-[0.9375rem] font-semibold text-ink">{grans.rubrik}</p>
          </li>
        ))}
      </Radlista>
      <IrisInstallningarLank />
    </Sektion>
  );
}

function IrisInstallningarLank() {
  const vag = useArbetsvag();
  return (
    <Link
      href={`${vag("/dashboard/iris/installningar")}#granser`}
      className="focus-ring mt-3 inline-block text-[0.9375rem] font-medium text-warning underline underline-offset-4 hover:text-ink"
    >
      Läs alla gränser och ställ in eskalering
    </Link>
  );
}

// ---------------------------------------------------------------------------
// Detaljpanelen — research, källor och mejlutkastet för ETT valt bolag.
// ---------------------------------------------------------------------------

type UtkastLage =
  | { fas: "kontrollerar" }
  | { fas: "ingen" }
  | { fas: "skapar" }
  | { fas: "fel"; meddelande: string }
  | { fas: "klar"; data: EmailStudioData; queueItemId: string | null };

async function snajpAnrop<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/snajp-support${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init
  });
  const kropp = (await readJsonBody<T & { error?: string; detail?: unknown }>(response)) ?? ({} as T);
  if (!response.ok) {
    const k = kropp as { error?: string; detail?: unknown };
    const detaljtext = Array.isArray(k.detail)
      ? k.detail
          .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
          .join("; ")
      : typeof k.detail === "string"
        ? k.detail
        : undefined;
    throw new Error(detaljtext ?? k.error ?? `Anropet avvisades (${response.status}).`);
  }
  return kropp;
}

function byggForskningssammanfattning(p: Prospekt): string {
  return kriterier(p.score_breakdown)
    .map((k) => `${k.etikett} (${k.utfall})${k.motivering ? `: ${k.motivering}` : ""}`)
    .join("\n")
    .slice(0, 8000);
}

function exempelStudioData(b: ExempelBolag): EmailStudioData {
  return {
    source: "mock",
    businessContext: null,
    email: {
      id: b.id,
      subject: b.draft.subject,
      body: b.draft.body,
      variantLength: "medium",
      variantType: "cold_outreach",
      status: "draft",
      companyId: b.id,
      contactId: null,
      companyName: b.companyName,
      signal: b.signal,
      offer: b.offer,
      cta: b.cta,
      contactName: kontaktnamn(b)
    }
  };
}

function LeadDetail({
  id,
  demo,
  exempel
}: Readonly<{ id: string; demo: boolean; exempel?: ExempelBolag }>) {
  const [lage, setLage] = useState<
    | { fas: "laddar" }
    | { fas: "fel"; meddelande: string }
    | { fas: "klar"; prospekt: Prospekt; kallor: { label: string; url: string }[] }
  >({ fas: "laddar" });
  const [utkastLage, setUtkastLage] = useState<UtkastLage>({ fas: "kontrollerar" });
  const [forsok, setForsok] = useState(0);

  useEffect(() => {
    let avbruten = false;
    async function load() {
      setLage({ fas: "laddar" });
      setUtkastLage({ fas: "kontrollerar" });

      if (exempel) {
        setLage({ fas: "klar", prospekt: exempelTillRad(exempel), kallor: exempel.kallor });
        setUtkastLage({ fas: "klar", data: exempelStudioData(exempel), queueItemId: null });
        return;
      }

      if (demo) {
        const svar = demoOversiktSvar("/leads/prospects") as { prospects?: Prospekt[] } | undefined;
        const träff = svar?.prospects?.find((p) => p.id === id);
        if (avbruten) return;
        if (träff) {
          setLage({ fas: "klar", prospekt: träff, kallor: [] });
          setUtkastLage({ fas: "ingen" });
        } else {
          setLage({ fas: "fel", meddelande: "Bolaget hittades inte." });
        }
        return;
      }

      try {
        const response = await fetch(`/api/snajp-support/leads/prospects/${encodeURIComponent(id)}`, {
          cache: "no-store"
        });
        if (avbruten) return;
        if (!response.ok) {
          setLage({ fas: "fel", meddelande: `Kunde inte hämta bolaget (status ${response.status}).` });
          return;
        }
        const kropp = await readJsonBody<{ prospect?: Prospekt; sources?: string[] }>(response);
        if (!kropp?.prospect) {
          setLage({ fas: "fel", meddelande: "Backenden svarade utan innehåll." });
          return;
        }
        // Backenden lämnar bara url:er — etiketten är url:en själv, samma
        // synliga text som förut. Exempelbolagen har en riktig etikett
        // (se lib/demo/iris-exempel.ts), båda formerna delar samma renderare.
        setLage({
          fas: "klar",
          prospekt: kropp.prospect,
          kallor: (kropp.sources ?? []).map((url) => ({ label: url, url }))
        });
        try {
          const utkast = await snajpAnrop<{
            utkast?: { id: string; subject?: string | null; body?: string | null } | null;
            queue_item_id?: string | null;
          }>(`/leads/prospects/${id}/utkast`);
          if (avbruten) return;
          if (utkast.utkast?.body) {
            setUtkastLage({
              fas: "klar",
              data: {
                source: "database",
                businessContext: null,
                email: {
                  id: utkast.utkast.id,
                  subject: utkast.utkast.subject || `Till ${kropp.prospect.company_name}`,
                  body: utkast.utkast.body,
                  variantLength: "medium",
                  variantType: "cold_outreach",
                  status: "draft",
                  companyId: kropp.prospect.id,
                  contactId: null,
                  companyName: kropp.prospect.company_name,
                  signal: beskrivning(kropp.prospect),
                  offer: null,
                  cta: null,
                  contactName: kropp.prospect.contact_name
                }
              },
              queueItemId: utkast.queue_item_id ?? null
            });
          } else {
            setUtkastLage({ fas: "ingen" });
          }
        } catch {
          setUtkastLage({ fas: "ingen" });
        }
      } catch (error) {
        if (!avbruten) setLage({ fas: "fel", meddelande: felmeddelande(error) });
      }
    }
    void load();
    return () => {
      avbruten = true;
    };
  }, [id, demo, exempel, forsok]);

  const skapaUtkast = useCallback(async () => {
    if (lage.fas !== "klar" || demo || exempel) return;
    const p = lage.prospekt;
    if (!p.contact_email) {
      setUtkastLage({
        fas: "fel",
        meddelande: "Prospektet saknar en mottagaradress. Lägg till en kontaktkälla med adress innan ett utkast kan skapas."
      });
      return;
    }
    setUtkastLage({ fas: "skapar" });
    try {
      const offerSummary = await lasOffertForUtkast();
      const svar = await snajpAnrop<{
        job_id?: string;
        fase?: string;
        escalated?: boolean;
        escalation_reason?: string | null;
        subject?: string;
        body?: string;
        queue_item_id?: string | null;
      }>("/leads/outreach/draft", {
        method: "POST",
        body: JSON.stringify({
          prospect_id: p.id,
          prospect_email: p.contact_email,
          company_name: p.company_name,
          offer_summary: offerSummary,
          brief:
            `Skriv ett kort, personligt första mejl till kontaktpersonen på ${p.company_name}. ` +
            "Utgå ifrån poängmotiveringen i researchunderlaget och håll dig till det som redan är " +
            "känt. Ingen hype, inga superlativ, ren text. Utkastet ska köas för granskning, inte skickas.",
          research_summary: byggForskningssammanfattning(p)
        })
      });
      if (svar.escalated || !svar.body) {
        setUtkastLage({
          fas: "fel",
          meddelande:
            svar.escalation_reason ||
            "Agenten lämnade över till en människa i stället för att skriva klart utkastet. Försök igen om en stund."
        });
        return;
      }
      setUtkastLage({
        fas: "klar",
        data: {
          source: "database",
          businessContext: null,
          email: {
            id: svar.queue_item_id ?? p.id,
            subject: svar.subject || `Till ${p.company_name}`,
            body: svar.body,
            variantLength: "medium",
            variantType: "cold_outreach",
            status: "draft",
            companyId: p.id,
            contactId: null,
            companyName: p.company_name,
            signal: beskrivning(p),
            offer: offerSummary,
            cta: null,
            contactName: p.contact_name
          }
        },
        queueItemId: svar.queue_item_id ?? null
      });
    } catch (error) {
      setUtkastLage({ fas: "fel", meddelande: felmeddelande(error) });
    }
  }, [lage, demo, exempel]);

  if (lage.fas === "laddar") {
    return <SkeletonRows />;
  }

  if (lage.fas === "fel") {
    return <FelBox meddelande={lage.meddelande} onForsok={() => setForsok((n) => n + 1)} />;
  }

  const { prospekt: p, kallor } = lage;
  const poangen = poang(p);

  return (
    <div className="rounded-card border border-ink/12 bg-paper p-5 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <h2 className={rubrikPanel}>{p.company_name}</h2>
          {segment(p) ? <p className={cn(meta, "mt-1")}>{segment(p)}</p> : null}
        </div>
        {/* Status är en bricka i huvudet, inte ett nyckeltal: den är ett
            ord, inte ett tal. */}
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Badge tone={AKTIV_STATUS.has(p.status) ? "warn" : "neutral"}>
            {STATUS_ETIKETT[p.status] ?? p.status}
          </Badge>
          {p.origin === "example" ? <Badge>Exempel</Badge> : null}
        </div>
      </div>

      <div className="mt-5">
        <Nyckeltal
          poster={[
            { etikett: "Poäng", varde: poangen ?? "–" },
            { etikett: "Källor", varde: kallor.length }
          ]}
        />
      </div>

      <div className="mt-6">
        <h3 className={rubrikPanel}>Research</h3>
        {kriterier(p.score_breakdown).length ? (
          <ul className="mt-3 divide-y divide-ink/10">
            {kriterier(p.score_breakdown).map((k, i) => (
              <li key={`${k.nyckel ?? k.etikett}-${i}`} className="py-3">
                <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                  <p className="text-[0.9375rem] font-medium">{k.etikett}</p>
                  <Badge tone={k.hart && k.utfall === "miss" ? "danger" : "neutral"}>{versal(k.utfall)}</Badge>
                </div>
                {k.motivering ? (
                  <p className="mt-1 max-w-[65ch] text-[0.9375rem] leading-6 text-ink-muted">{k.motivering}</p>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-[0.9375rem] text-ink-muted">Ingen poängmotivering sparad för det här bolaget.</p>
        )}

        {p.disqualifiers?.length ? (
          <div className="mt-4">
            <h4 className={etikett}>Skäl</h4>
            <ul className="mt-2 space-y-1.5">
              {p.disqualifiers.map((skal) => (
                <li key={skal} className="border-l-2 border-danger pl-3 text-[0.9375rem] text-ink-muted">
                  {skal}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <h4 className={cn(etikett, "mt-5")}>Källor</h4>
        {kallor.length ? (
          <ul className="mt-2 space-y-1.5">
            {kallor.map((kalla) => (
              <li key={kalla.url}>
                <a
                  href={kalla.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="focus-ring break-all text-[0.9375rem] text-ink-muted underline decoration-ink/25 underline-offset-4"
                >
                  {kalla.label}
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-[0.9375rem] text-ink-muted">
            Inga källor sparade. Utan minst en källa får Iris inte skriva ett utkast.
          </p>
        )}
      </div>

      <div className="mt-6 border-t border-ink/12 pt-5">
        <h3 className={rubrikPanel}>Mejlutkast</h3>

        {utkastLage.fas === "kontrollerar" ? (
          <div className="mt-3 h-16 animate-pulse rounded-input bg-ink/[0.03]" />
        ) : null}

        {utkastLage.fas === "ingen" ? (
          demo ? (
            <p className="mt-3 max-w-[65ch] text-[0.9375rem] leading-6 text-ink-muted">
              Inget utkast till det här bolaget. I drift skriver Iris ett första mejl utifrån
              poängmotiveringen och källorna ovan.
            </p>
          ) : (
            <div className="mt-3">
              <p className="max-w-[65ch] text-[0.9375rem] leading-6 text-ink-muted">
                Inget utkast ännu. Ett klick skriver ett första mejl utifrån research och källor,
                sedan väntar det på din granskning i kön.
              </p>
              <button type="button" onClick={() => void skapaUtkast()} className={cn(btnPrimary, "mt-4")}>
                Skapa utkast
              </button>
            </div>
          )
        ) : null}

        {utkastLage.fas === "skapar" ? <p className="mt-3 text-[0.9375rem] text-ink-muted">Skriver utkastet…</p> : null}

        {utkastLage.fas === "fel" ? (
          <div className="mt-3">
            <p role="alert" className="text-[0.9375rem] text-danger">
              {utkastLage.meddelande}
            </p>
            <button
              type="button"
              onClick={() => void skapaUtkast()}
              className={cn(btnSecondary, "mt-3")}
            >
              Försök igen
            </button>
          </div>
        ) : null}

        {utkastLage.fas === "klar" ? (
          <div className="mt-4">
            <EmailStudioEditor data={utkastLage.data} compact />
            {!demo && !exempel ? (
              <GodkannKnapp queueItemId={utkastLage.queueItemId} />
            ) : (
              <p className="mt-4 max-w-[65ch] text-[0.9375rem] leading-6 text-ink-muted">
                Exempelutkast. Inget skickas härifrån.
              </p>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function GodkannKnapp({ queueItemId }: Readonly<{ queueItemId: string | null }>) {
  const [godkant, setGodkant] = useState(false);
  const [busy, setBusy] = useState(false);
  const [fel, setFel] = useState<string | null>(null);

  async function godkann() {
    if (!queueItemId) return;
    setBusy(true);
    setFel(null);
    try {
      await snajpAnrop(`/leads/queue/${encodeURIComponent(queueItemId)}/approve`, { method: "POST" });
      setGodkant(true);
    } catch (error) {
      setFel(felmeddelande(error));
    } finally {
      setBusy(false);
    }
  }

  if (godkant) {
    return (
      <p role="status" className="mt-4 text-[15px] text-moss">
        Godkänt. Utkastet ligger nu i sändkön.
      </p>
    );
  }

  return (
    <div className="mt-4">
      <button
        type="button"
        disabled={busy || !queueItemId}
        onClick={() => void godkann()}
        className={cn(btnPrimary, "disabled:cursor-wait disabled:opacity-60")}
      >
        {busy ? "Godkänner…" : "Godkänn och skicka"}
      </button>
      {!queueItemId ? (
        <p className="mt-3 max-w-[65ch] text-[0.9375rem] leading-6 text-ink-muted">
          Det här utkastet saknar ett kö-id och kan inte godkännas härifrån. Se Iris › Granskning.
        </p>
      ) : null}
      {fel ? (
        <p role="alert" className="mt-3 max-w-[65ch] text-[0.9375rem] text-danger">
          {fel}
        </p>
      ) : null}
    </div>
  );
}
