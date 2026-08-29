import { arKonfigurerad } from "@/lib/skatteverket/oauth";

/**
 * Ingången till BankID-inloggningen mot Skatteverket.
 *
 * En vanlig länk och inte en knapp med onClick: flödet ÄR en navigering bort
 * från sajten, och en fetch hade inte kunnat följa omdirigeringen till
 * Skatteverkets legitimeringssida. `retur` tar användaren tillbaka hit efteråt
 * (spärrad mot öppen omdirigering i `sakerReturvag`).
 *
 * Serverkomponent med flit: `arKonfigurerad()` läser env-varer som aldrig får
 * nå webbläsaren. Är flödet inte påslaget renderas ingenting alls — en knapp
 * som garanterat svarar 503 är sämre än ingen knapp.
 */
export function SkatteverketKnapp({ retur = "/bokforing" }: { retur?: string }) {
  if (!arKonfigurerad()) return null;

  return (
    <div className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
      <h3 className="text-sm font-medium">Hämta uppgifter från Skatteverket</h3>
      <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
        Legitimera dig med BankID så kan assistenten se vilken momsperiod och
        redovisningsmetod som gäller för ditt bolag, i stället för att svara
        allmänt. Uppslaget gäller bara ditt eget företag.
      </p>
      <a
        href={`/api/skatteverket/start?retur=${encodeURIComponent(retur)}`}
        className="mt-3 inline-flex items-center rounded-md bg-neutral-900 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-700 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
      >
        Logga in med BankID
      </a>
      <p className="mt-2 text-xs text-neutral-500">
        Skatteverket loggar varje förfrågan i upp till fem år för att kunna
        utreda säkerhetsincidenter.
      </p>
    </div>
  );
}
