import { NextResponse } from "next/server";
import { getWorkspaceContext } from "@/lib/workspace";
import { requireSnajpTenant, SnajpTenantError } from "@/lib/snajp/tenant";
import { createPortalSession, stripeIsConfigured, StripeError } from "@/lib/billing/stripe";

// Stripes kundportal: uppgradera, nedgradera, byta kort, säga upp och se
// kvitton. Vi bygger inget eget för det — portalen är Stripes ansvar och
// hanterar moms, kvitton och regelverk åt oss.

export const runtime = "nodejs";
export const maxDuration = 60;

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
const SNAJP_SUPPORT_URL = process.env.SNAJP_SUPPORT_URL ?? "http://127.0.0.1:8000";

export async function POST() {
  const context = await getWorkspaceContext();
  if (!context) {
    return NextResponse.json({ error: "Du måste vara inloggad." }, { status: 401 });
  }

  if (!stripeIsConfigured()) {
    return NextResponse.json(
      { error: "Betalning är inte aktiverad i den här miljön (STRIPE_SECRET_KEY saknas)." },
      { status: 503 }
    );
  }

  try {
    const tenant = await requireSnajpTenant();

    // Kundid:t ligger hos backenden, satt av webhooken vid första köpet.
    const response = await fetch(`${SNAJP_SUPPORT_URL}/api/billing/subscription`, {
      headers: { "X-API-Key": tenant.apiKey },
      cache: "no-store"
    });
    if (!response.ok) {
      return NextResponse.json(
        { error: "Kunde inte läsa abonnemanget." },
        { status: 502 }
      );
    }
    const subscription = await response.json();
    const customerId = subscription?.stripe_customer_id;

    if (!customerId) {
      return NextResponse.json(
        {
          error:
            "Ni har inget abonnemang att hantera ännu. Välj en nivå först, så " +
            "skapas ert kundkonto hos Stripe."
        },
        { status: 400 }
      );
    }

    const portal = await createPortalSession({
      customerId,
      returnUrl: `${SITE_URL}/settings/billing`
    });
    return NextResponse.json({ url: portal.url });
  } catch (error) {
    if (error instanceof StripeError || error instanceof SnajpTenantError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    throw error;
  }
}
