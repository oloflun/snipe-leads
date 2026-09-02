import { ExempelbolagDemo } from "@/components/leads/ExempelbolagDemo";
import { ICP_ETIKETTER } from "@/lib/leads/icpLabels";

/**
 * Förhandsvisning av hur en avslutad leads-körning ser ut.
 *
 * ## Varför sidan finns
 *
 * Resultatvyn ligger bakom en inloggning OCH bakom en körning som kostar
 * LLM-anrop. Att granska hur den SER UT krävde alltså ett konto, en tenant med
 * nycklar och en riktig körning — vilket i praktiken betyder att ingen
 * granskar den, och att den vy som visar produktens viktigaste ögonblick är
 * den enda ingen tittar på.
 *
 * Sidan är publik med flit och kan vara det: varje bolag här är påhittat, och
 * ingen rad kommer från någon kunds data. Se `bygg_exempelbolag` i
 * app/leads/exempelbolag.py — org.numren har medvetet fel kontrollsiffra och
 * domänerna ligger under `.example`.
 *
 * ## Vad den INTE är
 *
 * Ingen körning startas härifrån och inget skrivs. Ändras listans utseende i
 * `LeadsRunForm` ändras den här sidan med, eftersom den renderar samma
 * komponent — en kopia hade slutat spegla produkten inom en vecka.
 *
 * Bolagen och "Uppdatera"-växlingen bodde tidigare inline här. De flyttade
 * till components/leads/ExempelbolagDemo.tsx när listan skulle visas bredvid
 * körningsformuläret på fler ytor — samma data, en källa.
 */

/** Samma etiketter som formuläret använder — se ICP_ETIKETTER. */
const ÖVERSKRIVNINGAR: [string, string][] = [
  [ICP_ETIKETTER.industries.label, "Bygg"],
  [ICP_ETIKETTER.geography.label, "Umeå"],
  [ICP_ETIKETTER.roles.label, "inköpschef"],
  [ICP_ETIKETTER.deal_breakers.label, "Under 10 anställda"]
];

export default function Page() {
  return (
    <main className="min-h-screen bg-paper py-10 text-ink">
      <div className="mx-auto max-w-[900px] space-y-6 px-4 md:px-6">
        <header>
          <p className="text-[0.8125rem] font-medium text-ink/45">Förhandsvisning</p>
          <h1 className="mt-1 text-[1.5rem] font-semibold leading-tight tracking-[-0.02em]">
            Så ser en avslutad körning ut
          </h1>
          <p className="mt-2 max-w-[68ch] text-[0.9375rem] leading-[1.6] text-ink/65">
            Samma komponenter som kundens leads-vy renderar efter en körning. Alla bolag här är
            påhittade — sidan startar ingen körning och skriver ingenting.
          </p>
          <p className="mt-3 max-w-[68ch] rounded-card bg-paper2/60 p-4 text-[0.9375rem] leading-[1.6] text-ink/70">
            <strong className="font-semibold">Klicka på ett bolag</strong> för att öppna utkastet.
            Där finns Email Studios alla åtgärder — Kortare, Skriv om, Förbättra, Personalisera,
            Översätt, A/B-varianter, Uppföljning och Analysera — och du kan skriva om texten själv
            innan du provar dem. <em>Skicka test</em> skickar ingenting.
          </p>
        </header>

        <div className="rounded-card bg-paper2/60 p-5">
          <p className="text-[15px]">
            <strong className="font-semibold">3</strong> bolag i körningen · bara research ·
            testkörning
          </p>
          <dl className="mt-4 grid gap-x-8 gap-y-3 sm:grid-cols-2">
            {ÖVERSKRIVNINGAR.map(([etikett, värde]) => (
              <div key={etikett} className="border-t border-ink/10 pt-2">
                <dt className="text-[12px] font-medium uppercase tracking-[0.04em] text-ink/45">
                  {etikett}
                </dt>
                <dd className="mt-1 text-[14px] leading-6 text-ink/80">{värde}</dd>
              </div>
            ))}
          </dl>
        </div>

        <ExempelbolagDemo />
      </div>
    </main>
  );
}
