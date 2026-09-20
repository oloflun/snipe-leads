"use server";

import type { BusinessContextInsert } from "@/lib/database.types";
import { redirect } from "next/navigation";
import { formateraOrgnr, orgnrFel } from "@/lib/orgnr";

/**
 * Bolagsfälten är fyra, inte åtta — de gamla åtta var förifyllda med påhittade
 * värden som gick att skicka in rakt av (se OnboardingWizard, som ärvde
 * lärdomen). Sedan 2026-09-20 bär flödet dessutom bransch, kontaktperson och
 * paketval, i fyra steg — se components/auth/OnboardingWizard.tsx.
 */
export type OnboardingInput = {
  orgnr: string;
  webbplats: string;
  produkt: string;
  fokus: string;
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
        error: `Ditt konto saknar ett workspace och kunde inte repareras: ${(repairError as Error).message}`
      };
    }
    profile = await getProfileForUser(user.id);
  }

  if (!profile) {
    return { success: false, error: "Ditt konto saknar ett workspace. Kontakta support." };
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

  const webbplats = normaliseraWebbplats(input.webbplats);
  if (!webbplats) {
    return {
      success: false,
      error: "Fyll i webbplatsen. Det är den agenterna läser för att förstå er."
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

  const { arBransch } = await import("@/lib/bransch");
  if (!arBransch(input.bransch)) {
    return { success: false, error: "Välj er bransch i listan." };
  }

  const kontaktNamn = input.kontaktNamn.trim();
  const kontaktMejl = input.kontaktMejl.trim().toLowerCase();
  if (!kontaktNamn) {
    return { success: false, error: "Fyll i vem som är kontaktperson hos er." };
  }
  if (!kontaktMejl.includes("@")) {
    return { success: false, error: "Fyll i kontaktpersonens e-postadress." };
  }
  const kontaktRoll = (input.kontaktRoll ?? "").trim();
  const kontaktTelefon = (input.kontaktTelefon ?? "").trim();

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
      input.testkund
        ? "Organisationsnummer: — (TESTARBETSYTA, inget riktigt bolag)"
        : `Organisationsnummer: ${formateraOrgnr(input.orgnr)}`,
      `Webbplats: ${webbplats}`,
      `Bransch: ${input.bransch}`,
      `Vad vi säljer: ${produkt}`,
      fokus ? `Särskilt fokus: ${fokus}` : null,
      // Kontaktpersonen står i texten OCKSÅ när CRM-skrivningen lyckas:
      // affärskontexten är det lager som aldrig tappas bort, och admin-
      // fliken Kunder & Data härleder redan andra fält härifrån.
      `Kontaktperson: ${kontaktNamn}${kontaktRoll ? ` (${kontaktRoll})` : ""} — ${kontaktMejl}${
        kontaktTelefon ? `, ${kontaktTelefon}` : ""
      }`
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
          true
        );

        // Kundregistret (Admin → Kunder → Data) fylls direkt vid onboarding —
        // lanseringshandoffens beställning 2026-09-20. Fail-soft: se
        // lib/snajp/kundregister.ts. Sluggen kommer ur provisioneringen,
        // aldrig ur klienten.
        if (kopplad?.slug) {
          const { registreraKunduppgifter } = await import("@/lib/snajp/kundregister");
          await registreraKunduppgifter(kopplad.slug, {
            orgnr: formateraOrgnr(input.orgnr),
            kontakt: {
              namn: kontaktNamn,
              roll: kontaktRoll || null,
              mejl: kontaktMejl,
              telefon: kontaktTelefon || null
            }
          });
        }
      }
    } catch (error) {
      console.error("[onboarding] kunde inte koppla arbetsytans tenant:", error);
    }
  }

  redirect("/dashboard");
}