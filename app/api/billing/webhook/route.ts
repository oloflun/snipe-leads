import { NextRequest, NextResponse } from "next/server";
import { planForPrice, verifyWebhookSignature } from "@/lib/billing/stripe";

// Stripes webhook. Håller tenantens abonnemangsstatus synkad med verkligheten.
//
// Två saker är kritiska här:
//
// 1. SIGNATUREN VERIFIERAS FÖRST, mot rå body. Utan det kan vem som helst posta
//    "betalning genomförd" till den här adressen och uppgradera sig gratis.
//    Endpointen är per definition öppen — signaturen ÄR autentiseringen.
// 2. Ingen kundnyckel används. Backendens abonnemangssynk kräver master-nyckeln,
//    så en kund aldrig kan sätta sin egen nivå.

export const runtime = "nodejs";
export const maxDuration = 60;

const SNAJP_SUPPORT_URL = process.env.SNAJP_SUPPORT_URL ?? "http://127.0.0.1:8000";
const MASTER_KEY = process.env.SNAJP_MASTER_API_KEY ?? "";

type StripeEvent = {
  id: string;
  type: string;
  data: { object: Record<string, any> };
};

function isoOrNull(seconds: unknown): string | null {
  return typeof seconds === "number" ? new Date(seconds * 1000).toISOString() : null;
}

async function syncToBackend(payload: Record<string, unknown>): Promise<boolean> {
  if (!MASTER_KEY) {
    console.error("[stripe-webhook] SNAJP_MASTER_API_KEY saknas — kan inte synka.");
    return false;
  }
  const response = await fetch(`${SNAJP_SUPPORT_URL}/api/billing/subscription`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-API-Key": MASTER_KEY },
    body: JSON.stringify(payload),
    cache: "no-store"
  });
  if (!response.ok) {
    console.error(`[stripe-webhook] Backenden svarade ${response.status}.`);
  }
  return response.ok;
}

/** Prenumerationen är sanningen för nivå, status och period. */
async function handleSubscription(subscription: Record<string, any>): Promise<boolean> {
  const priceId = subscription.items?.data?.[0]?.price?.id;
  const planId = planForPrice(priceId);

  return syncToBackend({
    tenant_id: subscription.metadata?.tenant_id ?? null,
    stripe_customer_id:
      typeof subscription.customer === "string" ? subscription.customer : null,
    stripe_subscription_id: subscription.id,
    // Okänt pris ⇒ lämna nivån orörd hellre än att gissa fel och ge fel kvot.
    plan_id: planId,
    status: subscription.status,
    current_period_start: isoOrNull(subscription.current_period_start),
    current_period_end: isoOrNull(subscription.current_period_end),
    cancel_at_period_end: Boolean(subscription.cancel_at_period_end)
  });
}

export async function POST(request: NextRequest) {
  // Rå text, inte request.json() — signaturen räknas på exakta bytes.
  const rawBody = await request.text();
  const verification = verifyWebhookSignature(
    rawBody,
    request.headers.get("stripe-signature")
  );

  if (!verification.valid) {
    console.warn(`[stripe-webhook] Avvisad: ${verification.reason}`);
    return NextResponse.json({ error: "Ogiltig signatur." }, { status: 400 });
  }

  let event: StripeEvent;
  try {
    event = JSON.parse(rawBody);
  } catch {
    return NextResponse.json({ error: "Ogiltig JSON." }, { status: 400 });
  }

  const object = event.data?.object ?? {};
  let handled = true;

  switch (event.type) {
    case "checkout.session.completed": {
      // Kunden finns nu hos Stripe. Koppla kundid:t till arbetsytan direkt, så
      // portalen fungerar även innan första subscription-händelsen kommit.
      handled = await syncToBackend({
        tenant_id: object.metadata?.tenant_id ?? null,
        stripe_customer_id: typeof object.customer === "string" ? object.customer : null,
        stripe_subscription_id:
          typeof object.subscription === "string" ? object.subscription : null,
        status: "active"
      });
      break;
    }

    case "customer.subscription.created":
    case "customer.subscription.updated":
    case "customer.subscription.deleted": {
      handled = await handleSubscription({
        ...object,
        // Raderad prenumeration rapporteras som canceled oavsett vad Stripe
        // hann sätta, så kvoten faller tillbaka till gratisnivån.
        status: event.type === "customer.subscription.deleted" ? "canceled" : object.status
      });
      break;
    }

    case "invoice.payment_failed": {
      handled = await syncToBackend({
        stripe_customer_id: typeof object.customer === "string" ? object.customer : null,
        status: "past_due"
      });
      break;
    }

    default:
      // Okända händelsetyper kvitteras med 200 — annars fortsätter Stripe att
      // skicka om dem i dagar.
      break;
  }

  // 200 även när synken misslyckades vore fel: då slutar Stripe försöka igen och
  // vi står med ett abonnemang som aldrig blev synkat.
  if (!handled) {
    return NextResponse.json({ received: false }, { status: 500 });
  }
  return NextResponse.json({ received: true });
}
