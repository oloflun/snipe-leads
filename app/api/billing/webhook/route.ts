import { NextResponse, type NextRequest } from "next/server";
import { hasDatabase, sql } from "@/lib/db";
import { arTestlage, paketForPris, verifieraSignatur } from "@/lib/billing/stripe";
import { PRODUKTER_FOR_PAKET, arPaketId } from "@/lib/pricing";

/**
 * Stripes webhook. Håller billing_subscriptions (migration 075) synkad med
 * Stripe.
 *
 * 1. SIGNATUREN VERIFIERAS FÖRST, mot rå body. Endpointen är per definition
 *    öppen — signaturen ÄR autentiseringen. Utan den kan vem som helst posta
 *    "betalning genomförd" och ge sig själv ett paket.
 * 2. Bara ett AKTIVT köp ändrar vad arbetsytan har (workspaces.products).
 *    Uppsägning och misslyckat kortdrag speglas som status och inget mer —
 *    avstängning är ett manuellt handgrepp i admin (se migration 075).
 * 3. 500 när synken misslyckas, aldrig 200: då slutar Stripe försöka igen och
 *    betalningen blir aldrig speglad.
 */

export const runtime = "nodejs";
export const maxDuration = 60;

type StripeHandelse = { id: string; type: string; data: { object: Record<string, any> } };

function isoEllerNull(sekunder: unknown): string | null {
  return typeof sekunder === "number" ? new Date(sekunder * 1000).toISOString() : null;
}

function strang(varde: unknown): string | null {
  return typeof varde === "string" && varde ? varde : null;
}

async function synka(p: {
  workspace: string | null;
  kund: string | null;
  prenumeration: string | null;
  paket: string | null;
  status: string;
  periodSlut?: string | null;
  uppsagd?: boolean;
}): Promise<void> {
  const paket = p.paket && arPaketId(p.paket) ? p.paket : null;
  // Produkterna följer bara med ett aktivt köp av ett KÄNT paket. Okänt pris
  // lämnar entitlementen orörd — hellre det än att gissa och ge fel produkter.
  const produkter =
    paket && (p.status === "active" || p.status === "trialing") ? PRODUKTER_FOR_PAKET[paket] : null;

  const rader = await sql<{ stripe_synka_abonnemang: string | null }>(
    `select public.stripe_synka_abonnemang($1::uuid, $2, $3, $4, $5, $6::timestamptz, $7, $8, $9::text[])`,
    [
      p.workspace,
      p.kund,
      p.prenumeration,
      paket,
      p.status,
      p.periodSlut ?? null,
      p.uppsagd ?? false,
      arTestlage(),
      produkter
    ]
  );
  const arbetsyta = rader[0]?.stripe_synka_abonnemang ?? null;
  if (!arbetsyta) {
    // Ingen arbetsyta att knyta händelsen till. Loggas men kvitteras: att be
    // Stripe försöka igen ändrar inte att metadata saknas.
    console.warn(`[stripe-webhook] Ingen arbetsyta för kund ${p.kund ?? "?"} — händelsen speglades inte.`);
  }
}

export async function POST(request: NextRequest) {
  // Rå text, inte request.json() — signaturen räknas på exakta bytes.
  const raKropp = await request.text();
  const kontroll = verifieraSignatur(raKropp, request.headers.get("stripe-signature"));
  if (!kontroll.giltig) {
    console.warn(`[stripe-webhook] Avvisad: ${kontroll.orsak}`);
    return NextResponse.json({ error: "Ogiltig signatur." }, { status: 400 });
  }

  if (!hasDatabase()) {
    return NextResponse.json({ error: "Databasen saknas i miljön." }, { status: 503 });
  }

  let handelse: StripeHandelse;
  try {
    handelse = JSON.parse(raKropp);
  } catch {
    return NextResponse.json({ error: "Ogiltig JSON." }, { status: 400 });
  }

  const objekt = handelse.data?.object ?? {};
  try {
    switch (handelse.type) {
      case "checkout.session.completed": {
        // Kunden finns nu hos Stripe. Knyt kund-id:t till arbetsytan direkt,
        // så portalen fungerar innan första prenumerationshändelsen kommit.
        // Status 'incomplete' och inga produkter: köpet räknas först när
        // prenumerationen själv säger active (händelsen nedan).
        await synka({
          workspace: strang(objekt.metadata?.workspace_id),
          kund: strang(objekt.customer),
          prenumeration: strang(objekt.subscription),
          paket: strang(objekt.metadata?.paket_id),
          status: "incomplete"
        });
        break;
      }

      case "customer.subscription.created":
      case "customer.subscription.updated":
      case "customer.subscription.deleted": {
        const prisId = objekt.items?.data?.[0]?.price?.id;
        await synka({
          workspace: strang(objekt.metadata?.workspace_id),
          kund: strang(objekt.customer),
          prenumeration: strang(objekt.id),
          // Priset är sanningen om paketet; metadata är reserven om priset
          // inte finns i miljöns tabell (t.ex. ett nyss ändrat pris-id).
          paket: paketForPris(prisId) ?? strang(objekt.metadata?.paket_id),
          status: handelse.type === "customer.subscription.deleted" ? "canceled" : String(objekt.status),
          periodSlut: isoEllerNull(
            objekt.current_period_end ?? objekt.items?.data?.[0]?.current_period_end
          ),
          uppsagd: Boolean(objekt.cancel_at_period_end)
        });
        break;
      }

      case "invoice.payment_failed": {
        await synka({
          workspace: null,
          kund: strang(objekt.customer),
          prenumeration: strang(objekt.subscription),
          paket: null,
          status: "past_due"
        });
        break;
      }

      default:
        // Okända händelsetyper kvitteras — annars skickar Stripe om dem i dagar.
        break;
    }
  } catch (fel) {
    console.error("[stripe-webhook] Synken misslyckades:", (fel as Error).message);
    return NextResponse.json({ received: false }, { status: 500 });
  }

  return NextResponse.json({ received: true });
}
