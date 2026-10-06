import "server-only";

import { SNAJP_SUPPORT_URL } from "@/app/api/snajp-support/_lib";
import { readJsonBody } from "@/lib/http/json";

/**
 * Standardinställningar ur kundens EGET underlag — så att en ny kund kan
 * använda produkten utan att först fylla i fyra formulär.
 *
 * ## Vad som var trasigt
 *
 * Kunden skriver in vad de säljer i uppstartsformuläret. Den texten hamnade i
 * `business_contexts` i Next-appens databas — och stannade där. Backenden, som
 * är den som faktiskt kör agenten, läser aldrig den tabellen: den läser
 * `context_docs` med `kind='product_marketing'` (se
 * snajp-support/app/leads/business_context.py, avsnittet "Var datan faktiskt
 * bor"). De två var inte synkade av någon.
 *
 * Följden: `require_business_context` avbröt VARJE leads-körning med
 * "Produktbeskrivningen saknas för den här kunden" trots att kunden fyllt i den
 * i uppstarten. Det som såg ut som en tom produkt var en bruten koppling.
 *
 * ## Vad som skrivs, och vad som inte skrivs
 *
 * Bara fält som är TOMMA. Funktionen är därför idempotent och går att köra på
 * varje inloggning utan att skriva över en enda rad kunden själv rört — det är
 * villkoret för att den ska få vara automatisk. Ett förslag som skriver över
 * kundens eget val är inte ett förslag, det är en bugg.
 *
 * ## Varför defaultarna ser ut som de gör
 *
 *  * **Produktbeskrivningen** är kundens egen text, ordagrant, i backendens
 *    format. Vi hittar inte på något: agenten ska sälja kundens erbjudande, och
 *    en påhittad mening blir ett faktum som grundningsgrinden sedan låter
 *    agenten citera.
 *  * **Röstdokumentet** är ett UTKAST med de regler som gäller alla svenska
 *    B2B-utskick (du-tilltal, korta meningar, inga utropstecken). Det är text
 *    kunden kan stryka över, inte ett påstående om hur just de låter.
 *  * **ICP** är det kunden själv valde i onboardingens målgruppssteg
 *    (`Underlag.malgruppsfilter`) — branscher, orter, undvik, roller och
 *    storleksspann. Utan det steget (inloggningsvägens läkning) får den bara
 *    det som går att sätta utan att gissa: storleksspannet (EU:s definition av
 *    småföretag, samma tal som backendens `SMAFORETAG_ANSTALLDA`) och
 *    beslutsfattarrollerna. Bransch och geografi GISSAS aldrig — ett gissat
 *    geografiskt filter smalnar av urvalet utan att någon bestämt det, och ett
 *    gissat branschfilter är samma sak fast dyrare.
 *  * **Autonomin** rörs inte. `draft` är backendens default och det enda läge
 *    som är säkert utan att en människa sagt något.
 */

/** Kundens underlag, som det står i `business_contexts`. */
export type Underlag = {
  /** `product` — orgnr, webbplats, vad de säljer, särskilt fokus. */
  produkt: string;
  /** `target_audience`. Tomt eller platshållartext tills kunden fyllt i. */
  malgrupp?: string | null;
  /** `offer`. */
  erbjudande?: string | null;
  /** `cta`. */
  nastaSteg?: string | null;
  /** Arbetsytans namn — rubriken i dokumentet. */
  namn?: string | null;
  /**
   * Målgruppen kunden fyllde i i onboardingen. Saknas i inloggningsvägen — då
   * gäller standardrollerna och småföretagsspannet som förut.
   */
  malgruppsfilter?: Malgruppsfilter;
};

/**
 * Onboardingens målgruppssteg, redan tolkat till listor och tal
 * (lib/actions/onboarding.ts). Tomma listor betyder "inget filter" — samma
 * semantik som ICP:n själv.
 */
export type Malgruppsfilter = {
  branscher: string[];
  orter: string[];
  undvik: string[];
  roller: string[];
  anstalldaMin: number | null;
  anstalldaMax: number | null;
};

/** Vad som faktiskt fylldes i. Loggas; ingen del av det är kritiskt. */
export type Standardutfall = {
  produktbeskrivning: boolean;
  rostdokument: boolean;
  icp: boolean;
};

/**
 * Platshållaren onboardingen skriver i fält den inte kan fylla. Den ska aldrig
 * gå vidare som om den vore kundens svar — se lib/actions/onboarding.ts.
 */
const AVVAKTAR = "(läses in från webbplatsen)";

