import Link from "next/link";
import { Radgivare } from "@/components/admin/Radgivare";
import type { TenantRow } from "@/lib/data/admin";
import { formateraPris } from "@/lib/pricing";
import {
  MARGINAL_GRON,
  MARGINAL_ROD,
  TOKENKOSTNAD_PER_MILJON_SEK,
  TYST_EFTER_DAGAR,
  bedomKund,
  sammanfattaPortfolj
} from "@/lib/admin/halsa";

/**
 * Adminöversikten: hela portföljen på en skärm.
 *
 * Ledger, inte kort — en rad per kund, hairline mellan, tabularsiffror så
 * kolumnerna går att jämföra vertikalt. Symbolen längst till vänster är det
 * enda som får färg; hade varje kolumn haft en accent hade ingen av dem varit
 * en.
 *
 * ## Två saker som INTE är mätvärden, och som därför står utskrivna
 *
 * 1. **Paketet härleds ur aktivitet.** `listTenants()` returnerar inte vilka
 *    produkter arbetsytan äger, så en kund med ärenden räknas som Support och
 *    en med körningar som Leads. Det stämmer för en kund som använder det den
 *    betalar för och blir fel för en som betalar utan att använda — vilket är
 *    precis den kund raden ska varna för. Kopplas `workspaces.products` in i
 *    admin-API:t ska härledningen bort.
 *
 * 2. **Tokenkostnaden är en uppskattning**, inte en faktura. Se
 *    `TOKENKOSTNAD_PER_MILJON_SEK`. Fotnoten under tabellen säger det till
 *    läsaren, eftersom en marginal som presenteras utan förbehåll blir ett
 *    beslutsunderlag den inte är.
 */

function harledProdukter(rad: TenantRow): string[] {
  const produkter: string[] = [];
  // Provkörningar räknas MED här, till skillnad från i volymkolumnen. Frågan
  // är vilken produkt tenanten använder, och en testkörning är leads-agenten
  // som kört — annars tappade demokontot sin leads-halva i samma sekund som
  // is_test började fyllas i.
  if (rad.runs + (rad.test_runs ?? 0) > 0) produkter.push("leads");
  if (rad.tickets > 0) produkter.push("support");
  return produkter;
}

const HALSOETIKETT: Record<string, string> = {
  bra: "Bra",
  ok: "Håll koll",
  dalig: "Åtgärda",
  tyst: "Tyst",
  okand: "Okänd"
};

