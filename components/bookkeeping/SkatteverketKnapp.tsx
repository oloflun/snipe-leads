import { ShieldCheck } from "lucide-react";
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
 *
 * ## Inga `dark:`-klasser här, och det är inte en förbiseelse
 *
 * Appen växlar tema med `:root[data-theme="dark"]` och byter TOKENS (se
 * app/globals.css), inte med Tailwinds `dark:`-variant. Första versionen av den
 * här komponenten använde `dark:bg-white` och liknande, och resultatet syntes
 * först när sidan renderades: i mörkt läge slog varianterna till och gav en vit
 * knapp — men bakgrunden och rubriken kom från tokens och förblev ljusa. En
 * halvvänd komponent, alltså. `bg-ink`/`text-paper` vänder sig själva.
 */
export function SkatteverketKnapp({ retur = "/bokforing" }: { retur?: string }) {
  if (!arKonfigurerad()) return null;

  return (
    <section className="rounded-card border border-ink/15 bg-paper2 p-5">
      <h3 className="flex items-center gap-2 text-[0.9375rem] font-medium text-ink">
        <ShieldCheck className="h-4 w-4 shrink-0 text-ochre" aria-hidden />
        Hämta uppgifter från Skatteverket
      </h3>

      <p className="mt-2 max-w-[58ch] text-[0.8125rem] leading-6 text-ink/60">
        Legitimera dig med BankID så kan assistenten se vilken momsperiod och
        redovisningsmetod som gäller för ditt bolag, i stället för att svara
        allmänt. Uppslaget gäller bara ditt eget företag.
      </p>

      <a
        href={`/api/skatteverket/start?retur=${encodeURIComponent(retur)}`}
        className="focus-ring mt-4 inline-flex h-10 items-center rounded-input bg-ink px-4 text-[0.8125rem] font-medium text-paper hover:bg-ink2"
      >
        Logga in med BankID
      </a>

      {/* Upplysningsskyldighet enligt §8 i Skatteverkets allmänna villkor —
          slutanvändaren SKA informeras om auditloggningen. Det är ett avtalskrav,
          inte en artighet, och därför står den här och inte i en hjälptext.

          Linjen sitter på WRAPPERN och inte på stycket: med `border-t` och
          `max-w` på samma element slutade linjen mitt i kortet, vilket syntes
          först i en rendering. Textbredden hör till texten, avdelaren till
          kortet. */}
      <div className="mt-4 border-t border-ink/10 pt-3">
        <p className="max-w-[58ch] text-[0.75rem] leading-5 text-ink/45">
          Skatteverket loggar varje förfrågan i upp till fem år för att kunna
          utreda säkerhetsincidenter.
        </p>
      </div>
    </section>
  );
}
