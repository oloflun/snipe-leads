"use client";

import { RefreshCw, Send } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import { DemoKorning } from "@/components/leads/DemoKorning";
import type { EmailStudioData } from "@/lib/data/emails";
import { btnPrimary, btnSecondary } from "@/components/ui";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
import { ICP_ETIKETTER } from "@/lib/leads/icpLabels";
import { cn } from "@/lib/utils";

/**
 * Formuläret som startar en leads-körning. EN komponent, två ytor.
 *
 * ## Varför den bröts ut
 *
 * Adminytans "Testkörningar" hade sedan tidigare ett fullständigt formulär —
 * bransch, geografi, roller, signaler, diskvalificerare, storleksspann,
 * omfattning och antal. Kundens leads-flik hade i stället fyra hårdkodade
 * knappar ("Bygg i Malmö", "Gym i Stockholm" …) ur `lib/mock-data.ts` och en
 * länk till assistentvyn, som också är mock. Kunden kunde alltså inte starta
 * en körning alls från sin egen yta.
 *
 * Att kopiera formuläret hade gett två formulär som glider isär: adminens fick
 * roller och signaler i augusti, kundens hade fortfarande inte fått dem. Därför
 * en komponent med två flaggor (`isTest`, `demo`), inte två filer.
 *
 * ## Överskrivningarna är inte inställningar
 *
 * Fälten gäller ENBART den startade körningen och rör aldrig arbetsytans
 * sparade ICP (`/settings/leads`). Alternativet — ändra målgruppen, köra, ändra
 * tillbaka — går fel den gång man glömmer sista steget, och då bearbetas nästa
 * riktiga körning med fel målgrupp utan att någon ser det.
 *
 * ## Vägen till prospekt
 *
 * Kedjan är ICP → hitta bolag → registrera sajt → research → ev. utkast.
 * **Egna bolag** är opt-in: namn kunden redan vet att de vill träffa. Tomt
 * fält betyder att agenten söker. Påhittade exempelbolag med färdigskrivna
 * pitchar finns bara på `/demo`.
 *
 * Efter `runs/batch` (`fase: soker`) pollas sökjobbet mot `/leads/jobb/{id}`.
 * När det är klart ligger research-jobben i `result.jobs` och pollas samma
 * väg. Sökningen (Gemini + Google) får inte ligga i POST-svaret — proxyn
 * avbryter efter 9 s och Safari visar "Kunde inte nå servern".
 */

type Jobb = { job_id: string; prospect_id?: string };

type LeadsSvar = {
  jobs?: Jobb[];
  count?: number;
  scope?: string;
  is_test?: boolean;
  fase?: string;
  overrides?: Record<string, unknown> | null;
  error?: string;
  detail?: string;
};

/**
 * Ett skapat exempelbolag, som backenden lämnar det.
 *
 * `orgnr` har MEDVETET fel kontrollsiffra och `website` ligger under `.example`
 * (RFC 2606, kan aldrig registreras). Se app/leads/exempelbolag.py: ett
 * påhittat bolag med ett giltigt org.nr är inte påhittat, det är ett riktigt
 * företag med påhittade uppgifter om sig.
 */
type Exempelbolag = {
  id?: string;
  company_name: string;
  contact_name?: string | null;
  orgnr?: string | null;
  ort?: string | null;
  website?: string | null;
  anstallda?: number | null;
  bransch?: string | null;
  signal?: string | null;
  beskrivning?: string | null;
  /** Utkastet backenden skrev till just det här bolaget. Se exempelbolag.py. */
  pitch_subject?: string | null;
  pitch_body?: string | null;
  pitch_varfor_nu?: string | null;
  /** Det konkreta erbjudandet och uppmaningen — se lib/demo/iris-exempel.ts. */
  offer?: string | null;
  cta?: string | null;
};

/**
 * Interna fältnamn -> etiketten kunden såg i formuläret.
 *
 * Ordningen är formulärets, inte objektets: en sammanfattning som räknar upp
 * fälten i en annan ordning än de fylldes i tvingar läsaren att leta.
 */
