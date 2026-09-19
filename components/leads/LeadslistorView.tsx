"use client";

import { Send } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { btnPrimary, btnSecondary, EmptyState, SkeletonRows } from "@/components/ui";
import { lasOffertForUtkast } from "@/lib/actions/affarskontext";
import type { EmailStudioData } from "@/lib/data/emails";
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
 *   POST /leads/listor            {titel, antal, is_test?, overrides?} → 202 {list_id, job_id}
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
  /** Radens id i lead_list_items — behövs för Skriv mejl-bron nedan. */
  id: string;
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

/** Kontakttrappans nivåer på svenska — speglar LeadsSnabbsok.KONTAKTETIKETT
 *  (samma medvetna spegling som `anropa` och fältklassen ovan). Pixel-
 *  granskningen 2026-09-02 visade råa `ROLE_ADDRESS`-värden i tabellen. */
const KONTAKTNIVA_ETIKETT: Record<string, string> = {
  named_role_match: "Namngiven beslutsfattare",
  named_other: "Namngiven kontakt",
  role_address: "Rolladress",
  contact_form: "Kontaktformulär"
};

function kontaktniva(rad: ListRad): string | null {
  if (!rad.contact_level) return null;
  return KONTAKTNIVA_ETIKETT[rad.contact_level] ?? rad.contact_level;
}

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
      <span className="text-[13px] font-medium text-ink-muted">{etikett}</span>
      {hint ? <span className="ml-2 text-[12px] text-ink-subtle">{hint}</span> : null}
      <div className="mt-1.5">{children}</div>
    </label>
  );
}

/**
 * Felet bär statuskoden. Snabbmailens svep måste skilja "den här raden gick
 * inte" från "budgeten/AI-kapaciteten är slut" — det senare ska stoppa hela
 * svepet direkt, inte ge 24 likadana fel till.
 */
