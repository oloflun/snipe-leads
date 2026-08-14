// SERVER-ONLY. Tunn Stripe-klient mot deras REST-API.
//
// Medvetet utan npm-paketet `stripe`: vi behöver tre anrop och en
// signaturkontroll, och ett beroende till hade inte gjort något av det säkrare.
//
// Allt körs i TESTLÄGE tills riktiga nycklar sätts. Saknas nycklarna svarar
// endpointsen 503 med förklaring i stället för att krascha — samma
// graceful degradation som resten av tjänsten.

import { createHmac, timingSafeEqual } from "node:crypto";

const STRIPE_API = "https://api.stripe.com/v1";

export const STRIPE_SECRET_KEY = process.env.STRIPE_SECRET_KEY ?? "";
export const STRIPE_WEBHOOK_SECRET = process.env.STRIPE_WEBHOOK_SECRET ?? "";

/**
 * Plan-id (samma som app/billing/plans.py) → Stripe-pris.
 *
 * Backenden äger TAKEN, Stripe äger PRISET, och den här tabellen binder ihop
 * dem. Att lägga till en nivå: lägg till i plans.py och sätt motsvarande
 * miljövariabel här.
 */
export const PRICE_BY_PLAN: Record<string, string> = {
  bas: process.env.STRIPE_PRICE_BAS ?? "",
  plus: process.env.STRIPE_PRICE_PLUS ?? "",
  pro: process.env.STRIPE_PRICE_PRO ?? ""
};

/** Omvänt uppslag — webhooken får ett pris och behöver veta vilken nivå det är. */
export function planForPrice(priceId: string | null | undefined): string | null {
  if (!priceId) return null;
  const found = Object.entries(PRICE_BY_PLAN).find(([, id]) => id && id === priceId);
  return found ? found[0] : null;
}

export function stripeIsConfigured(): boolean {
  return Boolean(STRIPE_SECRET_KEY);
}

export function isTestMode(): boolean {
  return STRIPE_SECRET_KEY.startsWith("sk_test_");
}

export class StripeError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
    this.name = "StripeError";
  }
}

/**
 * Stripe tar form-encoded data, inte JSON. Nästlade fält skrivs som
 * `foo[bar]`, och arrayer som `foo[0][bar]`.
 */
function encode(data: Record<string, unknown>, prefix = ""): string[] {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(data)) {
    if (value === undefined || value === null) continue;
    const field = prefix ? `${prefix}[${key}]` : key;
    if (Array.isArray(value)) {
      value.forEach((item, index) => {
        if (item && typeof item === "object") {
          parts.push(...encode(item as Record<string, unknown>, `${field}[${index}]`));
        } else {
          parts.push(`${encodeURIComponent(`${field}[${index}]`)}=${encodeURIComponent(String(item))}`);
        }
      });
    } else if (typeof value === "object") {
      parts.push(...encode(value as Record<string, unknown>, field));
    } else {
      parts.push(`${encodeURIComponent(field)}=${encodeURIComponent(String(value))}`);
    }
  }
  return parts;
}

async function stripeRequest<T>(path: string, body: Record<string, unknown>): Promise<T> {
  if (!stripeIsConfigured()) {
    throw new StripeError(
      "Betalning är inte konfigurerad i den här miljön (STRIPE_SECRET_KEY saknas).",
      503
    );
  }

  const response = await fetch(`${STRIPE_API}${path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${STRIPE_SECRET_KEY}`,
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: encode(body).join("&"),
    cache: "no-store"
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new StripeError(payload?.error?.message ?? "Stripe svarade med ett fel.", 502);
  }
  return payload as T;
}

export type CheckoutSession = { id: string; url: string };
export type PortalSession = { id: string; url: string };

export async function createCheckoutSession(options: {
  priceId: string;
  workspaceId: string;
  tenantId: string;
  customerEmail?: string | null;
  customerId?: string | null;
  successUrl: string;
  cancelUrl: string;
}): Promise<CheckoutSession> {
  return stripeRequest<CheckoutSession>("/checkout/sessions", {
    mode: "subscription",
    line_items: [{ price: options.priceId, quantity: 1 }],
    success_url: options.successUrl,
    cancel_url: options.cancelUrl,
    // Kunden får inte byta pris i checkout — nivån väljs i vårt UI.
    allow_promotion_codes: true,
    ...(options.customerId
      ? { customer: options.customerId }
      : options.customerEmail
        ? { customer_email: options.customerEmail }
        : {}),
    // Metadata är hur webhooken hittar tillbaka till rätt arbetsyta. Sätts på
    // BÅDE sessionen och prenumerationen: sessionen finns bara vid köpet,
    // medan senare händelser (förnyelse, uppsägning) bara bär prenumerationen.
    metadata: { workspace_id: options.workspaceId, tenant_id: options.tenantId },
    subscription_data: {
      metadata: { workspace_id: options.workspaceId, tenant_id: options.tenantId }
    }
  });
}

export async function createPortalSession(options: {
  customerId: string;
  returnUrl: string;
}): Promise<PortalSession> {
  return stripeRequest<PortalSession>("/billing_portal/sessions", {
    customer: options.customerId,
    return_url: options.returnUrl
  });
}

/**
 * Verifierar Stripes signatur (`Stripe-Signature`).
 *
 * Utan detta kan vem som helst posta en påhittad "betalning genomförd" till
 * webhooken och uppgradera sig gratis. Kontrollen görs mot RÅ body — parsas
 * JSON först ändras bytes och signaturen stämmer aldrig.
 */
export function verifyWebhookSignature(
  rawBody: string,
  signatureHeader: string | null,
  toleranceSeconds = 300
): { valid: boolean; reason?: string } {
  if (!STRIPE_WEBHOOK_SECRET) {
    return { valid: false, reason: "STRIPE_WEBHOOK_SECRET saknas i miljön." };
  }
  if (!signatureHeader) {
    return { valid: false, reason: "Stripe-Signature-huvudet saknas." };
  }

  const parts = Object.fromEntries(
    signatureHeader.split(",").map((piece) => {
      const [key, ...rest] = piece.split("=");
      return [key.trim(), rest.join("=")];
    })
  );

  const timestamp = parts.t;
  const signature = parts.v1;
  if (!timestamp || !signature) {
    return { valid: false, reason: "Signaturhuvudet har oväntat format." };
  }

  // Replayskydd: en avlyssnad men giltig händelse ska inte kunna spelas upp igen.
  const age = Math.abs(Date.now() / 1000 - Number(timestamp));
  if (!Number.isFinite(age) || age > toleranceSeconds) {
    return { valid: false, reason: "Signaturen är för gammal." };
  }

  const expected = createHmac("sha256", STRIPE_WEBHOOK_SECRET)
    .update(`${timestamp}.${rawBody}`, "utf8")
    .digest("hex");

  const a = Buffer.from(expected, "utf8");
  const b = Buffer.from(signature, "utf8");
  if (a.length !== b.length || !timingSafeEqual(a, b)) {
    return { valid: false, reason: "Signaturen stämmer inte." };
  }
  return { valid: true };
}
