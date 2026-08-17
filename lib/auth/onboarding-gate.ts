import "server-only";

import { redirect } from "next/navigation";

import { auth } from "@/lib/auth";
import { isPlatformAdmin } from "@/lib/auth/admin";
import { hasCompletedOnboarding } from "@/lib/workspace";

/**
 * Onboardingdirigeringen — läst FÄRSKT ur databasen, aldrig ur sessionen.
 *
 * Statusen låg först som ett anspråk i sessions-JWT:n, och proxyn dirigerade
 * på den. Det gav en loop i drift: onboardingen skrev `business_contexts`,
 * skickade till /dashboard, och proxyn skickade tillbaka — eftersom cookien
 * fortfarande sa `onboarded: false`. `unstable_update` skrev inte om den.
 *
 * Lärdomen är formen, inte anropet som fattades: en token är en ÖGONBLICKSBILD,
 * signerad och cachad hos klienten. Identitet hör hemma där, eftersom den inte
 * ändras under sessionen. Föränderligt tillstånd gör det inte — det blir
 * inaktuellt utan att något felar, och felet visar sig som en dirigering som
 * inte går att förklara från koden man läser.
 *
 * Kostnaden är en fråga per skyddad sidladdning. Den fanns redan i det gamla
 * upplägget, där proxyn gjorde TVÅ. Skillnaden är att svaret nu är sant.
 */
export async function requireOnboarded(): Promise<void> {
  const session = await auth();
  const userId = session?.user?.id;
  if (!userId) {
    // Proxyn har redan skickat oinloggade till /login. Når vi hit ändå är det
    // rätt att inte gissa: /login är svaret, inte /onboarding.
    redirect("/login");
  }
  // Plattformsadmin behöver inte gå igenom kund-onboardingen — deras startsida
  // är adminvyn, inte business-context-formuläret. De kan onboarda senare om de
  // vill använda leads/support i Snajps eget bolag.
  if (await isPlatformAdmin(userId)) {
    return;
  }
  if (!(await hasCompletedOnboarding(userId))) {
    redirect("/onboarding");
  }
}

/** Motsatt riktning: den som är klar ska inte fastna på onboardingsidan. */
export async function redirectIfOnboarded(): Promise<void> {
  const session = await auth();
  const userId = session?.user?.id;
  if (userId && (await hasCompletedOnboarding(userId))) {
    redirect("/dashboard");
  }
}
