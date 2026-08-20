"use server";

import type { BusinessContextInsert } from "@/lib/database.types";
import { redirect } from "next/navigation";
import { formateraOrgnr, orgnrFel } from "@/lib/orgnr";

/**
 * Fyra fält, inte åtta. Se components/auth/OnboardingForm.tsx om varför de
 * gamla fälten var aktivt skadliga: de var förifyllda med påhittade värden som
 * gick att skicka in rakt av.
 */
export type OnboardingInput = {
  orgnr: string;
  webbplats: string;
  produkt: string;
  fokus: string;
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
      error: "Fyll i webbplatsen. Det är den agenten läser för att förstå er."
    };
  }

  const produkt = input.produkt.trim();
  if (!produkt) {
    return {
      success: false,
      error: "Skriv en rad om vad ni säljer. Det är det agenten ska sälja."
    };
  }

  const fokus = input.fokus.trim();

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
      `Vad vi säljer: ${produkt}`,
      fokus ? `Särskilt fokus: ${fokus}` : null
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
  }

  redirect("/dashboard");
}