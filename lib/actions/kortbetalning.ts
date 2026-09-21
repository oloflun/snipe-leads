"use server";

import { lasAbonnemang, type Abonnemang } from "@/lib/billing/server";
import { arTestlage, prisForPaket, stripeAktiverad } from "@/lib/billing/stripe";
import { arPaketId } from "@/lib/pricing";
import { getWorkspaceContext } from "@/lib/workspace";

/**
 * Faktureringssidans läge för kortbetalning via Stripe.
 *
 * Server action och inte en läsning i komponenten: STRIPE_SECRET_KEY finns
 * bara på servern, och en `process.env`-läsning i en "use client"-fil blir
 * tyst tom i klientbundlen (samma fälla som LeadsView-bannern hade).
 */

export type Kortbetalningslage = {
  aktiverad: boolean;
  testlage: boolean;
  /** Om just det aktiva paketet har ett pris-id i miljön. */
  paketHarPris: boolean;
  abonnemang: Abonnemang | null;
};

export async function hamtaKortbetalning(paketId: string | undefined): Promise<Kortbetalningslage> {
  const avstangd: Kortbetalningslage = {
    aktiverad: false,
    testlage: false,
    paketHarPris: false,
    abonnemang: null
  };
  if (!stripeAktiverad()) return avstangd;

  const context = await getWorkspaceContext();
  if (!context) return avstangd;

  return {
    aktiverad: true,
    testlage: arTestlage(),
    paketHarPris: Boolean(paketId && arPaketId(paketId) && prisForPaket(paketId)),
    abonnemang: await lasAbonnemang(context.user.id)
  };
}
