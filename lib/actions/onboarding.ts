"use server";

import type { BusinessContextInsert } from "@/lib/database.types";
import { redirect } from "next/navigation";
import { formateraOrgnr, orgnrFel } from "@/lib/orgnr";

/**
 * Bolagsfälten är fyra, inte åtta — de gamla åtta var förifyllda med påhittade
 * värden som gick att skicka in rakt av (se OnboardingWizard, som ärvde
 * lärdomen). Sedan 2026-09-20 bär flödet dessutom bransch, kontaktperson och
 * paketval, och sedan 2026-09-30 leadsagentens målgrupp — i fem steg, se
 * components/auth/OnboardingWizard.tsx.
 */
export type OnboardingInput = {
  /**
   * Företagets namn. Blir arbetsytans namn och därmed kundens namn i
   * backenden, som står i sidfoten på varje utskick. Utan fältet hette
   * arbetsytan "<kontots namn> workspace" (signup-triggern), och det var det
   * namnet mottagarna fick se (uppmätt 2026-11-18).
   */
  foretag: string;
  orgnr: string;
  webbplats: string;
  produkt: string;
  /**
   * "Särskilt fokus" ur målgruppssteget. Fri text till produkttexten, som
   * Iris-profilen tolkar — det strukturerade i `malgrupp` vinner alltid över
   * tolkningen.
   */
  fokus: string;
  /**
   * Erbjudandena utskicken ska bygga på (Anton 2026-10-25), fri text med ett
   * erbjudande per stycke. Valfritt.
   */
  erbjudanden?: string;
  /**
   * Målgruppssteget — leads-agentens grundfilter, som råa fältvärden
   * (kommaseparerade listor, tal som text). Tolkas här, på serversidan, och
   * skrivs som ICP av lib/snajp/standard.ts — bara om ICP:n är tom, så en
   * omkörning aldrig skriver över kundens egna val.
   */
  malgrupp?: {
    branscher: string;
    orter: string;
    undvik: string;
    roller: string;
    anstalldaMin: string;
    anstalldaMax: string;
  };
  /**
   * Kundens EGEN bransch, ur listan i lib/bransch.ts. Skrivs som en rad i
   * produkttexten (agenternas kontext och ordförråd) — ALDRIG i
   * `industries`, som är leads-agentens målgruppsfilter. Se lib/bransch.ts.
   */
  bransch: string;
  /**
   * Kontaktpersonen hos kunden — den vi hör av oss till. Landar i
   * kundregistret (ss_customer_contacts) via lib/snajp/kundregister.ts och
   * som en rad i produkttexten, så uppgiften överlever även om
   * CRM-skrivningen fallerar.
   */
  kontaktNamn: string;
  kontaktRoll?: string;
  kontaktMejl: string;
  kontaktTelefon?: string;
  /**
   * Paketet kunden valde i onboardingen. Sätter `workspaces.products` via
   * samma RPC som paketbytet i inställningarna (set_workspace_products,
   * migration 044) — paketet ÄR entitlementen. Utelämnat = defaulten
   * (leads + support) står kvar.
   */
  paket?: string;
  /**
   * Testarbetsyta: organisationsnumret hoppas över.
   *
   * Det finns inget riktigt bolag bakom en testkund, och att kräva ett giltigt
   * nummer betyder i praktiken att någon klistrar in NÅGON ANNANS — vilket är
   * sämre än att markera arbetsytan för vad den är.
   *
   * Markeringen skrivs in i produkttexten, inte bara i ett flaggfält, så att
   * den syns för den som läser affärskontexten i adminvyn. En testkund som ser
   * ut som en riktig kund i portföljen är exakt den sortens siffra som fattar
   * beslut åt en.
   */
  testkund?: boolean;
  /**
   * Svaret på notisrutan i formuläret.
   *
   * Valfri med flit: den som saknas betyder "ingen fråga ställdes", och då
   * gäller standarden i migration 043 — notiser PÅ. Ett `false` här är alltså
   * ett aktivt NEJ och inget annat, vilket är precis den skillnad ett samtycke
   * måste kunna bära.
   */
  notiser?: boolean;
  /**
   * Villkorskryssrutan i sista steget: användarvillkoren och informationen om
   * distansavtalslagen och ångerrätt (/villkor och /angerratt). Krävs för ALLA
   * — även testarbetsytor använder tjänsten. Tidpunkten sätts på serversidan
   * och skrivs in i affärskontexten som beviskedja; en boolean från klienten
   * duger som svar men inte som klockslag.
   */
  villkorGodkanda?: boolean;
  /**
   * Faktureringsadressen — dit fakturan går efter gratisperioden. Krävs för
   * riktiga kunder; null för testarbetsytor, som inte har något bolag att
   * fakturera. Landar i kundregistrets fält `faktureringsadress`
   * (Admin → Kunder → Data), samma fält som adminvyn redigerar.
   */
  faktureringsadress?: { gata: string; postnummer: string; ort: string } | null;
};

