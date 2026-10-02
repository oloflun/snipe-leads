"use client";

import { useMemo, useState } from "react";
import { Cell, Tabell, btnPrimary, etikett, meta, tabellRad } from "@/components/ui";
import { felmeddelande } from "@/lib/http/json";
import { useLocale, type Localized } from "@/lib/i18n";
import { parseCsv } from "@/lib/leads/csv";
import {
  IMPORTFALT,
  IMPORTMALLAR,
  gissaKarta,
  kartaForMall,
  radTillImportrad,
  type ImportFalt,
  type Importrad,
  type Karta,
  type Mall
} from "@/lib/leads/importmallar";
import { leadsAnrop } from "@/lib/leads/suite";
import { cn } from "@/lib/utils";

/**
 * CSV-import till en leadslista (Fas 10, Leads Suite F3). Filen läses i
 * webbläsaren, mallen gissas ur rubrikraden (HubSpot, Pipedrive, Salesforce,
 * Upsales eller egen fil) och kunden kan ändra varje fälts kolumn innan
 * `POST /leads/import`. Listan får källan `import`; "Flytta till Iris" på
 * listan gör dedupen mot befintliga bolag.
 */

const MAX_RADER = 2000;

const T = {
  fil: { sv: "CSV-fil", en: "CSV file" },
  lasFel: { sv: "Filen kunde inte läsas.", en: "The file could not be read." },
  tomFil: { sv: "Filen har inga rader under rubrikraden.", en: "The file has no rows below the header row." },
  mall: { sv: "Mall", en: "Template" },
  titel: { sv: "Listans namn", en: "List name" },
  hoppaOver: { sv: "Hoppa över", en: "Skip" },
  forhandsvisning: { sv: "Förhandsvisning, fem första raderna", en: "Preview, first five rows" },
  importerar: { sv: "Importerar…", en: "Importing…" },
  ingetBolag: {
    sv: "Välj vilken kolumn som är bolagsnamnet.",
    en: "Choose which column holds the company name."
  },
  forMangaRader: {
    sv: `Högst ${MAX_RADER} rader per import. Dela upp filen.`,
    en: `At most ${MAX_RADER} rows per import. Split the file.`
  },
  kolumn: { sv: "Kolumn", en: "Column" },
  demo: { sv: "Importen sparas inte i demon.", en: "The import is not saved in the demo." }
} satisfies Record<string, Localized>;

const FALT_ETIKETT: Record<ImportFalt, Localized> = {
  company_name: { sv: "Bolag", en: "Company" },
  orgnr: { sv: "Org.nr", en: "Org. no." },
  contact_name: { sv: "Kontaktperson", en: "Contact person" },
  contact_role: { sv: "Roll", en: "Role" },
  contact_email: { sv: "E-post", en: "Email" },
  contact_phone: { sv: "Telefon", en: "Phone" },
  website: { sv: "Webbplats", en: "Website" },
  status: { sv: "Status", en: "Status" }
};

type Fil = { namn: string; rubriker: string[]; data: string[][] };

export type ImporteradLista = { id: string; titel: string; [nyckel: string]: unknown };

const faltKlass = "focus-ring min-h-11 w-full rounded-input border border-ink/15 bg-paper px-3 text-[16px] text-ink";

