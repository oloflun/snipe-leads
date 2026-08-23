/**
 * Ljust eller mörkt läge — ett VISNINGSVAL, och därför en cookie.
 *
 * ## Varför inte databasen
 *
 * Notisinställningarna nedanför i menyn är en rad i `notification_preferences`,
 * eftersom de styr vad systemet GÖR åt kunden när ingen tittar. Temat styr bara
 * hur den här skärmen ser ut just nu, och det finns ingen serverprocess som
 * behöver veta det. En kolumn hade betytt en rundtur till databasen innan
 * första pixeln kunde ritas.
 *
 * ## Varför inte localStorage
 *
 * Det var det uppenbara valet och det är fel av ett mätbart skäl: sidorna
 * renderas på servern. En klient som läser localStorage och sedan sätter temat
 * gör det EFTER att den ljusa sidan redan målats — resultatet är en vit blink
 * vid varje sidladdning för den som valt mörkt. Cookien läses i
 * app/layout.tsx, alltså innan HTML:en lämnar servern, och `data-theme` står
 * på `<html>` från första byten.
 *
 * Samma resonemang som `SCOPE_COOKIE` i lib/routes.ts, och den kommentaren
 * beskriver samma läxa: en inställning servern behöver får inte bo på ett
 * ställe servern inte ser.
 *
 * Inte httpOnly: växeln skriver den i webbläsaren. Den är ett utseendeval, inte
 * ett behörighetsval — ingenting grindas på den.
 */
export const TEMA_COOKIE = "snajp.tema";

export type Tema = "ljust" | "morkt";

export const TEMA_STANDARD: Tema = "ljust";

export function isTema(value: string): value is Tema {
  return value === "ljust" || value === "morkt";
}

export function parseTema(value: string | undefined | null): Tema {
  return value && isTema(value) ? value : TEMA_STANDARD;
}

/**
 * Värdet som hamnar i `<html data-theme>`.
 *
 * Ljust läge stämplar INGENTING. `:root` bär redan den ljusa paletten, och en
 * `data-theme="light"` hade betytt två selektorer som säger samma sak — den
 * dagen någon justerar en ljus token är det femtio procents risk att den
 * hamnar i fel av dem.
 */
export function dataTheme(tema: Tema): "dark" | undefined {
  return tema === "morkt" ? "dark" : undefined;
}

/** Vad webbläsaren ska rita sina egna kontroller i (rullister, fältmarkörer). */
export function colorScheme(tema: Tema): "dark" | "light" {
  return tema === "morkt" ? "dark" : "light";
}