export type OnboardingActionResult = {
  success: boolean;
  error?: string;
};

/**
 * Webbadressen normaliseras men VALIDERAS INTE hårt. En kund som skriver
 * "exempel.se" utan protokoll menar https://exempel.se, och att neka den
 * inmatningen hade stoppat onboardingen på en formalitet. Att adressen
 * faktiskt svarar upptäcks när agenten försöker läsa den, och det felet är
 * begripligt på ett sätt som "ogiltig URL" inte är.
 */
function normaliseraWebbplats(rå: string): string {
  const text = (rå ?? "").trim();
  if (!text) return "";
  return /^https?:\/\//i.test(text) ? text : `https://${text}`;
}

/**
 * En adress som går att slå upp: en punkt i värdnamnet och inga mellanslag.
 * Mer än så prövas inte här. Att sajten svarar visar sig när agenten läser den.
 */
function arWebbadress(adress: string): boolean {
  try {
    const { hostname } = new URL(adress);
    return hostname.includes(".") && !hostname.endsWith(".");
  } catch {
    return false;
  }
}

/** "41101" och "411 01" → "411 01". Allt annat → null. */
function postnummer(rå: string): string | null {
  const siffror = (rå ?? "").replace(/\s/g, "");
  return /^\d{5}$/.test(siffror) ? `${siffror.slice(0, 3)} ${siffror.slice(3)}` : null;
}

const EPOST = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** "Göteborg, Mölndal" → ["Göteborg", "Mölndal"]. Taket är backendens (25). */
function kommalista(rå: string | undefined): string[] {
  return (rå ?? "")
    .split(",")
    .map((del) => del.trim())
    .filter(Boolean)
    .slice(0, 25);
}

/** Tomt eller icke-tal = inget värde, alltså ingen gräns åt det hållet. */
function heltal(rå: string | undefined): number | null {
  const text = (rå ?? "").replace(/\s/g, "");
  return /^\d+$/.test(text) ? Number(text) : null;
}

