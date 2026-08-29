import type { TenantRow } from "@/lib/data/admin";

/**
 * Exempeldata för adminytan — påhittade tal på TOMMA rader, aldrig på riktiga.
 *
 * ## Varför den här filen finns, trots att kodbasen säger emot den
 *
 * Kunder & Data har en fotnot som säger att påhittade siffror är värre än
 * inga, och den står kvar. Den handlar om intäkter och utgifter, alltså tal
 * någon fattar ett beslut på. Det här är något annat: en adminyta som bara
 * visar nollor går inte att bedöma som gränssnitt — kolumnbredder, sortering,
 * hälsobedömning, marginalfärger och rådgivaren är alla osynliga tills det
 * finns tal att rendera. Vyn behövde kunna visas.
 *
 * Tre regler håller isär det påhittade från det mätta, och de är inte
 * kosmetiska:
 *
 * 1. **Bara helt tomma rader berikas.** En arbetsyta med en enda körning, ett
 *    enda ärende eller ett enda fel är en RIKTIG kund och rörs aldrig. Nordlys
 *    Handel med sina 119 ärenden ser likadan ut med och utan den här filen.
 * 2. **Varje berikad rad bär `ar_exempel`.** Vyerna märker dem synligt. Ett
 *    tal utan ursprung är exakt den sortens siffra fotnoten varnar för.
 * 3. **Talen är deterministiska**, härledda ur tenantens id. En server-
 *    komponent med `force-dynamic` renderas om vid varje anrop, och slumpade
 *    tal hade betytt att samma kund hade ny volym varje gång sidan laddades —
 *    ett gränssnitt som inte går att lita på ens som attrapp.
 *
 * Stäng av allt med `NEXT_PUBLIC_ADMIN_EXEMPELDATA=av`.
 */

/** Raden som vyerna får: tenantraden plus en flagga om talen är påhittade. */
export type BerikadTenant = TenantRow & { ar_exempel: boolean };

/**
 * FNV-1a över tenantens id. En hash och inte `Math.random()`: samma kund ska
 * ha samma tal i dag som i går, annars är siffran inte ens en attrapp utan
 * brus. Trettiotvå bitar räcker gott — vi fördelar tal i småintervall, inte
 * kryptonycklar.
 */