/**
 * Samma tal som `SMAFORETAG_ANSTALLDA` i snajp-support/app/leads/icp.py.
 * Exporteras för onboardingens förifyllning (app/onboarding/page.tsx skickar
 * dem som props — modulen är server-only och kan inte importeras i klienten).
 */
export const SMAFORETAG: [number, number] = [1, 49];

/**
 * Kontaktrollen i ett litet svenskt B2B-bolag: bara VD (Antons leadsregel 3,
 * 2026-10-04). Listan bar förut även "Inköpschef" och "Platschef". De nådde
 * sökprompten som "beslutsfattare att nå" i varje körning utan branschfilter,
 * drog sökningen mot byggbolag (platschef är en byggtitel) och gav ett utkast
 * ställt till en inköpschef (provkörningen 2026-10-05).
 */
export const STANDARDROLLER = ["VD"];

function rent(varde: string | null | undefined): string {
  const text = (varde ?? "").trim();
  return text === AVVAKTAR ? "" : text;
}

/**
 * Produktbeskrivningen i backendens format.
 *
 * `require_business_context` kräver minst 120 tecken (MINSTA_ANVANDBARA_LANGD)
 * och avvisar allt kortare som "för tunt för att skriva ett mejl på". Rubrikerna
 * nedan bär en del av den längden, men bara en del: en kund som skriver en rad
 * får fortfarande ett dokument som är för kort, och då ska körningen stanna med
 * backendens eget besked. Att fylla ut med generisk text hade tystat grinden
 * utan att ge agenten något att sälja — precis det grinden finns för.
 */
function produktdokument(underlag: Underlag): string {
  const rader = [
    `# Vad ${rent(underlag.namn) || "vi"} säljer`,
    "",
    rent(underlag.produkt),
    ...(rent(underlag.erbjudande) ? ["", "## Erbjudandet", rent(underlag.erbjudande)] : []),
    ...(rent(underlag.malgrupp) ? ["", "## Vem vi säljer till", rent(underlag.malgrupp)] : []),
    ...(rent(underlag.nastaSteg) ? ["", "## Nästa steg vi vill ha", rent(underlag.nastaSteg)] : []),
    "",
    "_Hämtat ur uppstartsformuläret. Ändra i Inställningar → Vad ni säljer._"
  ];
  return rader.join("\n").trim();
}

/** Utkastet till röstdokument. Regler, inte påståenden om kunden. */
function roststartpunkt(): string {
  return [
    "Vi säger du, aldrig ni.",
    "Korta meningar. Ett budskap per stycke.",
    "Inga utropstecken och inga superlativ.",
    'Vi skriver "hör av dig", inte "tveka inte att kontakta oss".',
    "Vi lovar bara det vi vet — saknas en uppgift frågar vi i stället för att gissa.",
    "",
    "Det här är ett utkast. Skriv om det så att det låter som ni."
  ].join("\n");
}

