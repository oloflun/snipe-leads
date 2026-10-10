"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Inbox,
  Loader2,
  Mail,
  ScanLine,
  Trash2,
  Upload
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Badge,
  Cell,
  EmptyState,
  SkeletonRows,
  Tabell,
  btnLiten,
  btnPrimary,
  btnSecondary,
  tabellRad
} from "@/components/ui";
import { Integritetsnotis } from "@/components/kvitton/Integritetsnotis";
import { HttpJsonError, felmeddelande, readJson } from "@/lib/http/json";
import { cn } from "@/lib/utils";
import { useLocale, type Localized } from "@/lib/i18n";

const ord = (s: string): Localized => ({ sv: s, en: s });

/**
 * Kvittohanterarens arbetsyta — skanning, resultat och sammanfattning.
 *
 * ## Skanningen SPELAS UPP, inte simuleras
 *
 * `POST /skanna` gör hela jobbet i ett anrop och svarar med en händelse per
 * genomläst mejl. Vyn spelar upp händelserna i tur och ordning (mejlet glider
 * in, beloppet markeras när det identifierats) — samma rörelse som demon, men
 * varje rad är en RIKTIG händelse ur körningen, inte en inspelning. Reduced
 * motion hoppar direkt till slutläget.
 *
 * ## Beloppen är strängar hela vägen
 *
 * Samma regel som bokföringspanelen hade och av samma skäl: ett belopp som
 * passerar en JavaScript-float kan ändras på sista decimalen. Formateringen
 * i `kronor` arbetar på strängen.
 */

const BAS = "/api/snajp-support/kvitton";

/** Speglar `LASBARA_MIMETYPER` i app/bookkeeping/underlag.py. */
const LASBARA = ".pdf,image/jpeg,image/png,image/webp,image/heic";

const STEG_MS = 420;

type Mejlkonto = { kopplad: boolean; leverantor?: string; adress?: string };

export type Kvitto = {
  id: string;
  datum: string | null;
  motpart: string | null;
  filnamn: string | null;
  brutto: string | null;
  momssats: string | null;
  kategori: string | null;
  kategorietikett: string;
  /** "intakt" = företagets egen faktura till en kund (sedan 2026-10-07). */
  riktning?: "kostnad" | "intakt";
  status: string;
  betalstatus: string | null;
  kalla: string;
  mejl_amne: string | null;
  mejl_avsandare: string | null;
  valuta: string;
  belopp_original: string | null;
  anmarkning: string;
  // Kvittohanterarens granskning (grundprompten, migration 096). Saknas på
  // rader som lästes in före 2026-10-06.
  granskningsstatus?: Granskningsstatus | null;
  flaggor?: string[];
  forfallodatum?: string | null;
};

export type Granskningsstatus =
  | "KLAR_FÖR_GRANSKNING" // inte-copy: backendens statuskod
  | "BEHÖVER_GRANSKNING" // inte-copy: backendens statuskod
  | "PRIORITERAD_GRANSKNING" // inte-copy: backendens statuskod
  | "KRÄVER_MANUELL_HÄMTNING"; // inte-copy: backendens statuskod

export const PRIORITERAD: Granskningsstatus = "PRIORITERAD_GRANSKNING"; // inte-copy: backendens statuskod
export const MANUELL_HAMTNING: Granskningsstatus = "KRÄVER_MANUELL_HÄMTNING"; // inte-copy: backendens statuskod

/** Flaggorna ur grundpromptens avsnitt 9.1, som granskaren läser dem. */
export const FLAGGETIKETT: Record<string, Localized> = {
  "oläsligt": { sv: "Svårläst", en: "Hard to read" },
  "belopp_stämmer_inte": { sv: "Beloppen går inte ihop", en: "Amounts don't add up" },
  "saknar_moms": { sv: "Moms saknas", en: "VAT missing" },
  "saknar_obligatoriska_fält": { sv: "Uppgifter saknas", en: "Details missing" },
  "utländsk_valuta": { sv: "Utländsk valuta", en: "Foreign currency" },
  "utländsk_leverantör": { sv: "Utländsk leverantör", en: "Foreign supplier" },
  "omvänd_skattskyldighet": { sv: "Omvänd skattskyldighet", en: "Reverse charge" },
  "tvetydigt_datum": { sv: "Tvetydigt datum", en: "Ambiguous date" },
  "osäker_klassning": { sv: "Osäker klassning", en: "Uncertain classification" },
  "osäker_dokumenttyp": { sv: "Osäker dokumenttyp", en: "Uncertain document type" },
  "fel_mottagare": { sv: "Annan mottagare", en: "Different recipient" },
  "möjligt_privat_köp": { sv: "Möjligt privat köp", en: "Possible private purchase" },
  "möjlig_dubblett": { sv: "Möjlig dubblett", en: "Possible duplicate" },
  "misstänkt_bedrägeri": { sv: "Kontrollera betalningsuppgifterna", en: "Check the payment details" },
  "instruktion_i_innehåll": { sv: "Innehåller instruktioner", en: "Contains instructions" },
  "många_rader": { sv: "Många rader", en: "Many lines" },
  "förfaller_snart": { sv: "Förfaller snart", en: "Due soon" },
  "förfallen": { sv: "Förfallen", en: "Overdue" }
};

