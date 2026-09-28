"use client";

import { Sidhuvud } from "@/components/ui";
import { a } from "@/lib/admin/sprak";
import { useLocale } from "@/lib/i18n";

/**
 * Rubriken för Kunder & Data.
 *
 * Egen klientkomponent av ett enda skäl: sidan är en server-komponent (den
 * hämtar), och rubriken måste ändå byta språk med EN/SV-knappen. Att flytta
 * hela sidan till klienten för en rubrik hade betytt att hämtningen också
 * flyttade dit.
 *
 * Ingressen under rubriken och fotnoten längst ned (`Kundfotnot`) togs bort
 * 2026-09-27 (F-016): båda beskrev sidan, vad som stod på den och vad som
 * inte gjorde det. Varför intäkter saknas här står i app/admin/kunder/page.tsx.
 */
export function Kundrubrik() {
  const { locale } = useLocale();
  return <Sidhuvud title={a("kunderRubrik", locale)} />;
}
