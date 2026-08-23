"use client";

import { useState } from "react";
import { Vaxel } from "@/components/settings/Vaxel";
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

  return (
    <div className="grid gap-7">
      <div className="border-t border-ink/15 pt-5">
        <Vaxel
          etikett="Mörkt läge"
          beskrivning="Byter arbetsytans papper mot svart. Allt annat följer med — text, hårlinjer, accenter och grafer — eftersom hela gränssnittet målas genom samma färgvariabler."
          pa={tema === "morkt"}
          onChange={(pa) => valj(pa ? "morkt" : "ljust")}
        />
      </div>

      <div className="border-t border-ink/15 pt-5">
        <p className="kicker text-mineral">Hur det sparas</p>
        <p className="mt-3 max-w-[60ch] text-[0.875rem] leading-6 text-ink/60">
          Valet ligger i den här webbläsaren och gäller direkt — det finns inget
          att spara. Loggar du in på en annan dator börjar den i ljust läge tills
          du väljer om.
        </p>
      </div>

      {/* Provbiten. En växel som ändrar hela sidan behöver inte en
          förhandsvisning — men rutan visar de fyra rollerna vid sidan av
          varandra, och det är där ett tema faktiskt går sönder: när accenten
          slutar synas mot papperet eller den dämpade texten blir oläslig. */}
      <div className="border-t border-ink/15 pt-5">
        <p className="kicker text-mineral">Så ser ytorna ut</p>
        <div className="mt-4 rounded-panel border border-ink/15 bg-paper2/50 p-5">
          <p className="text-[15px] font-medium text-ink">Brödtext på papper</p>
          <p className="mt-1 text-[0.875rem] leading-6 text-mineral">
            Dämpad text — hjälptexter, tidsstämplar och etiketter.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <span className="rounded-input bg-ink px-3 py-1.5 text-[0.8125rem] font-semibold text-paper">
              Primär knapp
            </span>
            <span className="rounded-input border border-ochre/40 bg-ochre/10 px-3 py-1.5 text-[0.8125rem] text-warning">
              Accent
            </span>
            <span className="text-[0.8125rem] text-moss">Klart</span>
            <span className="text-[0.8125rem] text-danger">Fel</span>
          </div>
        </div>
      </div>
    </div>
  );
}
