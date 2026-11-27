/**
 * Iris i CRM:et: anropen mot leads-API:t (`/api/snajp-support/leads/...`).
 *
 * Samma backend och samma ändpunkter som dagens Leads (lib/leads/suite.ts), men
 * felen kommer som `CrmFel`, så att CRM:ets `Felruta`, `ArbetsytanAktiveras` och
 * läsrollens besked fungerar likadant i Iris-vyerna som i registret.
 *
 * Leads-API:ts felform är inte CRM-API:ts: FastAPI svarar `{ detail: "text" }`
 * (svensk text), ibland `{ detail: { message, saknas } }` (befordran) eller en
 * pydantic-lista, och proxyn `{ error, kod }` (`lasroll`, `ej_aktiverad`).
 */
import { CrmFel } from "@/lib/crm/api";
import { PROXYKODER } from "@/lib/crm/felkoder";
import type { Localized } from "@/lib/i18n";

/** Ett fel från leads-API:t. `saknas` bär fälten befordran saknar (LR-104). */
export class IrisFel extends CrmFel {
  constructor(
    text: Localized,
    status: number,
    kod: string | null,
    readonly saknas: string[] = []
  ) {
    super(text, status, kod);
  }
}

type Felkropp = {
  detail?: unknown;
  error?: string;
  kod?: string;
};

function detaljtext(d: unknown): string | null {
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    const delar = d.map((x) => (x && typeof x === "object" && "msg" in x ? String((x as { msg: unknown }).msg) : String(x))).filter(Boolean);
    return delar.length ? delar.join("; ") : null;
  }
  if (d && typeof d === "object") {
    const m = (d as { message?: unknown }).message;
    return typeof m === "string" ? m : null;
  }
  return null;
}

/**
 * `vag` utan prefix: `/leads/prospects?lista=1`. Kastar `IrisFel` vid felstatus.
 * Serverns egna texter är svenska; de visas på båda språken som de står, som i
 * dagens Leads, medan proxyns koder översätts (lib/crm/felkoder.ts).
 */
export async function irisAnrop<T>(vag: string, init?: RequestInit): Promise<T> {
  const svar = await fetch(`/api/snajp-support${vag}`, {
    cache: "no-store",
    ...init,
    headers: init?.body ? { "Content-Type": "application/json", ...init.headers } : init?.headers
  });
  if (svar.status === 204) return null as T;
  const kropp = (await svar.json().catch(() => null)) as (T & Felkropp) | null;
  if (!svar.ok) {
    const okant: Localized = { sv: `Anropet gick inte igenom (HTTP ${svar.status}).`, en: `The request failed (HTTP ${svar.status}).` };
    const kod = typeof kropp?.kod === "string" ? kropp.kod : null;
    const detalj = detaljtext(kropp?.detail);
    const saknas =
      kropp?.detail && typeof kropp.detail === "object" && !Array.isArray(kropp.detail) && Array.isArray((kropp.detail as { saknas?: unknown }).saknas)
        ? ((kropp.detail as { saknas: unknown[] }).saknas.map(String))
        : [];
    const text: Localized = detalj ? { sv: detalj, en: detalj } : ((kod ? PROXYKODER[kod] : undefined) ?? okant);
    throw new IrisFel(text, svar.status, kod, saknas);
  }
  return kropp as T;
}

/**
 * Alla rader i Iris-listans läge (`lista=1`, upp till 5 000 per anrop) tills
 * `fler` är falskt (LR-030). `fraga` lägger till `bortvalda=1` eller `arkiverade=1`.
 */
export async function allaLeads<T>(fraga = ""): Promise<T[]> {
  const alla: T[] = [];
  let offset = 0;
  for (;;) {
    const sida = await irisAnrop<{ prospects?: T[]; fler?: boolean; nasta?: number }>(
      `/leads/prospects?lista=1&limit=5000&offset=${offset}${fraga ? `&${fraga}` : ""}`
    );
    alla.push(...(sida?.prospects ?? []));
    if (!sida?.fler || typeof sida.nasta !== "number" || sida.nasta <= offset) return alla;
    offset = sida.nasta;
  }
}

/** Skapa utkast delas i omgångar om så här många (LR-042: vyns omgångar, servern har inget tak). */
export const PROCESSA_OMGANG = 200;

/**
 * Avsändaren när leadets panel (eller något i den) meddelar att leadet ändrats.
 * Panelen har då redan läst om och lyssnar bara på ändringar från andra (listan,
 * körningar, dagens Leads).
 */
export const PANELENS_KALLA = "crm-iris-panel";

/** Signalen dagens Leads sänder när leads eller utkast ändrats. CRM:ets vyer lyssnar på samma. */
export { LEADS_UPPDATERADE, meddelaLeadsUppdaterade } from "@/lib/leads/utkast";