export function ImportCsv({ onKlar, demo = false }: Readonly<{ onKlar: (lista: ImporteradLista) => void; demo?: boolean }>) {
  const { text } = useLocale();
  const [fil, setFil] = useState<Fil | null>(null);
  const [mall, setMall] = useState<Mall>("egen");
  const [karta, setKarta] = useState<Karta>({});
  const [efternamn, setEfternamn] = useState<number | undefined>(undefined);
  const [titel, setTitel] = useState("");
  const [fel, setFel] = useState<string | null>(null);
  const [importerar, setImporterar] = useState(false);
  const [kvitto, setKvitto] = useState<Localized | null>(null);

  async function lasFil(f: File | undefined) {
    setFel(null);
    setKvitto(null);
    if (!f) return;
    try {
      const [rubriker, ...data] = parseCsv(await f.text());
      if (!rubriker || data.length === 0) {
        setFil(null);
        setFel(text(T.tomFil));
        return;
      }
      const gissning = gissaKarta(rubriker);
      setFil({ namn: f.name, rubriker, data });
      setMall(gissning.mall);
      setKarta(gissning.karta);
      setEfternamn(gissning.efternamn);
      setTitel(f.name.replace(/\.csv$/i, ""));
    } catch {
      setFil(null);
      setFel(text(T.lasFel));
    }
  }

  function bytMall(ny: Mall) {
    if (!fil) return;
    const k = kartaForMall(fil.rubriker, ny);
    setMall(ny);
    setKarta(k.karta);
    setEfternamn(k.efternamn);
  }

  function bytFalt(falt: ImportFalt, varde: string) {
    setKarta((k) => ({ ...k, [falt]: varde === "" ? undefined : Number(varde) }));
    if (falt === "contact_name") setEfternamn(undefined);
  }

  const rader = useMemo<Importrad[]>(
    () => (fil ? fil.data.map((r) => radTillImportrad(r, karta, efternamn)).filter((r): r is Importrad => r !== null) : []),
    [fil, karta, efternamn]
  );
  const lokaltOverhoppade = fil ? fil.data.length - rader.length : 0;
  const synligaFalt = IMPORTFALT.filter((f) => karta[f] !== undefined);

  async function importera() {
    if (!fil || rader.length === 0 || rader.length > MAX_RADER) return;
    setImporterar(true);
    setFel(null);
    try {
      const svar = await leadsAnrop<{ list: ImporteradLista; antal: number; hoppade_over: number }>("/leads/import", {
        method: "POST",
        body: JSON.stringify({ titel: titel.trim() || fil.namn, rader })
      });
      const hoppade = (svar.hoppade_over ?? 0) + lokaltOverhoppade;
      setKvitto({
        sv: `${svar.antal} rader importerade till ${svar.list.titel}. ${hoppade} hoppades över.`,
        en: `${svar.antal} rows imported to ${svar.list.titel}. ${hoppade} skipped.`
      });
      setFil(null);
      onKlar(svar.list);
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setImporterar(false);
    }
  }

  return (
    <div className="space-y-5">
      <label className={cn(etikett, "flex flex-col gap-1")}>
        {text(T.fil)}
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => void lasFil(e.target.files?.[0])}
          className="focus-ring min-h-11 text-[16px] text-ink file:mr-3 file:min-h-11 file:rounded-input file:border file:border-ink/15 file:bg-paper2 file:px-4 file:text-ink"
        />
      </label>

      {fil ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className={cn(etikett, "flex flex-col gap-1")}>
              {text(T.mall)}
              <select value={mall} onChange={(e) => bytMall(e.target.value as Mall)} className={faltKlass}>
                {(Object.keys(IMPORTMALLAR) as Mall[]).map((m) => (
                  <option key={m} value={m}>
                    {text(IMPORTMALLAR[m].namn)}
                  </option>
                ))}
              </select>
            </label>
            <label className={cn(etikett, "flex flex-col gap-1")}>
              {text(T.titel)}
              <input value={titel} onChange={(e) => setTitel(e.target.value)} maxLength={200} className={faltKlass} />
            </label>
          </div>

          <fieldset>
            <legend className={etikett}>{text(T.kolumn)}</legend>
            <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {IMPORTFALT.map((falt) => (
                <label key={falt} className={cn(etikett, "flex flex-col gap-1")}>
                  {text(FALT_ETIKETT[falt])}
                  <select
                    value={karta[falt] === undefined ? "" : String(karta[falt])}
                    onChange={(e) => bytFalt(falt, e.target.value)}
                    className={faltKlass}
                  >
                    <option value="">{text(T.hoppaOver)}</option>
                    {fil.rubriker.map((r, i) => (
                      <option key={`${r}-${i}`} value={i}>
                        {r || `${text(T.kolumn)} ${i + 1}`}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
          </fieldset>

          {karta.company_name === undefined ? (
            <p role="alert" className="text-[15px] text-danger">
              {text(T.ingetBolag)}
            </p>
          ) : rader.length > 0 ? (
            <div>
              <p className={etikett}>{text(T.forhandsvisning)}</p>
              <div className="mt-2">
                <Tabell
                  ariaLabel={text(T.forhandsvisning)}
                  minBredd={Math.max(480, synligaFalt.length * 140)}
                  kolumner={synligaFalt.map((f) => ({ rubrik: text(FALT_ETIKETT[f]) }))}
                >
                  {rader.slice(0, 5).map((r, i) => (
                    <tr key={i} className={tabellRad}>
                      {synligaFalt.map((f) => (
                        <Cell key={f} className="break-words">
                          {r[f] ?? ""}
                        </Cell>
                      ))}
                    </tr>
                  ))}
                </Tabell>
              </div>
              {lokaltOverhoppade > 0 ? (
                <p className={cn(meta, "mt-2")}>
                  {text({
                    sv: `${lokaltOverhoppade} rader saknar bolagsnamn och hoppas över.`,
                    en: `${lokaltOverhoppade} rows have no company name and are skipped.`
                  })}
                </p>
              ) : null}
            </div>
          ) : null}

          {rader.length > MAX_RADER ? (
            <p role="alert" className="text-[15px] text-danger">
              {text(T.forMangaRader)}
            </p>
          ) : null}

          {demo ? <p className={meta}>{text(T.demo)}</p> : null}
          <button
            type="button"
            onClick={() => void importera()}
            disabled={demo || importerar || rader.length === 0 || rader.length > MAX_RADER}
            className={btnPrimary}
          >
            {importerar
              ? text(T.importerar)
              : text({ sv: `Importera ${rader.length} rader`, en: `Import ${rader.length} rows` })}
          </button>
        </>
      ) : null}

      {fel ? (
        <p role="alert" className="text-[15px] text-danger">
          {fel}
        </p>
      ) : null}
      {kvitto ? (
        <p role="status" className="text-[15px] text-moss">
          {text(kvitto)}
        </p>
      ) : null}
    </div>
  );
}