function fro(id: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < id.length; i += 1) {
    h ^= id.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/** Plockar ett tal i [min, max] ur fröet. `steg` skiljer fälten åt. */
function tal(id: string, steg: number, min: number, max: number): number {
  const h = fro(`${id}#${steg}`);
  return min + (h % (max - min + 1));
}

/**
 * Profilerna som exempelraderna dras ur.
 *
 * ## Varför ingen profil är röd, och varför det INTE är en lucka
 *
 * Första utkastet hade en "ansträngd" profil som skulle ge låg marginal. Den
 * gick inte att fylla, och den gick inte att fylla ens efter att kostnaden
 * höjts till Googles riktiga listpris (7,14 kr in / 35,71 kr ut per miljon,
 * se `halsa.ts`): ett paket på 6 990 kr tål ungefär 39 miljoner utgående
 * tokens innan marginalen ens blir gul. Det talet finns inte i verkligheten
 * för en supportagent med några hundra ärenden.
 *
 * Slutsatsen är ett påstående om affären, inte om koden: vid realistiska
 * volymer är marginalen strukturellt ~99 % för varje kund, och den signal som
 * FAKTISKT varierar är om kunden använder tjänsten. Därför varierar profilerna
 * volym, fel och senaste aktivitet — och några av dem är tysta, vilket är det
 * utfall hälsologiken finns för att fånga.
 *
 * Att i stället hitta på hundra miljoner tokens för att få en röd rad hade
 * demonstrerat gränssnittet genom att ljuga om ekonomin.
 *
 * ## Produkterna
 *
 * `produkt` styr om raden får ärenden, körningar eller båda. Utan den blev
 * varje exempelrad Snajp Duo — Portfoljvy härleder paketet ur aktivitet, och
 * en kolumn där tolv rader visar samma paket ser ut som en bugg.
 */
const PROFILER = [
  /** Frisk och stadig. Den vanligaste kunden, och den tråkigaste. */
  {
    vikt: 5,
    produkt: "bada",
    arendeSpann: [40, 180],
    korSpann: [12, 60],
    tokenPerEnhet: 2600,
    felSpann: [0, 1],
    dagarSedan: [0, 3]
  },
  /** Tung användare: hög volym, synlig kostnad, några fel. */
  {
    vikt: 3,
    produkt: "bada",
    arendeSpann: [150, 420],
    korSpann: [40, 140],
    tokenPerEnhet: 9000,
    felSpann: [1, 6],
    dagarSedan: [0, 5]
  },
  /** Bara kundtjänst. Ger Snajp Support i paketkolumnen. */
  {
    vikt: 3,
    produkt: "support",
    arendeSpann: [60, 260],
    korSpann: [0, 0],
    tokenPerEnhet: 3800,
    felSpann: [0, 3],
    dagarSedan: [0, 6]
  },
  /** Bara leads. Ger Snajp Leads. */
  {
    vikt: 2,
    produkt: "leads",
    arendeSpann: [0, 0],
    korSpann: [18, 90],
    tokenPerEnhet: 5200,
    felSpann: [0, 2],
    dagarSedan: [0, 7]
  },
  /**
   * Slocknande: volymen finns i historiken men inget har hänt på veckor.
   * Den här profilen är hela skälet till att portföljvyn sorterar som den gör
   * — utan den visar "Kräver åtgärd" alltid noll, och sorteringen "sämst
   * först" går inte att se att den fungerar.
   */
  {
    vikt: 2,
    produkt: "bada",
    arendeSpann: [20, 90],
    korSpann: [5, 25],
    tokenPerEnhet: 4000,
    felSpann: [0, 3],
    dagarSedan: [17, 44]
  },
  /** Nystartad: liten volym, aktiv nyligen. */
  {
    vikt: 2,
    produkt: "bada",
    arendeSpann: [4, 20],
    korSpann: [1, 8],
    tokenPerEnhet: 3000,
    felSpann: [0, 1],
    dagarSedan: [1, 9]
  }
] as const;

function profilFor(id: string) {
  // Viktad dragning: de flesta kunder ska se normala ut. Hade profilerna varit
  // likafördelade hade en portfölj på tolv rader sett ut som en kris.
  const total = PROFILER.reduce((s, p) => s + p.vikt, 0);
  let n = tal(id, 99, 0, total - 1);
  for (const p of PROFILER) {
    if (n < p.vikt) return p;
    n -= p.vikt;
  }
  return PROFILER[0];
}

/**
 * Är raden tom? Alla mätvärden på noll OCH ingen aktivitetstidpunkt.
 *
 * `last_activity` räknas med av en anledning: en kund kan ha haft trafik i ett
 * fönster som statistiken inte längre täcker, och då är nollan ett mätvärde —
 * inte ett tomrum vi får fylla.
 */
export function arTom(rad: TenantRow): boolean {
  return (
    (rad.tickets ?? 0) === 0 &&
    (rad.runs ?? 0) === 0 &&
    (rad.test_runs ?? 0) === 0 &&
    (rad.errors ?? 0) === 0 &&
    (rad.tokens_in ?? 0) === 0 &&
    (rad.tokens_out ?? 0) === 0 &&
    !rad.last_activity
  );
}

/** Är exempeldata påslaget? Av med `NEXT_PUBLIC_ADMIN_EXEMPELDATA=av`. */
export function exempeldataPa(): boolean {
  return process.env.NEXT_PUBLIC_ADMIN_EXEMPELDATA !== "av";
}

function isoDagarSedan(dagar: number, nu: Date): string {
  const d = new Date(nu.getTime() - dagar * 86_400_000);
  // Klockslaget härleds inte ur `nu`, utan sätts fast: annars ändras
  // tidsstämpeln varje gång sidan renderas om, och "senast aktiv" hade tickat
  // sekundvis på en rad som inte har någon aktivitet alls.
  d.setUTCHours(9, 24, 0, 0);
  return d.toISOString();
}

/**
 * Hur många veckor bakåt kurvan i Kundstatistik täcker. Måste vara samma tal
 * som `beraknaKundstatistik(..., antalVeckor)` — spreds exempelraderna över
 * ett bredare fönster än grafen ritar hamnar de äldsta utanför bilden och
 * kurvan ser gles ut igen, fast av motsatt skäl.
 */
export const SPRIDNING_VECKOR = 12;

/**
 * Registreringsdatum för en exempelrad — påhittat, och det är en ändring värd
 * att förstå.
 *
 * ## Varför det INTE var påhittat förut
 *
 * `kund_sedan` är riktig data: registrets datum om det finns, annars
 * arbetsytans skapelsedatum. Berikningen lämnade det därför orört, och bara
 * avtalsdatumet hittades på. Följden var att kurvan klumpade ihop sig i tre
 * veckor — testarbetsytorna skapades allihop mellan 16 och 23 augusti, så det
 * var när de "blev kunder".
 *
 * ## Varför det är påhittat nu
 *
 * En kurva som visar tre staplar och nio tomma veckor säger ingenting om hur
 * vyn ser ut när den används. Spridningen är alltså medveten, och priset är
 * att kolumnen "Kund sedan" för en exempelrad inte längre är arbetsytans
 * verkliga skapelsedatum. Raden bär `Exempel`, och fotnoten under grafen säger
 * numera rakt ut att BÅDA datumen är påhittade — den sade tidigare att
 * registreringsdatumen var verkliga, vilket de inte längre är.
 *
 * `plats` är radens plats i den jämna spridningen, inte en hash: nio rader
 * fördelade med hashning lämnar hål och dubbletter, och "sprid över tolv
 * veckor" blev då sju veckor med tur. Se `berikaAlla`.
 */
function registreringsdatum(id: string, plats: number, nu: Date): string {
  // Måndag i den tilldelade veckan, plus 0-4 dagar: en kund registreras på en
  // vardag. Utan det landade varje stapel på exakt samma veckodag, vilket syns
  // i tabellen som en kolumn av måndagar.
  const dagar = plats * 7 + tal(id, 11, 0, 4);
  return isoDagarSedan(Math.max(0, dagar), nu);
}

/**
 * Avtalsdatum, härlett ur när arbetsytan blev kund.
 *
 * FÖRSTA VERSIONEN DROG ETT FRITT DATUM 30–260 DAGAR TILLBAKA, och resultatet
 * var rader som "kund sedan 2026-08-23, avtal signerat 2025-12-25" — ett avtal
 * undertecknat åtta månader innan kunden fanns, ett av dem på juldagen. Ingen
 * läser förbi det. Ett påhittat tal får vara ungefärligt, men det får inte
 * bryta mot ordningen mellan två fält som står bredvid varandra i samma rad.
 *
 * Avtalet signeras därför 0–21 dagar EFTER `kund_sedan`, och aldrig i
 * framtiden. Saknas `kund_sedan` finns ingen ordning att bevara, och då duger
 * ett datum bakåt i tiden.
 */
function avtalsdatum(id: string, kundSedan: string | null | undefined, nu: Date): string {
  const start = kundSedan ? new Date(`${kundSedan.slice(0, 10)}T00:00:00Z`) : null;
  if (!start || Number.isNaN(start.getTime())) {
    return isoDagarSedan(tal(id, 8, 30, 260), nu);
  }

  // FONSTRET kapas, inte datumet. Att dra 0-21 dagar och sedan klippa allt
  // som hamnade efter i dag gav fem rader med exakt dagens datum - kunderna
  // registrerades for under tre veckor sedan, sa de flesta dragningar landade
  // i framtiden och klipptes till samma dag. En kolumn dar halva listan visar
  // i dag laser som en bugg, inte som avtal.
  const dagarKvar = Math.floor((nu.getTime() - start.getTime()) / 86_400_000);
  if (dagarKvar <= 0) return isoDagarSedan(0, nu);

  const forskjutning = tal(id, 8, 0, Math.min(21, dagarKvar));
  const d = new Date(start.getTime() + forskjutning * 86_400_000);
  d.setUTCHours(9, 24, 0, 0);
  return d.toISOString();
}

/**
 * Berikar en tenantrad med exempeltal om — och bara om — den är helt tom.
 * `nu` skickas in i stället för att läsas här, så att funktionen går att testa.
 */
export function berika(rad: TenantRow, nu: Date, plats = 0): BerikadTenant {
  if (!arTom(rad)) return { ...rad, ar_exempel: false };

  const id = rad.id;
  const profil = profilFor(id);

  const arenden = tal(id, 1, profil.arendeSpann[0], profil.arendeSpann[1]);
  const korningar = tal(id, 2, profil.korSpann[0], profil.korSpann[1]);
  const provkorningar = korningar > 0 ? tal(id, 3, 0, 6) : 0;
  const fel = tal(id, 4, profil.felSpann[0], profil.felSpann[1]);
  const kundSedan = registreringsdatum(id, plats, nu);
  const dagarSomKund = Math.floor(
    (nu.getTime() - new Date(kundSedan).getTime()) / 86_400_000
  );

  // Senaste aktivitet kan aldrig ligga FÖRE registreringen. Utan taket fick en
  // kund som registrerades i veckan en profil med 44 dagars tystnad, alltså
  // aktivitet en månad innan arbetsytan fanns — ett tal som motsäger raden
  // bredvid sig.
  const dagar = Math.min(
    tal(id, 5, profil.dagarSedan[0], profil.dagarSedan[1]),
    Math.max(0, dagarSomKund)
  );

  // Tokens skalar med volymen, med en spridning på ±20 %. Ett fast tal per
  // ärende hade gett en marginal som var exakt densamma för varje kund i
  // samma profil — och en kolumn där alla rader visar samma procent läser som
  // en bugg, inte som data.
  const enheter = arenden + korningar * 3;
  const spridning = 0.8 + tal(id, 6, 0, 40) / 100;
  const tokens = Math.round(enheter * profil.tokenPerEnhet * spridning);
  const tokensIn = Math.round(tokens * 0.62);

  // Eskalerade ärenden: en liten andel av ärendena, alltid minst noll och
  // aldrig fler än ärendena själva — ett tal som överstiger sin egen grundmängd
  // syns direkt som påhittat.
  const eskalerade = Math.min(arenden, Math.round((arenden * tal(id, 7, 2, 11)) / 100));

  return {
    ...rad,
    tickets: arenden,
    escalated: eskalerade,
    runs: korningar,
    test_runs: provkorningar,
    tokens_in: tokensIn,
    tokens_out: tokens - tokensIn,
    errors: fel,
    last_activity: isoDagarSedan(dagar, nu),
    // Registreringsdatumet SKRIVS ÖVER för exempelrader — se
    // `registreringsdatum` för varför, och vad det kostar.
    kund_sedan: kundSedan,
    // Avtalet räknas ur det påhittade registreringsdatumet, inte ur radens
    // ursprungliga. Annars hade ordningen brutits igen: ett avtal från augusti
    // på en kund som enligt kurvan blev kund i juni.
    avtal_signerat: avtalsdatum(id, kundSedan, nu),
    ar_exempel: true
  };
}

/**
 * Berikar hela listan. Returnerar raderna oförändrade när exempeldata är
 * avstängt — då bär ingen rad flaggan, och vyerna visar inga märkningar.
 */
export function berikaAlla(rader: readonly TenantRow[], nu: Date): BerikadTenant[] {
  if (!exempeldataPa()) return rader.map((rad) => ({ ...rad, ar_exempel: false }));

  // Platserna delas ut JÄMNT över fönstret, inte hashat. Nio rader som var för
  // sig drar ett veckonummer ur sitt id ger hål och dubbletter — med tur sju
  // veckor av tolv, vilket är precis det glesa utfall spridningen finns för att
  // undvika. Här får rad i plats round(i * (V-1) / (n-1)), alltså både första
  // och sista veckan besatta.
  //
  // Sorteringen sker på id-hashen och inte på listans ordning: backendens
  // ordning är inte garanterad, och en rad som byter plats i svaret skulle
  // annars byta registreringsdatum mellan två laddningar.
  const tomma = rader.filter(arTom).sort((a, b) => fro(a.id) - fro(b.id));
  const platser = new Map<string, number>();
  tomma.forEach((rad, i) => {
    const plats =
      tomma.length === 1
        ? 0
        : Math.round((i * (SPRIDNING_VECKOR - 1)) / (tomma.length - 1));
    platser.set(rad.id, plats);
  });

  return rader.map((rad) => berika(rad, nu, platser.get(rad.id) ?? 0));
}

/** Hur många rader i listan som visar exempeltal. Vyerna fotnotar på det här. */
export function antalExempel(rader: readonly BerikadTenant[]): number {
  return rader.filter((r) => r.ar_exempel).length;
}