async function anrop<T>(apiKey: string, path: string, init: RequestInit = {}): Promise<T | null> {
  const response = await fetch(`${SNAJP_SUPPORT_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
      ...(init.headers ?? {})
    },
    cache: "no-store",
    signal: AbortSignal.timeout(30_000)
  });
  if (!response.ok) {
    throw new Error(`${path} svarade ${response.status}.`);
  }
  return readJsonBody<T>(response);
}

type Icp = {
  industries?: string[];
  exclude_industries?: string[];
  geography?: string[];
  roles?: string[];
  must_have?: string[];
  deal_breakers?: string[];
  /** Det GAMLA storleksfältet. UI:t läser det; backenden speglar det ur `size`. */
  company_size?: { min?: number | null; max?: number | null };
  /**
   * Det strukturerade storleksfältet — det källorna och scoringen faktiskt
   * läser. Måste sättas tillsammans med `company_size`, se `storlek()` nedan.
   */
  size?: {
    anstallda_min?: number | null;
    anstallda_max?: number | null;
    omsattning_min?: number | null;
    omsattning_max?: number | null;
  };
};

/**
 * Storleksspannet, satt i BÅDA fälten.
 *
 * Att bara sätta `company_size` räcker inte, och det är inte uppenbart av
 * API:et: backendens `_normalize_size` seedar visserligen ur `company_size`,
 * men skriver sedan över varje nyckel som FINNS i inkommande `size` — och ett
 * `size` läst ur GET-svaret innehåller `anstallda_min: null`. Spannet nollades
 * alltså av det egna svaret, och `company_size` speglades tillbaka som tomt.
 * Uppmätt mot `validate_icp(normalize_icp(...))`, inte antaget.
 *
 * `size` är dessutom det fält källorna och scoringen läser; `company_size` är
 * kvar för formuläret. Båda måste säga samma sak — ett filter vars utfall beror
 * på vem som läser det är värre än inget filter.
 */
function storlek(
  befintlig: Icp | undefined,
  [min, max]: [number | null, number | null] = SMAFORETAG
): Pick<Icp, "size" | "company_size"> {
  return {
    size: { ...(befintlig?.size ?? {}), anstallda_min: min, anstallda_max: max },
    company_size: { min, max }
  };
}

function icpArTomt(icp: Icp | undefined): boolean {
  if (!icp) return true;
  const listor = [
    icp.industries,
    icp.exclude_industries,
    icp.geography,
    icp.roles,
    icp.must_have,
    icp.deal_breakers
  ];
  const nagonLista = listor.some((lista) => Array.isArray(lista) && lista.length > 0);
  const storlek = icp.company_size ?? {};
  const nagonStorlek = storlek.min != null || storlek.max != null;
  return !nagonLista && !nagonStorlek;
}

/**
 * Fyller de tomma fälten. Kastar aldrig — anroparen får ett utfall att logga.
 *
 * Samma resonemang som notissvaret i lib/actions/onboarding.ts: ett misslyckat
 * sidospår får inte fälla ett lyckat huvudspår. Kunden har registrerat sig;
 * att skicka tillbaka dem till formuläret för att backenden sov vore att
 * straffa dem för fel sak.
 */
export async function sattStandardinstallningar(
  apiKey: string,
  underlag: Underlag
): Promise<Standardutfall> {
  const utfall: Standardutfall = { produktbeskrivning: false, rostdokument: false, icp: false };

  if (rent(underlag.produkt)) {
    try {
      const svar = await anrop<{ docs?: { content?: string }[] }>(
        apiKey,
        "/api/leads/context-docs?kind=product_marketing"
      );
      const finns = (svar?.docs ?? []).some((doc) => (doc.content ?? "").trim().length > 0);
      if (!finns) {
        await anrop(apiKey, "/api/leads/context-docs", {
          method: "POST",
          body: JSON.stringify({
            kind: "product_marketing",
            content: produktdokument(underlag),
            source: "onboarding-formular"
          })
        });
        utfall.produktbeskrivning = true;
      }
    } catch (error) {
      console.error("[standard] produktbeskrivningen kunde inte skrivas:", error);
    }
  }

  try {
    const svar = await anrop<{ content?: string }>(apiKey, "/api/leads/soul");
    if (!(svar?.content ?? "").trim()) {
      await anrop(apiKey, "/api/leads/soul", {
        method: "PUT",
        body: JSON.stringify({ content: roststartpunkt() })
      });
      utfall.rostdokument = true;
    }
  } catch (error) {
    console.error("[standard] röstdokumentet kunde inte skrivas:", error);
  }

  try {
    const svar = await anrop<{ icp?: Icp }>(apiKey, "/api/leads/config");
    if (icpArTomt(svar?.icp)) {
      const m = underlag.malgruppsfilter;
      // Kundens egna val från målgruppssteget, annars defaultarna. Fälten är
      // ICP:ns egna namn (LIST_FIELDS i snajp-support/app/leads/icp.py).
      const valt: Icp = m
        ? {
            industries: m.branscher,
            geography: m.orter,
            exclude_industries: m.undvik,
            roles: m.roller,
            ...storlek(svar?.icp, [m.anstalldaMin, m.anstalldaMax])
          }
        : { roles: STANDARDROLLER, ...storlek(svar?.icp) };
      await anrop(apiKey, "/api/leads/config", {
        method: "PUT",
        body: JSON.stringify({ icp: { ...(svar?.icp ?? {}), ...valt } })
      });
      utfall.icp = true;
    }
  } catch (error) {
    console.error("[standard] ICP-defaultarna kunde inte skrivas:", error);
  }

  // Iris-profilen kompileras direkt ur det som just skrevs, så att den är klar
  // när kunden först öppnar leads. Väntas INTE in: kompileringen kan gå genom
  // en LLM, och kunden ska inte sitta kvar i uppstarten för den. Uteblir den
  // kompileras profilen ändå vid första läsningen (sakerstall_profil).
  if (utfall.icp || utfall.produktbeskrivning) {
    void anrop(apiKey, "/api/leads/profil").catch((error) => {
      console.error("[standard] Iris-profilen kunde inte kompileras:", error);
    });
  }

  return utfall;
}
