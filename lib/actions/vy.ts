"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
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
 */
export async function bytVy(formData: FormData): Promise<void> {
  const admin = await getPlatformAdmin();
  if (!admin) {
    return;
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
      return;
    }

    (await cookies()).set(VY_COOKIE, kundVyVarde(slug), {
      path: "/",
      httpOnly: true,
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 30
    });

    // Loggen skrivs INNAN redirect. En redirect i Next kastar internt, och en
    // loggning efter den hade aldrig körts — vilket hade gett ett besök utan
    // spår, alltså precis det loggen finns för.
    //
    // Ett misslyckat skriv får inte blockera besöket: funktionen är
    // fail-closed på behörighet men vi vill inte att en full disk gör
    // supportytan oanvändbar. Felet syns i serverloggen i stället.
    try {
      await sqlAsUser(admin.userId, "select public.log_admin_impersonation($1)", [slug]);
    } catch (error) {
      console.error("log_admin_impersonation:", (error as Error).message);
    }

    redirect("/dashboard");
  }

  const till = val === "demo" ? "demo" : "admin";
  (await cookies()).set(VY_COOKIE, till, {
    path: "/",
    httpOnly: true,
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30
  });

  redirect(till === "demo" ? "/dashboard" : "/admin");
}
