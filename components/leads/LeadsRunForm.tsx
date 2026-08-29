"use client";

import { RefreshCw, Send } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { EmailStudioEditor } from "@/components/email/EmailStudioEditor";
import type { EmailStudioData } from "@/lib/data/emails";
import { btnPrimary, btnSecondary } from "@/components/ui";
import { felmeddelande, readJsonBody } from "@/lib/http/json";
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
 * ## Två vägar till prospekt
 *
 * `POST /leads/runs/batch` svarar 422 om tenanten saknar prospekt, och "Inga
 * prospekt att köra på" är ett dåligt svar på en knapp som heter "Starta
 * körning". Formuläret erbjuder därför båda vägarna in, i samma knapptryck:
 *
 *  1. **Egna bolag** — bolag kunden själv äger eller vill träffa, ett per rad.
 *  2. **Exempelbolag** — påhittade bolag som passar ICP:t, för att se hur
 *     agenten arbetar innan man har en lista. De märks `origin='example'` i
 *     databasen och kan aldrig mejlas (INV-SEND: send_guard fäller dem).
 */

type Jobb = { job_id: string; prospect_id?: string };

type LeadsSvar = {
  jobs?: Jobb[];
  count?: number;
  scope?: string;
  is_test?: boolean;
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
};

/**
 * Interna fältnamn -> etiketten kunden såg i formuläret.
 *
 * Ordningen är formulärets, inte objektets: en sammanfattning som räknar upp
 * fälten i en annan ordning än de fylldes i tvingar läsaren att leta.
 */