const ÖVERSKRIVNINGSETIKETTER: [string, string][] = [
  ["industries", ICP_ETIKETTER.industries.label],
  ["exclude_industries", ICP_ETIKETTER.exclude_industries.label],
  ["geography", ICP_ETIKETTER.geography.label],
  ["roles", ICP_ETIKETTER.roles.label],
  ["must_have", ICP_ETIKETTER.must_have.label],
  ["deal_breakers", ICP_ETIKETTER.deal_breakers.label],
  ["anstallda_min", "Anställda, minst"],
  ["anstallda_max", "Anställda, högst"]
];

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

/** "Bygg, Tillverkning" → ["Bygg","Tillverkning"]. Tom sträng → undefined. */
function lista(värde: string): string[] | undefined {
  const delar = värde
    .split(",")
    .map((d) => d.trim())
    .filter(Boolean);
  return delar.length ? delar : undefined;
}

function rader(värde: string): string[] {
  return värde
    .split(/[\n;]/)
    .map((d) => d.trim())
    .filter(Boolean);
}

function tal(värde: string): number | undefined {
  const n = Number(värde.trim());
  return värde.trim() && Number.isFinite(n) ? n : undefined;
}

export function LeadsRunForm({
  isTest = true,
  demo = false,
  rubrik = null,
  demoAction = null
}: Readonly<{
  isTest?: boolean;
  demo?: boolean;
  rubrik?: React.ReactNode;
  /**
   * Ersätter `DemoKorning` i demoläget. Iris › Bolag (IrisBolag.tsx) skickar
   * en egen "Kör exempelkörningen"-knapp här: den infogar de sex fixturbolagen
   * ur lib/demo/iris-exempel.ts överst i BOLAGSLISTAN i stället för att visa en
   * egen, fristående resultatlista med andra påhittade bolag
   * (lib/demo/leads-korning.ts) — kravet är EN lista, inte två.
   */
  demoAction?: React.ReactNode;
}>) {
  const [limit, setLimit] = useState("3");
  const [scope, setScope] = useState<"research" | "research_and_draft">("research");
  const [branscher, setBranscher] = useState("");
  const [undvik, setUndvik] = useState("");
  const [geografi, setGeografi] = useState("");
  // Roller, krävs och diskvalificerar ÄR nischen — bransch och geografi säger
  // bara var man letar. Utan dem gick en körning mot en särskild nisch inte att
  // styra: de tre kom alltid från arbetsytans sparade ICP.
  const [roller, setRoller] = useState("");
  const [kravs, setKravs] = useState("");
  const [diskvalificerar, setDiskvalificerar] = useState("");
  const [minAnst, setMinAnst] = useState("");
  const [maxAnst, setMaxAnst] = useState("");
  const [egnaBolag, setEgnaBolag] = useState("");
  const [svar, setSvar] = useState<LeadsSvar | null>(null);
  const [jobbLage, setJobbLage] = useState<{ klara: number; totalt: number; misslyckade: number } | null>(
    null
  );
  const [status, setStatus] = useState<string | null>(null);
  const [fel, setFel] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function byggÖverskrivningar() {
    // Tomma fält skickas INTE. null betyder "använd arbetsytans sparade ICP",
    // vilket inte är samma sak som "inga branscher alls".
    const overrides = {
      industries: lista(branscher),
      exclude_industries: lista(undvik),
      geography: lista(geografi),
      roles: lista(roller),
      must_have: lista(kravs),
      deal_breakers: lista(diskvalificerar),
      anstallda_min: tal(minAnst),
      anstallda_max: tal(maxAnst)
    };
    return Object.values(overrides).some((v) => v !== undefined) ? overrides : null;
  }

  async function anropa<T>(path: string, init: RequestInit): Promise<T> {
    const response = await fetch(`/api/snajp-support${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init
    });
    const kropp = (await readJsonBody<T & { error?: string; detail?: unknown }>(response)) ?? ({} as T);
    if (!response.ok) {
      const k = kropp as { error?: string; detail?: unknown };
      // Pydantics 422 lägger en LISTA av valideringsfel i `detail`. Ett rakt
      // `new Error(detail)` renderade "[object Object]" — plocka ut `msg`-
      // fälten i stället, så att "Antal bolag: högst 50" faktiskt står där.
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

  async function pollaJobb(
    jobId: string,
    maxForsok = 90
  ): Promise<{ status: string; error?: string; jobs?: Jobb[] }> {
    // Prefixet är en literal i anropet så rotvakten ser sökvägen.
    // `/leads/jobb/` är den inloggade proxyn — inte `/jobs/`, som är den
    // anonyma chattpollningen och slår upp under demonyckeln.
    for (let forsok = 0; forsok < maxForsok; forsok += 1) {
      await new Promise((r) => setTimeout(r, forsok < 5 ? 800 : 2000));
      const jobb = await anropa<{
        status?: string;
        error?: string;
        result?: { jobs?: Jobb[] };
      }>("/leads/jobb/" + jobId, { method: "GET" });
      if (jobb.status === "completed" || jobb.status === "failed") {
        return { status: jobb.status, error: jobb.error, jobs: jobb.result?.jobs };
      }
    }
    return { status: "timeout", error: "Körningen tog för lång tid." };
  }

  async function kör() {
    setBusy(true);
    setFel(null);
    setSvar(null);
    setJobbLage(null);
    setStatus(null);
    try {
      const overrides = byggÖverskrivningar();
      const antal = Number(limit) || 1;
      const egna = rader(egnaBolag);

      setStatus(egna.length ? "Startar körningen…" : "Letar bolag som matchar målgruppen…");
      const resultat = await anropa<LeadsSvar>("/leads/runs/batch", {
        method: "POST",
        body: JSON.stringify({
          limit: antal,
          scope,
          is_test: isTest,
          company_names: egna,
          ...(overrides ? { overrides } : {})
        })
      });

      let jobb = resultat.jobs ?? [];
      if (resultat.fase === "soker") {
        const sokId = jobb[0]?.job_id;
        if (!sokId) {
          throw new Error("Körningen startade inte. Försök igen.");
        }
        // Sökfasen får vänta ~5 min, research-jobben ~3. Den grundade
        // sökningen tog 55–156 s i mätningen 2026-09-15 och backendens tak
        // är ~3,3 min (discovery._SOKNING_TIMEOUT) — formuläret ska aldrig ge
        // upp före backenden, annars ser kunden "tog för lång tid" i stället
        // för det riktiga beskedet.
        const sok = await pollaJobb(sokId, 150);
        if (sok.status !== "completed") {
          throw new Error(sok.error ?? "Sökningen hittade inga bolag.");
        }
        jobb = sok.jobs ?? [];
      }

      if (!jobb.length) {
        throw new Error(
          "Inga bolag matchade målgruppen. Prova en bredare sökning."
        );
      }

      setSvar({ ...resultat, jobs: jobb, count: jobb.length, fase: "research" });

      let klara = 0;
      let misslyckade = 0;
      setJobbLage({ klara: 0, totalt: jobb.length, misslyckade: 0 });
      setStatus(jobb.length ? `Körningen pågår… (0/${jobb.length} klara)` : null);

      for (const rad of jobb) {
        const utfall = await pollaJobb(rad.job_id);
        if (utfall.status === "completed") klara += 1;
        else misslyckade += 1;
        setJobbLage({ klara, totalt: jobb.length, misslyckade });
        setStatus(`Körningen pågår… (${klara + misslyckade}/${jobb.length} klara)`);
      }

      setStatus(
        misslyckade
          ? `Klart: ${klara} bolag researchade, ${misslyckade} misslyckades.`
          : `Klart: ${klara} bolag researchade.`
      );
      window.dispatchEvent(new Event("snipra:leads-korning-klar"));
    } catch (cause) {
      setFel(felmeddelande(cause));
      setStatus(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      {rubrik}

      <div className="mt-6 grid max-w-[760px] gap-5 sm:grid-cols-2">
        <Rad etikett="Antal bolag" hint="1–50">
          <input
            type="number"
            min={1}
            max={50}
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
            className={fältklass}
          />
        </Rad>
        <Rad etikett="Omfattning">
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value as typeof scope)}
            className={fältklass}
          >
            <option value="research">Bara research</option>
            <option value="research_and_draft">Research och utkast</option>
          </select>
        </Rad>
        <Rad etikett={ICP_ETIKETTER.industries.label} hint="komma emellan">
          <input value={branscher} onChange={(e) => setBranscher(e.target.value)} placeholder={ICP_ETIKETTER.industries.hint} className={fältklass} />
        </Rad>
        <Rad etikett={ICP_ETIKETTER.exclude_industries.label}>
          <input value={undvik} onChange={(e) => setUndvik(e.target.value)} placeholder={ICP_ETIKETTER.exclude_industries.hint} className={fältklass} />
        </Rad>
        <Rad etikett={ICP_ETIKETTER.geography.label}>
          <input value={geografi} onChange={(e) => setGeografi(e.target.value)} placeholder={ICP_ETIKETTER.geography.hint} className={fältklass} />
        </Rad>
        <Rad etikett={ICP_ETIKETTER.roles.label}>
          <input value={roller} onChange={(e) => setRoller(e.target.value)} placeholder={ICP_ETIKETTER.roles.hint} className={fältklass} />
        </Rad>
        <Rad etikett={ICP_ETIKETTER.must_have.label} hint="nischen">
          <input value={kravs} onChange={(e) => setKravs(e.target.value)} placeholder={ICP_ETIKETTER.must_have.hint} className={fältklass} />
        </Rad>
        <Rad etikett={ICP_ETIKETTER.deal_breakers.label}>
          <input value={diskvalificerar} onChange={(e) => setDiskvalificerar(e.target.value)} placeholder={ICP_ETIKETTER.deal_breakers.hint} className={fältklass} />
        </Rad>
        <div className="grid grid-cols-2 gap-3">
          <Rad etikett="Anställda, min">
            <input type="number" min={0} value={minAnst} onChange={(e) => setMinAnst(e.target.value)} className={fältklass} />
          </Rad>
          <Rad etikett="max">
            <input type="number" min={0} value={maxAnst} onChange={(e) => setMaxAnst(e.target.value)} className={fältklass} />
          </Rad>
        </div>
        <Rad etikett="Egna bolag" hint="valfritt, ett per rad">
          <textarea
            value={egnaBolag}
            onChange={(e) => setEgnaBolag(e.target.value)}
            rows={3}
            placeholder="Tomt: agenten letar själv"
            className={cn(fältklass, "resize-y")}
          />
        </Rad>
      </div>

      {/* På demoytan finns ingen session, och /api/snajp-support/* svarar 401
          med flit (requireSnajpTenant härleder kunden ur sessionen). Tidigare
          stod här bara en logga-in-uppmaning: att fejka ett körresultat som
          ser körningsäkta ut vore värst av allt. Sedan 2026-09-15 kan demon
          ändå köras — som en MÄRKT exempelkörning (DemoKorning), samma
          mönster som bokföringens förskrivna svar. Märkningen är det som gör
          det ärligt; se lib/demo/leads-korning.ts. */}
      {demo ? (
        demoAction ?? <DemoKorning />
      ) : (
        <button type="button" onClick={() => void kör()} disabled={busy} className={cn(btnPrimary, "mt-6")}>
          {busy ? "Startar…" : isTest ? "Starta testkörning" : "Starta körning"}
        </button>
      )}

      {status ? <p className="mt-3 text-[13px] text-ink-subtle">{status}</p> : null}

      {fel ? (
        <p role="alert" className="mt-5 max-w-[70ch] break-words text-[15px] text-danger">
          {fel}
        </p>
      ) : null}

      {svar ? (
        <div className="mt-6 space-y-5">
          <div className="rounded-card bg-paper2/60 p-5">
            <p className="text-[15px]">
              <strong className="font-semibold">{svar.count}</strong>{" "}
              {svar.count === 1 ? "bolag" : "bolag"} i körningen ·{" "}
              {svar.scope === "research_and_draft" ? "research och utkast" : "bara research"}
              {svar.is_test ? " · testkörning" : null}
            </p>

            {/* Vad körningen FAKTISKT kördes med, inte vad formuläret råkade
                innehålla när knappen trycktes.

                Det här var en <pre> med JSON.stringify. Rådata i en kundvänd vy
                är inte transparens utan en läcka från utvecklarläget: kunden ska
                kunna läsa vilken målgrupp som gällde utan att kunna JSON, och
                fältnamnen (`deal_breakers`, `anstallda_min`) är dessutom våra
                interna namn, inte etiketterna som står i formuläret ovan. */}
            {svar.overrides ? (
              <dl className="mt-4 grid gap-x-8 gap-y-3 sm:grid-cols-2">
                {ÖVERSKRIVNINGSETIKETTER.map(([nyckel, etikett]) => {
                  const värde = svar.overrides?.[nyckel];
                  if (värde === undefined || värde === null) return null;
                  return (
                    <div key={nyckel} className="border-t border-ink/10 pt-2">
                      <dt className="text-[12px] font-medium uppercase tracking-[0.04em] text-ink-subtle">
                        {etikett}
                      </dt>
                      <dd className="mt-1 text-[14px] leading-6 text-ink-muted">
                        {Array.isArray(värde) ? värde.join(", ") : String(värde)}
                      </dd>
                    </div>
                  );
                })}
              </dl>
            ) : (
              <p className="mt-2 text-[13px] text-ink-subtle">
                Sparad målgrupp användes.
              </p>
            )}
          </div>

          {jobbLage && jobbLage.totalt > 0 ? (
            <p className="text-[14px] text-ink-muted">
              {jobbLage.klara + jobbLage.misslyckade}/{jobbLage.totalt} jobb avslutade
              {jobbLage.misslyckade ? ` · ${jobbLage.misslyckade} misslyckades` : null}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

/**
 * De skapade exempelbolagen, listade som prospekt — inte som ett svar från ett API.
 *
 * ## Varför den ser ut som den gör
 *
 * Vyn speglar ärendelistan i kundtjänstvyn med flit: samma radhöjd, samma
 * märkning uppe till höger, samma sekundärtext under rubriken. Det är samma
 * sorts objekt för användaren — något agenten hittat och som väntar på en
 * bedömning — och två olika listformer för samma sak tvingar läsaren att lära
 * sig produkten två gånger.
 *
 * ## Varför märkningen står på varje rad
 *
 * "Exempel" sitter per bolag och inte bara som en rubrik över listan. Raderna
 * hamnar i samma register som riktiga prospekt så fort körningen skrivit dem,
 * och en märkning som bara finns i rubriken följer inte med dit. Ett påhittat
 * bolag som läses som ett riktigt är den dyraste förväxlingen produkten kan
 * göra — då mejlas fel mottagare.
 */
export function Exempelbolagslista({
  bolag,
  onUppdatera,
  uppdaterar = false
}: Readonly<{ bolag: Exempelbolag[]; onUppdatera?: () => void; uppdaterar?: boolean }>) {
  const [valt, setValt] = useState<string | null>(null);

  return (
    <section aria-labelledby="exempelbolag" className="rounded-card bg-paper2/40 p-5 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <div>
          <h3 id="exempelbolag" className="text-[1.0625rem] font-semibold tracking-[-0.01em]">
            {bolag.length} exempelbolag inlagda
          </h3>
          <p className="mt-0.5 text-[13px] text-ink-subtle">Påhittade — kan aldrig mejlas</p>
        </div>

        {/* Uppdatera startar INGEN körning. Den som vill se agenten formulera
            sig om ett annat läge ska inte behöva betala för åtta LLM-anrop per
            bolag — och inte fylla i formuläret igen heller. */}
        {onUppdatera ? (
          <button
            type="button"
            onClick={onUppdatera}
            disabled={uppdaterar}
            className={cn(btnSecondary)}
          >
            <RefreshCw className={cn("h-4 w-4", uppdaterar && "animate-spin")} aria-hidden />
            {uppdaterar ? "Hämtar…" : "Uppdatera"}
          </button>
        ) : null}
      </div>

      <ul className="mt-4 divide-y divide-ink/10">
        {bolag.map((b, index) => {
          const nyckel = b.id ?? `${b.company_name}-${index}`;
          const öppen = valt === nyckel;
          return (
          <li key={nyckel} className="py-4 first:pt-0">
            <button
              type="button"
              onClick={() => setValt(öppen ? null : nyckel)}
              aria-expanded={öppen}
              className="focus-ring block w-full rounded-input text-left"
            >
            <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
              <div className="min-w-0">
                <p className="text-[15px] font-semibold tracking-[-0.01em]">{b.company_name}</p>
                <p className="mt-1 font-mono text-[12px] text-ink-subtle">
                  {[b.orgnr, b.ort, b.website].filter(Boolean).join(" · ")}
                </p>
              </div>
              <span className="shrink-0 rounded-input bg-ochre/15 px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.06em] text-warning">
                Exempel
              </span>
            </div>

            {b.beskrivning ? (
              <p className="mt-2 max-w-[70ch] text-[14px] leading-6 text-ink-muted">{b.beskrivning}</p>
            ) : null}

            <p className="mt-2 text-[13px] text-ink-subtle">
              {[
                b.contact_name ? `Beslutsfattare: ${b.contact_name}` : null,
                typeof b.anstallda === "number" ? `${b.anstallda} anställda` : null,
                b.bransch
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>

            <p className="mt-2 text-[13px] font-medium text-warning">
              {öppen ? "Dölj utkastet" : "Öppna utkastet"}
            </p>
            </button>

            {öppen ? <Pitchutkast bolag={b} /> : null}
          </li>
          );
        })}
      </ul>

      <p className="mt-4 border-t border-ink/10 pt-4 text-[13px] leading-6 text-ink-subtle">
        Organisationsnumren har medvetet fel kontrollsiffra och webbadresserna
        ligger under <span className="font-mono text-[12px]">.example</span>, som aldrig kan
        registreras. Ett påhittat bolag med giltiga uppgifter hade kunnat vara någon annans.
      </p>
    </section>
  );
}

/**
 * Utkastet till ETT bolag, öppnat i Email Studio.
 *
 * ## Varför samma editor som Email Studio och inte en egen
 *
 * `EmailStudioEditor` bär redan alla åtta åtgärder — Kortare, Skriv om,
 * Förbättra, Personalisera, Översätt, A/B-varianter, Uppföljning, Analysera —
 * och anropar `/api/email-studio`. En egen liten editor här hade betytt två
 * ställen där knapparna kan glida isär, och den som testar pitchen hade testat
 * något annat än det kunden sedan använder.
 *
 * Kontexten (bolag, signal, erbjudande) skickas med i varje åtgärd. Det är den
 * som gör "Personalisera" till något annat än "skriv om texten": modellen ser
 * vilket bolag och vilken signal utkastet gäller.
 *
 * ## Varför "Skicka test" inte skickar
 *
 * Bolaget är påhittat och saknar adress. Men det är inte skälet — skälet är att
 * INGET utkast här har passerat send_guard, och att en knapp som ibland skickar
 * och ibland inte är den farligaste sorten. Den bekräftar i stället vad som
 * skulle ha hänt, och säger rakt ut att ingenting lämnade huset.
 */
function Pitchutkast({ bolag }: Readonly<{ bolag: Exempelbolag }>) {
  const [skickat, setSkickat] = useState(false);

  const data: EmailStudioData = {
    source: "mock",
    businessContext: null,
    email: {
      id: bolag.id ?? bolag.company_name,
      subject: bolag.pitch_subject ?? `Till ${bolag.company_name}`,
      body: bolag.pitch_body ?? "",
      variantLength: "medium",
      variantType: "cold_outreach",
      status: "draft",
      companyId: bolag.id ?? null,
      contactId: null,
      companyName: bolag.company_name,
      signal: bolag.signal ?? bolag.pitch_varfor_nu ?? null,
      offer: bolag.offer ?? null,
      cta: bolag.cta ?? null,
      contactName: bolag.contact_name ?? null
    }
  };

  return (
    <div className="mt-4 rounded-card border border-ink/10 bg-paper p-4 md:p-5">
      <EmailStudioEditor data={data} compact />

      <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-ink/10 pt-4">
        <button
          type="button"
          onClick={() => setSkickat(true)}
          className={cn(btnSecondary)}
        >
          <Send className="h-4 w-4" aria-hidden />
          Skicka test
        </button>
        <p className="text-[13px] leading-6 text-ink-subtle">
          {skickat
            ? "Ingenting skickades. Utkastet finns kvar här och bolaget är påhittat — så här skulle utskicket ha sett ut."
            : "Provar hela vägen fram utan att något lämnar huset."}
        </p>
      </div>
    </div>
  );
}
