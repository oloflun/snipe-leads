"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getPlatformAdmin } from "@/lib/auth/admin";
import { VY_COOKIE } from "@/lib/vy";

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
  if (!(await getPlatformAdmin())) {
    return;
  }

  const till = formData.get("vy") === "demo" ? "demo" : "admin";
  (await cookies()).set(VY_COOKIE, till, {
    path: "/",
    httpOnly: true,
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30
  });

  redirect(till === "demo" ? "/dashboard" : "/admin");
}
