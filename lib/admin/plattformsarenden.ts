/**
 * Felrapporterna i adminytan: den rena logiken bakom listan i
 * `components/admin/Felrapporter.tsx` (planens del 5, PLAN-HJALPRUTAN-2026-11-25).
 *
 * Här bor bara det som går att testa utan React och utan nätet: lägena, i
 * vilken ordning ärendena står, vilka byten som finns på en öppnad rad och
 * vad varje byte kräver innan det får skickas. Texterna bor i
 * `lib/admin/sprak.ts`; den här filen bär bara nycklar.
 *
 * Kontraktet är backendens `GET /api/admin/plattformsarenden` och
 * `POST /api/admin/plattformsarenden/{id}/status`. Typerna nedan speglar det.
 *
 * Kör: node --test "lib/**\/*.test.ts"
 */

export const STATUSAR = [
  "mottagen",
  "undersoks",
  "rattning_pagar",
  "redo_att_testa",
  "kund_godkand",
  "i_development",
  "i_main",
  "behover_mer",
  "stangd"
] as const;

export type Arendestatus = (typeof STATUSAR)[number];

export type AdminHandelse = {
  tid: string;
  typ: string;
  status: string | null;
  meddelande: string | null;
  synlig_for_kund: boolean;
  aktor: string | null;
};

export type AdminArende = {
  id: string;
  nummer: string;
  status: Arendestatus;
  sida: string;
  gjorde: string;
  created_at: string;
  updated_at: string;
  vantar_pa_kund: boolean;
  testversion_url: string | null;
  rapportor_user_id: string;
  rapportor_namn: string | null;
  kund_workspace_id: string;
  kund_tenant_slug: string;
  vy: string;
  roll: string;
  besok_av_admin: boolean;
  hande: string;
  vantade: string;
  har_bild: boolean;
  handelser: AdminHandelse[];
};

export function arStatus(varde: unknown): varde is Arendestatus {
  return typeof varde === "string" && (STATUSAR as readonly string[]).includes(varde);
}

/** Klara ärenden: rättningen är ute, eller ärendet är stängt med en förklaring. */
export function arAvslutat(status: Arendestatus): boolean {
  return status === "i_main" || status === "stangd";
}

/** Samma regel som backendens `vantar_pa_kund`: kunden har nästa drag. */
export function vantarPaKund(status: Arendestatus): boolean {
  return status === "behover_mer" || status === "redo_att_testa";
}

/**
 * Var ärendet står i arbetet, för filterchipen och sorteringen.
 *
 * hos_oss: Snajp har nästa drag (det som väntar på oss står överst).
 * hos_kunden: kunden ska svara eller testa.
 * klara: ute i Snajp eller stängda, alltid sist.
 */
export type Grupp = "hos_oss" | "hos_kunden" | "klara";

export function grupp(status: Arendestatus): Grupp {
  if (arAvslutat(status)) return "klara";
  return vantarPaKund(status) ? "hos_kunden" : "hos_oss";
}

const GRUPPORDNING: Record<Grupp, number> = { hos_oss: 0, hos_kunden: 1, klara: 2 };

/**
 * Öppna ärenden först och stängda sist. Inom en grupp står det senast
 * ändrade överst: ett ärende som just fått ett svar från kunden ska synas.
 * Ger en ny lista; indata rörs inte.
 */
export function sorteraArenden<T extends Pick<AdminArende, "status" | "updated_at" | "created_at">>(
  arenden: readonly T[]
): T[] {
  return [...arenden].sort((x, y) => {
    const g = GRUPPORDNING[grupp(x.status)] - GRUPPORDNING[grupp(y.status)];
    if (g !== 0) return g;
    const tid = (y.updated_at || y.created_at).localeCompare(x.updated_at || x.created_at);
    return tid !== 0 ? tid : y.created_at.localeCompare(x.created_at);
  });
}

export type Filter = "oppna" | Grupp | "alla";
export const FILTER: readonly Filter[] = ["oppna", "hos_oss", "hos_kunden", "klara", "alla"];

export function passarFilter(status: Arendestatus, filter: Filter): boolean {
  if (filter === "alla") return true;
  if (filter === "oppna") return !arAvslutat(status);
  return grupp(status) === filter;
}

/**
 * Raderna listan visar under ett filter. Ett ärende som admin just bytt läge
 * på (`kvar`) står kvar fast det nya läget inte passar filtret, så att bytet
 * syns med sitt nya läge och sin händelse i stället för att raden försvinner.
 * Komponenten tömmer `kvar` när filtret byts; en omladdning tömmer det också.
 */
export function synligaArenden<T extends Pick<AdminArende, "id" | "status" | "updated_at" | "created_at">>(
  arenden: readonly T[],
  filter: Filter,
  kvar: ReadonlySet<string>
): T[] {
  return sorteraArenden(arenden.filter((x) => passarFilter(x.status, filter) || kvar.has(x.id)));
}

/**
 * Nyckeln aktören slås upp på i `sprak.ts` (`frAktor_<nyckel>`). Backenden
 * skriver en namngiven admin som `admin:<uuid>`; id:t säger plattformsadmin
 * inget, så det blir "Plattformsadmin" som en anonym.
 */
