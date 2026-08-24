import Link from "next/link";
import { BOLAG, bolagsuppgifterna_klara, DATASKYDD_MEJL } from "@/lib/bolag";
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
 * ## Varningsrutan
 *
 * Så länge bolagsuppgifterna är platshållare visas en synlig ruta. Den är
 * ful med flit: en gul ruta på säljsidan blir åtgärdad, en `TODO` i en
 * kommentar blir det inte.
 */
export function Sidfot() {
  return (
    <div className="border-t border-ink/12">
      <div className="mx-auto max-w-[1480px] px-6 py-8 md:px-10">
        {bolagsuppgifterna_klara ? null : (
          <p className="mb-6 rounded-card border border-ochre/40 bg-ochre/10 px-4 py-3 text-[0.875rem] leading-[1.6] text-ink/80">
            <strong className="font-semibold">Ej klart för lansering.</strong> Bolagsuppgifterna
            nedan är platshållare, och de juridiska sidorna är ett förstautkast som inte granskats
            av jurist. Se <code className="font-mono text-[0.8125rem]">docs/JURIDIK_ATGARDER.md</code>.
          </p>
        )}

        <div className="flex flex-col gap-4 text-[0.875rem] leading-[1.6] text-ink/50 md:flex-row md:items-baseline md:justify-between">
          <p>
            {BOLAG.namn} · org.nr {BOLAG.orgnr} · {BOLAG.postadress}
          </p>

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
            <a href={`mailto:${DATASKYDD_MEJL}`} className="focus-ring hover:text-ink">
              {DATASKYDD_MEJL}
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
