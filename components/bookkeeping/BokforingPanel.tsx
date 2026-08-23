"use client";

import { AlertTriangle, Download, Loader2, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Badge, EmptyState, SkeletonRows, btnPrimary, btnSecondary } from "@/components/ui";
import { felmeddelande, readJson } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * Det juridiska förbehållet. Renderas permanent, inte som en engångsruta man
 * klickar bort.
 *
 * Det här produktområdet har reella ekonomiska och legala konsekvenser om
 * agenten har fel, till skillnad från ett medelmåttigt supportsvar. Texten
 * finns också i backenden (`FORBEHALL` i app/api/bookkeeping.py) eftersom den
 * följer med exporten — och båda kopiorna säger samma sak med flit. Ändras
 * den ena ska den andra ändras samtidigt.
 */
const FORBEHALL =
  "Förslag, inte bokföring. Snajp Bokföring föreslår kontering och räknar perioden. " +
  "Förslagen är inte granskade av en auktoriserad redovisningskonsult och ersätter inte en. " +
  "Du ansvarar för att uppgifterna är riktiga innan de förs in i ert bokföringssystem eller " +
  "lämnas till Skatteverket.";

const BAS = "/api/snajp-support/bookkeeping";

//: Vad backendens `kontrollera_fil` släpper igenom. Står listan fel här får
//: användaren ett 422 från servern i stället för en filväljare som inte
//: erbjuder fel fil — sämre, men aldrig osant.
const LASBARA = ".pdf,image/jpeg,image/png,image/webp,image/heic";

type Underlag = {
  id: string;
  filnamn: string;
  status: string;
  datum: string | null;
  motpart: string | null;
  /** STRÄNG, aldrig number. Se `_kr` i app/api/bookkeeping.py. */
  brutto: string | null;
  momssats: string | null;
  kategori: string | null;
  anmarkning: string;
};

type Summor = Record<string, string> & { antal_poster: number };

type Rapport = {
  fran: string;
  till: string;
  status: string;
  brister: string[];
  summor: Summor;
  antal_underlag: number;
  antal_verifikat: number;
};

/** Första och sista dagen i innevarande månad, som ÅÅÅÅ-MM-DD. */
function innevarandeManad(): { fran: string; till: string } {
  const nu = new Date();
  const fran = new Date(nu.getFullYear(), nu.getMonth(), 1);
  const till = new Date(nu.getFullYear(), nu.getMonth() + 1, 0);
  const iso = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  return { fran: iso(fran), till: iso(till) };
}

/**
 * "1250.00" → "1 250,00 kr".
 *
 * Formatering på STRÄNGEN, aldrig via Number(). Ett belopp som passerar en
 * JavaScript-float kan ändras på sista decimalen, och hela poängen med att
 * API:t skickar strängar är att det inte ska hända. `Intl.NumberFormat` tar
 * bara tal, så tusenavgränsaren sätts för hand.
 */