export function aktorNyckel(aktor: string): string {
  return aktor.startsWith("admin:") ? "admin" : aktor;
}

/** Antalet öppna ärenden: talet i panelens rad nyckeltal. */
export function antalOppna(arenden: readonly Pick<AdminArende, "status">[]): number {
  return arenden.filter((a) => !arAvslutat(a.status)).length;
}

/* ------------------------------------------------------------ Åtgärderna */

export type AtgardId =
  | "undersok"
  | "rattning"
  | "redo"
  | "fraga"
  | "stang"
  | "development"
  | "ute";

export type Atgard = {
  id: AtgardId;
  status: Arendestatus;
  /** Bytet går inte att skicka utan ett meddelande till kunden. */
  kraverMeddelande: boolean;
  /** Bytet går inte att skicka utan adressen till testversionen. */
  kraverAdress: boolean;
};

/**
 * I arbetets ordning. "Fråga kunden" och "Stäng med förklaring" kräver ett
 * meddelande (backenden avvisar behover_mer och stangd utan det), och "Redo
 * att testa" kräver adressen kunden ska öppna.
 */
export const ATGARDER: readonly Atgard[] = [
  { id: "undersok", status: "undersoks", kraverMeddelande: false, kraverAdress: false },
  { id: "rattning", status: "rattning_pagar", kraverMeddelande: false, kraverAdress: false },
  { id: "redo", status: "redo_att_testa", kraverMeddelande: false, kraverAdress: true },
  { id: "fraga", status: "behover_mer", kraverMeddelande: true, kraverAdress: false },
  { id: "stang", status: "stangd", kraverMeddelande: true, kraverAdress: false },
  { id: "development", status: "i_development", kraverMeddelande: false, kraverAdress: false },
  { id: "ute", status: "i_main", kraverMeddelande: false, kraverAdress: false }
];

export function atgard(id: AtgardId): Atgard {
  const hittad = ATGARDER.find((x) => x.id === id);
  if (!hittad) throw new Error(`okänd åtgärd: ${id}`);
  return hittad;
}

/** Bytena på en öppnad rad: alla utom det läge ärendet redan står i. */
export function atgarderFor(status: Arendestatus): Atgard[] {
  return ATGARDER.filter((x) => x.status !== status);
}

/**
 * Bara en https-adress: kunden loggar in i testversionen, och en länk som
 * går över http eller `javascript:` ska aldrig nå kundens ruta.
 */
export function arTestadress(varde: string): boolean {
  try {
    const url = new URL(varde.trim());
    return url.protocol === "https:";
  } catch {
    return false;
  }
}

export type Valideringsfel = "meddelandeKravs" | "adressKravs" | "adressOgiltig";

/** Varför bytet inte får skickas ännu, eller null när det får det. */
export function validera(x: Atgard, meddelande: string, adress: string): Valideringsfel | null {
  if (x.kraverMeddelande && !meddelande.trim()) return "meddelandeKravs";
  if (x.kraverAdress) {
    if (!adress.trim()) return "adressKravs";
    if (!arTestadress(adress)) return "adressOgiltig";
  }
  return null;
}

export type Statuskropp = {
  status: Arendestatus;
  meddelande_till_kund: string | null;
  testversion_url: string | null;
};

/**
 * Kroppen till `POST /api/admin/plattformsarenden/{id}/status`. Tomt
 * meddelande blir null, så att ett byte utan ord inte blir en tom
 * kundsynlig händelse. Adressen följer bara med "Redo att testa".
 */
export function statuskropp(x: Atgard, meddelande: string, adress: string): Statuskropp {
  const text = meddelande.trim();
  return {
    status: x.status,
    meddelande_till_kund: text ? text : null,
    testversion_url: x.kraverAdress ? adress.trim() : null
  };
}

/* ---------------------------------------------------------------- Bilden */

/**
 * Kundens bild hämtas ett ärende i taget, när admin ber om den, från
 * `GET /api/admin/plattformsarenden/{id}/bild`. Listan bär bara `har_bild`.
 */
export function bildadress(id: string): string {
  return `/api/admin/plattformsarenden/${encodeURIComponent(id)}/bild`;
}

/** Samma fyra format som inlämningen (lib/snajp/hjalp.ts) och backenden släpper igenom. */
const BILD = /^data:image\/(?:png|jpeg|webp|gif);base64,[A-Za-z0-9+/=]+$/;

/** Bilden ur svaret som data-URL, eller null när svaret inte bär en bild i ett tillåtet format. */
export function lasBild(kropp: unknown): string | null {
  if (!kropp || typeof kropp !== "object") return null;
  const bild = (kropp as { bild?: unknown }).bild;
  return typeof bild === "string" && BILD.test(bild) ? bild : null;
}

/** Ersätter ärendet med samma id; resten av listan står kvar. */
export function ersatt<T extends { id: string }>(arenden: readonly T[], nytt: T): T[] {
  return arenden.map((x) => (x.id === nytt.id ? nytt : x));
}
