"use server";

import { cookies } from "next/headers";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { sqlAsUser } from "@/lib/db";
import { VY_COOKIE, kundVyVarde } from "@/lib/vy";

/**
 * Byter mellan den skarpa adminytan och demovyn.
 *
 * Server action och inte en klientnavigering: cookien måste vara satt INNAN
 * nästa sidas server-komponenter kör, annars renderas den första sidan i det
 * gamla läget och rättar sig först vid nästa klick. Det ser ut som att knappen
 * missade.
 *
 * Grinden upprepas här trots att `aktivVy()` också har den. Skälet är att det
 * här är en SKRIVNING: utan kontrollen kunde vem som helst sätta cookien via
 * ett formulär, och även om läsvägen ändå hade svarat `admin` vore det en
 * spärr som bara finns på ett ställe.
 *
 * Ingen redirect() sedan kunddemon 2026-11-24 (INV-SEC-014): en server
 * action-redirect är en mjuk navigering, och fliken behöll då förra vyns state
 * och routercache. Adressen går tillbaka till klienten, som säger till de andra
 * flikarna och öppnar den med window.location.replace
 * (DashboardContext.tsx:bytVyOchOppna). `url: null` betyder att inget bytts.
 */
export async function bytVy(formData: FormData): Promise<{ url: string | null }> {
  const admin = await getPlatformAdmin();
  if (!admin) {
    return { url: null };
  }

  const val = String(formData.get("vy") ?? "");

  /**
   * Kundbesök: `kund:<slug>`.
   *
   * Sluggen kommer från ett formulärfält, alltså från klienten, och används
   * BARA som cookievärde här. Den blir aldrig en databasfråga utan att
   * `tenant_api_key_for_admin()` (migration 042) först gjort om
   * admin-kontrollen i databasen — se lib/snajp/tenant.ts. Att skriva en
   * påhittad slug i cookien ger därför en arbetsyta utan nyckel, inte någon
   * annans data.
   */
  if (val.startsWith("kund:")) {
    const slug = val.slice("kund:".length);
    if (!/^[a-z0-9][a-z0-9-]{0,62}$/.test(slug)) {
      return { url: null };
    }

    (await cookies()).set(VY_COOKIE, kundVyVarde(slug), {
      path: "/",
      httpOnly: true,
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 30
    });

    // Loggen skrivs innan adressen lämnas tillbaka, så att inget besök blir
    // utan spår, alltså precis det loggen finns för.
    //
    // Ett misslyckat skriv får inte blockera besöket: funktionen är
    // fail-closed på behörighet men vi vill inte att en full disk gör
    // supportytan oanvändbar. Felet syns i serverloggen i stället.
    try {
      await sqlAsUser(admin.userId, "select public.log_admin_impersonation($1)", [slug]);
    } catch (error) {
      console.error("log_admin_impersonation:", (error as Error).message);
    }

    return { url: "/dashboard" };
  }

  const till = val === "demo" ? "demo" : "admin";
  (await cookies()).set(VY_COOKIE, till, {
    path: "/",
    httpOnly: true,
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30
  });

  return { url: till === "demo" ? "/dashboard" : "/admin" };
}