function kronor(varde: string | null): string {
  if (varde === null) return "—";
  const negativt = varde.startsWith("-");
  const [heltal, decimaler = "00"] = varde.replace("-", "").split(".");
  const grupperat = heltal.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${negativt ? "−" : ""}${grupperat},${decimaler.padEnd(2, "0")} kr`;
}

/**
 * Momssatsen som etikett. UPPSLAG, inte räkning.
 *
 * Den första versionen flyttade decimaltecknet med strängoperationer och gav
 * `0.0600` → **60 %**. Felet syntes bara mot Postgres: kolumnen är
 * `numeric(5,4)` och ger `"0.0600"`, medan MemoryStorage gav `"0.06"` — alltså
 * rätt i varje test och fel i drift. (Skalan är numera lika i båda, se
 * `bk_belopp` i app/storage/base.py, men uppslaget står kvar: det kan inte
 * producera en sats som inte finns, vilket ingen aritmetik kan lova.)
 *
 * Satserna är fyra och kända. En okänd sats blir "—" och inte närmaste
 * giltiga — samma regel som `normalisera_momssats` följer i backenden.
 */
const MOMSETIKETT: Record<string, string> = {
  "0.25": "25 %",
  "0.12": "12 %",
  "0.06": "6 %",
  "0": "0 %"
};

function procent(varde: string | null): string {
  if (varde === null) return "—";
  // "0.2500" → "0.25", "0.0000" → "0". Efterföljande nollor bort, sedan ett
  // rent uppslag.
  const normaliserad = varde.includes(".")
    ? varde.replace(/0+$/, "").replace(/\.$/, "")
    : varde;
  return MOMSETIKETT[normaliserad] ?? "—";
}

export function BokforingPanel() {
  const [underlag, setUnderlag] = useState<Underlag[] | null>(null);
  const [rapport, setRapport] = useState<Rapport | null>(null);
  const [period, setPeriod] = useState(innevarandeManad);
  const [laddarUpp, setLaddarUpp] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const filväljare = useRef<HTMLInputElement>(null);

  const hamta = useCallback(async () => {
    setFel(null);
    try {
      const [u, r] = await Promise.all([
        fetch(`${BAS}/underlag?fran=${period.fran}&till=${period.till}`).then((svar) =>
          readJson<{ underlag: Underlag[] }>(svar)
        ),
        fetch(`${BAS}/period?fran=${period.fran}&till=${period.till}`).then((svar) =>
          readJson<Rapport>(svar)
        )
      ]);
      setUnderlag(u?.underlag ?? []);
      setRapport(r);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
      setUnderlag([]);
    }
  }, [period]);

  useEffect(() => {
    void hamta();
  }, [hamta]);

  async function laddaUpp(filer: FileList | null) {
    if (!filer?.length) return;
    setLaddarUpp(true);
    setFel(null);
    try {
      for (const fil of Array.from(filer)) {
        const kropp = new FormData();
        kropp.append("fil", fil);
        const svar = await fetch(`${BAS}/underlag`, { method: "POST", body: kropp });
        await readJson(svar);
      }
      await hamta();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setLaddarUpp(false);
    }
  }

  const klar = rapport?.status === "klar";

  return (
    <div className="space-y-8">
      {/* Förbehållet står ÖVERST och alltid. Se FORBEHALL ovan. */}
      <p className="max-w-[78ch] border-l-2 border-ochre pl-4 text-[0.9375rem] leading-[1.6] text-ink/70">
        <span className="font-semibold text-ink">Förslag, inte bokföring.</span>{" "}
        {FORBEHALL.replace("Förslag, inte bokföring. ", "")}
      </p>

      {/* Period + åtgärder */}
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-[0.8125rem] font-medium text-ink/55">Från</span>
          {/* type="date" och inte en datumväljare: webbläsarens egen är
              tillgänglig, lokaliserad och kostar noll kilobyte. */}
          <input
            type="date"
            value={period.fran}
            onChange={(e) => setPeriod((p) => ({ ...p, fran: e.target.value }))}
            className="focus-ring min-h-11 rounded-input bg-paper2 px-3 text-base"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[0.8125rem] font-medium text-ink/55">Till</span>
          <input
            type="date"
            value={period.till}
            onChange={(e) => setPeriod((p) => ({ ...p, till: e.target.value }))}
            className="focus-ring min-h-11 rounded-input bg-paper2 px-3 text-base"
          />
        </label>

        <input
          ref={filväljare}
          type="file"
          multiple
          accept={LASBARA}
          onChange={(e) => {
            void laddaUpp(e.target.files);
            e.target.value = "";
          }}
          className="sr-only"
        />
        <button
          type="button"
          disabled={laddarUpp}
          onClick={() => filväljare.current?.click()}
          className={btnPrimary}
        >
          {laddarUpp ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <Upload className="h-4 w-4" aria-hidden />
          )}
          Ladda upp underlag
        </button>

        {/* Vanlig länk och inte fetch: filen ska sparas, inte visas, och
            webbläsaren gör nedladdningen bättre än vi gör den. Avstängd när
            perioden inte går ihop — servern svarar 409 ändå (se
            exportera_sie4), men en knapp som ser klickbar ut och ger ett fel
            är sämre än en som säger varför den inte är det. */}
        <a
          href={
            klar
              ? `${BAS}/period.sie?fran=${period.fran}&till=${period.till}` +
                `&foretagsnamn=${encodeURIComponent("Snajp")}&orgnr=`
              : undefined
          }
          aria-disabled={!klar}
          title={klar ? undefined : "Perioden går inte ihop och kan inte exporteras."}
          className={cn(btnSecondary, !klar && "pointer-events-none opacity-40")}
        >
          <Download className="h-4 w-4" aria-hidden />
          Exportera SIE4
        </a>
      </div>

      {fel ? (
        <p role="alert" className="max-w-[70ch] text-[14px] text-danger">
          {fel}
        </p>
      ) : null}

      {/* Periodsummorna */}
      {rapport ? (
        <section>
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="font-display text-[1.25rem]">Perioden</h2>
            <Badge tone={klar ? "good" : "warn"}>
              {klar ? "Går ihop" : "Granska manuellt"}
            </Badge>
          </div>

          <dl className="mt-4 grid gap-x-8 gap-y-3 border-y border-ink/15 py-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              ["Intäkter", rapport.summor.intakter],
              ["Kostnader", rapport.summor.kostnader],
              ["Utgående moms", rapport.summor.utgaende_moms],
              ["Ingående moms", rapport.summor.ingaende_moms],
              ["Moms att betala", rapport.summor.moms_att_betala],
              ["Resultat före skatt", rapport.summor.resultat_fore_skatt]
            ].map(([etikett, varde]) => (
              <div key={etikett} className="flex items-baseline justify-between gap-4">
                <dt className="text-[0.9375rem] text-ink/62">{etikett}</dt>
                <dd className="font-display text-[1.125rem] tabular-nums">{kronor(varde)}</dd>
              </div>
            ))}
          </dl>

          {rapport.brister.length ? (
            <div className="mt-4">
              <p className="flex items-center gap-2 text-[0.9375rem] font-semibold text-ink">
                <AlertTriangle className="h-4 w-4 text-ochre" aria-hidden />
                {rapport.brister.length} sak
                {rapport.brister.length === 1 ? "" : "er"} att titta på
              </p>
              <ul className="mt-2 max-w-[78ch] space-y-1 text-[0.9375rem] text-ink/70">
                {rapport.brister.map((brist) => (
                  <li key={brist}>{brist}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}

      {/* Underlagen */}
      <section>
        <h2 className="font-display text-[1.25rem]">Underlag</h2>
        {underlag === null ? (
          <div className="mt-4">
            <SkeletonRows />
          </div>
        ) : underlag.length === 0 ? (
          <div className="mt-4">
            <EmptyState
              title="Inga underlag i perioden"
              body="Ladda upp ett kvitto eller en faktura, så läser agenten av det och föreslår kontering."
            />
          </div>
        ) : (
          <div className="mt-4 divide-y divide-ink/15 border-y border-ink/15">
            {underlag.map((rad) => (
              <div key={rad.id} className="flex flex-wrap items-baseline gap-x-4 gap-y-1 py-3">
                <span className="w-[6.5rem] shrink-0 text-[0.9375rem] tabular-nums text-ink/62">
                  {rad.datum ?? "—"}
                </span>
                <span className="min-w-0 flex-1 truncate text-[0.9375rem]">
                  {rad.motpart || rad.filnamn}
                </span>
                <span className="text-[0.9375rem] text-ink/62">{procent(rad.momssats)}</span>
                <span className="w-[7.5rem] text-right text-[0.9375rem] font-medium tabular-nums">
                  {kronor(rad.brutto)}
                </span>
                <Badge tone={rad.status === "granska_manuellt" ? "warn" : "good"}>
                  {rad.status === "granska_manuellt" ? "Granska" : "Klar"}
                </Badge>
                {rad.anmarkning ? (
                  <p className="w-full text-[0.875rem] text-ink/55">{rad.anmarkning}</p>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
