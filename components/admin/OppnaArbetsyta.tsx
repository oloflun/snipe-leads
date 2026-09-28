"use client";

import { Eye } from "lucide-react";
import { btnLiten, btnSecondary } from "@/components/ui";
import { bytVy } from "@/lib/actions/vy";
import { useLocale } from "@/lib/i18n";

/**
 * "Öppna arbetsytan" — går in i en kunds vy i admin-läge.
 *
 * Formulär och server action, inte en länk med en query-parameter. Två skäl,
 * och båda har kostat tid i den här kodbasen förut:
 *
 *  * Cookien måste vara satt INNAN nästa sidas server-komponenter kör. En
 *    klientnavigering renderar den första sidan i det gamla läget och rättar
 *    sig först vid nästa klick — det ser ut som att knappen missade.
 *  * En query-parameter måste bäras vidare av varje länk i appen, och den länk
 *    som glöms tar användaren tillbaka till fel yta mitt i ett flöde. Samma
 *    resonemang som `useArbetsvag()` finns för.
 *
 * Knappen fungerar utan JavaScript, precis som VyVaxel och utloggningen.
 */
export function OppnaArbetsyta({ slug, namn }: Readonly<{ slug: string; namn: string }>) {
  const { text } = useLocale();
  return (
    <form action={bytVy}>
      <button
        type="submit"
        name="vy"
        value={`kund:${slug}`}
        // Knappvokabulären och inte egna klasser: den står bredvid "Profil och
        // tillägg" i samma cell, och två knappar i samma rad ska se likadana ut.
        className={`${btnSecondary} ${btnLiten}`}
        // Skärmläsare får hela meningen; seende ser knapptexten i sin rad.
        aria-label={text({
          sv: `Öppna arbetsytan för ${namn} i admin-läge`,
          en: `Open the workspace for ${namn} in admin mode`
        })}
      >
        <Eye className="h-3.5 w-3.5" aria-hidden />
        {text({ sv: "Öppna", en: "Open" })}
      </button>
    </form>
  );
}