const ÖVERSKRIVNINGSETIKETTER: [string, string][] = [
  ["industries", "Branscher"],
  ["exclude_industries", "Undviker"],
  ["geography", "Stad, län, region"],
  ["roles", "Beslutsfattarroller"],
  ["must_have", "Signaler som krävs"],
  ["deal_breakers", "Diskvalificerar"],
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
      <span className="text-[13px] font-medium text-ink/70">{etikett}</span>
      {hint ? <span className="ml-2 text-[12px] text-ink/45">{hint}</span> : null}
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
  rubrik = null
}: Readonly<{ isTest?: boolean; demo?: boolean; rubrik?: React.ReactNode }>) {
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
  const [exempelbolag, setExempelbolag] = useState(true);
  const [svar, setSvar] = useState<LeadsSvar | null>(null);
  const [bolag, setBolag] = useState<Exempelbolag[]>([]);
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

  /**
   * Hämtar ett urval exempelbolag med färdiga utkast.
   *
   * Bruten ur körningen för att "Uppdatera" ska gå samma väg. Två anropsplatser
   * med var sin kopia av taket och överskrivningarna hade glidit isär, och
   * symptomet blir att knappen ger en annan målgrupp än formuläret ovanför den.
   */
  async function hamtaExempelbolag(
    antal: number,
    overrides: ReturnType<typeof byggÖverskrivningar>
  ): Promise<Exempelbolag[]> {
    const svar = await anropa<{ created?: Exempelbolag[] }>("/leads/prospects/exempel", {
      method: "POST",
      body: JSON.stringify({
        // Taket i ExempelbolagRequest är 10: exempelbolag är en väg IN i
        // produkten, inte en lista att arbeta ur. Klamras här så att ett stort
        // `antal` ger tio exempel i stället för 422.
        limit: Math.min(Math.max(antal, 1), 10),
        ...(overrides ? { overrides } : {})
      })
    });
    return svar.created ?? [];
  }

  /**
   * "Uppdatera" — nytt urval, nya utkast, samma målgrupp.
   *
   * Startar INGEN körning. Den som vill se agenten formulera sig om ett annat
   * läge ska inte behöva betala för åtta LLM-anrop per bolag för att göra det,
   * och ska inte heller behöva fylla i formuläret igen.
   */
  async function uppdateraBolag() {
    setBusy(true);
    setFel(null);
    setStatus("Hämtar nya exempelbolag…");
    try {
      setBolag(await hamtaExempelbolag(Number(limit) || 3, byggÖverskrivningar()));
    } catch (cause) {
      setFel(felmeddelande(cause));
    } finally {
      setStatus(null);
      setBusy(false);
    }
  }

  async function kör() {
    setBusy(true);
    setFel(null);
    setSvar(null);
    setBolag([]);
    setStatus(null);
    try {
      const overrides = byggÖverskrivningar();
      const antal = Number(limit) || 1;

      // 1. Egna bolag blir prospekt först — de är det kunden helst vill se.
      //    is_test följer med som query-parameter (Fas 2.2, migration 054):
      //    utan den landade en testkörnings egna bolag som origin='manual',
      //    omöjliga att skilja från kundens riktiga lista och oskyddade av
      //    send-guardens spärr noll.
      const egna = rader(egnaBolag);
      for (const namn of egna) {
        setStatus(`Lägger till ${namn}…`);
        // Ruttdelen hålls som en REN literal (inte template) — rotvakten
        // tests/test_leads_ui_endpoints.py läser vägarna med regex och ska
        // kunna matcha den mot backendens routelista.
        await anropa("/leads/prospects" + (isTest ? "?is_test=true" : ""), {
          method: "POST",
          body: JSON.stringify({ company_name: namn })
        });
      }

      // 2. Exempelbolag, om kunden bad om det ELLER om det inte finns något
      //    att köra på. Att svara "Inga prospekt att köra på" på en knapp som
      //    heter Starta körning är att lämna tillbaka arbetet.
      if (exempelbolag || egna.length === 0) {
        const befintliga = await anropa<{ prospects?: unknown[] }>("/leads/prospects", {
          method: "GET"
        });
        const saknas = (befintliga.prospects?.length ?? 0) === 0;
        if (exempelbolag || saknas) {
          setStatus("Tar fram exempelbolag som passar er produkt…");
          setBolag(await hamtaExempelbolag(Math.max(antal - egna.length, 1), overrides));
        }
      }

      // 3. Själva körningen.
      setStatus("Startar körningen…");
      const resultat = await anropa<LeadsSvar>("/leads/runs/batch", {
        method: "POST",
        body: JSON.stringify({
          limit: antal,
          scope,
          is_test: isTest,
          ...(overrides ? { overrides } : {})
        })
      });
      setSvar(resultat);
      setStatus(null);
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
        <Rad etikett="Branscher" hint="komma emellan">
          <input value={branscher} onChange={(e) => setBranscher(e.target.value)} placeholder="Bygg, Tillverkning" className={fältklass} />
        </Rad>
        <Rad etikett="Undvik branscher">
          <input value={undvik} onChange={(e) => setUndvik(e.target.value)} placeholder="Bemanning" className={fältklass} />
        </Rad>
        <Rad etikett="Stad, län, region">
          <input value={geografi} onChange={(e) => setGeografi(e.target.value)} placeholder="Västra Götaland" className={fältklass} />
        </Rad>
        <Rad etikett="Beslutsfattarroller" hint="vem agenterna ska leta efter">
          <input value={roller} onChange={(e) => setRoller(e.target.value)} placeholder="VD, inköpschef" className={fältklass} />
        </Rad>
        <Rad etikett="Signaler som krävs" hint="nischen">
          <input value={kravs} onChange={(e) => setKravs(e.target.value)} placeholder="Egen produktion, växer" className={fältklass} />
        </Rad>
        <Rad etikett="Diskvalificerar">
          <input value={diskvalificerar} onChange={(e) => setDiskvalificerar(e.target.value)} placeholder="Under 10 anställda" className={fältklass} />
        </Rad>
        <div className="grid grid-cols-2 gap-3">
          <Rad etikett="Anställda, min">
            <input type="number" min={0} value={minAnst} onChange={(e) => setMinAnst(e.target.value)} className={fältklass} />
          </Rad>
          <Rad etikett="max">
            <input type="number" min={0} value={maxAnst} onChange={(e) => setMaxAnst(e.target.value)} className={fältklass} />
          </Rad>
        </div>
        <Rad etikett="Egna bolag" hint="ett per rad — bolag ni själva vill träffa">
          <textarea
            value={egnaBolag}
            onChange={(e) => setEgnaBolag(e.target.value)}
            rows={3}
            placeholder={"Byggkompaniet Syd AB\nNordvik Fastigheter"}
            className={cn(fältklass, "resize-y")}
          />
        </Rad>
      </div>

      <label className="mt-5 flex max-w-[70ch] items-start gap-3">
        <input
          type="checkbox"
          checked={exempelbolag}
          onChange={(e) => setExempelbolag(e.target.checked)}
          className="mt-1 h-4 w-4 accent-ochre"
        />
        <span className="text-[14px] leading-6 text-ink/70">
          Fyll på med <strong>exempelbolag</strong> som passar er produkt. Påhittade bolag som
          visar hur agenterna arbetar innan ni har en egen lista — de kan aldrig mejlas.
        </span>
      </label>

      {/* På demoytan finns ingen session, och /api/snajp-support/* svarar 401
          med flit (requireSnajpTenant härleder kunden ur sessionen). Att visa
          en knapp som alltid svarar "Du måste vara inloggad" är sämre än att
          säga det innan den trycks — och att fejka ett körresultat vore värst
          av allt: hela poängen med vyn är att den visar vad agenten FAKTISKT
          gjorde. */}
      {demo ? (
        <div className="mt-6 rounded-card bg-paper2/60 p-5">
          <p className="max-w-[65ch] text-[15px] leading-7 text-ink/70">
            Formuläret är det riktiga. En körning kostar LLM-anrop mot er egen
            målgrupp och kräver därför ett konto — här visar vi vilka reglagen är,
            inte ett påhittat resultat.
          </p>
          <Link href="/login" className={cn(btnPrimary, "mt-4")}>
            Logga in för att köra
          </Link>
        </div>
      ) : (
        <button type="button" onClick={() => void kör()} disabled={busy} className={cn(btnPrimary, "mt-6")}>
          {busy ? "Startar…" : isTest ? "Starta testkörning" : "Starta körning"}
        </button>
      )}

      {status ? <p className="mt-3 text-[13px] text-ink/55">{status}</p> : null}

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
                      <dt className="text-[12px] font-medium uppercase tracking-[0.04em] text-ink/45">
                        {etikett}
                      </dt>
                      <dd className="mt-1 text-[14px] leading-6 text-ink/80">
                        {Array.isArray(värde) ? värde.join(", ") : String(värde)}
                      </dd>
                    </div>
                  );
                })}
              </dl>
            ) : (
              <p className="mt-2 text-[13px] text-ink/55">
                Er sparade målgrupp användes — inga fält ändrades för den här körningen.
              </p>
            )}
          </div>

          {bolag.length > 0 ? (
            <Exempelbolagslista bolag={bolag} onUppdatera={uppdateraBolag} uppdaterar={busy} />
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
          <p className="mt-0.5 text-[13px] text-ink/45">Påhittade — kan aldrig mejlas</p>
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
                <p className="mt-1 font-mono text-[12px] text-ink/45">
                  {[b.orgnr, b.ort, b.website].filter(Boolean).join(" · ")}
                </p>
              </div>
              <span className="shrink-0 rounded-input bg-ochre/15 px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.06em] text-ochre">
                Exempel
              </span>
            </div>

            {b.beskrivning ? (
              <p className="mt-2 max-w-[70ch] text-[14px] leading-6 text-ink/70">{b.beskrivning}</p>
            ) : null}

            <p className="mt-2 text-[13px] text-ink/50">
              {[
                b.contact_name ? `Beslutsfattare: ${b.contact_name}` : null,
                typeof b.anstallda === "number" ? `${b.anstallda} anställda` : null,
                b.bransch
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>

            <p className="mt-2 inline-flex items-center gap-1.5 text-[13px] font-medium text-ochre">
              {öppen ? "Dölj utkastet" : "Öppna utkastet"}
              <span aria-hidden>{öppen ? "↑" : "→"}</span>
            </p>
            </button>

            {öppen ? <Pitchutkast bolag={b} /> : null}
          </li>
          );
        })}
      </ul>

      <p className="mt-4 border-t border-ink/10 pt-4 text-[13px] leading-6 text-ink/50">
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
      signal: bolag.signal ?? null,
      // "Varför nu" är det som gör signalen till ett skäl att höra av sig, och
      // det är precis vad Personalisera behöver för att inte bli en omskrivning.
      offer: bolag.pitch_varfor_nu ?? null,
      cta: null,
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
        <p className="text-[13px] leading-6 text-ink/55">
          {skickat
            ? "Ingenting skickades. Utkastet finns kvar här och bolaget är påhittat — så här skulle utskicket ha sett ut."
            : "Provar hela vägen fram utan att något lämnar huset."}
        </p>
      </div>
    </div>
  );
}
