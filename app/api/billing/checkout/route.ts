import { NextRequest, NextResponse } from "next/server";
import { getWorkspaceContext } from "@/lib/workspace";
import { requireSnajpTenant, SnajpTenantError } from "@/lib/snajp/tenant";
import {
  createCheckoutSession,
  PRICE_BY_PLAN,
  stripeIsConfigured,
  StripeError
} from "@/lib/billing/stripe";

// Startar ett köp. Kräver inloggning: nivån hör till organisationen, inte till
// en enskild användare.

export const runtime = "nodejs";
export const maxDuration = 60;

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export async function POST(request: NextRequest) {
  const context = await getWorkspaceContext();
  if (!context) {
    return NextResponse.json({ error: "Du måste vara inloggad." }, { status: 401 });
  }

  if (!stripeIsConfigured()) {
    return NextResponse.json(
      {
        error:
          "Betalning är inte aktiverad i den här miljön. Sätt STRIPE_SECRET_KEY " +
          "(testnyckel) och pris-id:na för nivåerna."
      },
      { status: 503 }
    );
  }

  let planId: string;
  try {
    planId = String((await request.json())?.plan ?? "");
  } catch {
    return NextResponse.json({ error: "Ogiltig begäran." }, { status: 400 });
  }

  const priceId = PRICE_BY_PLAN[planId];
  if (!priceId) {
    return NextResponse.json(
      {
        error: `Nivån "${planId}" saknar pris i den här miljön. Sätt STRIPE_PRICE_${planId.toUpperCase()}.`
      },
      { status: 400 }
    );
  }

  try {
    const tenant = await requireSnajpTenant();
    const session = await createCheckoutSession({
      priceId,
      workspaceId: context.workspace.id,
      tenantId: tenant.tenantId,
      customerEmail: context.user.email,
      successUrl: `${SITE_URL}/settings/billing?status=klar`,
      cancelUrl: `${SITE_URL}/settings/billing?status=avbruten`
    });
    return NextResponse.json({ url: session.url });
  } catch (error) {
    if (error instanceof StripeError || error instanceof SnajpTenantError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    throw error;
  }
}