class AnropsFel extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
  }
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
    throw new AnropsFel(
      detaljtext ?? k.error ?? `Anropet avvisades (${response.status}).`,
      response.status
    );
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
      kontaktniva(rad) ?? "",
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
      setBestallFel(
        "Beskriv vilka bolag listan ska hitta — beskrivningen är både sökningen och listans namn."
      );
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
      // 429 = budgettak, 422 = inget sökbart underlag (varken sparad målgrupp
      // eller titel). `anropa` plockar redan ut feltexten ur `detail`, så den
      // visas som den är i felraden nedan.
      await anropa<{ list_id?: string; job_id?: string }>("/leads/listor", {
        method: "POST",
        body: JSON.stringify({
          titel: titel.trim(),
          antal: antalTal,
          // Titeln STYR sökningen. Utan overrides byggde listjobbet bara på
          // den sparade målgruppen, och "Bygg i Norrland" gav samma bolag som
          // "Tandläkare i Skåne" — testaren skrev en titel som såg ut som en
          // sökning och fick något annat. Samma form som LeadsSnabbsok.
          overrides: { must_have: [titel.trim()] },
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
        <p className="mt-1 max-w-[65ch] text-[13px] text-ink-subtle">
          Agenten letar, verifierar och lägger raderna här — ingenting skickas och inga utkast
          skrivs.
        </p>

        <div className="mt-6 grid max-w-[760px] gap-5 sm:grid-cols-2">
          <Rad etikett="Vilka bolag ska listan hitta?" hint="t.ex. Bygg i Norrland, 10–50 anställda">
            <input
              value={titel}
              onChange={(e) => setTitel(e.target.value)}
              placeholder="Bransch, ort, storlek"
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

        {status ? <p className="mt-3 text-[13px] text-ink-subtle">{status}</p> : null}
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
                        <p className="mt-1 text-[13px] text-ink-subtle">
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
                              ? "text-warning"
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
                      <p className="mt-2 inline-flex items-center gap-1.5 text-[13px] font-medium text-warning">
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
 * Hur många utkast ETT klick på "Skriv utkast till alla med mejladress" får
 * starta. Varje utkast är ett riktigt LLM-jobb mot leadsbudgeten; en lista på
 * 200 bolag ska inte kunna tömma budgeten i ett enda klick som ingen hann
 * ångra. Nästa klick tar nästa omgång.
 */
const SVEP_TAK = 25;

/**
 * Leverantörens och backendens formuleringar för slut kapacitet. Speglar
 * `_KREDITMARKORER` och kundtexterna i snajp-support/app/kvotfel.py — en
 * misslyckad utkastjobbstext bär bara meningen, inte statuskoden, så svepet
 * måste känna igen texten för att veta att det ska sluta.
 */
const KAPACITETSMARKORER = [
  "prepayment credits",
  "credits are depleted",
  "billing#prepay",
  "ai-kapaciteten är slut",
  "kvot är slut",
  "kvoten är slut"
];

/** Saknad erbjudandetext gäller varje rad lika — därför stoppar den svepet. */
const OFFERT_SAKNAS =
  "Affärskontexten (Vad ni säljer) behövs för utkastet. Fyll i den under Inställningar, " +
  "Vad agenterna vet, Affärskontext — och kontrollera att du fortfarande är inloggad.";

/** Ska svepet stanna helt? 429 = budgettak, 503 = ingen skarp LLM, eller en
 *  kredit-/kvottext ur ett misslyckat jobb. Allt annat gäller bara raden. */
function stopparSvepet(fel: unknown): boolean {
  if (fel instanceof AnropsFel && (fel.status === 429 || fel.status === 503)) return true;
  if (fel instanceof Error && fel.message === OFFERT_SAKNAS) return true;
  const text = (fel instanceof Error ? fel.message : String(fel)).toLocaleLowerCase("sv");
  return KAPACITETSMARKORER.some((markor) => text.includes(markor));
}

type Utkast = {
  prospectId: string;
  subject: string | null | undefined;
  body: string;
  queueItemId: string | null;
  offert: string | null;
  /** Ett utkast fanns redan för bolaget — inget nytt jobb startades. */
  fanns: boolean;
};

/**
 * Utkastkedjan för EN listrad. Delas av mejlrutan och snabbmailens svep, så
 * att de två aldrig kan skriva utkast på olika sätt.
 *
 * (1) Raden lyfts in i prospektregistret — LLM-fritt och idempotent, en
 * befintlig rad återanvänds. (2) Saknade raden adress sparas den som
 * användaren angav på prospektet. (3) Finns ett utkast redan visas det i
 * stället för att ett nytt skrivs. (4) Annars skrivs utkastet av samma kedja
 * som bolagssidans (/leads/outreach/draft) och pollas tills jobbet är klart.
 *
 * `adress` krävs. Backenden bygger avregistreringsfoten som lagen kräver ur
 * mottagaradressen NÄR UTKASTET KÖAS (leads_tools._med_lagstadgad_fot) — ett
 * utkast utan adress hade legat i kön utan fot och blivit oskickbart på
 * lagligt vis även sedan en adress lagts till.
 */
async function skrivUtkastForRad(
  lista: Lista,
  rad: ListRad,
  adress: string,
  steg: (text: string) => void = () => {}
): Promise<Utkast> {
  steg("Lägger bolaget i registret…");
  const befordran = await anropa<{ prospect?: { id: string } }>(
    `/leads/listor/${encodeURIComponent(lista.id)}/items/${encodeURIComponent(rad.id)}/prospekt`,
    { method: "POST" }
  );
  const prospectId = befordran.prospect?.id;
  if (!prospectId) throw new Error("Bolaget kunde inte läggas i registret.");

  if (!rad.contact_email) {
    // Adressen hör hemma på prospektet, inte bara i det här anropet: tråden
    // och sändkön läser mottagaren ur prospects.contact_email.
    steg("Sparar adressen på bolaget…");
    await anropa(`/leads/prospects/${encodeURIComponent(prospectId)}`, {
      method: "PATCH",
      body: JSON.stringify({ contact_email: adress })
    });
  }

  // Finns ett utkast redan (rutan öppnad förut, eller en körning har hunnit
  // skriva ett)? Då används det — ett andra utkastjobb för samma bolag är
  // dubbel kostnad för samma fråga.
  steg("Ser efter om ett utkast redan finns…");
  try {
    const befintligt = await anropa<{
      utkast?: { subject?: string | null; body?: string | null } | null;
      queue_item_id?: string | null;
    }>(`/leads/prospects/${encodeURIComponent(prospectId)}/utkast`);
    if (befintligt.utkast?.body) {
      return {
        prospectId,
        subject: befintligt.utkast.subject,
        body: befintligt.utkast.body,
        queueItemId: befintligt.queue_item_id ?? null,
        offert: null,
        fanns: true
      };
    }
  } catch {
    // Ett fel här ska inte hindra ett nytt utkast från att skrivas.
  }

  steg("Agenten skriver utkastet…");
  // Utan erbjudandetext svarar /leads/outreach/draft 422 (offer_summary har
  // min_length=1) — att skicka `undefined` gav bara ett obegripligare fel ett
  // steg senare. Felet skrivs om här i stället för att föras vidare: en server
  // action maskerar sitt meddelande i produktionsbygget, och de två sätt den
  // kan kasta på (utloggad, tom affärskontext) har samma åtgärd för kunden.
  let offert: string;
  try {
    offert = await lasOffertForUtkast();
  } catch {
    throw new Error(OFFERT_SAKNAS);
  }

  type Utkastsvar = {
    job_id?: string;
    fase?: string;
    subject?: string;
    body?: string;
    escalated?: boolean;
    escalation_reason?: string | null;
    queue_item_id?: string | null;
  };
  const koat = await anropa<Utkastsvar>("/leads/outreach/draft", {
    method: "POST",
    body: JSON.stringify({
      prospect_id: prospectId,
      prospect_email: adress,
      company_name: rad.company_name,
      offer_summary: offert ?? undefined,
      brief:
        `Skriv ett kort, personligt första mejl till kontaktvägen på ${rad.company_name}. ` +
        "Utgå från signalen i underlaget och håll dig till det som är känt. " +
        "Ingen hype, inga superlativ, ren text. Utkastet ska köas för granskning, inte skickas.",
      research_summary: [
        rad.ort ? `Ort: ${rad.ort}` : null,
        rad.signal ? `Signal: ${signaltext(rad)}` : null,
        rad.source_name ? `Källa: ${rad.source_name}` : null,
        rad.contact_name || rad.contact_role
          ? `Kontakt: ${[rad.contact_name, rad.contact_role].filter(Boolean).join(", ")}`
          : null
      ]
        .filter(Boolean)
        .join("\n"),
      research_evidence: rad.source_url ? [rad.source_url] : []
    })
  });

  let svar: Utkastsvar = koat;
  if (koat.job_id && (koat.fase === "skriver" || !koat.body)) {
    let klart = false;
    for (let forsok = 0; forsok < 90; forsok += 1) {
      await new Promise((r) => setTimeout(r, forsok < 5 ? 800 : 2000));
      const jobb = await anropa<{ status?: string; error?: string; result?: Utkastsvar }>(
        `/leads/jobb/${encodeURIComponent(koat.job_id)}`
      );
      if (jobb.status === "completed" && jobb.result) {
        svar = jobb.result;
        klart = true;
        break;
      }
      if (jobb.status === "failed") {
        throw new Error(jobb.error || "Utkastet kunde inte skrivas.");
      }
    }
    // Utan den här raden föll en utgången väntan igenom till eskalerings-
    // texten nedan, och "agenten lämnade över till en människa" är inte vad
    // som hände — jobbet kan fortfarande bli klart.
    if (!klart) {
      throw new Error(
        "Utkastet tog för lång tid att skriva. Det kan dyka upp i granskningskön ändå — titta där innan ni försöker igen."
      );
    }
  }

  if (svar.escalated || !svar.body) {
    throw new Error(
      svar.escalation_reason ||
        "Agenten lämnade över till en människa i stället för att skriva klart utkastet."
    );
  }

  return {
    prospectId,
    subject: svar.subject,
    body: svar.body,
    queueItemId: svar.queue_item_id ?? null,
    offert,
    fanns: false
  };
}

type Svep =
  | { fas: "bekraftar" }
  | { fas: "kor"; klara: number; totalt: number; bolag: string };

/**
 * Raderna i EN klar lista. Samma form som Bolagsregistret: tabell från md och
 * upp, kort under — sex kolumner krympta till 375px blir oläsliga.
 */
function Listtabell({ lista, items }: Readonly<{ lista: Lista; items: ListRad[] }>) {
  // I demon finns ingen riktig utkastkedja att köra mot — mejlrutan döljs,
  // CSV:n står kvar.
  const { isDemo, vy } = useDashboard();
  const mejlbro = !isDemo && vy !== "demo";

  // Skriv mejl: rutan med Email studio öppnas UNDER raden. Ett öppet rad-id i
  // taget: två samtidiga utkastjobb från samma lista är dubbel kostnad för
  // samma klick.
  const [oppenRad, setOppenRad] = useState<string | null>(null);
  const [laggerAlla, setLaggerAlla] = useState(false);
  const [allaResultat, setAllaResultat] = useState<string | null>(null);
  const [radFel, setRadFel] = useState<string | null>(null);

  // Snabbmail: utkast till alla rader med adress, i omgångar om SVEP_TAK.
  // `hanterade` minns vilka rader svepet redan tagit (lyckade som felade), så
  // att nästa klick tar NÄSTA omgång i stället för att köra om de första 25.
  const [svep, setSvep] = useState<Svep | null>(null);
  const [svepResultat, setSvepResultat] = useState<string | null>(null);
  const [svepStopp, setSvepStopp] = useState<string | null>(null);
  const [hanterade, setHanterade] = useState<Set<string>>(new Set());
  const avbryt = useRef(false);
  const korRef = useRef(false);
  const [stopparBegart, setStopparBegart] = useState(false);
  // Stängs listan mitt i svepet ska loopen inte fortsätta beställa jobb åt en
  // vy ingen längre tittar på — det pågående utkastet blir klart, inget mer.
  useEffect(
    () => () => {
      avbryt.current = true;
    },
    []
  );

  const medAdress = items.filter((rad) => rad.contact_email);
  const kandidater = medAdress.filter((rad) => !hanterade.has(rad.id));
  const omgang = kandidater.slice(0, SVEP_TAK);
  const svepKor = svep?.fas === "kor";

  const laggAllaIRegistret = useCallback(async () => {
    setLaggerAlla(true);
    setRadFel(null);
    setAllaResultat(null);
    let nya = 0;
    let fanns = 0;
    let fel = 0;
    // Sekventiellt med flit: befordran är billig, och en parallell skur mot
    // dedupe-kontrollen hade kunnat skapa just de dubbletter den finns för
    // att stoppa.
    for (const rad of items) {
      try {
        const svar = await anropa<{ skapad?: boolean }>(
          `/leads/listor/${encodeURIComponent(lista.id)}/items/${encodeURIComponent(rad.id)}/prospekt`,
          { method: "POST" }
        );
        if (svar.skapad) nya += 1;
        else fanns += 1;
      } catch {
        fel += 1;
      }
    }
    setAllaResultat(
      [
        nya ? `${nya} nya i registret` : null,
        fanns ? `${fanns} fanns redan` : null,
        fel ? `${fel} gick inte att lägga in` : null
      ]
        .filter(Boolean)
        .join(" · ") || "Inga rader att lägga in."
    );
    setLaggerAlla(false);
  }, [items, lista.id]);

  const skrivAllaUtkast = useCallback(async () => {
    const rader = omgang;
    // Ref och inte state: ett dubbelklick på bekräftelsen hinner avfyras två
    // gånger innan dialogen renderats bort, och två svep hade dubblat jobben.
    if (!rader.length || korRef.current) return;
    korRef.current = true;
    setStopparBegart(false);
    // Mejlrutan stängs: den och svepet hade annars kunnat starta två jobb för
    // samma bolag samtidigt.
    setOppenRad(null);
    setSvepResultat(null);
    setSvepStopp(null);
    avbryt.current = false;

    let nya = 0;
    let fanns = 0;
    let fel = 0;
    let klara = 0;
    const tagna = new Set(hanterade);

    // Sekventiellt, inte parallellt: budgetgrinden räknar per jobb, och 25
    // samtidiga jobb hade passerat grinden innan det första hunnit räknas.
    for (const rad of rader) {
      if (avbryt.current) break;
      setSvep({ fas: "kor", klara, totalt: rader.length, bolag: rad.company_name });
      try {
        const utkast = await skrivUtkastForRad(lista, rad, rad.contact_email as string);
        if (utkast.fanns) fanns += 1;
        else nya += 1;
        tagna.add(rad.id);
      } catch (orsak) {
        if (stopparSvepet(orsak)) {
          // Backendens egen mening visas, inte en omskrivning: den säger om
          // det är budgettaket eller kapaciteten, och vad som gäller härnäst.
          // Raden räknas INTE som hanterad — den ska med i nästa försök.
          setSvepStopp(felmeddelande(orsak));
          break;
        }
        fel += 1;
        tagna.add(rad.id);
      }
      klara += 1;
      setHanterade(new Set(tagna));
    }

    korRef.current = false;
    const stoppadAvDig = avbryt.current;
    setStopparBegart(false);
    setSvep(null);
    setSvepResultat(
      [
        stoppadAvDig ? "Stoppat" : null,
        nya ? `${nya} ${nya === 1 ? "nytt" : "nya"} utkast` : null,
        fanns ? `${fanns} hade redan ett utkast` : null,
        fel ? `${fel} gick inte att skriva — öppna raden för att se varför` : null
      ]
        .filter(Boolean)
        .join(" · ") || "Inga utkast skrevs."
    );
  }, [hanterade, lista, omgang]);

  if (!items.length) {
    return (
      <p className="mt-4 border-t border-ink/10 pt-4 text-[15px] text-ink-muted">
        Listan är klar men innehåller inga rader.
      </p>
    );
  }

  function skrivMejlKnapp(rad: ListRad, extra?: string) {
    return (
      <button
        type="button"
        onClick={() => setOppenRad(oppenRad === rad.id ? null : rad.id)}
        aria-expanded={oppenRad === rad.id}
        disabled={svepKor}
        className={cn(btnSecondary, "whitespace-nowrap disabled:opacity-60", extra)}
      >
        {oppenRad === rad.id ? "Stäng mejlet" : "Skriv mejl"}
      </button>
    );
  }

  return (
    <div className="mt-4 rounded-card border border-ink/10 bg-paper p-4 md:p-5">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <p className="text-[13px] text-ink-subtle">
          {items.length} bolag i listan · {medAdress.length} med mejladress
        </p>
        <div className="flex flex-wrap items-center gap-2">
          {/* Snabbmail: ett utkast per rad med adress, rakt in i granskningskön.
              Bekräftas först — det är upp till 25 LLM-jobb på ett klick. */}
          {mejlbro && medAdress.length ? (
            <button
              type="button"
              onClick={() => {
                setSvepResultat(null);
                setSvepStopp(null);
                setSvep({ fas: "bekraftar" });
              }}
              disabled={svep !== null || kandidater.length === 0}
              className={cn(btnSecondary, "disabled:opacity-60")}
            >
              {kandidater.length === 0
                ? "Alla med adress är genomgångna"
                : "Skriv utkast till alla med mejladress"}
            </button>
          ) : null}
          {/* Hela listan in i Leads-registret i ett svep — därifrån kan en
              körning researcha och skriva utkast till flera på en gång. */}
          {mejlbro ? (
            <button
              type="button"
              onClick={() => void laggAllaIRegistret()}
              disabled={laggerAlla || svepKor}
              className={cn(btnSecondary)}
            >
              {laggerAlla ? "Lägger in…" : "Lägg alla i registret"}
            </button>
          ) : null}
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
      </div>

      {svep?.fas === "bekraftar" ? (
        <div
          role="alertdialog"
          aria-label="Bekräfta utkast till hela listan"
          className="mt-4 rounded-card border border-warning/40 bg-warning/10 p-4"
        >
          <p className="max-w-[70ch] text-[0.875rem] leading-6 text-ink">
            Agenten skriver <strong className="font-semibold">{omgang.length} utkast</strong>
            {kandidater.length > omgang.length
              ? ` — de första ${omgang.length} av ${kandidater.length} med adress. Nästa klick tar resten.`
              : ", ett per bolag med mejladress."}{" "}
            Utkasten landar i granskningskön under Leads.{" "}
            <strong className="font-semibold">Ingenting skickas</strong> förrän ni godkänner
            varje mejl. Varje utkast räknas mot er leadsbudget.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void skrivAllaUtkast()}
              // Bekräftelsen dyker upp på knapptryck; fokus följer med så att
              // tangentbordet landar på beslutet i stället för bakom det.
              autoFocus
              className="focus-ring rounded-input bg-ink px-4 py-2 text-[0.8125rem] font-semibold text-paper hover:bg-ink2"
            >
              Skriv {omgang.length} utkast
            </button>
            <button
              type="button"
              onClick={() => setSvep(null)}
              className="focus-ring rounded-input bg-paper2 px-4 py-2 text-[0.8125rem] text-ink hover:bg-paper2/70"
            >
              Avbryt
            </button>
          </div>
        </div>
      ) : null}

      {svep?.fas === "kor" ? (
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
          <p role="status" className="text-[13px] text-ink-muted">
            Skriver utkast {svep.klara + 1} av {svep.totalt} — {svep.bolag}
          </p>
          <button
            type="button"
            onClick={() => {
              avbryt.current = true;
              setStopparBegart(true);
            }}
            disabled={stopparBegart}
            className="focus-ring text-[13px] underline underline-offset-4 hover:text-ochre disabled:text-ink-subtle disabled:no-underline"
          >
            {stopparBegart ? "Stoppar efter det här utkastet…" : "Stoppa efter det här utkastet"}
          </button>
        </div>
      ) : null}
      {svepStopp ? (
        <p role="alert" className="mt-3 max-w-[70ch] break-words text-[14px] text-danger">
          Svepet stoppades: {svepStopp}
        </p>
      ) : null}
      {svepResultat ? (
        <p className="mt-3 text-[13px] text-ink-subtle">
          {svepResultat} — utkasten ligger i granskningskön under Leads.
        </p>
      ) : null}

      {allaResultat ? (
        <p className="mt-3 text-[13px] text-ink-subtle">
          {allaResultat} — bolagen ligger under Leads och kan researchas och mejlas därifrån.
        </p>
      ) : null}
      {radFel ? (
        <p role="alert" className="mt-3 max-w-[70ch] break-words text-[14px] text-danger">
          {radFel}
        </p>
      ) : null}

      {/* Testaren hittade inte bron alls: knappen syntes bara på rader med
          adress, och den listan hade inga. En rad om vad raderna gör kostar
          ingenting och gör vägen till Email studio synlig även innan någon
          klickat. */}
      {mejlbro ? (
        <p className="mt-4 max-w-[70ch] text-[13px] leading-6 text-ink-subtle">
          Skriv mejl på en rad öppnar Email studio: agenten skriver ett utkast som ni kan
          förbättra, personalisera och godkänna.
        </p>
      ) : null}

      {/* Fast layout (table-fixed + colgroup): bredderna deklareras i procent
          och summerar till 100 — se Tabell i components/ui.tsx. Knappkolumnen
          finns bara när mejlbron är på, så colgroup och expanderradens colSpan
          måste följa samma villkor som cellerna. */}
      <div className="mt-4 hidden overflow-x-auto border-y border-ink/15 md:block">
        <table className="w-full min-w-[960px] table-fixed border-collapse text-[15px]">
          <colgroup>
            <col style={{ width: "22%" }} />
            <col style={{ width: "10%" }} />
            <col style={{ width: "18%" }} />
            <col style={{ width: "12%" }} />
            <col style={{ width: "24%" }} />
            <col style={{ width: "14%" }} />
            {mejlbro ? <col style={{ width: "130px" }} /> : null}
          </colgroup>
          <thead>
            <tr className="border-b border-ink/15 text-left">
              {[..."Bolag,Ort,Kontakt,Kontaktnivå,Signal,Källa".split(","), ...(mejlbro ? [""] : [])].map(
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
            {items.map((rad, index) => [
              <tr key={`${rad.company_name}-${index}`} className="transition hover:bg-paper2/60">
                <th scope="row" className="py-4 pr-6 text-left font-normal">
                  <p className="text-[15px] font-semibold tracking-[-0.01em]">
                    {rad.company_name}
                  </p>
                  {rad.website ? (
                    <p className="mt-1 break-all text-sm text-ink-subtle">{rad.website}</p>
                  ) : null}
                </th>
                <td className="kicker py-4 pr-6 text-mineral">{rad.ort ?? "—"}</td>
                <td className="py-4 pr-6">
                  <p className="text-[15px]">{kontakt(rad)}</p>
                  {rad.contact_email && (rad.contact_name || rad.contact_role) ? (
                    <p className="mt-1 break-all text-sm text-ink-subtle">{rad.contact_email}</p>
                  ) : null}
                </td>
                <td className="py-4 pr-6 text-[14px] text-ink-muted">{kontaktniva(rad) ?? "—"}</td>
                <td className="py-4 pr-6 text-[15px] leading-6 text-ink-muted">{signaltext(rad)}</td>
                <td className="py-4 pr-6">
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
                    <span className="text-[14px] text-ink-subtle">{rad.source_name ?? "—"}</span>
                  )}
                </td>
                {/* Knappen står på VARJE rad. Förut syntes den bara där en
                    adress fanns, och i en lista utan adresser fanns ingen
                    väg till Email studio alls. Saknas adressen frågar rutan
                    efter den i stället. */}
                {mejlbro ? <td className="py-4 text-right">{skrivMejlKnapp(rad)}</td> : null}
              </tr>,
              oppenRad === rad.id ? (
                <tr key={`${rad.id}-mejl`}>
                  {/* Samma villkor som colgroup och huvudet: sex kolumner utan
                      mejlbro, sju med. */}
                  <td colSpan={mejlbro ? 7 : 6} className="pb-6 pt-1">
                    <MejlRuta lista={lista} rad={rad} />
                  </td>
                </tr>
              ) : null
            ])}
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
              {kontaktniva(rad) ? (
                <span className="shrink-0 text-[12px] text-ink-subtle">{kontaktniva(rad)}</span>
              ) : null}
            </div>
            <p className="kicker mt-1 text-mineral">
              {[rad.ort, rad.website].filter(Boolean).join(" · ") || "—"}
            </p>
            <p className="mt-2 text-sm leading-6 text-ink-muted">{signaltext(rad)}</p>
            <div className="mt-2 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
              <span className="min-w-0 break-all text-sm text-ink-muted">{kontakt(rad)}</span>
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
            {mejlbro ? skrivMejlKnapp(rad, "mt-3 w-full") : null}
            {mejlbro && oppenRad === rad.id ? (
              <div className="mt-3">
                <MejlRuta lista={lista} rad={rad} />
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Tillräckligt för att fånga ett felskrivet fält, inte en RFC 5322-validering —
 *  backenden och sändvägen är domarna. */
const ADRESS_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Mejlrutan under en listrad: Email studio, på plats.
 *
 * Kedjan är `skrivUtkastForRad` ovan. Utkastet landar i granskningskön och
 * visas här i Email studio-editorn, med Förbättra/Personalisera-knapparna och
 * "Godkänn och skicka".
 *
 * Saknar raden adress frågar rutan efter den FÖRST. Ett utkast utan mottagare
 * går inte att skicka lagligt (avregistreringsfoten byggs på adressen när
 * utkastet köas), så ett utkast före adressen hade varit ett löfte rutan inte
 * kan hålla.
 *
 * Ingenting skickas från den här rutan — godkännandet släpper utkastet till
 * samma sändkö som alla andra prospekt (INV-SEC-004 består: listjobbet har
 * inget sändverktyg, det har bara människan efter granskning).
 */
function MejlRuta({ lista, rad }: Readonly<{ lista: Lista; rad: ListRad }>) {
  const [fas, setFas] = useState<"adress" | "skapar" | "klar" | "fel">(
    rad.contact_email ? "skapar" : "adress"
  );
  const [steg, setSteg] = useState("Lägger bolaget i registret…");
  const [fel, setFel] = useState<string | null>(null);
  const [data, setData] = useState<EmailStudioData | null>(null);
  const [queueItemId, setQueueItemId] = useState<string | null>(null);
  const [godkant, setGodkant] = useState(false);
  const [godkannBusy, setGodkannBusy] = useState(false);
  const [godkannFel, setGodkannFel] = useState<string | null>(null);
  const [adressfalt, setAdressfalt] = useState("");
  const [adressFel, setAdressFel] = useState<string | null>(null);
  const [adress, setAdress] = useState<string | null>(rad.contact_email ?? null);

  const skapa = useCallback(
    async (mottagare: string) => {
      setFas("skapar");
      setFel(null);
      try {
        const utkast = await skrivUtkastForRad(lista, rad, mottagare, setSteg);
        setData(byggStudioData(rad, utkast.prospectId, utkast.subject, utkast.body, utkast.offert));
        setQueueItemId(utkast.queueItemId);
        setFas("klar");
      } catch (orsak) {
        setFel(felmeddelande(orsak));
        setFas("fel");
      }
    },
    [lista, rad]
  );

  useEffect(() => {
    if (rad.contact_email) void skapa(rad.contact_email);
    // Kör en gång när rutan öppnas för raden — skapa() är stabil per rad.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rad.id]);

  function sparaAdress() {
    const varde = adressfalt.trim();
    if (!ADRESS_RE.test(varde)) {
      setAdressFel("Skriv en hel mejladress, t.ex. namn@bolaget.se.");
      return;
    }
    setAdressFel(null);
    setAdress(varde);
    void skapa(varde);
  }

  const godkann = useCallback(async () => {
    if (!queueItemId) return;
    setGodkannBusy(true);
    setGodkannFel(null);
    try {
      await anropa(`/leads/queue/${encodeURIComponent(queueItemId)}/approve`, { method: "POST" });
      setGodkant(true);
    } catch (orsak) {
      setGodkannFel(felmeddelande(orsak));
    } finally {
      setGodkannBusy(false);
    }
  }, [queueItemId]);

  return (
    <div className="rounded-card border border-ink/15 bg-paper2/50 p-4 md:p-5">
      <p className="kicker text-mineral">Mejl till {adress ?? rad.company_name}</p>

      {fas === "adress" ? (
        <form
          className="mt-3"
          // Egen svensk validering nedan; webbläsarens bubbla hade hunnit före.
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            sparaAdress();
          }}
        >
          <p className="max-w-[65ch] text-[14px] leading-6 text-ink-muted">
            Raden saknar mejladress. Lägg till mottagaren, så skriver agenten utkastet. Adressen
            sparas på bolaget under Leads.
          </p>
          <label className="mt-3 block max-w-[420px]">
            <span className="text-[13px] font-medium text-ink-muted">Mejladress</span>
            <input
              type="email"
              value={adressfalt}
              onChange={(e) => setAdressfalt(e.target.value)}
              placeholder="namn@bolaget.se"
              autoComplete="off"
              aria-invalid={adressFel ? true : undefined}
              aria-describedby={adressFel ? `adressfel-${rad.id}` : undefined}
              className={cn(fältklass, "mt-1.5")}
            />
          </label>
          {adressFel ? (
            <p id={`adressfel-${rad.id}`} role="alert" className="mt-2 text-[14px] text-danger">
              {adressFel}
            </p>
          ) : null}
          <button type="submit" className={cn(btnPrimary, "mt-3")}>
            Spara adressen och skriv utkast
          </button>
        </form>
      ) : null}

      {fas === "skapar" ? (
        <p className="mt-3 text-[14px] text-ink-subtle" role="status">
          {steg}
        </p>
      ) : null}

      {fas === "fel" ? (
        <div className="mt-3">
          <p role="alert" className="max-w-[70ch] text-[14px] leading-6 text-danger">
            {fel}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => (adress ? void skapa(adress) : setFas("adress"))}
              className={cn(btnSecondary)}
            >
              Försök igen
            </button>
            {!rad.contact_email ? (
              <button
                type="button"
                onClick={() => {
                  setAdressfalt(adress ?? "");
                  setFas("adress");
                }}
                className={cn(btnSecondary)}
              >
                Ändra adressen
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      {fas === "klar" && data ? (
        <div className="mt-4">
          <EmailStudioEditor data={data} compact />
          <p className="mt-4 max-w-[65ch] text-[13px] leading-6 text-ink-subtle">
            Godkänn skickar utkastet som det sparades i granskningskön. Ändringar i fälten ovan
            uppdaterar bara den här vyn tills en sparväg finns.
          </p>
          <div className="mt-4 border-t border-ink/15 pt-4">
            {godkant ? (
              <p role="status" className="text-[15px] text-moss">
                Godkänt. Mejlet ligger nu i sändkön.
              </p>
            ) : (
              <>
                <button
                  type="button"
                  disabled={godkannBusy || !queueItemId}
                  onClick={() => void godkann()}
                  className={cn(btnPrimary, "disabled:cursor-wait disabled:opacity-60")}
                >
                  <Send className="h-4 w-4" aria-hidden />
                  {godkannBusy ? "Godkänner…" : "Godkänn och skicka"}
                </button>
                {!queueItemId ? (
                  <p className="mt-3 max-w-[65ch] text-[13px] leading-6 text-ink-subtle">
                    Utkastet saknar ett kö-id och kan inte godkännas härifrån. Se granskningskön
                    under Leads.
                  </p>
                ) : null}
                {godkannFel ? (
                  <p role="alert" className="mt-3 max-w-[65ch] text-[14px] text-danger">
                    {godkannFel}
                  </p>
                ) : null}
              </>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

/** Radens fält som Email studio-kontext: signalen och kontakten följer med
 *  till Förbättra/Personalisera-knapparna, så omskrivningar behåller bolaget
 *  och sammanhanget i stället för att bli generisk text. */
function byggStudioData(
  rad: ListRad,
  prospectId: string,
  subject: string | null | undefined,
  body: string,
  offert: string | null
): EmailStudioData {
  return {
    source: "database",
    businessContext: null,
    email: {
      id: prospectId,
      subject: subject || `Till ${rad.company_name}`,
      body,
      variantLength: "medium",
      variantType: "cold_outreach",
      status: "draft",
      companyId: prospectId,
      contactId: null,
      companyName: rad.company_name,
      signal: signaltext(rad) === "—" ? null : signaltext(rad),
      offer: offert,
      cta: null,
      contactName: rad.contact_name ?? null
    }
  };
}
