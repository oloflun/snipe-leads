import { NextResponse, type NextRequest } from "next/server";
import { FAKTURERINGSSIDA, kravBetalare, lasAbonnemang, publikBas } from "@/lib/billing/server";
import { StripeFel, prisForPaket, skapaCheckout, stripeAktiverad } from "@/lib/billing/stripe";
import { arPaketId } from "@/lib/pricing";

/**
 * Startar ett köp i Stripe Checkout för ett paket ur lib/pricing.ts.
 *
 * Paketet i sig ändras INTE här — det gör webhooken när Stripe bekräftat
 * betalningen. Annars hade en avbruten checkout gett paketet gratis.
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

  let paketId: string;
  try {
    paketId = String((await request.json())?.paket ?? "");
  } catch {
    return NextResponse.json({ error: "Ogiltig begäran." }, { status: 400 });
  }
  if (!arPaketId(paketId)) {
    return NextResponse.json({ error: `Okänt paket: ${paketId}.` }, { status: 400 });
  }

  const prisId = prisForPaket(paketId);
  if (!prisId) {
    return NextResponse.json(
      { error: `Paketet saknar pris i den här miljön (STRIPE_PRICE_${paketId.toUpperCase()}).` },
      { status: 400 }
    );
  }

  const bas = publikBas(request);
  const befintligt = await lasAbonnemang(vem.userId);
  try {
    const session = await skapaCheckout({
      prisId,
      paketId,
      workspaceId: vem.workspaceId,
      kundEpost: vem.epost,
      // En kund som redan finns hos Stripe ska inte få en andra kundpost —
      // då hade portalen visat hälften av fakturorna.
      stripeKund: befintligt?.stripe_customer_id ?? null,
      lyckadUrl: `${bas}${FAKTURERINGSSIDA}?betalning=klar`,
      avbrytUrl: `${bas}${FAKTURERINGSSIDA}?betalning=avbruten`
    });
    return NextResponse.json({ url: session.url });
  } catch (fel) {
    if (fel instanceof StripeFel) {
      return NextResponse.json({ error: fel.message }, { status: fel.status });
    }
    throw fel;
  }
}
