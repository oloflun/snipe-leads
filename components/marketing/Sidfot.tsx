"use client";

import Link from "next/link";
import { useLocale, type Localized } from "@/lib/i18n";
import { bolagsraden, dataskyddKontakt } from "@/lib/bolag";
import { FAMILJ, LANDNINGAR } from "@/lib/landningar";
import type { Paket } from "@/lib/pricing";
import { KONTAKT_MEJL, shared } from "@/components/marketing/copy";

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
/**
 * Sökordssidorna i sidfoten (2026-11-05). Utan länkar från varje sida är de
 * sidor ingen hittar: en sökmotor väger en sida efter hur sajten själv länkar
 * till den, och Googles sidlänkar under träffen på "snajp" väljs bland sidorna
 * sajten lyfter fram. Grupperade efter produkt, i lib/landningar.ts ordning.
 */
const forPaket = (id: Paket["id"]): { namn: Localized; vag: string }[] => LANDNINGAR.filter((p) => p.produkt === id);

const GRUPPER: { rubrik: Localized; poster: { namn: Localized; vag: string }[] }[] = [
  { rubrik: FAMILJ.leads.namn, poster: [{ namn: FAMILJ.leads.lank, vag: FAMILJ.leads.vag }, ...forPaket("leads")] },
  { rubrik: FAMILJ.support.namn, poster: [{ namn: FAMILJ.support.lank, vag: FAMILJ.support.vag }, ...forPaket("support")] },
  {
    rubrik: { sv: "Snajp", en: "Snajp" },
    poster: [
      ...forPaket("duo"),
      { namn: { sv: "Frågor och svar", en: "Questions and answers" }, vag: "/faq" },
      { namn: shared.menyTeam, vag: "/vart-team" },
      { namn: shared.menyBokaDemo, vag: "/boka-demo" }
    ]
  }
];

export function Sidfot() {
  const { text } = useLocale();
  return (
    <div className="border-t border-ink/12">
      <div className="mx-auto max-w-[1480px] px-6 py-8 md:px-10">
        <nav
          aria-label={text({ sv: "Lösningar", en: "Solutions" })}
          className="grid grid-cols-1 gap-x-10 gap-y-8 border-b border-ink/12 pb-10 pt-2 md:grid-cols-2 lg:grid-cols-3"
        >
          {GRUPPER.map((grupp) => (
            <div key={grupp.rubrik.sv}>
              <p className="text-[0.8125rem] font-medium text-ink-subtle">{text(grupp.rubrik)}</p>
              <ul className="mt-3 flex flex-col gap-2.5">
                {grupp.poster.map((post) => (
                  <li key={post.vag}>
                    {/* Ingen förhämtning: sidorna är dynamiska, och elva
                        förhämtningar varje gång sidfoten syns hade varit elva
                        serveranrop som sällan används. En crawler läser href
                        oavsett. */}
                    <Link
                      href={post.vag}
                      prefetch={false}
                      className="focus-ring rounded-input text-[0.9375rem] text-ink-muted transition-colors hover:text-ink"
                    >
                      {text(post.namn)}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        <div className="mt-8 flex flex-col gap-4 text-[0.875rem] leading-[1.6] text-ink-subtle md:flex-row md:items-baseline md:justify-between">
          <p>{bolagsraden()}</p>

          <nav className="flex flex-wrap gap-x-6 gap-y-2">
            <Link href="/integritetspolicy" className="focus-ring hover:text-ink">
              {text({ sv: "Integritetspolicy", en: "Privacy policy" })}
            </Link>
            <Link href="/villkor" className="focus-ring hover:text-ink">
              {text({ sv: "Användarvillkor", en: "Terms of service" })}
            </Link>
            <Link href="/angerratt" className="focus-ring hover:text-ink">
              {text({ sv: "Ångerrätt", en: "Right of withdrawal" })}
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

        <p className="mt-4 text-[0.8125rem] text-ink-subtle">
          {text({ sv: "Frågor om tjänsten: ", en: "Questions about the service: " })}<a href={`mailto:${KONTAKT_MEJL}`} className="focus-ring hover:text-ink-muted">{KONTAKT_MEJL}</a>
        </p>
      </div>
    </div>
  );
}
