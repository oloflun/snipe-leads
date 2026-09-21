/**
 * Tunn Stripe-klient mot deras REST-API — Checkout, kundportal och
 * webhooksignaturen.
 *
 * Porterad från grenen feature/snajp-multitenant-saas (2026-08-14) med två
 * ändringar: priserna hör till PAKETEN i lib/pricing.ts i stället för grenens
 * kvotnivåer (Bas/Plus/Pro), och `server-only` saknas med flit — filen
 * importeras av node:test, och ingen klientkomponent importerar den (nyckeln
 * läses ur process.env och hade ändå varit tom i en klientbundle).
 *
 * Utan npm-paketet `stripe`: tre anrop och en signaturkontroll, och ett
 * beroende till hade inte gjort något av det säkrare.
 *
 * Saknas nycklarna svarar routerna 503 med förklaring, och faktureringssidan
 * visar ingen Stripe-yta alls. Ingenting kraschar av att växeln är avstängd.
 */

import { createHmac, timingSafeEqual } from "node:crypto";
// `import type` raderas vid typstrippningen, så node:test behöver inte kunna
// lösa aliaset.
import type { Paket } from "@/lib/pricing";

const STRIPE_API = "https://api.stripe.com/v1";

function hemlighet(): string {
  return process.env.STRIPE_SECRET_KEY ?? "";
}

/**
 * Paket-id → Stripe-pris. Stripe äger BELOPPET, lib/pricing.ts äger vad
 * paketet innehåller och vad prislistan säger, och den här tabellen binder
 * ihop dem. Ett nytt paket: lägg till i lib/pricing.ts och sätt
 * STRIPE_PRICE_<ID> här.
 *
 * Läses vid anrop, inte vid modulladdning: en miljövariabel som sätts efter
 * uppstart (och testerna, som sätter dem själva) ska synas.
 */
export function prisForPaket(paketId: Paket["id"]): string {
  const karta: Record<Paket["id"], string | undefined> = {
    support: process.env.STRIPE_PRICE_SUPPORT,
    leads: process.env.STRIPE_PRICE_LEADS,
    duo: process.env.STRIPE_PRICE_DUO,
    trio: process.env.STRIPE_PRICE_TRIO,
    bookkeeping: process.env.STRIPE_PRICE_BOOKKEEPING
  };
  return karta[paketId] ?? "";
}

const PAKET_IDN: Paket["id"][] = ["support", "leads", "duo", "trio", "bookkeeping"];

/** Omvänt uppslag — webhooken får ett pris och behöver veta vilket paket det är. */
export function paketForPris(prisId: string | null | undefined): Paket["id"] | null {
  if (!prisId) return null;
  return PAKET_IDN.find((id) => prisForPaket(id) === prisId) ?? null;
}

export function stripeAktiverad(): boolean {
  return Boolean(hemlighet());
}

export function arTestlage(): boolean {
  return hemlighet().startsWith("sk_test_");
}

export class StripeFel extends Error {
  // Vanligt fält, inte parameteregenskap: node:test kör filen med ren
  // typstrippning, och den stödjer inte `constructor(readonly status …)`.
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "StripeFel";
    this.status = status;
  }
}

/**
 * Stripe tar form-encoded data, inte JSON. Nästlade fält skrivs som
 * `foo[bar]`, och arrayer som `foo[0][bar]`.
 */
export function formkoda(data: Record<string, unknown>, prefix = ""): string[] {
  const delar: string[] = [];
  for (const [nyckel, varde] of Object.entries(data)) {
    if (varde === undefined || varde === null) continue;
    const falt = prefix ? `${prefix}[${nyckel}]` : nyckel;
    if (Array.isArray(varde)) {
      varde.forEach((post, index) => {
        if (post && typeof post === "object") {
          delar.push(...formkoda(post as Record<string, unknown>, `${falt}[${index}]`));
        } else {
          delar.push(`${encodeURIComponent(`${falt}[${index}]`)}=${encodeURIComponent(String(post))}`);
        }
      });
    } else if (typeof varde === "object") {
      delar.push(...formkoda(varde as Record<string, unknown>, falt));
    } else {
      delar.push(`${encodeURIComponent(falt)}=${encodeURIComponent(String(varde))}`);
    }
  }
  return delar;
}