/** Prioriterade först, sedan de som kräver hämtning, sedan resten. */
const GRANSKNINGSORDNING: Record<string, number> = {
  "PRIORITERAD_GRANSKNING": 0, // inte-copy: backendens statuskod
  "KRÄVER_MANUELL_HÄMTNING": 1, // inte-copy: backendens statuskod
  "BEHÖVER_GRANSKNING": 2, // inte-copy: backendens statuskod
  "KLAR_FÖR_GRANSKNING": 3 // inte-copy: backendens statuskod
};

export function granskningsordning(rad: Kvitto): number {
  return GRANSKNINGSORDNING[rad.granskningsstatus ?? ""] ?? 2;
}

/**
 * Märket för ett kvitto som väntar på granskning. ETT märke per rad: det
 * skarpaste skälet ersätter "Granska" i stället för att staplas ovanpå.
 */
export function Granskningsmarke({ rad }: Readonly<{ rad: Kvitto }>) {
  const { text } = useLocale();
  if (rad.granskningsstatus === PRIORITERAD) {
    return <Badge tone="danger">{text({ sv: "Prioriterad", en: "Priority" })}</Badge>;
  }
  if (rad.granskningsstatus === MANUELL_HAMTNING) {
    return <Badge tone="warn">{text({ sv: "Hämta själv", en: "Fetch it" })}</Badge>;
  }
  return <Badge tone="warn">{text({ sv: "Granska", en: "Review" })}</Badge>;
}

/** Flaggorna som små etiketter. `mork` för Att göra-kortets inverterade yta. */
export function Flaggrad({ flaggor, mork = false }: Readonly<{ flaggor?: string[]; mork?: boolean }>) {
  const { text } = useLocale();
  const kanda = (flaggor ?? []).filter((f) => FLAGGETIKETT[f]);
  if (kanda.length === 0) return null;
  return (
    <ul
      aria-label={text({ sv: "Flaggor", en: "Flags" })}
      className="mt-1.5 flex flex-wrap gap-1.5"
    >
      {kanda.map((f) => (
        <li
          key={f}
          className={cn(
            "rounded-[3px] border px-1.5 py-0.5 text-[0.75rem]",
            mork ? "border-paper/25 text-paper-muted" : "border-ink/15 text-ink-muted"
          )}
        >
          {text(FLAGGETIKETT[f])}
        </li>
      ))}
    </ul>
  );
}

type Intakter = {
  antal: number;
  antal_klara: number;
  antal_granska: number;
  totalt: string;
  moms: string;
  antal_obetalda: number;
  obetalt: string;
};

type Sammanfattning = {
  intakter?: Intakter;
  antal: number;
  antal_klara: number;
  antal_granska: number;
  totalt: string;
  moms: string;
  per_kategori: { kategori: string; etikett: string; antal: number; summa: string }[];
  text?: string;
};

type Handelse = {
  mejl_id: string;
  avsandare: string;
  amne: string;
  datum: string;
  utfall: "kvitto" | "kvitto_granska" | "ej_kvitto" | "redan_last";
  belopp?: string | null;
  belopp_original?: string | null;
  kategori?: string | null;
  motpart?: string | null;
  granskningsstatus?: Granskningsstatus | null;
};

export function innevarandeManad(): { fran: string; till: string } {
  const nu = new Date();
  const fran = new Date(nu.getFullYear(), nu.getMonth(), 1);
  const till = new Date(nu.getFullYear(), nu.getMonth() + 1, 0);
  const iso = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  return { fran: iso(fran), till: iso(till) };
}

