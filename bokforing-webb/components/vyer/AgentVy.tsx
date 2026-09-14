"use client";

import { AlertTriangle, FileUp, Loader2, ScanLine, Upload } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, btnLiten, btnSecondary } from "@/components/ui";
import { BAS, LASBARA, type Underlag } from "@/lib/api";
import { kronor, procent } from "@/lib/format";
import { HttpJsonError, felmeddelande, readJson } from "@/lib/http/json";
import { useBokforing } from "@/lib/useBokforing";
import { cn } from "@/lib/utils";

/**
 * Bokföringsagenten: hit släpper kunden sina PDF:er och foton.
 *
 * Uppladdningslogiken är huvudappens beprövade (BokforingPanel.laddaUpp):
 * en fil i taget med utfall per fil, batchen stoppas vid kreditslut, och
 * filer som föll på något övergående (kvot, nätet, serverhicka) samlas bakom
 * en Försök igen-knapp — File-objekten finns kvar i webbläsaren.
 *
 * Dubbelgenomgången görs av BACKENDEN inne i ett och samma anrop
 * (las_underlag kör avläsning + kontrolläsning). Vyn påstår därför aldrig
 * "genomgång 1 klar" i realtid — det vore ett hittepå-förlopp — utan säger
 * vad som pågår och visar de avlästa fälten när svaret kommer.
 */

type Utfall =
  | { slag: "klar" | "granska"; namn: string; underlag: Underlag; brister: string[] }
  | { slag: "fel" | "ej_behandlad"; namn: string; orsak: string };

type Uppladdningssvar = {
  underlag: Underlag;
  status: string;
  brister: string[];
};

function tolkaFel(orsak: unknown): { text: string; klass: string | null; status: number } {
  if (orsak instanceof HttpJsonError) {
    const kropp =
      orsak.body && typeof orsak.body === "object" ? (orsak.body as Record<string, unknown>) : {};
    const text =
      (typeof kropp.error === "string" && kropp.error) ||
      (typeof kropp.detail === "string" && kropp.detail) ||
      orsak.message;
    return { text, klass: typeof kropp.klass === "string" ? kropp.klass : null, status: orsak.status };
  }
  return { text: felmeddelande(orsak), klass: null, status: 0 };
}

/** Kvot (429), nätavbrott (0) och serverhicka (5xx) kan gå vägen vid nästa
 *  försök. En dubblett eller en oläsbar fil (422) gör det aldrig. */
function arOmforsokbart(status: number): boolean {
  return status === 0 || status === 429 || status >= 500;
}