async function stripeAnrop<T>(sokvag: string, kropp: Record<string, unknown>): Promise<T> {
  if (!stripeAktiverad()) {
    throw new StripeFel(
      "Kortbetalning är inte aktiverad i den här miljön (STRIPE_SECRET_KEY saknas).",
      503
    );
  }

  const svar = await fetch(`${STRIPE_API}${sokvag}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${hemlighet()}`,
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: formkoda(kropp).join("&"),
    cache: "no-store"
  });

  const data = await svar.json().catch(() => null);
  if (!svar.ok) {
    throw new StripeFel(data?.error?.message ?? "Stripe svarade med ett fel.", 502);
  }
  return data as T;
}

export type Session = { id: string; url: string };

export async function skapaCheckout(opt: {
  prisId: string;
  workspaceId: string;
  paketId: Paket["id"];
  kundEpost?: string | null;
  stripeKund?: string | null;
  lyckadUrl: string;
  avbrytUrl: string;
}): Promise<Session> {
  const metadata = { workspace_id: opt.workspaceId, paket_id: opt.paketId };
  return stripeAnrop<Session>("/checkout/sessions", {
    mode: "subscription",
    line_items: [{ price: opt.prisId, quantity: 1 }],
    success_url: opt.lyckadUrl,
    cancel_url: opt.avbrytUrl,
    allow_promotion_codes: true,
    // Moms och fakturaadress: Stripe samlar in det som krävs för en svensk
    // B2B-faktura, i stället för att vi bygger ett eget formulär för det.
    billing_address_collection: "required",
    tax_id_collection: { enabled: true },
    ...(opt.stripeKund
      ? { customer: opt.stripeKund }
      : opt.kundEpost
        ? { customer_email: opt.kundEpost }
        : {}),
    // Metadata är hur webhooken hittar tillbaka till rätt arbetsyta. Sätts på
    // BÅDE sessionen och prenumerationen: sessionen finns bara vid köpet,
    // medan senare händelser (förnyelse, uppsägning) bara bär prenumerationen.
    metadata,
    subscription_data: { metadata }
  });
}

export async function skapaPortal(opt: { stripeKund: string; returUrl: string }): Promise<Session> {
  return stripeAnrop<Session>("/billing_portal/sessions", {
    customer: opt.stripeKund,
    return_url: opt.returUrl
  });
}

/**
 * Verifierar Stripes signatur (`Stripe-Signature`).
 *
 * Utan den kan vem som helst posta en påhittad "betalning genomförd" till
 * webhooken och ge sig själv ett paket. Kontrollen görs mot RÅ body — parsas
 * JSON först ändras bytes och signaturen stämmer aldrig.
 *
 * `hemligheten` och `nu` är parametrar för testernas skull; routen skickar
 * miljövariabeln och klockan.
 */
export function verifieraSignatur(
  raKropp: string,
  signaturHuvud: string | null,
  opt: { hemligheten?: string; toleransSekunder?: number; nu?: number } = {}
): { giltig: boolean; orsak?: string } {
  const webhookHemlighet = opt.hemligheten ?? process.env.STRIPE_WEBHOOK_SECRET ?? "";
  const tolerans = opt.toleransSekunder ?? 300;
  const nu = opt.nu ?? Date.now() / 1000;

  if (!webhookHemlighet) {
    return { giltig: false, orsak: "STRIPE_WEBHOOK_SECRET saknas i miljön." };
  }
  if (!signaturHuvud) {
    return { giltig: false, orsak: "Stripe-Signature-huvudet saknas." };
  }

  // Huvudet kan bära flera v1 (under en nyckelrotation). Varje giltig räcker.
  let tid = "";
  const signaturer: string[] = [];
  for (const bit of signaturHuvud.split(",")) {
    const [nyckel, ...rest] = bit.split("=");
    const varde = rest.join("=");
    if (nyckel.trim() === "t") tid = varde;
    if (nyckel.trim() === "v1") signaturer.push(varde);
  }
  if (!tid || signaturer.length === 0) {
    return { giltig: false, orsak: "Signaturhuvudet har oväntat format." };
  }

  // Replayskydd: en avlyssnad men giltig händelse ska inte kunna spelas upp igen.
  const alder = Math.abs(nu - Number(tid));
  if (!Number.isFinite(alder) || alder > tolerans) {
    return { giltig: false, orsak: "Signaturen är för gammal." };
  }

  const vantad = Buffer.from(
    createHmac("sha256", webhookHemlighet).update(`${tid}.${raKropp}`, "utf8").digest("hex"),
    "utf8"
  );
  const traff = signaturer.some((sig) => {
    const given = Buffer.from(sig, "utf8");
    return given.length === vantad.length && timingSafeEqual(given, vantad);
  });
  return traff ? { giltig: true } : { giltig: false, orsak: "Signaturen stämmer inte." };
}
