import { NextResponse, type NextRequest } from "next/server";
import { FAKTURERINGSSIDA, kravBetalare, lasAbonnemang, publikBas } from "@/lib/billing/server";
import { StripeFel, skapaPortal, stripeAktiverad } from "@/lib/billing/stripe";

/**
 * Stripes kundportal: byta kort, se och ladda ned fakturor, säga upp. Vi
 * bygger inget eget för det — portalen hanterar moms, kvitton och regelverk.
 */

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: NextRequest) {
  const vem = await kravBetalare();
  if (!vem.ok) return NextResponse.json({ error: vem.fel }, { status: vem.status });

  if (!stripeAktiverad()) {
    return NextResponse.json(
      { error: "Kortbetalning är inte aktiverad i den här miljön." },
      { status: 503 }
    );
  }

  const abonnemang = await lasAbonnemang(vem.userId);
  if (!abonnemang?.stripe_customer_id) {
    return NextResponse.json(
      { error: "Ni har inget kortabonnemang att hantera ännu. Välj att betala med kort först." },
      { status: 400 }
    );
  }

  try {
    const portal = await skapaPortal({
      stripeKund: abonnemang.stripe_customer_id,
      returUrl: `${publikBas(request)}${FAKTURERINGSSIDA}`
    });
    return NextResponse.json({ url: portal.url });
  } catch (fel) {
    if (fel instanceof StripeFel) {
      return NextResponse.json({ error: fel.message }, { status: fel.status });
    }
    throw fel;
  }
}
