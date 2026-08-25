"use client";

import { AlertTriangle, Download, Forward, Loader2, Scale, Trash2, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Badge,
  EmptyState,
  SkeletonRows,
  btnLiten,
  btnPrimary,
  btnSecondary
} from "@/components/ui";
import { felmeddelande, readJson } from "@/lib/http/json";
import { cn } from "@/lib/utils";

/**
 * FÖRBEHÅLLET ÄR BORTTAGET UR VYN, på begäran 2026-08-24.
 *
 * Det stod som ett stycke överst: "Förslag, inte bokföring. …". Texten finns
 * kvar i backenden (`FORBEHALL` i app/agent/bookkeeping_agent.py) och följer
 * med i varje API-svar och i SIE-exporten — den är alltså inte raderad, den
 * syns bara inte i gränssnittet längre.
 *
 * Sidbeskrivningen i `BookkeepingView` bär numera samma innebörd i mjukare
 * form: underlagen blir "klart för granskning och bokföring", alltså något en
 * människa tar vidare. Att det är ett svagare påstående än det gamla
 * förbehållet är ett medvetet val och inte en förbiseelse.
 */

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

type Avstamning = {
  antal_transaktioner: number;
  antal_underlag: number;
  matchade: { datum: string; text: string; belopp: string; motpart: string | null }[];
  saknar_underlag: { datum: string; text: string; belopp: string }[];
  saknar_banktransaktion: { datum: string; motpart: string | null; brutto: string }[];
  sammanfattning: string[];
};

