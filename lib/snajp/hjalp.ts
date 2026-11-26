import "server-only";

import { createHmac, hkdfSync, timingSafeEqual } from "node:crypto";
import { NextResponse } from "next/server";
import { proxyWithApiKey } from "@/app/api/snajp-support/_lib";
import { hasDatabase, sqlAsUser } from "@/lib/db";
import { aktivVy } from "@/lib/vy";
import type { WorkspaceContext } from "@/lib/workspace";

/**
 * Hjälprutans servergräns (docs/PLAN-HJALPRUTAN-2026-11-25.md, del 2 och 5).
 *
 * Varje väg under app/api/snajp-support/hjalp/ går genom den här filen. Den
 * gör två saker och inget annat:
 *
 *  1. Bygger IDENTITETEN ur sessionen: vem som frågar, i vilken arbetsyta, i
 *     vilken vy och med vilken roll. Inget av det tas ur klientens kropp.
 *  2. Plockar ur klientens kropp de få fält som får komma därifrån (texten,
 *     sidans sökväg, de tre felfälten, en bild, ett svar, ett utslag) och
 *     kastar resten.
 *
 * Nyckeln är hjälpens egen kund i systemet (`SNAJP_KEY_SNAJP_HJALP`, slug
 * `snajp-hjalp`), aldrig kundens och aldrig proxyAsTenant. Varje väg läser
 * variabeln själv och skickar den hit, så att det syns i vägen vilken nyckel
 * som används (tests/invariants/test_inv_hjalp_001.py).
 *
 * `arbetsyta` sätts aldrig: den flaggan ger agenten den anropande kundens
 * interna nyckeltal, och under hjälpens nyckel hade det varit Snajps egna.
 *
 * Får inte importeras från en klientkomponent: den läser sessionen.
 */

/** Domänen för den inloggades identitet hos hjälpen. Den anonyma chatten avvisar den. */
export const HJALP_DOMAN = "@kund.snajp.se";

/** Sidans sökväg: bara sökvägen, högst så här lång. */
export const SIDA_MAX = 300;
/** Felfälten och svaren. Backendens chattfält tar 8000; en felrapport behöver mindre. */
export const FALT_MAX = 4000;
/** Chattmeddelandet, samma tak som backendens ChatRequest.message. */
export const MEDDELANDE_MAX = 8000;
/**
 * En bild som data-URL. Chattens bilagor skalas ned till 1024 px i webbläsaren
 * (components/snajp/SupportChat.tsx:downscaleImage) och hamnar under det här.
 */
export const BILD_MAX_TECKEN = 2_000_000;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const BILD = /^data:image\/(?:png|jpeg|webp|gif);base64,[A-Za-z0-9+/=]+$/;
// eslint-disable-next-line no-control-regex
const KONTROLLTECKEN = /[\u0000-\u001f\u007f]/g;

export type HjalpIdentitet = {
  /** auth.users.id för den inloggade. Rapportören är alltid hen, även i ett adminbesök. */
  userId: string;
  /** profiles.full_name, eller sessionens namn. */
  namn: string | null;
  /** Den inloggades arbetsyta; i ett adminbesök den besökta kundens, om den går att slå upp. */
  workspaceId: string;
  /** Kunden rapporten gäller: arbetsytans slug, eller den besökta kundens. */
  tenantSlug: string;
  /** "egen" (kundens egen yta), "admin", "demo" eller "kund" (adminbesök hos en kund). */
  vy: string;
  /** profiles.role: owner, member eller viewer. */
  roll: string;
  /** Plattformsadmin som tittar som en namngiven kund. */
  besokAvAdmin: boolean;
};

export function hjalpAvsandare(userId: string): string {
  return `${userId}${HJALP_DOMAN}`;
}

export function arUuid(varde: unknown): varde is string {
  return typeof varde === "string" && UUID.test(varde);
}

/** Klientens kropp som objekt; allt annat blir ett tomt objekt. */
export function tolka(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return {};
  }
}

function falt(kropp: unknown): Record<string, unknown> {
  return kropp && typeof kropp === "object" && !Array.isArray(kropp) ? (kropp as Record<string, unknown>) : {};
}

function text(varde: unknown, max: number): string {
  return typeof varde === "string" ? varde.trim().slice(0, max) : "";
}

