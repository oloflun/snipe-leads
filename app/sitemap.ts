import { KANONISK_ORIGIN } from "@/lib/kanonisk";
import type { MetadataRoute } from "next";
import { arProduktion } from "@/lib/miljo";

/**
 * sitemap.xml för de publika sidorna.
 *
 * ## Varför den tillkommer nu
 *
 * Fram till 2026-08-25 fanns ingen, och `app/robots.ts` sa det uttryckligen:
 * en `sitemap:`-rad som pekar på en 404 är sämre än ingen rad alls. Det stämde
 * så länge sajten var en enda sida med ankare — en sitemap över ett dokument
 * tillför ingenting.
 *
 * Med /boka-demo, /faq och /vart-team är den situationen en annan. Tre nya
 * publika adresser som bara nås via en hopfälld meny är tre adresser en
 * sökmotor kan missa, och /faq är dessutom den sida som svarar på de frågor
 * folk faktiskt söker på.
 *
 * ## Samma grind som robots.txt
 *
 * `arProduktion()` avgör, av exakt det skäl som står i lib/miljo.ts:
 * development-miljön är en SPEGEL av produktionen. En sitemap som räknar upp
 * spegelns adresser vore att servera den på fat åt en crawler — värre än
 * ingen robots.txt, eftersom den pekar ut varje sida i stället för att låta
 * dem hittas en och en.
 *
 * Utanför produktion returneras därför en tom lista. Filen svarar 200 med noll
 * poster i stället för 404, vilket är rätt: robots.txt i produktion pekar hit,
 * och en tom sitemap är ett giltigt svar medan en trasig länk inte är det.
 *
 * `force-dynamic` av samma skäl som robots.ts: miljövariabeln får inte bakas
 * in vid bygget, för då avgörs utfallet av VAR bygget skedde i stället för var
 * det körs.
 */
export const dynamic = "force-dynamic";

// Kanonisk adress ur EN källa. Tre hårdkodade kopior av ett värdnamn
// (layout, robots, sitemap) glider isär, och en sitemap som pekar på fel
// värd ber sökmotorn indexera en omdirigering.
const BAS = KANONISK_ORIGIN;

/** De publika sidorna. Inloggade ytor hör inte hemma här — se robots.ts. */
const SIDOR: { vag: string; prioritet: number; frekvens: MetadataRoute.Sitemap[number]["changeFrequency"] }[] = [
  { vag: "/", prioritet: 1.0, frekvens: "weekly" },
  { vag: "/leads", prioritet: 0.9, frekvens: "weekly" },
  { vag: "/support", prioritet: 0.9, frekvens: "weekly" },
  { vag: "/bokforing", prioritet: 0.9, frekvens: "weekly" },
  // Bokningen är den sida vi faktiskt vill att folk landar på.
  { vag: "/boka-demo", prioritet: 0.8, frekvens: "monthly" },
  // FAQ:n svarar på det folk söker efter, och varje fråga har ett eget ankare.
  { vag: "/faq", prioritet: 0.7, frekvens: "monthly" },
  { vag: "/vart-team", prioritet: 0.5, frekvens: "monthly" },
  { vag: "/integritetspolicy", prioritet: 0.3, frekvens: "yearly" },
  { vag: "/villkor", prioritet: 0.3, frekvens: "yearly" },
  { vag: "/cookies", prioritet: 0.3, frekvens: "yearly" }
];

export default function sitemap(): MetadataRoute.Sitemap {
  if (!arProduktion()) return [];

  return SIDOR.map(({ vag, prioritet, frekvens }) => ({
    url: `${BAS}${vag}`,
    // Ingen `lastModified`. Ett påhittat datum är sämre än inget: en sökmotor
    // som får "ändrad i dag" på en sida som stått stilla i ett halvår lär sig
    // att inte lita på fältet. Vill vi ha det ska det komma från git, inte
    // från new Date().
    changeFrequency: frekvens,
    priority: prioritet
  }));
}