export function BokforingPanel() {
  const [underlag, setUnderlag] = useState<Underlag[] | null>(null);
  const [rapport, setRapport] = useState<Rapport | null>(null);
  const [period, setPeriod] = useState(innevarandeManad);
  const [laddarUpp, setLaddarUpp] = useState(false);
  const [fel, setFel] = useState<string | null>(null);
  const filväljare = useRef<HTMLInputElement>(null);
  // Avstämningen har en EGEN väljare. Delad med underlagsväljaren hade betytt
  // ett accept-attribut som släpper igenom både kvitton och CSV, och då hamnar
  // kontoutdraget i avläsningen — vilket ger ett nonsensverifikat per rad.
  const utdragsväljare = useRef<HTMLInputElement>(null);
  const [avstamning, setAvstamning] = useState<Avstamning | null>(null);
  const [stammerAv, setStammerAv] = useState(false);
  const [rensar, setRensar] = useState(false);

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

  async function stamAv(fil: File | null) {
    if (!fil) return;
    setStammerAv(true);
    setFel(null);
    setAvstamning(null);
    try {
      const kropp = new FormData();
      kropp.append("fil", fil);
      const svar = await fetch(
        `${BAS}/avstamning?fran=${period.fran}&till=${period.till}`,
        { method: "POST", body: kropp }
      );
      setAvstamning(await readJson<Avstamning>(svar));
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setStammerAv(false);
    }
  }

  /**
   * Tömmer perioden — underlagen och verifikaten som räknats ur dem.
   *
   * EN funktion bakom BÅDA Rensa-knapparna, med flit. Summorna i
   * periodavsnittet ÄR underlagen: `berakna_period` läser inget annat, så en
   * knapp som bara nollade siffrorna hade nollat en vy och inte ett underlag,
   * och nästa hämtning hade satt tillbaka dem. Två knappar som gjorde olika
   * saker åt samma data hade dessutom lämnat frågan om vilken som gällde.
   *
   * Frågan innan är inte en formalitet. Raderingen är äkta, och originalfilerna
   * finns inte kvar att ladda upp igen — bara sha256:n sparades någonsin — så
   * det som försvinner går bara att få tillbaka genom att läsa av kvittona på
   * nytt.
   */
  async function rensa() {
    if (!harUnderlag) return;
    const bekraftat = window.confirm(
      `Rensa ${period.fran} till ${period.till}?\n\n` +
        `${underlag?.length ?? 0} underlag och deras konteringar raderas. ` +
        "Det går inte att ångra."
    );
    if (!bekraftat) return;

    setRensar(true);
    setFel(null);
    try {
      const svar = await fetch(`${BAS}/period?fran=${period.fran}&till=${period.till}`, {
        method: "DELETE"
      });
      await readJson(svar);
      // Avstämningen jämförde mot underlag som inte finns längre. Att låta den
      // ligga kvar hade gett en lista över "saknar underlag" som stämmer av
      // ren slump.
      setAvstamning(null);
      await hamta();
    } catch (orsak) {
      setFel(felmeddelande(orsak));
    } finally {
      setRensar(false);
    }
  }

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
  const harUnderlag = (underlag?.length ?? 0) > 0;

  /**
   * Vidarebefordran: ett `mailto:`-utkast med periodens dokument som text.
   *
   * DOKUMENTET SJÄLVT KAN INTE BIFOGAS, och det är inte en förenkling utan en
   * följd av två saker som båda står fast. `mailto:` har ingen
   * bilage-parameter i någon webbläsare — det är en RFC 6068-begränsning, inte
   * en lucka — och originalfilen finns dessutom inte kvar att bifoga: `sha256`
   * är allt som sparas av ett kvitto (migration 045). Det som går att skicka
   * vidare är alltså de AVLÄSTA fälten, och utkastet säger det rakt ut i
   * stället för att låta mottagaren undra var filen tog vägen.
   *
   * Det bär kunddata till kundens EGEN e-postklient och ingen annanstans:
   * `mailto:` går till operativsystemet, inte över nätet, och adressraden
   * lämnas tom så att avsändaren fyller i mottagaren själv.
   */
  const vidarebefordran = (() => {
    const rader = (underlag ?? []).map(
      (rad) =>
        `${rad.datum ?? "utan datum"}  ${rad.motpart || rad.filnamn}  ` +
        `${kronor(rad.brutto)}  moms ${procent(rad.momssats)}` +
        `${rad.status === "granska_manuellt" ? "  (granskas manuellt)" : ""}`
    );
    const brodtext = [
      `Bokföringsunderlag ${period.fran} till ${period.till}.`,
      "",
      ...rader,
      "",
      `${rader.length} dokument. Beloppen är avlästa ur kvittona och är förslag `
        + "— originalfilerna sparas inte och kan därför inte bifogas här.",
      ""
    ].join("\n");
    // encodeURIComponent, inte URLSearchParams: den senare kodar mellanslag
    // som "+", och ett plustecken i en mailto-kropp blir ett plustecken i
    // utkastet — inte ett mellanslag.
    return (
      `mailto:?subject=${encodeURIComponent(`Bokföringsunderlag ${period.fran}–${period.till}`)}` +
      `&body=${encodeURIComponent(brodtext)}`
    );
  })();

  // SAMMA element på två ställen: sist i periodavsnittets rubrikrad, sist i
  // dokumentavsnittets. Skrivet en gång så att de två inte kan glida isär i
  // utseende — att de ser lika ut är hela poängen med dem.
  const rensaKnapp = (
    <button
      type="button"
      disabled={rensar || !harUnderlag}
      onClick={() => void rensa()}
      title={harUnderlag ? undefined : "Det finns inget att rensa i perioden."}
      className={cn(btnSecondary, btnLiten)}
    >
      {rensar ? (
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      ) : (
        <Trash2 className="h-4 w-4" aria-hidden />
      )}
      Rensa
    </button>
  );

  // Datumfälten. Bor i periodavsnittets rubrikrad och ERSÄTTER rubriken
  // "Perioden" som stod där — intervallet säger vilken period det är, vilket
  // ordet aldrig gjorde.
  const datumfalt = (
    <div className="flex flex-wrap items-end gap-2">
      <label className="flex flex-col gap-1">
        <span className="text-[0.75rem] font-medium text-ink/55">Från</span>
        {/* type="date" och inte en datumväljare: webbläsarens egen är
            tillgänglig, lokaliserad och kostar noll kilobyte. */}
        <input
          type="date"
          value={period.fran}
          onChange={(e) => setPeriod((p) => ({ ...p, fran: e.target.value }))}
          className="focus-ring h-9 rounded-input bg-paper2 px-2.5 text-[0.875rem]"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-[0.75rem] font-medium text-ink/55">Till</span>
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
          {fel}
        </p>
      ) : null}

      {/* Periodsummorna.

          Avsnittet renderas ALLTID, inte bara när `rapport` finns. Datumfälten
          bor numera i rubrikraden, och ett villkorat avsnitt hade tagit bort
          dem i exakt det läge de behövs mest: när hämtningen misslyckats och
          perioden ska bytas för att komma vidare. */}
      <section>
        <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-3">
          {datumfalt}
          <div className="flex flex-wrap items-center gap-2">
            {/* Bara den fällda perioden får en märkning. "Går ihop" är
                borttaget på begäran 2026-08-24: siffrorna VISAS bara när
                perioden går ihop — `berakna_period` lämnar brister i stället —
                så märket sa samma sak som summorna redan sa. Går den inte ihop
                står det däremot ingen annanstans i rubrikraden, och det märket
                står kvar. */}
            {rapport && !klar ? <Badge tone="warn">Granska manuellt</Badge> : null}
            {/* Avstämningen hör till perioden, inte till dokumenten: den
                svarar på om periodens underlag täcker kontoutdragets rader. Den
                flyttade hit när uppladdning och export flyttade ner, hellre än
                att bli ensam kvar i en åtgärdsrad utan avsnitt. */}
            <button
              type="button"
              disabled={stammerAv}
              onClick={() => utdragsväljare.current?.click()}
              className={cn(btnSecondary, btnLiten)}
            >
              {stammerAv ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Scale className="h-4 w-4" aria-hidden />
              )}
              Stäm av kontoutdrag
            </button>
            {rensaKnapp}
          </div>
        </div>

        {rapport ? (
          <>
            <dl // Två kolumner, inte tre. `lg:grid-cols-3` mäter VIEWPORTEN, inte spalten
              // — och sedan panelen ligger i sju av tolv kolumner blev tre summor
              // bredvid varandra trånga just på de bredder där tre skulle rymts.
              className="mt-4 grid gap-x-8 gap-y-3 border-y border-ink/15 py-4 sm:grid-cols-2">
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
          </>
        ) : null}
      </section>

      {/* Avstämningen mot kontoutdraget.

          Ligger FÖRE underlagslistan med flit: den svarar på frågan "har jag
          fått med allt?", och svaret bestämmer om man behöver läsa listan alls. */}
      {avstamning ? (
        <section>
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="font-display text-[1.25rem]">Avstämning</h2>
            <Badge
              tone={
                avstamning.saknar_underlag.length || avstamning.saknar_banktransaktion.length
                  ? "warn"
                  : "good"
              }
            >
              {avstamning.matchade.length} av {avstamning.antal_transaktioner} matchade
            </Badge>
          </div>

          <ul className="mt-3 space-y-1 text-[0.9375rem] text-ink/70">
            {avstamning.sammanfattning.map((rad) => (
              <li key={rad}>{rad}</li>
            ))}
          </ul>

          {avstamning.saknar_underlag.length ? (
            <div className="mt-4">
              <p className="kicker text-mineral">Banktransaktioner utan underlag</p>
              <div className="mt-2 divide-y divide-ink/15 border-y border-ink/15">
                {avstamning.saknar_underlag.map((rad, i) => (
                  <div key={i} className="flex flex-wrap items-baseline gap-x-4 py-2">
                    <span className="w-[6.5rem] shrink-0 text-[0.875rem] tabular-nums text-ink/62">
                      {rad.datum}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-[0.875rem]">{rad.text || "—"}</span>
                    <span className="w-[7.5rem] text-right text-[0.875rem] font-medium tabular-nums">
                      {kronor(rad.belopp)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {avstamning.saknar_banktransaktion.length ? (
            <div className="mt-4">
              <p className="kicker text-mineral">Underlag utan banktransaktion</p>
              <div className="mt-2 divide-y divide-ink/15 border-y border-ink/15">
                {avstamning.saknar_banktransaktion.map((rad, i) => (
                  <div key={i} className="flex flex-wrap items-baseline gap-x-4 py-2">
                    <span className="w-[6.5rem] shrink-0 text-[0.875rem] tabular-nums text-ink/62">
                      {rad.datum}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-[0.875rem]">
                      {rad.motpart || "—"}
                    </span>
                    <span className="w-[7.5rem] text-right text-[0.875rem] font-medium tabular-nums">
                      {kronor(rad.brutto)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          <p className="mt-3 max-w-[70ch] text-[0.8125rem] leading-6 text-ink/50">
            Matchat på belopp och datum inom tre dagar. Kontoutdraget sparas
            inte — det läses, jämförs och kastas.
          </p>
        </section>
      ) : null}

      {/* Underlagen */}
      <section>
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
          <h2 className="font-display text-[1.25rem]">Infoga dokument</h2>
          {/* Knapparna står i rubrikraden av samma skäl som datumen står i
              periodens: åtgärden hör till avsnittet den verkar på. Alla har
              btnLiten och därmed samma höjd som datumfälten. */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={laddarUpp}
              onClick={() => filväljare.current?.click()}
              className={cn(btnPrimary, btnLiten)}
            >
              {laddarUpp ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Upload className="h-4 w-4" aria-hidden />
              )}
              Ladda upp
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
              className={cn(btnSecondary, btnLiten, !klar && "pointer-events-none opacity-40")}
            >
              <Download className="h-4 w-4" aria-hidden />
              Exportera
            </a>

            {/* `mailto:` och inte en egen utskicksväg. Se `vidarebefordran`. */}
            <a
              href={harUnderlag ? vidarebefordran : undefined}
              aria-disabled={!harUnderlag}
              title={
                harUnderlag
                  ? "Öppnar ett utkast i din e-post med periodens dokument som text."
                  : "Det finns inga dokument att vidarebefordra."
              }
              className={cn(
                btnSecondary,
                btnLiten,
                !harUnderlag && "pointer-events-none opacity-40"
              )}
            >
              <Forward className="h-4 w-4" aria-hidden />
              Vidarebefordra
            </a>

            {rensaKnapp}
          </div>
        </div>
        {underlag === null ? (
          <div className="mt-4">
            <SkeletonRows />
          </div>
        ) : underlag.length === 0 ? (
          <div className="mt-4">
            <EmptyState
              title="Inga dokument i perioden"
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

      {/* Filväljarna. Knapparna som öppnar dem bor i sina avsnitt; själva
          inputarna är `sr-only` och renderar ingenting, så de ligger sist —
          `ref`:en bryr sig inte om var i DOM:en de står, men `space-y-8` gör
          det: en absolut positionerad input tar ingen plats men räknas som
          syskon, och två av dem överst gav panelen ett tomt glapp på toppen.

          TVÅ väljare, inte en. Se `utdragsväljare` ovan. */}
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
      <input
        ref={utdragsväljare}
        type="file"
        accept=".csv,text/csv"
        onChange={(e) => {
          void stamAv(e.target.files?.[0] ?? null);
          e.target.value = "";
        }}
        className="sr-only"
      />
    </div>
  );
}