export function Portfoljvy({ tenants }: Readonly<{ tenants: TenantRow[] }>) {
  const rader = tenants.map((rad) => ({
    rad,
    ekonomi: bedomKund({
      produkter: harledProdukter(rad),
      tokensIn: rad.tokens_in ?? 0,
      tokensUt: rad.tokens_out ?? 0,
      korningar: rad.runs ?? 0,
      arenden: rad.tickets ?? 0,
      senasteAktivitet: rad.last_activity
    })
  }));

  // Sämst först. Adminvyn finns för att hitta problem, inte för att bekräfta
  // att det mesta är bra — en lista sorterad på namn hade begravt den enda rad
  // som krävde en åtgärd.
  const ordning = { dalig: 0, tyst: 1, ok: 2, okand: 3, bra: 4 } as const;
  rader.sort(
    (a, b) =>
      ordning[a.ekonomi.halsa] - ordning[b.ekonomi.halsa] ||
      b.ekonomi.intakt - a.ekonomi.intakt
  );

  const p = sammanfattaPortfolj(rader.map((r) => r.ekonomi));

  return (
    <div>
      {/* "Översikt" och inte "Kunder": fliken heter Översikt, och NÄSTA flik
          heter Kunder och leder till en annan sida. Två flikar vars sidor båda
          rubricerades "Kunder" läste som samma vy renderad två gånger. */}
      <h1 className="font-display text-4xl tracking-[-0.03em]">Översikt</h1>

      <div className="mt-8 grid gap-px overflow-hidden rounded-input border border-ink/15 bg-ink/15 sm:grid-cols-2 lg:grid-cols-4">
        <Nyckeltal
          etikett="Månadsintäkt"
          varde={formateraPris(p.mrr)}
          rad={`${p.antalBetalande} av ${p.antalKunder} kunder betalar`}
        />
        <Nyckeltal
          etikett="Uppskattad kostnad"
          varde={formateraPris(Math.round(p.kostnad))}
          rad="Tokens, alla kunder"
        />
        <Nyckeltal
          etikett="Marginal"
          varde={p.marginal === null ? "—" : `${Math.round(p.marginal * 100)} %`}
          rad={p.marginal === null ? "Ingen intäkt att räkna på" : "Intäkt minus tokenkostnad"}
        />
        <Nyckeltal
          etikett="Kräver åtgärd"
          varde={String(p.fordelning.dalig + p.fordelning.tyst)}
          rad={`${p.fordelning.dalig} med låg marginal, ${p.fordelning.tyst} tysta`}
        />
      </div>

      <div className="mt-10 overflow-x-auto">
        <div className="min-w-[900px]">
          <div className="grid grid-cols-12 gap-x-4 border-b border-ink/15 pb-3">
            {[
              ["", "col-span-1"],
              ["Kund", "col-span-3"],
              ["Paket", "col-span-2"],
              ["Ärenden", "col-span-1 text-right"],
              ["Körningar", "col-span-1 text-right"],
              ["Tokens", "col-span-1 text-right"],
              ["Kostnad", "col-span-1 text-right"],
              ["Marginal", "col-span-1 text-right"],
              ["Fel", "col-span-1 text-right"]
            ].map(([rubrik, kl]) => (
              <div key={String(rubrik) || "symbol"} className={`kicker text-mineral ${kl}`}>
                {rubrik}
              </div>
            ))}
          </div>

          <div className="divide-y divide-ink/15">
            {rader.map(({ rad, ekonomi }) => (
              <div key={rad.id} className="grid grid-cols-12 items-baseline gap-x-4 py-4">
                <div className="col-span-1 text-[1.25rem]" title={HALSOETIKETT[ekonomi.halsa]}>
                  <span aria-hidden="true">{ekonomi.symbol}</span>
                  <span className="sr-only">{HALSOETIKETT[ekonomi.halsa]}</span>
                </div>
                <div className="col-span-3 min-w-0">
                  <p className="truncate text-[1rem] font-semibold">{rad.name}</p>
                  <p className="mt-0.5 truncate text-[0.8125rem] text-ink/60">
                    {ekonomi.motivering}
                  </p>
                </div>
                <div className="col-span-2 text-[0.875rem] text-ink/70">
                  {ekonomi.paketNamn ?? "—"}
                  {ekonomi.intakt > 0 ? (
                    <span className="block text-[0.8125rem] text-mineral">
                      {formateraPris(ekonomi.intakt)}/mån
                    </span>
                  ) : null}
                </div>
                <Tal>{rad.tickets}</Tal>
                <Tal>
                  {rad.runs}
                  {/* Testkörningar göms inte, de räknas bara inte som kundvolym.
                      En siffra som tyst blivit mindre är svårare att lita på än
                      en siffra som säger vad den utelämnat. */}
                  {rad.test_runs ? (
                    <span className="block text-[0.8125rem] text-ink/40">
                      +{rad.test_runs} test
                    </span>
                  ) : null}
                </Tal>
                <Tal>{((rad.tokens_in ?? 0) + (rad.tokens_out ?? 0)).toLocaleString("sv-SE")}</Tal>
                <Tal>{formateraPris(Math.round(ekonomi.kostnad))}</Tal>
                <Tal>
                  {ekonomi.marginal === null ? "—" : `${Math.round(ekonomi.marginal * 100)} %`}
                </Tal>
                {/* Ochre bara på avvikelsen. */}
                <div
                  className={`col-span-1 text-right tabular-nums text-[0.9375rem] ${
                    rad.errors > 0 ? "text-ochre" : "text-ink/45"
                  }`}
                >
                  {rad.errors}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {rader.length === 0 ? (
        <p className="mt-8 text-[15px] text-ink/60">
          Inga kunder ännu. Tom lista är ett giltigt svar, inte ett fel.
        </p>
      ) : null}

      <div className="mt-10 max-w-[80ch] space-y-2 border-t border-ink/15 pt-5 text-[0.8125rem] leading-[1.6] text-mineral">
        <p>
          <strong className="text-ink/70">Kostnaden är en uppskattning</strong>, inte en faktura:{" "}
          {formateraPris(TOKENKOSTNAD_PER_MILJON_SEK)} per miljon tokens. Ändra talet i{" "}
          <code>lib/admin/halsa.ts</code> när ni vet utfallet från leverantören.
        </p>
        <p>
          Grönt över {Math.round(MARGINAL_GRON * 100)} % marginal, gult över{" "}
          {Math.round(MARGINAL_ROD * 100)} %. En kund utan aktivitet på{" "}
          {TYST_EFTER_DAGAR} dagar visas som tyst <span aria-hidden="true">😴</span> oavsett
          marginal — den som inte använder tjänsten har låg kostnad och ser lönsam ut precis
          innan den säger upp sig.
        </p>
        <p>
          Paketet härleds ur aktivitet, eftersom admin-API:t ännu inte returnerar{" "}
          <code>workspaces.products</code>. En kund som betalar utan att använda får därför fel
          paket i tabellen — och är samtidigt precis den kund raden ska varna för.
        </p>
      </div>

      {/* Rådgivaren får SAMMA rader som tabellen räknat fram, inte en egen
          hämtning. Två uträkningar av samma tal är två tillfällen att räkna
          olika, och här skulle skillnaden synas som att sidan säger emot sig
          själv. */}
      <Radgivare rader={rader.map(({ rad, ekonomi }) => ({ namn: rad.name, ekonomi }))} />

      <p className="mt-8">
        <Link href="/admin/korningar" className="focus-ring text-[15px] text-ochre underline underline-offset-4">
          Se alla körningar
        </Link>
      </p>
    </div>
  );
}

function Nyckeltal({
  etikett,
  varde,
  rad
}: Readonly<{ etikett: string; varde: string; rad: string }>) {
  return (
    <div className="bg-paper px-5 py-4">
      <p className="kicker text-mineral">{etikett}</p>
      <p className="mt-1.5 font-display text-[1.75rem] tabular-nums tracking-[-0.02em]">{varde}</p>
      <p className="mt-1 text-[0.8125rem] leading-[1.45] text-ink/60">{rad}</p>
    </div>
  );
}

function Tal({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="col-span-1 text-right tabular-nums text-[0.9375rem] text-ink/75">
      {children}
    </div>
  );
}