/** Sökvägen utan söksträng och fragment. En hel adress blir sin sökväg. */
export function renSida(varde: unknown): string {
  if (typeof varde !== "string") return "/";
  let sida = varde.trim();
  if (/^[a-z][a-z0-9+.-]*:/i.test(sida)) {
    try {
      sida = new URL(sida).pathname;
    } catch {
      return "/";
    }
  }
  sida = sida.split(/[?#]/)[0].replace(KONTROLLTECKEN, "");
  if (!sida.startsWith("/")) sida = `/${sida}`;
  return sida.slice(0, SIDA_MAX);
}

/** En bild som data-URL i ett av fyra bildformat, eller null. */
export function renBild(varde: unknown): string | null {
  return typeof varde === "string" && varde.length <= BILD_MAX_TECKEN && BILD.test(varde) ? varde : null;
}

export type HjalpChattkropp = {
  message: string;
  channel: "web";
  customer_email: string;
  customer_name: string | null;
  attachments: { data_url: string }[];
  is_test: false;
};

/**
 * Chattanropet till hjälpens agent. Ur klienten: texten och högst en bild.
 * Allt annat (customer_email, tenant, arbetsyta, is_test, subject) kastas.
 */
export function hjalpChattkropp(klient: unknown, id: HjalpIdentitet): HjalpChattkropp | null {
  const k = falt(klient);
  const message = text(k.message, MEDDELANDE_MAX);
  if (!message) return null;
  const forsta = Array.isArray(k.attachments) ? falt(k.attachments[0]).data_url : undefined;
  const bild = renBild(forsta);
  return {
    message,
    channel: "web",
    customer_email: hjalpAvsandare(id.userId),
    customer_name: id.namn,
    attachments: bild ? [{ data_url: bild }] : [],
    is_test: false
  };
}

/** Samtalet läses alltid under den inloggades egen adress; klientens kropp används inte. */
export function hjalpSamtalskropp(id: HjalpIdentitet): { customer_email: string } {
  return { customer_email: hjalpAvsandare(id.userId) };
}

export type Rapportkropp = {
  rapportor_user_id: string;
  rapportor_namn: string | null;
  kund_workspace_id: string;
  kund_tenant_slug: string;
  vy: string;
  roll: string;
  besok_av_admin: boolean;
  sida: string;
  gjorde: string;
  hande: string;
  vantade: string;
  bild: string | null;
};

/** Felrapporten. Null när inget av de tre fälten är ifyllt. */
export function rapportkropp(klient: unknown, id: HjalpIdentitet): Rapportkropp | null {
  const k = falt(klient);
  const gjorde = text(k.gjorde, FALT_MAX);
  const hande = text(k.hande, FALT_MAX);
  const vantade = text(k.vantade, FALT_MAX);
  if (!gjorde && !hande && !vantade) return null;
  return {
    rapportor_user_id: id.userId,
    rapportor_namn: id.namn,
    kund_workspace_id: id.workspaceId,
    kund_tenant_slug: id.tenantSlug,
    vy: id.vy,
    roll: id.roll,
    besok_av_admin: id.besokAvAdmin,
    sida: renSida(k.sida),
    gjorde,
    hande,
    vantade,
    bild: renBild(k.bild)
  };
}

export function svarkropp(klient: unknown, id: HjalpIdentitet): { rapportor_user_id: string; text: string } | null {
  const svar = text(falt(klient).text, FALT_MAX);
  return svar ? { rapportor_user_id: id.userId, text: svar } : null;
}

export function utslagskropp(
  klient: unknown,
  id: HjalpIdentitet
): { rapportor_user_id: string; fungerar: boolean; kommentar: string | null } | null {
  const k = falt(klient);
  if (typeof k.fungerar !== "boolean") return null;
  return { rapportor_user_id: id.userId, fungerar: k.fungerar, kommentar: text(k.kommentar, FALT_MAX) || null };
}

/**
 * Den besökta kundens arbetsyte-id, slaget ur sluggen. Null när raden inte
 * syns för adminens roll (RLS, se lib/data/dashboard.ts) eller när kunden
 * saknar arbetsyta (demokontot nordlys-handel).
 */
async function besoktArbetsyta(userId: string, slug: string): Promise<string | null> {
  if (!hasDatabase()) return null;
  try {
    const rader = await sqlAsUser<{ id: string }>(
      userId,
      "select id from public.workspaces where slug = $1 limit 1",
      [slug]
    );
    const id = rader[0]?.id;
    return arUuid(id) ? id : null;
  } catch {
    return null;
  }
}

/**
 * Identiteten ur sessionen. Anroparen har redan grindat på getWorkspaceContext.
 *
 * I ett adminbesök (`vy: "kund"`) och i demovyn är rapportören adminen själv
 * och kunden den besökta. Arbetsytan slås upp ur den besöktas slug, så att
 * kund_workspace_id och kund_tenant_slug pekar på samma kund. Går den inte att
 * slå upp (RLS, eller demokontot utan arbetsyta) står adminens egen arbetsyta
 * kvar, eftersom kontraktet kräver ett uuid; då är kund_tenant_slug den enda
 * pålitliga kunduppgiften, och `besokAvAdmin` säger att det är ett besök.
 */
export async function hjalpIdentitet(context: WorkspaceContext): Promise<HjalpIdentitet> {
  const lage = await aktivVy();
  const namn = context.profile.full_name?.trim() || context.user.name?.trim() || null;
  const workspaceId =
    lage.vy === "admin"
      ? context.workspace.id
      : ((await besoktArbetsyta(context.user.id, lage.slug)) ?? context.workspace.id);
  return {
    userId: context.user.id,
    namn,
    workspaceId,
    tenantSlug: lage.vy === "admin" ? (context.workspace.slug ?? "") : lage.slug,
    vy: lage.vy === "admin" ? (context.isPlatformAdmin ? "admin" : "egen") : lage.vy,
    roll: context.profile.role || "member",
    besokAvAdmin: lage.vy === "kund"
  };
}

/** Texten när hjälpen inte är påslagen i miljön. Båda språken: klienten väljer efter `kod`. */
export const HJALP_AV = {
  sv: "Hjälpen är inte påslagen här ännu. Skriv till snajpsupport@gmail.com så länge.",
  en: "Help is not switched on here yet. Write to snajpsupport@gmail.com in the meantime."
};

function privat(svar: Response): Response {
  svar.headers.set("Cache-Control", "private, no-store");
  svar.headers.set("Vary", "Cookie");
  return svar;
}

export function ejInloggadSvar(): Response {
  return privat(
    NextResponse.json(
      { error: "Du måste vara inloggad. / You need to be signed in.", kod: "ej_inloggad" },
      { status: 401 }
    )
  );
}

export function ogiltigtSvar(): Response {
  return privat(
    NextResponse.json(
      {
        error: "Uppgifterna saknas eller gick inte att läsa. / The details are missing or could not be read.",
        kod: "ogiltig"
      },
      { status: 422 }
    )
  );
}

export function hittadesInteSvar(): Response {
  return privat(NextResponse.json({ error: "Ärendet finns inte. / The case does not exist.", kod: "saknas" }, { status: 404 }));
}

/**
 * Ett hjälpjobb som inte finns, har städats bort, eller tillhör någon annan.
 * Samma svar i alla tre fallen: ingen ska kunna pröva sig fram till vilka id
 * som finns.
 */
export function jobbetSaknasSvar(): Response {
  return privat(
    NextResponse.json(
      {
        error: "Frågan finns inte eller har städats bort. / The question does not exist or has been cleaned up.",
        kod: "saknas"
      },
      { status: 404 }
    )
  );
}

/*
 * Ägarkontrollen på hjälpens jobb.
 *
 * Alla kunders hjälpfrågor går under SAMMA hjälpkund (`snajp-hjalp`), så
 * backendens tenantkontroll på GET /api/jobs/{id} skiljer dem inte åt: den som
 * har ett jobb-id hade kunnat läsa en annan kunds fråga och svar. Jobb-id:t
 * lämnar därför aldrig servern naket. POST /hjalp byter backendens job_id mot
 * `<uuid>.<signatur>`, där signaturen är HMAC-SHA256 över id:t, användaren och
 * arbetsytan med en nyckel härledd ur `AUTH_SECRET` (HKDF, eget info-värde, så
 * att nyckeln inte är densamma som tvåstegsverifieringens). Pollningen prövar
 * signaturen mot den inloggades identitet i konstant tid och svarar 404 när
 * den inte stämmer, innan något når backenden.
 *
 * Saknas `AUTH_SECRET` går ingen inloggning alls i miljön; då signeras inget,
 * startvägen svarar 503 och pollningen 404 (stängt, aldrig öppet).
 */
const JOBBTOKEN = /^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.([A-Za-z0-9_-]{43})$/i;

function jobbnyckel(hemlighet: string): Buffer {
  return Buffer.from(hkdfSync("sha256", hemlighet, "snajp-hjalp", "hjalpjobb-v1", 32));
}

function jobbsignatur(jobId: string, id: HjalpIdentitet, hemlighet: string): Buffer {
  return createHmac("sha256", jobbnyckel(hemlighet))
    .update(`hjalpjobb\n${jobId.toLowerCase()}\n${id.userId}\n${id.workspaceId}`)
    .digest();
}

/** Jobb-id:t som klienten får: `<uuid>.<signatur>`. Null utan hemlighet eller med ett id som inte är ett uuid. */
export function signeraJobb(jobId: unknown, id: HjalpIdentitet, hemlighet: string | undefined): string | null {
  if (!hemlighet || !arUuid(jobId)) return null;
  return `${jobId}.${jobbsignatur(jobId, id, hemlighet).toString("base64url")}`;
}

/** Ser värdet ut som en jobbtoken alls? Prövas före identiteten, så att skräp inte kostar en databasfråga. */
export function arJobbtoken(varde: unknown): varde is string {
  return typeof varde === "string" && JOBBTOKEN.test(varde);
}

/**
 * Backendens jobb-id ur klientens token, men bara om signaturen hör till den
 * här användaren och arbetsytan. Allt annat (fel användare, manipulerat id
 * eller signatur, ingen hemlighet) blir null.
 */
export function lasJobb(token: unknown, id: HjalpIdentitet, hemlighet: string | undefined): string | null {
  if (!hemlighet || typeof token !== "string") return null;
  const delar = JOBBTOKEN.exec(token);
  if (!delar) return null;
  const [, jobId, signatur] = delar;
  const given = Buffer.from(signatur, "base64url");
  const vantad = jobbsignatur(jobId, id, hemlighet);
  if (given.length !== vantad.length || !timingSafeEqual(given, vantad)) return null;
  // Sista tecknet bär två utfyllnadsbitar som avkodningen struntar i: bara
  // den kanoniska stavningen godtas, så att en token har exakt en form.
  if (given.toString("base64url") !== signatur) return null;
  // Signaturen räknas på gemener; samma stavning går vidare till backenden.
  return jobId.toLowerCase();
}

/**
 * Backendens svar på en ny fråga, med job_id utbytt mot den signerade
 * token. Ett svar utan ett giltigt job_id (fel, kvot, offline) går vidare
 * oförändrat; ett lyckat svar vars id inte går att signera blir 503 i stället
 * för ett naket id.
 */
export async function medSigneratJobb(
  svar: Response,
  id: HjalpIdentitet,
  hemlighet: string | undefined
): Promise<Response> {
  if (!svar.ok) return svar;
  const text = await svar.text();
  const kropp = falt(tolka(text));
  if (!("job_id" in kropp)) {
    return privat(new Response(text, { status: svar.status, headers: { "Content-Type": "application/json" } }));
  }
  const token = signeraJobb(kropp.job_id, id, hemlighet);
  if (!token) {
    console.error("snajp-hjalp: jobbet kunde inte signeras (AUTH_SECRET saknas eller job_id är inget uuid).");
    return hjalpAvSvar();
  }
  return privat(NextResponse.json({ ...kropp, job_id: token }, { status: svar.status }));
}

/** 503 med hjälpens av-text, när hjälpen inte går att använda säkert i miljön. */
export function hjalpAvSvar(): Response {
  return privat(
    NextResponse.json({ error: `${HJALP_AV.sv} / ${HJALP_AV.en}`, kod: "hjalp_av", ...HJALP_AV }, { status: 503 })
  );
}

/**
 * Vidare till backenden under hjälpens nyckel. Saknas nyckeln svarar vägen
 * 503 och ingenting skickas: ett fel som syns är bättre än ett svar ur fel
 * kunds kunskapsbas.
 */
export async function tillHjalpen(
  nyckel: string | undefined,
  path: string,
  init: RequestInit,
  userId: string
): Promise<Response> {
  if (!nyckel) {
    console.error("snajp-hjalp: SNAJP_KEY_SNAJP_HJALP är inte satt i den här miljön; hjälprutan svarar 503.");
    return hjalpAvSvar();
  }
  return proxyWithApiKey(path, init, nyckel, userId);
}