export function kronor(varde: string | null): string {
  if (varde === null) return "—";
  const negativt = varde.startsWith("-");
  const [heltal, decimaler = "00"] = varde.replace("-", "").split(".");
  const grupperat = heltal.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${negativt ? "−" : ""}${grupperat},${decimaler.padEnd(2, "0")} kr`;
}

export function arIntakt(rad: Pick<Kvitto, "riktning">): boolean {
  return rad.riktning === "intakt";
}

/** Beloppet som det står i listorna: en intäkt med plustecken. */
export function radbelopp(rad: Kvitto): string {
  if (rad.brutto === null) return rad.belopp_original ?? "—";
  return `${arIntakt(rad) ? "+" : ""}${kronor(rad.brutto)}`;
}

export const KUNDFAKTURA: Localized = { sv: "Kundfaktura", en: "Customer invoice" };

/**
 * Människans besked om att ett underlag i granskningen är en kundfaktura
 * (intäkt) eller ett kvitto (kostnad). Svarar null eller felet att visa.
 */
export async function bytRiktning(rad: Kvitto, riktning: "kostnad" | "intakt"): Promise<Localized | null> {
  try {
    const svar = await fetch(`${BAS}/${rad.id}/riktning`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ riktning })
    });
    await readJson(svar);
    return null;
  } catch (orsak) {
    return ord(feltext(orsak));
  }
}

const MOMSETIKETT: Record<string, string> = {
  "0.25": "25 %",
  "0.12": "12 %",
  "0.06": "6 %",
  "0": "0 %"
};

function procent(varde: string | null): string {
  if (varde === null) return "—";
  const normaliserad = varde.includes(".")
    ? varde.replace(/0+$/, "").replace(/\.$/, "")
    : varde;
  return MOMSETIKETT[normaliserad] ?? "—";
}

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

/**
 * Att göra-kortet — samma bärande yta som översikterna fick 2026-09-20:
 * antalet i klartext, tonal inversion (sidans enda), och HANDLINGEN på raden.
 * Här är handlingen inte en länk till en kö utan själva godkännandet, för
 * granskningen bor i den här vyn. Underraden är anmärkningen, alltså skälet
 * till att kvittot väntar. Tom kö ritar ingenting: tabellen nedanför bär
 * redan statusen, och en tom svart ruta hade skrikit i onödan.
 *
 * Exporterad för att kunna monteras ensam i en skiss under verifiering.
 */
export function KvittoAttGora({
  rader,
  onGodkann
}: Readonly<{ rader: Kvitto[]; onGodkann: (rad: Kvitto) => void }>) {
  const { text } = useLocale();
  if (rader.length === 0) return null;
  const fler = rader.length - 5;
  return (
    <section aria-label={text({ sv: "Att göra", en: "To do" })} className="rounded-card bg-ink p-6 text-paper md:p-8">
      <h2 className="text-[1.25rem] font-semibold tracking-[-0.01em]">
        {rader.length === 1
          ? text({ sv: "1 kvitto väntar på dig", en: "1 receipt is waiting for you" })
          : text({ sv: `${rader.length} kvitton väntar på dig`, en: `${rader.length} receipts are waiting for you` })}
      </h2>
      <ul className="mt-5 border-t border-paper/15">
        {[...rader].sort((a, b) => granskningsordning(a) - granskningsordning(b)).slice(0, 5).map((rad) => (
          <li
            key={rad.id}
            className="grid grid-cols-12 items-center gap-x-4 border-b border-paper/15 py-3.5"
          >
            <div className="col-span-12 min-w-0 sm:col-span-7">
              <p className="flex min-w-0 items-center gap-2 text-[0.9375rem] font-semibold">
                <span className="truncate">
                  {rad.motpart || rad.mejl_amne || rad.filnamn || text({ sv: "Kvitto", en: "Receipt" })}
                </span>
                {rad.granskningsstatus === PRIORITERAD ? (
                  <span className="shrink-0 rounded-[3px] bg-paper px-1.5 py-0.5 text-[0.6875rem] font-semibold uppercase tracking-[0.04em] text-ink">
                    {text({ sv: "Prioriterad", en: "Priority" })}
                  </span>
                ) : null}
              </p>
              <p className="mt-0.5 line-clamp-2 text-[0.8125rem] text-paper-muted">
                {rad.anmarkning ||
                  [rad.datum, rad.kategorietikett].filter(Boolean).join(" · ") ||
                  text({ sv: "Uppgifter saknas.", en: "Details missing." })}
              </p>
              <Flaggrad flaggor={rad.flaggor} mork />
            </div>
            <div className="col-span-12 mt-2 flex items-center justify-between gap-4 sm:col-span-5 sm:mt-0 sm:justify-end">
              <span className="num text-[0.875rem] tabular-nums text-paper-muted">
                {radbelopp(rad)}
              </span>
              <button
                type="button"
                onClick={() => onGodkann(rad)}
                className="focus-ring inline-flex min-h-9 shrink-0 items-center rounded-input bg-paper px-4 text-[0.875rem] font-semibold text-ink transition-colors hover:bg-paper/85"
              >
                {text({ sv: "Godkänn", en: "Approve" })}
              </button>
            </div>
          </li>
        ))}
      </ul>
      {fler > 0 ? (
        <p className="mt-4 text-[0.8125rem] text-paper-muted">
          {fler === 1
            ? text({ sv: "1 till i tabellen nedan.", en: "1 more in the table below." })
            : text({ sv: `${fler} till i tabellen nedan.`, en: `${fler} more in the table below.` })}
        </p>
      ) : null}
    </section>
  );
}

/**
 * Godkännandet av ett flaggat kvitto: frågar efter det som saknas (belopp,
 * moms, datum, butik, kategori, betalstatus) och postar. Fristående så att
 * Översikten (KvittoOversikt) godkänner med exakt samma frågor som tabellen.
 *
 * Svarar null när kvittot gick igenom, "avbrutet" när en fråga stängdes, och
 * annars felet att visa.
 */
export async function godkannKvitto(
  rad: Kvitto,
  text: (v: Localized) => string
): Promise<Localized | "avbrutet" | null> {
  const kropp: Record<string, string> = {};
  if (rad.brutto === null) {
    const belopp = window.prompt(
      rad.belopp_original
        ? text({
            sv: `Kvittot är på ${rad.belopp_original}. Ange beloppet omräknat till kronor (t.ex. 495,00):`,
            en: `The receipt is for ${rad.belopp_original}. Enter the amount converted to SEK (e.g. 495.00):`
          })
        : text({
            sv: "Kvittot saknar läsbart belopp. Ange beloppet i kronor (t.ex. 495,00):",
            en: "The receipt has no readable amount. Enter the amount in SEK (e.g. 495.00):"
          })
    );
    if (!belopp) return "avbrutet";
    kropp.brutto = belopp.replace(/\s/g, "").replace(",", ".");
  }
  if (rad.momssats === null) {
    const sats = window.prompt(
      text({ sv: "Ange momssatsen i procent (25, 12, 6 eller 0):", en: "Enter the VAT rate in percent (25, 12, 6 or 0):" })
    );
    if (sats === null) return "avbrutet";
    const normaliserad = { "25": "0.25", "12": "0.12", "6": "0.06", "0": "0" }[sats.trim()];
    if (!normaliserad) {
      return { sv: "Momssatsen ska vara 25, 12, 6 eller 0.", en: "The VAT rate must be 25, 12, 6 or 0." };
    }
    kropp.momssats = normaliserad;
  }
  if (rad.datum === null) {
    const datum = window.prompt(
      text({ sv: "Kvittot saknar datum. Ange köpdatum (ÅÅÅÅ-MM-DD):", en: "The receipt has no date. Enter the purchase date (YYYY-MM-DD):" })
    );
    if (!datum) return "avbrutet";
    kropp.datum = datum.trim();
  }
  if (rad.motpart === null) {
    const motpart = window.prompt(
      arIntakt(rad)
        ? text({ sv: "Vilken kund är fakturan till?", en: "Which customer is the invoice to?" })
        : text({ sv: "Vilken butik eller leverantör är kvittot från?", en: "Which shop or supplier is the receipt from?" })
    );
    if (!motpart) return "avbrutet";
    kropp.motpart = motpart.trim();
  }
  if (rad.kategori === null && !arIntakt(rad)) {
    const kategori = window.prompt(
      text({
        sv: "Ange kategori: drivmedel, biljett, kost_och_logi, representation, kontorsmateriel, programvara, forbrukningsinventarier eller ovrig_extern_kostnad:",
        en: "Enter category: drivmedel, biljett, kost_och_logi, representation, kontorsmateriel, programvara, forbrukningsinventarier or ovrig_extern_kostnad:"
      })
    );
    if (!kategori) return "avbrutet";
    kropp.kategori = kategori.trim().toLowerCase();
  }
  if (rad.betalstatus === null) {
    // Frågas, gissas aldrig: betalstatus avgör om kvittot bokas mot
    // bankkontot eller som en obetald skuld.
    const betald = window.confirm(
      arIntakt(rad)
        ? text({
            sv: "Har kunden redan betalat fakturan?\n\nOK = betald\nAvbryt = obetald (kundfordran)",
            en: "Has the customer already paid the invoice?\n\nOK = paid\nCancel = unpaid (receivable)"
          })
        : text({
            sv: "Är kvittot redan betalt?\n\nOK = betalt (kort, Swish, kontant)\nAvbryt = obetald faktura",
            en: "Is the receipt already paid?\n\nOK = paid (card, Swish, cash)\nCancel = unpaid invoice"
          })
    );
    kropp.betalstatus = betald ? "betald" : "obetald";
  }
  try {
    const svar = await fetch(`${BAS}/${rad.id}/godkann`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(kropp)
    });
    const data = await readJson<{ godkand: boolean; brister?: string[] }>(svar);
    if (data && !data.godkand) {
      return {
        sv: `Kvittot kunde inte godkännas ännu: ${(data.brister ?? []).join("; ") || "fält saknas."}`,
        en: `The receipt could not be approved yet: ${(data.brister ?? []).join("; ") || "fields missing."}`
      };
    }
    return null;
  } catch (orsak) {
    return ord(feltext(orsak));
  }
}

export function KvittoYta() {
  const { text } = useLocale();
  const [konto, setKonto] = useState<Mejlkonto | null>(null);
  const [kvitton, setKvitton] = useState<Kvitto[] | null>(null);
  const [samman, setSamman] = useState<Sammanfattning | null>(null);
  const [period, setPeriod] = useState(innevarandeManad);
  const [fel, setFel] = useState<Localized | null>(null);

  const [skannar, setSkannar] = useState(false);
  const [handelser, setHandelser] = useState<Handelse[] | null>(null);
  const [visadeHandelser, setVisadeHandelser] = useState(0);

  const [laddarUpp, setLaddarUpp] = useState(false);
  const [uppladdningsfel, setUppladdningsfel] = useState<string[]>([]);
  const [rensar, setRensar] = useState(false);
  const filväljare = useRef<HTMLInputElement>(null);
  const fakturaväljare = useRef<HTMLInputElement>(null);

  const hamta = useCallback(async () => {
    setFel(null);
    try {
      const [kontoSvar, listaSvar, sammanSvar] = await Promise.all([
        fetch(`${BAS}/mejlkonto`).then((s) => readJson<Mejlkonto>(s)),
        fetch(`${BAS}?fran=${period.fran}&till=${period.till}`).then((s) =>
          readJson<{ kvitton: Kvitto[] }>(s)
        ),
        fetch(`${BAS}/sammanfattning?fran=${period.fran}&till=${period.till}`).then((s) =>
          readJson<Sammanfattning>(s)
        )
      ]);
      setKonto(kontoSvar);
      setKvitton(listaSvar?.kvitton ?? []);
      setSamman(sammanSvar);
    } catch (orsak) {
      setFel(ord(feltext(orsak)));
      setKvitton([]);
    }
  }, [period]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  // Uppspelningen av skanningens händelser. Se docstringen.
  useEffect(() => {
    if (!handelser || visadeHandelser >= handelser.length) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setVisadeHandelser(handelser.length);
      return;
    }
    const timer = window.setTimeout(
      () => setVisadeHandelser((n) => n + 1),
      STEG_MS
    );
    return () => window.clearTimeout(timer);
  }, [handelser, visadeHandelser]);

  const uppspelningKlar = handelser !== null && visadeHandelser >= handelser.length;

  async function skanna() {
    setSkannar(true);
    setFel(null);
    setHandelser(null);
    setVisadeHandelser(0);
    try {
      const svar = await fetch(
        `${BAS}/skanna?fran=${period.fran}&till=${period.till}`,
        { method: "POST" }
      );
      const data = await readJson<{
        handelser: Handelse[];
        kvitton: Kvitto[];
        sammanfattning: Sammanfattning;
        text: string;
      }>(svar);
      setHandelser(data?.handelser ?? []);
      setKvitton(data?.kvitton ?? []);
      setSamman(data ? { ...data.sammanfattning, text: data.text } : null);
    } catch (orsak) {
      setFel(ord(feltext(orsak)));
    } finally {
      setSkannar(false);
    }
  }

  async function laddaUpp(filer: File[], riktning: "kostnad" | "intakt" = "kostnad") {
    if (!filer.length) return;
    setLaddarUpp(true);
    setFel(null);
    setUppladdningsfel([]);
    const misslyckade: string[] = [];
    try {
      for (const fil of filer) {
        try {
          const kropp = new FormData();
          kropp.append("fil", fil);
          if (riktning === "intakt") kropp.append("riktning", "intakt");
          const svar = await fetch(`${BAS}/underlag`, { method: "POST", body: kropp });
          await readJson(svar);
        } catch (orsak) {
          misslyckade.push(`${fil.name}: ${feltext(orsak)}`);
        }
      }
      setUppladdningsfel(misslyckade);
      await hamta();
    } finally {
      setLaddarUpp(false);
    }
  }

  async function godkann(rad: Kvitto) {
    setFel(null);
    const utfall = await godkannKvitto(rad, text);
    if (utfall === "avbrutet") return;
    if (utfall) setFel(utfall);
    await hamta();
  }

  async function andraRiktning(rad: Kvitto) {
    setFel(null);
    const utfall = await bytRiktning(rad, arIntakt(rad) ? "kostnad" : "intakt");
    if (utfall) setFel(utfall);
    await hamta();
  }

  async function rensa() {
    if (!kvitton?.length) return;
    const bekraftat = window.confirm(
      text({
        sv: `Rensa ${period.fran} till ${period.till}?\n\n${kvitton.length} kvitton raderas. Det går inte att ångra.`,
        en: `Clear ${period.fran} to ${period.till}?\n\n${kvitton.length} receipts will be deleted. This cannot be undone.`
      })
    );
    if (!bekraftat) return;
    setRensar(true);
    setFel(null);
    try {
      const svar = await fetch(`${BAS}/period?fran=${period.fran}&till=${period.till}`, {
        method: "DELETE"
      });
      await readJson(svar);
      setHandelser(null);
      await hamta();
    } catch (orsak) {
      setFel(ord(feltext(orsak)));
    } finally {
      setRensar(false);
    }
  }

  const harKvitton = (kvitton?.length ?? 0) > 0;

  const datumfalt = (
    <div className="flex flex-wrap items-end gap-2">
      <label className="flex flex-col gap-1">
        <span className="text-[0.75rem] font-medium text-ink-subtle">{text({ sv: "Från", en: "From" })}</span>
        <input
          type="date"
          value={period.fran}
          onChange={(e) => setPeriod((p) => ({ ...p, fran: e.target.value }))}
          className="focus-ring h-9 rounded-input bg-paper2 px-2.5 text-[0.875rem]"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-[0.75rem] font-medium text-ink-subtle">{text({ sv: "Till", en: "To" })}</span>
        <input
          type="date"
          value={period.till}
          onChange={(e) => setPeriod((p) => ({ ...p, till: e.target.value }))}
          className="focus-ring h-9 rounded-input bg-paper2 px-2.5 text-[0.875rem]"
        />
      </label>
    </div>
  );

  return (
    <div className="space-y-8">
      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[14px] text-danger">
          {text(fel)}
        </p>
      ) : null}

      {/* Mejlkontot och skanningen. */}
      <section>
        <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-3">
          {datumfalt}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={skannar || !konto?.kopplad}
              onClick={() => void skanna()}
              title={
                konto?.kopplad
                  ? undefined
                  : text({ sv: "Ingen inkorg kopplad.", en: "No mailbox connected." })
              }
              className={cn(btnPrimary, btnLiten)}
            >
              {skannar ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <ScanLine className="h-4 w-4" aria-hidden />
              )}
              {text({ sv: "Skanna inkorgen", en: "Scan mailbox" })}
            </button>
            <button
              type="button"
              disabled={laddarUpp}
              onClick={() => filväljare.current?.click()}
              className={cn(btnSecondary, btnLiten)}
            >
              {laddarUpp ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Upload className="h-4 w-4" aria-hidden />
              )}
              {text({ sv: "Ladda upp kvitto", en: "Upload receipt" })}
            </button>
            <button
              type="button"
              disabled={laddarUpp}
              onClick={() => fakturaväljare.current?.click()}
              title={text({
                sv: "En faktura ni skickat till en kund. Den räknas som intäkt, inte som utlägg.",
                en: "An invoice you sent to a customer. It counts as income, not as an expense."
              })}
              className={cn(btnSecondary, btnLiten)}
            >
              <Upload className="h-4 w-4" aria-hidden />
              {text({ sv: "Ladda upp kundfaktura", en: "Upload customer invoice" })}
            </button>
            <a
              href={
                harKvitton
                  ? `${BAS}/export.csv?fran=${period.fran}&till=${period.till}`
                  : undefined
              }
              aria-disabled={!harKvitton}
              title={harKvitton ? undefined : text({ sv: "Det finns inga kvitton att exportera.", en: "There are no receipts to export." })}
              className={cn(btnSecondary, btnLiten, !harKvitton && "pointer-events-none opacity-40")}
            >
              <Download className="h-4 w-4" aria-hidden />
              {text({ sv: "Exportera", en: "Export" })}
            </a>
            <button
              type="button"
              disabled={rensar || !harKvitton}
              onClick={() => void rensa()}
              title={harKvitton ? undefined : text({ sv: "Det finns inget att rensa i perioden.", en: "There is nothing to clear in the period." })}
              className={cn(btnSecondary, btnLiten)}
            >
              {rensar ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Trash2 className="h-4 w-4" aria-hidden />
              )}
              {text({ sv: "Rensa", en: "Clear" })}
            </button>
          </div>
        </div>

        <p className="mt-3 flex flex-wrap items-center gap-2 text-[0.875rem] text-ink-muted">
          <Mail className="h-4 w-4 shrink-0 text-mineral" aria-hidden />
          {konto === null ? (
            text({ sv: "Hämtar mejlkontot…", en: "Loading the email account…" })
          ) : konto.kopplad ? (
            <>
              {text({ sv: "Kopplad inkorg:", en: "Connected mailbox:" })}{" "}
              <span className="font-medium text-ink">{konto.adress}</span>
              <Badge tone="good">
                {konto.leverantor === "gmail"
                  ? "Gmail"
                  : konto.leverantor === "microsoft"
                    ? "Outlook/Hotmail"
                    : text({ sv: "Demokonto", en: "Demo account" })}
              </Badge>
            </>
          ) : (
            <>
              {text({ sv: "Ingen inkorg kopplad.", en: "No mailbox connected." })}{" "}
              <a
                href="mailto:kontakt@snajp.se?subject=Koppla%20mejl%20till%20Kvittohanteraren"
                className="focus-ring rounded-input font-medium text-ink underline underline-offset-4 hover:text-ochre"
              >
                {text({ sv: "Hör av dig", en: "Get in touch" })}
              </a>{" "}
              {text({ sv: "så kopplar vi den.", en: "and we will connect it." })}
            </>
          )}
        </p>
      </section>

      {/* Inkorgsvyn — uppspelningen av senaste skanningen. */}
      {handelser !== null ? (
        <section className="rounded-card border border-ink/12 bg-paper2/30 p-5">
          <div className="flex items-baseline justify-between gap-4">
            <p className="kicker flex items-center gap-2 text-mineral">
              <Inbox className="h-3.5 w-3.5" aria-hidden />
              {text({ sv: "Inkorgen", en: "Mailbox" })}
            </p>
            <p className="text-[0.75rem] tabular-nums text-mineral" role="status">
              {uppspelningKlar
                ? text({ sv: `${handelser.length} mejl genomlästa`, en: `${handelser.length} emails read` })
                : text({
                    sv: `läser mejl ${Math.min(visadeHandelser + 1, handelser.length)} av ${handelser.length}…`,
                    en: `reading email ${Math.min(visadeHandelser + 1, handelser.length)} of ${handelser.length}…`
                  })}
            </p>
          </div>
          <ul className="mt-3 divide-y divide-ink/10 border-t border-ink/10">
            {handelser.slice(0, visadeHandelser).map((h) => (
              <li key={h.mejl_id} className="animate-mejl-in py-2.5">
                <div className="flex min-w-0 items-baseline justify-between gap-3">
                  <p className="min-w-0 truncate text-[0.875rem] font-medium text-ink">
                    {h.avsandare}
                    <span className="ml-2 font-normal text-ink-subtle">{h.amne}</span>
                  </p>
                  <span className="shrink-0">
                    {h.utfall === "kvitto" ? (
                      <Badge tone="good">{text({ sv: "Kvitto", en: "Receipt" })}</Badge>
                    ) : h.utfall === "kvitto_granska" && h.granskningsstatus === PRIORITERAD ? (
                      <Badge tone="danger">{text({ sv: "Prioriterad", en: "Priority" })}</Badge>
                    ) : h.utfall === "kvitto_granska" ? (
                      <Badge tone="warn">{text({ sv: "Granska", en: "Review" })}</Badge>
                    ) : h.utfall === "redan_last" ? (
                      <span className="text-[0.75rem] text-mineral">{text({ sv: "redan inläst", en: "already read" })}</span>
                    ) : (
                      <span className="text-[0.75rem] text-mineral">{text({ sv: "inte ett kvitto", en: "not a receipt" })}</span>
                    )}
                  </span>
                </div>
                {h.belopp || h.belopp_original ? (
                  <p className="mt-1 font-mono text-[0.75rem] text-ink-subtle">
                    {text({ sv: "Belopp:", en: "Amount:" })}{" "}
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
          {uppspelningKlar ? (
            <p className="mt-3 flex items-center gap-2 border-t border-ink/10 pt-3 text-[0.8125rem] text-moss">
              <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden />
              {text({ sv: "Klart.", en: "Done." })}
            </p>
          ) : null}
        </section>
      ) : null}

      {/* Uppladdningsfelen, per fil. */}
      {uppladdningsfel.length ? (
        <div role="status" className="max-w-[78ch] border-y border-ink/15 py-3">
          <p className="flex items-center gap-2 text-[0.9375rem] font-semibold text-ink">
            <AlertTriangle className="h-4 w-4 text-warning" aria-hidden />
            {uppladdningsfel.length}{" "}
            {uppladdningsfel.length === 1
              ? text({ sv: "fil kom inte in", en: "file did not get in" })
              : text({ sv: "filer kom inte in", en: "files did not get in" })}
          </p>
          <ul className="mt-2 space-y-1">
            {uppladdningsfel.map((rad, i) => (
              <li key={i} className="text-[0.875rem] text-ink-muted">
                {rad}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* Det som väntar på kunden, före tabellen. Härleds ur samma lista som
          tabellen, så kortet töms i samma stund som sista godkännandet går
          igenom — ingen egen hämtning, inget eget tillstånd. */}
      <KvittoAttGora
        rader={(kvitton ?? []).filter((rad) => rad.status === "granska_manuellt")}
        onGodkann={(rad) => void godkann(rad)}
      />

      {/* Kvittona. */}
      <section>
        <h2 className="font-display text-[1.25rem]">{text({ sv: "Kvitton i perioden", en: "Receipts in the period" })}</h2>
        {kvitton === null ? (
          <div className="mt-4">
            <SkeletonRows />
          </div>
        ) : kvitton.length === 0 ? (
          <div className="mt-4">
            <EmptyState title={text({ sv: "Inga kvitton i perioden", en: "No receipts in the period" })} />
          </div>
        ) : (
          <div className="mt-4">
            <Tabell
              ariaLabel={text({ sv: "Kvitton i perioden", en: "Receipts in the period" })}
              kolumner={[
                { rubrik: text({ sv: "Datum", en: "Date" }), bredd: "12%" },
                { rubrik: text({ sv: "Motpart", en: "Counterparty" }), bredd: "32%" },
                { rubrik: text({ sv: "Kategori", en: "Category" }), bredd: "16%" },
                { rubrik: text({ sv: "Källa", en: "Source" }), bredd: "10%" },
                { rubrik: text({ sv: "Moms", en: "VAT" }), bredd: "8%", hoger: true },
                { rubrik: text({ sv: "Belopp", en: "Amount" }), bredd: "12%", hoger: true },
                { rubrik: text({ sv: "Status", en: "Status" }), bredd: "10%", hoger: true }
              ]}
            >
              {kvitton.map((rad) => (
                <tr key={rad.id} className={tabellRad}>
                  <Cell>
                    <span className="tabular-nums text-ink-muted">{rad.datum ?? "—"}</span>
                  </Cell>
                  <Cell titel>
                    <p className="truncate">{rad.motpart || rad.mejl_amne || rad.filnamn}</p>
                    {rad.anmarkning ? (
                      <p className="mt-1 text-[0.875rem] font-normal text-ink-subtle">
                        {rad.anmarkning}
                      </p>
                    ) : null}
                    <Flaggrad flaggor={rad.flaggor} />
                  </Cell>
                  <Cell>
                    {arIntakt(rad) ? (
                      <Badge tone="good">{text(KUNDFAKTURA)}</Badge>
                    ) : (
                      <span className="text-ink-muted">{rad.kategorietikett}</span>
                    )}
                  </Cell>
                  <Cell>
                    <span className="text-ink-muted">
                      {rad.kalla === "mejl" ? text({ sv: "Mejl", en: "Email" }) : text({ sv: "Uppladdad", en: "Uploaded" })}
                    </span>
                  </Cell>
                  <Cell hoger>
                    <span className="text-ink-muted">{procent(rad.momssats)}</span>
                  </Cell>
                  <Cell hoger>
                    <span className={cn("font-medium", arIntakt(rad) && "text-moss")}>{radbelopp(rad)}</span>
                  </Cell>
                  <Cell hoger>
                    <span className="flex flex-wrap items-center justify-end gap-1.5">
                      {rad.status === "granska_manuellt" ? (
                        <Granskningsmarke rad={rad} />
                      ) : (
                        <Badge tone="good">{text({ sv: "Klar", en: "Done" })}</Badge>
                      )}
                      {rad.status === "granska_manuellt" ? (
                        <button
                          type="button"
                          onClick={() => void godkann(rad)}
                          className="focus-ring rounded-input text-[0.8125rem] font-medium text-ink underline underline-offset-4 hover:text-ochre"
                        >
                          {text({ sv: "Godkänn", en: "Approve" })}
                        </button>
                      ) : null}
                      {rad.status === "granska_manuellt" ? (
                        <button
                          type="button"
                          onClick={() => void andraRiktning(rad)}
                          className="focus-ring rounded-input text-[0.8125rem] text-ink-muted underline underline-offset-4 hover:text-ink"
                        >
                          {arIntakt(rad)
                            ? text({ sv: "Är ett kvitto", en: "Is a receipt" })
                            : text({ sv: "Är en kundfaktura", en: "Is a customer invoice" })}
                        </button>
                      ) : null}
                    </span>
                  </Cell>
                </tr>
              ))}
            </Tabell>
          </div>
        )}
      </section>

      <input
        ref={filväljare}
        type="file"
        multiple
        accept={LASBARA}
        onChange={(e) => {
          void laddaUpp(Array.from(e.target.files ?? []));
          e.target.value = "";
        }}
        className="sr-only"
      />
      <input
        ref={fakturaväljare}
        type="file"
        multiple
        accept={LASBARA}
        onChange={(e) => {
          void laddaUpp(Array.from(e.target.files ?? []), "intakt");
          e.target.value = "";
        }}
        className="sr-only"
      />
    </div>
  );
}

/**
 * Sammanfattningsrutan — högerkolumnens topp. Egen komponent så att
 * serverskalet kan placera den bredvid chatten utan att arbetsytan behöver
 * veta om kolumnbrytningen.
 */
export function KvittoSammanfattning() {
  const { text } = useLocale();
  const [samman, setSamman] = useState<Sammanfattning | null>(null);
  const [period] = useState(innevarandeManad);

  useEffect(() => {
    let aktiv = true;
    const hamta = () =>
      fetch(`${BAS}/sammanfattning?fran=${period.fran}&till=${period.till}`)
        .then((s) => readJson<Sammanfattning>(s))
        .then((data) => {
          if (aktiv) setSamman(data);
        })
        .catch(() => undefined);
    void hamta();
    // Sammanfattningen ändras när en skanning eller uppladdning skriver — den
    // hämtas om var 15:e sekund i stället för att koppla ihop komponenterna.
    const timer = window.setInterval(hamta, 15_000);
    return () => {
      aktiv = false;
      window.clearInterval(timer);
    };
  }, [period]);

  return (
    <div className="rounded-card border border-ink/12 bg-paper p-5">
      <p className="kicker text-mineral">{text({ sv: "Sammanfattning", en: "Summary" })}</p>
      {samman === null ? (
        <p className="mt-3 text-[0.875rem] text-ink-subtle">{text({ sv: "Hämtar…", en: "Loading…" })}</p>
      ) : samman.antal === 0 && !samman.intakter?.antal ? (
        <p className="mt-3 text-[0.875rem] leading-6 text-ink-subtle">{text({ sv: "Inga inlästa kvitton.", en: "No receipts read." })}</p>
      ) : (
        <>
          <p className="mt-3 font-display text-[2.25rem] leading-none tracking-[-0.01em]">
            {kronor(samman.totalt)}
          </p>
          <p className="mt-1 text-[0.8125rem] text-ink-subtle">
            {text({
              sv: `${samman.antal_klara} avlästa kvitton · ingående moms ${kronor(samman.moms)}`,
              en: `${samman.antal_klara} receipts read · input VAT ${kronor(samman.moms)}`
            })}
          </p>
          {samman.intakter?.antal_klara ? (
            <p className="mt-3 flex items-baseline justify-between gap-4 rounded-input bg-moss/10 px-3 py-2 text-[0.875rem]">
              <span className="text-ink-muted">
                {text({ sv: "Fakturerat", en: "Invoiced" })}
                <span className="ml-1.5 text-[0.75rem] text-mineral">×{samman.intakter.antal_klara}</span>
              </span>
              <span className="num font-medium text-ink">+{kronor(samman.intakter.totalt)}</span>
            </p>
          ) : null}
          {samman.per_kategori.length ? (
            <dl className="mt-4 divide-y divide-ink/10 border-y border-ink/10">
              {samman.per_kategori.map((rad) => (
                <div key={rad.kategori} className="flex items-baseline justify-between gap-4 py-2">
                  <dt className="text-[0.875rem] text-ink-muted">
                    {rad.etikett}
                    <span className="ml-1.5 text-[0.75rem] text-mineral">×{rad.antal}</span>
                  </dt>
                  <dd className="num text-[0.875rem]">{kronor(rad.summa)}</dd>
                </div>
              ))}
            </dl>
          ) : null}
          {samman.text ? (
            <p className="mt-4 text-[0.875rem] leading-6 text-ink-muted">{samman.text}</p>
          ) : null}
        </>
      )}
      <div className="mt-4">
        <Integritetsnotis />
      </div>
    </div>
  );
}
