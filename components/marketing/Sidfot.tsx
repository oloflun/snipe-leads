import Link from "next/link";
import { bolagsraden, dataskyddKontakt } from "@/lib/bolag";
import { KONTAKT_MEJL } from "@/components/marketing/copy";

/**
 * Den juridiska raden längst ned på Snajps EGNA publika sidor.
 *
 * ## Varför den är skild från sidfoten i LandingPhoto
 *
 * Den sidfoten är marknadsföring: vilka vi är, hur du når oss, vad som gäller
 * kunddata. Den här är identifikation — bolagsnamn, organisationsnummer,
 * postadress och länkarna till policy, villkor och cookies. Två olika syften,
 * och det andra måste finnas på VARJE publik sida, inte bara på startsidan.
 * Därför en egen komponent som båda ställena renderar.
 *
 * ## Aldrig på kundens domän
 *
 * Anroparen ansvarar för att bara rendera den när `tenant` är null. På
 * kundens domän är vi supportchatten på deras sajt (TENANTS.md) — vårt
 * organisationsnummer i deras sidfot är fel bolag på fel sajt.
 *
 * ## Varningsrutan är borttagen (2026-08-25, på begäran)
 *
 * Den gula rutan sade att uppgifterna nedan är platshållare. Med den borta får
 * ingen platshållare renderas: raden byggs av `bolagsraden()`, som utelämnar
 * det som inte är ifyllt. I dag finns bara bolagsnamnet, så raden är kort —
 * det är rätt. "org.nr [XXXXXX-XXXX]" var det inte.
 *
 * `bolagsuppgifterna_klara` finns kvar i lib/bolag.ts och är fortfarande false.
 * Ingenting läser den längre, och det är värt att veta: det finns inte längre
 * något i gränssnittet som påminner om att uppgifterna saknas.
 */
export function Sidfot() {
  return (
    <div className="border-t border-ink/12">
      <div className="mx-auto max-w-[1480px] px-6 py-8 md:px-10">
        <div className="flex flex-col gap-4 text-[0.875rem] leading-[1.6] text-ink/50 md:flex-row md:items-baseline md:justify-between">
          <p>{bolagsraden()}</p>

          <nav className="flex flex-wrap gap-x-6 gap-y-2">
            <Link href="/integritetspolicy" className="focus-ring hover:text-ink">
              Integritetspolicy
            </Link>
            <Link href="/villkor" className="focus-ring hover:text-ink">
              Användarvillkor
            </Link>
            <Link href="/cookies" className="focus-ring hover:text-ink">
              Cookies
            </Link>
            {/* Dataskyddsadressen, med KONTAKT_MEJL som fungerande reserv tills
                den ligger på egen domän. Stod förut som `[integritet@snajp.se]`
                och länkade dit — alltså en död mailto på den rad där en
                registrerad ska höra av sig. */}
            <a
              href={`mailto:${dataskyddKontakt(KONTAKT_MEJL)}`}
              className="focus-ring hover:text-ink"
            >
              {dataskyddKontakt(KONTAKT_MEJL)}
            </a>
          </nav>
        </div>

        <p className="mt-4 text-[0.8125rem] text-ink/35">
          Frågor om tjänsten: <a href={`mailto:${KONTAKT_MEJL}`} className="focus-ring hover:text-ink/60">{KONTAKT_MEJL}</a>
        </p>
      </div>
    </div>
  );
}