export async function saveBusinessContext(input: OnboardingInput): Promise<OnboardingActionResult> {
  const { auth } = await import("@/lib/auth");
  const session = await auth();
  const user = session?.user;

  if (!user?.id) {
    return { success: false, error: "Du måste vara inloggad." };
  }

  const { getProfileForUser } = await import("@/lib/workspace");
  const { sqlAsUser } = await import("@/lib/db");
  const { skapaTesttenant } = await import("@/lib/snajp/testtenant");
  let profile = await getProfileForUser(user.id);

  // Läsrollen: en inbjuden läsare landar i en FÄRDIG arbetsyta och ska aldrig
  // skriva om dess affärskontext, hur onboardingflödet än nås.
  {
    const { LASROLL, LASROLL_FEL } = await import("@/lib/auth/lasroll");
    if ((profile?.role ?? "") === LASROLL) {
      return { success: false, error: LASROLL_FEL };
    }
  }

  if (!profile) {
    // "Försök logga in igen" var en återvändsgränd: en ny inloggning gav aldrig
    // en profilrad, eftersom bara signup-triggern kunde skapa den. Läk istället.
    try {
      await sqlAsUser(user.id, "select public.ensure_workspace_for_current_user()");
    } catch (repairError) {
      return {
        success: false,
        error: `Ditt konto saknar en arbetsyta och kunde inte repareras: ${(repairError as Error).message}`
      };
    }
    profile = await getProfileForUser(user.id);
  }

  if (!profile) {
    return { success: false, error: "Ditt konto saknar en arbetsyta. Kontakta support." };
  }

  // Serversidan validerar OM. lib/orgnr.ts kör samma kontroll i webbläsaren,
  // men klientkod går att kringgå och det som skyddar är alltid den här sidan.
  // Serversidan validerar OM — men inte för en testarbetsyta. Kontrollen
  // hoppas över på BÅDA sidor, annars vore klientens kryssruta verkningslös och
  // felet hade dykt upp först vid inskickning.
  const orgnrProblem = input.testkund ? null : orgnrFel(input.orgnr);
  if (orgnrProblem) {
    return { success: false, error: orgnrProblem };
  }

  const foretag = (input.foretag ?? "").replace(/\s+/g, " ").trim();
  if (foretag.length < 2 || foretag.length > 80) {
    return { success: false, error: "Fyll i företagets namn." };
  }

  const webbplats = normaliseraWebbplats(input.webbplats);
  if (!webbplats) {
    return {
      success: false,
      error: "Fyll i webbplatsen. Det är den agenterna läser för att förstå er."
    };
  }
  if (!arWebbadress(webbplats)) {
    return {
      success: false,
      error: "Webbadressen går inte att läsa. Skriv den som exempel.se."
    };
  }

  const produkt = input.produkt.trim();
  if (!produkt) {
    return {
      success: false,
      error: "Skriv en rad om vad ni säljer. Det är det agenterna ska sälja."
    };
  }

  const fokus = input.fokus.trim();
  // Ett erbjudande per stycke (tom rad emellan), högst fem, som i Leads › Erbjudanden.
  const erbjudanden = (input.erbjudanden ?? "")
    .split(/\n\s*\n/)
    .map((stycke) => stycke.replace(/\s+/g, " ").trim().slice(0, 600))
    .filter(Boolean)
    .slice(0, 5);

  // Målgruppen tolkas här och inte i klienten — det är den här sidan som
  // skyddar. Ett spann där min > max hade fällts av backendens validate_icp
  // (422) och hela ICP:n hade tyst uteblivit, så det stoppas med ett besked.
  const malgrupp = input.malgrupp
    ? {
        branscher: kommalista(input.malgrupp.branscher),
        orter: kommalista(input.malgrupp.orter),
        undvik: kommalista(input.malgrupp.undvik),
        roller: kommalista(input.malgrupp.roller),
        anstalldaMin: heltal(input.malgrupp.anstalldaMin),
        anstalldaMax: heltal(input.malgrupp.anstalldaMax)
      }
    : undefined;
  if (
    malgrupp?.anstalldaMin != null &&
    malgrupp.anstalldaMax != null &&
    malgrupp.anstalldaMin > malgrupp.anstalldaMax
  ) {
    return { success: false, error: "Minsta antal anställda är större än största." };
  }

  const { arBransch } = await import("@/lib/bransch");
  if (!arBransch(input.bransch)) {
    return { success: false, error: "Välj er bransch i listan." };
  }

  const kontaktNamn = input.kontaktNamn.trim();
  const kontaktMejl = input.kontaktMejl.trim().toLowerCase();
  if (!kontaktNamn) {
    return { success: false, error: "Fyll i vem som är kontaktperson hos er." };
  }
  if (!EPOST.test(kontaktMejl)) {
    return { success: false, error: "Fyll i kontaktpersonens e-postadress." };
  }
  const kontaktRoll = (input.kontaktRoll ?? "").trim();
  const kontaktTelefon = (input.kontaktTelefon ?? "").trim();

  // Villkoren måste vara godkända — kryssrutan finns i klienten, men det som
  // skyddar är alltid den här sidan. Utan godkännande finns inget avtal att
  // starta en gratisperiod på.
  if (!input.villkorGodkanda) {
    return {
      success: false,
      error: "Kryssa i att ni godkänner villkoren för att kunna starta gratisperioden."
    };
  }

  // Faktureringsadressen: krävs för riktiga kunder, hoppas över för
  // testarbetsytor av samma skäl som organisationsnumret — ett obligatoriskt
  // fält utan riktigt bolag bakom fylls med påhitt.
  const faktGata = (input.faktureringsadress?.gata ?? "").trim();
  const faktPostnrRa = (input.faktureringsadress?.postnummer ?? "").trim();
  const faktPostnr = postnummer(faktPostnrRa);
  const faktOrt = (input.faktureringsadress?.ort ?? "").trim();
  if (!input.testkund && (!faktGata || !faktPostnrRa || !faktOrt)) {
    return {
      success: false,
      error: "Fyll i faktureringsadressen. Dit går fakturan efter gratisperioden."
    };
  }
  // "abc" gick igenom som postnummer till 2026-11-18 och hamnade på fakturan.
  if (!input.testkund && !faktPostnr) {
    return { success: false, error: "Postnumret ska ha fem siffror." };
  }
  const faktureringsadress =
    faktGata && faktPostnr && faktOrt ? `${faktGata}, ${faktPostnr} ${faktOrt}` : null;

  const { arPaketId } = await import("@/lib/pricing");
  const paket = input.paket && arPaketId(input.paket) ? input.paket : null;
  if (input.paket && !paket) {
    return { success: false, error: `Okänt paket: ${input.paket}.` };
  }

  // De gamla kolumnerna är not null i schemat och kan inte lämnas tomma. De
  // fylls därför med det agenten VET, inte med gissningar: målgrupp, branscher,
  // geografi och tonläge härleds ur webbplatsen i researchsteget, och att
  // skriva in en gissning här hade gjort gissningen till ett faktum som
  // grundningsgrinden sedan låter agenten citera.
  const AVVAKTAR = "(läses in från webbplatsen)";

  const payload: BusinessContextInsert = {
    workspace_id: profile.workspace_id,
    product: [
      // "Vårt", som branschraden nedan: säljarens namn, inte ett målfilter.
      `Vårt företag: ${foretag}`,
      input.testkund
        ? "Organisationsnummer: — (TESTARBETSYTA, inget riktigt bolag)"
        : `Organisationsnummer: ${formateraOrgnr(input.orgnr)}`,
      `Webbplats: ${webbplats}`,
      // SÄLJARENS bransch, inte målgruppens — med bara "Bransch:" läste
      // Iris-profilen raden som ett målfilter.
      `Vår egen bransch: ${input.bransch}`,
      `Vad vi säljer: ${produkt}`,
      fokus ? `Särskilt fokus: ${fokus}` : null,
      // Står här också: affärskontexten tappas aldrig, även om erbjudande-
      // inställningarna inte hann skrivas (testarbetsytor får dem inte alls).
      ...erbjudanden.map((e, i) => `Vårt erbjudande i utskicken${erbjudanden.length > 1 ? ` ${i + 1}` : ""}: ${e}`),
      // Kontaktpersonen står i texten OCKSÅ när CRM-skrivningen lyckas:
      // affärskontexten är det lager som aldrig tappas bort, och admin-
      // fliken Kunder & Data härleder redan andra fält härifrån.
      `Kontaktperson: ${kontaktNamn}${kontaktRoll ? ` (${kontaktRoll})` : ""} — ${kontaktMejl}${
        kontaktTelefon ? `, ${kontaktTelefon}` : ""
      }`,
      faktureringsadress ? `Faktureringsadress: ${faktureringsadress}` : null,
      // Villkorsgodkännandet med serverns klockslag — beviskedjan för att
      // avtalet ingicks, i det lager som aldrig tappas bort.
      `Villkoren godkända vid registreringen: ${new Date().toISOString().slice(0, 10)} (användarvillkoren samt informationen om distansavtalslagen och ångerrätt)`
    ]
      .filter(Boolean)
      .join("\n"),
    target_audience: AVVAKTAR,
    industries: [],
    geography: [],
    tone: AVVAKTAR,
    offer: produkt,
    cta: AVVAKTAR,
    contact_roles: [],
    updated_at: new Date().toISOString()
  };

  // En upsert i stället för läs-sen-skriv: unika index på workspace_id gör
  // villkoret till databasens jobb, och två samtidiga sparningar kan inte
  // längre skapa två rader.
  try {
    // EN skrivväg mot raden, delad med /settings/affarskontext. Innan den
    // delades ägde den här filen satsen ensam och inställningssidan skrev
    // inte alls — två vyer mot samma rad där bara den ena kunde spara.
    const { sparaBusinessContext } = await import("@/lib/data/business-context");
    await sparaBusinessContext(user.id, payload);
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }

  /**
   * Arbetsytan får företagets namn, FÖRE tenanten skapas nedan: backendens
   * kundnamn tas ur arbetsytans namn (lib/snajp/provisionering.ts) och står i
   * sidfoten på varje utskick.
   *
   * Genom en RPC (migration 120), som paketbytet nedan: `workspaces` har
   * radskydd utan uppdateringsregel, så en vanlig UPDATE träffar noll rader
   * utan att fela. Fäller inte onboardingen: saknas funktionen i en miljö där
   * migrationen inte hunnit köras står signup-namnet kvar, och felet loggas.
   */
  try {
    await sqlAsUser(user.id, "select public.set_workspace_name($1)", [foretag]);
  } catch (error) {
    console.error("[onboarding] kunde inte sätta arbetsytans namn:", error);
  }

  /**
   * Paketvalet — samma RPC som paketbytet i inställningarna (migration 044),
   * så onboardingen kan aldrig sätta något inställningssidan inte kan.
   *
   * Fäller inte onboardingen: defaulten (leads + support) är ett fungerande
   * läge, och kunden kan byta paket under Inställningar → Plan. Ett fel här
   * loggas i stället för att kasta bort ett sparat bolag.
   */
  if (paket) {
    try {
      const { PRODUKTER_FOR_PAKET } = await import("@/lib/pricing");
      await sqlAsUser(user.id, "select public.set_workspace_products($1::text[])", [
        PRODUKTER_FOR_PAKET[paket]
      ]);
    } catch (error) {
      console.error("[onboarding] kunde inte sätta paketet:", error);
    }
  }

  /**
   * Notissvaret skrivs EFTER affärskontexten och fäller aldrig onboardingen.
   *
   * Samma regel som kontextdokumentet i actions/affarskontext.ts: ett
   * misslyckat sidospår får inte kasta bort ett lyckat huvudspår. Kunden har
   * fyllt i sitt bolag; att skicka tillbaka dem till formuläret för att en
   * notisrad inte gick att skriva vore att straffa dem för fel sak.
   *
   * Att ett JA kan falla bort är ofarligt — utan rad gäller standarden, som är
   * på. Ett NEJ som faller bort betyder däremot mejl till någon som sagt nej,
   * och därför loggas felet uttryckligen i stället för att sväljas tyst.
   */
  if (typeof input.notiser === "boolean") {
    try {
      const { sparaNotissvarViaOnboarding } = await import("@/lib/actions/notiser");
      const svar = await sparaNotissvarViaOnboarding(input.notiser);
      if (!svar.success) {
        console.error("[onboarding] kunde inte spara notissvaret:", svar.error);
      }
    } catch (error) {
      console.error("[onboarding] kunde inte spara notissvaret:", error);
    }
  }

  /**
   * Testarbetsytan får en EGEN backend-tenant (migration 040).
   *
   * Den delade `testkund`-tenanten finns kvar som fallback och beskrivs nedan.
   * Skälet att den inte längre är förstahandsvalet: delad tenant = delad
   * kunskapsbas, och en testkunds villkor kunde grunda ett svar till en annan
   * testkunds kund.
   *
   * Utan det här är bypassen halvfärdig. Uppmätt mot dev-deployen 2026-08-19:
   * den nyskapade testkunden mötte 409 på Kontroll, Kundtjänst och Röst,
   * eftersom `requireSnajpTenant()` härleder kunden ur `workspaces.slug` och
   * den var null. En testkund som inte kan använda produkten testar ingenting.
   *
   * Bara för testarbetsytor. En RIKTIG kund kopplas av
   * `scripts/onboard_tenant.py` till en EGEN tenant — en delad tenant betyder
   * delad inkorg och delad kunskapsbas, vilket är rätt för ett test och
   * oacceptabelt för en kund.
   *
   * Villkorad på att slug är tom: en workspace som redan pekar på en kund rörs
   * aldrig härifrån, hur rutan än kryssas.
   */
  /** Arbetsytans nyckel när den kopplades just nu. Webbplatsskanningen startas med den. */
  let tenantNyckel: string | null = null;
  if (input.testkund) {
    try {
      // EGEN tenant per testarbetsyta, skapad i drift.
      //
      // Den delade `testkund`-tenanten (migration 038) betydde delad inkorg,
      // delad kunskapsbas och delat röstdokument. Med flera testkunder växte
      // basen med policys från olika bolag, och ett svar till kund A kunde
      // grundas i kund B:s villkor — grundningsgrinden ser en träff, den kan
      // inte se att artikeln kom från fel företag.
      //
      // Backenden skapar tenanten (`POST /api/keys`), och nyckeln sparas i
      // `workspace_tenant_keys` genom en security definer-funktion. Migration
      // 040 förklarar varför den inte får ligga i `workspaces`.
      const tenant = await skapaTesttenant(payload.workspace_id, `Testarbetsyta ${webbplats}`);
      const kopplad = await sqlAsUser<{ ok: boolean }>(
        user.id,
        "select public.link_test_tenant($1, $2, $3) as ok",
        [tenant.slug, tenant.tenantId, tenant.apiKey]
      );
      if (!kopplad[0]?.ok) {
        throw new Error("link_test_tenant nekade kopplingen (arbetsytan hade redan en kund?).");
      }
      tenantNyckel = tenant.apiKey;
    } catch (error) {
      // Kopplingen får inte fälla onboardingen. Affärskontexten är sparad, och
      // en okopplad testyta ger ett ärligt 409 med instruktion — att slänga
      // bort ett lyckat sparande för det vore sämre.
      //
      // Fallbacken är den GAMLA delade tenanten. Den är sämre (delad
      // kunskapsbas) men fungerande, och alternativet — en arbetsyta som inte
      // kan användas alls — är sämre än så. Att den användes syns på att
      // workspacets slug är `testkund` utan suffix.
      console.error("[onboarding] kunde inte skapa egen testtenant:", error);
      try {
        await sqlAsUser(user.id, "select public.link_testkund_workspace()");
      } catch (fallbackError) {
        console.error("[onboarding] kunde inte koppla testarbetsytan:", fallbackError);
      }
    }
  } else {
    /**
     * RIKTIGA kunder får också sin tenant här, sedan migration 061.
     *
     * Tidigare gjorde de inte det: en vanlig registrering lämnade
     * `workspaces.slug` som null, och `requireSnajpTenant()` svarade 409 på
     * varje inloggad yta tills någon av oss körde `scripts/onboard_tenant.py`
     * för hand. Produkten var alltså oanvändbar för varje ny kund fram till
     * nästa gång vi tittade — översikten visade streck, röstdokumentet
     * "Kunde inte hämta", och målgruppssidan ett meddelande om databaskolumner.
     *
     * Samtidigt blir det kunden just skrev till STANDARDINSTÄLLNINGAR i
     * backenden: produktbeskrivningen är den agenten faktiskt läser
     * (`context_docs` med kind `product_marketing`, inte `business_contexts`),
     * och röstdokument och målgrupp får ett utkast att ändra i stället för ett
     * tomt fält. Se lib/snajp/standard.ts för vad som fylls i och vad som med
     * flit lämnas tomt.
     *
     * Fäller inte onboardingen. Affärskontexten är sparad, och
     * `requireSnajpTenant()` gör om samma koppling vid första sidladdningen om
     * backenden sov just nu.
     */
    try {
      const { sakerstallKundtenant } = await import("@/lib/snajp/provisionering");
      const { getWorkspaceForUser } = await import("@/lib/workspace");
      const workspace = await getWorkspaceForUser(user.id);
      if (workspace && !workspace.slug) {
        // Samma fyra fält som `Kundunderlag` — payloaden ovan är redan den
        // text kunden skrev, så en omläsning ur databasen hade bara varit en
        // extra tur och retur för samma sak.
        const kopplad = await sakerstallKundtenant(
          user.id,
          workspace,
          {
            product: payload.product,
            target_audience: payload.target_audience,
            offer: payload.offer,
            cta: payload.cta
          },
          // Tålmodigt: uppstarten får vänta ut en kallstartande backend. Det är
          // enda tillfället kunden faktiskt väntar på att bli upplagd.
          true,
          malgrupp,
          erbjudanden
        );

        // Kundregistret (Admin → Kunder → Data) fylls direkt vid onboarding —
        // lanseringshandoffens beställning 2026-09-20. Fail-soft: se
        // lib/snajp/kundregister.ts. Sluggen kommer ur provisioneringen,
        // aldrig ur klienten.
        tenantNyckel = kopplad?.apiKey ?? null;
        if (kopplad?.slug) {
          const { registreraKunduppgifter } = await import("@/lib/snajp/kundregister");
          await registreraKunduppgifter(kopplad.slug, {
            orgnr: formateraOrgnr(input.orgnr),
            faktureringsadress,
            kontakt: {
              namn: kontaktNamn,
              roll: kontaktRoll || null,
              mejl: kontaktMejl,
              telefon: kontaktTelefon || null
            }
          });
        }
      } else if (workspace?.slug) {
        /**
         * Arbetsytan har redan en kund i backenden, fast onboardingen inte var
         * klar: ett anrop genom proxyn kopplar den (`requireSnajpTenant()`),
         * till exempel från en annan flik. Uppmätt i development 2026-11-18:
         * då hoppades standardinställningarna, kundregistret och
         * webbplatsskanningen över. De körs nu mot den befintliga nyckeln.
         * Standardinställningarna skriver bara tomma fält, så inget kunden
         * redan ändrat skrivs över.
         */
        //
        // Nyckeln hämtas direkt och inte via requireSnajpTenant(): den läser
        // arbetsytans kontext genom React-cachen, som delas med renderingen av
        // omdirigeringen nedan. Med den vägen visade sidan ett tomt steg 1
        // efter inskickningen i stället för översikten (uppmätt 2026-11-18).
        const nycklar = await sqlAsUser<{ nyckel: string | null }>(
          user.id,
          "select public.tenant_api_key_for_current_workspace() as nyckel"
        );
        const apiKey = nycklar[0]?.nyckel;
        if (!apiKey) {
          throw new Error(`arbetsytan pekar på ${workspace.slug} men saknar sparad nyckel`);
        }
        const { fyllStandardinstallningar } = await import("@/lib/snajp/provisionering");
        tenantNyckel = apiKey;
        await fyllStandardinstallningar(
          apiKey,
          workspace,
          {
            product: payload.product,
            target_audience: payload.target_audience,
            offer: payload.offer,
            cta: payload.cta
          },
          malgrupp,
          erbjudanden
        );
        const { registreraKunduppgifter } = await import("@/lib/snajp/kundregister");
        await registreraKunduppgifter(workspace.slug, {
          orgnr: formateraOrgnr(input.orgnr),
          faktureringsadress,
          kontakt: {
            namn: kontaktNamn,
            roll: kontaktRoll || null,
            mejl: kontaktMejl,
            telefon: kontaktTelefon || null
          }
        });
      }
    } catch (error) {
      console.error("[onboarding] kunde inte koppla arbetsytans tenant:", error);
    }
  }

  /**
   * Webbplatsskanningen startas åt kunden (Antons beställning 2026-11-18), så
   * att kunskapsbasen inte är tom när arbetsytan öppnas. Den skriver förslag,
   * aldrig artiklar: kunden lägger till dem, och en rubrik kunden redan har
   * föreslås inte. Bara med supportagenten i paketet, som är den som svarar
   * ur kunskapsbasen, och bara när arbetsytan just fick sin egen nyckel.
   */
  const { PRODUKTER_FOR_PAKET } = await import("@/lib/pricing");
  const medSupport = paket ? PRODUKTER_FOR_PAKET[paket].includes("support") : true;
  if (tenantNyckel && medSupport) {
    const { startaWebbplatsskanning } = await import("@/lib/snajp/webbplatsskanning");
    await startaWebbplatsskanning(tenantNyckel, webbplats);
  }

  redirect("/dashboard");
}