export function AgentVy() {
  const { hamta } = useBokforing();
  const [utfall, setUtfall] = useState<Utfall[]>([]);
  const [attForsokaIgen, setAttForsokaIgen] = useState<File[]>([]);
  const [pagaende, setPagaende] = useState<string | null>(null);
  const [arOver, setArOver] = useState(false);
  const filvaljare = useRef<HTMLInputElement>(null);

  async function laddaUpp(filer: File[]) {
    if (!filer.length || pagaende !== null) return;
    setUtfall([]);
    setAttForsokaIgen([]);
    const resultat: Utfall[] = [];
    const igen: File[] = [];
    try {
      for (let i = 0; i < filer.length; i += 1) {
        const fil = filer[i];
        setPagaende(fil.name);
        try {
          const kropp = new FormData();
          kropp.append("fil", fil);
          const svar = await fetch(`${BAS}/underlag`, { method: "POST", body: kropp });
          const data = await readJson<Uppladdningssvar>(svar);
          if (!data) throw new Error("Tomt svar från servern.");
          resultat.push({
            slag: data.status === "klar" ? "klar" : "granska",
            namn: fil.name,
            underlag: data.underlag,
            brister: data.brister ?? []
          });
        } catch (orsak) {
          const { text, klass, status } = tolkaFel(orsak);
          resultat.push({ slag: "fel", namn: fil.name, orsak: text });
          if (klass === "kreditslut") {
            for (const rest of filer.slice(i + 1)) {
              resultat.push({
                slag: "ej_behandlad",
                namn: rest.name,
                orsak: "Skickades inte — uppladdningen stoppades när AI-kapaciteten tog slut."
              });
            }
            break;
          }
          if (arOmforsokbart(status)) igen.push(fil);
        }
        setUtfall([...resultat]);
      }
      setAttForsokaIgen(igen);
      await hamta();
    } finally {
      setPagaende(null);
    }
  }

  const lyckade = utfall.filter((rad) => rad.slag === "klar" || rad.slag === "granska");
  const misslyckade = utfall.filter((rad) => rad.slag === "fel" || rad.slag === "ej_behandlad");

  return (
    <div className="space-y-10">
      <PageHeader
        rubrik="Bokföringsagenten"
        beskrivning="Släpp ett kvitto eller en faktura. Agenten går igenom underlaget två gånger — en avläsning och en oberoende kontrolläsning — och bara fält som båda genomgångarna är överens om godkänns. Allt annat hamnar i granskningskön i stället för att gissas."
      />

      {/* Släppytan. */}
      <section aria-label="Ladda upp underlag">
        <div
          role="button"
          tabIndex={0}
          aria-label="Ladda upp underlag — klicka eller släpp filer här"
          onClick={() => filvaljare.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              filvaljare.current?.click();
            }
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setArOver(true);
          }}
          onDragLeave={() => setArOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setArOver(false);
            void laddaUpp(Array.from(e.dataTransfer.files ?? []));
          }}
          className={cn(
            "dropzone focus-ring flex cursor-pointer flex-col items-center justify-center gap-3 rounded-panel border-2 border-dashed border-ink/20 bg-paper2/40 px-6 py-14 text-center",
            arOver && "ar-over",
            pagaende !== null && "pointer-events-none opacity-60"
          )}
        >
          {pagaende !== null ? (
            <>
              <Loader2 className="h-7 w-7 animate-spin text-ochre" aria-hidden />
              <p className="font-display text-[1.25rem] text-ink">Läser {pagaende}</p>
              <p className="max-w-[46ch] text-[0.9375rem] leading-6 text-ink/60">
                Två genomgångar pågår: avläsning och kontrolläsning. Det tar oftast under en
                halv minut per dokument.
              </p>
            </>
          ) : (
            <>
              <ScanLine className="h-7 w-7 text-ochre" aria-hidden />
              <p className="font-display text-[1.25rem] text-ink">
                Släpp PDF eller foto här — eller klicka för att välja
              </p>
              <p className="max-w-[46ch] text-[0.9375rem] leading-6 text-ink/60">
                Kvitton och fakturor som PDF, JPEG, PNG, WEBP eller HEIC, upp till 12 MB.
                Filen läses i minnet och sparas aldrig — bara de avlästa fälten.
              </p>
            </>
          )}
        </div>
        <input
          ref={filvaljare}
          type="file"
          multiple
          accept={LASBARA}
          onChange={(e) => {
            void laddaUpp(Array.from(e.target.files ?? []));
            e.target.value = "";
          }}
          className="sr-only"
        />
      </section>

      {/* Det som inte kom in — före det som gick bra: det kunden måste agera
          på går först. */}
      {misslyckade.length ? (
        <section role="status" className="max-w-[78ch] border-y border-ink/15 py-4">
          <p className="flex items-center gap-2 text-[0.9375rem] font-semibold text-ink">
            <AlertTriangle className="h-4 w-4 text-ochre" aria-hidden />
            {misslyckade.length} {misslyckade.length === 1 ? "fil kom" : "filer kom"} inte in
          </p>
          <ul className="mt-2 space-y-2">
            {misslyckade.map((rad, i) => (
              <li key={`${rad.namn}-${i}`} className="text-[0.9375rem]">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="min-w-0 truncate font-medium text-ink">{rad.namn}</span>
                  {rad.slag === "ej_behandlad" ? <Badge tone="warn">Inte skickad</Badge> : null}
                </span>
                {rad.slag === "fel" || rad.slag === "ej_behandlad" ? (
                  <span className="block text-[0.875rem] text-ink/62">{rad.orsak}</span>
                ) : null}
              </li>
            ))}
          </ul>
          {attForsokaIgen.length ? (
            <button
              type="button"
              disabled={pagaende !== null}
              onClick={() => void laddaUpp(attForsokaIgen)}
              className={cn(btnSecondary, btnLiten, "mt-3")}
            >
              {pagaende !== null ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Upload className="h-4 w-4" aria-hidden />
              )}
              Försök igen med {attForsokaIgen.length}{" "}
              {attForsokaIgen.length === 1 ? "fil" : "filer"}
            </button>
          ) : null}
        </section>
      ) : null}

      {/* De avlästa dokumenten. */}
      {lyckade.length ? (
        <section>
          <h2 className="font-display text-[1.25rem]">Avläst i den här omgången</h2>
          <div className="mt-3 divide-y divide-ink/12 border-y border-ink/15">
            {lyckade.map((rad, i) => {
              if (rad.slag !== "klar" && rad.slag !== "granska") return null;
              const u = rad.underlag;
              return (
                <div key={`${rad.namn}-${i}`} className="py-4">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <FileUp className="h-4 w-4 shrink-0 text-ink/45" aria-hidden />
                    <span className="min-w-0 truncate font-medium">{rad.namn}</span>
                    <Badge tone="neutral">Läst 2 gånger</Badge>
                    <Badge tone={rad.slag === "granska" ? "warn" : "good"}>
                      {rad.slag === "granska" ? "Till granskning" : "Klar — verifikat skapat"}
                    </Badge>
                  </div>
                  <dl className="mt-3 grid gap-x-8 gap-y-2 text-[0.9375rem] sm:grid-cols-2 lg:grid-cols-4">
                    {[
                      ["Datum", u.datum ?? "—"],
                      ["Motpart", u.motpart ?? "—"],
                      ["Belopp", kronor(u.brutto)],
                      ["Moms", procent(u.momssats)]
                    ].map(([etikett, varde]) => (
                      <div key={etikett}>
                        <dt className="text-[0.8125rem] text-ink/50">{etikett}</dt>
                        <dd className="num mt-0.5 font-medium">{varde}</dd>
                      </div>
                    ))}
                  </dl>
                  {rad.brister.length ? (
                    <ul className="mt-2 max-w-[78ch] space-y-1 text-[0.875rem] text-ink/62">
                      {rad.brister.map((brist) => (
                        <li key={brist}>{brist}</li>
                      ))}
                    </ul>
                  ) : null}
                  {u.anmarkning ? (
                    <p className="mt-2 max-w-[78ch] text-[0.875rem] text-ink/55">{u.anmarkning}</p>
                  ) : null}
                </div>
              );
            })}
          </div>
          <p className="mt-3 text-[0.875rem] text-ink/60">
            Siffrorna är nu med i{" "}
            <Link href="/resultat" className="focus-ring rounded-[4px] underline decoration-ochre/50 underline-offset-4 hover:text-ink">
              Resultat
            </Link>{" "}
            och listas under{" "}
            <Link href="/pdf-filer" className="focus-ring rounded-[4px] underline decoration-ochre/50 underline-offset-4 hover:text-ink">
              PDF-filer
            </Link>
            .
          </p>
        </section>
      ) : null}

      {/* Hur agenten arbetar — kort, konkret, inga påhittade siffror. */}
      <section aria-label="Så arbetar agenten">
        <h2 className="font-display text-[1.25rem]">Så arbetar agenten</h2>
        <ol className="mt-3 grid gap-y-5 border-y border-ink/15 py-5 sm:grid-cols-3 sm:gap-x-8">
          {[
            {
              rubrik: "Läser två gånger",
              text: "Varje dokument får en avläsning och en oberoende kontrolläsning. Fält som genomgångarna läser olika lämnas till granskning — ingen av läsningarna vinner på ordningsföljd."
            },
            {
              rubrik: "Koden räknar",
              text: "Moms, kontering och periodens summor räknas av kod ur de avlästa beloppen. Modellen skriver av vad som står — den räknar aldrig själv."
            },
            {
              rubrik: "Hellre fråga än gissa",
              text: "Ett fält som inte står på underlaget lämnas tomt och dokumentet hamnar i granskningskön. Ett gissat fält hade hamnat i en momsdeklaration."
            }
          ].map((steg, i) => (
            <li key={steg.rubrik} className="min-w-0">
              <span className="numeral text-[1.75rem] text-ochre">{i + 1}</span>
              <h3 className="mt-2 font-semibold">{steg.rubrik}</h3>
              <p className="mt-1 text-[0.9375rem] leading-6 text-ink/62">{steg.text}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
