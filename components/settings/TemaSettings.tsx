"use client";

import { useState } from "react";
import { Vaxel } from "@/components/settings/Vaxel";
import { Rad, Radlista } from "@/components/ui";
import { colorScheme, dataTheme, TEMA_COOKIE, type Tema } from "@/lib/tema";

/**
 * Ljust eller mörkt — den enda inställningen utan Spara-knapp.
 *
 * ## Varför ingen Spara-knapp
 *
 * Temat är det enda valet på hela /settings där resultatet ÄR förhandsvisningen.
 * Man klickar och ser om det blev bra. En Spara-knapp mellan klicket och
 * effekten hade betytt att man byter läge, tittar, och sedan måste bekräfta det
 * man redan ser — och den som glömmer bekräfta får tillbaka det gamla läget vid
 * nästa laddning utan att förstå varför.
 *
 * ## Varför både attributet och cookien skrivs, i den ordningen
 *
 * `document.documentElement` byts FÖRST, så att sidan vänder i samma bildruta
 * som klicket. Cookien är till för NÄSTA sidladdning: app/layout.tsx läser den
 * på servern och stämplar `data-theme` innan HTML:en skickas, vilket är det som
 * gör att mörkt läge inte blinkar vitt vid varje navigering.
 *
 * Ingen serveråtgärd, ingen omladdning. En `router.refresh()` här hade kastat
 * bort hela klientträdet för att byta ett attribut som redan är bytt.
 *
 * ## Varför startvärdet kommer som en PROP och inte ur DOM:en
 *
 * Första versionen läste `document.documentElement.dataset.theme`, med
 * motiveringen att attributet redan ÄR sanningen och att en prop skulle skapa
 * ett andra värde som kan hamna ur fas. Argumentet var fel, och felet var
 * mätbart.
 *
 * Den här komponenten renderas nämligen på servern också — "use client"
 * betyder "hydreras i webbläsaren", inte "körs bara där". På servern finns
 * inget `document`, så växeln renderades i läge AV medan resten av sidan var
 * mörk. Klienten rättade den vid hydrering, och React svarade med #418.
 *
 * Det syntes BARA med cookien satt till `morkt` — alltså i exakt det läge en
 * användare som valt mörkt möter varje gång, och aldrig i det läge man råkar
 * testa i först. Uppmätt med Playwright mot dev-miljön, per sida och per tema.
 *
 * Servern läser cookien i SettingsSection och skickar ner den. Det är inte en
 * andra sanning: det är samma cookie som app/layout.tsx redan läser för att
 * stämpla <html>, läst i samma request.
 */
export function TemaSettings({ initial }: Readonly<{ initial: Tema }>) {
  const [tema, setTema] = useState<Tema>(initial);

  function valj(nytt: Tema) {
    setTema(nytt);

    const rot = document.documentElement;
    const attribut = dataTheme(nytt);
    if (attribut) {
      rot.dataset.theme = attribut;
    } else {
      // delete och inte data-theme="light": :root ÄR den ljusa paletten, och en
      // andra selektor för samma sak är en till plats att glömma. Se globals.css.
      delete rot.dataset.theme;
    }
    rot.style.colorScheme = colorScheme(nytt);

    // Ett år. Samma livslängd som scope-cookien — ett utseendeval som går ut
    // efter en session är ett val man får göra om varje måndag.
    document.cookie = `${TEMA_COOKIE}=${nytt}; path=/; max-age=31536000; samesite=lax`;
  }

  // En rad, samma form som övriga inställningar. "Hur det sparas" stod här
  // som en egen etikett med ett stycke under, och sidrubrikens ingress sa
  // samma sak en gång till; nu är det en mening vid växeln. Provbiten med
  // "Brödtext på papper", "Primär knapp" och "Accent" är borttagen: växeln
  // byter hela sidan, så sidan ÄR förhandsvisningen, och rutans text handlade
  // bara om rutan själv (F-018).
  return (
    <Radlista ariaLabel="Tema">
      <Rad>
        <Vaxel
          etikett="Mörkt läge"
          beskrivning="Valet gäller bara den här webbläsaren och slår igenom direkt. På en annan dator börjar arbetsytan i ljust läge tills du väljer om."
          pa={tema === "morkt"}
          onChange={(pa) => valj(pa ? "morkt" : "ljust")}
        />
      </Rad>
    </Radlista>
  );
}
